"""Coverage of a wiki recording: WHICH work items an entry declared itself about (E10-FEAT-062).

A recording used to be honoured for *existing*: `scan` zeroed the pending set as soon as today's log
partition appeared among the uncommitted changes. That made the gate answer "is there a recording?"
instead of "is this work recorded?" — so writing the entry, which the ritual prescribes, switched
the gate off for the rest of the day.

Coverage replaces presence. An entry carries the set of items it covers, derived when it is written,
and `scan` computes `pending = work_in_scope - coverage`.

**Identity is `(path, content)`, not `path` alone**, and that is what makes the date disappear from
the logic rather than merely move: an old coverage carries an old content identity, so it stops
matching by itself. Nothing has to decide which entries are "recent" — which in turn means nothing
has to parse entry headings, whose shape is host-configurable (`log_format`) and would have made
this capability silently wrong on any host that configures its own.

Format contract: `specs/124-copertura-changeset-scan/contracts/sertor-covers.1.md`.
"""
from __future__ import annotations

from collections.abc import Iterable

BLOCK_OPEN = "<!-- sertor-covers/1"
BLOCK_CLOSE = "-->"

#: Content identity of an item that is not on disk (a deletion is work, and must be coverable).
ABSENT = "-"

#: A covered item: `(project-relative POSIX path, content identity)`.
CoveredItem = tuple[str, str]


def serialize(items: Iterable[CoveredItem]) -> str:
    """Render the coverage block appended to a log entry (empty string if nothing is covered).

    Sorted on purpose: the block lands in a versioned file, so a stable order keeps two runs that
    covered the same thing from producing spurious differences.
    """
    ordered = sorted(set(items))
    if not ordered:
        return ""
    lines = [BLOCK_OPEN, *(f"{path}@{content_id}" for path, content_id in ordered), BLOCK_CLOSE]
    return "\n".join(lines)


def parse(text: str) -> set[CoveredItem]:
    """Every covered item declared anywhere in `text` (union across all blocks it contains).

    Union, not last-wins: a day's partition holds several entries and their coverages compose.

    Malformed lines are skipped rather than raising. This runs inside a Stop-time gate that must
    never trap a turn, and a half-written block should narrow coverage — more pending, not a crash.
    """
    covered: set[CoveredItem] = set()
    inside = False
    for raw in text.splitlines():
        line = raw.strip()
        if not inside:
            if line.startswith(BLOCK_OPEN):
                inside = True
            continue
        if line.startswith(BLOCK_CLOSE):
            inside = False
            continue
        path, sep, content_id = line.rpartition("@")
        # rpartition: the LAST `@` separates, so a path containing `@` stays valid.
        if sep and path and content_id:
            covered.add((path, content_id))
    return covered


def has_block(text: str) -> bool:
    """Whether `text` declares any coverage at all.

    Tells "this entry covers nothing" from "this entry predates coverage": only the second earns the
    declared compatibility rule (see `scan`, `legacy_coverage`).
    """
    return any(line.strip().startswith(BLOCK_OPEN) for line in text.splitlines())


def has_entry(text: str, log_format: str) -> bool:
    """Whether `text` holds at least one recording, per the **host's own** entry format.

    Needed only to tell "an entry written before coverage existed" from "no entry at all": an empty
    partition, or one touched by whitespace alone, is not a recording and must not earn the
    compatibility rule.

    The matcher is **derived from `log_format`**, never hardcoded. Assuming `## [` would be true for
    our journal and false for any host that configures its own — and it would fail *silently*: no
    error, just zero entries recognised. That is the same class of defect this feature closes, so it
    must not be reintroduced by the fix itself.

    Conservative when the format opens with a placeholder and offers no literal prefix to anchor on:
    no entry is claimed, so the compatibility rule stays off and the gate stays strict.
    """
    prefix = log_format.split("{", 1)[0].strip()
    if not prefix:
        return False
    return any(line.strip().startswith(prefix) for line in text.splitlines())


def covers(coverage: set[CoveredItem], path: str, content_id: str) -> bool:
    """Whether the item is covered **as it is now**.

    A path present with a *different* content identity is NOT covered: that is how an item recorded
    and then edited again comes back as pending, and how stale coverages expire on their own.
    """
    return (path, content_id) in coverage
