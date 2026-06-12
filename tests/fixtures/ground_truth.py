"""Ground-truth del corpus sertor: coppie (query → file attesi) per la misura di qualità.

FR-023/026 (REQ-050/053): ≥10 coppie miste — query a simbolo esatto (`kind="symbol"`) e query
architetturali in linguaggio naturale (`kind="nl"`). I path sono relativi alla RADICE del
repository, in forma POSIX (host-agnostico: niente assunzioni di struttura — se il repo viene
riorganizzato basta aggiornare i path, le query restano valide). I consumatori che indicizzano
una sottocartella (es. i test, root=`src/sertor_core`) riconducono i path con `relative_to`.

Usato da: i 2 test strict di pertinenza (ex `xfail`) e la valutazione comparativa
baseline / ibrido / ibrido+rerank (REQ-051).
"""
from __future__ import annotations

# (query, [path attesi, repo-root relative POSIX], kind ∈ {"symbol", "nl"})
GROUND_TRUTH: list[tuple[str, list[str], str]] = [
    # --- simboli esatti (il caso debole della via solo-vettoriale) ---
    ("EmbeddingProvider", ["src/sertor_core/domain/ports.py"], "symbol"),
    ("IndexNotFoundError", ["src/sertor_core/domain/errors.py",
                            "src/sertor_core/engines/baseline.py"], "symbol"),
    ("collection_name", ["src/sertor_core/composition.py"], "symbol"),
    ("log_event", ["src/sertor_core/observability/logging.py"], "symbol"),
    ("ensure_index", ["src/sertor_core/engines/baseline.py",
                      "src/sertor_core/engines/hybrid.py"], "symbol"),
    ("ProviderMismatchError", ["src/sertor_core/domain/errors.py",
                               "src/sertor_core/services/retrieval.py"], "symbol"),
    # --- query architetturali in linguaggio naturale ---
    ("dove si scelgono gli adapter concreti e si cabla la configurazione",
     ["src/sertor_core/composition.py"], "nl"),
    ("rebuild atomico dell'indice da zero",
     ["src/sertor_core/services/indexing.py", "src/sertor_core/engines/baseline.py"], "nl"),
    ("fusione dei risultati multi-collezione della ricerca combinata",
     ["src/sertor_core/services/retrieval.py"], "nl"),
    ("redazione dei segreti nei log strutturati",
     ["src/sertor_core/observability/logging.py"], "nl"),
    ("chunking con dispatch per tipo di documento e linguaggio",
     ["src/sertor_core/services/chunking/dispatch.py"], "nl"),
]


def relative_to(prefix: str) -> list[tuple[str, list[str], str]]:
    """Ground-truth coi path ricondotti a una radice di indicizzazione diversa dal repo root.

    Es. `relative_to("src/sertor_core")` per i test che indicizzano solo il nucleo: i path
    diventano `domain/ports.py`, ...; le coppie i cui attesi cadono tutti fuori dal prefisso
    vengono scartate.
    """
    norm = prefix.rstrip("/") + "/"
    out: list[tuple[str, list[str], str]] = []
    for query, expected, kind in GROUND_TRUTH:
        rebased = [p[len(norm):] for p in expected if p.startswith(norm)]
        if rebased:
            out.append((query, rebased, kind))
    return out
