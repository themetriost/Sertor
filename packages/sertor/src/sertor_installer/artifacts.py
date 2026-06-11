"""Entità di dominio dell'installer: `Artifact` e `ArtifactOutcome` (data-model §1, §4).

Value object puri, senza import di SDK esterni (Principio I). Ogni `Artifact` conosce la propria
**regola di non-distruttività** (la `WriteStrategy`); l'esecuzione del piano produce un
`ArtifactOutcome` per ciascun artefatto (più d'uno per `INIT_STRUCTURE`, aggregato).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sertor_core.domain.errors import ConfigError


class ArtifactKind(Enum):
    """Natura dell'artefatto installabile (data-model §1)."""

    FILE = "file"
    SETTINGS_MERGE = "settings_merge"
    MARKER_BLOCK = "marker_block"
    STRUCTURE = "structure"
    CONFIG = "config"


class WriteStrategy(Enum):
    """Regola di scrittura non-distruttiva associata al `kind` (data-model §1)."""

    CREATE_IF_ABSENT = "create_if_absent"
    MERGE_DEDUP = "merge_dedup"
    APPEND_BLOCK = "append_block"
    INIT_STRUCTURE = "init_structure"
    GENERATE_CONFIG = "generate_config"


class Outcome(Enum):
    """Esito di un singolo artefatto (data-model §4)."""

    CREATED = "created"
    SKIPPED = "skipped"
    MERGED = "merged"
    BLOCK = "block"
    ERROR = "error"


@dataclass(frozen=True)
class Artifact:
    """Unità che l'installer porta sull'ospite.

    `target_rel` è SEMPRE relativo al `--target` (mai assoluto, mai risalente con `..`): la
    validazione in `__post_init__` impedisce path-traversal (data-model §1, regole di validità).
    """

    kind: ArtifactKind
    source: str | None
    target_rel: str
    strategy: WriteStrategy

    def __post_init__(self) -> None:
        rel = self.target_rel.replace("\\", "/")
        if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
            raise ConfigError("target_rel deve essere relativo", key=self.target_rel)
        if ".." in rel.split("/"):
            raise ConfigError("target_rel non può risalire con '..'", key=self.target_rel)


@dataclass(frozen=True)
class ArtifactOutcome:
    """Esito per artefatto: cosa è successo a `target_rel` (data-model §4)."""

    target_rel: str
    outcome: Outcome
    detail: str | None = None
