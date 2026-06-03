"""Entry-point della CLI `sertor`: parser argparse, dispatch ai comandi, mapping errori → exit code.

Layer sottile: nessuna logica RAG qui. Le eccezioni di dominio del core diventano messaggi leggibili
su stderr + exit code non-zero (REQ-003/004); il traceback completo solo in `--verbose`.
"""
from __future__ import annotations

import argparse
import sys

from sertor_cli import observability
from sertor_cli.commands import index_cmd, search_cmd, wiki_cmd
from sertor_core.domain.errors import SertorError


def _force_utf8() -> None:
    """Forza l'output UTF-8 anche su console non-UTF-8 (es. cp1252 su Windows).

    Senza, stampare caratteri come `→` o accenti su una console Windows solleva UnicodeEncodeError.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass  # stream non riconfigurabile (es. catturato nei test): nessun problema


def _global_opts() -> argparse.ArgumentParser:
    """Opzioni globali condivise — aggiunte sia al parser top sia a ogni sottocomando, così
    funzionano sia prima (`sertor -v index`) sia dopo (`sertor index -v`) il sottocomando.
    `SUPPRESS` evita che i default del sottocomando sovrascrivano un valore dato al livello top.
    """
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS,
                        help="log INFO a console")
    common.add_argument("--log-json", action="store_true", default=argparse.SUPPRESS,
                        help="emette i log come record JSON")
    common.add_argument("--log-config", metavar="FILE", default=argparse.SUPPRESS,
                        help="config di logging dictConfig (YAML/JSON) per appender esterni")
    return common


def _build_parser() -> argparse.ArgumentParser:
    common = _global_opts()
    parser = argparse.ArgumentParser(prog="sertor", parents=[common],
                                     description="Sertor — RAG su una codebase.")
    sub = parser.add_subparsers(dest="command")

    p_index = sub.add_parser("index", parents=[common], help="indicizza un repository")
    p_index.add_argument("path", help="path della codebase da indicizzare")
    p_index.add_argument("--corpus", help="namespace del corpus (collezione dedicata)")
    p_index.add_argument("--json", action="store_true", help="output del report in JSON")
    p_index.set_defaults(func=index_cmd.run)

    p_search = sub.add_parser("search", parents=[common], help="interroga l'indice")
    p_search.add_argument("query", help="testo della query")
    p_search.add_argument("-k", type=int, default=None, help="numero di risultati (default: core)")
    p_search.add_argument("--type", choices=["code", "doc", "both"], default=None,
                          help="ambito della ricerca (default: both)")
    p_search.add_argument("--json", action="store_true", help="output risultati in JSON")
    p_search.add_argument("--full", action="store_true", help="testo completo, non l'anteprima")
    p_search.add_argument("--corpus", help="namespace del corpus da interrogare")
    p_search.set_defaults(func=search_cmd.run)

    p_wiki = sub.add_parser("wiki", parents=[common], help="operazioni sul wiki")
    wiki_sub = p_wiki.add_subparsers(dest="wiki_command")
    p_wiki_index = wiki_sub.add_parser("index", parents=[common],
                                       help="indicizza un wiki nel corpus RAG")
    p_wiki_index.add_argument("wiki_path", help="path della radice del wiki")
    p_wiki_index.add_argument("--corpus", help="namespace del corpus")
    p_wiki_index.add_argument("--json", action="store_true", help="output del report in JSON")
    p_wiki_index.set_defaults(func=wiki_cmd.run)

    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    parser = _build_parser()
    args = parser.parse_args(argv)

    observability.configure(
        verbose=getattr(args, "verbose", False),
        log_json=getattr(args, "log_json", False),
        log_config=getattr(args, "log_config", None),
    )

    func = getattr(args, "func", None)
    if func is None:
        parser.print_help(sys.stderr)
        return 1

    try:
        return func(args)
    except SertorError as exc:
        print(f"errore: {exc}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        return 1
