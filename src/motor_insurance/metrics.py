from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def compute_portfolio_kpis(
    policies: pd.DataFrame,
    claims: pd.DataFrame,
    expense_ratio: float,
) -> dict[str, Any]:
    exposure = float(policies["exposure_years"].sum())
    written_premium = float(policies["annual_written_premium"].sum())
    earned_premium = float(policies["earned_premium"].sum())
    commission_expense = float((policies["earned_premium"] * policies["commission_ratio"]).sum())
    operating_expense = float(earned_premium * expense_ratio)
    paid = float(claims["paid_to_date"].sum())
    case_reserve = float(claims["case_reserve"].sum())
    incurred = float(claims["incurred_amount"].sum())
    ultimate_truth = float(claims["ultimate_incurred_synthetic_truth"].sum())
    claim_count = int(len(claims))
    open_claims = int((claims["claim_status"] == "Open").sum())
    closed_claims = claim_count - open_claims

    loss_ratio = _safe_divide(incurred, earned_premium)
    expense_ratio_actual = _safe_divide(operating_expense + commission_expense, earned_premium)
    combined_ratio = loss_ratio + expense_ratio_actual

    return {
        "policy_count": int(len(policies)),
        "exposure_years": round(exposure, 2),
        "claim_count": claim_count,
        "open_claim_count": open_claims,
        "closed_claim_count": closed_claims,
        "written_premium": round(written_premium, 2),
        "earned_premium": round(earned_premium, 2),
        "paid_claims": round(paid, 2),
        "case_reserve": round(case_reserve, 2),
        "incurred_claims": round(incurred, 2),
        "ultimate_claims_synthetic_truth": round(ultimate_truth, 2),
        "claim_frequency": round(_safe_divide(claim_count, exposure), 6),
        "average_incurred_severity": round(_safe_divide(incurred, claim_count), 2),
        "loss_ratio": round(loss_ratio, 6),
        "expense_and_commission_ratio": round(expense_ratio_actual, 6),
        "combined_ratio": round(combined_ratio, 6),
        "open_claim_rate": round(_safe_divide(open_claims, claim_count), 6),
    }


def build_analysis_frame(
    policies: pd.DataFrame,
    customers: pd.DataFrame,
    vehicles: pd.DataFrame,
    claims: pd.DataFrame,
) -> pd.DataFrame:
    claim_agg = (
        claims.groupby("policy_id", as_index=False)
        .agg(
            claim_count=("claim_id", "count"),
            paid_claims=("paid_to_date", "sum"),
            case_reserve=("case_reserve", "sum"),
            incurred_claims=("incurred_amount", "sum"),
            ultimate_claims=("ultimate_incurred_synthetic_truth", "sum"),
            open_claim_count=("claim_status", lambda values: int((values == "Open").sum())),
        )
    )
    frame = (
        policies.merge(customers, on="customer_id", how="left", validate="one_to_one")
        .merge(vehicles, on="vehicle_id", how="left", validate="one_to_one")
        .merge(claim_agg, on="policy_id", how="left", validate="one_to_one")
    )
    financial_columns = [
        "claim_count",
        "paid_claims",
        "case_reserve",
        "incurred_claims",
        "ultimate_claims",
        "open_claim_count",
    ]
    frame[financial_columns] = frame[financial_columns].fillna(0)
    frame["claim_count"] = frame["claim_count"].astype(int)
    frame["open_claim_count"] = frame["open_claim_count"].astype(int)
    frame["policy_start"] = pd.to_datetime(frame["policy_start"])
    frame["policy_start_month_index"] = (
        (frame["policy_start"].dt.year - 2023) * 12 + frame["policy_start"].dt.month - 1
    )
    frame["actual_frequency"] = frame["claim_count"] / frame["exposure_years"].clip(lower=1e-6)
    frame["actual_average_severity"] = np.where(
        frame["claim_count"] > 0,
        frame["ultimate_claims"] / frame["claim_count"],
        np.nan,
    )
    frame["incurred_loss_ratio"] = frame["incurred_claims"] / frame["earned_premium"].clip(lower=1.0)
    return frame


def segment_performance(analysis_frame: pd.DataFrame, dimensions: list[str]) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for dimension in dimensions:
        grouped = (
            analysis_frame.groupby(dimension, dropna=False)
            .agg(
                policy_count=("policy_id", "count"),
                exposure_years=("exposure_years", "sum"),
                earned_premium=("earned_premium", "sum"),
                claim_count=("claim_count", "sum"),
                incurred_claims=("incurred_claims", "sum"),
                ultimate_claims=("ultimate_claims", "sum"),
            )
            .reset_index()
            .rename(columns={dimension: "segment"})
        )
        grouped.insert(0, "dimension", dimension)
        grouped["claim_frequency"] = grouped["claim_count"] / grouped["exposure_years"].clip(lower=1e-6)
        grouped["average_severity"] = np.where(
            grouped["claim_count"] > 0,
            grouped["incurred_claims"] / grouped["claim_count"],
            np.nan,
        )
        grouped["loss_ratio"] = grouped["incurred_claims"] / grouped["earned_premium"].clip(lower=1.0)
        records.append(grouped)
    output = pd.concat(records, ignore_index=True)
    numeric_columns = output.select_dtypes(include=["number"]).columns
    output[numeric_columns] = output[numeric_columns].round(6)
    return output


def finite_json_values(payload: dict[str, Any]) -> dict[str, Any]:
    """Replace non-finite floats before JSON serialization."""
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, float) and not math.isfinite(value):
            cleaned[key] = None
        elif isinstance(value, np.generic):
            cleaned[key] = value.item()
        else:
            cleaned[key] = value
    return cleaned
