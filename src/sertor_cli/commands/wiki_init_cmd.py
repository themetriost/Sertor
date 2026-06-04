"""Comando `sertor wiki init <root> [--ingest <path>]` — setup del wiki (FEAT-010, US1).

Layer sottile: delega al servizio di confine `init_wiki` (struttura + binding + ingest iniziale).
"""
from __future__ import annotations

from sertor_core.services.wiki_setup import init_wiki


def run(args) -> int:
    report = init_wiki(args.root, install_binding=True, initial_ingest=args.ingest)
    status = "creata" if report.created else "già presente"
    binding = "installato" if report.binding_installed else "già presente"
    print(f"Wiki '{args.root}': struttura {status}, binding del trigger {binding}.")
    if args.ingest:
        print(f"Ingest iniziale: {report.ingested} file in ingested_sources/.")
    return 0
