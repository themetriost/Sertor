"""CLI `skillauthor` — interfaccia pubblica (Principio III, contracts/cli.md).

Deterministico, offline, in sola lettura: l'unico output è su stdout. Codici d'uscita:
0 esito positivo · 1 esito negativo di dominio · 2 errore d'uso o d'ingresso.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections.abc import Callable

from .domain.errors import SkillAuthorError

EXIT_OK = 0
EXIT_NEGATIVE = 1
EXIT_USAGE = 2


class _Parser(argparse.ArgumentParser):
    """argparse che segnala l'errore d'uso con un'eccezione invece di uscire dal processo."""

    def error(self, message: str):  # noqa: D401 — firma di argparse
        raise _UsageError(message)


class _UsageError(Exception):
    pass


def run_guarded(action: Callable[[], int]) -> int:
    """Esegue un comando e traduce gli errori di SkillAuthor nel codice 2, con il messaggio su stderr."""

    try:
        return action()
    except SkillAuthorError as exc:
        print(f"skillauthor: errore: {exc}", file=sys.stderr)
        return EXIT_USAGE


def emit(document: dict, as_json: bool, text: str) -> None:
    print(json.dumps(document, ensure_ascii=False, indent=2) if as_json else text)


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):  # pragma: no cover
                reconfigure(encoding="utf-8")


def build_parser() -> _Parser:
    parser = _Parser(prog="skillauthor", description="Runtime della capability di authoring di skill.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    _register_commands(sub)
    return parser


def _register_commands(sub) -> None:
    """Registra i sottocomandi. Ogni modulo di comando espone `register(sub)`."""

    from . import commands

    for register in commands.REGISTRY:
        register(sub)


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    try:
        args = build_parser().parse_args(argv)
    except _UsageError as exc:
        print(f"skillauthor: errore d'uso: {exc}", file=sys.stderr)
        return EXIT_USAGE
    return run_guarded(lambda: args.handler(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
