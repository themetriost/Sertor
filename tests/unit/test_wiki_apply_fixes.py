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


def test_rewrite_preserves_line_endings(wiki_sandbox):
    """Regressione (bug da dogfood): la riscrittura non deve convertire i fine-riga del file."""
    rel = "concepts/crlf.md"
    p = wiki_sandbox / "concepts" / "crlf.md"
    # File con fine-riga CRLF scritto byte-per-byte (no traduzione).
    content = _GEN.format(t="Crlf", b=f"Intro.\n\n{_CLAIM}\n\nCoda.").replace("\n", "\r\n")
    p.write_bytes(content.encode("utf-8"))
    apply_fixes([_rewrite_proposal(rel)], wiki_sandbox)

    raw = p.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")  # resta CRLF ovunque
    assert b"Usa Azure come default." in raw                          # claim aggiornata
    assert b"Intro." in raw and b"Coda." in raw                       # chirurgico


def test_rewrite_keeps_lf_only_files_lf(wiki_sandbox):
    rel = "concepts/lf.md"
    p = wiki_sandbox / "concepts" / "lf.md"
    p.write_bytes(_GEN.format(t="Lf", b=f"Intro.\n\n{_CLAIM}\n").encode("utf-8"))  # solo LF
    apply_fixes([_rewrite_proposal(rel)], wiki_sandbox)

    assert b"\r\n" not in p.read_bytes()                              # niente LF→CRLF su Windows
