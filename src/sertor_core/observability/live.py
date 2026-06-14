"""Live state model for the observability panel (feature 022): the pure, testable layer.

`live_snapshot` composes a current-state snapshot from the F2 reports (`ObservabilityReports`) —
WITHOUT any terminal/Textual dependency (Principio V): the *what to show* is verifiable offline,
while the *how to draw it* lives in the thin Textual shell (`tui.py`). Read-only: composes reports,
writes nothing (FR-004).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sertor_core.domain.entities import ObservedEvent
from sertor_core.services.observability_report import (
    CacheReport,
    CostReport,
    HealthReport,
    ObservabilityReports,
)


@dataclass(frozen=True)
class LiveSnapshot:
    """A read-only snapshot of the current observability state, drawn by the panel."""

    has_data: bool = False
    last_index: HealthReport = field(default_factory=HealthReport)
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    estimated_tokens_saved: int = 0
    total_tokens: int = 0
    tokens_by_provider: dict[str, int] = field(default_factory=dict)
    recent_events: list[ObservedEvent] = field(default_factory=list)
    errors: int = 0
    retries: int = 0
    low_confidence: int = 0


def live_snapshot(
    reports: ObservabilityReports,
    recent_limit: int = 20,
    since: float | None = None,
    until: float | None = None,
) -> LiveSnapshot:
    """Compose the current-state snapshot from the F2 reports (pure, read-only).

    `has_data` is False when no events are present (persistence off / empty store) → the panel shows
    an honest empty state, never a crash (FR-005).
    """
    cache = reports.cache_report(since, until)
    cost = reports.cost_report(since, until)
    health = reports.health_report(since, until)
    reliability = reports.reliability_report(since, until)
    recent = reports.recent_events(recent_limit, since, until)

    total_cache = cache.total_hits + cache.total_misses
    hit_rate = (cache.total_hits / total_cache) if total_cache else 0.0
    has_data = bool(recent) or total_cache > 0 or cost.total_tokens > 0 or health.last_index_ts

    return LiveSnapshot(
        has_data=bool(has_data),
        last_index=health,
        cache_hits=cache.total_hits,
        cache_misses=cache.total_misses,
        cache_hit_rate=hit_rate,
        estimated_tokens_saved=cache.estimated_tokens_saved,
        total_tokens=cost.total_tokens,
        tokens_by_provider=dict(cost.by_provider),
        recent_events=list(recent),
        errors=reliability.errors,
        retries=reliability.retries,
        low_confidence=reliability.low_confidence,
    )


def render_snapshot(s: LiveSnapshot) -> str:
    """Render a snapshot to plain text (pure, no terminal). The Textual shell draws this string."""
    if not s.has_data:
        return (
            "No observability data yet.\n"
            "Enable it with SERTOR_OBSERVABILITY=true and run an operation (index/search)."
        )
    li = s.last_index
    providers = ", ".join(f"{p}={n}" for p, n in sorted(s.tokens_by_provider.items())) or "-"
    lines = [
        f"Last index: {li.documents} docs · {li.chunks} chunks · dim {li.embedding_dim}",
        f"Cache: {s.cache_hits} hits / {s.cache_misses} misses "
        f"({s.cache_hit_rate:.0%}) · ~{s.estimated_tokens_saved} tokens saved",
        f"Tokens: {s.total_tokens} total · {providers}",
        f"Reliability: {s.errors} errors · {s.retries} retries · {s.low_confidence} low-confidence",
        "",
        "Recent events:",
    ]
    for e in reversed(s.recent_events[-10:]):
        lines.append(f"  {e.operation}: {e.fields}")
    return "\n".join(lines)


# --- browsable report views (feature 022 F4): pure renderers + time window --------------------

_WINDOW_ORDER = ("all", "7d", "24h")


def time_window(preset: str, now: float) -> tuple[float | None, float | None]:
    """Resolve a preset into a `(since, until)` window. `all` → unbounded. Pure (`now` injected)."""
    if preset == "7d":
        return (now - 7 * 86400, None)
    if preset == "24h":
        return (now - 86400, None)
    return (None, None)


def next_window(preset: str) -> str:
    """Cycle the time-range preset: all → 7d → 24h → all."""
    i = _WINDOW_ORDER.index(preset) if preset in _WINDOW_ORDER else 0
    return _WINDOW_ORDER[(i + 1) % len(_WINDOW_ORDER)]


def _humanize_age(seconds: float) -> str:
    if seconds < 60:
        return "<1m"
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds // 86400)}d"


def render_cache_report(r: CacheReport) -> str:
    """Render the cache report (hit/miss over time + savings) to text. Pure."""
    if not r.series and r.total_hits == 0 and r.total_misses == 0:
        return "Cache: no data in range."
    lines = [
        f"Cache: {r.total_hits} hits / {r.total_misses} misses "
        f"· ~{r.estimated_tokens_saved} tokens saved",
        "",
        "By bucket:",
    ]
    lines += [f"  {b.bucket}: {b.hits} hits / {b.misses} misses" for b in r.series]
    return "\n".join(lines)


def render_cost_report(r: CostReport) -> str:
    """Render the cost report (tokens per provider/bucket) to text. Pure (currency is FEAT-007)."""
    if not r.series and r.total_tokens == 0:
        return "Cost: no data in range."
    providers = ", ".join(f"{p}={n}" for p, n in sorted(r.by_provider.items())) or "-"
    lines = [f"Cost: {r.total_tokens} tokens · {providers}", "", "By bucket:"]
    lines += [f"  {b.bucket}: {b.tokens} tokens" for b in r.series]
    return "\n".join(lines)


def render_corpus_report(r: HealthReport, now: float) -> str:
    """Render corpus health + freshness (time since last index). Pure (`now` injected)."""
    if r.last_index_ts is None:
        return "Corpus: no index recorded in range."
    return (
        f"Corpus: {r.documents} docs · {r.chunks} chunks · dim {r.embedding_dim}\n"
        f"Freshness: last index {_humanize_age(now - r.last_index_ts)} ago"
    )
