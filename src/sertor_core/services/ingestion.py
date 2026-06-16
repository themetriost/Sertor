"""Repo-agnostic ingestion: discovers and reads code + documentation from any repository.

Without prior knowledge of the structure (REQ-001): **ordered** discovery by relative path
(determinism, Principio VI), configurable exclusion of artifacts/secrets (REQ-002), skip of
unreadable files with a warning (REQ-003), stable id = POSIX relative path (REQ-004), type and
language detected from extension (REQ-005).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
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


@dataclass(frozen=True)
class SourceFile:
    """A discovered indexable source file, before reading (046, T007).

    Separates the **stat** (cheap, all files) from the **read+parse** (only the changed candidates):
    `path` is the absolute path, `rel` the POSIX relative id, `language` the detected language,
    `mtime` the modification time. The incremental branch stats every file but reads only the ones
    that changed.
    """

    path: Path
    rel: str
    language: str
    mtime: float


def discover_files(root: Path | str, settings: Settings) -> list[SourceFile]:
    """Stat-only discovery of the indexable files under `root` (ordered, deterministic).

    Applies the same exclusion/extension filtering as `discover` but does NOT read any file: the
    cost of a no-op incremental run is ~just these `stat`s (NFR-4). Raises `IngestionError` if the
    root is not accessible (same contract as `discover`).
    """
    root = Path(root)
    if not root.exists() or not root.is_dir():
        raise IngestionError("repository root not accessible", path=str(root))

    files: list[SourceFile] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        rel_parts = tuple(rel.split("/"))
        if _is_excluded(rel_parts, settings.exclude_patterns):
            continue
        language = _language_for(path)
        if language is None:
            continue  # non-indexable extension (binaries, non-text formats): out of MVP (A-2)
        try:
            mtime = path.stat().st_mtime
        except OSError as exc:
            log_event(logging.WARNING, "ingest_skip", path=rel, reason=type(exc).__name__)
            continue
        files.append(SourceFile(path=path, rel=rel, language=language, mtime=mtime))
    return files


def read_source(source: SourceFile) -> Document | None:
    """Read+parse a single discovered file into a `Document`, or `None` if unreadable (warning).

    The read half of `discover_files`: used by the incremental branch only for the changed files.
    Unreadable files are skipped with a warning (not an error), same policy as `discover`.
    """
    try:
        text = _read_text(source.path)
    except OSError as exc:
        log_event(logging.WARNING, "ingest_skip", path=source.rel, reason=type(exc).__name__)
        return None
    doc_type = DocType.DOC if source.path.suffix.lower() in _DOC_EXTS else DocType.CODE
    return Document(id=source.rel, text=text, doc_type=doc_type, language=source.language)


def discover(root: Path | str, settings: Settings) -> list[Document]:
    """Discovers and reads indexable documents under `root`.

    Raises `IngestionError` if the root is not an accessible directory (Principio IV). Unreadable
    files are **skipped** with a warning (not an error); files with unrecognised extensions
    (binaries/other) are silently ignored (out of MVP corpus). Built on the stat/read split so the
    full path and the incremental path share the same discovery+filtering logic.
    """
    sources = discover_files(root, settings)
    documents: list[Document] = []
    skipped = 0
    for source in sources:
        doc = read_source(source)
        if doc is None:
            skipped += 1
            continue
        documents.append(doc)

    log_event(
        logging.INFO, "ingest", root=str(Path(root)), documents=len(documents), skipped=skipped
    )
    return documents
