"""Compone i tre flussi resi all'agente: somiglianza (doc + codice) + struttura (118, FEAT-012).

**Non è un router.** Un router sceglie una via e scarta le altre; qui si fa **fan-out** e si
consegnano tutti i segnali separati, lasciando all'agente l'uso. La decisione su quale usare resta
sua — gli arriva solo più materiale su cui esercitarla, e in particolare gli arriva il segnale
strutturale *senza che debba sapere di doverlo chiedere*.

Il lavoro non ovvio di questo servizio è **tipizzare l'assenza**. Il grafo può non essere
consultabile per tre ragioni con **rimedi opposti** — non è stato costruito, manca la libreria di
l'artefatto è illeggibile — e l'adapter ne segnala due con lo *stesso tipo* di eccezione.
Collassarle in una lista vuota farebbe concludere all'agente «nessuno chiama questa funzione»
è rotto: il contratto gli fabbricherebbe un'affermazione falsa.
"""
from __future__ import annotations

import logging

from sertor_core.domain.agent_context import (
    GRAPH_ARTIFACT_UNUSABLE,
    GRAPH_NOT_BUILT,
    NAVIGATION_LIBRARY_MISSING,
    AgentContext,
    EntryPoint,
    GraphBranch,
    RelationBlock,
    SymbolContext,
)
from sertor_core.domain.entities import ContextBundle, RetrievalResult, SymbolHit
from sertor_core.domain.errors import ConfigError, GraphNotFoundError
from sertor_core.domain.ports import CodeGraph
from sertor_core.observability.logging import log_event
from sertor_core.services.graph_entry import resolve_entry_points


def _unavailable_reason(exc: Exception) -> str:
    """Traduce un guasto del grafo nella sua causa, distinguendo i casi che condividono il tipo.

    `ConfigError` copre sia l'extra di navigazione mancante sia l'artefatto illeggibile: il
    discriminante è `key == "graph"`, valorizzato solo nel primo caso. È una distinzione fragile —
    poggia su un attributo, non su un tipo — e per questo è **pinnata da un test**: se l'adapter
    smettesse di valorizzarla, la regressione fallirebbe invece di degradare in silenzio.
    """
    if isinstance(exc, GraphNotFoundError):
        return GRAPH_NOT_BUILT
    if isinstance(exc, ConfigError) and getattr(exc, "key", None) == "graph":
        return NAVIGATION_LIBRARY_MISSING
    return GRAPH_ARTIFACT_UNUSABLE


def _block(items: tuple[SymbolHit, ...], bundle: ContextBundle, section: str) -> RelationBlock:
    return RelationBlock.of(items, total=bundle.total_for(section))


def _docs_block(bundle: ContextBundle) -> RelationBlock:
    """I documenti che menzionano il simbolo: percorsi, non simboli, quindi resi come `SymbolHit`.

    Il grafo li restituisce come path nudi; qui prendono la stessa forma citabile degli altri hit,
    così l'agente cita allo stesso modo qualunque cosa abbia usato.
    """
    items = tuple(
        SymbolHit(path=p, line=None, kind="doc", qualname=p, ref=p) for p in bundle.docs
    )
    return RelationBlock.of(items, total=bundle.total_for("docs"))


