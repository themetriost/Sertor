"""Lint semantico del wiki (FEAT-007, Gruppo H): verifica la *sostanza*, non solo la forma.

Confronta le affermazioni del wiki col **codice** (contesto dalla facade di retrieval) e con la
**coerenza interna** tra pagine, a livello di **singola claim**, usando un `LLMProvider`. Rileva:
obsolescenza, contraddizioni semantiche, lacune di copertura, sommari stantii. **Sola lettura**:
`semantic_lint` non scrive; `propose_fixes` produce solo proposte (solo per le pagine *generate*).
Senza LLM degrada **senza errore** (report `skipped`). Riusa le convenzioni e `maintenance._pages`.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from pathlib import Path

from sertor_core.domain.ports import LLMProvider
from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import PROVENANCE_GENERATED, read_provenance
from sertor_core.wiki.maintenance import _pages, _summary


class Severity(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


_SEVERITY_BY_NAME = {s.name.lower(): s for s in Severity}


class SemanticIssueKind(StrEnum):
    OBSOLETE = "obsolete"
    SEMANTIC_CONTRADICTION = "semantic_contradiction"
    COVERAGE_GAP = "coverage_gap"
    STALE_SUMMARY = "stale_summary"


_KIND_BY_NAME = {k.value: k for k in SemanticIssueKind}


@dataclass(frozen=True)
class SemanticIssue:
    kind: SemanticIssueKind
    page: str
    claim: str = ""
    severity: Severity = Severity.MEDIUM
    detail: str = ""
    evidence: str = ""


class FixAction(StrEnum):
    REWRITE_CLAIM = "rewrite_claim"
    DELETE_PAGE = "delete_page"


@dataclass(frozen=True)
class FixProposal:
    issue: SemanticIssue
    page: str
    action: FixAction
    proposed_text: str = ""
    rationale: str = ""


@dataclass
class SemanticReport:
    issues: list[SemanticIssue] = field(default_factory=list)
    pages_checked: int = 0
    pages_total: int = 0
    skipped: bool = False
    threshold: Severity = Severity.HIGH
    llm_calls: int = 0
    pages_without_code_context: int = 0   # pagine verificate senza contesto codice (REQ-083/097)

    @property
    def ok(self) -> bool:
        """Pass se non c'è alcuna issue con severità ≥ soglia (uno skip non fa fallire il gate)."""
        return not any(i.severity >= self.threshold for i in self.issues)

    def render(self) -> str:
        if self.skipped:
            return "Lint semantico saltato (nessun LLM configurato)."
        head = (f"{len(self.issues)} problemi semantici · {self.pages_checked}/{self.pages_total} "
                f"pagine · {self.llm_calls} chiamate LLM · {'OK' if self.ok else 'FAIL'}")
        lines = [head]
        if self.pages_without_code_context:
            lines.append(
                f"  ⚠ contesto codice assente per {self.pages_without_code_context}/"
                f"{self.pages_checked} pagine: il controllo di obsolescenza vs codice è PARZIALE."
            )
        for i in sorted(self.issues, key=lambda x: x.severity, reverse=True):
            claim = f' — "{i.claim[:80]}"' if i.claim else ""
            lines.append(f"  [{i.severity.name}] {i.kind} {i.page}{claim}")
        return "\n".join(lines)


_SYSTEM = (
    "Sei un revisore della documentazione tecnica. Confronti una PAGINA WIKI con il CODICE ATTUALE "
    "e con i SOMMARI delle altre pagine, per trovare SOLO problemi reali. Rispondi con un **array "
    "JSON**; ogni elemento ha i campi: kind (obsolete|semantic_contradiction|coverage_gap|"
    "stale_summary), claim (la frase ESATTA della pagina interessata; vuota per coverage_gap), "
    "severity (info|low|medium|high|critical), detail (spiegazione breve), evidence (path del "
    "codice o pagina). Se non ci sono problemi rispondi []. Non inventare: usa solo il contesto."
)


def _page_query(text: str) -> str:
    title = _summary(text)
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("---") and ":" not in s[:12]:
            return f"{title} {s}"[:300]
    return title


def _code_context(facade, query: str, k: int) -> tuple[str, list[str]]:
    if facade is None:
        return "", []
    try:
        hits = facade.search_code(query, k=k)
    except Exception as exc:  # il contesto è best-effort: un fallimento non rompe il lint
        log_event(logging.WARNING, "semantic_context_error", error=str(exc))
        return "", []
    blocks, refs = [], []
    for h in hits:
        ref = f"{h.path}#{h.chunk_id}"
        refs.append(ref)
        blocks.append(f"// {ref}\n{h.text}")
    return "\n\n".join(blocks), refs


