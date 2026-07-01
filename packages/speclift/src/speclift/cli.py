"""Entry point CLI `speclift` (interfaccia pubblica, Constitution III) — vedi `contracts/cli.md`.

Quattro modalità:
- `speclift <ref> …`        — percorso monolitico (autore in-process: stub/offline);
- `speclift changeset <ref> …` — marcia **0** (opzionale): emette il changeset grezzo, pre-
  localizzazione, per un locator alternativo (agente + tool MCP, vedi
  `contracts/evidence-locator-port.md`);
- `speclift bundle <ref> …` — **marcia 1** (agente-autore): emette il fascicolo di evidenza per l'agente.
  Con `--changeset`/`--located` consuma invece l'evidenza già localizzata dall'agente (marcia 0);
- `speclift assemble …`     — **marcia 2**: rilegge le frasi dell'agente, le riverifica (moat) e stampa.

Mappa gli errori di dominio sugli exit code del contratto: 0 ok · 2 ref invalido · 3 RAG giù ·
4 EarsAuthor giù · 5 bundle/contratto invalido. Nessun output parziale silenzioso su errore: causa e
stadio finiscono su stderr (Constitution VI/XI).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from speclift.adapters.anchor_fs import FilesystemAnchorResolver
from speclift.adapters.authored import AuthoredRequirementsAuthor
from speclift.adapters.provided_locator import ProvidedEvidenceLocator
from speclift.config import DEFAULT_CONFIG, JSON_OUTPUT_SUFFIX, MD_OUTPUT_SUFFIX
from speclift.domain.errors import SpecLiftError
from speclift.domain.models import SpecLiftReport
from speclift.observability import configure as configure_logging
from speclift.pipeline import (
    Components,
    RunOptions,
    assemble_report,
    build_bundle_from_changeset,
    build_changeset,
    build_evidence_bundle,
    default_components,
    run,
)
from speclift.serialize import (
    authoring_bundle_to_dict,
    bundle_from_dict,
    changeset_from_dict,
    changeset_to_dict,
)
from speclift.stages.filter_sources import excluded_notes
from speclift.stages.render import render_json, render_markdown

BUNDLE_OUTPUT_SUFFIX = ".bundle.json"
CHANGESET_OUTPUT_SUFFIX = ".changeset.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="speclift",
        description="Genera requisiti EARS ancorati da un changeset git (MVP).",
    )
    p.add_argument("ref", nargs="?", default=None, help="commit (sha o riferimento); default HEAD")
    p.add_argument("--staged", action="store_true", help="analizza il diff staged (ignora <ref>)")
    p.add_argument("--range", dest="range_spec", metavar="A..B", help="analizza il range A..B")
    p.add_argument(
        "--format", choices=["json", "md", "both"], default="both", help="formato di output"
    )
    p.add_argument("--out", metavar="PATH", help="percorso base dell'output (default: stdout)")
    p.add_argument(
        "--include-docs",
        action="store_true",
        help="includi la documentazione come fonte (spec/requisiti restano sempre esclusi)",
    )
    p.add_argument("--verbose", action="store_true", help="log strutturati per stadio")
    return p


def main(argv: list[str] | None = None, *, components: Components | None = None) -> int:
    raw_argv = sys.argv[1:] if argv is None else argv
    if raw_argv and raw_argv[0] == "changeset":
        return _cmd_changeset(raw_argv[1:], components=components)
    if raw_argv and raw_argv[0] == "bundle":
        return _cmd_bundle(raw_argv[1:], components=components)
    if raw_argv and raw_argv[0] == "assemble":
        return _cmd_assemble(raw_argv[1:])
    return _cmd_generate(raw_argv, components=components)


# --- Modalità monolitica (legacy: autore in-process) ------------------------------------------


def _cmd_generate(argv: list[str], *, components: Components | None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(verbose=args.verbose)

    if args.staged and args.range_spec:
        print("speclift: --staged e --range sono mutuamente esclusivi", file=sys.stderr)
        return 2

    options = RunOptions(
        ref=args.ref,
        staged=args.staged,
        range_spec=args.range_spec,
        include_docs=args.include_docs,
    )
    comps = components or default_components(".", config=DEFAULT_CONFIG)

    try:
        report = run(options, comps, config=DEFAULT_CONFIG)
    except SpecLiftError as exc:
        print(f"speclift: {type(exc).__name__}: {exc}", file=sys.stderr)
        return exc.exit_code

    _emit(report, fmt=args.format, out=args.out)
    return 0


# --- Marcia 0 (opzionale): emetti il changeset grezzo per un locator alternativo ---------------


def _cmd_changeset(argv: list[str], *, components: Components | None) -> int:
    p = argparse.ArgumentParser(
        prog="speclift changeset",
        description=(
            "Emette il changeset grezzo (post-filtro, pre-localizzazione) per un locator "
            "alternativo: l'agente chiamante, coi propri tool MCP, invece della CLI-vehicle."
        ),
    )
    p.add_argument("ref", nargs="?", default=None, help="commit (sha o riferimento); default HEAD")
    p.add_argument("--staged", action="store_true", help="analizza il diff staged (ignora <ref>)")
    p.add_argument("--range", dest="range_spec", metavar="A..B", help="analizza il range A..B")
    p.add_argument("--repo", default=".", help="radice del repo da analizzare (default: .)")
    p.add_argument("--out", metavar="PATH", help="file di output (default: stdout)")
    p.add_argument(
        "--include-docs",
        action="store_true",
        help="includi la documentazione come fonte (spec/requisiti restano sempre esclusi)",
    )
    p.add_argument("--verbose", action="store_true", help="log strutturati per stadio")
    args = p.parse_args(argv)
    configure_logging(verbose=args.verbose)

    if args.staged and args.range_spec:
        print("speclift: --staged e --range sono mutuamente esclusivi", file=sys.stderr)
        return 2

    options = RunOptions(
        ref=args.ref,
        staged=args.staged,
        range_spec=args.range_spec,
        include_docs=args.include_docs,
    )
    diff_source = (components or default_components(args.repo, config=DEFAULT_CONFIG)).diff_source

    try:
        changeset, excluded = build_changeset(options, diff_source, config=DEFAULT_CONFIG)
    except SpecLiftError as exc:
        print(f"speclift: {type(exc).__name__}: {exc}", file=sys.stderr)
        return exc.exit_code

    if excluded:
        print(f"speclift: esclusi {len(excluded)} file non-fonte (spec/requisiti/doc)", file=sys.stderr)
    text = json.dumps(changeset_to_dict(changeset, excluded), indent=2, ensure_ascii=False) + "\n"
    if args.out:
        path = _suffixed(args.out, CHANGESET_OUTPUT_SUFFIX)
        path.write_text(text, encoding="utf-8")
        print(f"speclift: scritto {path}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


# --- Marcia 1: emetti il fascicolo per l'agente -----------------------------------------------


def _cmd_bundle(argv: list[str], *, components: Components | None) -> int:
    p = argparse.ArgumentParser(
        prog="speclift bundle",
        description="Emette il fascicolo di evidenza (bundle) da far autorare all'agente chiamante.",
    )
    p.add_argument("ref", nargs="?", default=None, help="commit (sha o riferimento); default HEAD")
    p.add_argument("--staged", action="store_true", help="analizza il diff staged (ignora <ref>)")
    p.add_argument("--range", dest="range_spec", metavar="A..B", help="analizza il range A..B")
    p.add_argument("--repo", default=".", help="radice del repo da analizzare (default: .)")
    p.add_argument("--out", metavar="PATH", help="file di output (default: stdout)")
    p.add_argument(
        "--include-docs",
        action="store_true",
        help="includi la documentazione come fonte (spec/requisiti restano sempre esclusi)",
    )
    p.add_argument("--verbose", action="store_true", help="log strutturati per stadio")
    p.add_argument(
        "--changeset",
        metavar="PATH",
        help="changeset prodotto da `speclift changeset` (alternativa a <ref>/--staged/--range)",
    )
    p.add_argument(
        "--located",
        metavar="PATH",
        help="evidenza localizzata dall'agente via MCP (richiede --changeset)",
    )
    args = p.parse_args(argv)
    configure_logging(verbose=args.verbose)

    if bool(args.changeset) != bool(args.located):
        print("speclift: --changeset e --located vanno usati insieme", file=sys.stderr)
        return 2
    if args.changeset and (args.ref or args.staged or args.range_spec):
        print("speclift: --changeset è alternativo a <ref>/--staged/--range", file=sys.stderr)
        return 2
    if args.staged and args.range_spec:
        print("speclift: --staged e --range sono mutuamente esclusivi", file=sys.stderr)
        return 2

    if args.changeset:
        try:
            changeset_payload = json.loads(Path(args.changeset).read_text(encoding="utf-8"))
            located_payload = json.loads(Path(args.located).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"speclift: input non leggibile: {exc}", file=sys.stderr)
            return 5
        try:
            changeset = changeset_from_dict(changeset_payload)
            locator = ProvidedEvidenceLocator(located_payload)
            bundle = build_bundle_from_changeset(changeset, locator, config=DEFAULT_CONFIG)
        except SpecLiftError as exc:
            print(f"speclift: {type(exc).__name__}: {exc}", file=sys.stderr)
            return exc.exit_code
        except (KeyError, TypeError, ValueError) as exc:
            print(f"speclift: changeset/located malformato: {exc}", file=sys.stderr)
            return 5
        excluded = [tuple(e) for e in changeset_payload.get("excluded_sources", [])]
    else:
        options = RunOptions(
            ref=args.ref,
            staged=args.staged,
            range_spec=args.range_spec,
            include_docs=args.include_docs,
        )
        comps = components or default_components(args.repo, config=DEFAULT_CONFIG)
        try:
            bundle, excluded = build_evidence_bundle(options, comps, config=DEFAULT_CONFIG)
        except SpecLiftError as exc:
            print(f"speclift: {type(exc).__name__}: {exc}", file=sys.stderr)
            return exc.exit_code

    if excluded:
        print(f"speclift: esclusi {len(excluded)} file non-fonte (spec/requisiti/doc)", file=sys.stderr)
    text = json.dumps(authoring_bundle_to_dict(bundle, excluded), indent=2, ensure_ascii=False) + "\n"
    if args.out:
        path = _suffixed(args.out, BUNDLE_OUTPUT_SUFFIX)
        path.write_text(text, encoding="utf-8")
        print(f"speclift: scritto {path}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


# --- Marcia 2: assembla le frasi dell'agente, riverifica e stampa ------------------------------


def _cmd_assemble(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="speclift assemble",
        description="Rilegge le frasi scritte dall'agente, riverifica le àncore (moat) e stampa il report.",
    )
    p.add_argument("--bundle", required=True, metavar="PATH", help="fascicolo prodotto da `speclift bundle`")
    p.add_argument("--authored", required=True, metavar="PATH", help="frasi scritte dall'agente (JSON)")
    p.add_argument("--repo", default=".", help="radice del repo per la verifica delle àncore (default: .)")
    p.add_argument(
        "--format", choices=["json", "md", "both"], default="both", help="formato di output"
    )
    p.add_argument("--out", metavar="PATH", help="percorso base dell'output (default: stdout)")
    p.add_argument("--verbose", action="store_true", help="log strutturati per stadio")
    args = p.parse_args(argv)
    configure_logging(verbose=args.verbose)

    try:
        bundle_payload = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        authored = json.loads(Path(args.authored).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"speclift: input non leggibile: {exc}", file=sys.stderr)
        return 5

    # Accetta sia il file authoring (chiave `bundle`) sia un bundle stretto diretto.
    inner = bundle_payload.get("bundle", bundle_payload) if isinstance(bundle_payload, dict) else None
    if not isinstance(inner, dict):
        print("speclift: file bundle non valido (atteso oggetto con chiave 'bundle')", file=sys.stderr)
        return 5

    try:
        bundle = bundle_from_dict(inner)
        author = AuthoredRequirementsAuthor(authored)
        resolver = FilesystemAnchorResolver(args.repo)
        report = assemble_report(bundle, author, resolver, config=DEFAULT_CONFIG)
    except SpecLiftError as exc:
        print(f"speclift: {type(exc).__name__}: {exc}", file=sys.stderr)
        return exc.exit_code
    except (KeyError, TypeError, ValueError) as exc:
        print(f"speclift: bundle/authored malformato: {exc}", file=sys.stderr)
        return 5

    # Trasparenza G3: propaga nelle domande aperte i file esclusi dal filtro a monte (marcia bundle).
    excluded = [tuple(e) for e in bundle_payload.get("excluded_sources", [])]
    if excluded:
        report = replace(report, open_questions=[*report.open_questions, *excluded_notes(excluded)])

    _emit(report, fmt=args.format, out=args.out)
    return 0


# --- Output condiviso -------------------------------------------------------------------------


def _emit(report: SpecLiftReport, *, fmt: str, out: str | None) -> None:
    want_json = fmt in ("json", "both")
    want_md = fmt in ("md", "both")

    if out:
        if want_json:
            path = _suffixed(out, JSON_OUTPUT_SUFFIX)
            path.write_text(render_json(report), encoding="utf-8")
            print(f"speclift: scritto {path}", file=sys.stderr)
        if want_md:
            path = _suffixed(out, MD_OUTPUT_SUFFIX)
            path.write_text(render_markdown(report), encoding="utf-8")
            print(f"speclift: scritto {path}", file=sys.stderr)
        return

    if want_json:
        sys.stdout.write(render_json(report))
    if want_md:
        sys.stdout.write(render_markdown(report))


def _suffixed(base: str, suffix: str) -> Path:
    p = Path(base)
    return p.with_name(p.name + suffix)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
