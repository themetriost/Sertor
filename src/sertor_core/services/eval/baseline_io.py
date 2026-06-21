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
from sertor_core.services.eval.models import Baseline, FusedBaseline, SurfaceBaseline


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
    """Persist the baseline with round-trip validation (REQ-044, fail-safe).

    Preserves an existing `[fused_baseline]` section (069, preserve-both): re-appends it after the
    IR top-level scalars + `[hit_rate]` so recording the IR baseline never drops the fused one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_fused = load_fused_baseline(path) if path.exists() else None
    text = _serialize_baseline(baseline)
    if existing_fused is not None:
        text = text + "\n" + _serialize_fused_baseline(existing_fused)
    path.write_text(text, encoding="utf-8")
    try:
        reloaded = load_baseline(path)
    except (SuiteValidationError, tomllib.TOMLDecodeError, OSError) as exc:
        raise SuiteWriteError(str(path)) from exc
    if reloaded is None or reloaded.hit_rate != baseline.hit_rate or reloaded.mrr != baseline.mrr:
        raise SuiteWriteError(str(path))


def load_fused_baseline(path: Path) -> FusedBaseline | None:
    """Load the `[fused_baseline]` section of `path`, or `None` when absent (069, REQ-040).

    File absent → `None` (no recorded reference yet; the gate passes with `no-baseline`). File
    present but without a `[fused_baseline]` section → `None` (the file may carry only the IR
    `[baseline]`; additivity, not an error). A present-but-malformed `[fused_baseline]` IS an error
    (`SuiteValidationError`): a curated, versioned file (contract artifacts-toml.md §2).
    """
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise SuiteValidationError(-1, f"malformed baseline TOML: {exc}") from exc
    raw = data.get("fused_baseline")
    if not isinstance(raw, dict):
        return None
    try:
        fusion_coverage = float(raw["fusion_coverage"])
        queries = int(raw["queries"])
        provider = str(raw["provider"])
        recorded_at = str(raw.get("recorded_at", ""))
        raw_surfaces = raw.get("surface", [])
        if not isinstance(raw_surfaces, list):
            raise SuiteValidationError(-1, "`fused_baseline.surface` must be an array of tables")
        surfaces: list[SurfaceBaseline] = []
        for s in raw_surfaces:
            raw_hit = s.get("hit_rate", {})
            if not isinstance(raw_hit, dict):
                raise SuiteValidationError(-1, "`fused_baseline.surface.hit_rate` must be a table")
            surfaces.append(
                SurfaceBaseline(
                    surface=str(s["surface"]),
                    hit_rate={int(k): float(v) for k, v in raw_hit.items()},
                    mrr=float(s["mrr"]),
                )
            )
    except (KeyError, ValueError, TypeError) as exc:
        raise SuiteValidationError(-1, f"malformed fused_baseline: {exc}") from exc
    return FusedBaseline(
        surfaces=tuple(surfaces),
        fusion_coverage=fusion_coverage,
        queries=queries,
        provider=provider,
        recorded_at=recorded_at,
    )


def _load_ir_if_present(path: Path) -> Baseline | None:
    """Load the IR `[baseline]` (top-level scalars) only if the file actually carries it (069).

    A fused-only file (`[fused_baseline]` without top-level IR scalars) must NOT make this fail:
    return `None`. Used by `write_fused_baseline` to preserve the IR baseline without assuming it
    exists.
    """
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise SuiteValidationError(-1, f"malformed baseline TOML: {exc}") from exc
    if "mrr" not in data:
        return None  # no top-level IR baseline (e.g. a fused-only file)
    return load_baseline(path)


def _serialize_fused_baseline(baseline: FusedBaseline) -> str:
    """Serialize the `[fused_baseline]` section to TOML (scalars + `[[…surface]]` array tables)."""
    provider = baseline.provider.replace("\\", "\\\\").replace('"', '\\"')
    lines = [
        "[fused_baseline]",
        f'recorded_at = "{baseline.recorded_at}"',
        f'provider = "{provider}"',
        f"queries = {baseline.queries}",
        f"fusion_coverage = {baseline.fusion_coverage!r}",
    ]
    for s in baseline.surfaces:
        surface = s.surface.replace("\\", "\\\\").replace('"', '\\"')
        lines.append("")
        lines.append("[[fused_baseline.surface]]")
        lines.append(f'surface = "{surface}"')
        lines.append(f"mrr = {s.mrr!r}")
        lines.append("[fused_baseline.surface.hit_rate]")
        for k in sorted(s.hit_rate):
            lines.append(f"{k} = {s.hit_rate[k]!r}")
    return "\n".join(lines) + "\n"


def write_fused_baseline(path: Path, baseline: FusedBaseline) -> None:
    """Persist the `[fused_baseline]` section with round-trip validation (069, preserve-both).

    Preserves the IR `[baseline]` (top-level scalars + `[hit_rate]`): reads the existing IR
    baseline, re-serializes it, then appends the new `[fused_baseline]` section (replacing a prior).
    Written ONLY on `eval run --fused --record-baseline` (controlled by the CLI). Round-trip
    validated (`SuiteWriteError` if it does not parse back) — fail-safe, no ambiguous file left.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    ir = _load_ir_if_present(path)
    parts: list[str] = []
    if ir is not None:
        parts.append(_serialize_baseline(ir).rstrip("\n"))
    parts.append(_serialize_fused_baseline(baseline).rstrip("\n"))
    text = "\n\n".join(parts) + "\n"
    path.write_text(text, encoding="utf-8")
    try:
        reloaded = load_fused_baseline(path)
        # Preserve-both: re-read the IR baseline ONLY when one was present (a fused-only file has no
        # top-level IR scalars → `load_baseline` would legitimately fail to find `mrr`).
        reloaded_ir = load_baseline(path) if ir is not None else None
    except (SuiteValidationError, tomllib.TOMLDecodeError, OSError) as exc:
        raise SuiteWriteError(str(path)) from exc
    if reloaded is None or reloaded.surfaces != baseline.surfaces:
        raise SuiteWriteError(str(path))
    # Preserve-both: the IR baseline (if any) must survive the fused write untouched.
    if ir is not None and (reloaded_ir is None or reloaded_ir.mrr != ir.mrr):
        raise SuiteWriteError(str(path))
