"""Entità del contesto reso all'agente: i tre flussi di una ricerca eterogenea (118, FEAT-012).

Il retrieval espone due famiglie di interrogazione **strutturalmente diverse**: la ricerca per
similarità produce una **classifica** con punteggio, il code-graph produce un **insieme** esatto
senza punteggio. Fonderle in una lista sola richiederebbe di inventare una scala comune che non
esiste — quindi si consegnano **separate e nominate** (`contracts/agent-context.md`).

Il cuore di questo modulo è la **tipizzazione dell'assenza**. Un blocco vuoto non dice nulla di per
sé: può voler dire «ho guardato e non c'è» (conclusione legittima) oppure «non ho potuto guardare»
(nessuna conclusione possibile). Se le due cose sono indistinguibili, l'agente afferma *«nessuno
chiama questa funzione»* quando in realtà manca una dipendenza — cioè **il contratto gli fa
fabbricare un'affermazione falsa**. Da qui `RelationStatus` e `unavailable_reason`.

Nessun import di SDK (Principio I): entità pure, `frozen`, campi a tuple come nel resto del dominio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sertor_core.domain.entities import RetrievalResult, SymbolHit

# Come è stato individuato un punto d'ingresso al grafo. SOLO le due vie effettivamente prodotte:
# la via per espansione dai risultati semantici è rinviata (i risultati solo-lessicali non portano
# il nome qualificato), quella per simboli dichiarati dal chiamante richiederebbe un parametro sul
# tool che non si espone. Prevederle qui senza produrle mai sarebbe un'astrazione senza evidenza.
EntrySource = Literal["extracted_from_query", "symbol_table_match"]

# `ok` = risultati presenti · `empty` = guardato, non c'è (conclusione LEGITTIMA di assenza)
# `unavailable` = NON guardato (nessuna conclusione possibile) — richiede sempre una causa.
RelationStatus = Literal["ok", "empty", "unavailable"]

# Le tre cause di indisponibilità, con RIMEDI DIVERSI — per questo non si conflatano.
GRAPH_NOT_BUILT = "graph_not_built"                          # → indicizzare il corpus
NAVIGATION_LIBRARY_MISSING = "navigation_library_missing"     # → installare l'extra `graph`
GRAPH_ARTIFACT_UNUSABLE = "graph_artifact_unusable"           # → re-indicizzare


@dataclass(frozen=True)
class EntryPoint:
    """Un simbolo da cui interrogare il grafo, con la PROVENIENZA dichiarata.

    `source` non è telemetria: è ciò che permette all'agente di **scontare** un ingresso debole. Un
    identificatore scritto nella domanda vale più di una sovrapposizione lessicale dedotta, e chi
    legge deve poterlo sapere invece di prendere per buono tutto allo stesso modo.
    """

    symbol: str
    source: EntrySource


@dataclass(frozen=True)
class RelationBlock:
    """I risultati di UN tipo di relazione per UN simbolo, col proprio esito e troncamento.

    `total` è il conteggio **prima** del taglio: mostrarne 8 di 47 senza dirlo fa affermare
    all'agente che i chiamanti sono otto.
    """

    items: tuple[SymbolHit, ...] = ()
    status: RelationStatus = "ok"
    reason: str | None = None
    total: int = 0

    @property
    def shown(self) -> int:
        return len(self.items)

    @property
    def truncated(self) -> bool:
        return self.shown < self.total

    @classmethod
    def of(cls, items: tuple[SymbolHit, ...], total: int | None = None) -> RelationBlock:
        """Blocco riuscito: `empty` se non c'è nulla — che è un esito, non un guasto."""
        count = len(items) if total is None else total
        return cls(items=items, status="ok" if items else "empty", total=count)

    @classmethod
    def unavailable(cls, reason: str) -> RelationBlock:
        """Blocco non ottenibile: la causa è OBBLIGATORIA, altrimenti è un vuoto muto."""
        return cls(items=(), status="unavailable", reason=reason, total=0)


@dataclass(frozen=True)
class SymbolContext:
    """I quattro blocchi di relazione che riguardano lo stesso simbolo.

    Gli stati sono **indipendenti**: chiamanti calcolati e documenti no è il caso NORMALE, non
    l'eccezione. È la ragione per cui lo stato non può vivere solo al livello superiore.
    """

    qualname: str
    definitions: RelationBlock = field(default_factory=RelationBlock)
    callers: RelationBlock = field(default_factory=RelationBlock)
    callees: RelationBlock = field(default_factory=RelationBlock)
    docs: RelationBlock = field(default_factory=RelationBlock)

    @property
    def blocks(self) -> tuple[RelationBlock, ...]:
        return (self.definitions, self.callers, self.callees, self.docs)


@dataclass(frozen=True)
class GraphBranch:
    """Il flusso strutturale: da dove si è entrati, cosa si è trovato, e con quale esito.

    **`status` è una property DERIVATA, non un campo.** Un campo impostabile a mano può divergere
    dai sotto-stati che dovrebbe riassumere, e quel giorno il riassunto mente. Così invece
    l'invariante «`not_attempted` ⟺ nessun ingresso» è vera **per costruzione**, non per disciplina.
    """

    entry_points: tuple[EntryPoint, ...] = ()
    symbols: tuple[SymbolContext, ...] = ()
    unavailable_reason: str | None = None

    @property
    def status(self) -> str:
        if self.unavailable_reason is not None:
            return "unavailable"
        if not self.entry_points:
            return "not_attempted"
        if any(b.status != "ok" for s in self.symbols for b in s.blocks):
            return "partial"
        return "ok"

    @classmethod
    def not_attempted(cls) -> GraphBranch:
        """Nessun ingresso ricavabile: il grafo NON viene interrogato, e non costa nulla."""
        return cls()

    @classmethod
    def unavailable(cls, reason: str, entry_points: tuple[EntryPoint, ...] = ()) -> GraphBranch:
        """Il grafo non è consultabile: si dichiara la causa, non si restituisce un insieme vuoto.

        Gli `entry_points` restano: l'agente deve poter distinguere «non ho trovato cosa cercare» da
        «sapevo cosa cercare ma lo strumento è rotto».
        """
        return cls(entry_points=entry_points, unavailable_reason=reason)


@dataclass(frozen=True)
class AgentContext:
    """I tre flussi consegnati insieme, mai fusi in una classifica sola."""

    docs: tuple[RetrievalResult, ...] = ()
    code: tuple[RetrievalResult, ...] = ()
    graph: GraphBranch = field(default_factory=GraphBranch)
