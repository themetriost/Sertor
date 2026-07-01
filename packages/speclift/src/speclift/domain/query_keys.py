"""Derivazione delle query/chiavi di localizzazione da un hunk (G6) — pura, senza I/O.

Condivisa da entrambi gli adapter `EvidenceLocator` (`SertorRagLocator` via CLI,
`ProvidedEvidenceLocator` via evidenza fornita dall'agente/MCP): la stessa regola deve produrre le
stesse chiavi in entrambi i mondi, altrimenti un locator alternativo non potrebbe rispondere alle
query che l'altro avrebbe fatto.
"""

from __future__ import annotations


def build_identifier_queries(identifiers: list[str], snippet: str, max_queries: int) -> list[str]:
    """Identificatori candidati, deduplicati e limitati a `max_queries`.

    (G6) Fallback alla prima riga dello snippet SOLO se è un singolo identificatore valido:
    altrimenti una riga intera (docstring, import, statement) diventerebbe un "simbolo" spurio.
    """
    queries: list[str] = list(dict.fromkeys(i for i in identifiers if i))
    if not queries:
        first = next((ln.strip() for ln in snippet.splitlines() if ln.strip()), "")
        if first.isidentifier():
            queries.append(first)
    return queries[:max_queries]
