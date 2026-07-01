"""Serializzazione dominio → dict conformi agli schemi in `contracts/`.

Unico punto che conosce la forma di wire. Attenzione ai campi ammessi (`additionalProperties: false`):
es. l'`hunk` nello schema bundle NON ammette `lines`, quindi qui non viene emesso.
Le quote serializzano col loro `value` `lower_snake` (analyze E3).
"""

from __future__ import annotations

from speclift.config import DEFAULT_CONFIG, Config
from speclift.domain.models import (
    Anchor,
    Changeset,
    DriftFlag,
    EarsRequirement,
    EvidenceBundle,
    EvidenceItem,
    ExcludedRequirement,
    FileChange,
    Hunk,
    SpecLiftReport,
    Symbol,
    TestRef,
)


def _hunk(h: Hunk) -> dict:
    return {
        "file_path": h.file_path,
        "old_range": list(h.old_range),
        "new_range": list(h.new_range),
        "candidate_identifiers": list(h.candidate_identifiers),
    }


def _symbol(s: Symbol) -> dict:
    out = {"name": s.name, "path": s.path, "line": s.line}
    if s.kind:
        out["kind"] = s.kind
    if s.provenance:
        out["provenance"] = s.provenance
    return out


def _test(t: TestRef | None) -> dict | None:
    if t is None:
        return None
    out = {"name": t.name, "path": t.path, "covers_symbol": t.covers_symbol}
    if t.line:
        out["line"] = t.line
    if t.provenance:
        out["provenance"] = t.provenance
    return out


def _anchor(a: Anchor) -> dict:
    return {
        "file": a.file,
        "lines": list(a.lines),
        "symbol": a.symbol,
        "test": _test(a.test),
        "granularity": a.granularity,
        "status": a.status,
    }


def _item(i: EvidenceItem) -> dict:
    return {
        "hunk": _hunk(i.hunk),
        "symbols": [_symbol(s) for s in i.symbols],
        "tests": [_test(t) for t in i.tests],
        "anchor": _anchor(i.anchor),
        "granularity_used": i.granularity_used,
    }


def bundle_to_dict(bundle: EvidenceBundle) -> dict:
    return {
        "version": bundle.version,
        "changeset_ref": bundle.changeset_ref,
        "items": [_item(i) for i in bundle.items],
        "unresolved": [_hunk(h) for h in bundle.unresolved],
    }


# --- Fascicolo di authoring (input per l'agente) + ricostruzione (per `assemble`) -------------
# La stesura EARS è a carico dell'agente chiamante (contracts/ears-author-port.md): la CLI emette un
# "fascicolo" che l'agente legge, e poi rilegge il bundle per verificare ciò che l'agente ha scritto.


def _authoring_item(index: int, item: EvidenceItem) -> dict:
    """Vista per-item amichevole per l'agente: indice, àncora e il contenuto del diff da descrivere."""
    a = item.anchor
    return {
        "index": index,
        "file": a.file,
        "lines": list(a.lines),
        "symbol": a.symbol,
        "test": a.test.path if a.test else None,
        "granularity": item.granularity_used,
        "identifiers": list(item.hunk.candidate_identifiers),
        "diff": "\n".join(item.hunk.lines),
    }


def authoring_bundle_to_dict(
    bundle: EvidenceBundle, excluded_sources: list[tuple[str, str]] | None = None
) -> dict:
    """Artefatto della marcia `bundle`: il bundle stretto (per `assemble`) + la vista per l'agente.

    `excluded_sources` (path, motivo) sono i file esclusi dal filtro G3, riportati per trasparenza e
    inoltrati alla marcia `assemble`.
    """
    return {
        "version": bundle.version,
        "changeset_ref": bundle.changeset_ref,
        "bundle": bundle_to_dict(bundle),
        "items": [_authoring_item(i, it) for i, it in enumerate(bundle.items)],
        "unresolved_count": len(bundle.unresolved),
        "excluded_sources": [list(e) for e in (excluded_sources or [])],
    }


def _hunk_from(d: dict) -> Hunk:
    return Hunk(
        file_path=d["file_path"],
        old_range=tuple(d["old_range"]),  # type: ignore[arg-type]
        new_range=tuple(d["new_range"]),  # type: ignore[arg-type]
        candidate_identifiers=list(d.get("candidate_identifiers", [])),
    )


def _symbol_from(d: dict) -> Symbol:
    return Symbol(
        name=d["name"],
        path=d["path"],
        line=d["line"],
        kind=d.get("kind", ""),
        provenance=d.get("provenance", ""),
    )


