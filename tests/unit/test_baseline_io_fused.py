"""Test baseline_io for the `[fused_baseline]` section (069, TASK-A05): round-trip + preserve-both.

stdlib only; a tmp baseline file. Verifies the fused section round-trips, that an absent
file/section returns None, and that the fused write preserves the IR `[baseline]` (preserve-both).
"""
from __future__ import annotations

import pytest

from sertor_core.domain.errors import SuiteWriteError
from sertor_core.services.eval import baseline_io
from sertor_core.services.eval.baseline_io import (
    load_baseline,
    load_fused_baseline,
    now_iso_utc,
    write_baseline,
    write_fused_baseline,
)
from sertor_core.services.eval.models import Baseline, FusedBaseline, SurfaceBaseline


def _fused() -> FusedBaseline:
    return FusedBaseline(
        surfaces=(
            SurfaceBaseline("search_code", {1: 0.5, 3: 0.75, 5: 0.88}, 0.64),
            SurfaceBaseline("search_docs", {1: 0.62, 3: 0.88, 5: 0.88}, 0.73),
            SurfaceBaseline("search_combined", {1: 0.55, 3: 0.82, 5: 0.91}, 0.69),
        ),
        fusion_coverage=0.5,
        queries=22,
        provider="hash",
        recorded_at=now_iso_utc(),
    )


def _ir() -> Baseline:
    return Baseline(
        hit_rate={1: 0.55, 3: 0.82, 5: 0.91, 10: 1.0},
        mrr=0.83,
        queries=11,
        provider="hash",
        recorded_at=now_iso_utc(),
    )


def test_round_trip(tmp_path):
    path = tmp_path / "baseline.toml"
    fused = _fused()
    write_fused_baseline(path, fused)
    loaded = load_fused_baseline(path)
    assert loaded is not None
    assert loaded.surfaces == fused.surfaces
    assert loaded.fusion_coverage == 0.5
    assert loaded.queries == 22
    assert loaded.recorded_at == fused.recorded_at


def test_absent_file_is_none(tmp_path):
    assert load_fused_baseline(tmp_path / "nope.toml") is None


def test_ir_only_file_returns_none_for_fused(tmp_path):
    path = tmp_path / "baseline.toml"
    write_baseline(path, _ir())
    assert load_fused_baseline(path) is None
    assert load_baseline(path) is not None  # IR still loads


def test_write_fused_preserves_ir_baseline(tmp_path):
    path = tmp_path / "baseline.toml"
    write_baseline(path, _ir())
    write_fused_baseline(path, _fused())
    ir = load_baseline(path)
    fused = load_fused_baseline(path)
    assert ir is not None and ir.mrr == 0.83  # IR untouched (preserve-both)
    assert fused is not None and fused.fusion_coverage == 0.5


def test_write_ir_preserves_fused_baseline(tmp_path):
    path = tmp_path / "baseline.toml"
    write_fused_baseline(path, _fused())
    write_baseline(path, _ir())  # recording the IR baseline must keep the fused one
    assert load_fused_baseline(path) is not None
    assert load_baseline(path).mrr == 0.83


def test_recorded_at_present(tmp_path):
    path = tmp_path / "baseline.toml"
    write_fused_baseline(path, _fused())
    loaded = load_fused_baseline(path)
    assert loaded.recorded_at and loaded.recorded_at.endswith("Z")


def test_round_trip_failure_raises(tmp_path, monkeypatch):
    path = tmp_path / "baseline.toml"

    def _none(_p):
        return None

    monkeypatch.setattr(baseline_io, "load_fused_baseline", _none)
    with pytest.raises(SuiteWriteError):
        write_fused_baseline(path, _fused())
