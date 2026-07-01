"""Adapter `EvidenceLocator` via il **vehicle** Sertor RAG (`sertor-rag search --json`).

**Mai** `import sertor_core` (Constitution III + regola di progetto): si parla solo alla CLI. La CLI
espone `search` (semantica, su `code`/`doc`); la navigazione `find_symbol`/`who_calls` è solo MCP e non
disponibile qui → si usa `search` per la **localizzazione** (proporre file/simboli candidati), mentre la
**verifica** delle àncore resta deterministica sul filesystem (vedi `anchor_fs`). Multi-search con cap
(`MAX_QUERIES_PER_SYMBOL`) contro il rischio cross-layer (research R3).

Fail-loud (Constitution XI): runner che fallisce, output non-JSON, o indice mancante → `RagUnavailableError`.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from speclift.config import DEFAULT_CONFIG, Config
from speclift.domain.errors import RagUnavailableError
from speclift.domain.models import Symbol, TestRef
from speclift.domain.query_keys import build_identifier_queries

Runner = Callable[[list[str]], str]

#: Risultati per query (k contenuto: la localizzazione non ha bisogno di molti hit).
_SEARCH_K = 5


class SertorRagLocator:
    """Localizza simboli e test interrogando il RAG via subprocess della sua CLI."""

    def __init__(
        self,
        repo_path: str | Path = ".",
        *,
        config: Config = DEFAULT_CONFIG,
        runner: Runner | None = None,
    ) -> None:
        self._config = config
        self._runner = runner or _subprocess_runner(config.sertor_rag_vehicle, str(repo_path))

    def locate_symbols(
        self, file_path: str, identifiers: list[str], snippet: str
    ) -> list[Symbol]:
        queries = self._build_queries(identifiers, snippet)
        symbols: dict[tuple[str, str], Symbol] = {}
        for query in queries:
            for hit in self._search(query):
                key = (query, hit["path"])
                symbols.setdefault(
                    key,
                    Symbol(
                        name=query,
                        path=hit["path"],
                        line=0,  # la CLI search non fornisce la riga; l'àncora usa l'hunk
                        provenance=str(hit.get("chunk_id", "")),
                    ),
                )
        return list(symbols.values())

    def locate_tests(self, symbol: Symbol) -> list[TestRef]:
        tests: dict[str, TestRef] = {}
        for hit in self._search(symbol.name):
            path = hit["path"]
            if not _is_test_path(path) or path in tests:
                continue
            tests[path] = TestRef(
                name=Path(path).stem,
                path=path,
                covers_symbol=symbol.name,
                provenance=str(hit.get("chunk_id", "")),
            )
        return list(tests.values())

    def _build_queries(self, identifiers: list[str], snippet: str) -> list[str]:
        return build_identifier_queries(identifiers, snippet, self._config.max_queries_per_symbol)

    def _search(self, query: str) -> list[dict]:
        args = ["search", query, "--type", "code", "--json", "-k", str(_SEARCH_K)]
        try:
            out = self._runner(args)
        except Exception as exc:  # noqa: BLE001 — qualunque fallimento del vehicle è fail-loud
            raise RagUnavailableError(f"Sertor RAG non raggiungibile: {exc}") from exc
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            raise RagUnavailableError(
                f"output RAG non-JSON (indice mancante o errore?): {out[:160]}"
            ) from exc
        if not isinstance(data, list):
            raise RagUnavailableError("output RAG inatteso: atteso un array JSON")
        return data


def _is_test_path(path: str) -> bool:
    name = Path(path).name
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or "/tests/" in f"/{path.replace(chr(92), '/')}/"
    )


def _subprocess_runner(vehicle: tuple[str, ...], repo_path: str) -> Runner:
    def run(args: list[str]) -> str:
        proc = subprocess.run(  # noqa: S603 — vehicle fisso, niente shell
            [*vehicle, *args],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_path,
        )
        if proc.returncode != 0:
            raise RagUnavailableError(
                f"`sertor-rag {args[0]}` exit {proc.returncode}: {proc.stderr.strip()[:200]}"
            )
        return proc.stdout

    return run
