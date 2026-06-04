"""Comando `sertor wiki semantic-gate <wiki>` — gate semantico pre-commit/pre-push (US5).

Layer sottile: costruisce porta git + LLM + facade dalla configurazione, invoca `run_semantic_gate`
(servizio di confine) e mappa lo `status` a un exit code: `blocked` → 1, `pass`/`warning` → 0.
Trigger a monte del configuration-manager (REQ-092): le correzioni alle pagine generate sono già sul
working tree e finiscono nello stesso commit.
"""
from __future__ import annotations

import sys

from sertor_core.adapters.git import SubprocessGitAdapter
from sertor_core.composition import build_facade, build_llm
from sertor_core.services.semantic_gate import GateStatus, run_semantic_gate
from sertor_core.wiki.semantic import Severity

_SEVERITY = {s.name.lower(): s for s in Severity}


def run(args) -> int:
    threshold = _SEVERITY.get(getattr(args, "threshold", "high"), Severity.HIGH)
    git = SubprocessGitAdapter(repo_root=".")
    llm = build_llm()
    facade = build_facade()

    outcome = run_semantic_gate(
        args.wiki_path,
        llm=llm,
        facade=facade,
        git=git,
        threshold=threshold,
        override=getattr(args, "override", False),
        override_reason=getattr(args, "reason", None),
    )

    print(outcome.report.render())
    if outcome.applied:
        print(f"\nauto-fix applicati: {len(outcome.applied)}")
        for a in outcome.applied:
            print(f"  [{a.outcome}] {a.page} — {a.detail}")
    if outcome.override_record:
        print(f"\n⚠ OVERRIDE — {outcome.override_record}", file=sys.stderr)

    print(f"\nesito gate: {outcome.status}")
    return 1 if outcome.status == GateStatus.BLOCKED else 0
