"""Scritture meccaniche di registro e indice, idempotenti (FR-008, SC-002).

`append_log` appende **una** voce nel formato configurato (`log_format`); `upsert_index` inserisce
o aggiorna una riga link+sommario nell'indice. Entrambe sono **idempotenti**: rieseguire su input
invariato non duplica voci né modifica file (confronto set-based, research D7). L'identità stabile
di una pagina è il suo percorso relativo POSIX (FR-009/REQ-051).
"""
from __future__ import annotations

import logging
from datetime import date

from sertor_core.domain.errors import ConfigError
from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.profile import WikiProfile


def append_log(
    profile: WikiProfile,
    op: str,
    title: str,
    *,
    on_date: date | None = None,
) -> bool:
    """Appende una voce di registro se non già presente; ritorna `True` se ha scritto.

    Idempotente: se una riga identica esiste già nel registro, non scrive nulla (nessun duplicato,
    nessun timestamp modificato — SC-002). Il registro deve esistere (init struttura prima).
    """
    log_path = profile.log_path
    if not log_path.is_file():
        raise ConfigError("registro del wiki non trovato (inizializzare la struttura)",
                          key=str(log_path))

    entry_date = (on_date or date.today()).isoformat()
    entry = profile.log_format.format(date=entry_date, op=op, title=title)

    existing = log_path.read_text(encoding="utf-8")
    existing_lines = {line.strip() for line in existing.splitlines() if line.strip()}
    if entry.strip() in existing_lines:
        log_event(logging.INFO, "registry", profile=profile.profile,
                  target="log", action="noop-duplicate")
        return False

    sep = "" if existing.endswith("\n") or not existing else "\n"
    log_path.write_text(f"{existing}{sep}{entry}\n", encoding="utf-8")
    log_event(logging.INFO, "registry", profile=profile.profile, target="log", action="append")
    return True


def upsert_index(profile: WikiProfile, page: str, summary: str) -> bool:
    """Inserisce/aggiorna la riga d'indice per `page` (id = path relativo); idempotente.

    La riga ha forma `- [[page]] — summary`. Se esiste già una riga per la stessa `page` con lo
    stesso sommario, non scrive (SC-002); se il sommario è cambiato, la riga viene aggiornata.
    """
    index_path = profile.index_path
    if not index_path.is_file():
        raise ConfigError("indice del wiki non trovato (inizializzare la struttura)",
                          key=str(index_path))

    line = f"- [[{page}]] — {summary}"
    existing = index_path.read_text(encoding="utf-8")
    lines = existing.splitlines()

    marker = f"[[{page}]]"
    out: list[str] = []
    replaced = False
    already = False
    for current in lines:
        if marker in current:
            if current.strip() == line.strip():
                already = True
                out.append(current)
            else:
                out.append(line)
                replaced = True
        else:
            out.append(current)

    if already:
        log_event(logging.INFO, "registry", profile=profile.profile,
                  target="index", action="noop-duplicate")
        return False

    if not replaced:
        out.append(line)

    index_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    log_event(logging.INFO, "registry", profile=profile.profile, target="index",
              action="update" if replaced else "insert")
    return True
