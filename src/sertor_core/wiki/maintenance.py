"""Manutenzione del wiki (FEAT-007): lint, rigenerazione indice, coperture.

LLM-free e **non distruttivo**: `lint` è sola lettura (salvo `fix=True`, che applica solo il fix
sicuro di rigenerazione indice); `regenerate_index` tocca solo il blocco catalogo tra marcatori.
Riusa le convenzioni di FEAT-003 (DRY). Pensato per girare di frequente come gate (esito pass/fail).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import (
    CATALOG_BEGIN,
    CATALOG_END,
    replace_managed_block,
)

_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_MD_LINK = re.compile(r"\]\(([^)]+)\)")
_HEADING = re.compile(r"^#\s+(.*\S)\s*$", re.MULTILINE)
_TITLE_FM = re.compile(r"^title:\s*(.*\S)\s*$", re.MULTILINE)
# Marcatore esatto scritto dall'ingest di FEAT-003 (`> ⚠️ Contraddizione (fonte ...): ...`).
# Preciso di proposito: una pagina che *parla* di contraddizioni non deve dare un falso positivo.
_CONTRADICTION = "⚠️ Contraddizione (fonte"
_EXEMPT = {"index.md", "log.md"}         # mai orfani per definizione (DA-5)


class IssueKind(StrEnum):
    BROKEN_LINK = "broken_link"
    ORPHAN = "orphan"
    INDEX_MISSING = "index_missing"
    COVERAGE_MISSING = "coverage_missing"
    CONTRADICTION = "contradiction"


@dataclass(frozen=True)
class Issue:
    kind: IssueKind
    page: str
    detail: str = ""


@dataclass
class LintReport:
    issues: list[Issue] = field(default_factory=list)
    pages: int = 0

    @property
    def ok(self) -> bool:
        """Esito pass/fail del gate: pass se non ci sono problemi."""
        return not self.issues

    def render(self) -> str:
        if not self.issues:
            return f"OK — {self.pages} pagine, nessun problema."
        lines = [f"{len(self.issues)} problemi su {self.pages} pagine:"]
        for i in self.issues:
            lines.append(f"  [{i.kind}] {i.page}{(' — ' + i.detail) if i.detail else ''}")
        return "\n".join(lines)


def _pages(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def _summary(text: str) -> str:
    m = _TITLE_FM.search(text) or _HEADING.search(text)
    return m.group(1).strip() if m else ""


def lint(root: Path | str, *, expected: list[str] | None = None, fix: bool = False) -> LintReport:
    """Analizza il wiki e produce un report tipizzato (sola lettura, salvo `fix=True`).

    Rileva: link rotti, pagine orfane, pagine assenti dall'indice, coperture mancanti e
    contraddizioni marcate. Con `fix=True` applica l'unico fix sicuro (rigenera indice).
    """
    root = Path(root)
    if fix:
        regenerate_index(root)

    pages = _pages(root)
    rels = [p.relative_to(root).as_posix() for p in pages]
    stems = {p.stem: p.relative_to(root).as_posix() for p in pages}
    texts = {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8", errors="ignore")
             for p in pages}

    index_text = texts.get("index.md", "")
    index_targets = set(_WIKILINK.findall(index_text)) | {
        Path(m).stem for m in _MD_LINK.findall(index_text)
    }
    referenced: set[str] = set()
    for rel, text in texts.items():
        for tgt in _WIKILINK.findall(text):
            if tgt != Path(rel).stem:        # ignora i self-link
                referenced.add(tgt)

    issues: list[Issue] = []
    # link rotti
    for rel, text in texts.items():
        for tgt in _WIKILINK.findall(text):
            if tgt not in stems:
                issues.append(Issue(IssueKind.BROKEN_LINK, rel, f"[[{tgt}]]"))
    # orfani + indice disallineato + contraddizioni
    for rel in rels:
        stem = Path(rel).stem
        if rel not in _EXEMPT:
            if stem not in referenced and stem not in index_targets:
                issues.append(Issue(IssueKind.ORPHAN, rel))
            if index_text and stem not in index_targets and rel not in index_text:
                issues.append(Issue(IssueKind.INDEX_MISSING, rel))
        if _CONTRADICTION in texts[rel]:
            issues.append(Issue(IssueKind.CONTRADICTION, rel))
    # coperture mancanti
    for exp in expected or []:
        if exp not in rels:
            issues.append(Issue(IssueKind.COVERAGE_MISSING, exp, "documentazione attesa mancante"))

    log_event(logging.INFO, "wiki_lint", root=str(root), pages=len(pages), issues=len(issues),
              ok=not issues)
    return LintReport(issues=issues, pages=len(pages))


def regenerate_index(root: Path | str) -> bool:
    """Rigenera il blocco catalogo di `index.md` (tra marcatori), idempotente e non distruttivo.

    Aggiorna solo la regione gestita; il resto di `index.md` resta intatto. Ritorna True se il file
    è cambiato.
    """
    root = Path(root)
    index = root / "index.md"
    if not index.exists():
        return False
    pages = [p for p in _pages(root)
             if p.relative_to(root).as_posix() not in _EXEMPT]
    lines = []
    for p in pages:
        summary = _summary(p.read_text(encoding="utf-8", errors="ignore"))
        lines.append(f"- [[{p.stem}]]{(' — ' + summary) if summary else ''}")
    catalog = "\n".join(lines) if lines else "_(nessuna pagina)_"

    before = index.read_text(encoding="utf-8")
    after = replace_managed_block(before, CATALOG_BEGIN, CATALOG_END, catalog)
    if after != before:
        index.write_text(after, encoding="utf-8")
        log_event(logging.INFO, "wiki_reindex", root=str(root), pages=len(pages), changed=True)
        return True
    log_event(logging.INFO, "wiki_reindex", root=str(root), pages=len(pages), changed=False)
    return False
