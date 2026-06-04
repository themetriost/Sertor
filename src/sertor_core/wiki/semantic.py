"""Lint semantico del wiki (FEAT-007, Gruppo H): verifica la *sostanza*, non solo la forma.

Confronta le affermazioni del wiki col **codice** (contesto dalla facade di retrieval) e con la
**coerenza interna** tra pagine, a livello di **singola claim**, usando un `LLMProvider`. Rileva:
obsolescenza, contraddizioni semantiche, lacune di copertura, sommari stantii. **Sola lettura**:
`semantic_lint` non scrive; `propose_fixes` produce solo proposte (solo per le pagine *generate*).
Senza LLM degrada **senza errore** (report `skipped`). Riusa le convenzioni e `maintenance._pages`.
"""
from __future__ import annotations

import fnmatch
import json
import logging
import re
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from pathlib import Path

from sertor_core.domain.ports import GitPort, GitScope, LLMProvider
from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import (
    PROVENANCE_GENERATED,
    mark_provenance,
    read_provenance,
    read_watermark,
)
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
    mode: str = "baseline"                # "baseline" | "incremental" (US3, REQ-087/088)
    fallbacks: list[str] = field(default_factory=list)  # degradi segnalati (REQ-091/097)

    @property
    def ok(self) -> bool:
        """Pass se non c'è alcuna issue con severità ≥ soglia (uno skip non fa fallire il gate)."""
        return not any(i.severity >= self.threshold for i in self.issues)

    def render(self) -> str:
        if self.skipped:
            return "Lint semantico saltato (nessun LLM configurato)."
        head = (f"{len(self.issues)} problemi semantici · {self.pages_checked}/{self.pages_total} "
                f"pagine · {self.mode} · {self.llm_calls} chiamate LLM · "
                f"{'OK' if self.ok else 'FAIL'}")
        lines = [head]
        if self.fallbacks:
            lines.append(f"  ⚠ fallback: {', '.join(self.fallbacks)}")
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
    "Sei un revisore di documentazione tecnica, **conservativo**. Confronti UNA pagina wiki con "
    "(a) il CODICE ATTUALE fornito e (b) i SOMMARI di altre pagine. Segnala SOLO problemi che puoi "
    "**dimostrare** con l'evidenza fornita; **nel dubbio NON segnalare** (meglio pochi problemi "
    "certi che molti incerti). Un fatto corretto (percorso, conteggio, nome) che il contesto NON "
    "smentisce NON è un problema. L'assenza di codice rilevante NON implica un errore.\n\n"
    "Tipi (usa il PIÙ specifico, una volta per frase):\n"
    "- obsolete: una frase della pagina è **contraddetta dal CODICE fornito** (il codice mostra il "
    "contrario). Se manca codice rilevante, NON usarlo. evidence = path#chunk del codice.\n"
    "- semantic_contradiction: due affermazioni in **conflitto reale** tra QUESTA pagina e "
    "**un'altra pagina** dei sommari. evidence = path .md dell'ALTRA pagina. Non per il codice.\n"
    "- coverage_gap: un'entità **presente nel codice fornito** non documentata. Solo se il codice "
    "la mostra. claim vuota. evidence = path del codice.\n"
    "- stale_summary: un sommario/indice non riflette più il contenuto reale della pagina.\n\n"
    "Severità high/critical SOLO con evidenza forte e diretta; altrimenti low/medium. Rispondi con "
    "un **array JSON**; campi: kind, claim (frase ESATTA della pagina; vuota per coverage_gap), "
    "severity (info|low|medium|high|critical), detail, evidence. Nessun problema → []."
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


def _is_grounded(issue: SemanticIssue) -> bool:
    """Filtro deterministico anti-rumore: tiene solo le issue **ancorate** a un'evidenza valida.

    Riduce i falsi positivi tipici di un LLM rumoroso: un'`obsolete` deve indicare il **codice** che
    la smentisce; una `semantic_contradiction` deve citare **un'altra pagina** (`.md`), non il
    codice né sé stessa. `coverage_gap`/`stale_summary` passano (gestite dal prompt).
    """
    if issue.kind == SemanticIssueKind.OBSOLETE:
        return bool(issue.evidence)
    if issue.kind == SemanticIssueKind.SEMANTIC_CONTRADICTION:
        return ".md" in issue.evidence and issue.evidence != issue.page
    return True


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
    dropped = 0
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
        parsed = _parse_issues(llm.generate(prompt, system=_SYSTEM), rel)
        kept = [i for i in parsed if _is_grounded(i)]
        dropped += len(parsed) - len(kept)
        issues += kept
        calls += 1

    report = SemanticReport(issues=issues, pages_checked=len(targets), pages_total=total,
                            threshold=threshold, llm_calls=calls, pages_without_code_context=no_ctx)
    log_event(logging.INFO, "semantic_lint", pages_checked=len(targets), pages_total=total,
              issues=len(issues), dropped_ungrounded=dropped, llm_calls=calls, ok=report.ok,
              pages_without_code_context=no_ctx)
    return report


