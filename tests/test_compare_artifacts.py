"""scripts/compare_artifacts.py: tolerant numeric comparison, strict structure."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "compare_artifacts", PROJECT_ROOT / "scripts" / "compare_artifacts.py"
)
compare_artifacts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_artifacts)


class CompareArtifactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        root = Path(self._temp.name)
        self.committed, self.regenerated = root / "committed", root / "regenerated"
        for folder in (self.committed, self.regenerated):
            (folder / "pricing").mkdir(parents=True)
            (folder / "pricing" / "coefficients.csv").write_text(
                "feature,coefficient\nage,0.2502309429143051\nregion,-0.1606\n", encoding="utf-8"
            )
            (folder / "metrics.json").write_text(
                json.dumps({"ultimate": 247477885.74, "status": "PASS", "rows": [1, 2]}),
                encoding="utf-8",
            )

    def tearDown(self) -> None:
        self._temp.cleanup()

    def errors(self) -> list[str]:
        return compare_artifacts.compare(self.committed, self.regenerated)

    def test_identical_outputs_match(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_last_digit_float_noise_is_tolerated(self) -> None:
        (self.regenerated / "pricing" / "coefficients.csv").write_text(
            "feature,coefficient\nage,0.25023094291432699\nregion,-0.1606\n", encoding="utf-8"
        )
        self.assertEqual(self.errors(), [])

    def test_model_drift_is_reported(self) -> None:
        (self.regenerated / "metrics.json").write_text(
            json.dumps({"ultimate": 247481484.77, "status": "PASS", "rows": [1, 2]}),
            encoding="utf-8",
        )
        self.assertEqual(self.errors(), ["metrics.json.ultimate: 247477885.74 != 247481484.77"])

    def test_text_structure_and_missing_files_are_reported(self) -> None:
        (self.regenerated / "pricing" / "coefficients.csv").write_text(
            "feature,coefficient\nregion,0.2502309429143051\nage,-0.1606\n", encoding="utf-8"
        )
        (self.regenerated / "metrics.json").unlink()
        errors = self.errors()
        self.assertIn("metrics.json: missing from regenerated artifacts", errors)
        self.assertTrue(any(e.startswith("pricing/coefficients.csv row 2") for e in errors))

    def test_extra_regenerated_files_are_ignored(self) -> None:
        shutil.copy(
            self.regenerated / "metrics.json", self.regenerated / "pricing" / "scores_ignored.json"
        )
        self.assertEqual(self.errors(), [])

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(compare_artifacts.main([str(self.committed), str(self.regenerated)]), 0)
        (self.regenerated / "metrics.json").write_text(json.dumps({"ultimate": 1}), encoding="utf-8")
        self.assertEqual(compare_artifacts.main([str(self.committed), str(self.regenerated)]), 1)


if __name__ == "__main__":
    unittest.main()