class AgentContextService:
    """Orchestra facade + code-graph in un unico contesto etichettato."""

    def __init__(self, facade, graph: CodeGraph, settings) -> None:
        self._facade = facade
        self._graph = graph
        self._settings = settings

    def search(self, query: str, k: int | None = None) -> AgentContext:
        docs, code = self._facade.search_combined(query, k)
        branch = self._graph_branch(query)
        docs, code, branch = mark_corroboration(tuple(docs), tuple(code), branch)
        return AgentContext(docs=docs, code=code, graph=branch)

    # --- il ramo strutturale --------------------------------------------------------------------

    def _graph_branch(self, query: str) -> GraphBranch:
        try:
            qualnames = self._graph.list_symbols()
        except Exception as exc:  # noqa: BLE001 — ogni guasto diventa una causa DICHIARATA
            reason = _unavailable_reason(exc)
            self._log(query, (), reason)
            return GraphBranch.unavailable(reason)

        entries = tuple(
            resolve_entry_points(
                query,
                qualnames,
                max_symbols=self._settings.combined_graph_max_symbols,
                min_overlap=self._settings.combined_match_min_overlap,
            )
        )
        if not entries:
            # Nessun ingresso: il grafo NON viene interrogato. È ciò che rende il costo del fan-out
            # auto-correlato alla rilevanza — una domanda concettuale non paga quasi nulla.
            self._log(query, (), None)
            return GraphBranch.not_attempted()

        symbols: list[SymbolContext] = []
        for entry in entries:
            try:
                bundle = self._graph.get_context(entry.symbol)
            except Exception as exc:  # noqa: BLE001
                reason = _unavailable_reason(exc)
                symbols.append(_all_unavailable(entry, reason))
                continue
            symbols.append(
                SymbolContext(
                    qualname=entry.symbol,
                    definitions=_block(bundle.definitions, bundle, "definitions"),
                    callers=_block(bundle.callers, bundle, "callers"),
                    callees=_block(bundle.callees, bundle, "callees"),
                    docs=_docs_block(bundle),
                )
            )

        branch = GraphBranch(entry_points=entries, symbols=tuple(symbols))
        self._log(query, entries, None, status=branch.status)
        return branch

    def _log(
        self,
        query: str,
        entries: tuple[EntryPoint, ...],
        reason: str | None,
        status: str | None = None,
    ) -> None:
        """Rende osservabile anche il caso «nessun ingresso»: è normale, ma il suo TASSO dice se la
        selezione degli ingressi funziona."""
        log_event(
            logging.INFO,
            "combined_graph",
            entry_points=len(entries),
            sources=",".join(sorted({e.source for e in entries})) or None,
            graph_status=status or ("unavailable" if reason else "not_attempted"),
            reason=reason,
        )


def _all_unavailable(entry: EntryPoint, reason: str) -> SymbolContext:
    block = RelationBlock.unavailable(reason)
    return SymbolContext(
        qualname=entry.symbol, definitions=block, callers=block, callees=block, docs=block
    )


# --- corroborazione ------------------------------------------------------------------------------


def mark_corroboration(
    docs: tuple[RetrievalResult, ...],
    code: tuple[RetrievalResult, ...],
    branch: GraphBranch,
) -> tuple[tuple[RetrievalResult, ...], tuple[RetrievalResult, ...], GraphBranch]:
    """Marca le posizioni su cui i due metodi INDIPENDENTI convergono, in entrambe le direzioni.

    **Nessun dedup fra flussi.** Se somiglianza e struttura indicano lo stesso file, quella
    convergenza è essa stessa un segnale di rilevanza: rimuoverne una metà lo nasconderebbe. E il
    costo è contenuto, perché i due flussi portano cose diverse — il ramo `code` il testo, il ramo
    grafo un puntatore.

    **Limite v1 dichiarato:** il confronto è **sul solo path**. Un file con molte definizioni
    corrobora qualunque chunk dello stesso file. Grossolano, e registrato come tale: affinarlo per
    intervallo di righe richiede che i chunk lo trasportino.
    """
    by_path: dict[str, list[str]] = {}
    for symbol in branch.symbols:
        for hit in symbol.definitions.items:
            by_path.setdefault(hit.path, []).append(symbol.qualname)
    if not by_path:
        return docs, code, branch

    chunk_ids: dict[str, list[str]] = {}

    def _mark(results: tuple[RetrievalResult, ...]) -> tuple[RetrievalResult, ...]:
        out = []
        for r in results:
            names = by_path.get(r.path)
            if not names:
                out.append(r)
                continue
            chunk_ids.setdefault(r.path, []).append(r.chunk_id)
            metadata = dict(r.metadata or {})
            metadata["corroborated_by"] = sorted(set(names))
            out.append(
                RetrievalResult(
                    text=r.text, path=r.path, chunk_id=r.chunk_id, doc_type=r.doc_type,
                    score=r.score, metadata=metadata,
                )
            )
        return tuple(out)

    marked_docs, marked_code = _mark(docs), _mark(code)
    return marked_docs, marked_code, branch
