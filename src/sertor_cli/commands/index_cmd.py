"""Comando `sertor index <path>` — indicizza un repository riusando il core (REQ-010..014)."""
from __future__ import annotations

from dataclasses import replace

from sertor_cli import output
from sertor_core.composition import build_indexer
from sertor_core.config.settings import Settings


def run(args) -> int:
    settings = Settings.load()
    if args.corpus:
        settings = replace(settings, corpus=args.corpus)
    indexer = build_indexer(settings)
    report = indexer.index(args.path, rebuild=True)  # full rebuild idempotente
    print(output.format_report(report, as_json=args.json))
    return 0
