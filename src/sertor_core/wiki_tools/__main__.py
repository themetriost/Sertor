"""CLI sottile del nucleo wiki deterministico (research D6, contracts/cli-commands.md).

`python -m sertor_core.wiki_tools <op> --config <path> [--root <override>] [--json]` (equivalente al
console-script `sertor-wiki-tools`). Entry-point **sottile** (Principio I): fa parsing → chiama le
funzioni pure → stampa il contratto JSON o un output umano. Exit code: `0` ok · `1` errore esplicito
(`ConfigError`) con messaggio su stderr e, con `--json`, `wiki.error/1`.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from sertor_core.domain.errors import ConfigError, SertorError
from sertor_core.wiki_tools.collect import collect
from sertor_core.wiki_tools.contracts import ErrorResult
from sertor_core.wiki_tools.lint import lint
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.registry import append_log, migrate_log
from sertor_core.wiki_tools.scan import scan
from sertor_core.wiki_tools.structure import init_structure, validate

_OPS = ("scan", "structure", "validate", "lint", "collect", "index", "append-log", "migrate")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sertor-wiki-tools",
        description="Nucleo wiki deterministico host-agnostico (zero LLM, offline).",
    )
    parser.add_argument("op", choices=_OPS, help="operazione da eseguire")
    parser.add_argument(
        "subcommand", nargs="?", default=None,
        help="sotto-comando (es. 'init' per 'structure')",
    )
    parser.add_argument(
        "--config", default="wiki.config.toml",
        help="percorso del profilo dell'ospite (TOML); default ./wiki.config.toml",
    )
    parser.add_argument(
        "--root", default=None,
        help="override della radice del progetto-ospite (stile Transcriptio --root)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="emette il contratto JSON su stdout (altrimenti output umano sintetico)",
    )
    parser.add_argument(
        "--entry-op", default=None,
        help="operazione della voce di log (per 'append-log': record|lint|distill|...)",
    )
    parser.add_argument(
        "--title", default=None, help="titolo della voce di log (per 'append-log')",
    )
    parser.add_argument(
        "--date", default=None,
        help="data della voce YYYY-MM-DD (per 'append-log'; default: oggi)",
    )
    parser.add_argument(
        "--body-file", default=None,
        help="file col corpo curato della voce (per 'append-log'; altrimenti letto da stdin)",
    )
    return parser


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"data non valida (atteso YYYY-MM-DD): {value}") from exc


def _read_body(args) -> str | None:
    """Corpo curato della voce: da `--body-file`, altrimenti da stdin se non è un terminale."""
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        return data if data.strip() else None
    return None


def _run(args, profile):
    op = args.op
    if op == "scan":
        return scan(profile)
    if op == "lint":
        return lint(profile)
    if op == "validate":
        return validate(profile)
    if op == "collect":
        return collect(profile)
    if op == "structure":
        if args.subcommand not in (None, "init"):
            raise ConfigError(
                f"sotto-comando 'structure {args.subcommand}' non supportato (usa 'init')"
            )
        return init_structure(profile)
    if op == "index":
        from sertor_core.wiki_tools.indexing import index_wiki

        return index_wiki(profile)
    if op == "append-log":
        if not args.entry_op or not args.title:
            raise ConfigError("append-log richiede --entry-op e --title")
        return append_log(
            profile, args.entry_op, args.title,
            on_date=_parse_date(args.date), body=_read_body(args),
        )
    if op == "migrate":
        return migrate_log(profile)
    raise ConfigError(f"operazione non supportata: {op}")  # pragma: no cover


def _human(op: str, result) -> str:
    data = result.to_dict()
    if op == "scan":
        return f"pending={data['pending']} anchor={data['anchor']} :: {data['message']}"
    if op in ("lint", "validate"):
        return (
            f"broken_links={len(data['broken_links'])} orphans={len(data['orphans'])} "
            f"missing_frontmatter={len(data['missing_frontmatter'])} "
            f"naming_violations={len(data['naming_violations'])} "
            f"stubs={len(data.get('stubs', []))}"
        )
    if op == "collect":
        return f"pages={len(data['pages'])} root={data['root']}"
    if op == "structure":
        return f"created={data['created']} skipped_existing={data['skipped_existing']}"
    if op == "index":
        return (
            f"collection={data['collection']} documents={data['documents']} "
            f"regenerated={data['regenerated']}"
        )
    if op == "append-log":
        return (
            f"written={data['written']} partition={data['partition']} created={data['created']}"
        )
    if op == "migrate":
        return (
            f"migrated_entries={data['migrated_entries']} created={len(data['created'])} "
            f"skipped={len(data['skipped'])}"
        )
    return result.to_json()  # pragma: no cover


def main(argv: list[str] | None = None) -> int:
    """Punto d'ingresso del console-script. Ritorna l'exit code."""
    # I/O UTF-8 stabile su QUALSIASI console (es. Windows cp1252 non sa codificare → e i contenuti
    # del wiki contengono caratteri non-ASCII). stdout/stderr per l'output; **stdin** per il corpo
    # curato di `append-log` (altrimenti il body verrebbe decodificato in cp1252 → mojibake).
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):  # stream non riconfigurabile (es. redirezione): ok
            pass

    args = _build_parser().parse_args(argv)
    try:
        profile = load_profile(args.config, root_override=args.root)
        result = _run(args, profile)
    except SertorError as exc:
        error = ErrorResult(error=type(exc).__name__, message=str(exc))
        if args.json:
            print(error.to_json())
        print(f"errore: {exc}", file=sys.stderr)
        return 1

    print(result.to_json() if args.json else _human(args.op, result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
