"""Test US2/US5 — record e ingest (REQ-010..013, 020..023)."""
from __future__ import annotations

from sertor_core.wiki.conventions import Brief, SourceBrief
from sertor_core.wiki.operations import ingest, record

T = "2026-06-03"


# ----------------------------------------------------------------- record (US2)
def test_record_creates_page_index_and_log(wiki_sandbox):
    res = record(wiki_sandbox, Brief("Scelta DB", "synthesis", "Scelto Postgres."), today=T)
    assert res.changed and res.log_appended
    page = wiki_sandbox / "syntheses" / "scelta-db.md"
    assert page.exists()                                   # pagina nel tema (REQ-010)
    index = (wiki_sandbox / "index.md").read_text(encoding="utf-8")
    assert "](syntheses/scelta-db.md)" in index            # link in indice (REQ-011)
    log = (wiki_sandbox / "log.md").read_text(encoding="utf-8")
    assert log.count("] record | Scelta DB") == 1         # esattamente una voce (REQ-012)


def test_record_rerun_is_noop(wiki_sandbox):
    record(wiki_sandbox, Brief("Scelta DB", "synthesis", "Scelto Postgres."), today=T)
    log_before = (wiki_sandbox / "log.md").read_text(encoding="utf-8")
    again = Brief("Scelta DB", "synthesis", "Scelto Postgres.")
    res = record(wiki_sandbox, again, today="2026-07-01")
    assert res.changed is False                            # no-op (REQ-013)
    # nessuna 2ª voce di log
    assert (wiki_sandbox / "log.md").read_text(encoding="utf-8") == log_before


# ----------------------------------------------------------------- ingest (US5)
def test_ingest_creates_source_and_propagates(wiki_sandbox):
    # pagina correlata esistente
    record(wiki_sandbox, Brief("Hybrid Search", "concept", "Concetto."), today=T)
    res = ingest(wiki_sandbox, SourceBrief(
        title="Paper Ibrido",
        summary="Il paper dimostra X.",
        reference="https://example.org/p",
        related=["concepts/hybrid-search"],
    ), today=T)
    assert res.changed
    src = wiki_sandbox / "sources" / "paper-ibrido.md"
    assert src.exists()
    assert "https://example.org/p" in src.read_text(encoding="utf-8")          # reference (REQ-020)
    related = (wiki_sandbox / "concepts" / "hybrid-search.md").read_text(encoding="utf-8")
    assert "[[paper-ibrido]]" in related                  # propagazione (REQ-021)


def test_ingest_marks_contradiction(wiki_sandbox):
    record(wiki_sandbox, Brief("Baseline", "concept", "La baseline fa Y."), today=T)
    ingest(wiki_sandbox, SourceBrief(
        title="Studio Contrario",
        summary="Contraddice Y.",
        reference="ref",
        contradicts=[("concepts/baseline", "Y non regge in caso Z")],
    ), today=T)
    page = (wiki_sandbox / "concepts" / "baseline.md").read_text(encoding="utf-8")
    assert "Contraddizione" in page and "Y non regge in caso Z" in page        # REQ-023