def _test_from(d: dict | None) -> TestRef | None:
    if d is None:
        return None
    return TestRef(
        name=d["name"],
        path=d["path"],
        covers_symbol=d["covers_symbol"],
        line=d.get("line", 0),
        provenance=d.get("provenance", ""),
    )


def _anchor_from(d: dict) -> Anchor:
    return Anchor(
        file=d["file"],
        lines=tuple(d["lines"]),  # type: ignore[arg-type]
        granularity=d["granularity"],
        status=d["status"],
        symbol=d.get("symbol"),
        test=_test_from(d.get("test")),
    )


def _item_from(d: dict) -> EvidenceItem:
    return EvidenceItem(
        hunk=_hunk_from(d["hunk"]),
        anchor=_anchor_from(d["anchor"]),
        granularity_used=d["granularity_used"],
        symbols=[_symbol_from(s) for s in d.get("symbols", [])],
        tests=[t for t in (_test_from(x) for x in d.get("tests", [])) if t is not None],
    )


def bundle_from_dict(d: dict) -> EvidenceBundle:
    """Ricostruisce un `EvidenceBundle` dal dict prodotto da `bundle_to_dict` (round-trip per `assemble`)."""
    return EvidenceBundle(
        version=d["version"],
        changeset_ref=d["changeset_ref"],
        items=[_item_from(i) for i in d.get("items", [])],
        unresolved=[_hunk_from(h) for h in d.get("unresolved", [])],
    )


# --- Changeset grezzo (input per un locator alternativo, es. agente + tool MCP) ----------------
# `speclift changeset` emette il changeset POST-filtro ma PRIMA della localizzazione (contracts/
# evidence-locator-port.md): a differenza dell'hunk del bundle, qui `lines` è incluso perché
# l'agente deve leggere il diff per decidere cosa cercare via MCP.


def _changeset_hunk(h: Hunk) -> dict:
    return {
        "file_path": h.file_path,
        "old_range": list(h.old_range),
        "new_range": list(h.new_range),
        "candidate_identifiers": list(h.candidate_identifiers),
        "lines": list(h.lines),
    }


def _changeset_hunk_from(d: dict) -> Hunk:
    return Hunk(
        file_path=d["file_path"],
        old_range=tuple(d["old_range"]),  # type: ignore[arg-type]
        new_range=tuple(d["new_range"]),  # type: ignore[arg-type]
        candidate_identifiers=list(d.get("candidate_identifiers", [])),
        lines=list(d.get("lines", [])),
    )


def _file_change(f: FileChange) -> dict:
    return {
        "path": f.path,
        "change_type": f.change_type,
        "old_path": f.old_path,
        "is_binary": f.is_binary,
        "hunks": [_changeset_hunk(h) for h in f.hunks],
    }


def _file_change_from(d: dict) -> FileChange:
    return FileChange(
        path=d["path"],
        change_type=d["change_type"],
        old_path=d.get("old_path"),
        is_binary=d.get("is_binary", False),
        hunks=[_changeset_hunk_from(h) for h in d.get("hunks", [])],
    )


def changeset_to_dict(
    changeset: Changeset,
    excluded_sources: list[tuple[str, str]] | None = None,
    *,
    config: Config = DEFAULT_CONFIG,
) -> dict:
    """Artefatto della marcia `changeset`: il changeset grezzo, pronto per un locator alternativo."""
    return {
        "version": config.contract_version,
        "changeset_ref": changeset.ref,
        "kind": changeset.kind,
        "files": [_file_change(f) for f in changeset.files],
        "excluded_sources": [list(e) for e in (excluded_sources or [])],
    }


def changeset_from_dict(d: dict) -> Changeset:
    """Ricostruisce un `Changeset` dal dict prodotto da `changeset_to_dict`."""
    return Changeset(
        ref=d["changeset_ref"],
        kind=d["kind"],
        files=[_file_change_from(f) for f in d.get("files", [])],
    )


def _requirement(r: EarsRequirement) -> dict:
    out = {
        "id": r.id,
        "quota": r.quota.value,
        "statement": r.statement,
        "anchor": _anchor(r.anchor),
    }
    if r.source_item is not None:
        out["source_item"] = r.source_item
    return out


def _drift(d: DriftFlag) -> dict:
    return {"description": d.description, "anchor": _anchor(d.anchor), "status": d.status}


def _excluded(e: ExcludedRequirement) -> dict:
    return {"statement": e.statement, "reason": e.reason}


def report_to_dict(report: SpecLiftReport) -> dict:
    return {
        "version": report.version,
        "changeset_ref": report.changeset_ref,
        "requirements": [_requirement(r) for r in report.requirements],
        "drifts": [_drift(d) for d in report.drifts],
        "excluded": [_excluded(e) for e in report.excluded],
        "open_questions": list(report.open_questions),
    }
