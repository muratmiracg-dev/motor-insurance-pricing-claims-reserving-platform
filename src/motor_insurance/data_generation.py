from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .config import ProjectConfig


REGIONS = np.array(["Marmara", "Central Anatolia", "Aegean", "Mediterranean", "Black Sea", "Eastern Anatolia", "Southeastern Anatolia"])
REGION_PROBABILITIES = np.array([0.34, 0.19, 0.15, 0.12, 0.09, 0.05, 0.06])
REGION_RISK = {
    "Marmara": 1.18,
    "Central Anatolia": 0.98,
    "Aegean": 1.02,
    "Mediterranean": 1.07,
    "Black Sea": 1.03,
    "Eastern Anatolia": 0.88,
    "Southeastern Anatolia": 0.94,
}
VEHICLE_SEGMENTS = np.array(["A-Mini", "B-Compact", "C-Medium", "D-Large", "SUV", "LCV"])
SEGMENT_PROBABILITIES = np.array([0.08, 0.24, 0.29, 0.10, 0.20, 0.09])
SEGMENT_VALUE = {
    "A-Mini": 620_000.0,
    "B-Compact": 880_000.0,
    "C-Medium": 1_250_000.0,
    "D-Large": 1_900_000.0,
    "SUV": 1_650_000.0,
    "LCV": 1_100_000.0,
}


def _factor(values: np.ndarray, mapping: dict[str, float]) -> np.ndarray:
    return np.fromiter((mapping[str(value)] for value in values), dtype=float, count=len(values))


def _date_array(start: pd.Timestamp, offsets: np.ndarray) -> pd.Series:
    return pd.Series(start + pd.to_timedelta(offsets, unit="D"))


