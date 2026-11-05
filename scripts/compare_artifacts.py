"""Compare regenerated pipeline outputs in artifacts/ with a committed copy.

Numbers are compared with a tight tolerance (relative 1e-9, absolute 1e-9) so last-digit
floating-point noise between platforms passes, while real drift (for example from a changed
scikit-learn solver) fails. Text values, keys, columns and row order must match exactly.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL_TOL = 1e-9
ABS_TOL = 1e-9


def _as_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _same(expected: object, actual: object) -> bool:
    left, right = _as_number(expected), _as_number(actual)
    if left is not None and right is not None:
        if math.isnan(left) or math.isnan(right):
            return math.isnan(left) and math.isnan(right)
        return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return expected == actual


def _compare_json(expected: object, actual: object, where: str, errors: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            errors.append(f"{where}: keys differ")
            return
        for key in expected:
            _compare_json(expected[key], actual[key], f"{where}.{key}", errors)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            errors.append(f"{where}: length {len(expected)} != {len(actual)}")
            return
        for index, (left, right) in enumerate(zip(expected, actual)):
            _compare_json(left, right, f"{where}[{index}]", errors)
    elif not _same(expected, actual):
        errors.append(f"{where}: {expected!r} != {actual!r}")


def _compare_csv(expected: Path, actual: Path, name: str, errors: list[str]) -> None:
    with expected.open(newline="", encoding="utf-8") as left, actual.open(newline="", encoding="utf-8") as right:
        rows_left, rows_right = list(csv.reader(left)), list(csv.reader(right))
    if len(rows_left) != len(rows_right):
        errors.append(f"{name}: {len(rows_left)} rows != {len(rows_right)}")
        return
    for number, (row_left, row_right) in enumerate(zip(rows_left, rows_right), start=1):
        if len(row_left) != len(row_right):
            errors.append(f"{name} row {number}: column count differs")
            return
        for column, (left, right) in enumerate(zip(row_left, row_right)):
            if not _same(left, right):
                header = rows_left[0][column] if rows_left else column
                errors.append(f"{name} row {number} {header}: {left!r} != {right!r}")
                return


def compare(committed: Path, regenerated: Path) -> list[str]:
    errors: list[str] = []
    expected_files = {p.relative_to(committed) for p in committed.rglob("*") if p.is_file()}
    actual_files = {p.relative_to(regenerated) for p in regenerated.rglob("*") if p.is_file()}
    # Only committed outputs are compared; extra regenerated files (e.g. the git-ignored
    # policy_pricing_scores.csv) are working outputs, not part of the published record.
    for missing in sorted(expected_files - actual_files):
        errors.append(f"{missing}: missing from regenerated artifacts")
    for relative in sorted(expected_files & actual_files):
        left, right = committed / relative, regenerated / relative
        if relative.suffix == ".json":
            _compare_json(json.loads(left.read_text(encoding="utf-8")),
                          json.loads(right.read_text(encoding="utf-8")), str(relative), errors)
        elif relative.suffix == ".csv":
            _compare_csv(left, right, str(relative), errors)
        elif left.read_bytes() != right.read_bytes():
            errors.append(f"{relative}: bytes differ")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("committed", type=Path,
                        help="Copy of the committed artifacts/ taken before the pipeline ran")
    parser.add_argument("regenerated", type=Path, nargs="?", default=ROOT / "artifacts")
    args = parser.parse_args(argv)
    errors = compare(args.committed, args.regenerated)
    for error in errors[:50]:
        print(f"DRIFT {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} difference(s); regenerate with pinned requirements and review.", file=sys.stderr)
        return 1
    print("Regenerated artifacts match the committed outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
