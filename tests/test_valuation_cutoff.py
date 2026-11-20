"""Losses reported after the valuation date are IBNR, not open claims."""

from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

import pandas as pd

from motor_insurance.config import load_config
from motor_insurance.data_generation import (
    generate_portfolio,
    reported_claims,
    validate_datasets,
)
from motor_insurance.metrics import compute_portfolio_kpis

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class GeneratedValuationCutoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = load_config(PROJECT_ROOT / "config" / "project.yaml")
        cls.config = replace(config, n_policies=12_000)
        cls.datasets = generate_portfolio(cls.config)
        cls.valuation = pd.Timestamp(cls.config.valuation_date)

    def test_claims_reported_after_valuation_are_unreported_ibnr(self) -> None:
        claims = self.datasets["claims"]
        late = pd.to_datetime(claims["report_date"]) > self.valuation
        # The fixture must contain the case being tested.
        self.assertGreater(int(late.sum()), 0)
        self.assertTrue((claims.loc[late, "claim_status"] == "Unreported").all())
        self.assertTrue((claims.loc[late, ["paid_to_date", "case_reserve", "incurred_amount"]] == 0).all().all())
        self.assertTrue((claims.loc[late, "ultimate_incurred_synthetic_truth"] > 0).all())
        self.assertFalse((claims.loc[~late, "claim_status"] == "Unreported").any())

    def test_reported_claims_excludes_only_unreported(self) -> None:
        claims = self.datasets["claims"]
        known = reported_claims(claims)
        self.assertTrue((pd.to_datetime(known["report_date"]) <= self.valuation).all())
        self.assertEqual(len(known), int((claims["claim_status"] != "Unreported").sum()))


class PortfolioKpiCutoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policies = pd.DataFrame(
            {
                "exposure_years": [1.0, 1.0],
                "annual_written_premium": [1_000.0, 1_000.0],
                "earned_premium": [1_000.0, 1_000.0],
                "commission_ratio": [0.1, 0.1],
            }
        )
        self.claims = pd.DataFrame(
            {
                "claim_status": ["Open", "Closed", "Unreported"],
                "paid_to_date": [100.0, 300.0, 0.0],
                "case_reserve": [200.0, 0.0, 0.0],
                "incurred_amount": [300.0, 300.0, 0.0],
                "ultimate_incurred_synthetic_truth": [320.0, 300.0, 500.0],
            }
        )

    def test_kpis_count_only_reported_claims(self) -> None:
        kpis = compute_portfolio_kpis(self.policies, self.claims, expense_ratio=0.2)
        self.assertEqual(kpis["claim_count"], 2)
        self.assertEqual(kpis["open_claim_count"], 1)
        self.assertEqual(kpis["closed_claim_count"], 1)
        self.assertEqual(kpis["unreported_claim_count_synthetic_truth"], 1)
        self.assertEqual(kpis["claim_frequency"], 1.0)
        self.assertEqual(kpis["average_incurred_severity"], 300.0)
        self.assertEqual(kpis["open_claim_rate"], 0.5)
        # The synthetic truth still includes the IBNR loss.
        self.assertEqual(kpis["ultimate_claims_synthetic_truth"], 1_120.0)


class UnreportedClaimValidationTests(unittest.TestCase):
    def _datasets(self, **claim_overrides: object) -> dict[str, pd.DataFrame]:
        claim = {
            "claim_id": "CLM-1",
            "policy_id": "POL-1",
            "claim_status": "Unreported",
            "paid_to_date": 0.0,
            "case_reserve": 0.0,
            "incurred_amount": 0.0,
        }
        claim.update(claim_overrides)
        return {
            "policies": pd.DataFrame(
                {
                    "policy_id": ["POL-1"],
                    "exposure_years": [1.0],
                    "annual_written_premium": [1.0],
                    "earned_premium": [1.0],
                }
            ),
            "claims": pd.DataFrame([claim]),
            "claim_payments": pd.DataFrame({"claim_id": pd.Series([], dtype=str)}),
        }

    def test_accepts_unreported_claim_without_amounts(self) -> None:
        validate_datasets(self._datasets())

    def test_rejects_unreported_claim_with_case_reserve(self) -> None:
        with self.assertRaisesRegex(ValueError, "not yet reported"):
            validate_datasets(self._datasets(case_reserve=10.0, incurred_amount=10.0))

    def test_rejects_unknown_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "claim_status"):
            validate_datasets(self._datasets(claim_status="Pending"))


if __name__ == "__main__":
    unittest.main()
