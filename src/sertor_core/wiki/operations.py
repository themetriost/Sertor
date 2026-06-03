"""Operazioni del wiki LLM-free: record (documentare) e ingest (fonti esterne).

Idempotenti per struttura (REQ-013/050): si scrive una pagina solo se il contenuto cambia, si
aggiorna l'indice solo per pagine nuove/cambiate, si appende **una** voce di log per operazione che
modifica. `index.md`/`log.md` non vengono mai riscritti retroattivamente.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import (
    Brief,
    SourceBrief,
    WikiArea,
    area_dir,
    log_entry,
    page_relpath,
    parse_created,
    render_page,
    slugify,
    today_str,
)
from sertor_core.wiki.structure import WikiOpResult

_UPDATED_RE = re.compile(r"^updated:.*$", re.MULTILINE)


def _without_updated(text: str) -> str:
    """Testo senza la riga `updated:` (per confrontare il contenuto ignorando il timestamp)."""
    return _UPDATED_RE.sub("updated:", text)


def _one_line(text: str) -> str:
    for line in text.strip().splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def _write_page_if_changed(path: Path, brief: Brief, today: str) -> bool:
    """Scrive la pagina solo se cambia; preserva `created` e aggiorna `updated` solo a modifica."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        created = parse_created(existing) or today
        candidate = render_page(brief, created=created, updated=today)
        if _without_updated(existing) == _without_updated(candidate):
            return False  # nessuna modifica reale: no-op (idempotenza)
        path.write_text(candidate, encoding="utf-8")
        return True
    path.write_text(render_page(brief, created=today, updated=today), encoding="utf-8")
    return True


def _add_index_entry(root: Path, relpath: str, title: str, summary: str) -> None:
    index = root / "index.md"
    if not index.exists():
        return
    content = index.read_text(encoding="utf-8")
    if f"]({relpath})" in content:
        return  # già presente: idempotente
    line = f"- [{title}]({relpath}) — {summary}\n"
    index.write_text(content.rstrip("\n") + "\n" + line, encoding="utf-8")


def _append_log(root: Path, operation: str, title: str, today: str) -> None:
    log = root / "log.md"
    entry = log_entry(today, operation, title)
    base = log.read_text(encoding="utf-8") if log.exists() else ""
    log.write_text(base.rstrip("\n") + "\n\n" + entry, encoding="utf-8")


def record(root: Path | str, brief: Brief, today: str | None = None) -> WikiOpResult:
    """Crea/aggiorna la pagina del tema, aggiorna l'indice, appende una voce log (REQ-010-013)."""
    root = Path(root)
    today = today or today_str()
    relpath = page_relpath(brief.kind, brief.title)
    changed = _write_page_if_changed(root / relpath, brief, today)
    if changed:
        _add_index_entry(root, relpath, brief.title, _one_line(brief.body))
        _append_log(root, "record", brief.title, today)
    log_event(logging.INFO, "wiki_record", page=relpath, changed=changed)
    return WikiOpResult("record", page_path=relpath, changed=changed, log_appended=changed)


def ingest(root: Path | str, source: SourceBrief, today: str | None = None) -> WikiOpResult:
    """Incorpora una fonte in `sources/`, propaga i ref, marca le contraddizioni (REQ-020-023)."""
    root = Path(root)
    today = today or today_str()
    relpath = f"{area_dir(WikiArea.SOURCE)}/{slugify(source.title)}.md"
    brief = Brief(
        title=source.title,
        kind=WikiArea.SOURCE,
        body=source.summary,
        tags=["source"],
        sources=[source.reference] if source.reference else [],
    )
    changed = _write_page_if_changed(root / relpath, brief, today)

    source_link = f"[[{slugify(source.title)}]]"
    # Propaga il riferimento alla fonte nelle pagine correlate esistenti (REQ-021).
    for rel in source.related:
        page = root / (rel if rel.endswith(".md") else f"{rel}.md")
        if page.exists():
            text = page.read_text(encoding="utf-8")
            note = f"\n> Fonte correlata: {source_link}\n"
            if source_link not in text:
                page.write_text(text.rstrip("\n") + "\n" + note, encoding="utf-8")
    # Marca esplicitamente le contraddizioni segnalate (REQ-023).
    for rel, reason in source.contradicts:
        page = root / (rel if rel.endswith(".md") else f"{rel}.md")
        if page.exists():
            text = page.read_text(encoding="utf-8")
            mark = f"\n> ⚠️ Contraddizione (fonte {source_link}): {reason}\n"
            if reason not in text:
                page.write_text(text.rstrip("\n") + "\n" + mark, encoding="utf-8")

    if changed:
        _add_index_entry(root, relpath, source.title, _one_line(source.summary))
        _append_log(root, "ingest", source.title, today)
    log_event(logging.INFO, "wiki_ingest", page=relpath, changed=changed)
    return WikiOpResult("ingest", page_path=relpath, changed=changed, log_appended=changed)
