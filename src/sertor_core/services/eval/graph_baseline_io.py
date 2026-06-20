"""Read/write the graph non-regression baseline `eval/graph_baseline.toml` (066, artifacts-toml.md).

Twin of `baseline_io.py` (IR), DISTINCT file (DA-a/REQ-031): flat scalar schema (no `[hit_rate]`
sub-table). Read with `tomllib`, write with a minimal hand-rolled serializer; written/updated ONLY
on an explicit `--record-baseline`. Absent → `load_graph_baseline` returns `None` (legitimate
absence, gate passes — REQ-033); malformed → `SuiteValidationError`. Round-trip validated after
write (`SuiteWriteError`, fail-safe).
"""
from __future__ import annotations

import tomllib
from datetime import UTC, datetime
from pathlib import Path

from sertor_core.domain.errors import SuiteValidationError, SuiteWriteError
from sertor_core.services.eval.models import GraphBaseline


def now_iso_utc() -> str:
    """Current time as ISO-8601 UTC with a trailing `Z` (the `recorded_at` of a baseline)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_graph_baseline(path: Path) -> GraphBaseline | None:
    """Load the graph baseline at `path`, or `None` when the file is absent (REQ-033).

    Absence is NOT an error (no recorded reference yet) — the run reports `no-baseline`. A
    present-but-malformed file IS an error (`SuiteValidationError`): a curated file.
    """
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise SuiteValidationError(-1, f"malformed graph baseline TOML: {exc}") from exc
    try:
        return GraphBaseline(
            mean_f1=float(data["mean_f1"]),
            mean_recall=float(data["mean_recall"]),
            mean_precision=float(data["mean_precision"]),
            cases=int(data["cases"]),
            recorded_at=str(data.get("recorded_at", "")),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise SuiteValidationError(-1, f"malformed graph baseline: {exc}") from exc


def _serialize_graph_baseline(baseline: GraphBaseline) -> str:
    """Serialize the graph baseline to flat TOML (scalars only — artifacts-toml.md)."""
    return (
        "\n".join(
            [
                f'recorded_at = "{baseline.recorded_at}"',
                f"cases = {baseline.cases}",
                f"mean_f1 = {baseline.mean_f1!r}",
                f"mean_recall = {baseline.mean_recall!r}",
                f"mean_precision = {baseline.mean_precision!r}",
            ]
        )
        + "\n"
    )


def write_graph_baseline(path: Path, baseline: GraphBaseline) -> None:
    """Persist the graph baseline with round-trip validation (REQ-044-twin, fail-safe)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _serialize_graph_baseline(baseline)
    path.write_text(text, encoding="utf-8")
    try:
        reloaded = load_graph_baseline(path)
    except (SuiteValidationError, tomllib.TOMLDecodeError, OSError) as exc:
        raise SuiteWriteError(str(path)) from exc
    if (
        reloaded is None
        or reloaded.mean_f1 != baseline.mean_f1
        or reloaded.mean_recall != baseline.mean_recall
        or reloaded.mean_precision != baseline.mean_precision
    ):
        raise SuiteWriteError(str(path))
