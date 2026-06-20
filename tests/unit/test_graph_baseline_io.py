"""Test graph baseline IO (066, TASK-F05): round-trip, absence → None, recorded_at present."""
from __future__ import annotations

from sertor_core.services.eval.graph_baseline_io import (
    load_graph_baseline,
    now_iso_utc,
    write_graph_baseline,
)
from sertor_core.services.eval.models import GraphBaseline


def _baseline() -> GraphBaseline:
    return GraphBaseline(
        mean_f1=0.83,
        mean_recall=0.90,
        mean_precision=0.79,
        cases=6,
        recorded_at=now_iso_utc(),
    )


def test_round_trip_identical(tmp_path):
    path = tmp_path / "graph_baseline.toml"
    b = _baseline()
    write_graph_baseline(path, b)
    loaded = load_graph_baseline(path)
    assert loaded == b


def test_absent_file_is_none(tmp_path):
    assert load_graph_baseline(tmp_path / "missing.toml") is None


def test_recorded_at_iso_format(tmp_path):
    path = tmp_path / "graph_baseline.toml"
    write_graph_baseline(path, _baseline())
    loaded = load_graph_baseline(path)
    assert loaded is not None
    assert loaded.recorded_at.endswith("Z") and "T" in loaded.recorded_at


def test_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "graph_baseline.toml"
    write_graph_baseline(path, _baseline())
    assert path.exists()
