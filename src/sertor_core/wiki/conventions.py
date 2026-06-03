"""Convenzioni del wiki: struttura, frontmatter, naming, formato del log (REQ-003/004/005).

Definisce i contratti formali condivisi da tutte le operazioni: aree tematiche → cartelle, brief di
input, rendering deterministico di frontmatter e pagine, voce di log append-only. Il rendering è
deterministico (stessi input → stesso output) per abilitare l'idempotenza strutturale (REQ-050).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class WikiArea(StrEnum):
    """Aree tematiche del wiki (determinano la sottocartella)."""

    CONCEPT = "concept"
    TECH = "tech"
    EXPERIMENT = "experiment"
    SOURCE = "source"
    SYNTHESIS = "synthesis"


_AREA_DIR: dict[WikiArea, str] = {
    WikiArea.CONCEPT: "concepts",
    WikiArea.TECH: "tech",
    WikiArea.EXPERIMENT: "experiments",
    WikiArea.SOURCE: "sources",
    WikiArea.SYNTHESIS: "syntheses",
}
THEMATIC_DIRS: tuple[str, ...] = tuple(_AREA_DIR.values())
LOG_OPS = ("setup", "record", "ingest", "query", "lint")


@dataclass
class Brief:
    """Input strutturato per record/distill (prodotto dall'agente chiamante, DA-W2)."""

    title: str
    kind: WikiArea | str
    body: str
    tags: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


@dataclass
class SourceBrief:
    """Input strutturato per ingest di una fonte esterna."""

    title: str
    summary: str
    reference: str = ""
    # related: pagine a cui propagare il riferimento; contradicts: (pagina, nota)
    related: list[str] = field(default_factory=list)
    contradicts: list[tuple[str, str]] = field(default_factory=list)


def today_str() -> str:
    """Data odierna in formato YYYY-MM-DD."""
    return date.today().isoformat()


def slugify(title: str) -> str:
    """Nome file kebab-case da un titolo (REQ-005)."""
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "pagina"


def area_dir(kind: WikiArea | str) -> str:
    """Sottocartella tematica per un'area."""
    return _AREA_DIR[WikiArea(kind)]


def page_relpath(kind: WikiArea | str, title: str) -> str:
    """Path relativo (POSIX) della pagina nella sottocartella corretta."""
    return f"{area_dir(kind)}/{slugify(title)}.md"


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]"


def render_frontmatter(
    *, title: str, type: str, tags: list[str], created: str, updated: str, sources: list[str]
) -> str:
    """Blocco frontmatter YAML con i campi obbligatori (REQ-003), ordine stabile."""
    return (
        "---\n"
        f"title: {title}\n"
        f"type: {type}\n"
        f"tags: {_yaml_list(tags)}\n"
        f"created: {created}\n"
        f"updated: {updated}\n"
        f"sources: {_yaml_list(sources)}\n"
        "---\n"
    )


def render_page(brief: Brief, *, created: str, updated: str) -> str:
    """Pagina completa: frontmatter + corpo. Deterministico a parità di input."""
    fm = render_frontmatter(
        title=brief.title,
        type=str(WikiArea(brief.kind)),
        tags=brief.tags,
        created=created,
        updated=updated,
        sources=brief.sources,
    )
    body = brief.body.rstrip("\n")
    return f"{fm}\n# {brief.title}\n\n{body}\n"


def log_entry(date_str: str, operation: str, title: str) -> str:
    """Voce di log append-only: `## [YYYY-MM-DD] <operazione> | <titolo>` (REQ-012)."""
    return f"## [{date_str}] {operation} | {title}\n"


_CREATED_RE = re.compile(r"^created:\s*(\S+)\s*$", re.MULTILINE)


def parse_created(existing_text: str) -> str | None:
    """Estrae il campo `created` dal frontmatter di una pagina esistente (per preservarlo)."""
    m = _CREATED_RE.search(existing_text)
    return m.group(1) if m else None
