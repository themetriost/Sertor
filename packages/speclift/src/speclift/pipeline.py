"""Composition root: wira i port agli adapter ed esegue il sandwich deterministico.

È l'unico punto che conosce gli adapter concreti (Constitution I/IX). I componenti sono iniettabili
(`Components`) così i test e2e possono sostituire fake senza toccare gli stadi.

Sequenza: ingest → parse_diff → locate_evidence → bundle → lift → verify → render(report).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from speclift.config import DEFAULT_CONFIG, Config
from speclift.domain.models import Changeset, EvidenceBundle, SpecLiftReport
from speclift.domain.ports import AnchorResolver, DiffSource, EarsAuthor, EvidenceLocator
from speclift.observability import stage_event
from speclift.stages.bundle import build_bundle
from speclift.stages.filter_sources import Excluded, excluded_notes, filter_source_files
from speclift.stages.ingest import ingest
from speclift.stages.lift import detect_drift, lift
from speclift.stages.locate_evidence import locate_evidence
from speclift.stages.parse_diff import parse_diff
from speclift.stages.verify import verify


@dataclass(frozen=True)
class RunOptions:
    ref: str | None = None
    staged: bool = False
    range_spec: str | None = None
    include_docs: bool = False  # G3: include la documentazione (i "due SpecLift", con/senza doc)


@dataclass(frozen=True)
class Components:
    diff_source: DiffSource
    locator: EvidenceLocator
    author: EarsAuthor
    resolver: AnchorResolver


def default_components(repo_path: str | Path = ".", *, config: Config = DEFAULT_CONFIG) -> Components:
    # Import locale: gli adapter toccano I/O; il modulo resta importabile senza di essi nei test.
    from speclift.adapters.anchor_fs import FilesystemAnchorResolver
    from speclift.adapters.ears_requirements import StubEarsAuthor
    from speclift.adapters.git_diff import GitDiffSource
    from speclift.adapters.rag_sertor import SertorRagLocator

    return Components(
        diff_source=GitDiffSource(repo_path),
        locator=SertorRagLocator(repo_path, config=config),
        author=StubEarsAuthor(),
        resolver=FilesystemAnchorResolver(repo_path),
    )


def run(
    options: RunOptions,
    components: Components,
    *,
    config: Config = DEFAULT_CONFIG,
) -> SpecLiftReport:
    raw = ingest(
        components.diff_source,
        ref=options.ref,
        staged=options.staged,
        range_spec=options.range_spec,
    )
    stage_event("ingest", f"ref={raw.ref} kind={raw.kind} empty={raw.is_empty}")

    if raw.is_empty:
        stage_event("ingest", "diff vuoto → report vuoto")
        return _empty_report(raw.ref, config)

    changeset = parse_diff(raw)
    changeset, filtered_out = filter_source_files(changeset, config, include_docs=options.include_docs)
    n_hunks = sum(len(f.hunks) for f in changeset.files)
    stage_event(
        "parse_diff",
        f"files={len(changeset.files)} hunks={n_hunks} filtered={len(filtered_out)}",
    )

    items, unresolved = locate_evidence(changeset, components.locator)
    stage_event("locate_evidence", f"items={len(items)} unresolved={len(unresolved)}")

    bundle = build_bundle(raw.ref, items, unresolved, config=config)
    lifted = lift(bundle, components.author)
    stage_event("lift", f"requirements={len(lifted.requirements)} open_q={len(lifted.open_questions)}")

    verified = verify(lifted.requirements, components.resolver)
    stage_event("verify", f"verified={len(verified.requirements)} excluded={len(verified.excluded)}")

    drifts = detect_drift(bundle, verified.requirements)
    stage_event("render", f"drifts={len(drifts)}")

    return SpecLiftReport(
        version=config.contract_version,
        changeset_ref=raw.ref,
        requirements=verified.requirements,
        drifts=drifts,
        excluded=verified.excluded,
        open_questions=[*lifted.open_questions, *excluded_notes(filtered_out)],
    )


def _empty_report(ref: str, config: Config) -> SpecLiftReport:
    return SpecLiftReport(version=config.contract_version, changeset_ref=ref)


# --- Pipeline spezzata al confine del bundle (modello agente-autore) ---------------------------
# `run()` (sopra) è il percorso monolitico (autore in-process: stub/test). Le due funzioni qui sotto
# spezzano il sandwich al bundle così l'autore può essere l'AGENTE CHIAMANTE: la CLI `bundle` produce
# l'evidenza, l'agente scrive le frasi, la CLI `assemble` le riverifica. Vedi contracts/ears-author-port.md.


def build_changeset(
    options: RunOptions,
    diff_source: DiffSource,
    *,
    config: Config = DEFAULT_CONFIG,
) -> tuple[Changeset, Excluded]:
    """Prima metà del confine bundle, PRIMA della localizzazione: ingest → parse → filtro sorgenti.

    Espone il changeset grezzo (post-filtro) così un locator ALTERNATIVO — tipicamente l'agente
    stesso coi propri tool MCP, quando l'host non offre la CLI-vehicle `sertor-rag` — possa produrre
    l'evidenza senza passare da `EvidenceLocator.locate_symbols`/`locate_tests`. Vedi
    `contracts/evidence-locator-port.md` e la marcia CLI `speclift changeset`.
    """
    raw = ingest(diff_source, ref=options.ref, staged=options.staged, range_spec=options.range_spec)
    stage_event("ingest", f"ref={raw.ref} kind={raw.kind} empty={raw.is_empty}")
    if raw.is_empty:
        return Changeset(ref=raw.ref, kind=raw.kind), []

    changeset = parse_diff(raw)
    changeset, filtered_out = filter_source_files(changeset, config, include_docs=options.include_docs)
    n_hunks = sum(len(f.hunks) for f in changeset.files)
    stage_event(
        "parse_diff",
        f"files={len(changeset.files)} hunks={n_hunks} filtered={len(filtered_out)}",
    )
    return changeset, filtered_out


def build_bundle_from_changeset(
    changeset: Changeset,
    locator: EvidenceLocator,
    *,
    config: Config = DEFAULT_CONFIG,
) -> EvidenceBundle:
    """Seconda metà del confine bundle: locate_evidence → bundle, dato un changeset già pronto.

    `locator` può essere il default `SertorRagLocator` (CLI-vehicle) o un `ProvidedEvidenceLocator`
    (evidenza già localizzata dall'agente via MCP) — il resto della pipeline non li distingue.
    """
    items, unresolved = locate_evidence(changeset, locator)
    stage_event("locate_evidence", f"items={len(items)} unresolved={len(unresolved)}")
    return build_bundle(changeset.ref, items, unresolved, config=config)


def build_evidence_bundle(
    options: RunOptions,
    components: Components,
    *,
    config: Config = DEFAULT_CONFIG,
) -> tuple[EvidenceBundle, Excluded]:
    """Prima metà del sandwich (deterministica): ingest → parse → filtro sorgenti → locate → bundle.

    Percorso di default (`components.locator` = CLI-vehicle). Per un locator alternativo (agente +
    MCP), usa `build_changeset` + `build_bundle_from_changeset` separatamente — è ciò che fa la CLI
    per `speclift changeset` + `speclift bundle --changeset/--located`.

    Ritorna il bundle e l'elenco (path, motivo) dei file esclusi dal filtro (trasparenza per la marcia 2).
    """
    changeset, filtered_out = build_changeset(options, components.diff_source, config=config)
    return build_bundle_from_changeset(changeset, components.locator, config=config), filtered_out


def assemble_report(
    bundle: EvidenceBundle,
    author: EarsAuthor,
    resolver: AnchorResolver,
    *,
    config: Config = DEFAULT_CONFIG,
) -> SpecLiftReport:
    """Seconda metà del sandwich (deterministica): lift (invariante) → verify (moat) → drift → report."""
    lifted = lift(bundle, author)
    stage_event("lift", f"requirements={len(lifted.requirements)} open_q={len(lifted.open_questions)}")

    verified = verify(lifted.requirements, resolver)
    stage_event("verify", f"verified={len(verified.requirements)} excluded={len(verified.excluded)}")

    drifts = detect_drift(bundle, verified.requirements)
    stage_event("render", f"drifts={len(drifts)}")

    return SpecLiftReport(
        version=config.contract_version,
        changeset_ref=bundle.changeset_ref,
        requirements=verified.requirements,
        drifts=drifts,
        excluded=verified.excluded,
        open_questions=lifted.open_questions,
    )