_SOURCES_RE = re.compile(r"^sources:\s*\[(.*?)\]\s*$", re.MULTILINE)


def _parse_sources(text: str) -> list[str]:
    """Estrae i pattern del campo `sources:` dal frontmatter (es. `["src/**", "specs/001/**"]`)."""
    m = _SOURCES_RE.search(text)
    if not m:
        return []
    return [s.strip().strip('"').strip("'") for s in m.group(1).split(",") if s.strip()]


def _entity_page_map(root: Path | str) -> dict[str, set[str]]:
    """Associazione **pattern di codice → pagine** che lo documentano, *derivata* dai `sources:`.

    Nessun indice persistito (Principio III, REQ-090): si legge il frontmatter `sources:` di ogni
    pagina a ogni run. La chiave è il pattern (glob) dichiarato dalla pagina; il valore l'insieme
    delle pagine che lo citano. Un file di codice cambiato seleziona le pagine i cui pattern lo
    intercettano (vedi `_pages_for_changes`).
    """
    root = Path(root)
    out: dict[str, set[str]] = {}
    for p in _pages(root):
        rel = p.relative_to(root).as_posix()
        text = p.read_text(encoding="utf-8", errors="ignore")
        for src in _parse_sources(text):
            out.setdefault(src, set()).add(rel)
    return out


def _pages_for_changes(emap: dict[str, set[str]], changed: list[str]) -> set[str]:
    """Pagine da ri-verificare: quelle il cui pattern `sources:` intercetta un path cambiato."""
    selected: set[str] = set()
    for path in changed:
        for pattern, pages in emap.items():
            # fnmatch: `*` attraversa anche `/`, così `src/sertor_core/**` cattura i file annidati;
            # un pattern senza glob equivale all'uguaglianza esatta.
            if path == pattern or fnmatch.fnmatch(path, pattern):
                selected |= pages
    return selected


def semantic_lint_incremental(
    root: Path | str,
    llm: LLMProvider | None,
    facade=None,
    git: GitPort | None = None,
    *,
    scope: GitScope = "since_watermark",
    watermark_path: str | None = None,  # simmetria col contratto; lo stato vive in .sertor/
    threshold: Severity = Severity.HIGH,
    k_code: int = 5,
    max_pages: int | None = None,
) -> SemanticReport:
    """Verifica semantica **incrementale** git-driven (US3): ri-controlla solo le pagine collegate
    alle entità del change set, ripiegando su baseline completo se manca lo stato (REQ-087..091).

    Riusa `semantic_lint(pages=…)` per la rilevazione (nessuna logica duplicata). Il re-index reale
    del corpus è **inattivo** (FEAT-009 assente): il confronto usa il contesto disponibile e segnala
    `stale-index` (REQ-096/097). A run completato è il **chiamante** a persistere il watermark.
    """
    root = Path(root)
    watermark = read_watermark(root)

    # Senza git utilizzabile o senza baseline pregresso → baseline completo, segnalato (REQ-091).
    head = git.head_commit() if git is not None else None
    if git is None or head is None or watermark is None:
        report = semantic_lint(root, llm, facade, threshold=threshold, k_code=k_code,
                               max_pages=max_pages)
        report.mode = "baseline"
        if not report.skipped:
            reason = "no-git" if (git is None or head is None) else "no-watermark"
            report.fallbacks = [reason, "stale-index"]
        log_event(logging.INFO, "semantic_lint_incremental", mode="baseline",
                  fallbacks=report.fallbacks, pages_checked=report.pages_checked)
        return report

    # Incrementale: change set → mappa entità↔pagine → sottoinsieme di pagine (REQ-088/090).
    changed = git.changed_paths(scope, watermark)
    emap = _entity_page_map(root)
    selected = sorted(_pages_for_changes(emap, changed))

    if not selected:
        # No-op rapido: nessuna pagina collegata alle entità cambiate (REQ-093).
        total = len(_pages(root))
        report = SemanticReport(mode="incremental", pages_total=total, threshold=threshold,
                                fallbacks=["stale-index"])
        log_event(logging.INFO, "semantic_lint_incremental", mode="incremental", no_op=True,
                  changed=len(changed), pages_total=total)
        return report

    report = semantic_lint(root, llm, facade, threshold=threshold, k_code=k_code,
                           max_pages=max_pages, pages=selected)
    report.mode = "incremental"
    # pages_total = pagine del wiki (copertura reale), non solo le selezionate.
    report.pages_total = len(_pages(root))
    if not report.skipped:
        # re-index reale inattivo (FEAT-009 assente, REQ-096/097)
        report.fallbacks = ["stale-index"]
    log_event(logging.INFO, "semantic_lint_incremental", mode="incremental",
              changed=len(changed), selected=len(selected), pages_checked=report.pages_checked)
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


