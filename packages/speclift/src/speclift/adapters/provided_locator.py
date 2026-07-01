"""Adapter `EvidenceLocator` che consuma evidenza GIA' localizzata (agente + tool MCP di Sertor).

Alternativa a `SertorRagLocator` per gli host dove l'agente ha accesso diretto ai tool MCP di
navigazione (`search_code`/`find_symbol`/`who_calls`) ma NON alla CLI-vehicle `sertor-rag` (il caso
del dogfooding di Sertor su se stesso — vedi
`wiki/sources/input-other-agents/sertor-feedback-speclift-cli-to-mcp.md`). L'agente produce
`located.json` **prima** che `bundle` giri (marcia `speclift changeset` + i propri tool MCP); questo
adapter si limita a **rileggerlo** — nessuna ricerca propria, nessun subprocess, nessuna rete.

Le chiavi di lookup sono le STESSE query che `SertorRagLocator` avrebbe derivato
(`domain.query_keys.build_identifier_queries`): garantisce che i due adapter rispondano in modo
compatibile alla stessa regola di derivazione (G6), non due euristiche divergenti.

Degrado onesto: una chiave assente non è un errore, è un "non trovato" (`[]`) — stessa semantica del
locator CLI quando il RAG non ha hit. Il moat (verifica sul filesystem) resta l'unica garanzia forte.
"""

from __future__ import annotations

from speclift.config import DEFAULT_CONFIG, Config
from speclift.domain.models import Symbol, TestRef
from speclift.domain.query_keys import build_identifier_queries


class ProvidedEvidenceLocator:
    """Localizza simboli e test da una mappa pre-calcolata (agente/MCP), mai da un subprocess."""

    def __init__(self, payload: dict, *, config: Config = DEFAULT_CONFIG) -> None:
        self._symbols: dict[str, list[dict]] = payload.get("symbols", {})
        self._tests: dict[str, list[dict]] = payload.get("tests", {})
        self._config = config

    def locate_symbols(self, file_path: str, identifiers: list[str], snippet: str) -> list[Symbol]:
        queries = build_identifier_queries(identifiers, snippet, self._config.max_queries_per_symbol)
        symbols: dict[tuple[str, str], Symbol] = {}
        for query in queries:
            for raw in self._symbols.get(_key(file_path, query), []):
                sym = _symbol_from(raw)
                symbols.setdefault((sym.name, sym.path), sym)
        return list(symbols.values())

    def locate_tests(self, symbol: Symbol) -> list[TestRef]:
        tests: dict[str, TestRef] = {}
        for raw in self._tests.get(symbol.name, []):
            test = _test_from(raw)
            tests.setdefault(test.path, test)
        return list(tests.values())


def _key(file_path: str, query: str) -> str:
    """La chiave `located.json["symbols"]` per un file+query. Vedi contracts/evidence-locator-port.md."""
    return f"{file_path}::{query}"


def _symbol_from(raw: dict) -> Symbol:
    return Symbol(
        name=raw["name"],
        path=raw["path"],
        line=raw.get("line", 0),
        kind=raw.get("kind", ""),
        provenance=raw.get("provenance", ""),
    )


def _test_from(raw: dict) -> TestRef:
    return TestRef(
        name=raw["name"],
        path=raw["path"],
        covers_symbol=raw["covers_symbol"],
        line=raw.get("line", 0),
        provenance=raw.get("provenance", ""),
    )
