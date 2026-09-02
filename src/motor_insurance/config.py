from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    name: str
    seed: int
    valuation_date: date
    portfolio_start: date
    n_policies: int
    sample_rows: int
    expense_ratio: float
    commission_ratio: float
    expected_loss_ratio: float
    annual_claim_inflation: float
    train_end: date
    test_start: date
    poisson_alpha: float
    gamma_alpha: float
    fraud_alert_rate: float
    raw_dir: Path
    processed_dir: Path
    artifacts_dir: Path
    reports_dir: Path


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def load_config(path: str | Path) -> ProjectConfig:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle)

    root = config_path.parent.parent
    project = raw["project"]
    economics = raw["economics"]
    modeling = raw["modeling"]
    paths = raw["paths"]

    return ProjectConfig(
        root=root,
        name=str(project["name"]),
        seed=int(project["seed"]),
        valuation_date=date.fromisoformat(str(project["valuation_date"])),
        portfolio_start=date.fromisoformat(str(project["portfolio_start"])),
        n_policies=int(project["n_policies"]),
        sample_rows=int(project["sample_rows"]),
        expense_ratio=float(economics["expense_ratio"]),
        commission_ratio=float(economics["commission_ratio"]),
        expected_loss_ratio=float(economics["expected_loss_ratio"]),
        annual_claim_inflation=float(economics["annual_claim_inflation"]),
        train_end=date.fromisoformat(str(modeling["train_end"])),
        test_start=date.fromisoformat(str(modeling["test_start"])),
        poisson_alpha=float(modeling["poisson_alpha"]),
        gamma_alpha=float(modeling["gamma_alpha"]),
        fraud_alert_rate=float(modeling["fraud_alert_rate"]),
        raw_dir=_resolve(root, str(paths["raw_dir"])),
        processed_dir=_resolve(root, str(paths["processed_dir"])),
        artifacts_dir=_resolve(root, str(paths["artifacts_dir"])),
        reports_dir=_resolve(root, str(paths["reports_dir"])),
    )

