"""Costo dichiarato del collaudo (FR-017): quante esecuzioni e valutazioni costerà, prima di partire."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import config
from .domain.errors import InputError
from .jsonfiles import load_validated


@dataclass(frozen=True)
class Cost:
    cases: int
    runs: int
    warnings: tuple[str, ...] = ()

    @property
    def executions(self) -> int:
        return self.cases * len(config.CONFIGS) * self.runs

    @property
    def gradings(self) -> int:
        return self.executions

    def to_dict(self) -> dict:
        return {
            "cases": self.cases,
            "runs": self.runs,
            "executions": self.executions,
            "gradings": self.gradings,
            "warnings": list(self.warnings),
        }


def compute_cost(skill_dir: Path, runs: int = config.DEFAULT_RUNS, evals_file: Path | None = None) -> Cost:
    if runs < 1:
        raise InputError("--runs", f"deve essere almeno 1 (ricevuto {runs})")
    evals = load_validated(evals_file or skill_dir / "evals" / "evals.json", "evals")
    cases = len(evals["evals"])
    warnings = (
        ()
        if cases == config.DEFAULT_CASES
        else (f"{cases} casi invece dei {config.DEFAULT_CASES} di default",)
    )
    return Cost(cases=cases, runs=runs, warnings=warnings)
