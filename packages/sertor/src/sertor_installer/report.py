"""`InstallReport`: contratto di osservabilità dell'operazione `sertor install wiki`.

Aggrega gli `ArtifactOutcome` in conteggi + exit code (data-model §5, contracts/install-report.md,
D8). Due rese: umana (default, una riga per artefatto + riepilogo) e JSON (`--json`, schema
`install.report/1`, F5). Il report **è** l'osservabilità dell'install (Principio IX): nessun side
effect, solo formattazione di stato.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from sertor_installer.artifacts import ArtifactOutcome, Outcome

_SCHEMA = "install.report/1"


@dataclass
class InstallReport:
    """Esito complessivo dell'install: esiti in ordine, conteggi, eventuale passo fallito."""

    target: str
    capability: str = "wiki"  # "wiki" | "rag" — solo per il titolo della resa umana
    outcomes: list[ArtifactOutcome] = field(default_factory=list)
    created: int = 0
    skipped: int = 0
    merged: int = 0
    block: int = 0
    errors: int = 0
    failed_step: str | None = None

    def add(self, outcome: ArtifactOutcome) -> None:
        """Registra un esito e aggiorna i conteggi (più il `failed_step` su errore)."""
        self.outcomes.append(outcome)
        if outcome.outcome is Outcome.CREATED:
            self.created += 1
        elif outcome.outcome is Outcome.SKIPPED:
            self.skipped += 1
        elif outcome.outcome is Outcome.MERGED:
            self.merged += 1
        elif outcome.outcome is Outcome.BLOCK:
            self.block += 1
        elif outcome.outcome is Outcome.ERROR:
            self.errors += 1
            if self.failed_step is None:
                self.failed_step = outcome.target_rel

    def exit_code(self) -> int:
        """0 se nessun errore (anche se tutto skipped — idempotenza); 1 su errore di dominio."""
        return 1 if self.errors else 0

    def render_human(self) -> str:
        """Resa umana su stdout (contracts/install-report.md §Formato umano)."""
        lines = [f"sertor install {self.capability} — target: {self.target}"]
        for o in self.outcomes:
            suffix = f" ({o.detail})" if o.detail else ""
            lines.append(f"  {o.outcome.value:<8}{o.target_rel}{suffix}")
        if self.errors and self.failed_step:
            lines.append(
                f"Aborted: failed step = {self.failed_step}. Fix it and re-run."
            )
        else:
            lines.append(
                f"Summary: {self.created} created · {self.skipped} skipped · "
                f"{self.merged} merged · {self.block} block · {self.errors} errors"
            )
        return "\n".join(lines)

    def render_json(self) -> str:
        """Resa JSON (`--json`, schema `install.report/1`)."""
        payload = {
            "schema": _SCHEMA,
            "target": self.target,
            "outcomes": [
                {"target_rel": o.target_rel, "outcome": o.outcome.value, "detail": o.detail}
                for o in self.outcomes
            ],
            "summary": {
                "created": self.created,
                "skipped": self.skipped,
                "merged": self.merged,
                "block": self.block,
                "errors": self.errors,
            },
            "failed_step": self.failed_step,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=False)
