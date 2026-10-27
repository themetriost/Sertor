"""Verdetto di separazione (research R4): quali asserzioni separano la skill dal baseline, e se sul merito.

Un'asserzione separa se il suo tasso di successo con la skill supera quello del baseline. Il verdetto è
`validated` solo se separa almeno un'asserzione di merito. Se manca una valutazione è `incomplete`:
il runtime lo dichiara invece di indovinare.
"""

from __future__ import annotations

from pathlib import Path

from .adapters.workspace_fs import FsGradingSource
from .digest import agent_digest, skill_digest
from .domain.models import ExpectationOutcome, Verdict
from .domain.ports import GradingSource
from .jsonfiles import load_validated


def _expectations(case: dict) -> list[tuple[str, str]]:
    out = []
    for e in case["expectations"]:
        out.append((e, "merit") if isinstance(e, str) else (e["text"], e["kind"]))
    return out


def _pass_rate(gradings: list[dict], text: str) -> float | None:
    """Media di `passed` sui giri; None se un giro non ha valutato l'asserzione."""

    values = []
    for g in gradings:
        match = next((e for e in g["expectations"] if e["text"] == text), None)
        if match is None:
            return None
        values.append(1.0 if match["passed"] else 0.0)
    return sum(values) / len(values)


def compute_verdict(
    workspace: Path,
    evals_path: Path,
    source: GradingSource | None = None,
    skill_dir: Path | None = None,
) -> Verdict:
    """Calcola il verdetto; con `skill_dir` lo lega all'impronta della skill collaudata."""

    evals = load_validated(evals_path, "evals")
    runs = (source or FsGradingSource()).runs(workspace)
    outcomes: list[ExpectationOutcome] = []
    missing: list[str] = []
    challenges: list[dict] = []

    for case in evals["evals"]:
        eid = case["id"]
        with_runs, without_runs = runs.get((eid, "with_skill")), runs.get((eid, "without_skill"))
        for cfg, present in (("with_skill", with_runs), ("without_skill", without_runs)):
            if not present:
                missing.append(f"eval-{eid}/{cfg}")
        if not (with_runs and without_runs):
            continue
        for text, kind in _expectations(case):
            rate_with, rate_without = _pass_rate(with_runs, text), _pass_rate(without_runs, text)
            if rate_with is None or rate_without is None:
                missing.append(f"eval-{eid}: asserzione non valutata '{text}'")
                continue
            outcomes.append(ExpectationOutcome(eid, text, kind, rate_with, rate_without))
        challenges.extend(_challenges(eid, with_runs + without_runs))

    return Verdict(
        skill_name=evals["skill_name"],
        verdict=_classify(outcomes, missing),
        per_expectation=tuple(outcomes),
        missing=tuple(missing),
        kind_challenges=tuple(challenges),
        skill_digest=_digest(skill_dir),
    )


def _digest(subject: Path | None) -> str | None:
    """Impronta di ciò che è stato collaudato: una cartella-skill o, dalla 006, un file d'agente."""

    if subject is None:
        return None
    return agent_digest(subject) if subject.is_file() else skill_digest(subject)


def _challenges(eval_id: int, gradings: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for g in gradings:
        for e in g["expectations"]:
            ch = e.get("kind_challenge")
            if ch and e["text"] not in seen:
                seen[e["text"]] = {
                    "eval_id": eval_id,
                    "text": e["text"],
                    "proposed_kind": ch["proposed_kind"],
                    "why": ch["why"],
                }
    return list(seen.values())


def _classify(outcomes: list[ExpectationOutcome], missing: list[str]) -> str:
    if missing:
        return "incomplete"
    separating = [o for o in outcomes if o.separates]
    if any(o.kind == "merit" for o in separating):
        return "validated"
    return "protocol-only" if separating else "no-separation"