def _parse_issues(raw: str, page: str) -> list[SemanticIssue]:
    """Parsing difensivo dell'output LLM: estrae l'array JSON, salta le voci malformate (log)."""
    text = raw.strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        log_event(logging.WARNING, "semantic_parse_skip", page=page, reason="no_json_array")
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        log_event(logging.WARNING, "semantic_parse_skip", page=page, reason="invalid_json")
        return []
    out: list[SemanticIssue] = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        kind = _KIND_BY_NAME.get(str(item.get("kind", "")).strip())
        if kind is None:
            continue  # voce malformata: saltata
        sev = _SEVERITY_BY_NAME.get(str(item.get("severity", "")).strip().lower(), Severity.MEDIUM)
        out.append(SemanticIssue(
            kind=kind,
            page=page,
            claim=str(item.get("claim", "")).strip(),
            severity=sev,
            detail=str(item.get("detail", "")).strip(),
            evidence=str(item.get("evidence", "")).strip(),
        ))
    return out


def _index_summaries(root: Path, rels: list[str]) -> str:
    lines = []
    for rel in rels:
        text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        s = _summary(text)
        if s:
            lines.append(f"- {rel}: {s}")
    return "\n".join(lines)


def semantic_lint(
    root: Path | str,
    llm: LLMProvider | None,
    facade=None,
    *,
    threshold: Severity = Severity.HIGH,
    k_code: int = 5,
    max_pages: int | None = None,
    pages: list[str] | None = None,
) -> SemanticReport:
    """Verifica semantica per-claim del wiki contro il codice e la coerenza interna (Gruppo H).

    Sola lettura. Senza LLM ritorna un report `skipped` (degrado senza errore, REQ-081). `max_pages`
    limita il costo riportando la copertura (REQ-083). `pages` permette di mirare un sottoinsieme.
    """
    root = Path(root)
    if pages is not None:
        all_rels = pages
    else:
        all_rels = [p.relative_to(root).as_posix() for p in _pages(root)]
    total = len(all_rels)
    if llm is None:
        log_event(logging.INFO, "semantic_lint", skipped=True, pages_total=total)
        return SemanticReport(skipped=True, pages_total=total, threshold=threshold)

    targets = all_rels[:max_pages] if max_pages is not None else all_rels
    summaries = _index_summaries(root, all_rels)
    issues: list[SemanticIssue] = []
    calls = 0
    no_ctx = 0
    for rel in targets:
        text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        code_ctx, _ = _code_context(facade, _page_query(text), k_code)
        if not code_ctx:
            no_ctx += 1
        prompt = (
            f"PAGINA WIKI ({rel}):\n{text}\n\n"
            f"CODICE ATTUALE (estratti rilevanti):\n{code_ctx or '(nessun contesto)'}\n\n"
            f"SOMMARI DELLE ALTRE PAGINE:\n{summaries}\n\n"
            "Restituisci l'array JSON dei problemi (vedi istruzioni di sistema)."
        )
        issues += _parse_issues(llm.generate(prompt, system=_SYSTEM), rel)
        calls += 1

    report = SemanticReport(issues=issues, pages_checked=len(targets), pages_total=total,
                            threshold=threshold, llm_calls=calls, pages_without_code_context=no_ctx)
    log_event(logging.INFO, "semantic_lint", pages_checked=len(targets), pages_total=total,
              issues=len(issues), llm_calls=calls, ok=report.ok, pages_without_code_context=no_ctx)
    return report


_FIX_SYSTEM = (
    "Sei un documentalista. Ti viene data una FRASE obsoleta/errata di una pagina wiki e il CODICE "
    "ATTUALE. Riscrivi SOLO quella frase in modo corretto e conciso, senza aggiungere altro. "
    "Restituisci esclusivamente la frase riscritta."
)


def propose_fixes(report: SemanticReport, root: Path | str, llm: LLMProvider) -> list[FixProposal]:
    """Proposte di correzione per le issue su pagine **generate** (REQ-078/080/085). Non scrive.

    Per le issue con una claim → proposta di **riscrittura chirurgica**; per un'obsolescenza senza
    claim (pagina interamente obsoleta) → proposta di **cancellazione**. Le pagine **curate** sono
    saltate (solo segnalazione tramite l'issue originale).
    """
    root = Path(root)
    proposals: list[FixProposal] = []
    prov_cache: dict[str, str] = {}
    for issue in report.issues:
        page = root / issue.page
        if not page.exists():
            continue
        prov = prov_cache.get(issue.page)
        if prov is None:
            prov = read_provenance(page.read_text(encoding="utf-8", errors="ignore"))
            prov_cache[issue.page] = prov
        if prov != PROVENANCE_GENERATED:
            continue  # pagina curata a mano: solo proposta-zero (segnalata dall'issue)
        if not issue.claim and issue.kind == SemanticIssueKind.OBSOLETE:
            proposals.append(FixProposal(issue=issue, page=issue.page, action=FixAction.DELETE_PAGE,
                                         rationale=issue.detail or "pagina obsoleta"))
            continue
        prompt = f"FRASE:\n{issue.claim}\n\nMOTIVO:\n{issue.detail}\n\nEVIDENZA:\n{issue.evidence}"
        proposed = llm.generate(prompt, system=_FIX_SYSTEM).strip()
        proposals.append(FixProposal(issue=issue, page=issue.page, action=FixAction.REWRITE_CLAIM,
                                     proposed_text=proposed, rationale=issue.detail))
    log_event(logging.INFO, "semantic_propose_fixes", proposals=len(proposals))
    return proposals
