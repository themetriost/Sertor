"""Ground-truth strutturale del corpus sertor (FEAT-005, FR-023/FR-025).

Simboli REALI di `src/sertor_core/` scelti per **stabilità dell'insieme dei chiamanti**
(fix analyze U1: niente simboli ad alto churn come `log_event` per i caller). I path sono
relativi alla RADICE INDICIZZATA (`src/sertor_core`), POSIX.

Metriche (fix U1): sul corpus reale si misura il **recall** degli attesi (nuovi chiamanti
legittimi non rompono il test); la **precisione** piena si misura sul mini-corpus CHIUSO
(`tests/fixtures/graph_corpus.py`), dove il ground-truth è totale.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SymbolTruth:
    name: str
    definition_path: str                      # path atteso della definizione
    expected_callers: tuple[str, ...] = ()    # qualname dei chiamanti attesi (lista chiusa)
    expected_docs: tuple[str, ...] = field(default=())  # doc che lo menzionano


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
