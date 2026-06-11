"""CLI di esecuzione RAG `sertor-rag` (FEAT-011, contracts/cli-commands.md).

`sertor-rag index <path>` indicizza un repository; `sertor-rag search <query>` interroga l'indice.
Equivalente: `python -m sertor_core.cli`. Layer **sottile** (Principio I): parsing → composition
root del core → formattazione. Nessuna logica di retrieval qui. Exit code: `0` successo · `1`
errore di dominio (`SertorError`, messaggio su stderr) · `2` errore d'uso (argparse). Pattern di
riferimento: `sertor_core/wiki_tools/__main__.py`.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from sertor_core.cli import output
from sertor_core.cli.logging_setup import setup_logging
from sertor_core.composition import (
    build_baseline_engine,
    build_facade,
    build_indexer,
)
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError, IngestionError, SertorError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sertor-rag",
        description="CLI di esecuzione RAG: indicizza un repository e interrogalo dal terminale.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="comando")

    p_index = sub.add_parser(
        "index", help="indicizza un repository in una collezione vettoriale (full rebuild)",
        description="Costruisce l'indice vettoriale del repository e riporta i conteggi.",
    )
    p_index.add_argument("path", help="radice del repository da indicizzare")
    p_index.add_argument("--corpus", default=None,
                         help="namespace del corpus; prevale su SERTOR_CORPUS")
    p_index.add_argument("--json", action="store_true", help="report come oggetto JSON")
    _add_logging_flags(p_index)
    p_index.set_defaults(handler=_cmd_index)

    p_search = sub.add_parser(
        "search", help="interroga l'indice e restituisce i top-k risultati",
        description="Ricerca semantica sull'indice; risultati con path, tipo, chunk_id, score.",
    )
    p_search.add_argument("query", help="testo della query (non vuoto)")
    p_search.add_argument("-k", type=int, default=None,
                          help="numero di risultati (default: Settings.default_k)")
    p_search.add_argument("--type", choices=["code", "doc", "both"], default="both",
                          help="filtro per tipo documento (default: both)")
    p_search.add_argument("--full", action="store_true",
                          help="testo completo del chunk invece dell'anteprima troncata")
    p_search.add_argument("--json", action="store_true", help="risultati come array JSON")
    p_search.add_argument("--corpus", default=None,
                          help="namespace del corpus; prevale su SERTOR_CORPUS")
    _add_logging_flags(p_search)
    p_search.set_defaults(handler=_cmd_search)

    return parser


def _add_logging_flags(p: argparse.ArgumentParser) -> None:
    """Leve di osservabilità comuni a entrambi i sottocomandi (US3, FR-017..019)."""
    p.add_argument("-v", "--verbose", action="store_true",
                   help="abilita i log INFO strutturati su stderr")
    p.add_argument("--log-json", action="store_true",
                   help="emette i record di log come JSON (un oggetto per evento)")
    p.add_argument("--log-config", default=None,
                   help="file dictConfig (JSON/YAML) per configurare gli appender del logging")


def _resolve_settings(args) -> Settings:
    """Carica la config centralizzata e applica l'override `--corpus` se presente (D7)."""
    settings = Settings.load()
    if args.corpus:
        settings = dataclasses.replace(settings, corpus=args.corpus)
    return settings


def _check_backend(settings: Settings) -> None:
    """Validazione statica del backend prima di contattare qualunque servizio (FR-015, D3)."""
    missing = settings.validate_backend()
    if missing:
        raise ConfigError(
            f"configurazione backend incompleta: mancano {', '.join(missing)}"
        )


def _cmd_index(args) -> None:
    """Handler di `index`: valida path/backend, costruisce l'indexer e stampa il report."""
    setup_logging(args)
    path = Path(args.path)
    # Check pre-volo della CLI (non duplica logica del core, FR-006/edge case).
    if not path.exists() or not path.is_dir():
        raise IngestionError(
            f"path non valido o non e' una directory: {args.path}", path=str(args.path)
        )
    settings = _resolve_settings(args)
    _check_backend(settings)
    report = build_indexer(settings).index(path, rebuild=True)
    print(output.format_index_report(report, json=args.json))


def _cmd_search(args) -> None:
    """Handler di `search`: via strict per ogni `--type`, poi instrada e formatta (US2)."""
    setup_logging(args)
    if not args.query.strip():
        raise ConfigError("query vuota o solo spazi")
    settings = _resolve_settings(args)
    _check_backend(settings)
    # Via strict per QUALUNQUE --type: indice assente → IndexNotFoundError (FR-012, D6).
    engine = build_baseline_engine(settings)
    engine.ensure_index()
    if args.type == "both":
        # search_combined eredita il fan-out sui corpora extra (fix F13).
        results = build_facade(settings).search_combined(args.query, k=args.k)
    else:
        facade = build_facade(settings)
        results = (
            facade.search_code(args.query, k=args.k)
            if args.type == "code"
            else facade.search_docs(args.query, k=args.k)
        )
    print(output.format_search_results(results, settings, json=args.json, full=args.full))


def main(argv: list[str] | None = None) -> int:
    """Punto d'ingresso del console-script. Ritorna l'exit code (0/1; argparse esce con 2)."""
    # I/O UTF-8 stabile su qualsiasi console (Windows cp1252 non codifica i contenuti del repo).
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):  # stream non riconfigurabile (es. redirezione): ok
            pass

    args = _build_parser().parse_args(argv)
    try:
        args.handler(args)
    except SertorError as exc:
        print(f"errore: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
