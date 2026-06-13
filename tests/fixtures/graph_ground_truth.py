"""Structural ground-truth of the sertor corpus (FEAT-005, FR-023/FR-025).

REAL symbols from `src/sertor_core/` chosen for **stability of the caller set**
(fix analyze U1: no high-churn symbols like `log_event` for callers). Paths are
relative to the INDEXED ROOT (`src/sertor_core`), POSIX.

Metrics (fix U1): on the real corpus **recall** of expected items is measured (new legitimate
callers do not break the test); full **precision** is measured on the CLOSED mini-corpus
(`tests/fixtures/graph_corpus.py`), where the ground-truth is total.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SymbolTruth:
    name: str
    definition_path: str                      # expected path of the definition
    expected_callers: tuple[str, ...] = ()    # qualnames of expected callers (closed list)
    expected_docs: tuple[str, ...] = field(default=())  # docs that mention the symbol


GROUND_TRUTH: tuple[SymbolTruth, ...] = (
    SymbolTruth(
        "collection_name", "composition.py",
        expected_callers=("build_indexer", "build_facade", "build_engine",
                          "build_baseline_engine"),
    ),
    SymbolTruth(
        "discover", "services/ingestion.py",
        expected_callers=("IndexingService.index",),
    ),
    SymbolTruth(
        "chunk_document", "services/chunking/dispatch.py",
        expected_callers=("IndexingService.index",),
    ),
    SymbolTruth(
        "redact", "observability/logging.py",
        expected_callers=("log_event",),
        expected_docs=("observability/README.md",),
    ),
    SymbolTruth(
        "rrf", "engines/hybrid.py",
        expected_callers=("HybridEngine.retrieve",),
    ),
    SymbolTruth(
        "build_facade", "composition.py",
        expected_docs=("README.md",),
    ),
)
