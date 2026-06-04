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
from pathlib import Path


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

# Aree di INPUT (FEAT-010): mai scritte dalla generazione, sono fonti per la compilazione.
MANUAL_EDITED_DIR = "manual_edited"        # input umano, versionato, immutabile (D-1/FR-016)
INGESTED_SOURCES_DIR = "ingested_sources"  # fonti esterne importate (non versionate, FR-022)
# Cartella di stato: esclusa dalla scoperta pagine e dall'indicizzazione.
STATE_DIR = ".sertor"
WATERMARK_FILE = "watermark"             # <root>/.sertor/watermark: SHA dell'ultima generazione

# Aree escluse dalla scoperta delle pagine GENERATE del wiki (input + stato).
NON_PAGE_DIRS: tuple[str, ...] = (MANUAL_EDITED_DIR, INGESTED_SOURCES_DIR, STATE_DIR)

# Provenance di una pagina (D-1/FR-016): generata dall'LLM vs curata a mano.
PROVENANCE_GENERATED = "generated"
PROVENANCE_MANUAL = "manual"
_PROVENANCE_RE = re.compile(r"^provenance:\s*(\S+)\s*$", re.MULTILINE)


def watermark_path(root: Path | str) -> Path:
    """Path del file watermark (`<root>/.sertor/watermark`)."""
    return Path(root) / STATE_DIR / WATERMARK_FILE


def read_watermark(root: Path | str) -> str | None:
    """SHA dell'ultima generazione, o `None` se assente (non distruttivo)."""
    path = watermark_path(root)
    if not path.exists():
        return None
    sha = path.read_text(encoding="utf-8").strip()
    return sha or None


def write_watermark(root: Path | str, sha: str) -> None:
    """Scrive il watermark (crea `.sertor/` se assente; non tocca altro)."""
    path = watermark_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sha.strip() + "\n", encoding="utf-8")


def read_provenance(text: str, *, relpath: str | None = None) -> str:
    """Provenance di una pagina dal frontmatter; default `generated`.

    Le pagine sotto `manual_edited/` sono sempre `manual` (indipendentemente dal frontmatter).
    """
    if relpath is not None and relpath.replace("\\", "/").split("/")[0] == MANUAL_EDITED_DIR:
        return PROVENANCE_MANUAL
    m = _PROVENANCE_RE.search(text)
    return m.group(1) if m else PROVENANCE_GENERATED


def mark_provenance(text: str, value: str) -> str:
    """Imposta/aggiorna il campo `provenance:` nel frontmatter (non distruttivo sul resto).

    Se la pagina ha già un `provenance:`, lo sostituisce; altrimenti lo inserisce nel frontmatter
    (dopo `type:` se presente, altrimenti in cima al blocco). Testo senza frontmatter → invariato
    con il campo prepeso a un nuovo blocco minimale.
    """
    if _PROVENANCE_RE.search(text):
        return _PROVENANCE_RE.sub(f"provenance: {value}", text, count=1)
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            insert_at = text.find("\n", 4) + 1  # dopo la prima riga del frontmatter
            return text[:insert_at] + f"provenance: {value}\n" + text[insert_at:]
    return f"---\nprovenance: {value}\n---\n\n{text}"


_SOURCES_RE = re.compile(r"^sources:\s*\[(.*)\]\s*$", re.MULTILINE)


def _parse_sources(text: str) -> list[str]:
    """Estrae la lista `sources: [a, b, ...]` dal frontmatter (vuota se assente)."""
    m = _SOURCES_RE.search(text)
    if not m:
        return []
    inner = m.group(1).strip()
    if not inner:
        return []
    return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]


def _is_page_path(rel: str) -> bool:
    """True se `rel` è una pagina del wiki GENERATO (esclude aree di input/stato)."""
    top = rel.replace("\\", "/").split("/")[0]
    return top not in NON_PAGE_DIRS


def iter_pages(root: Path | str) -> list[Path]:
    """Pagine Markdown del wiki generato (escluse aree di input/stato), ordinate per path."""
    root = Path(root)
    pages: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if _is_page_path(rel):
            pages.append(path)
    return pages


def entity_page_map(root: Path | str) -> dict[str, set[str]]:
    """Mappa `pattern-codice -> {pagine}` derivata dal frontmatter `sources:` (FR-018/037).

    Per ogni pagina del wiki generato si leggono i `sources:`: ciascuno è un pattern/percorso di
    codice che la pagina documenta. Un path del changeset che combacia con un pattern seleziona le
    pagine da (ri)generare. Nessun indice persistito (derivata al volo).
    """
    root = Path(root)
    mapping: dict[str, set[str]] = {}
    for page in iter_pages(root):
        rel = page.relative_to(root).as_posix()
        text = page.read_text(encoding="utf-8")
        for src in _parse_sources(text):
            mapping.setdefault(src, set()).add(rel)
    return mapping


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
