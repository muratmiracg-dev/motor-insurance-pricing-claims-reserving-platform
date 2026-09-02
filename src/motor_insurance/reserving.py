from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ReservingResult:
    incremental_triangle: pd.DataFrame
    cumulative_triangle: pd.DataFrame
    development_factors: pd.DataFrame
    accident_period_summary: pd.DataFrame
    portfolio_summary: dict[str, float]


def _quarter_ordinal(values: pd.Series) -> np.ndarray:
    dates = pd.to_datetime(values)
    return dates.dt.year.to_numpy() * 4 + dates.dt.quarter.to_numpy() - 1


def _quarter_label(ordinal: int) -> str:
    return f"{ordinal // 4}Q{ordinal % 4 + 1}"


def build_incremental_triangle(
    claims: pd.DataFrame,
    payments: pd.DataFrame,
    valuation_date: str | pd.Timestamp,
) -> pd.DataFrame:
    valuation = pd.Timestamp(valuation_date)
    valuation_ordinal = valuation.year * 4 + valuation.quarter - 1
    claim_dates = claims[["claim_id", "claim_date"]].copy()
    claim_dates["claim_date"] = pd.to_datetime(claim_dates["claim_date"])
    claim_dates["accident_ordinal"] = _quarter_ordinal(claim_dates["claim_date"])
    accident_ordinals = np.arange(claim_dates["accident_ordinal"].min(), valuation_ordinal + 1)
    max_development = valuation_ordinal - int(accident_ordinals.min())

    triangle = pd.DataFrame(
        np.nan,
        index=[_quarter_label(int(value)) for value in accident_ordinals],
        columns=list(range(max_development + 1)),
        dtype=float,
    )
    for accident_ordinal in accident_ordinals:
        max_observed = valuation_ordinal - int(accident_ordinal)
        triangle.loc[_quarter_label(int(accident_ordinal)), list(range(max_observed + 1))] = 0.0

    if not payments.empty:
        merged = payments.merge(claim_dates, on="claim_id", how="left", validate="many_to_one")
        merged["payment_date"] = pd.to_datetime(merged["payment_date"])
        merged = merged.loc[merged["payment_date"] <= valuation].copy()
        merged["payment_ordinal"] = _quarter_ordinal(merged["payment_date"])
        merged["development_quarter"] = merged["payment_ordinal"] - merged["accident_ordinal"]
        grouped = (
            merged.groupby(["accident_ordinal", "development_quarter"], as_index=False)["payment_amount"]
            .sum()
        )
        for row in grouped.itertuples(index=False):
            if row.development_quarter >= 0:
                triangle.loc[_quarter_label(int(row.accident_ordinal)), int(row.development_quarter)] = float(row.payment_amount)
    triangle.index.name = "accident_quarter"
    triangle.columns.name = "development_quarter"
    return triangle


def _cumulative_triangle(incremental: pd.DataFrame) -> pd.DataFrame:
    cumulative = incremental.fillna(0.0).cumsum(axis=1)
    cumulative = cumulative.mask(incremental.isna())
    cumulative.index.name = incremental.index.name
    cumulative.columns.name = incremental.columns.name
    return cumulative


def _development_factors(cumulative: pd.DataFrame) -> np.ndarray:
    factors: list[float] = []
    for development in range(cumulative.shape[1] - 1):
        current = cumulative.iloc[:, development]
        following = cumulative.iloc[:, development + 1]
        valid = current.notna() & following.notna() & (current > 0)
        denominator = float(current.loc[valid].sum())
        numerator = float(following.loc[valid].sum())
        raw_factor = numerator / denominator if denominator > 0 else 1.0
        factors.append(max(float(raw_factor), 1.0))
    return np.asarray(factors, dtype=float)


