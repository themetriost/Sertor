"""Repo-agnostic ingestion: discovers and reads code + documentation from any repository.

Without prior knowledge of the structure (REQ-001): **ordered** discovery by relative path
(determinism, Principio VI), configurable exclusion of artifacts/secrets (REQ-002), skip of
unreadable files with a warning (REQ-003), stable id = POSIX relative path (REQ-004), type and
language detected from extension (REQ-005).
"""
from __future__ import annotations

import logging
from fnmatch import fnmatch
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, Document
from sertor_core.domain.errors import IngestionError
from sertor_core.observability.logging import log_event

# Extension -> language. Language names match those expected by the chunker (tree-sitter).
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
    """Reads a file as UTF-8 text, tolerating non-decodable bytes."""
    return path.read_text(encoding="utf-8", errors="ignore")


def _is_excluded(rel_parts: tuple[str, ...], patterns: tuple[str, ...]) -> bool:
    """True if any segment of the relative path matches an exclusion pattern."""
    for part in rel_parts:
        for pat in patterns:
            if part == pat or fnmatch(part, pat):
                return True
    return False


def _language_for(path: Path) -> str | None:
    return _EXT_LANG.get(path.suffix.lower())


def discover(root: Path | str, settings: Settings) -> list[Document]:
    """Discovers and reads indexable documents under `root`.

    Raises `IngestionError` if the root is not an accessible directory (Principio IV). Unreadable
    files are **skipped** with a warning (not an error); files with unrecognised extensions
    (binaries/other) are silently ignored (out of MVP corpus).
    """
    root = Path(root)
    if not root.exists() or not root.is_dir():
        raise IngestionError("repository root not accessible", path=str(root))

    documents: list[Document] = []
    skipped = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        rel_parts = tuple(rel.split("/"))
        if _is_excluded(rel_parts, settings.exclude_patterns):
            continue
        language = _language_for(path)
        if language is None:
            continue  # non-indexable extension (binaries, non-text formats): out of MVP (A-2)
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
