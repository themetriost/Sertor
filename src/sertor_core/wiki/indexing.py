"""Indicizzazione del wiki nel RAG (Gruppo E, REQ-040..045).

Riusa il nucleo (FEAT-001/002): costruisce embedder+store dalla configurazione e delega a
`IndexingService(rebuild=True)` puntato sulla radice del wiki. Le pagine entrano nel corpus come
documenti `doc`/`markdown` paritari (DA-W1, nessun boost). Le proprietà di idempotenza (id = path
relativo), errore esplicito su store irraggiungibile e peso paritario sono **ereditate** dal nucleo.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from sertor_core.composition import build_embedder, build_store, collection_name
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import IndexReport
from sertor_core.observability.logging import log_event
from sertor_core.services.indexing import IndexingService
from sertor_core.wiki.conventions import NON_PAGE_DIRS

_MD_GLOBS = ("*.md", "*.markdown")


def _has_markdown(root: Path) -> bool:
    return any(next(root.rglob(g), None) is not None for g in _MD_GLOBS)


def index_wiki(wiki_root: Path | str, settings: Settings | None = None) -> IndexReport:
    """Indicizza (full rebuild) le pagine Markdown del wiki nel corpus RAG configurato.

    Radice vuota o senza Markdown → warning e indice immutato (REQ-045). Store irraggiungibile →
    l'errore del nucleo (`VectorStoreError`/`EmbeddingError`) si propaga senza corrompere l'indice
    esistente (REQ-043).
    """
    wiki_root = Path(wiki_root)
    settings = settings or Settings.load()

    if not wiki_root.exists() or not _has_markdown(wiki_root):
        log_event(logging.WARNING, "wiki_index", root=str(wiki_root), status="empty")
        return IndexReport(collection="", documents=0, chunks=0)

    embedder = build_embedder(settings)
    store = build_store(settings)
    collection = collection_name(settings, embedder)
    report = IndexingService(embedder, store, collection, settings).index(wiki_root, rebuild=True)
    log_event(logging.INFO, "wiki_index", root=str(wiki_root), collection=collection,
              documents=report.documents, chunks=report.chunks)
    return report


def index_wiki_generated(wiki_root: Path | str, settings: Settings | None = None) -> IndexReport:
    """Indicizza SOLO le pagine del wiki **generato** in una collezione **separata** (FR-010/011).

    Le aree di **input** (`manual_edited/`, `ingested_sources/`) e lo stato (`.sertor/`) sono
    escluse: non entrano nel corpus. La collezione è namespaced su `settings.wiki_collection`
    (corpus dedicato), distinta dalla collezione del codice — interrogabili insieme ma rigenerabili
    in modo indipendente (D-3/D-7). Riusa `IndexingService` (Principio III).
    """
    wiki_root = Path(wiki_root)
    settings = settings or Settings.load()
    # Corpus dedicato al wiki + esclusione delle aree di input/stato (oltre ai default).
    wiki_settings = replace(
        settings,
        corpus=settings.wiki_collection,
        exclude_patterns=tuple(settings.exclude_patterns) + NON_PAGE_DIRS,
    )

    if not wiki_root.exists() or not _has_markdown(wiki_root):
        log_event(logging.WARNING, "wiki_index_generated", root=str(wiki_root), status="empty")
        return IndexReport(collection="", documents=0, chunks=0)

    embedder = build_embedder(wiki_settings)
    store = build_store(wiki_settings)
    collection = collection_name(wiki_settings, embedder)
    service = IndexingService(embedder, store, collection, wiki_settings)
    report = service.index(wiki_root, rebuild=True)
    log_event(logging.INFO, "wiki_index_generated", root=str(wiki_root), collection=collection,
              documents=report.documents, chunks=report.chunks)
    return report
