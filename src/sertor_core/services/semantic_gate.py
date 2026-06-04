"""Gate pre-commit/pre-push del lint semantico (FEAT-007, US5) — **fuori dal dominio wiki**.

Orchestrazione di confine: esegue il lint **incrementale**, applica le correzioni alle pagine
**generate**, e mappa l'esito a uno `status` (`pass|warning|blocked`) consumabile come gate
(l'exit code lo decide il layer CLI). Il dominio (`wiki/semantic.py`) resta una libreria che NON
conosce git né exit code (Principio I); qui si compongono porta git + LLM + facade. È il **trigger a
monte** del configuration-manager (REQ-092): le correzioni alle pagine generate finiscono nello
stesso commit imminente.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from sertor_core.domain.ports import GitPort, GitScope, LLMProvider
from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import write_watermark
from sertor_core.wiki.semantic import (
    FixApplication,
    FixOutcome,
    SemanticReport,
    Severity,
    apply_fixes,
    propose_fixes,
    semantic_lint_incremental,
)


class GateStatus(StrEnum):
    PASS = "pass"        # nessuna issue aperta ≥ soglia → l'operazione procede
    WARNING = "warning"  # issue aperte sotto soglia → procede con avviso
    BLOCKED = "blocked"  # issue aperte ≥ soglia → l'operazione va bloccata (exit ≠ 0)


@dataclass
class GateOutcome:
    status: GateStatus
    report: SemanticReport
    applied: list[FixApplication] = field(default_factory=list)
    override: bool = False
    override_record: str | None = None


def _remaining_issues(report: SemanticReport, applied: list[FixApplication]) -> list:
    """Issue ancora aperte dopo l'auto-fix: quelle non risolte da un'applicazione/cancellazione."""
    resolved = {
        id(a.proposal.issue)
        for a in applied
        if a.outcome in (FixOutcome.APPLIED, FixOutcome.DELETED)
    }
    return [i for i in report.issues if id(i) not in resolved]


def run_semantic_gate(
    root: Path | str,
    llm: LLMProvider | None,
    facade=None,
    git: GitPort | None = None,
    *,
    scope: GitScope = "since_watermark",
    threshold: Severity = Severity.HIGH,
    override: bool = False,
    override_reason: str | None = None,
    persist_watermark: bool = False,
) -> GateOutcome:
    """Esegue il gate: incrementale → auto-fix su generate → valutazione soglia (REQ-092..095).

    `override=True` fa procedere anche con issue bloccanti, **registrando** l'override (escape hatch
    tracciato, non un bypass silenzioso, REQ-095). Con `persist_watermark=True` aggiorna il
    watermark a fine run riuscito (delegato al chiamante, per non legarlo alla policy di commit).
    """
    root = Path(root)
    report = semantic_lint_incremental(root, llm, facade, git, scope=scope, threshold=threshold)

    # Senza LLM (semantico saltato) o senza issue: nessun auto-fix, gate passa.
    applied: list[FixApplication] = []
    if not report.skipped and report.issues and llm is not None:
        proposals = propose_fixes(report, root, llm)
        applied = apply_fixes(proposals, root)

    remaining = _remaining_issues(report, applied)
    blocking = any(i.severity >= threshold for i in remaining)

    override_record: str | None = None
    n_blocking = sum(1 for i in remaining if i.severity >= threshold)
    if blocking and override:
        status = GateStatus.PASS
        override_record = (f"override: {override_reason or 'non specificato'} "
                           f"({n_blocking} issue bloccanti)")
        log_event(logging.WARNING, "semantic_gate_override", reason=override_reason,
                  blocking=n_blocking)
    elif blocking:
        status = GateStatus.BLOCKED
    elif remaining:
        status = GateStatus.WARNING
    else:
        status = GateStatus.PASS

    if persist_watermark and status != GateStatus.BLOCKED and git is not None:
        head = git.head_commit()
        if head:
            write_watermark(root, head)

    log_event(logging.INFO, "semantic_gate", status=str(status), mode=report.mode,
              issues=len(report.issues), remaining=len(remaining),
              applied=len(applied), override=override)
    return GateOutcome(status=status, report=report, applied=applied,
                       override=override and blocking, override_record=override_record)
