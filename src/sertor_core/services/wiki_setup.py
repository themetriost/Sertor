"""Setup del wiki (confine, US1): struttura + binding del trigger + ingest iniziale (FEAT-010).

`init_wiki` vive al **confine** (services), non nel dominio né nel config-manager (Principio I/VII):
riusa `create_wiki` per la struttura (Principio III) e installa il **binding del trigger** tramite
un'astrazione semplice (`install_trigger_binding`) — un marcatore di stato che rappresenta
l'aggancio del momento "commit". Idempotente e non-distruttivo (Principio VI).
"""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import INGESTED_SOURCES_DIR, STATE_DIR
from sertor_core.wiki.structure import create_wiki

_TRIGGER_FILE = "trigger"  # <root>/.sertor/trigger: marcatore del binding installato


@dataclass
class SetupReport:
    """Esito del setup del wiki (osservabilità + idempotenza verificabile)."""

    created: bool = False
    binding_installed: bool = False
    ingested: int = 0


def trigger_binding_path(root: Path | str) -> Path:
    """Path del marcatore del binding del trigger (`<root>/.sertor/trigger`)."""
    return Path(root) / STATE_DIR / _TRIGGER_FILE


def install_trigger_binding(root: Path | str) -> bool:
    """Installa il binding del trigger del commit (astrazione, default = marcatore di stato).

    Rappresenta l'aggancio "commit → generazione/gate". Il binding concreto per un client (es.
    hook/configuration-manager di Claude Code) è installato fuori da qui; questo default scrive un
    marcatore client-agnostico così il setup è verificabile e idempotente (D-8/FR-028). Ritorna
    True se ha scritto il marcatore (assente prima), False se già presente (no-op).
    """
    path = trigger_binding_path(root)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("commit-trigger: installed\n", encoding="utf-8")
    return True


def _initial_ingest(root: Path, initial_ingest: Path | str) -> int:
    """Copia una fonte iniziale in `ingested_sources/` (import, non compile). Conta i file."""
    src = Path(initial_ingest)
    dest_dir = root / INGESTED_SOURCES_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return 0
    if src.is_file():
        shutil.copy2(src, dest_dir / src.name)
        return 1
    count = 0
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src)
        target = dest_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
    return count


def init_wiki(
    root: Path | str,
    *,
    install_binding: bool = True,
    initial_ingest: Path | str | None = None,
) -> SetupReport:
    """Inizializza il wiki: struttura + binding del trigger + ingest iniziale opzionale.

    Idempotente: rieseguito su un wiki esistente non sovrascrive struttura/binding. Riusa
    `create_wiki` (Principio III).
    """
    root = Path(root)
    create_result = create_wiki(root)
    report = SetupReport(created=create_result.changed)

    if install_binding:
        report.binding_installed = install_trigger_binding(root)

    if initial_ingest is not None:
        report.ingested = _initial_ingest(root, initial_ingest)

    log_event(logging.INFO, "wiki_init", root=str(root), created=report.created,
              binding_installed=report.binding_installed, ingested=report.ingested)
    return report
