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
from sertor_core.wiki_tools.registry import append_log, migrate_log, upsert_index
from sertor_core.wiki_tools.scan import scan
from sertor_core.wiki_tools.structure import init_structure, validate

_OPS = ("scan", "structure", "validate", "lint", "collect", "index", "append-log", "migrate",
        "upsert-index", "move", "reconcile")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sertor-wiki-tools",
        description="Host-agnostic deterministic wiki core (zero LLM, offline).",
    )
    parser.add_argument("op", choices=_OPS, help="operation to run")
    parser.add_argument(
        "subcommand", nargs="?", default=None,
        help="subcommand (e.g. 'init' for 'structure') or source page (for 'move')",
    )
    parser.add_argument(
        "dest", nargs="?", default=None,
        help="destination page (for 'move')",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="for 'move': compute the plan without modifying any file",
    )
    parser.add_argument(
        "--config", default=None,
        help="path to the host profile (TOML); if omitted, auto-discovery: "
             "./wiki.config.toml then ./wiki/wiki.config.toml",
    )
    parser.add_argument(
        "--root", default=None,
        help="override of the host project root (Transcriptio-style --root)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="emit the JSON contract on stdout (otherwise a terse human summary)",
    )
    parser.add_argument(
        "--entry-op", default=None,
        help="log entry operation (for 'append-log': record|lint|distill|...)",
    )
    parser.add_argument(
        "--title", default=None, help="log entry title (for 'append-log')",
    )
    parser.add_argument(
        "--date", default=None,
        help="entry date YYYY-MM-DD (for 'append-log'; default: today)",
    )
    parser.add_argument(
        "--body-file", default=None,
        help="file with the curated entry body (for 'append-log'; otherwise read from stdin)",
    )
    parser.add_argument(
        "--page", default=None,
        help="relative path of the page in the wiki (for 'upsert-index')",
    )
    parser.add_argument(
        "--summary", default=None,
        help="index-line summary (for 'upsert-index'; otherwise read from stdin). "
             "The text is author-provided (LLM); the CLI neither generates nor rewrites it",
    )
    return parser


def _resolve_config(config_arg: str | None, root_arg: str | None) -> tuple[str, str | None]:
    """Risolve `--config` (esplicito o auto-discovery) e il `root_override` effettivo (feature 016).

    Se `--config` è esplicito, è usato così com'è (root = `--root` se dato). Altrimenti cerca, in
    ordine, `./wiki.config.toml` (config in radice, retro-compat) e `./wiki/wiki.config.toml` (nuova
    collocazione): nel secondo caso, se `--root` non è dato, il root effettivo è la CWD, così i path
    relativi (`root="wiki"`, `source_dirs`) si risolvono dalla radice ospite. Nessuna trovata →
    `ConfigError` esplicito (Principio IV). Ordine di ricerca generico, nessun path Sertor (P. X).
    """
    if config_arg is not None:
        return config_arg, root_arg
    cwd = Path.cwd()
    if (cwd / "wiki.config.toml").is_file():
        return "wiki.config.toml", root_arg
    if (cwd / "wiki" / "wiki.config.toml").is_file():
        return "wiki/wiki.config.toml", (root_arg if root_arg is not None else ".")
    raise ConfigError(
        "configurazione del wiki non trovata: attese ./wiki.config.toml o "
        "./wiki/wiki.config.toml (oppure indicala con --config)"
    )


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"invalid date (expected YYYY-MM-DD): {value}") from exc


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
                f"subcommand 'structure {args.subcommand}' not supported (use 'init')"
            )
        return init_structure(profile)
    if op == "index":
        from sertor_core.wiki_tools.indexing import index_wiki

        return index_wiki(profile)
    if op == "append-log":
        if not args.entry_op or not args.title:
            raise ConfigError("append-log requires --entry-op and --title")
        return append_log(
            profile, args.entry_op, args.title,
            on_date=_parse_date(args.date), body=_read_body(args),
        )
    if op == "migrate":
        return migrate_log(profile)
    if op == "upsert-index":
        if not args.page:
            raise ConfigError("upsert-index requires --page")
        summary = args.summary if args.summary is not None else _read_body(args)
        if summary is None:
            raise ConfigError("upsert-index requires the summary (--summary or stdin)")
        return upsert_index(profile, args.page, summary)
    if op == "move":
        from sertor_core.wiki_tools.move import move

        if not args.subcommand or not args.dest:
            raise ConfigError("move requires <src> <dest>")
        return move(profile, args.subcommand, args.dest, dry_run=args.dry_run)
    if op == "reconcile":
        from sertor_core.wiki_tools.reconcile import reconcile

        return reconcile(profile)
    raise ConfigError(f"unsupported operation: {op}")  # pragma: no cover


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
    if op == "upsert-index":
        return f"written={data['written']} action={data['action']} page={data['page']}"
    if op == "move":
        occ = sum(r["occurrences"] for r in data["rewritten"])
        return (
            f"moved={data['moved']} dry_run={data['dry_run']} "
            f"rewritten={len(data['rewritten'])} occurrences={occ}"
        )
    if op == "reconcile":
        return f"candidates={len(data['candidates'])} clean={data['clean']}"
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
        config_path, root_override = _resolve_config(args.config, args.root)
        profile = load_profile(config_path, root_override=root_override)
        result = _run(args, profile)
    except SertorError as exc:
        error = ErrorResult(error=type(exc).__name__, message=str(exc))
        if args.json:
            print(error.to_json())
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(result.to_json() if args.json else _human(args.op, result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
