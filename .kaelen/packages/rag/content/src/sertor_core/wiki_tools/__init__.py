"""Host-agnostic deterministic wiki core (FEAT-003-D).

All *mechanical* operations of the LLM Wiki — profile config, structure, conventions,
pending-work scan, structural lint, enumeration, idempotent registries and
indexing orchestration — **without any LLM judgment or call** (SC-005).

Host-agnostic (Principio X): all host-specific details live in `WikiProfile`
(loaded from `wiki.config.toml`); no path/name/language/taxonomy is hard-coded in the body.
Depends only on `config/`, `domain/errors` and `observability/`; the sole hook to the vector
store (`indexing`) imports the facade/indexer **lazily**.
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
