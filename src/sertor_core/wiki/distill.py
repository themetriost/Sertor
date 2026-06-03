"""Distillazione di una conversazione/sessione in una pagina wiki (REQ-030..033).

Richiede un `LLMProvider` configurato (REQ-031): senza, l'operazione è bloccata con un errore
esplicito. L'input è un brief **già condensato** (non una trascrizione grezza, DA-W3). La pagina
prodotta segue le stesse convenzioni di tutte le altre (frontmatter, wikilink, kebab-case, tema).
"""
from __future__ import annotations

import logging
from pathlib import Path

from sertor_core.domain.errors import LLMNotConfiguredError
from sertor_core.domain.ports import LLMProvider
from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import Brief, today_str
from sertor_core.wiki.operations import record
from sertor_core.wiki.structure import WikiOpResult

_SYSTEM = (
    "Sei un archivista tecnico. Distilla il brief in una pagina wiki concisa in italiano: "
    "cattura decisioni, concetti ed esiti chiave. Non inventare; usa solo il contenuto fornito."
)


def distill(
    root: Path | str,
    brief: Brief,
    llm: LLMProvider | None,
    today: str | None = None,
) -> WikiOpResult:
    """Genera una pagina distillata dal brief usando l'LLM, poi la registra come record.

    `brief.body` è il brief condensato in input; il corpo della pagina è il testo generato dall'LLM.
    Solleva `LLMNotConfiguredError` se nessun provider è configurato (REQ-031).
    """
    if llm is None:
        raise LLMNotConfiguredError(
            "distillazione non disponibile: configura un provider LLM (REQ-031)"
        )
    today = today or today_str()
    generated = llm.generate(brief.body, system=_SYSTEM)
    page_brief = Brief(
        title=brief.title,
        kind=brief.kind,
        body=generated,
        tags=brief.tags,
        sources=brief.sources,
    )
    # La distillazione registra come 'record' (REQ-032) e riusa la logica idempotente di record.
    result = record(root, page_brief, today=today)
    log_event(logging.INFO, "wiki_distill", page=result.page_path, provider=llm.name,
              changed=result.changed)
    return WikiOpResult("distill", page_path=result.page_path, changed=result.changed,
                        log_appended=result.log_appended)
