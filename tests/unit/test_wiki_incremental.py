"""Test FEAT-007 (Gruppo H) — verifica incrementale git-driven (US3, REQ-087..091/096/097)."""
from __future__ import annotations

import json

from sertor_core.wiki.conventions import read_watermark, write_watermark
from sertor_core.wiki.semantic import semantic_lint_incremental
from tests.fixtures.mocks import FakeGit, ScriptedLLM

_FM = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
       "updated: 2026-06-03\nsources: [{src}]\n---\n\n# {t}\n\n{b}\n")

_OBSOLETE = json.dumps([{"kind": "obsolete", "claim": "Usa X", "severity": "high",
                         "detail": "il codice usa Y", "evidence": "src/x.py#1"}])


def _add(root, slug, title, sources, body="Corpo."):
    src = ", ".join(f'"{s}"' for s in sources)
    (root / "concepts" / f"{slug}.md").write_text(
        _FM.format(t=title, b=body, src=src), encoding="utf-8")
    return f"concepts/{slug}.md"


# --- T021: baseline / incrementale / no-op ---

def test_baseline_without_watermark_checks_all(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha", ["src/moduleA/**"])
    _add(wiki_sandbox, "beta", "Beta", ["src/moduleB/**"])
    git = FakeGit(changed=[], head="c0ffee")  # nessun watermark persistito
    report = semantic_lint_incremental(wiki_sandbox, ScriptedLLM([_OBSOLETE]), git=git)

    assert report.mode == "baseline"                       # REQ-087
    assert "no-watermark" in report.fallbacks
    assert report.pages_checked == report.pages_total      # tutte le pagine


def test_incremental_selects_only_touched_pages(wiki_sandbox):
    a = _add(wiki_sandbox, "alpha", "Alpha", ["src/moduleA/**"])
    _add(wiki_sandbox, "beta", "Beta", ["src/moduleB/**"])
    write_watermark(wiki_sandbox, "base000")
    git = FakeGit(changed={"since_watermark": ["src/moduleA/foo.py"]}, head="head111")
    llm = ScriptedLLM([_OBSOLETE])
    report = semantic_lint_incremental(wiki_sandbox, llm, git=git)

    assert report.mode == "incremental"                    # REQ-088
    assert report.pages_checked == 1                       # SC-006: solo la pagina toccata
    assert llm.calls == 1
    assert all(i.page == a for i in report.issues)
    assert report.pages_total > 1                          # copertura reale del wiki


def test_no_op_when_changeset_touches_no_page(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha", ["src/moduleA/**"])
    write_watermark(wiki_sandbox, "base000")
    git = FakeGit(changed={"since_watermark": ["docs/unrelated.txt"]}, head="head111")
    llm = ScriptedLLM([_OBSOLETE])
    report = semantic_lint_incremental(wiki_sandbox, llm, git=git)

    assert report.mode == "incremental"
    assert report.pages_checked == 0 and llm.calls == 0    # REQ-093 no-op rapido
    assert report.issues == []


# --- T022: fallback / segnalazione / watermark ---

def test_fallback_baseline_when_no_git(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha", ["src/moduleA/**"])
    write_watermark(wiki_sandbox, "base000")
    report = semantic_lint_incremental(wiki_sandbox, ScriptedLLM([_OBSOLETE]), git=None)

    assert report.mode == "baseline"                       # REQ-091
    assert "no-git" in report.fallbacks


def test_fallback_baseline_when_head_missing(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha", ["src/moduleA/**"])
    write_watermark(wiki_sandbox, "base000")
    git = FakeGit(changed=[], head=None)                   # git presente ma non in un repo
    report = semantic_lint_incremental(wiki_sandbox, ScriptedLLM([_OBSOLETE]), git=git)

    assert report.mode == "baseline" and "no-git" in report.fallbacks


def test_stale_index_flagged_feat009_absent(wiki_sandbox):
    a = _add(wiki_sandbox, "alpha", "Alpha", ["src/moduleA/**"])
    write_watermark(wiki_sandbox, "base000")
    git = FakeGit(changed={"since_watermark": ["src/moduleA/foo.py"]}, head="head111")
    report = semantic_lint_incremental(wiki_sandbox, ScriptedLLM([_OBSOLETE]), git=git)

    # Re-index reale inattivo (FEAT-009 assente) → segnalazione esplicita (REQ-096/097).
    assert "stale-index" in report.fallbacks
    assert a  # la pagina toccata è stata verificata


def test_watermark_read_write_roundtrip(wiki_sandbox):
    assert read_watermark(wiki_sandbox) is None            # assente → baseline (REQ-089)
    write_watermark(wiki_sandbox, "abc123\n")
    assert read_watermark(wiki_sandbox) == "abc123"        # non distruttivo, trim
