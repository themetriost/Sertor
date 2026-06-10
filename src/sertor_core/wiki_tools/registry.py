"""Scritture meccaniche di registro e indice, idempotenti (FR-008, SC-002).

`append_log` appende **una** voce di log nel posto giusto: in modalità **rotazione** (`log_dir`
configurato) la partizione giornaliera della data della voce, altrimenti il file di log unico
(back-compat). Riceve un **corpo curato** opzionale (lead/bullet/esito, formato `log-craft`) e lo
piazza **senza riformattarlo** — il confine deterministico↔giudizio: il codice fa il piazzamento,
l'LLM fornisce il contenuto. `migrate_log` splitta retroattivamente il log monolitico in partizioni.
`upsert_index` inserisce/aggiorna una riga link+sommario nell'indice. Tutto **idempotente**.
L'identità di una voce di log è il suo **heading** (`data + op + titolo`); quella di una pagina, il
suo path relativo POSIX.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

from sertor_core.domain.errors import ConfigError
from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.contracts import AppendLogResult, MigrateResult, UpsertIndexResult
from sertor_core.wiki_tools.profile import WikiProfile

_PARTITION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ENTRY_HEADING = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]")


def _partition_seed(day: date) -> str:
    """Header seed minimo di una partizione giornaliera (file append-only, niente frontmatter)."""
    return f"# Log {day.isoformat()}\n\nVoci di registro del {day.isoformat()}.\n"


def _rel_to_root(profile: WikiProfile, path: Path) -> str:
    """Path relativo POSIX rispetto alla radice del wiki (identità stabile, host-agnostica)."""
    try:
        return path.relative_to(profile.root_path).as_posix()
    except ValueError:
        return path.name


def _target_log(profile: WikiProfile, day: date) -> tuple[Path, bool]:
    """File di destinazione per la data + flag `created`.

    Rotazione: la partizione del giorno, creata col seed se assente (FR-002). File-unico
    (back-compat): il registro `log_path`, che deve già esistere (Principio IV).
    """
    if profile.rotation_enabled:
        path = profile.partition_path(day)
        if path.is_file():
            return path, False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_partition_seed(day), encoding="utf-8")
        return path, True
    path = profile.log_path
    if not path.is_file():
        raise ConfigError("registro del wiki non trovato (inizializzare la struttura)",
                          key=str(path))
    return path, False


def _append_block(path: Path, block: str) -> None:
    """Appende `block` separato dal contenuto precedente da una riga vuota; termina con newline."""
    existing = path.read_text(encoding="utf-8")
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    path.write_text(prefix + block.rstrip() + "\n", encoding="utf-8")


def append_log(
    profile: WikiProfile,
    op: str,
    title: str,
    *,
    on_date: date | None = None,
    body: str | None = None,
) -> AppendLogResult:
    """Appende una voce di log nel file della sua data; ritorna l'esito (`wiki.append_log/1`).

    L'heading è costruito dal `log_format` del profilo; se `body` è dato, il **corpo curato** vi è
    accodato **senza riformattazione**. Idempotente: se una voce con lo stesso heading esiste già
    nel file target, non scrive nulla (SC-002, DA-5).
    """
    day = on_date or date.today()
    heading = profile.log_format.format(date=day.isoformat(), op=op, title=title)
    entry = heading if not body else f"{heading}\n\n{body.strip()}"

    target, created = _target_log(profile, day)
    rel = _rel_to_root(profile, target)
    existing_lines = {
        line.strip() for line in target.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    if heading.strip() in existing_lines:
        log_event(logging.INFO, "registry", profile=profile.profile, target="log",
                  action="noop-duplicate")
        return AppendLogResult(written=False, partition=rel, created=False)

    _append_block(target, entry)
    if created and profile.rotation_enabled:
        update_log_index(profile)
    log_event(logging.INFO, "registry", profile=profile.profile, target="log",
              action="append", partition=rel)
    return AppendLogResult(written=True, partition=rel, created=created)


def update_log_index(profile: WikiProfile) -> bool:
    """Rigenera l'indice delle partizioni (`<log_dir>/<log_index_file>`); idempotente.

    No-op se la rotazione non è attiva o la directory non esiste. Usa link Markdown relativi (non
    wikilink) per non interferire col lint dei wikilink della tassonomia.
    """
    if not profile.rotation_enabled or not profile.log_dir_path.is_dir():
        return False
    days = sorted(p.stem for p in profile.log_dir_path.glob("*.md") if _PARTITION_RE.match(p.stem))
    lines = ["# Indice del log", "", "Partizioni giornaliere (cronologico):", ""]
    lines += [f"- [{d}]({d}.md)" for d in days]
    content = "\n".join(lines) + "\n"

    idx = profile.log_index_path
    if idx.is_file() and idx.read_text(encoding="utf-8") == content:
        return False
    idx.write_text(content, encoding="utf-8")
    log_event(logging.INFO, "registry", profile=profile.profile, target="log-index",
              action="update", days=len(days))
    return True


def migrate_log(profile: WikiProfile) -> MigrateResult:
    """Splitta il log monolitico (`log_path`) in partizioni giornaliere (`wiki.migrate/1`).

    Segmenta per heading datato `## [YYYY-MM-DD] ...`, raggruppa per data, scrive una partizione per
    data distinta (preservando ordine e contenuto). **Idempotente** (data già presente → skip) e
    **non distruttivo** (non cancella il log monolitico). Il preambolo prima della prima voce è
    ignorato. Richiede la rotazione attiva.
    """
    if not profile.rotation_enabled:
        raise ConfigError("rotazione non attiva: configurare `log_dir` prima di migrare",
                          key="log_dir")
    src = profile.log_path
    if not src.is_file():
        return MigrateResult(migrated_entries=0)

    groups: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []

    def _flush() -> None:
        nonlocal buf, current
        if current is not None and buf:
            groups.setdefault(current, []).append("\n".join(buf).rstrip())
        buf = []

    for line in src.read_text(encoding="utf-8").splitlines():
        match = _ENTRY_HEADING.match(line)
        if match:
            _flush()
            current = match.group(1)
            buf = [line]
        elif current is not None:
            buf.append(line)
        # preambolo (frontmatter/intro prima della prima voce): ignorato
    _flush()

    created: list[str] = []
    skipped: list[str] = []
    migrated = 0
    for d_iso in sorted(groups):
        day = date.fromisoformat(d_iso)
        path = profile.partition_path(day)
        if path.is_file():
            skipped.append(path.name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_partition_seed(day) + "\n" + "\n\n".join(groups[d_iso]) + "\n",
                        encoding="utf-8")
        created.append(path.name)
        migrated += len(groups[d_iso])

    if created:
        update_log_index(profile)
    log_event(logging.INFO, "registry", profile=profile.profile, target="log", action="migrate",
              created=len(created), skipped=len(skipped), migrated=migrated)
    return MigrateResult(migrated_entries=migrated, created=created, skipped=skipped)


def upsert_index(profile: WikiProfile, page: str, summary: str) -> UpsertIndexResult:
    """Inserisce/aggiorna la riga d'indice per `page` (id = path relativo); idempotente.

    La riga ha forma `- [[page]] — summary`. Se esiste già una riga per la stessa `page` con lo
    stesso sommario, non scrive (SC-002); se il sommario è cambiato, la riga viene aggiornata.
    Il sommario è **autorato esternamente** e scritto fedelmente (solo trim, FR-014): vuoto o
    multilinea → errore esplicito, nessuna scrittura e nessuna normalizzazione (FR-018).
    """
    summary = summary.strip()
    if not summary:
        raise ConfigError("sommario vuoto: upsert-index richiede una riga di testo non vuota",
                          key=page)
    if "\n" in summary or "\r" in summary:
        raise ConfigError(
            "sommario multilinea: la riga d'indice è una riga singola (fornire il testo su una "
            "riga, nessuna normalizzazione automatica)", key=page,
        )

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
        return UpsertIndexResult(written=False, action="noop", page=page)

    if not replaced:
        out.append(line)

    action = "update" if replaced else "insert"
    index_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    log_event(logging.INFO, "registry", profile=profile.profile, target="index", action=action)
    return UpsertIndexResult(written=True, action=action, page=page)
