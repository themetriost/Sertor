"""Textual shell for the observability panel (features 022/023): the thin rendering layer.

Imports Textual at module top — so this module is imported ONLY behind the `[tui]` extra (the
launcher `composition.run_observability_panel` does it lazily and raises an actionable `ConfigError`
when the extra is missing). All the *what to show* logic lives in `live.py` (pure, testable without
a terminal); here we only draw the snapshot/reports and refresh on a timer. Read-only.

The panel is tabbed: **Live** (current state, 022) + **Cache/Cost/Corpus** (browsable reports, 023)
+ **RAG** (demonstrability, 064), with `t` to cycle the time range (all → 7d → 24h) and `r` to
refresh on demand; the sub-title carries the last-update clock.
"""
from __future__ import annotations

import time

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from sertor_core.observability.live import (
    live_snapshot,
    next_window,
    render_cache_report,
    render_corpus_report,
    render_cost_report,
    render_rag_report,
    render_snapshot,
    time_window,
)
from sertor_core.services.observability_report import ObservabilityReports


class ObservabilityApp(App):
    """Observability panel: live state + browsable reports, refreshed on a timer (read-only)."""

    TITLE = "Sertor — observability"
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("t", "cycle_window", "Time range"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, reports: ObservabilityReports, refresh_s: float = 2.0):
        super().__init__()
        self._reports = reports
        self._refresh_s = refresh_s
        self._window = "all"
        # Last rendered texts per tab (testable seam, independent of Textual internals).
        self.rendered: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        # markup=False: our renderers emit plain text; event details (e.g. `results_preview=[...]`,
        # `provider=azure:...`) contain `[`/`:` that Textual would otherwise parse as Rich markup.
        with TabbedContent():
            with TabPane("Live", id="tab-live"):
                yield Static(id="live", markup=False)
            with TabPane("Cache", id="tab-cache"):
                yield Static(id="cache", markup=False)
            with TabPane("Cost", id="tab-cost"):
                yield Static(id="cost", markup=False)
            with TabPane("Corpus", id="tab-corpus"):
                yield Static(id="corpus", markup=False)
            with TabPane("RAG", id="tab-rag"):
                yield Static(id="rag", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._update()
        self.set_interval(self._refresh_s, self._update)

    def _update(self) -> None:
        now = time.time()
        since, until = time_window(self._window, now)
        clock = time.strftime("%H:%M:%S", time.localtime(now))
        self.sub_title = f"range: {self._window} · updated {clock}"
        snap = live_snapshot(self._reports, since=since, until=until)
        self.rendered = {
            "live": render_snapshot(snap),
            "cache": render_cache_report(self._reports.cache_report(since, until)),
            "cost": render_cost_report(self._reports.cost_report(since, until)),
            "corpus": render_corpus_report(self._reports.health_report(since, until), now),
            "rag": render_rag_report(snap.recent_events),
        }
        for key, text in self.rendered.items():
            self.query_one(f"#{key}", Static).update(text)

    def action_refresh(self) -> None:
        self._update()

    def action_cycle_window(self) -> None:
        self._window = next_window(self._window)
        self._update()
