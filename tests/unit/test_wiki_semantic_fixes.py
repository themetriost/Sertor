"""Test FEAT-007 (Gruppo H) — proposte di correzione, solo su pagine generate (US4)."""
from __future__ import annotations

from sertor_core.wiki.conventions import PROVENANCE_GENERATED, mark_provenance
from sertor_core.wiki.semantic import (
    FixAction,
    SemanticIssue,
    SemanticIssueKind,
    SemanticReport,
    Severity,
    propose_fixes,
)
from tests.fixtures.mocks import ScriptedLLM

_FM = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
       "updated: 2026-06-03\nsources: []\n---\n\n# {t}\n\nCorpo.\n")


def _write(root, slug, title, generated):
    text = _FM.format(t=title)
    if generated:
        text = mark_provenance(text, PROVENANCE_GENERATED)
    (root / "concepts" / f"{slug}.md").write_text(text, encoding="utf-8")
    return f"concepts/{slug}.md"


def test_proposals_only_for_generated_pages(wiki_sandbox):
    gen = _write(wiki_sandbox, "gen", "Gen", generated=True)
    cur = _write(wiki_sandbox, "cur", "Cur", generated=False)
    report = SemanticReport(issues=[
        SemanticIssue(SemanticIssueKind.OBSOLETE, gen, claim="vecchia frase",
                      severity=Severity.HIGH, detail="il codice usa Azure"),
        SemanticIssue(SemanticIssueKind.OBSOLETE, gen, claim="", severity=Severity.CRITICAL,
                      detail="pagina interamente obsoleta"),
        SemanticIssue(SemanticIssueKind.OBSOLETE, cur, claim="x", severity=Severity.HIGH),
    ])
    before = {p: p.stat().st_mtime_ns for p in wiki_sandbox.rglob("*.md")}

    proposals = propose_fixes(report, wiki_sandbox, llm=ScriptedLLM(["Usa Azure come default."]))

    # Nessuna proposta per la pagina curata (REQ-080)
    assert all(p.page == gen for p in proposals)
    actions = {p.action for p in proposals}
    assert actions == {FixAction.REWRITE_CLAIM, FixAction.DELETE_PAGE}     # REQ-078/085
    rewrite = next(p for p in proposals if p.action == FixAction.REWRITE_CLAIM)
    assert rewrite.proposed_text == "Usa Azure come default."
    # Non scrive nulla (Principio VI)
    assert {p: p.stat().st_mtime_ns for p in wiki_sandbox.rglob("*.md")} == before
