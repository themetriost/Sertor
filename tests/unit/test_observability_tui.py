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


def test_app_smoke_renders_snapshot():
    # FR-001/002: the Textual app mounts headless and shows the snapshot. Skip without the extra.
    pytest.importorskip("textual")
    from sertor_core.observability.tui import ObservabilityApp
    from sertor_core.services.observability_report import ObservabilityReports
    from tests.fixtures.mocks import InMemoryObservabilityStore

    store = InMemoryObservabilityStore()
    store.record_event(1_700_000_000.0, "index", {"documents": 3, "chunks": 42, "embedding_dim": 8})
    app = ObservabilityApp(ObservabilityReports(store), refresh_s=100)

    async def _run():
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "42 chunks" in app.last_text

    asyncio.run(_run())


def test_app_smoke_empty_state():
    pytest.importorskip("textual")
    from sertor_core.observability.tui import ObservabilityApp
    from sertor_core.services.observability_report import ObservabilityReports
    from tests.fixtures.mocks import InMemoryObservabilityStore

    app = ObservabilityApp(ObservabilityReports(InMemoryObservabilityStore()), refresh_s=100)

    async def _run():
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "No observability data" in app.last_text  # FR-005

    asyncio.run(_run())
