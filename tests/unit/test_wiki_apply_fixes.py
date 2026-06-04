"""Test FEAT-007 (Gruppo H) — applicazione assistita su working tree (US4-scrittura)."""
from __future__ import annotations

from sertor_core.wiki.conventions import read_provenance
from sertor_core.wiki.semantic import (
    FixAction,
    FixOutcome,
    FixProposal,
    SemanticIssue,
    SemanticIssueKind,
    apply_fixes,
)

_CLAIM = "Usa Ollama come default."

_GEN = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
        "updated: 2026-06-03\nsources: []\nprovenance: generated\n---\n\n# {t}\n\n{b}\n")
_CUR = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
        "updated: 2026-06-03\nsources: []\n---\n\n# {t}\n\n{b}\n")  # niente provenance → curated


def _write(root, slug, title, fm, body):
    p = root / "concepts" / f"{slug}.md"
    p.write_text(fm.format(t=title, b=body), encoding="utf-8")
    return f"concepts/{slug}.md", p


def _rewrite_proposal(rel, claim=_CLAIM, proposed="Usa Azure come default."):
    issue = SemanticIssue(kind=SemanticIssueKind.OBSOLETE, page=rel, claim=claim,
                          detail="il codice usa Azure")
    return FixProposal(issue=issue, page=rel, action=FixAction.REWRITE_CLAIM,
                       proposed_text=proposed, rationale="aggiorna provider")


def test_rewrite_on_generated_is_surgical_and_stays_generated(wiki_sandbox):
    rel, p = _write(wiki_sandbox, "alpha", "Alpha", _GEN, f"Intro.\n\n{_CLAIM}\n\nCoda.")
    apps = apply_fixes([_rewrite_proposal(rel)], wiki_sandbox)

    assert apps[0].outcome == FixOutcome.APPLIED
    text = p.read_text(encoding="utf-8")
    assert "Usa Azure come default." in text                 # SC-007: claim aggiornata
    assert _CLAIM not in text
    assert "Intro." in text and "Coda." in text              # chirurgico: il resto resta
    assert read_provenance(text) == "generated"              # resta generated


def test_delete_on_generated_removes_file(wiki_sandbox):
    rel, p = _write(wiki_sandbox, "old", "Old", _GEN, "Pagina interamente obsoleta.")
    issue = SemanticIssue(kind=SemanticIssueKind.OBSOLETE, page=rel, claim="")
    prop = FixProposal(issue=issue, page=rel, action=FixAction.DELETE_PAGE, rationale="obsoleta")
    apps = apply_fixes([prop], wiki_sandbox)

    assert apps[0].outcome == FixOutcome.DELETED            # REQ-085
    assert not p.exists()


def test_curated_page_is_refused(wiki_sandbox):
    rel, p = _write(wiki_sandbox, "manual", "Manual", _CUR, f"Intro.\n\n{_CLAIM}\n")
    before = p.read_text(encoding="utf-8")
    apps = apply_fixes([_rewrite_proposal(rel)], wiki_sandbox)

    assert apps[0].outcome == FixOutcome.REFUSED_CURATED    # REQ-080
    assert p.read_text(encoding="utf-8") == before          # nessuna scrittura


def test_skipped_when_claim_absent(wiki_sandbox):
    rel, p = _write(wiki_sandbox, "alpha", "Alpha", _GEN, "Tutt'altro contenuto.")
    before = p.read_text(encoding="utf-8")
    apps = apply_fixes([_rewrite_proposal(rel, claim="frase inesistente")], wiki_sandbox)

    assert apps[0].outcome == FixOutcome.SKIPPED_NO_MATCH   # non è un errore
    assert p.read_text(encoding="utf-8") == before


def test_dry_run_does_not_touch_filesystem(wiki_sandbox):
    rel, p = _write(wiki_sandbox, "alpha", "Alpha", _GEN, f"Intro.\n\n{_CLAIM}\n")
    before = p.read_text(encoding="utf-8")
    apps = apply_fixes([_rewrite_proposal(rel)], wiki_sandbox, dry_run=True)

    assert apps[0].outcome == FixOutcome.APPLIED            # esito calcolato
    assert p.read_text(encoding="utf-8") == before          # ma nessuna scrittura (Principio VI)