def _detect_newline(path: Path) -> str:
    """Fine-riga dominante del file (`\\r\\n` o `\\n`), per non alterarlo in riscrittura su Win."""
    raw = path.read_bytes()
    return "\r\n" if b"\r\n" in raw else "\n"


def _write_preserving_newline(path: Path, text: str, newline: str) -> None:
    """Scrive `text` (normalizzato a `\\n`) traducendo SOLO al fine-riga originale del file.

    `Path.write_text` su Windows tradurrebbe ogni `\\n` in `\\r\\n`, riscrivendo l'intero file anche
    per una modifica di una riga: qui fissiamo `newline` esplicito così il diff resta chirurgico.
    """
    with open(path, "w", encoding="utf-8", newline=newline) as f:
        f.write(text)


class FixOutcome(StrEnum):
    APPLIED = "applied"                  # claim riscritta sul working tree
    DELETED = "deleted"                  # pagina generata obsoleta rimossa
    REFUSED_CURATED = "refused_curated"  # pagina curata: mai modificata/cancellata (REQ-080)
    SKIPPED_NO_MATCH = "skipped_no_match"  # claim non più presente nel file (non è un errore)


@dataclass(frozen=True)
class FixApplication:
    proposal: FixProposal
    page: str
    outcome: FixOutcome
    detail: str = ""


def apply_fixes(
    proposals: list[FixProposal],
    root: Path | str,
    *,
    dry_run: bool = False,
) -> list[FixApplication]:
    """Applica le proposte sul **working tree**, SOLO su pagine *generate* (US4-scrittura).

    - `rewrite_claim` → sostituzione **chirurgica** della sola claim (preserva il resto e il
      marcatore `generated`); claim non più presente → `skipped_no_match` (REQ-078/079).
    - `delete_page` → rimozione del file (REQ-085).
    - pagina **curated** → `refused_curated`, **nessuna** scrittura/cancellazione (REQ-080).
    - `dry_run=True` → calcola gli esiti senza toccare il filesystem (Principio VI).

    Il diff è minimo e revisionabile via git. Non interattiva (integrabile in hook/CI).
    """
    root = Path(root)
    applications: list[FixApplication] = []
    for prop in proposals:
        page_path = root / prop.page
        if not page_path.exists():
            applications.append(FixApplication(prop, prop.page, FixOutcome.SKIPPED_NO_MATCH,
                                               "pagina assente"))
            continue
        text = page_path.read_text(encoding="utf-8", errors="ignore")
        if read_provenance(text) != PROVENANCE_GENERATED:
            applications.append(FixApplication(prop, prop.page, FixOutcome.REFUSED_CURATED,
                                               "pagina curata a mano: non modificata"))
            continue
        if prop.action == FixAction.DELETE_PAGE:
            if not dry_run:
                page_path.unlink()
            applications.append(FixApplication(prop, prop.page, FixOutcome.DELETED,
                                               "pagina generata obsoleta rimossa"))
            continue
        # rewrite_claim: sostituzione chirurgica della claim esatta.
        claim = prop.issue.claim
        if not claim or claim not in text:
            applications.append(FixApplication(prop, prop.page, FixOutcome.SKIPPED_NO_MATCH,
                                               "claim non trovata nel file"))
            continue
        new_text = text.replace(claim, prop.proposed_text, 1)
        new_text = mark_provenance(new_text, PROVENANCE_GENERATED)  # resta generated (SC-007)
        if not dry_run:
            # preserva il fine-riga del file: niente LF→CRLF a tappeto (diff chirurgico)
            _write_preserving_newline(page_path, new_text, _detect_newline(page_path))
        applications.append(FixApplication(prop, prop.page, FixOutcome.APPLIED, "claim riscritta"))
    log_event(logging.INFO, "semantic_apply_fixes", total=len(applications), dry_run=dry_run,
              applied=sum(1 for a in applications if a.outcome == FixOutcome.APPLIED),
              deleted=sum(1 for a in applications if a.outcome == FixOutcome.DELETED),
              refused=sum(1 for a in applications if a.outcome == FixOutcome.REFUSED_CURATED))
    return applications
