from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ProjectConfig, load_config
from .data_generation import generate_portfolio, save_datasets, with_policy_count
from .fraud import score_claims_for_review
from .metrics import build_analysis_frame, compute_portfolio_kpis, finite_json_values, segment_performance
from .pricing import fit_pricing_models
from .reporting import write_excel_workbench, write_executive_summary, write_json
from .reserving import build_incremental_triangle, chain_ladder


def _ensure_directories(config: ProjectConfig) -> None:
    for path in [
        config.raw_dir,
        config.processed_dir,
        config.artifacts_dir / "metrics",
        config.artifacts_dir / "pricing",
        config.artifacts_dir / "reserving",
        config.artifacts_dir / "fraud",
        config.reports_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def run_pipeline(config: ProjectConfig) -> dict[str, Any]:
    _ensure_directories(config)
    datasets = generate_portfolio(config)
    save_datasets(datasets, config)

    analysis_frame = build_analysis_frame(
        datasets["policies"],
        datasets["customers"],
        datasets["vehicles"],
        datasets["claims"],
    )
    analysis_frame.to_csv(config.processed_dir / "policy_modeling_frame.csv", index=False, date_format="%Y-%m-%d")

    portfolio_kpis = finite_json_values(
        compute_portfolio_kpis(
            datasets["policies"],
            datasets["claims"],
            expense_ratio=config.expense_ratio,
        )
    )
    segment_table = segment_performance(
        analysis_frame,
        dimensions=["region", "vehicle_segment", "usage_type", "sales_channel", "coverage_package"],
    )
    segment_table.to_csv(config.artifacts_dir / "metrics" / "segment_performance.csv", index=False)
    write_json(portfolio_kpis, config.artifacts_dir / "metrics" / "portfolio_kpis.json")

    pricing = fit_pricing_models(analysis_frame, config)
    pricing.scores.to_csv(config.artifacts_dir / "pricing" / "policy_pricing_scores.csv", index=False, date_format="%Y-%m-%d")
    pricing.frequency_coefficients.to_csv(config.artifacts_dir / "pricing" / "frequency_coefficients.csv", index=False)
    pricing.severity_coefficients.to_csv(config.artifacts_dir / "pricing" / "severity_coefficients.csv", index=False)
    write_json(pricing.metrics, config.artifacts_dir / "pricing" / "pricing_metrics.json")

    incremental = build_incremental_triangle(
        datasets["claims"],
        datasets["claim_payments"],
        config.valuation_date,
    )
    reserve = chain_ladder(
        incremental,
        datasets["policies"],
        datasets["claims"],
        expected_loss_ratio=config.expected_loss_ratio,
    )
    reserve.incremental_triangle.to_csv(config.artifacts_dir / "reserving" / "incremental_paid_triangle.csv")
    reserve.cumulative_triangle.to_csv(config.artifacts_dir / "reserving" / "cumulative_paid_triangle.csv")
    reserve.development_factors.to_csv(config.artifacts_dir / "reserving" / "development_factors.csv", index=False)
    reserve.accident_period_summary.to_csv(config.artifacts_dir / "reserving" / "reserve_by_accident_quarter.csv", index=False)
    write_json(reserve.portfolio_summary, config.artifacts_dir / "reserving" / "reserve_metrics.json")

    fraud = score_claims_for_review(datasets["claims"], alert_rate=config.fraud_alert_rate)
    fraud.scored_claims.to_csv(config.artifacts_dir / "fraud" / "claim_triage_scores.csv", index=False, date_format="%Y-%m-%d")
    write_json(fraud.metrics, config.artifacts_dir / "fraud" / "triage_metrics.json")

    write_excel_workbench(
        config.reports_dir / "motor_insurance_analytics_workbench.xlsx",
        portfolio_kpis,
        segment_table,
        pricing.metrics,
        pricing.scores,
        reserve.portfolio_summary,
        reserve.accident_period_summary,
        reserve.development_factors,
        fraud.metrics,
        fraud.scored_claims,
    )
    write_executive_summary(
        config.reports_dir / "executive_analytical_summary.md",
        portfolio_kpis,
        pricing.metrics,
        reserve.portfolio_summary,
        fraud.metrics,
    )

    manifest = {
        "project": config.name,
        "seed": config.seed,
        "valuation_date": config.valuation_date.isoformat(),
        "policy_count": len(datasets["policies"]),
        "claim_count": len(datasets["claims"]),
        "payment_count": len(datasets["claim_payments"]),
        "portfolio_kpis": portfolio_kpis,
        "pricing_validation": pricing.metrics,
        "reserving_validation": reserve.portfolio_summary,
        "fraud_triage_validation": fraud.metrics,
    }
    write_json(manifest, config.artifacts_dir / "run_manifest.json")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the motor insurance analytics pipeline")
    parser.add_argument("--config", default="config/project.yaml", help="Path to project YAML configuration")
    parser.add_argument("--n-policies", type=int, default=None, help="Override policy count for a smaller or larger run")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config))
    if args.n_policies is not None:
        config = with_policy_count(config, args.n_policies)
    manifest = run_pipeline(config)
    print(
        "Pipeline completed: "
        f"{manifest['policy_count']:,} policies, "
        f"{manifest['claim_count']:,} claims, "
        f"valuation {manifest['valuation_date']}."
    )


if __name__ == "__main__":
    main()

