from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import GammaRegressor, PoissonRegressor
from sklearn.metrics import mean_gamma_deviance, mean_poisson_deviance
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import ProjectConfig

CATEGORICAL_FEATURES = [
    "region",
    "vehicle_segment",
    "usage_type",
    "sales_channel",
    "coverage_package",
    "fuel_type",
]
NUMERICAL_FEATURES = [
    "driver_age",
    "license_years",
    "customer_tenure_years",
    "vehicle_age",
    "vehicle_value",
    "annual_km",
    "deductible",
    "no_claim_years",
    "policy_start_month_index",
]
MODEL_FEATURES = CATEGORICAL_FEATURES + NUMERICAL_FEATURES


@dataclass
class PricingResult:
    scores: pd.DataFrame
    metrics: dict[str, Any]
    frequency_coefficients: pd.DataFrame
    severity_coefficients: pd.DataFrame


def _preprocessor() -> ColumnTransformer:
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
        ]
    )
    numerical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler(with_mean=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("categorical", categorical, CATEGORICAL_FEATURES),
            ("numerical", numerical, NUMERICAL_FEATURES),
        ],
        sparse_threshold=0.3,
    )


def _coefficient_table(model: Pipeline, label: str) -> pd.DataFrame:
    feature_names = model.named_steps["preprocess"].get_feature_names_out()
    coefficients = model.named_steps["model"].coef_
    table = pd.DataFrame(
        {
            "model": label,
            "feature": feature_names,
            "log_link_coefficient": coefficients,
            "multiplicative_effect": np.exp(np.clip(coefficients, -10, 10)),
            "absolute_coefficient": np.abs(coefficients),
        }
    )
    return table.sort_values("absolute_coefficient", ascending=False).drop(
        columns="absolute_coefficient"
    )


