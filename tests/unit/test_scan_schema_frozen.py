"""The scan contract identifier is FROZEN while fail-open consumers exist (E10-FEAT-045, T006).

**Why this guard is written before the feature, not after.** The installed hooks compare the schema
for EQUALITY and return early when it does not match — a deliberate, correct fail-open (a Stop-time
gate must never trap a turn). But that same policy means bumping the identifier would NOT break the
wiki gate: it would make it **disappear** on every host that updated the library but not the assets.
No error, no breadcrumb, no `pending` — just sessions that always close. Absence looks like success.

Two design choices here are the point of the guard, not incidental:

1. **Neither side hardcodes the value.** The expected string is read from the library constant and
   compared against the literal parsed out of each consumer. A test that spelled `"wiki.scan/1"` out
   would itself be a copy of a fact with nothing reconciling it — the very thing Principle XIV
   forbids, reintroduced inside the guard meant to enforce it.
2. **Consumers are DISCOVERED, not listed.** The guard scans every hook file for the comparison, so
   a consumer added later is covered without anyone remembering to update this file. Listing them
   would give the guard a perimeter narrower than the rule it protects — the failure mode that let a
   defect through twice already (see `wiki/concepts/esito-sull-host-vs-forma-dell-asset.md`).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from sertor_core.wiki_tools.contracts import SCAN_SCHEMA, ScanResult

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories holding hook consumers: the shipped assets (source of truth) and the dogfood copies.
_HOOK_DIRS = (
    _REPO_ROOT / "packages" / "sertor" / "src" / "sertor_installer" / "assets" / "claude" / "hooks",
    _REPO_ROOT / ".claude" / "hooks",
)

# `scan.get("schema") != "<literal>"` — the fail-open comparison we must stay compatible with.
_COMPARISON = re.compile(
    r"""\.get\(\s*["']schema["']\s*\)\s*!=\s*["']([^"']+)["']""",
)

# A file is in scope when it INVOKES the `scan` subcommand. Sibling hooks consume other wiki
# contracts (`distill-floor` reads `wiki.distill_audit/1`) and comparing them here would make the
# guard fail on a correct file — a perimeter must match its rule in BOTH directions, not just
# be wide enough.
_INVOKES_SCAN = re.compile(r"""["']sertor-wiki-tools["']\s*,\s*["']scan["']""")


def _comparison_sites() -> list[tuple[Path, str]]:
    """Every (file, compared literal) pair, restricted to files that actually run `scan`."""
    sites: list[tuple[Path, str]] = []
    for directory in _HOOK_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            try:
                body = path.read_text(encoding="utf-8")
            except OSError:  # pragma: no cover - unreadable file is not this guard's business
                continue
            if not _INVOKES_SCAN.search(body):
                continue
            sites.extend((path, literal) for literal in _COMPARISON.findall(body))
    return sites


def test_the_guard_actually_finds_consumers():
    """A guard that matches nothing passes vacuously — which is the failure it exists to prevent.

    If the hooks are refactored so the comparison no longer looks like this, THIS test must fail
    loudly so the perimeter gets re-established, rather than going quietly green and blind.
    """
    sites = _comparison_sites()
    assert len(sites) >= 2, (
        "no schema comparison found in the hook consumers — either the hooks changed shape or the "
        "assets moved. Re-establish the perimeter of this guard instead of deleting it: a green "
        "guard that inspects nothing is worse than no guard."
    )


@pytest.mark.parametrize("path,literal", _comparison_sites(), ids=lambda v: getattr(v, "name", v))
def test_consumers_compare_the_schema_the_library_emits(path: Path, literal: str):
    """Every consumer's expected identifier must equal the one `scan` actually emits."""
    assert literal == SCAN_SCHEMA, (
        f"{path} expects schema {literal!r} but the library emits {SCAN_SCHEMA!r}.\n"
        "This is NOT cosmetic: these consumers fail OPEN on a mismatch, so the wiki gate would "
        "not fail — it would silently stop existing on every host running the older asset.\n"
        "While fail-open consumers exist, the contract evolves by ADDITION only: add fields, "
        "leave the identifier alone."
    )


def test_scan_result_default_matches_the_constant():
    """The dataclass default and the exported constant are one fact, not two."""
    result = ScanResult(pending=0, anchor=None, dirs_scanned=[], message="")
    assert result.schema == SCAN_SCHEMA


def test_additive_fields_do_not_disturb_the_original_contract():
    """A consumer that knows only the original four keys keeps working (FR-012, FR-013)."""
    payload = ScanResult(pending=0, anchor=None, dirs_scanned=[], message="ok").to_dict()
    for key in ("pending", "anchor", "dirs_scanned", "message", "schema"):
        assert key in payload
    # `anchor` stays an instant-or-null in every mode, never a commit id (FR-013).
    assert payload["anchor"] is None
