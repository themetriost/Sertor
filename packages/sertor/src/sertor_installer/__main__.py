"""Backbone CLI del comando `sertor` (contracts/cli-commands.md, D8).

Layer **sottile** (Principio I): parsing argparse → funzioni dell'installer → formattazione report.
Pattern di riferimento: `src/sertor_core/cli/__main__.py`. Exit code: `0` successo · `1` errore di
dominio (`SertorError`) · `2` errore d'uso (argparse).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sertor_core.domain.errors import ConfigError, IngestionError, SertorError
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_wiki import build_install_plan, execute_plan


class CapabilityNotAvailableError(SertorError):
    """Una capacità d'install dichiarata ma non ancora implementata (stub; D8, REQ-104)."""

    def __init__(self, capability: str):
        self.capability = capability
        super().__init__(f"install {capability} non è ancora disponibile (taglio futuro)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sertor",
        description="Installer del sistema-wiki (LLM Wiki) su un repo ospite.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<comando>")

    install = sub.add_parser(
        "install", help="installa una capacità sull'ospite (wiki | rag | governance)"
    )
    install_sub = install.add_subparsers(
        dest="capability", required=True, metavar="<capacità>"
    )

    wiki = install_sub.add_parser("wiki", help="installa il sistema-wiki (disponibile)")
    wiki.add_argument("--target", default=".", help="radice del repo ospite (default: cwd)")
    wiki.add_argument(
        "--language", default="en", help="lingua del wiki.config.toml generato (default: en)"
    )
    wiki.add_argument(
        "--source-dirs", default=None,
        help="override CSV delle cartelle sorgente (es. 'src,docs'); bypassa l'euristica",
    )
    wiki.add_argument("--json", action="store_true", help="emette il report come JSON")

    install_sub.add_parser("rag", help="installa l'infrastruttura RAG (pianificato)")
    install_sub.add_parser("governance", help="installa la governance (pianificato)")

    return parser


def _cmd_install_wiki(args) -> int:
    """Handler `install wiki`: valida il target, costruisce il piano, esegue, stampa il report."""
    target_root = Path(args.target).resolve()
    if not target_root.exists():
        raise ConfigError("target inesistente", key=str(target_root))
    if not target_root.is_dir():
        raise IngestionError("il target non è una directory", path=str(target_root))

    source_dirs = (
        [d for d in args.source_dirs.split(",")] if args.source_dirs else None
    )
    profile = build_host_profile(
        target_root, source_dirs_override=source_dirs, language=args.language
    )
    plan = build_install_plan()
    report = execute_plan(plan, profile)

    print(report.render_json() if args.json else report.render_human())
    return report.exit_code()


def _dispatch(args) -> int:
    if args.command == "install":
        if args.capability == "wiki":
            return _cmd_install_wiki(args)
        # stub leggibili: exit 1 via eccezione di dominio dedicata
        raise CapabilityNotAvailableError(args.capability)
    raise ConfigError(f"comando non supportato: {args.command}")  # pragma: no cover


def main(argv: list[str] | None = None) -> int:
    """Punto d'ingresso del console-script `sertor`. Ritorna l'exit code (0/1/2)."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    args = _build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except SertorError as exc:
        print(f"errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
