"""Adapter filesystem di `GradingSource`: `<ws>/eval-<id>/<config>/run-<n>/grading.json`."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import CONFIGS
from ..jsonfiles import load_validated

_EVAL_DIR = re.compile(r"^eval-(\d+)$")
_RUN_DIR = re.compile(r"^run-(\d+)$")


class FsGradingSource:
    def runs(self, workspace: Path) -> dict[tuple[int, str], list[dict]]:
        out: dict[tuple[int, str], list[dict]] = {}
        if not workspace.is_dir():
            return out
        for eval_dir in sorted(workspace.iterdir()):
            m = _EVAL_DIR.match(eval_dir.name)
            if not (m and eval_dir.is_dir()):
                continue
            for cfg in CONFIGS:
                cfg_dir = eval_dir / cfg
                if not cfg_dir.is_dir():
                    continue
                run_dirs = sorted(
                    (d for d in cfg_dir.iterdir() if _RUN_DIR.match(d.name)),
                    key=lambda d: int(_RUN_DIR.match(d.name).group(1)),
                )
                gradings = [load_validated(d / "grading.json", "grading") for d in run_dirs]
                if gradings:
                    out[(int(m.group(1)), cfg)] = gradings
        return out
