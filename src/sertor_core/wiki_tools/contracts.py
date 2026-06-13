"""Contratti di risultato versionati delle operazioni wiki (FR-011, research D4).

Ogni operazione restituisce una dataclass pura e serializzabile con un campo `schema`
versionato (`<nome>/<versione>`). I contratti contengono **metadati e riferimenti**, mai il
contenuto integrale delle pagine. I consumatori (hook, skill, metà LLM FEAT-003-N) verificano
`schema` e tollerano campi aggiuntivi futuri (forward-compatible).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


def _to_json(payload: dict) -> str:
    """Serializza un contratto in JSON stabile (chiavi ordinate, UTF-8 non-escaped)."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=False)


@dataclass(frozen=True)
class ScanResult:
    """`wiki.scan/1` — esito della ricerca di lavoro pendente (FR-005)."""

    pending: int
    anchor: str | None
    dirs_scanned: list[str]
    message: str
    schema: str = "wiki.scan/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class StructureResult:
    """`wiki.structure/1` — esito dell'inizializzazione struttura (FR-003, SC-006)."""

    created: list[str]
    skipped_existing: list[str]
    schema: str = "wiki.structure/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class LintResult:
    """`wiki.lint/1` — difetti strutturali (FR-006); usato anche da `validate`.

    `stubs` elenca le pagine-segnaposto (frontmatter `status: stub`) da riempire: NON sono difetti
    (un forward-link risolto a uno stub è intenzionale, non `broken`), ma una worklist di nodi
    voluti.
    Campo additivo, forward-compatible (i consumatori più vecchi lo ignorano).
    """

    broken_links: list[dict] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    missing_frontmatter: list[dict] = field(default_factory=list)
    naming_violations: list[dict] = field(default_factory=list)
    stubs: list[str] = field(default_factory=list)
    schema: str = "wiki.lint/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class CollectResult:
    """`wiki.collect/1` — mappa delle pagine + metadati, senza corpo (FR-007)."""

    root: str
    index: str
    log: str
    pages: list[dict] = field(default_factory=list)
    schema: str = "wiki.collect/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class IndexResult:
    """`wiki.index/1` — esito orchestrazione indicizzazione (FR-010, US5)."""

    collection: str | None
    documents: int
    regenerated: bool
    schema: str = "wiki.index/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class AppendLogResult:
    """`wiki.append_log/1` — esito del write-back di una voce di log (FR-005/007)."""

    written: bool
    partition: str | None
    created: bool
    schema: str = "wiki.append_log/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class UpsertIndexResult:
    """`wiki.upsert_index/1` — esito del write idempotente di una riga d'indice (feature 010).

    `action`: `insert` (riga nuova) | `update` (sommario cambiato, riga sostituita in place) |
    `noop` (riga identica già presente, nessuna scrittura).
    """

    written: bool
    action: str
    page: str
    schema: str = "wiki.upsert_index/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class MigrateResult:
    """`wiki.migrate/1` — esito dello split retroattivo del log monolitico (FR-009)."""

    migrated_entries: int
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    schema: str = "wiki.migrate/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class MoveResult:
    """`wiki.move/1` — esito dello spostamento di una pagina con riscrittura dei link (feature 017).

    `rewritten`: lista di `{"page": rel_path, "occurrences": int}` per i file in cui sono stati
    riscritti link. `moved`: True se il file è stato spostato (False in `--dry-run` o in recovery
    quando il file era già a destinazione).
    """

    source: str
    destination: str
    rewritten: list[dict] = field(default_factory=list)
    moved: bool = False
    dry_run: bool = False
    schema: str = "wiki.move/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class ReconcileResult:
    """`wiki.reconcile/1` — candidate all'obsolescenza (sola lettura, feature 017).

    `candidates`: lista di `{"path", "status", "updated", "superseded_by", "reason"}`. `clean`:
    True se non ci sono pagine `status: superseded`. Il comando non modifica mai alcun file.
    """

    candidates: list[dict] = field(default_factory=list)
    clean: bool = True
    schema: str = "wiki.reconcile/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class ErrorResult:
    """`wiki.error/1` — errore esplicito (Principio IV); niente stato parziale."""

    error: str
    message: str
    schema: str = "wiki.error/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())
