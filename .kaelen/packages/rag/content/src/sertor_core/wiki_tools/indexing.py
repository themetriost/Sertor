"""`index_wiki`: indexing orchestration into separate collections (FR-010, US5, D5).

Reuses the existing `sertor_core` facade/indexer (DRY, Principio III): embedding is an adapter
call, not an LLM judgment. The wiki collection is kept separate from source collections via
`collection_name((corpus, provider))`, so regenerating the wiki does not touch the source
collection. The composition root import is **lazy** (inside the function): the other core
operations remain free of vector-store dependencies (Principio I/II). No-op if `rag.enabled=false`.
"""
from __future__ import annotations

import logging
from dataclasses import replace

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.contracts import IndexResult
from sertor_core.wiki_tools.profile import WikiProfile


def index_wiki(profile: WikiProfile, *, indexer_factory=None) -> IndexResult:
    """Indexes the wiki into a separate collection; no-op if `rag.enabled` is false.

    `indexer_factory` (for tests) replaces the indexer construction: receives `Settings`
    and returns an object with `.index(root, rebuild=...) -> report` (fields `collection`,
    `documents`). In production, `build_indexer` from the composition root is used (lazy import).
    """
    rag = profile.rag or {}
    if not rag.get("enabled", False):
        result = IndexResult(collection=None, documents=0, regenerated=False)
        log_event(logging.INFO, "index", profile=profile.profile, action="noop-disabled")
        return result

    # Lazy import: only this operation touches the composition root / vector store.
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
