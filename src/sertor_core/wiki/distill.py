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
from sertor_core.wiki.conventions import (
    Brief,
    WikiArea,
    page_relpath,
    render_page,
    today_str,
)
from sertor_core.wiki.operations import _add_index_entry, _append_log, _one_line, record
from sertor_core.wiki.structure import WikiOpResult

_SYSTEM = (
    "Sei un archivista tecnico. Distilla il brief in una pagina wiki concisa in italiano: "
    "cattura decisioni, concetti ed esiti chiave. Non inventare; usa solo il contenuto fornito."
)

_SYSTEM_DOC = (
    "Sei il documentalista ufficiale del progetto. Distilla la sorgente (artifact SpecKit "
    "o discussione) in una pagina di documentazione ufficiale concisa in italiano: descrivi entità "
    "di business, funzionalità, motivazioni e architettura realizzate nel codice. Non inventare e "
    "non duplicare la sorgente: sintetizza e RIMANDA ad essa. Usa solo il contenuto fornito."
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


def distill_artifact(
    root: Path | str,
    source: str,
    kind: WikiArea | str,
    title: str,
    llm: LLMProvider | None,
    today: str | None = None,
) -> WikiOpResult:
    """Distilla un artifact (spec/plan/requisito/discussione) in documentazione ufficiale.

    Legge la sorgente (path se esiste, altrimenti testo inline), la sintetizza con l'LLM in una
    pagina conforme con **backlink** alla fonte (`sources` + riga di rimando), senza duplicarla.
    **Crea-se-assente**: non sovrascrive una pagina curata a mano (assistita/non distruttiva, DA-3).
    Solleva `LLMNotConfiguredError` se nessun provider è configurato (REQ-065).
    """
    if llm is None:
        raise LLMNotConfiguredError(
            "distillazione documentale non disponibile: configura un provider LLM (REQ-065)"
        )
    root = Path(root)
    today = today or today_str()

    src_path = Path(source)
    material = src_path.read_text(encoding="utf-8") if src_path.exists() else source

    generated = llm.generate(material, system=_SYSTEM_DOC).rstrip("\n")
    body = f"{generated}\n\n> Fonte (dettaglio): [`{source}`]({source})\n"
    brief = Brief(title=title, kind=kind, body=body, tags=["doc"], sources=[source])

    relpath = page_relpath(kind, title)
    page = root / relpath
    if page.exists():
        # Pagina già curata: non sovrascrivere (non distruttivo).
        log_event(logging.INFO, "wiki_distill_artifact", page=relpath, provider=llm.name,
                  changed=False, skipped="exists")
        return WikiOpResult("distill_artifact", page_path=relpath, changed=False,
                            log_appended=False)

    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(render_page(brief, created=today, updated=today), encoding="utf-8")
    _add_index_entry(root, relpath, title, _one_line(generated))
    _append_log(root, "record", title, today)
    log_event(logging.INFO, "wiki_distill_artifact", page=relpath, provider=llm.name, changed=True)
    return WikiOpResult("distill_artifact", page_path=relpath, changed=True, log_appended=True)