def chain_ladder(
    incremental: pd.DataFrame,
    policies: pd.DataFrame,
    claims: pd.DataFrame,
    expected_loss_ratio: float,
) -> ReservingResult:
    cumulative = _cumulative_triangle(incremental)
    factors = _development_factors(cumulative)
    factor_table = pd.DataFrame(
        {
            "from_development_quarter": np.arange(len(factors)),
            "to_development_quarter": np.arange(1, len(factors) + 1),
            "age_to_age_factor": factors,
        }
    )

    summary_records: list[dict[str, float | int | str]] = []
    for accident_quarter, row in cumulative.iterrows():
        observed = row.dropna()
        if observed.empty:
            last_development = 0
            latest_paid = 0.0
        else:
            last_development = int(observed.index[-1])
            latest_paid = float(observed.iloc[-1])
        future_factor = float(np.prod(factors[last_development:])) if last_development < len(factors) else 1.0
        chain_ultimate = latest_paid * future_factor
        reported_percentage = min(1.0 / max(future_factor, 1.0), 1.0)
        summary_records.append(
            {
                "accident_quarter": accident_quarter,
                "latest_development_quarter": last_development,
                "latest_paid": latest_paid,
                "chain_ladder_ultimate": chain_ultimate,
                "chain_ladder_ibnr": max(chain_ultimate - latest_paid, 0.0),
                "reported_percentage": reported_percentage,
            }
        )
    summary = pd.DataFrame(summary_records)

    policy_premium = policies.copy()
    policy_premium["accident_quarter"] = pd.to_datetime(policy_premium["policy_start"]).dt.to_period("Q").astype(str)
    premium_by_quarter = policy_premium.groupby("accident_quarter", as_index=False)["earned_premium"].sum()
    summary = summary.merge(premium_by_quarter, on="accident_quarter", how="left")
    summary["earned_premium"] = summary["earned_premium"].fillna(0.0)
    summary["expected_ultimate"] = summary["earned_premium"] * expected_loss_ratio
    summary["bf_ultimate"] = (
        summary["latest_paid"]
        + summary["expected_ultimate"] * (1.0 - summary["reported_percentage"])
    )
    summary["bf_ibnr"] = np.maximum(summary["bf_ultimate"] - summary["latest_paid"], 0.0)

    truth = claims.copy()
    truth["accident_quarter"] = pd.to_datetime(truth["claim_date"]).dt.to_period("Q").astype(str)
    truth_by_quarter = (
        truth.groupby("accident_quarter", as_index=False)["ultimate_incurred_synthetic_truth"]
        .sum()
        .rename(columns={"ultimate_incurred_synthetic_truth": "synthetic_true_ultimate"})
    )
    summary = summary.merge(truth_by_quarter, on="accident_quarter", how="left")
    summary["synthetic_true_ultimate"] = summary["synthetic_true_ultimate"].fillna(0.0)
    denominator = summary["synthetic_true_ultimate"].replace(0, np.nan)
    summary["chain_ladder_error_pct"] = (summary["chain_ladder_ultimate"] - denominator) / denominator
    summary["bf_error_pct"] = (summary["bf_ultimate"] - denominator) / denominator

    total_latest_paid = float(summary["latest_paid"].sum())
    total_chain_ultimate = float(summary["chain_ladder_ultimate"].sum())
    total_bf_ultimate = float(summary["bf_ultimate"].sum())
    total_truth = float(summary["synthetic_true_ultimate"].sum())
    portfolio_summary = {
        "latest_paid": round(total_latest_paid, 2),
        "chain_ladder_ultimate": round(total_chain_ultimate, 2),
        "chain_ladder_ibnr": round(max(total_chain_ultimate - total_latest_paid, 0.0), 2),
        "bornhuetter_ferguson_ultimate": round(total_bf_ultimate, 2),
        "bornhuetter_ferguson_ibnr": round(max(total_bf_ultimate - total_latest_paid, 0.0), 2),
        "synthetic_true_ultimate": round(total_truth, 2),
        "chain_ladder_total_error_pct": round((total_chain_ultimate - total_truth) / max(total_truth, 1.0), 6),
        "bornhuetter_ferguson_total_error_pct": round((total_bf_ultimate - total_truth) / max(total_truth, 1.0), 6),
    }
    numeric_columns = summary.select_dtypes(include=["number"]).columns
    summary[numeric_columns] = summary[numeric_columns].round(6)
    return ReservingResult(
        incremental_triangle=incremental,
        cumulative_triangle=cumulative,
        development_factors=factor_table,
        accident_period_summary=summary,
        portfolio_summary=portfolio_summary,
    )
