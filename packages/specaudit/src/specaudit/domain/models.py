"""Entità di dominio di SpecAudit (dati puri, niente I/O — Constitution I).

I tipi seguono `specs/002-specaudit-mvp/data-model.md`. Le àncore SpecLift sono trasportate
inalterate (mai riverificate — REQ-A02).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class VerdictKind(StrEnum):
    """I quattro verdetti classici + il simmetrico per gli item 'di più'."""

    SODDISFATTO = "SODDISFATTO"
    PARZIALE = "PARZIALE"
    MANCANTE = "MANCANTE"
    DRIFTED = "DRIFTED"
    NON_DOCUMENTATO = "NON_DOCUMENTATO"


class Level(StrEnum):
    """Scala categorica unica (confidenza, severità, rilevabilità, rischio)."""

    ALTA = "alta"
    MEDIA = "media"
    BASSA = "bassa"


# --- Àncora (trasportata da SpecLift, mai riverificata) -------------------------------------


@dataclass(frozen=True)
class Anchor:
    """Àncora SpecLift, inalterata. `status` riflette ciò che SpecLift aveva marcato."""

    file: str
    lines: tuple[int, int]
    granularity: str  # "symbol" | "hunk"
    status: str  # "verified" | "unverified"
    symbol: str | None = None
    test: str | None = None


# --- I due insiemi in input ----------------------------------------------------------------


@dataclass(frozen=True)
class OriginalRequirement:
    """Requisito originale (forward), estratto dalla fonte. Contenuto non alterato."""

    index: int
    id: str
    text: str
    provenance: str


@dataclass(frozen=True)
class SpecLiftItem:
    """Requisito reverse-engineered da SpecLift (o un suo drift), con àncora ereditata."""

    index: int
    origin: str  # "requirement" | "drift"
    statement: str
    anchor: Anchor
    quota: str | None = None  # user_capability | behaviour | implementation | None (drift)


# --- Bundle (output di prepare, input dell'agente) -----------------------------------------


@dataclass(frozen=True)
class AuditBundle:
    """Fascicolo autoconsistente: i due insiemi indicizzati + i gap dichiarati."""

    version: str
    changeset_ref: str
    original: list[OriginalRequirement]
    speclift: list[SpecLiftItem]
    declared_gaps: list[str]
    source_provenance: dict[str, str]  # {"original": ..., "speclift": ...}


# --- Adjudication (prodotta dall'agente) ---------------------------------------------------


@dataclass(frozen=True)
class AlignedGroup:
    """Un gruppo centrato su un requisito originale. speclift vuoto = candidato MANCANTE."""

    original: int
    speclift: list[int]
    alignment_confidence: Level
    verdict: VerdictKind
    verdict_confidence: Level
    explanation: str | None = None
    severity: Level | None = None
    detectability: Level | None = None


@dataclass(frozen=True)
class ExtraItem:
    """Item SpecLift 'di più' (senza contropartita originale)."""

    speclift: int
    verdict: VerdictKind
    explanation: str
    verdict_confidence: Level
    severity: Level | None = None
    detectability: Level | None = None


@dataclass(frozen=True)
class Adjudication:
    """Allineamento (N:M) + classificazione. Referenzia gli item per indice."""

    changeset_ref: str
    groups: list[AlignedGroup]
    extras: list[ExtraItem]
    open_questions: list[str] = field(default_factory=list)


# --- Report (output finale) ----------------------------------------------------------------


@dataclass(frozen=True)
class RiskScore:
    severity: Level
    detectability: Level
    risk: Level


@dataclass(frozen=True)
class AuditRecord:
    """Verdetto emesso per un requisito/item. Cita sempre l'àncora (copiata dal bundle)."""

    verdict: VerdictKind
    verdict_confidence: Level
    anchors: list[Anchor]
    proposed: bool
    speclift_refs: list[str]
    original_ref: str | None = None
    explanation: str | None = None
    alignment_confidence: Level | None = None
    risk: RiskScore | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Matrix:
    counts: dict[str, int]
    records_by_verdict: dict[str, list[str]]


@dataclass(frozen=True)
class AuditReport:
    version: str
    changeset_ref: str
    records: list[AuditRecord]
    matrix: Matrix
    declared_gaps: list[str]
    open_questions: list[str]
