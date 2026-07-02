"""Stadio 1 (FEAT-001) — costruisce l'`AuditBundle` dai due port.

Normalizza + indicizza densamente i due insiemi (0..N-1 separati), raccoglie i gap dichiarati.
Autoconsistente: l'agente giudicherà leggendo solo il bundle.
"""

from __future__ import annotations

from dataclasses import replace

from ..config import DEFAULT_CONFIG, Config
from ..domain.models import AuditBundle
from ..domain.ports import OriginalSourceResolver, SpecLiftSource
from .ingest_speclift import ingest_speclift
from .resolve_source import resolve_original


def prepare(
    speclift_source: SpecLiftSource,
    original_resolver: OriginalSourceResolver,
    changeset_ref: str | None = None,
    extra_gaps: list[str] | None = None,
    config: Config = DEFAULT_CONFIG,
) -> AuditBundle:
    ref, speclift_items = ingest_speclift(speclift_source, changeset_ref)
    original, provenance, gaps = resolve_original(original_resolver, ref)

    # re-indicizza densamente (difensivo: gli adapter già indicizzano, ma il bundle garantisce 0..N-1)
    original = [replace(o, index=i) for i, o in enumerate(original)]
    speclift_items = [replace(s, index=i) for i, s in enumerate(speclift_items)]

    declared_gaps = list(gaps)
    if extra_gaps:
        declared_gaps.extend(extra_gaps)

    return AuditBundle(
        version=config.bundle_version,
        changeset_ref=ref,
        original=original,
        speclift=speclift_items,
        declared_gaps=declared_gaps,
        source_provenance={"original": provenance, "speclift": "speclift-output"},
    )
