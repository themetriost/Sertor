"""Read/write the non-regression baseline `eval/baseline.toml` (065, contract artifacts-toml.md).

Same approach as `suite_io`: read with `tomllib`, write with a minimal hand-rolled serializer for
the flat schema (scalar fields + a `[hit_rate]` sub-table keyed by k). Written/updated ONLY on an
explicit `--record-baseline` (REQ-040/044); absent → `load_baseline` returns `None` (a legitimate
absence the caller handles explicitly, Principio IV — not an error). A malformed file is an
authoring bug → `SuiteValidationError`.
"""
from __future__ import annotations

import tomllib
from datetime import UTC, datetime
from pathlib import Path

from sertor_core.domain.errors import SuiteValidationError, SuiteWriteError
from sertor_core.services.eval.models import Baseline


def now_iso_utc() -> str:
    """Current time as ISO-8601 UTC with a trailing `Z` (the `recorded_at` of a baseline)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_baseline(path: Path) -> Baseline | None:
    """Load the baseline at `path`, or `None` when the file is absent (REQ-040).

    Absence is NOT an error (no recorded reference yet) — the run reports `no-baseline` and offers
    to record it. A present-but-malformed file IS an error (`SuiteValidationError`): curated file.
    """
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise SuiteValidationError(-1, f"malformed baseline TOML: {exc}") from exc
    try:
        mrr = float(data["mrr"])
        provider = str(data["provider"])
        queries = int(data["queries"])
        recorded_at = str(data.get("recorded_at", ""))
        raw_hit = data.get("hit_rate", {})
        if not isinstance(raw_hit, dict):
            raise SuiteValidationError(-1, "baseline `hit_rate` must be a table")
        hit_rate = {int(k): float(v) for k, v in raw_hit.items()}
    except (KeyError, ValueError, TypeError) as exc:
        raise SuiteValidationError(-1, f"malformed baseline: {exc}") from exc
    return Baseline(
        hit_rate=hit_rate,
        mrr=mrr,
        queries=queries,
        provider=provider,
        recorded_at=recorded_at,
    )


def _serialize_baseline(baseline: Baseline) -> str:
    """Serialize the baseline to flat TOML (scalars + `[hit_rate]` sub-table)."""
    provider = baseline.provider.replace("\\", "\\\\").replace('"', '\\"')
    lines = [
        f'recorded_at = "{baseline.recorded_at}"',
        f'provider = "{provider}"',
        f"queries = {baseline.queries}",
        f"mrr = {baseline.mrr!r}",
        "",
        "[hit_rate]",
    ]
    for k in sorted(baseline.hit_rate):
        lines.append(f"{k} = {baseline.hit_rate[k]!r}")
    return "\n".join(lines) + "\n"


def write_baseline(path: Path, baseline: Baseline) -> None:
    """Persist the baseline with round-trip validation (REQ-044, fail-safe)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _serialize_baseline(baseline)
    path.write_text(text, encoding="utf-8")
    try:
        reloaded = load_baseline(path)
    except (SuiteValidationError, tomllib.TOMLDecodeError, OSError) as exc:
        raise SuiteWriteError(str(path)) from exc
    if reloaded is None or reloaded.hit_rate != baseline.hit_rate or reloaded.mrr != baseline.mrr:
        raise SuiteWriteError(str(path))
