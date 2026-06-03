"""Ingestione repo-agnostica: scopre e legge codice + documentazione di un repo qualunque.

Senza conoscenza a priori della struttura (REQ-001): scoperta **ordinata** per path relativo
(determinismo, Principio VI), esclusione configurabile di artefatti/segreti (REQ-002), skip dei
file illeggibili con warning (REQ-003), id stabile = path relativo POSIX (REQ-004), tipo e
linguaggio rilevati dall'estensione (REQ-005).
"""
from __future__ import annotations

import logging
from fnmatch import fnmatch
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, Document
from sertor_core.domain.errors import IngestionError
from sertor_core.observability.logging import log_event

# Estensione -> linguaggio. I nomi dei linguaggi sono quelli attesi dal chunker (tree-sitter).
_EXT_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java",
    ".cs": "c_sharp",
    ".go": "go",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".php": "php",
    ".rb": "ruby",
    ".ps1": "powershell", ".psm1": "powershell",
    ".sh": "bash", ".bash": "bash",
    ".sql": "sql",
    ".md": "markdown", ".markdown": "markdown",
}
_DOC_EXTS = {".md", ".markdown"}


def _read_text(path: Path) -> str:
    """Legge un file come testo UTF-8, tollerando byte non decodificabili."""
    return path.read_text(encoding="utf-8", errors="ignore")


def _is_excluded(rel_parts: tuple[str, ...], patterns: tuple[str, ...]) -> bool:
    """True se un qualunque segmento del path relativo combacia con un pattern di esclusione."""
    for part in rel_parts:
        for pat in patterns:
            if part == pat or fnmatch(part, pat):
                return True
    return False


def _language_for(path: Path) -> str | None:
    return _EXT_LANG.get(path.suffix.lower())


def discover(root: Path | str, settings: Settings) -> list[Document]:
    """Scopre e legge i documenti indicizzabili sotto `root`.

    Solleva `IngestionError` se la radice non è una directory accessibile (Principio IV). I file
    illeggibili sono **saltati** con un warning (non sono un errore); i file con estensione non
    riconosciuta (binari/altri) sono ignorati silenziosamente (fuori corpus MVP).
    """
    root = Path(root)
    if not root.exists() or not root.is_dir():
        raise IngestionError("radice del repository non accessibile", path=str(root))

    documents: list[Document] = []
    skipped = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        rel_parts = tuple(rel.split("/"))
        if _is_excluded(rel_parts, settings.exclude_patterns):
            continue
        language = _language_for(path)
        if language is None:
            continue  # estensione non indicizzabile (binari, formati non-testo): fuori MVP (A-2)
        try:
            text = _read_text(path)
        except OSError as exc:
            skipped += 1
            log_event(logging.WARNING, "ingest_skip", path=rel, reason=type(exc).__name__)
            continue
        doc_type = DocType.DOC if path.suffix.lower() in _DOC_EXTS else DocType.CODE
        documents.append(Document(id=rel, text=text, doc_type=doc_type, language=language))

    log_event(
        logging.INFO, "ingest", root=str(root), documents=len(documents), skipped=skipped
    )
    return documents
