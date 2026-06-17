"""`InstallReport`: observability contract for an `install <capability>` operation.

Aggregates `ArtifactOutcome` entries into counts + exit code (data-model §5). Two renderings: human
(default, one line per artifact + summary) and JSON (`--json`, schema `install.report/1`). The
report **is** the install's observability (Principio IX): no side effects, only status formatting.

`capability` is a **required** argument (F4): the default `"wiki"` was removed so each consumer
(`sertor` wiki/rag, `sertor-flow` governance) passes its own capability explicitly and titles never
silently inherit `"wiki"`. The JSON method keeps its existing name `render_json()` (NOT renamed to
`to_json()`, F1) to avoid touching the call sites of `sertor`.

Feature 048 (lifecycle): the report gains the `updated`/`removed` counters and an optional `op`
verb. The schema id stays `install.report/1` (additive, retrocompatible — NOT a second schema,
NFR-06): an install report simply carries `0` for the two new counts. The human title reflects the
verb (`sertor upgrade rag — …`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from sertor_install_kit.artifacts import ArtifactOutcome, LifecycleOp, Outcome

_SCHEMA = "install.report/1"


@dataclass
class InstallReport:
    """Overall install outcome: ordered artifact outcomes, counts, and optional failed step."""

    target: str
    capability: str  # e.g. "wiki" | "rag" | "governance" — required, used in the human title (F4)
    # Informative target assistant (feature 044, Principio IX): "claude" | "copilot". Optional so
    # existing call sites and `sertor-flow` keep working unchanged.
    assistant: str | None = None
    # Lifecycle verb (feature 048): drives the human title ("install"/"upgrade"/"uninstall").
    # Defaults to INSTALL → every existing call site renders exactly as before.
    op: LifecycleOp = LifecycleOp.INSTALL
    outcomes: list[ArtifactOutcome] = field(default_factory=list)
    created: int = 0
    skipped: int = 0
    merged: int = 0
    block: int = 0
    updated: int = 0  # feature 048
    removed: int = 0  # feature 048
    errors: int = 0
    failed_step: str | None = None

    def add(self, outcome: ArtifactOutcome) -> None:
        """Records an outcome and updates counts (including `failed_step` on error)."""
        self.outcomes.append(outcome)
        if outcome.outcome is Outcome.CREATED:
            self.created += 1
        elif outcome.outcome is Outcome.SKIPPED:
            self.skipped += 1
        elif outcome.outcome is Outcome.MERGED:
            self.merged += 1
        elif outcome.outcome is Outcome.BLOCK:
            self.block += 1
        elif outcome.outcome is Outcome.UPDATED:
            self.updated += 1
        elif outcome.outcome is Outcome.REMOVED:
            self.removed += 1
        elif outcome.outcome is Outcome.ERROR:
            self.errors += 1
            if self.failed_step is None:
                self.failed_step = outcome.target_rel

    def exit_code(self) -> int:
        """0 if no errors (even if everything was skipped — idempotency); 1 on domain error."""
        return 1 if self.errors else 0

    def render_human(self) -> str:
        """Human rendering to stdout."""
        assistant = f" — assistant: {self.assistant}" if self.assistant else ""
        verb = self.op.value  # "install" | "upgrade" | "uninstall" (feature 048)
        lines = [f"sertor {verb} {self.capability} — target: {self.target}{assistant}"]
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
                f"{self.merged} merged · {self.block} block · {self.updated} updated · "
                f"{self.removed} removed · {self.errors} errors"
            )
        return "\n".join(lines)

    def render_json(self) -> str:
        """JSON rendering (`--json`, schema `install.report/1` — additive, feature 048)."""
        payload = {
            "schema": _SCHEMA,
            "target": self.target,
            "assistant": self.assistant,
            "outcomes": [
                {"target_rel": o.target_rel, "outcome": o.outcome.value, "detail": o.detail}
                for o in self.outcomes
            ],
            "summary": {
                "created": self.created,
                "skipped": self.skipped,
                "merged": self.merged,
                "block": self.block,
                "updated": self.updated,
                "removed": self.removed,
                "errors": self.errors,
            },
            "failed_step": self.failed_step,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=False)
