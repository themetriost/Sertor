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
    (un forward-link risolto a uno stub è intenzionale, non `broken`), ma una worklist di nodi voluti.
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
class ErrorResult:
    """`wiki.error/1` — errore esplicito (Principio IV); niente stato parziale."""

    error: str
    message: str
    schema: str = "wiki.error/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())
