"""Port (Protocol) del dominio — Constitution I/II/IV.

Il dominio dipende solo da queste interfacce; gli adapter concreti (git, RAG, requirements,
filesystem) le implementano e sono iniettati nel composition root. Strutturali → i test usano
fake senza ereditarietà.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from speclift.domain.models import (
    Anchor,
    ChangeKind,
    EarsRequirement,
    EvidenceBundle,
    Symbol,
    TestRef,
)


@runtime_checkable
class DiffSource(Protocol):
    """Fornisce il diff grezzo (unified) a partire da un riferimento git."""

    def raw_diff(self, ref: str, kind: ChangeKind) -> str:
        """Ritorna il testo unified-diff per `ref`. Solleva `InvalidRefError` se il ref è invalido."""
        ...


@runtime_checkable
class EvidenceLocator(Protocol):
    """Localizza simboli e test toccati, via Sertor RAG (multi-search)."""

    def locate_symbols(self, file_path: str, identifiers: list[str], snippet: str) -> list[Symbol]:
        """Risolve i simboli toccati da un hunk. Solleva `RagUnavailableError` se il RAG è giù."""
        ...

    def locate_tests(self, symbol: Symbol) -> list[TestRef]:
        """Trova i test che coprono `symbol`. Solleva `RagUnavailableError` se il RAG è giù."""
        ...


@runtime_checkable
class AnchorResolver(Protocol):
    """Verifica deterministicamente un'àncora contro la realtà del repo + RAG (il moat)."""

    def verify(self, anchor: Anchor) -> Anchor:
        """Ritorna l'àncora con `status` aggiornato (`verified`/`unverified`). Idempotente."""
        ...


@runtime_checkable
class EarsAuthor(Protocol):
    """L'unico stadio LLM: delega la stesura EARS alla capacità `requirements` di Sertor."""

    def author(self, bundle: EvidenceBundle) -> EarsAuthoringResult:
        """Genera EARS multi-quota ancorati al bundle. Solleva `EarsAuthorUnavailableError`."""
        ...


class EarsAuthoringResult:
    """Risultato della stesura EARS: requisiti + domande aperte (vedi ears-author-port.md)."""

    def __init__(
        self,
        requirements: list[EarsRequirement],
        open_questions: list[str] | None = None,
    ) -> None:
        self.requirements = requirements
        self.open_questions = open_questions or []
