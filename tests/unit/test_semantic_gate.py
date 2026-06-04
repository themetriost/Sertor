"""Test FEAT-007 (Gruppo H) — gate pre-commit/pre-push del lint semantico (US5, REQ-092..095)."""
from __future__ import annotations

import json

from sertor_core.services.semantic_gate import GateStatus, run_semantic_gate
from tests.fixtures.mocks import FakeGit, ScriptedLLM

_FM = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
       "updated: 2026-06-03\nsources: [{src}]\n{prov}---\n\n# {t}\n\n{b}\n")


def _add(root, slug, title, sources, *, generated=False, body="Usa X come default."):
    src = ", ".join(f'"{s}"' for s in sources)
    prov = "provenance: generated\n" if generated else ""
    (root / "concepts" / f"{slug}.md").write_text(
        _FM.format(t=title, b=body, src=src, prov=prov), encoding="utf-8")
    return f"concepts/{slug}.md"


def _detection(severity):
    return json.dumps([{"kind": "obsolete", "claim": "Usa X come default.", "severity": severity,
                        "detail": "il codice usa Azure", "evidence": "src/a/x.py#1"}])


def _incremental_git():
    return FakeGit(changed={"since_watermark": ["src/a/foo.py"]}, head="head111")


def _watermark(root):
    from sertor_core.wiki.conventions import write_watermark
    write_watermark(root, "base000")


def test_blocked_above_threshold(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha", ["src/a/**"])          # curated → non auto-fixabile
    _watermark(wiki_sandbox)
    outcome = run_semantic_gate(wiki_sandbox, ScriptedLLM([_detection("high")]),
                                git=_incremental_git())
    assert outcome.status == GateStatus.BLOCKED                # REQ-094
    assert not outcome.override


def test_warning_below_threshold(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha", ["src/a/**"])
    _watermark(wiki_sandbox)
    outcome = run_semantic_gate(wiki_sandbox, ScriptedLLM([_detection("low")]),
                                git=_incremental_git())
    assert outcome.status == GateStatus.WARNING                # sotto soglia: non blocca


def test_pass_when_changeset_irrelevant(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha", ["src/a/**"])
    _watermark(wiki_sandbox)
    git = FakeGit(changed={"since_watermark": ["docs/other.txt"]}, head="head111")
    outcome = run_semantic_gate(wiki_sandbox, ScriptedLLM([_detection("high")]), git=git)
    assert outcome.status == GateStatus.PASS                   # REQ-093 no-op


def test_override_forces_pass_and_records(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha", ["src/a/**"])
    _watermark(wiki_sandbox)
    outcome = run_semantic_gate(wiki_sandbox, ScriptedLLM([_detection("high")]),
                                git=_incremental_git(), override=True, override_reason="hotfix")
    assert outcome.status == GateStatus.PASS                   # SC-008: override fa procedere
    assert outcome.override and outcome.override_record        # REQ-095: registrato
    assert "hotfix" in outcome.override_record


def test_apply_resolves_and_passes(wiki_sandbox):
    p = wiki_sandbox / "concepts" / "gen.md"
    _add(wiki_sandbox, "gen", "Gen", ["src/a/**"], generated=True)
    _watermark(wiki_sandbox)
    before = p.read_text(encoding="utf-8")
    # ScriptedLLM: 1ª risposta = rilevazione; 2ª = frase riscritta (propose_fixes su generated).
    llm = ScriptedLLM([_detection("high"), "Usa Azure come default."])
    outcome = run_semantic_gate(wiki_sandbox, llm, git=_incremental_git(), apply=True)
    assert outcome.status == GateStatus.PASS                   # issue risolta dall'auto-fix
    assert any(a.outcome.value == "applied" for a in outcome.applied)
    assert p.read_text(encoding="utf-8") != before             # con --apply ha scritto


def test_default_proposes_without_writing_and_blocks(wiki_sandbox):
    p = wiki_sandbox / "concepts" / "gen.md"
    _add(wiki_sandbox, "gen", "Gen", ["src/a/**"], generated=True)
    _watermark(wiki_sandbox)
    before = p.read_text(encoding="utf-8")
    llm = ScriptedLLM([_detection("high"), "Usa Azure come default."])
    outcome = run_semantic_gate(wiki_sandbox, llm, git=_incremental_git())  # apply=False (default)
    assert outcome.status == GateStatus.BLOCKED                # senza scrittura, issue resta aperta
    assert p.read_text(encoding="utf-8") == before             # default sicuro: NON scrive
