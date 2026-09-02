from __future__ import annotations

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

    frame = claims.copy()
    customer_claim_count = frame.groupby("customer_id")["claim_id"].transform("count")
    high_severity_threshold = float(frame["incurred_amount"].quantile(0.95))
    very_high_severity_threshold = float(frame["incurred_amount"].quantile(0.99))

    short_tenure = frame["policy_tenure_days"] <= 30
    delayed_report = frame["report_delay_days"] >= 10
    unusual_hour = (frame["loss_hour"] <= 4) | (frame["loss_hour"] >= 23)
    repeated_customer = customer_claim_count >= 2
    high_severity = frame["incurred_amount"] >= high_severity_threshold
    very_high_severity = frame["incurred_amount"] >= very_high_severity_threshold
    watchlist_garage = frame["garage_watchlist_signal"].astype(bool)

    score = (
        short_tenure.astype(int) * 24
        + delayed_report.astype(int) * 12
        + unusual_hour.astype(int) * 9
        + repeated_customer.astype(int) * 14
        + high_severity.astype(int) * 15
        + very_high_severity.astype(int) * 8
        + watchlist_garage.astype(int) * 22
    )
    frame["triage_score"] = np.clip(score, 0, 100)
    threshold = float(frame["triage_score"].quantile(max(0.0, 1.0 - alert_rate), interpolation="lower"))
    frame["review_recommended"] = frame["triage_score"] >= threshold
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
    truth = frame["fraud_synthetic_truth"].astype(bool)
    alert_count = int(alerted.sum())
    precision = float(truth.loc[alerted].mean()) if alert_count else 0.0
    recall = float((alerted & truth).sum() / max(int(truth.sum()), 1))
    baseline_rate = float(truth.mean())
    metrics: dict[str, Any] = {
        "claim_count": int(len(frame)),
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
