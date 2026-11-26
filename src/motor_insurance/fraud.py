from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class FraudTriageResult:
    scored_claims: pd.DataFrame
    metrics: dict[str, Any]


def score_claims_for_review(claims: pd.DataFrame, alert_rate: float = 0.05) -> FraudTriageResult:
    """Create an explainable review-priority score.

    The score is a workflow aid only. It cannot reject, delay, or reduce a claim
    without authorized human investigation and documented evidence.
    """

    if (
        isinstance(alert_rate, (bool, np.bool_))
        or not np.isfinite(alert_rate)
        or not 0 < alert_rate <= 1
    ):
        raise ValueError("alert_rate must be a finite value in (0, 1]")
    if claims.empty:
        raise ValueError("claims must contain at least one record")
    required = {
        "claim_id",
        "customer_id",
        "report_date",
        "incurred_amount",
        "policy_tenure_days",
        "report_delay_days",
        "loss_hour",
        "garage_watchlist_signal",
        "fraud_synthetic_truth",
    }
    missing = sorted(required.difference(claims.columns))
    if missing:
        raise ValueError(f"claims are missing required triage columns: {missing}")
    for column in ("claim_id", "customer_id"):
        values = claims[column]
        if values.isna().any() or values.astype(str).str.strip().eq("").any():
            raise ValueError(f"{column} must contain populated identifiers")
    numeric = claims[
        ["incurred_amount", "policy_tenure_days", "report_delay_days", "loss_hour"]
    ].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("fraud triage numeric inputs must be finite")
    if (numeric[["incurred_amount", "policy_tenure_days", "report_delay_days"]] < 0).any().any():
        raise ValueError("fraud triage monetary and duration inputs cannot be negative")
    if not numeric["loss_hour"].between(0, 23).all():
        raise ValueError("loss_hour must be between 0 and 23")
    report_date = pd.to_datetime(claims["report_date"], errors="coerce")
    if report_date.isna().any():
        raise ValueError("report_date must contain only valid dates")
    claims = claims.assign(
        **{column: numeric[column] for column in numeric}, report_date=report_date
    )
    for column in ("garage_watchlist_signal", "fraud_synthetic_truth"):
        values = claims[column]
        if not values.map(lambda value: isinstance(value, (bool, np.bool_))).all():
            raise ValueError(f"{column} must contain only boolean values")

    frame = claims.copy()
    # Claims the same customer had already reported when this claim arrived. Counting the
    # customer's whole claim file let a first claim be flagged because of a claim reported
    # months later: information the reviewer cannot have at triage time, which inflated the
    # measured precision and lift.
    prior_customer_claims = (
        frame.groupby("customer_id")["report_date"].rank(method="min").astype(int) - 1
    )
    high_severity_threshold = float(frame["incurred_amount"].quantile(0.95))
    very_high_severity_threshold = float(frame["incurred_amount"].quantile(0.99))

    short_tenure = frame["policy_tenure_days"] <= 30
    delayed_report = frame["report_delay_days"] >= 10
    unusual_hour = (frame["loss_hour"] <= 4) | (frame["loss_hour"] >= 23)
    repeated_customer = prior_customer_claims >= 1
    high_severity = frame["incurred_amount"] >= high_severity_threshold
    very_high_severity = frame["incurred_amount"] >= very_high_severity_threshold
    watchlist_garage = frame["garage_watchlist_signal"]

    score = (
        short_tenure.astype(int) * 24
        + delayed_report.astype(int) * 12
        + unusual_hour.astype(int) * 9
        + repeated_customer.astype(int) * 14
        + high_severity.astype(int) * 15
        + very_high_severity.astype(int) * 8
        + watchlist_garage.astype(int) * 22
    )
    frame["prior_customer_claims"] = prior_customer_claims
    frame["triage_score"] = np.clip(score, 0, 100)
    # Review capacity is a fixed share of claims. Rule scores take few distinct values, so a
    # plain score cut-off can admit every tied claim and overshoot the queue; ties at the
    # boundary are broken by incurred amount (largest exposure first), then claim_id.
    queue_size = math.ceil(alert_rate * len(frame))
    queue_order = frame.assign(_claim_id=frame["claim_id"].astype(str)).sort_values(
        ["triage_score", "incurred_amount", "_claim_id"],
        ascending=[False, False, True],
        kind="mergesort",
    )
    selected = queue_order.index[:queue_size]
    frame["review_recommended"] = frame.index.isin(selected)
    threshold = float(frame.loc[selected, "triage_score"].min())
    frame["review_priority"] = pd.cut(
        frame["triage_score"],
        bins=[-1, 19, 39, 59, 100],
        labels=["Low", "Moderate", "High", "Critical"],
    ).astype(str)

    reasons: list[str] = []
    for idx in frame.index:
        row_reasons: list[str] = []
        if short_tenure.loc[idx]:
            row_reasons.append("CLAIM_WITHIN_30_DAYS")
        if delayed_report.loc[idx]:
            row_reasons.append("REPORT_DELAY_10_PLUS_DAYS")
        if unusual_hour.loc[idx]:
            row_reasons.append("UNUSUAL_LOSS_HOUR")
        if repeated_customer.loc[idx]:
            row_reasons.append("REPEATED_CLAIMANT")
        if high_severity.loc[idx]:
            row_reasons.append("HIGH_SEVERITY")
        if watchlist_garage.loc[idx]:
            row_reasons.append("GARAGE_NETWORK_SIGNAL")
        reasons.append(";".join(row_reasons) if row_reasons else "NO_MATERIAL_RULE_SIGNAL")
    frame["reason_codes"] = reasons
    frame["decision_boundary"] = "Human review required; no automated adverse action"

    alerted = frame["review_recommended"]
    truth = frame["fraud_synthetic_truth"]
    alert_count = int(alerted.sum())
    precision = float(truth.loc[alerted].mean()) if alert_count else 0.0
    recall = float((alerted & truth).sum() / max(int(truth.sum()), 1))
    baseline_rate = float(truth.mean())
    metrics: dict[str, Any] = {
        "claim_count": len(frame),
        "alert_count": alert_count,
        "alert_rate": round(float(alerted.mean()), 6),
        "score_threshold": threshold,
        "synthetic_truth_rate": round(baseline_rate, 6),
        "precision_at_alert_rate": round(precision, 6),
        "recall_at_alert_rate": round(recall, 6),
        "precision_lift_vs_random": round(precision / max(baseline_rate, 1e-9), 6),
        "automated_claim_denials": 0,
    }
    return FraudTriageResult(scored_claims=frame, metrics=metrics)
