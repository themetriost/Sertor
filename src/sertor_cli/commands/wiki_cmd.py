"""Comando `sertor wiki index <wiki>` — indicizza un wiki nel corpus RAG (REQ-030/031)."""
from __future__ import annotations

from dataclasses import replace

from sertor_cli import output
from sertor_core.config.settings import Settings
from sertor_core.wiki.indexing import index_wiki


def run(args) -> int:
    settings = Settings.load()
    if args.corpus:
        settings = replace(settings, corpus=args.corpus)
    report = index_wiki(args.wiki_path, settings)
    if report.chunks == 0:
        print("Nessuna pagina wiki indicizzata (radice vuota o senza Markdown).")
    else:
        print(output.format_report(report, as_json=args.json))
    return 0