def generate_portfolio(config: ProjectConfig, n_policies: int | None = None) -> dict[str, pd.DataFrame]:
    """Generate a deterministic, Turkish-market-inspired synthetic motor portfolio.

    The data are intentionally synthetic. Aggregate assumptions are plausible rather
    than representations of any insurer, customer, tariff, or claim file.
    """

    n = int(n_policies or config.n_policies)
    rng = np.random.default_rng(config.seed)
    valuation = pd.Timestamp(config.valuation_date)
    portfolio_start = pd.Timestamp(config.portfolio_start)
    latest_start = valuation - pd.Timedelta(days=30)
    start_span = (latest_start - portfolio_start).days + 1

    policy_start = _date_array(portfolio_start, rng.integers(0, start_span, size=n))
    policy_end = policy_start + pd.to_timedelta(364, unit="D")
    observation_end = pd.Series(np.minimum(policy_end.values, np.datetime64(valuation)))
    exposure_days = (observation_end - policy_start).dt.days.to_numpy() + 1
    exposure_years = np.clip(exposure_days / 365.25, 30 / 365.25, 1.0)

    driver_age = np.clip(np.rint(rng.normal(42, 12, size=n)), 18, 78).astype(int)
    license_years = np.minimum(
        np.maximum(driver_age - 18, 0),
        np.clip(np.rint(rng.normal(14, 9, size=n)), 0, 55).astype(int),
    )
    region = rng.choice(REGIONS, size=n, p=REGION_PROBABILITIES)
    vehicle_segment = rng.choice(VEHICLE_SEGMENTS, size=n, p=SEGMENT_PROBABILITIES)
    vehicle_age = np.clip(rng.gamma(shape=2.3, scale=3.2, size=n).astype(int), 0, 20)
    base_values = _factor(vehicle_segment, SEGMENT_VALUE)
    vehicle_value = base_values * np.exp(rng.normal(0, 0.18, size=n)) * np.power(0.93, vehicle_age)
    vehicle_value = np.round(np.clip(vehicle_value, 180_000, 4_500_000), -3)
    annual_km = np.round(np.clip(rng.lognormal(np.log(14_000), 0.42, size=n), 3_000, 70_000), -2)
    no_claim_years = np.clip(rng.poisson(2.2, size=n), 0, 6)

    usage_type = rng.choice(["Private", "Commercial", "Fleet"], size=n, p=[0.83, 0.11, 0.06])
    sales_channel = rng.choice(["Agency", "Bank", "Direct", "Broker"], size=n, p=[0.58, 0.14, 0.22, 0.06])
    coverage_package = rng.choice(["Standard", "Extended", "Premium"], size=n, p=[0.56, 0.34, 0.10])
    fuel_type = rng.choice(["Petrol", "Diesel", "Hybrid", "Electric"], size=n, p=[0.38, 0.43, 0.13, 0.06])
    deductible = rng.choice([0, 2_500, 5_000, 10_000], size=n, p=[0.54, 0.23, 0.16, 0.07]).astype(float)

    young_factor = np.where(driver_age < 25, 1.62, np.where(driver_age > 67, 1.20, 1.0))
    experience_factor = np.where(license_years < 3, 1.28, 1.0)
    vehicle_age_factor = np.where(vehicle_age >= 12, 1.22, np.where(vehicle_age <= 2, 0.94, 1.0))
    usage_factor = np.select([usage_type == "Commercial", usage_type == "Fleet"], [1.43, 1.22], default=1.0)
    km_factor = np.clip(np.power(annual_km / 14_000, 0.34), 0.72, 1.52)
    no_claim_factor = np.clip(1.0 - 0.075 * no_claim_years, 0.58, 1.0)
    region_factor = _factor(region, REGION_RISK)
    annual_frequency = 0.155 * young_factor * experience_factor * vehicle_age_factor * usage_factor * km_factor * no_claim_factor * region_factor
    annual_frequency = np.clip(annual_frequency, 0.035, 0.72)

    coverage_factor = np.select(
        [coverage_package == "Extended", coverage_package == "Premium"],
        [1.10, 1.21],
        default=1.0,
    )
    policy_year_fraction = (
        (policy_start.dt.year.to_numpy() - portfolio_start.year)
        + (policy_start.dt.month.to_numpy() - 1) / 12
    )
    pricing_inflation_factor = np.power(1.0 + config.annual_claim_inflation, policy_year_fraction)
    expected_severity = (
        72_000
        * np.power(vehicle_value / 900_000, 0.55)
        * coverage_factor
        * np.where(usage_type == "Commercial", 1.10, 1.0)
        * pricing_inflation_factor
    )
    expected_pure_premium = annual_frequency * expected_severity
    target_loss_ratio = np.clip(rng.normal(config.expected_loss_ratio, 0.055, size=n), 0.50, 0.82)
    deductible_credit = np.select([deductible == 2_500, deductible == 5_000, deductible == 10_000], [0.96, 0.92, 0.86], default=1.0)
    annual_written_premium = expected_pure_premium / target_loss_ratio * deductible_credit * np.exp(rng.normal(0, 0.10, size=n))
    annual_written_premium = np.round(np.clip(annual_written_premium, 3_000, 180_000), 2)
    earned_premium = np.round(annual_written_premium * exposure_years, 2)

    customer_ids = np.array([f"CUS-{i:07d}" for i in range(1, n + 1)])
    vehicle_ids = np.array([f"VEH-{i:07d}" for i in range(1, n + 1)])
    policy_ids = np.array([f"POL-{i:07d}" for i in range(1, n + 1)])

    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "driver_age": driver_age,
            "license_years": license_years,
            "region": region,
            "customer_tenure_years": np.clip(rng.gamma(2.2, 2.1, size=n), 0, 18).round(1),
        }
    )
    vehicles = pd.DataFrame(
        {
            "vehicle_id": vehicle_ids,
            "vehicle_segment": vehicle_segment,
            "vehicle_age": vehicle_age,
            "vehicle_value": vehicle_value,
            "fuel_type": fuel_type,
            "annual_km": annual_km.astype(int),
        }
    )
    channel_commission = {"Agency": 0.15, "Bank": 0.13, "Direct": 0.06, "Broker": 0.17}
    policies = pd.DataFrame(
        {
            "policy_id": policy_ids,
            "customer_id": customer_ids,
            "vehicle_id": vehicle_ids,
            "policy_start": policy_start,
            "policy_end": policy_end,
            "observation_end": observation_end,
            "underwriting_year": policy_start.dt.year,
            "usage_type": usage_type,
            "sales_channel": sales_channel,
            "coverage_package": coverage_package,
            "deductible": deductible,
            "no_claim_years": no_claim_years,
            "exposure_years": exposure_years.round(6),
            "annual_written_premium": annual_written_premium,
            "earned_premium": earned_premium,
            "commission_ratio": pd.Series(sales_channel).map(channel_commission).to_numpy(),
            "expected_annual_frequency_seed": annual_frequency.round(6),
            "expected_severity_seed": expected_severity.round(2),
        }
    )

    claim_counts = np.minimum(rng.poisson(annual_frequency * exposure_years), 4)
    policy_index = np.repeat(np.arange(n), claim_counts)
    m = len(policy_index)
    if m == 0:
        raise RuntimeError("Synthetic generator produced no claims; increase policy count.")

    available_days = exposure_days[policy_index]
    loss_offsets = np.floor(rng.random(m) * available_days).astype(int)
    claim_date = policy_start.iloc[policy_index].reset_index(drop=True) + pd.to_timedelta(loss_offsets, unit="D")
    report_delay_days = np.clip(rng.negative_binomial(2, 0.55, size=m), 0, 30)
    report_date = claim_date + pd.to_timedelta(report_delay_days, unit="D")
    claim_type = rng.choice(
        ["Collision", "Glass", "Theft", "Weather", "Vandalism"],
        size=m,
        p=[0.65, 0.15, 0.04, 0.09, 0.07],
    )
    claim_share = {"Collision": 0.072, "Glass": 0.011, "Theft": 0.72, "Weather": 0.047, "Vandalism": 0.030}
    share = _factor(claim_type, claim_share)
    claim_year_fraction = (claim_date.dt.year.to_numpy() - portfolio_start.year) + (claim_date.dt.month.to_numpy() - 1) / 12
    inflation_factor = np.power(1.0 + config.annual_claim_inflation, claim_year_fraction)
    raw_severity = vehicle_value[policy_index] * share * inflation_factor * rng.lognormal(mean=-0.12, sigma=0.62, size=m)
    ultimate = np.minimum(raw_severity, vehicle_value[policy_index] * 1.05)
    ultimate = np.round(np.clip(ultimate - deductible[policy_index] * 0.65, 750, None), 2)

    garage_count = max(80, int(np.sqrt(n) * 0.9))
    garage_ids = np.array([f"GAR-{i:04d}" for i in range(1, garage_count + 1)])
    garage_weights = rng.dirichlet(np.full(garage_count, 1.5))
    assigned_garage = rng.choice(garage_ids, size=m, p=garage_weights)
    watchlist_garages = set(rng.choice(garage_ids, size=max(5, garage_count // 18), replace=False))
    garage_watchlist = np.fromiter((g in watchlist_garages for g in assigned_garage), dtype=bool, count=m)

    policy_tenure_days = (claim_date.reset_index(drop=True) - policy_start.iloc[policy_index].reset_index(drop=True)).dt.days.to_numpy()
    repeated_claim = claim_counts[policy_index] >= 2
    severity_ratio = ultimate / np.maximum(expected_severity[policy_index], 1)
    fraud_probability = (
        0.012
        + 0.085 * (policy_tenure_days <= 30)
        + 0.075 * garage_watchlist
        + 0.045 * repeated_claim
        + 0.055 * (severity_ratio >= 2.2)
        + 0.025 * (report_delay_days >= 10)
    )
    fraud_probability = np.clip(fraud_probability, 0.005, 0.38)
    fraud_truth = rng.random(m) < fraud_probability
    ultimate = np.round(ultimate * np.where(fraud_truth, rng.uniform(1.04, 1.28, size=m), 1.0), 2)

    claim_ids = np.array([f"CLM-{i:07d}" for i in range(1, m + 1)])
    hour_weights = np.array([2, 2, 2, 2, 2, 3, 4, 6, 6, 5, 5, 5, 5, 5, 5, 6, 7, 8, 8, 7, 5, 4, 3, 2], dtype=float)
    loss_hour = rng.choice(np.arange(24), size=m, p=hour_weights / hour_weights.sum())

    payment_records: list[dict[str, object]] = []
    paid_to_date = np.zeros(m, dtype=float)
    full_payment_date: list[pd.Timestamp] = []
    for idx in range(m):
        payment_count = int(rng.integers(1, 4 if claim_type[idx] != "Theft" else 3))
        claim_year_delay = 1.0 + 0.10 * max(int(claim_date.iloc[idx].year) - portfolio_start.year, 0)
        claim_type_delay = {
            "Glass": 0.62,
            "Collision": 1.00,
            "Vandalism": 1.10,
            "Weather": 1.24,
            "Theft": 1.55,
        }[str(claim_type[idx])]
        base_delays = np.sort(
            np.clip(
                (rng.gamma(shape=1.5, scale=70, size=payment_count) * claim_year_delay * claim_type_delay).astype(int),
                3,
                900,
            )
        )
        fractions = rng.dirichlet(np.full(payment_count, 1.7))
        scheduled_dates = report_date.iloc[idx] + pd.to_timedelta(base_delays, unit="D")
        full_payment_date.append(pd.Timestamp(scheduled_dates.max()))
        for payment_no, (payment_date, fraction) in enumerate(zip(scheduled_dates, fractions, strict=True), start=1):
            if payment_date <= valuation:
                amount = round(float(ultimate[idx] * fraction), 2)
                paid_to_date[idx] += amount
                payment_records.append(
                    {
                        "payment_id": f"PAY-{len(payment_records) + 1:08d}",
                        "claim_id": claim_ids[idx],
                        "payment_no": payment_no,
                        "payment_date": payment_date,
                        "payment_amount": amount,
                        "payment_type": "Indemnity",
                    }
                )

    remaining = np.maximum(ultimate - paid_to_date, 0)
    is_closed = np.array([payment_date <= valuation for payment_date in full_payment_date])
    reserve_noise = np.clip(rng.normal(0.96, 0.13, size=m), 0.55, 1.35)
    case_reserve = np.where(is_closed, 0.0, remaining * reserve_noise)
    incurred = paid_to_date + case_reserve
    closure_date = pd.Series([date_value if closed else pd.NaT for date_value, closed in zip(full_payment_date, is_closed, strict=True)])

    claims = pd.DataFrame(
        {
            "claim_id": claim_ids,
            "policy_id": policy_ids[policy_index],
            "customer_id": customer_ids[policy_index],
            "vehicle_id": vehicle_ids[policy_index],
            "claim_date": claim_date.reset_index(drop=True),
            "report_date": report_date.reset_index(drop=True),
            "closure_date": closure_date,
            "claim_type": claim_type,
            "claim_status": np.where(is_closed, "Closed", "Open"),
            "garage_id": assigned_garage,
            "garage_watchlist_signal": garage_watchlist,
            "policy_tenure_days": policy_tenure_days,
            "report_delay_days": report_delay_days,
            "loss_hour": loss_hour,
            "paid_to_date": np.round(paid_to_date, 2),
            "case_reserve": np.round(case_reserve, 2),
            "incurred_amount": np.round(incurred, 2),
            "ultimate_incurred_synthetic_truth": ultimate,
            "fraud_synthetic_truth": fraud_truth,
        }
    )
    payments = pd.DataFrame(payment_records)

    garages = pd.DataFrame(
        {
            "garage_id": garage_ids,
            "garage_region": rng.choice(REGIONS, size=garage_count, p=REGION_PROBABILITIES),
            "network_watchlist_signal": [garage_id in watchlist_garages for garage_id in garage_ids],
        }
    )

    datasets = {
        "customers": customers,
        "vehicles": vehicles,
        "policies": policies,
        "claims": claims,
        "claim_payments": payments,
        "garages": garages,
    }
    validate_datasets(datasets)
    return datasets


def validate_datasets(datasets: dict[str, pd.DataFrame]) -> None:
    policies = datasets["policies"]
    claims = datasets["claims"]
    payments = datasets["claim_payments"]

    if policies["policy_id"].duplicated().any():
        raise ValueError("policy_id must be unique")
    if claims["claim_id"].duplicated().any():
        raise ValueError("claim_id must be unique")
    if not claims["policy_id"].isin(policies["policy_id"]).all():
        raise ValueError("Every claim must reference a policy")
    if not payments["claim_id"].isin(claims["claim_id"]).all():
        raise ValueError("Every payment must reference a claim")
    if (policies[["exposure_years", "annual_written_premium", "earned_premium"]].to_numpy() < 0).any():
        raise ValueError("Policy exposure and premium values must be non-negative")
    if (claims[["paid_to_date", "case_reserve", "incurred_amount"]].to_numpy() < 0).any():
        raise ValueError("Claim financial values must be non-negative")


def save_datasets(
    datasets: dict[str, pd.DataFrame],
    config: ProjectConfig,
    write_samples: bool = True,
) -> None:
    config.raw_dir.mkdir(parents=True, exist_ok=True)
    sample_dir = config.root / "data" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in datasets.items():
        frame.to_csv(config.raw_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d")
        if write_samples:
            frame.head(config.sample_rows).to_csv(sample_dir / f"{name}_sample.csv", index=False, date_format="%Y-%m-%d")


def with_policy_count(config: ProjectConfig, n_policies: int) -> ProjectConfig:
    return replace(config, n_policies=int(n_policies))
