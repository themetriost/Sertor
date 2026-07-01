"""Adapter `AnchorResolver` — verifica deterministica delle àncore sul **filesystem** (il moat).

RAG propone, il filesystem dispone: la verifica non usa giudizio LLM né esecuzione di codice (research
R6/R7). Controlla, in ordine:
  (a) il file dell'àncora esiste e l'intervallo di righe è entro i limiti del file;
  (b) se l'àncora cita un **simbolo**, il suo nome compare nel file (presenza statica);
  (c) se l'àncora cita un **test**, il file di test esiste e **referenzia** il simbolo (uso statico —
      "tocca" nel senso MVP, niente esecuzione del test).
Verdetto idempotente: un'àncora già `verified` ri-verificata resta `verified`.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from speclift.domain.models import Anchor


class FilesystemAnchorResolver:
    """Verifica un'àncora leggendo i file del repo (read-only)."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        self._root = Path(repo_path)

    def verify(self, anchor: Anchor) -> Anchor:
        verified = (
            self._file_and_lines_ok(anchor)
            and self._symbol_ok(anchor)
            and self._test_ok(anchor)
        )
        return replace(anchor, status="verified" if verified else "unverified")

    def _read(self, rel: str) -> list[str] | None:
        path = self._root / rel
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            return None

    def _file_and_lines_ok(self, anchor: Anchor) -> bool:
        lines = self._read(anchor.file)
        if lines is None:
            return False
        start, end = anchor.lines
        return 1 <= start <= end <= len(lines)

    def _symbol_ok(self, anchor: Anchor) -> bool:
        if anchor.symbol is None:
            return True
        lines = self._read(anchor.file)
        return lines is not None and any(anchor.symbol in ln for ln in lines)

    def _test_ok(self, anchor: Anchor) -> bool:
        if anchor.test is None:
            return True
        lines = self._read(anchor.test.path)
        if lines is None:
            return False
        return any(anchor.test.covers_symbol in ln for ln in lines)
