"""`index_wiki`: orchestrazione dell'indicizzazione a collezioni separate (FR-010, US5, D5).

Riusa il facade/indexer esistente di `sertor_core` (DRY, Principio III): l'embedding è una chiamata
all'adapter, non un giudizio LLM. La collezione del wiki è separata dalle sorgenti via
`collection_name((corpus, provider))`, così rigenerare il wiki non tocca la collezione delle
sorgenti. L'import del composition root è **lazy** (dentro la funzione): le altre operazioni del
nucleo restano senza dipendenze dal vector store (Principio I/II). No-op se `rag.enabled=false`.
"""
from __future__ import annotations

import logging
from dataclasses import replace

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.contracts import IndexResult
from sertor_core.wiki_tools.profile import WikiProfile


def index_wiki(profile: WikiProfile, *, indexer_factory=None) -> IndexResult:
    """Indicizza il wiki in una collezione separata; no-op se `rag.enabled` è falso.

    `indexer_factory` (per i test) sostituisce la costruzione dell'indexer: riceve i `Settings`
    e restituisce un oggetto con `.index(root, rebuild=...) -> report` (campi `collection`,
    `documents`). In produzione si usa `build_indexer` del composition root (import lazy).
    """
    rag = profile.rag or {}
    if not rag.get("enabled", False):
        result = IndexResult(collection=None, documents=0, regenerated=False)
        log_event(logging.INFO, "index", profile=profile.profile, action="noop-disabled")
        return result

    # Import lazy: solo questa operazione tocca il composition root / vector store.
    from sertor_core.config.settings import Settings

    settings = Settings.load()
    corpus = str(rag.get("corpus") or "wiki")
    settings = replace(settings, corpus=corpus)

    if indexer_factory is None:
        from sertor_core.composition import build_indexer

        indexer = build_indexer(settings)
    else:
        indexer = indexer_factory(settings)

    report = indexer.index(profile.root_path, rebuild=True)
    result = IndexResult(
        collection=report.collection,
        documents=report.documents,
        regenerated=True,
    )
    log_event(
        logging.INFO,
        "index",
        profile=profile.profile,
        collection=report.collection,
        documents=report.documents,
        regenerated=True,
    )
    return result
