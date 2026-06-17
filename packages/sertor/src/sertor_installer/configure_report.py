"""Report entities for `sertor configure` (feature 051, data-model §1/3/4/5/6).

Pure entities (no I/O): the profile, per-field resolution, validation/probe outcomes and the
overall `ConfigureReport` with `render_human`/`render_json`/`exit_code`. Secrets enter the report
ONLY through `mask_secret` (the single masking point); a test asserts a known secret never appears
in either render form (FR-013/SC-008 — anti-leak structural).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from sertor_installer.configure_fields import ConfigField, FieldStatus, mask_secret

_BACKENDS = ("azure", "local")
_STORES = ("local", "azure")


@dataclass(frozen=True)
class ConfigProfile:
    """The chosen provider × store combination (data-model §1)."""

    backend: str
    store: str

    def __post_init__(self) -> None:
        if self.backend not in _BACKENDS:
            raise ValueError(f"invalid backend: {self.backend}")
        if self.store not in _STORES:
            raise ValueError(f"invalid store: {self.store}")


@dataclass(frozen=True)
class FieldResolution:
    """Outcome of resolving a single field (data-model §3)."""

    field: ConfigField
    value: str | None
    status: FieldStatus
    source: str

    @property
    def display_value(self) -> str | None:
        """Value as shown in reports: masked when the field is secret (the only exposure path)."""
        if self.value is None:
            return None
        return mask_secret(self.value) if self.field.secret else self.value


@dataclass(frozen=True)
class ValidationOutcome:
    """Outcome of the static validation (data-model §4)."""

    complete: bool
    missing: tuple[str, ...]


@dataclass(frozen=True)
class LiveCheckOutcome:
    """Outcome of the live probe (only with --check, data-model §5).

    `ok=None` means "not requested" OR "probe unavailable in this runtime" (honest degradation):
    in both cases the exit code is decided by the static validation alone.
    """

    requested: bool
    ok: bool | None
    detail: str


@dataclass(frozen=True)
class ConfigureReport:
    """Overall outcome (human + --json, zero secrets in clear, data-model §6)."""

    target: str
    profile: ConfigProfile
    fields: tuple[FieldResolution, ...]
    validation: ValidationOutcome
    live_check: LiveCheckOutcome
    env_path: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    def exit_code(self) -> int:
        """0 iff static validation complete AND (probe not requested OR probe ok); else 1."""
        if not self.validation.complete:
            return 1
        if self.live_check.requested and self.live_check.ok is False:
            return 1
        return 0

    def render_human(self) -> str:
        lines: list[str] = []
        lines.append(f"sertor configure — target: {self.target}")
        lines.append(f"profile: backend={self.profile.backend}, store={self.profile.store}")
        lines.append(f"env file: {self.env_path}")
        lines.append("")
        lines.append("fields:")
        if not self.fields:
            lines.append("  (none required for this profile)")
        for res in self.fields:
            shown = res.display_value if res.display_value is not None else "(unset)"
            lines.append(
                f"  - {res.field.name}: {res.status.value} "
                f"[source={res.source}] {shown}"
            )
        lines.append("")
        if self.validation.complete:
            lines.append("validation: complete")
        else:
            lines.append(
                "validation: INCOMPLETE — missing: " + ", ".join(self.validation.missing)
            )
        if self.live_check.requested:
            if self.live_check.ok is True:
                lines.append("live check: ok")
            elif self.live_check.ok is False:
                lines.append(f"live check: FAILED — {self.live_check.detail}")
            else:
                lines.append(f"live check: skipped — {self.live_check.detail}")
        for note in self.notes:
            lines.append(f"note: {note}")
        return "\n".join(lines)

    def render_json(self) -> str:
        payload = {
            "target": self.target,
            "profile": {"backend": self.profile.backend, "store": self.profile.store},
            "fields": [self._field_json(res) for res in self.fields],
            "validation": {
                "complete": self.validation.complete,
                "missing": list(self.validation.missing),
            },
            "live_check": {
                "requested": self.live_check.requested,
                "ok": self.live_check.ok,
                "detail": self.live_check.detail,
            },
            "env_path": self.env_path,
            "notes": list(self.notes),
            "exit_code": self.exit_code(),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _field_json(res: FieldResolution) -> dict:
        entry: dict = {
            "name": res.field.name,
            "status": res.status.value,
            "source": res.source,
        }
        # Only expose a value (always masked for secrets) when one was resolved.
        if res.display_value is not None:
            entry["value"] = res.display_value
        return entry
