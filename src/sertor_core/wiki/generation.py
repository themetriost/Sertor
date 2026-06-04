"""Generazione del wiki (momento a): l'LLM aggiorna il corpo delle pagine generate (FEAT-010).

Due regimi:
- **baseline** — senza git/watermark: target = tutte le pagine generate (rigenerazione larga).
- **incremental** — con git+watermark: dal changeset si selezionano, via `entity_page_map`, le sole
  pagine collegate (FR-018/037); changeset irrilevante → no-op rapido.

Invarianti (Principio VI): `manual_edited/` e `ingested_sources/` sono **input** (leggibili come
contesto, mai scritti); il frontmatter è preservato (si riscrive solo il corpo); l'idempotenza è
strutturale (stesso input → stesso esito; corpo invariato → nessuna scrittura). Il re-index
incrementale reale è FEAT-009: finché assente, si segnala il fallback `stale-index` (Principio IV).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sertor_core.domain.ports import GitPort, GitScope, LLMProvider
from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import (
    entity_page_map,
    iter_pages,
    read_watermark,
    today_str,
)

_NON_TARGET_FILES = ("index.md", "log.md")

_SYSTEM = (
    "Sei un curatore di wiki tecnico. Aggiorni il CORPO (markdown, senza frontmatter) di una "
    "pagina mantenendola accurata e concisa. Non inventare. Restituisci solo il corpo aggiornato."
)


@dataclass
class GenerationReport:
    """Esito della generazione (osservabilità + idempotenza verificabile)."""

    mode: str = "baseline"
    pages_written: int = 0
    pages_total: int = 0
    llm_calls: int = 0
    fallbacks: list[str] = field(default_factory=list)


def _split_page(text: str) -> tuple[str, str]:
    """Separa (frontmatter_incluso_intestazione, corpo) di una pagina.

    Una pagina è `---\\n...frontmatter...\\n---\\n\\n# Titolo\\n\\n<corpo>\\n`. Si conserva tutto
    fino alla riga di intestazione `# ...` inclusa (la "testa"); il resto è il corpo. Senza
    frontmatter/intestazione riconoscibili, la testa è vuota e tutto è corpo.
    """
    lines = text.splitlines(keepends=True)
    # Salta il blocco frontmatter, se presente.
    idx = 0
    if lines and lines[0].startswith("---"):
        for i in range(1, len(lines)):
            if lines[i].startswith("---"):
                idx = i + 1
                break
    # Trova la prima intestazione `# ...` dopo il frontmatter.
    head_end = idx
    for i in range(idx, len(lines)):
        if lines[i].lstrip().startswith("# "):
            head_end = i + 1
            break
    else:
        head_end = idx
    head = "".join(lines[:head_end])
    body = "".join(lines[head_end:])
    return head, body.lstrip("\n").rstrip("\n")


def _targets(root: Path) -> list[Path]:
    """Pagine del wiki generato candidate alla rigenerazione (esclusi index/log e aree input)."""
    return [p for p in iter_pages(root) if p.name not in _NON_TARGET_FILES]


def _select_incremental(root: Path, changed: list[str]) -> list[Path]:
    """Pagine collegate al changeset via `entity_page_map` (frontmatter `sources:`)."""
    mapping = entity_page_map(root)
    selected: set[str] = set()
    for src, pages in mapping.items():
        for path in changed:
            norm = path.replace("\\", "/")
            if norm == src or norm.endswith(src) or norm.startswith(src):
                selected.update(pages)
    return [root / rel for rel in sorted(selected)]


def _regenerate_page(path: Path, llm: LLMProvider, today: str) -> bool:
    """Chiede all'LLM un corpo aggiornato; riscrive SOLO il corpo se cambia. True se scritto."""
    text = path.read_text(encoding="utf-8")
    head, body = _split_page(text)
    prompt = (
        f"Aggiorna il corpo della seguente pagina di wiki, restando fedele ai contenuti.\n\n"
        f"--- CORPO ATTUALE ---\n{body}\n"
    )
    new_body = llm.generate(prompt, system=_SYSTEM).strip("\n")
    if new_body == body:
        return False  # idempotenza: nessuna modifica reale
    new_text = head.rstrip("\n") + "\n\n" + new_body + "\n"
    path.write_text(new_text, encoding="utf-8")
    return True


def generate(
    root: Path | str,
    llm: LLMProvider,
    *,
    sources: list[str] | None = None,
    git: GitPort | None = None,
    scope: GitScope = "since_watermark",
    facade=None,
    max_pages: int | None = None,
) -> GenerationReport:
    """Genera/aggiorna le pagine del wiki (baseline o incrementale). Vedi il contratto FEAT-010.

    `manual_edited/`/`ingested_sources/` sono input: mai scritti. Il re-index incrementale reale è
    FEAT-009: si segnala `stale-index` finché assente.
    """
    root = Path(root)
    today = today_str()
    watermark = read_watermark(root)
    head = git.head_commit() if git is not None else None

    incremental = git is not None and head is not None and watermark is not None
    report = GenerationReport(mode="incremental" if incremental else "baseline")
    # FEAT-009 (re-index incrementale reale) assente: fallback esplicito (Principio IV).
    report.fallbacks.append("stale-index")

    if incremental:
        changed = git.changed_paths(scope, watermark)
        targets = _select_incremental(root, changed)
        if not targets:  # changeset irrilevante: no-op rapido
            log_event(logging.INFO, "wiki_generate", mode=report.mode, status="no-op",
                      changed=len(changed))
            report.pages_total = 0
            return report
    else:
        targets = _targets(root)

    if max_pages is not None:
        targets = targets[:max_pages]
    report.pages_total = len(targets)

    for path in targets:
        if not path.exists():
            continue
        report.llm_calls += 1
        if _regenerate_page(path, llm, today):
            report.pages_written += 1

    log_event(logging.INFO, "wiki_generate", mode=report.mode,
              pages_written=report.pages_written, pages_total=report.pages_total,
              llm_calls=report.llm_calls)
    return report
