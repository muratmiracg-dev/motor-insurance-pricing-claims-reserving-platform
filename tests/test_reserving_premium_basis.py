"""Bornhuetter-Ferguson must use premium earned in each accident quarter."""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from motor_insurance.config import load_config  # noqa: E402
from motor_insurance.data_generation import generate_portfolio  # noqa: E402
from motor_insurance.reserving import (  # noqa: E402
    _earned_premium_by_accident_quarter,
    build_incremental_triangle,
    chain_ladder,
)


def policies(*rows: tuple[str, str, float]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["policy_start", "policy_end", "earned_premium"])


def allocation(frame: pd.DataFrame, valuation: str) -> dict[str, float]:
    result = _earned_premium_by_accident_quarter(frame, pd.Timestamp(valuation))
    return dict(zip(result["accident_quarter"], result["earned_premium"].round(6)))


class EarnedPremiumAllocationTests(unittest.TestCase):
    def test_annual_policy_is_spread_by_days_in_each_quarter(self) -> None:
        # 2024-01-01..2024-12-30 = 365 earned days; one unit of premium per day.
        result = allocation(policies(("2024-01-01", "2024-12-30", 365.0)), "2025-03-31")
        self.assertEqual(result["2024Q1"], 91.0)  # leap-year February
        self.assertEqual(result["2024Q2"], 91.0)
        self.assertEqual(result["2024Q3"], 92.0)
        self.assertEqual(result["2024Q4"], 91.0)
        self.assertEqual(result["2025Q1"], 0.0)

    def test_exposure_after_valuation_is_not_earned(self) -> None:
        # Earned premium already covers 2025-11-01..2025-12-31 (61 days) at valuation.
        result = allocation(policies(("2025-11-01", "2026-10-31", 61.0)), "2025-12-31")
        self.assertEqual(result, {"2025Q4": 61.0})

    def test_policy_starting_after_valuation_contributes_nothing(self) -> None:
        frame = policies(("2025-01-01", "2025-12-31", 90.0), ("2026-02-01", "2027-01-31", 0.0))
        result = allocation(frame, "2025-03-31")
        self.assertEqual(result, {"2025Q1": 90.0})

    def test_total_premium_is_preserved(self) -> None:
        frame = policies(
            ("2023-02-14", "2024-02-13", 1_000.0),
            ("2023-07-01", "2024-06-29", 2_500.0),
            ("2024-11-15", "2025-11-14", 410.0),
        )
        result = allocation(frame, "2024-12-31")
        self.assertAlmostEqual(sum(result.values()), 3_910.0, places=4)

    def test_invalid_policy_inputs_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "policy_end"):
            _earned_premium_by_accident_quarter(
                pd.DataFrame({"policy_start": ["2024-01-01"], "earned_premium": [1.0]}),
                pd.Timestamp("2024-12-31"),
            )
        with self.assertRaisesRegex(ValueError, "before policy_start"):
            allocation(policies(("2024-05-01", "2024-04-01", 1.0)), "2024-12-31")
        with self.assertRaisesRegex(ValueError, "non-negative"):
            allocation(policies(("2024-01-01", "2024-12-30", -1.0)), "2024-12-31")


class BornhuetterFergusonBasisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        base = load_config(PROJECT_ROOT / "config" / "project.yaml")
        cls.config = replace(base, n_policies=6_000)
        cls.data = generate_portfolio(cls.config)
        triangle = build_incremental_triangle(
            cls.data["claims"], cls.data["claim_payments"], cls.config.valuation_date
        )
        cls.result = chain_ladder(
            triangle,
            cls.data["policies"],
            cls.data["claims"],
            cls.config.expected_loss_ratio,
            valuation_date=cls.config.valuation_date,
        )

    def test_accident_quarter_premium_reconciles_to_portfolio_earned_premium(self) -> None:
        summary = self.result.accident_period_summary
        self.assertAlmostEqual(
            summary["earned_premium"].sum(),
            self.data["policies"]["earned_premium"].sum(),
            delta=1.0,
        )

    def test_implied_loss_ratios_are_plausible_in_every_quarter(self) -> None:
        # With premium booked on the policy-start quarter, the implied ratio ranged from
        # about 0.08 (first quarter) to 5.2 (valuation quarter).
        summary = self.result.accident_period_summary
        ratio = summary["synthetic_true_ultimate"] / summary["earned_premium"]
        self.assertTrue(np.all((ratio > 0.3) & (ratio < 1.5)), ratio.round(3).tolist())

    def test_bf_ultimate_is_close_to_synthetic_truth(self) -> None:
        # Previously about -13% in total and -69% in the valuation quarter.
        self.assertLess(abs(self.result.portfolio_summary["bornhuetter_ferguson_total_error_pct"]), 0.05)

    def test_valuation_date_defaults_to_last_triangle_quarter(self) -> None:
        triangle = self.result.incremental_triangle
        inferred = chain_ladder(
            triangle, self.data["policies"], self.data["claims"], self.config.expected_loss_ratio
        )
        self.assertEqual(inferred.portfolio_summary, self.result.portfolio_summary)


if __name__ == "__main__":
    unittest.main()
