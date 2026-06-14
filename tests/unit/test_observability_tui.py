"""Test 022 US2 — TUI panel: actionable error when the extra is missing + Textual smoke.

The missing-extra path is tested without Textual (monkeypatch); the app smoke runs headless via
Textual's `run_test()` (skipped if the extra is not installed).
"""
from __future__ import annotations

import asyncio

import pytest

from sertor_core import composition
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError


def test_missing_extra_raises_actionable_configerror(monkeypatch):
    # FR-006 / SC-004: extra absent → ConfigError with the install instruction, not an obscure one.
    def _boom():
        raise ImportError("no module named textual")

    monkeypatch.setattr(composition, "_load_observability_app", _boom)
    with pytest.raises(ConfigError) as ei:
        composition.run_observability_panel(Settings())
    assert "[tui]" in str(ei.value)


def _app_with_events(events):
    from sertor_core.observability.tui import ObservabilityApp
    from sertor_core.services.observability_report import ObservabilityReports
    from tests.fixtures.mocks import InMemoryObservabilityStore

    store = InMemoryObservabilityStore()
    for ts, op, fields in events:
        store.record_event(ts, op, fields)
    return ObservabilityApp(ObservabilityReports(store), refresh_s=100)


def test_app_smoke_renders_tabs():
    # FR-001/002/008: the tabbed app mounts headless; live + report tabs show content.
    pytest.importorskip("textual")
    app = _app_with_events([
        (1_700_000_000.0, "index", {"documents": 3, "chunks": 42, "embedding_dim": 8}),
        (1_700_000_000.0, "embeddings_cache", {"hits": 5, "misses": 1}),
    ])

    async def _run():
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "42 chunks" in app.rendered["live"]
            assert "5 hits" in app.rendered["cache"]
            assert "Corpus" in app.rendered["corpus"]

    asyncio.run(_run())


def test_app_smoke_empty_state():
    pytest.importorskip("textual")
    app = _app_with_events([])

    async def _run():
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "No observability data" in app.rendered["live"]   # FR-005
            assert "no data" in app.rendered["cache"]

    asyncio.run(_run())


def test_app_cycle_time_range():
    # FR-003/004: pressing `t` cycles the time range.
    pytest.importorskip("textual")
    app = _app_with_events([(1_700_000_000.0, "index", {"documents": 1, "chunks": 1})])

    async def _run():
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._window == "all"
            await pilot.press("t")
            await pilot.pause()
            assert app._window == "7d"

    asyncio.run(_run())
