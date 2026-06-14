"""Textual shell for the observability live panel (feature 022): the thin rendering layer.

Imports Textual at module top — so this module is imported ONLY behind the `[tui]` extra (the
launcher `composition.run_observability_panel` does it lazily and raises an actionable `ConfigError`
when the extra is missing). All the *what to show* logic lives in `live.py` (pure, testable without
a terminal); here we only draw the snapshot and refresh it on a timer. Read-only.
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static

from sertor_core.observability.live import live_snapshot, render_snapshot
from sertor_core.services.observability_report import ObservabilityReports


class ObservabilityApp(App):
    """Live observability panel: draws the current snapshot and refreshes on a timer (read-only)."""

    TITLE = "Sertor — observability"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, reports: ObservabilityReports, refresh_s: float = 2.0):
        super().__init__()
        self._reports = reports
        self._refresh_s = refresh_s
        self.last_text = ""  # last rendered text (testable seam, independent of Textual internals)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="body")
        yield Footer()

    def on_mount(self) -> None:
        self._update()
        self.set_interval(self._refresh_s, self._update)

    def _update(self) -> None:
        self.last_text = render_snapshot(live_snapshot(self._reports))
        self.query_one("#body", Static).update(self.last_text)
