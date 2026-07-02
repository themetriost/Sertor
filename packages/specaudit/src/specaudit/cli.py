"""CLI `specaudit` — interfaccia pubblica (Principio III). Host-agnostica.

Tre sottocomandi: `prepare` (marcia 1), `report` (marcia 2), `audit` (monolite offline con stub).
Non legge mai codice/test/CI (REQ-A01); non riverifica le àncore (REQ-A02).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

from .adapters.adjudication_file import FileAdjudicator, StubAdjudicator
from .adapters.requirements_fs import RequirementsFsResolver
from .adapters.speclift_json import SpecLiftJsonSource
from .config import DEFAULT_CONFIG
from .domain.errors import (
    ChangesetMismatchError,
    InvalidAdjudicationError,
    SpecLiftArtifactError,
    SpecLiftVersionError,
)
from .pipeline import audit as run_audit
from .pipeline import build_bundle, build_report
from .serialize import bundle_from_dict, bundle_to_dict
from .stages import render

EXIT_OK = 0
EXIT_ARGS = 2
EXIT_SPECLIFT = 3
EXIT_ADJUDICATION = 5


class _ArgsError(Exception):
    """Uso improprio delle opzioni → exit code 2 (fail-loud, non silenzioso)."""


def _build_resolver(args: argparse.Namespace) -> RequirementsFsResolver:
    provided = getattr(args, "provided", None)
    if provided:
        raise _ArgsError(
            "--provided (fonte via agente/RAG) è differito nell'MVP (FR-020, deferral dichiarato); "
            "usa --requirements o --original"
        )
    original = getattr(args, "original", None)
    requirements = getattr(args, "requirements", None)
    if original and requirements:
        raise _ArgsError("--original e --requirements sono mutuamente esclusivi")
    if original:
        return RequirementsFsResolver(original)
    if requirements:
        return RequirementsFsResolver(requirements)
    return RequirementsFsResolver(DEFAULT_CONFIG.requirements_dir)


def _ensure_utf8_stdio() -> None:
    """Windows: la console cp1252 non codifica i caratteri Unicode del report (à, ↔, ×, ⚠️).

    Riconfigura stdout/stderr a UTF-8 dove possibile; i file di output sono già scritti UTF-8.
    """

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):  # pragma: no cover
                reconfigure(encoding="utf-8")


def _fail(code: int, message: str) -> int:
    print(f"specaudit: errore: {message}", file=sys.stderr)
    return code


def _write_outputs(base: str | None, report, fmt: str) -> None:
    out_json = render.to_json(report)
    out_md = render.to_markdown(report)
    if base is None:
        # stdout: preferisci md se richiesto, altrimenti json
        print(out_md if fmt == "md" else out_json)
        return
    if fmt in ("json", "both"):
        Path(f"{base}.json").write_text(out_json, encoding="utf-8")
    if fmt in ("md", "both"):
        Path(f"{base}.md").write_text(out_md, encoding="utf-8")
    print(f"specaudit: report scritto in {base}.{'json/md' if fmt == 'both' else fmt}", file=sys.stderr)


def _cmd_prepare(args: argparse.Namespace) -> int:
    source = SpecLiftJsonSource(args.speclift)
    resolver = _build_resolver(args)
    bundle = build_bundle(source, resolver, args.changeset_ref)
    payload = json.dumps(bundle_to_dict(bundle), ensure_ascii=False, indent=2)
    if args.out:
        Path(f"{args.out}.audit-bundle.json").write_text(payload, encoding="utf-8")
        print(f"specaudit: bundle scritto in {args.out}.audit-bundle.json", file=sys.stderr)
    else:
        print(payload)
    for gap in bundle.declared_gaps:
        print(f"specaudit: gap dichiarato: {gap}", file=sys.stderr)
    return EXIT_OK


def _cmd_report(args: argparse.Namespace) -> int:
    bundle = bundle_from_dict(json.loads(Path(args.bundle).read_text(encoding="utf-8")))
    adjudicator = FileAdjudicator(args.adjudicated)
    adj = adjudicator.adjudicate(bundle)
    report = build_report(bundle, adj)
    _write_outputs(args.out, report, args.format)
    return EXIT_OK


def _cmd_audit(args: argparse.Namespace) -> int:
    source = SpecLiftJsonSource(args.speclift)
    resolver = _build_resolver(args)
    report = run_audit(source, resolver, StubAdjudicator(), args.changeset_ref)
    _write_outputs(args.out, report, args.format)
    return EXIT_OK


def _add_original_opts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--original", help="documento di requisiti originali (file)")
    p.add_argument("--requirements", help="cartella requirements/ canonica")
    p.add_argument("--provided", help="fonte fornita dall'agente (differito nell'MVP)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="specaudit", description="Auditor di conformità requisito↔codice")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prepare", help="marcia 1: costruisce il fascicolo di audit")
    p_prep.add_argument("--speclift", required=True, help="output SpecLift (*.speclift.json)")
    _add_original_opts(p_prep)
    p_prep.add_argument("--changeset-ref", dest="changeset_ref", help="ref atteso (fail-loud se diverso)")
    p_prep.add_argument("--out", help="path base di output (default: stdout)")
    p_prep.add_argument("--verbose", action="store_true")
    p_prep.set_defaults(func=_cmd_prepare)

    p_rep = sub.add_parser("report", help="marcia 2: emette il report verificato")
    p_rep.add_argument("--bundle", required=True, help="audit-bundle.json prodotto da prepare")
    p_rep.add_argument("--adjudicated", required=True, help="adjudicated.json scritto dall'agente")
    p_rep.add_argument("--format", choices=["json", "md", "both"], default="both")
    p_rep.add_argument("--out", help="path base di output (default: stdout)")
    p_rep.add_argument("--verbose", action="store_true")
    p_rep.set_defaults(func=_cmd_report)

    p_aud = sub.add_parser("audit", help="monolite offline/test (StubAdjudicator, verdetti placeholder)")
    p_aud.add_argument("--speclift", required=True, help="output SpecLift (*.speclift.json)")
    _add_original_opts(p_aud)
    p_aud.add_argument("--changeset-ref", dest="changeset_ref", help="ref atteso (fail-loud se diverso)")
    p_aud.add_argument("--format", choices=["json", "md", "both"], default="both")
    p_aud.add_argument("--out", help="path base di output (default: stdout)")
    p_aud.add_argument("--verbose", action="store_true")
    p_aud.set_defaults(func=_cmd_audit)

    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except _ArgsError as exc:
        return _fail(EXIT_ARGS, str(exc))
    except (SpecLiftArtifactError, SpecLiftVersionError, ChangesetMismatchError) as exc:
        return _fail(EXIT_SPECLIFT, str(exc))
    except InvalidAdjudicationError as exc:
        return _fail(EXIT_ADJUDICATION, str(exc))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
