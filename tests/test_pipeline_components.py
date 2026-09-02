from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

from motor_insurance.config import load_config
from motor_insurance.data_generation import generate_portfolio
from motor_insurance.fraud import score_claims_for_review
from motor_insurance.metrics import build_analysis_frame, compute_portfolio_kpis
from motor_insurance.pricing import fit_pricing_models
from motor_insurance.reserving import build_incremental_triangle, chain_ladder


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PipelineComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        base_config = load_config(PROJECT_ROOT / "config" / "project.yaml")
        cls.config = replace(base_config, n_policies=6_000)
        cls.datasets = generate_portfolio(cls.config)
        cls.analysis = build_analysis_frame(
            cls.datasets["policies"],
            cls.datasets["customers"],
            cls.datasets["vehicles"],
            cls.datasets["claims"],
        )

    def test_generation_is_referentially_consistent(self) -> None:
        policies = self.datasets["policies"]
        claims = self.datasets["claims"]
        payments = self.datasets["claim_payments"]
        self.assertEqual(policies["policy_id"].nunique(), len(policies))
        self.assertTrue(claims["policy_id"].isin(policies["policy_id"]).all())
        self.assertTrue(payments["claim_id"].isin(claims["claim_id"]).all())
        self.assertTrue((policies["exposure_years"] > 0).all())

    def test_generation_is_deterministic(self) -> None:
        second = generate_portfolio(self.config)
        first_values = self.datasets["policies"].head(20)["annual_written_premium"].to_numpy()
        second_values = second["policies"].head(20)["annual_written_premium"].to_numpy()
        np.testing.assert_allclose(first_values, second_values)

    def test_portfolio_metrics_are_coherent(self) -> None:
        metrics = compute_portfolio_kpis(
            self.datasets["policies"],
            self.datasets["claims"],
            expense_ratio=self.config.expense_ratio,
        )
        self.assertGreater(metrics["claim_frequency"], 0)
        self.assertGreater(metrics["average_incurred_severity"], 0)
        self.assertGreater(metrics["combined_ratio"], metrics["loss_ratio"])

    def test_pricing_predictions_are_positive(self) -> None:
        result = fit_pricing_models(self.analysis, self.config)
        self.assertTrue((result.scores["predicted_annual_frequency"] > 0).all())
        self.assertTrue((result.scores["predicted_average_severity"] > 0).all())
        self.assertGreater(result.metrics["oot_policy_count"], 0)

    def test_reserving_outputs_are_non_negative(self) -> None:
        triangle = build_incremental_triangle(
            self.datasets["claims"],
            self.datasets["claim_payments"],
            self.config.valuation_date,
        )
        result = chain_ladder(
            triangle,
            self.datasets["policies"],
            self.datasets["claims"],
            self.config.expected_loss_ratio,
        )
        self.assertGreaterEqual(result.portfolio_summary["chain_ladder_ibnr"], 0)
        self.assertGreaterEqual(result.portfolio_summary["bornhuetter_ferguson_ibnr"], 0)
        self.assertTrue((result.development_factors["age_to_age_factor"] >= 1).all())

    def test_fraud_triage_has_human_control_boundary(self) -> None:
        result = score_claims_for_review(self.datasets["claims"], self.config.fraud_alert_rate)
        self.assertEqual(result.metrics["automated_claim_denials"], 0)
        self.assertTrue(result.scored_claims["decision_boundary"].str.contains("Human review").all())
        self.assertTrue(result.scored_claims["triage_score"].between(0, 100).all())


if __name__ == "__main__":
    unittest.main()
