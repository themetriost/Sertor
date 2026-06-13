"""Test US2 — engine selection in the composition root (FR-015/017/030/031).

The choice lives ONLY in `composition.py`: `build_engine` from `Settings.engine` (default hybrid),
invalid value → `ConfigError`; facade and indexer wired accordingly. Store on tmp_path
(local Chroma), local embedder constructed but never invoked: no network.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from sertor_core import composition
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.engines.hybrid import HybridEngine


def _settings(tmp_path, **overrides) -> Settings:
    base = Settings(index_dir=tmp_path / ".index", corpus="sel-test")
    return replace(base, **overrides) if overrides else base


def test_default_engine_is_hybrid(tmp_path):
    engine = composition.build_engine(_settings(tmp_path))
    assert isinstance(engine, HybridEngine)            # best engine is the default (FR-015)
    assert engine.name == "hybrid"


def test_baseline_remains_selectable(tmp_path):
    engine = composition.build_engine(_settings(tmp_path, engine="baseline"))
    assert isinstance(engine, BaselineEngine)          # FR-030/031


def test_invalid_engine_raises_config_error_with_valid_values(tmp_path):
    with pytest.raises(ConfigError) as exc:
        composition.build_engine(_settings(tmp_path, engine="bogus"))
    msg = str(exc.value)
    assert "bogus" in msg and "baseline" in msg and "hybrid" in msg  # valid values in the message


def test_facade_gets_strategy_only_when_hybrid(tmp_path):
    hybrid_facade = composition.build_facade(_settings(tmp_path))
    assert isinstance(hybrid_facade._retriever, HybridEngine)        # FR-017/018
    baseline_facade = composition.build_facade(_settings(tmp_path, engine="baseline"))
    assert baseline_facade._retriever is None          # current path unchanged


def test_facade_build_rejects_invalid_engine(tmp_path):
    with pytest.raises(ConfigError):
        composition.build_facade(_settings(tmp_path, engine="bogus"))


def test_indexer_gets_lexical_sink_only_when_hybrid(tmp_path):
    hybrid_indexer = composition.build_indexer(_settings(tmp_path))
    assert hybrid_indexer._lexical is not None         # sidecar written by re-index (REQ-034 hint)
    baseline_indexer = composition.build_indexer(_settings(tmp_path, engine="baseline"))
    assert baseline_indexer._lexical is None           # pipeline identical to today's (FR-031)


def test_build_baseline_engine_untouched(tmp_path):
    # The legacy factory remains unchanged regardless of Settings.engine (FR-030).
    engine = composition.build_baseline_engine(_settings(tmp_path))
    assert isinstance(engine, BaselineEngine)


def test_build_engine_is_exported_from_package():
    import sertor_core

    assert sertor_core.build_engine is composition.build_engine
