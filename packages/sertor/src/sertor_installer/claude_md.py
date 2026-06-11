"""Blocco a marker nel `CLAUDE.md` (D4, contracts/claude-md-block.md).

Algoritmo idempotente e non-distruttivo: il blocco step-ritual è delimitato da marker su riga
propria; tutto ciò che sta **fuori** dai marker è dell'utente e resta byte-per-byte intatto. Tre
casi: assente → crea col solo blocco; presente senza marker → appendi; presente con marker → skip.
"""
from __future__ import annotations

from pathlib import Path

from sertor_installer.artifacts import Outcome

MARKER_START = "<!-- SERTOR:WIKI-RITUAL START -->"
MARKER_END = "<!-- SERTOR:WIKI-RITUAL END -->"


def _wrap(block_content: str) -> str:
    """Avvolge il contenuto del blocco fra i marker (marker su riga propria)."""
    return f"{MARKER_START}\n{block_content.rstrip()}\n{MARKER_END}\n"


def write_ritual_block(claude_md_path: Path, block_content: str) -> Outcome:
    """Scrive/non-tocca il blocco step-ritual nel `CLAUDE.md` (D4).

    Garanzia di non-distruttività: nei casi "presente", il contenuto fuori dai marker è preservato
    byte-per-byte (lettura con `read_text(encoding="utf-8")`, nessuna normalizzazione dei line
    ending; il file esistente non viene riscritto se i marker ci sono già).

    - assente → crea il file col solo blocco → `Outcome.BLOCK`;
    - presente, marker assenti → appendi il blocco in coda (riga vuota di separazione) → `BLOCK`;
    - presente, marker presenti → non toccare nulla → `Outcome.SKIPPED`.
    """
    block = _wrap(block_content)

    if not claude_md_path.exists():
        claude_md_path.write_text(block, encoding="utf-8")
        return Outcome.BLOCK

    existing = claude_md_path.read_text(encoding="utf-8")
    if MARKER_START in existing:
        return Outcome.SKIPPED

    # Append non-distruttivo: una riga vuota di separazione, poi il blocco. Il contenuto
    # preesistente resta byte-per-byte (concateniamo, non riscriviamo).
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    claude_md_path.write_text(existing + separator + block, encoding="utf-8")
    return Outcome.BLOCK
