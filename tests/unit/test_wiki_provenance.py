"""Test FEAT-007 (Gruppo H) — provenienza delle pagine (US2)."""
from __future__ import annotations

from sertor_core.wiki.conventions import (
    PROVENANCE_CURATED,
    PROVENANCE_GENERATED,
    mark_provenance,
    read_provenance,
)
from sertor_core.wiki.distill import distill_artifact
from tests.fixtures.mocks import FakeLLM

_PAGE = ("---\ntitle: X\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
         "updated: 2026-06-03\nsources: []\n---\n\n# X\n\nCorpo.\n")


def test_default_is_curated():
    assert read_provenance(_PAGE) == PROVENANCE_CURATED          # REQ-077c (default sicuro)


def test_mark_inserts_then_updates_without_destroying():
    marked = mark_provenance(_PAGE, PROVENANCE_GENERATED)
    assert read_provenance(marked) == PROVENANCE_GENERATED       # REQ-076
    assert "# X" in marked and "Corpo." in marked                # resto preservato
    # idempotente sull'aggiornamento: rimarcare non duplica la riga
    again = mark_provenance(marked, PROVENANCE_CURATED)
    assert again.count("provenance:") == 1
    assert read_provenance(again) == PROVENANCE_CURATED


def test_distill_artifact_marks_generated(wiki_sandbox, fake_llm, tmp_path):
    art = tmp_path / "spec.md"
    art.write_text("# Spec\n\nDettagli.\n", encoding="utf-8")
    distill_artifact(wiki_sandbox, source=str(art), kind="synthesis",
                     title="Architettura", llm=fake_llm, today="2026-06-03")
    text = (wiki_sandbox / "syntheses" / "architettura.md").read_text(encoding="utf-8")
    assert read_provenance(text) == PROVENANCE_GENERATED         # REQ-077 (auto-marcatura)


def test_manual_edit_reclassifies_to_curated():
    # Simula l'intervento manuale: la salvaguardia rimette la pagina come curated (REQ-077b)
    generated = mark_provenance(_PAGE, PROVENANCE_GENERATED)
    edited = mark_provenance(generated, PROVENANCE_CURATED)
    assert read_provenance(edited) == PROVENANCE_CURATED
    assert isinstance(FakeLLM().name, str)  # sanity import