def fit_pricing_models(analysis_frame: pd.DataFrame, config: ProjectConfig) -> PricingResult:
    frame = analysis_frame.copy()
    required_numeric = [
        *NUMERICAL_FEATURES,
        "claim_count",
        "exposure_years",
        "commission_ratio",
        "annual_written_premium",
        "earned_premium",
        "ultimate_claims",
    ]
    numeric = frame[required_numeric].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("pricing inputs must contain only finite numeric values")
    if (numeric["exposure_years"] <= 0).any():
        raise ValueError("exposure_years must be positive")
    if (numeric["claim_count"] < 0).any() or not np.equal(
        numeric["claim_count"], np.floor(numeric["claim_count"])
    ).all():
        raise ValueError("claim_count must contain non-negative integers")
    if not numeric["commission_ratio"].between(0, 1, inclusive="left").all():
        raise ValueError("commission_ratio must be between 0 inclusive and 1 exclusive")
    if ((numeric["commission_ratio"] + config.expense_ratio) >= 1).any():
        raise ValueError("expense and commission ratios must leave a positive premium margin")
    positive_claims = frame["claim_count"] > 0
    severities = pd.to_numeric(
        frame.loc[positive_claims, "actual_average_severity"], errors="coerce"
    )
    if not np.isfinite(severities).all() or (severities <= 0).any():
        raise ValueError("positive claims require finite positive average severity")
    frame["policy_start"] = pd.to_datetime(frame["policy_start"])
    train_mask = frame["policy_start"] <= pd.Timestamp(config.train_end)
    test_mask = frame["policy_start"] >= pd.Timestamp(config.test_start)
    if not train_mask.any() or not test_mask.any():
        raise ValueError("Both training and out-of-time test observations are required")

    frequency_model = Pipeline(
        steps=[
            ("preprocess", _preprocessor()),
            ("model", PoissonRegressor(alpha=config.poisson_alpha, max_iter=600)),
        ]
    )
    frequency_target = frame["claim_count"] / frame["exposure_years"].clip(lower=1e-6)
    frequency_model.fit(
        frame.loc[train_mask, MODEL_FEATURES],
        frequency_target.loc[train_mask],
        model__sample_weight=frame.loc[train_mask, "exposure_years"],
    )

    severity_mask = train_mask & (frame["claim_count"] > 0) & (frame["actual_average_severity"] > 0)
    severity_test_mask = (
        test_mask & (frame["claim_count"] > 0) & (frame["actual_average_severity"] > 0)
    )
    if severity_mask.sum() < 50 or severity_test_mask.sum() < 20:
        raise ValueError("Insufficient positive-claim observations for the severity model")
    severity_model = Pipeline(
        steps=[
            ("preprocess", _preprocessor()),
            ("model", GammaRegressor(alpha=config.gamma_alpha, max_iter=800)),
        ]
    )
    severity_model.fit(
        frame.loc[severity_mask, MODEL_FEATURES],
        frame.loc[severity_mask, "actual_average_severity"],
        model__sample_weight=frame.loc[severity_mask, "claim_count"],
    )

    predicted_frequency = np.clip(frequency_model.predict(frame[MODEL_FEATURES]), 1e-6, None)
    predicted_severity = np.clip(severity_model.predict(frame[MODEL_FEATURES]), 1.0, None)
    predicted_pure_premium = predicted_frequency * predicted_severity
    net_premium_share = np.clip(
        1.0 - config.expense_ratio - frame["commission_ratio"].to_numpy(), 0.45, 0.85
    )
    technical_premium = predicted_pure_premium / net_premium_share
    pricing_adequacy = frame["annual_written_premium"].to_numpy() / np.maximum(
        technical_premium, 1.0
    )

    scores = frame[
        [
            "policy_id",
            "policy_start",
            "region",
            "vehicle_segment",
            "usage_type",
            "sales_channel",
            "coverage_package",
            "exposure_years",
            "annual_written_premium",
            "earned_premium",
            "claim_count",
            "ultimate_claims",
        ]
    ].copy()
    scores["dataset_split"] = np.where(train_mask, "Development", "Out-of-time")
    scores["predicted_annual_frequency"] = predicted_frequency
    scores["predicted_average_severity"] = predicted_severity
    scores["predicted_pure_premium"] = predicted_pure_premium
    scores["indicated_technical_premium"] = technical_premium
    scores["pricing_adequacy_index"] = pricing_adequacy
    scores["pricing_action"] = pd.cut(
        pricing_adequacy,
        bins=[-np.inf, 0.85, 1.15, np.inf],
        labels=["Review increase", "Adequate band", "Review competitiveness"],
    ).astype(str)

    test_frequency_target = frequency_target.loc[test_mask]
    test_frequency_prediction = predicted_frequency[test_mask.to_numpy()]
    frequency_deviance = mean_poisson_deviance(
        test_frequency_target,
        test_frequency_prediction,
        sample_weight=frame.loc[test_mask, "exposure_years"],
    )
    severity_test_prediction = predicted_severity[severity_test_mask.to_numpy()]
    severity_deviance = mean_gamma_deviance(
        frame.loc[severity_test_mask, "actual_average_severity"],
        severity_test_prediction,
        sample_weight=frame.loc[severity_test_mask, "claim_count"],
    )
    oot_actual_ultimate = float(frame.loc[test_mask, "ultimate_claims"].sum())
    oot_predicted_ultimate = float(
        np.sum(
            predicted_pure_premium[test_mask.to_numpy()]
            * frame.loc[test_mask, "exposure_years"].to_numpy()
        )
    )
    oot_frequency_actual = float(
        frame.loc[test_mask, "claim_count"].sum() / frame.loc[test_mask, "exposure_years"].sum()
    )
    oot_frequency_predicted = float(
        np.average(
            test_frequency_prediction,
            weights=frame.loc[test_mask, "exposure_years"],
        )
    )

    metrics: dict[str, Any] = {
        "development_policy_count": int(train_mask.sum()),
        "oot_policy_count": int(test_mask.sum()),
        "frequency_oot_mean_poisson_deviance": round(float(frequency_deviance), 6),
        "severity_oot_mean_gamma_deviance": round(float(severity_deviance), 6),
        "oot_actual_frequency": round(oot_frequency_actual, 6),
        "oot_predicted_frequency": round(oot_frequency_predicted, 6),
        "oot_frequency_calibration_ratio": round(
            oot_frequency_actual / max(oot_frequency_predicted, 1e-9), 6
        ),
        "oot_actual_ultimate_claims": round(oot_actual_ultimate, 2),
        "oot_predicted_ultimate_claims": round(oot_predicted_ultimate, 2),
        "oot_pure_premium_calibration_ratio": round(
            oot_actual_ultimate / max(oot_predicted_ultimate, 1.0), 6
        ),
        "underpriced_policy_share": round(
            float((pricing_adequacy[test_mask.to_numpy()] < 0.85).mean()), 6
        ),
        "adequate_band_policy_share": round(
            float(
                (
                    (pricing_adequacy[test_mask.to_numpy()] >= 0.85)
                    & (pricing_adequacy[test_mask.to_numpy()] <= 1.15)
                ).mean()
            ),
            6,
        ),
    }

    return PricingResult(
        scores=scores,
        metrics=metrics,
        frequency_coefficients=_coefficient_table(frequency_model, "Poisson frequency"),
        severity_coefficients=_coefficient_table(severity_model, "Gamma severity"),
    )
