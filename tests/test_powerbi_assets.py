from __future__ import annotations

import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class TestPowerBIAssets(unittest.TestCase):
    def test_theme_is_valid_json(self) -> None:
        theme = json.loads((ROOT / "powerbi/theme/motor-insurance-theme.json").read_text())
        self.assertEqual(theme["name"], "Motor Insurance Executive")
        self.assertGreaterEqual(len(theme["dataColors"]), 6)

    def test_all_dashboard_pages_have_mockups(self) -> None:
        mockups = list((ROOT / "powerbi/mockups").glob("*.png"))
        self.assertEqual(len(mockups), 6)
        self.assertTrue(all(path.stat().st_size > 25_000 for path in mockups))

    def test_operational_claim_export_excludes_synthetic_truth(self) -> None:
        builder = (ROOT / "scripts/build_powerbi_assets.py").read_text()
        self.assertIn('"fraud_synthetic_truth"', builder)
        self.assertIn('"ultimate_incurred_synthetic_truth"', builder)
        self.assertIn(".drop(", builder)

    def test_data_contract_sources_exist(self) -> None:
        contract = pd.read_csv(ROOT / "powerbi/model/model_contract.csv")
        for row in contract.itertuples(index=False):
            target = ROOT / "powerbi" / row.source
            if row.storage == "versioned":
                self.assertTrue(target.exists(), row.source)
            else:
                self.assertEqual(row.storage, "generated")
                self.assertIn(target.stem, (ROOT / "scripts/build_powerbi_assets.py").read_text())


if __name__ == "__main__":
    unittest.main()
