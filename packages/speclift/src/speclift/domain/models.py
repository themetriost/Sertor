"""Entità di dominio (dati puri, niente I/O) — vedi `specs/001-speclift-mvp/data-model.md`.

I valori dell'enum `Quota` serializzano in `lower_snake` (`user_capability`, `behaviour`,
`implementation`) per combaciare con `contracts/output.schema.json` (analyze E3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

# --- Tipi letterali condivisi -----------------------------------------------------------------

ChangeKind = Literal["commit", "range", "staged"]
ChangeType = Literal["added", "modified", "deleted", "renamed"]
Granularity = Literal["symbol", "hunk"]
AnchorStatus = Literal["verified", "unverified"]

#: Sentinel per il diff staged usato come `Changeset.ref`.
STAGED_REF = "STAGED"


class Quota(StrEnum):
    """Le tre quote di requisito (FR-006, REQ-X04). Il `value` è la forma `lower_snake`."""

    USER_CAPABILITY = "user_capability"
    BEHAVIOUR = "behaviour"
    IMPLEMENTATION = "implementation"


#: Tutte le quote, nell'ordine canonico usato per la copertura multi-quota.
ALL_QUOTAS: tuple[Quota, ...] = (Quota.USER_CAPABILITY, Quota.BEHAVIOUR, Quota.IMPLEMENTATION)


# --- Diff e changeset -------------------------------------------------------------------------


@dataclass(frozen=True)
class Hunk:
    """Porzione di diff. Unità di fallback dell'àncora ibrida quando nessun simbolo si risolve."""

    file_path: str
    old_range: tuple[int, int]  # (start, len)
    new_range: tuple[int, int]  # (start, len)
    lines: list[str] = field(default_factory=list)
    candidate_identifiers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FileChange:
    path: str
    change_type: ChangeType
    old_path: str | None = None  # solo per rename
    is_binary: bool = False
    hunks: list[Hunk] = field(default_factory=list)


@dataclass(frozen=True)
class RawDiff:
    """Diff grezzo (unified) prodotto da `ingest`, prima della strutturazione di `parse_diff`."""

    ref: str
    kind: ChangeKind
    text: str

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


@dataclass(frozen=True)
class Changeset:
    """La modifica in input, strutturata. `ref` è un commit, un range, o il sentinel `STAGED`."""

    ref: str
    kind: ChangeKind
    files: list[FileChange] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any(f.hunks for f in self.files)


# --- Evidenza ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Symbol:
    """Entità di codice localizzata via RAG."""

    name: str
    path: str
    line: int
    kind: str = ""
    provenance: str = ""


@dataclass(frozen=True)
class TestRef:
    __test__ = False  # non è una classe di test pytest (prefisso "Test")

    name: str
    path: str
    covers_symbol: str
    line: int = 0
    provenance: str = ""


@dataclass(frozen=True)
class Anchor:
    """Legame citabile requisito → evidenza. Cuore del moat."""

    file: str
    lines: tuple[int, int]  # (start, end)
    granularity: Granularity
    status: AnchorStatus = "unverified"
    symbol: str | None = None
    test: TestRef | None = None


@dataclass(frozen=True)
class EvidenceItem:
    """Un elemento del changeset con la sua evidenza (uno per simbolo, o uno per hunk)."""

    hunk: Hunk
    anchor: Anchor
    granularity_used: Granularity
    symbols: list[Symbol] = field(default_factory=list)
    tests: list[TestRef] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceBundle:
    """Contratto versionato, fonte di verità (FR-005, REQ-X06). Autoconsistente."""

    version: str
    changeset_ref: str
    items: list[EvidenceItem] = field(default_factory=list)
    unresolved: list[Hunk] = field(default_factory=list)


# --- Output -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class EarsRequirement:
    """Requisito generato (output dell'unico stadio LLM). Ogni `anchor` ∈ bundle (mai nuova)."""

    id: str
    quota: Quota
    statement: str
    anchor: Anchor
    source_item: str | None = None


@dataclass(frozen=True)
class DriftFlag:
    """Comportamento del changeset non coperto da alcun requisito (FR-010). Mai auto-confermato."""

    description: str
    anchor: Anchor
    status: Literal["proposed"] = "proposed"


@dataclass(frozen=True)
class ExcludedRequirement:
    """Requisito scartato perché privo di àncora verificabile (trasparenza del moat)."""

    statement: str
    reason: str


@dataclass(frozen=True)
class SpecLiftReport:
    """Output root. Schema: `contracts/output.schema.json`."""

    version: str
    changeset_ref: str
    requirements: list[EarsRequirement] = field(default_factory=list)
    drifts: list[DriftFlag] = field(default_factory=list)
    excluded: list[ExcludedRequirement] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
