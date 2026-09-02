from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VerifiedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with (PROJECT_ROOT / "artifacts" / "run_manifest.json").open("r", encoding="utf-8") as handle:
            cls.manifest = json.load(handle)

    def test_verified_run_identity(self) -> None:
        self.assertEqual(self.manifest["seed"], 20260902)
        self.assertEqual(self.manifest["valuation_date"], "2025-12-31")
        self.assertEqual(self.manifest["policy_count"], 60_000)

    def test_pricing_calibration_acceptance_band(self) -> None:
        pricing = self.manifest["pricing_validation"]
        self.assertTrue(0.85 <= pricing["oot_frequency_calibration_ratio"] <= 1.15)
        self.assertTrue(0.80 <= pricing["oot_pure_premium_calibration_ratio"] <= 1.20)

    def test_reserving_and_triage_controls(self) -> None:
        reserve = self.manifest["reserving_validation"]
        triage = self.manifest["fraud_triage_validation"]
        self.assertGreaterEqual(reserve["chain_ladder_ibnr"], 0)
        self.assertGreaterEqual(reserve["bornhuetter_ferguson_ibnr"], 0)
        self.assertGreater(triage["precision_lift_vs_random"], 1)
        self.assertEqual(triage["automated_claim_denials"], 0)


if __name__ == "__main__":
    unittest.main()
