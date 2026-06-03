"""Test FEAT-007 — lint del wiki: igiene, coperture, gate, contraddizioni (US1/US2/US5)."""
from __future__ import annotations

from sertor_core.wiki.maintenance import IssueKind, lint


def _kinds(report):
    return {i.kind for i in report.issues}


def _pages_of(report, kind):
    return {i.page for i in report.issues if i.kind == kind}


# --- US1: report di igiene e coperture -------------------------------------------------

def test_lint_detects_broken_link(wiki_with_issues):
    report = lint(wiki_with_issues)
    broken = [i for i in report.issues if i.kind == IssueKind.BROKEN_LINK]
    assert any(i.page == "concepts/alpha.md" and "ghost" in i.detail for i in broken)  # REQ-002


def test_lint_detects_orphans_with_index_log_exempt(wiki_with_issues):
    report = lint(wiki_with_issues)
    orphans = _pages_of(report, IssueKind.ORPHAN)
    assert "concepts/alpha.md" in orphans          # nessuno la referenzia
    assert "concepts/beta.md" not in orphans       # referenziata da alpha
    assert "index.md" not in orphans and "log.md" not in orphans   # esenti (REQ-003/DA-5)


def test_lint_detects_pages_missing_from_index(wiki_with_issues):
    report = lint(wiki_with_issues)
    missing = _pages_of(report, IssueKind.INDEX_MISSING)
    assert "concepts/alpha.md" in missing and "concepts/beta.md" in missing  # REQ-004


def test_lint_detects_marked_contradictions(wiki_with_issues):
    report = lint(wiki_with_issues)
    assert "concepts/contraddetta.md" in _pages_of(report, IssueKind.CONTRADICTION)  # REQ-020


def test_lint_reports_coverage_gaps(wiki_with_issues):
    report = lint(wiki_with_issues, expected=["syntheses/architettura.md"])
    gaps = _pages_of(report, IssueKind.COVERAGE_MISSING)
    assert "syntheses/architettura.md" in gaps                                      # REQ-064


def test_lint_is_read_only(wiki_with_issues):
    before = {p: p.stat().st_mtime_ns for p in wiki_with_issues.rglob("*.md")}
    lint(wiki_with_issues, expected=["syntheses/x.md"])
    after = {p: p.stat().st_mtime_ns for p in wiki_with_issues.rglob("*.md")}
    assert before == after                                                          # REQ-005


# --- US2: gate pass/fail ---------------------------------------------------------------

def test_gate_pass_on_healthy_wiki(wiki_sandbox):
    report = lint(wiki_sandbox)
    assert report.ok is True and not report.issues                                  # REQ-053


def test_gate_fail_on_wiki_with_issues(wiki_with_issues):
    assert lint(wiki_with_issues).ok is False                                       # REQ-053


def test_lint_is_idempotent(wiki_with_issues):
    first, second = lint(wiki_with_issues), lint(wiki_with_issues)
    assert _kinds(first) == _kinds(second)
    assert len(first.issues) == len(second.issues)                                  # REQ-040
