"""Nucleo wiki deterministico host-agnostico (FEAT-003-D).

Tutte le operazioni *meccaniche* del LLM Wiki — config-profilo, struttura, convenzioni,
scan del lavoro pendente, lint strutturale, enumerazione, registri idempotenti e
orchestrazione dell'indicizzazione — **senza alcun giudizio o chiamata LLM** (SC-005).

Host-agnostico (Principio X): tutta la specificità dell'ospite vive in `WikiProfile`
(caricato da `wiki.config.toml`); nessun path/nome/lingua/tassonomia è hard-coded nel corpo.
Dipende solo da `config/`, `domain/errors` e `observability/`; l'unico aggancio al vector
store (`indexing`) importa il facade/indexer in modo **lazy**.
"""
from __future__ import annotations

from sertor_core.wiki_tools.collect import collect
from sertor_core.wiki_tools.contracts import (
    CollectResult,
    ErrorResult,
    IndexResult,
    LintResult,
    ScanResult,
    StructureResult,
)
from sertor_core.wiki_tools.lint import lint
from sertor_core.wiki_tools.profile import TaxonomyEntry, WikiProfile, load_profile
from sertor_core.wiki_tools.registry import append_log, upsert_index
from sertor_core.wiki_tools.scan import scan
from sertor_core.wiki_tools.structure import init_structure, validate

__all__ = [
    "WikiProfile",
    "TaxonomyEntry",
    "load_profile",
    "scan",
    "init_structure",
    "validate",
    "lint",
    "collect",
    "append_log",
    "upsert_index",
    "ScanResult",
    "LintResult",
    "CollectResult",
    "StructureResult",
    "IndexResult",
    "ErrorResult",
]
