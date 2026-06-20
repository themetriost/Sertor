"""Test baseline I/O (065, TASK-012): round-trip, absence → None, recorded_at present."""
from __future__ import annotations

import pytest

from sertor_core.domain.errors import SuiteValidationError
from sertor_core.services.eval import baseline_io
from sertor_core.services.eval.models import Baseline


def _baseline() -> Baseline:
    return Baseline(
        hit_rate={1: 0.55, 3: 0.82, 5: 0.91, 10: 1.0},
        mrr=0.83,
        queries=11,
        provider="ollama:nomic-embed-text",
        recorded_at=baseline_io.now_iso_utc(),
    )


def test_round_trip_identity(tmp_path):
    path = tmp_path / "baseline.toml"
    b = _baseline()
    baseline_io.write_baseline(path, b)
    loaded = baseline_io.load_baseline(path)
    assert loaded is not None
    assert loaded.hit_rate == b.hit_rate
    assert loaded.mrr == b.mrr
    assert loaded.queries == b.queries
    assert loaded.provider == b.provider


def test_absent_file_returns_none(tmp_path):
    assert baseline_io.load_baseline(tmp_path / "baseline.toml") is None


def test_recorded_at_is_iso_utc(tmp_path):
    path = tmp_path / "baseline.toml"
    baseline_io.write_baseline(path, _baseline())
    loaded = baseline_io.load_baseline(path)
    assert loaded is not None
    assert loaded.recorded_at.endswith("Z")
    assert "T" in loaded.recorded_at


def test_hit_rate_keys_are_ints_after_load(tmp_path):
    path = tmp_path / "baseline.toml"
    baseline_io.write_baseline(path, _baseline())
    loaded = baseline_io.load_baseline(path)
    assert loaded is not None
    assert all(isinstance(k, int) for k in loaded.hit_rate)


def test_malformed_baseline_raises(tmp_path):
    path = tmp_path / "baseline.toml"
    path.write_text('provider = "x"\n', encoding="utf-8")  # missing mrr/queries
    with pytest.raises(SuiteValidationError):
        baseline_io.load_baseline(path)
