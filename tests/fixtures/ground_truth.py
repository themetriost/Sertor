"""Ground-truth of the sertor corpus: (query → expected files) pairs for quality measurement.

FR-023/026 (REQ-050/053): ≥10 mixed pairs — exact-symbol queries (`kind="symbol"`) and
architectural natural-language queries (`kind="nl"`). Paths are relative to the repository ROOT,
in POSIX form (host-agnostic: no structural assumptions — if the repo is reorganised just update
the paths, the queries stay valid). Consumers that index a subfolder (e.g. the tests, root=
`src/sertor_core`) rebase the paths with `relative_to`.

Used by: the 2 strict relevance tests (ex `xfail`) and the comparative evaluation
baseline / hybrid / hybrid+rerank (REQ-051).

NB: the NL queries are in English, matching the (English) docstrings/comments of the source.
"""
from __future__ import annotations

# (query, [expected paths, repo-root relative POSIX], kind ∈ {"symbol", "nl"})
GROUND_TRUTH: list[tuple[str, list[str], str]] = [
    # --- exact symbols (the weak case of the vector-only path) ---
    ("EmbeddingProvider", ["src/sertor_core/domain/ports.py"], "symbol"),
    ("IndexNotFoundError", ["src/sertor_core/domain/errors.py",
                            "src/sertor_core/engines/baseline.py"], "symbol"),
    ("collection_name", ["src/sertor_core/composition.py"], "symbol"),
    ("log_event", ["src/sertor_core/observability/logging.py"], "symbol"),
    ("ensure_index", ["src/sertor_core/engines/baseline.py",
                      "src/sertor_core/engines/hybrid.py"], "symbol"),
    ("ProviderMismatchError", ["src/sertor_core/domain/errors.py",
                               "src/sertor_core/services/retrieval.py"], "symbol"),
    # --- architectural natural-language queries ---
    ("where concrete adapters are chosen and the configuration is wired",
     ["src/sertor_core/composition.py"], "nl"),
    ("atomic rebuild of the index from scratch",
     ["src/sertor_core/services/indexing.py", "src/sertor_core/engines/baseline.py"], "nl"),
    ("fusion of multi-collection results in combined search",
     ["src/sertor_core/services/retrieval.py"], "nl"),
    ("redaction of secrets in structured logs",
     ["src/sertor_core/observability/logging.py"], "nl"),
    ("chunking with dispatch by document type and language",
     ["src/sertor_core/services/chunking/dispatch.py"], "nl"),
]


def relative_to(prefix: str) -> list[tuple[str, list[str], str]]:
    """Ground-truth with paths rebased to an indexing root different from the repo root.

    E.g. `relative_to("src/sertor_core")` for tests that index only the core: paths become
    `domain/ports.py`, ...; pairs whose expected paths all fall outside the prefix are dropped.
    """
    norm = prefix.rstrip("/") + "/"
    out: list[tuple[str, list[str], str]] = []
    for query, expected, kind in GROUND_TRUTH:
        rebased = [p[len(norm):] for p in expected if p.startswith(norm)]
        if rebased:
            out.append((query, rebased, kind))
    return out
