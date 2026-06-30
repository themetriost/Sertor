"""Host OS environment helpers for install-time guard checks (E10-FEAT-018).

All functions are pure stdlib, deterministic, mockable — zero imports of sertor_core or LLMs.

The deposited lifecycle hooks are PowerShell-only (`.ps1`). On Windows they run via the bundled
PowerShell 5.1; on macOS/Linux they require PowerShell Core (`pwsh`). This module detects the
non-Windows-without-`pwsh` case and lets the installer surface an honest, actionable note instead of
silently depositing hooks that never fire (Principio XII — fail loud). It does NOT rewrite the hook
wiring (`"shell": "powershell"` / `pwsh -File`): it only detects and reports (research D-3).
"""
from __future__ import annotations

import os
import shutil
from collections.abc import Sequence

from sertor_install_kit.report import InstallReport

PWSH_INSTALL_URL = (
    "https://learn.microsoft.com/powershell/scripting/install/installing-powershell"
)


def is_windows() -> bool:
    """True on Windows (os.name == 'nt'), False on macOS/Linux."""
    return os.name == "nt"


def pwsh_available() -> bool:
    """True if 'pwsh' (PowerShell Core) is found in PATH. Binary check: no version test (NFR-4)."""
    return shutil.which("pwsh") is not None


def pwsh_unavailability_note(hook_surfaces: Sequence[str]) -> str:
    """Pure builder for the `pwsh` unavailability note (Nota A, contracts/install-notes.md).

    Mentions `pwsh`/PowerShell Core (A1), includes the install URL (A2), lists the affected hook
    surfaces (A3) and states explicitly that they are installed but non-operational (A4). No
    side-effects; does not call `is_windows`/`pwsh_available`.
    """
    surfaces = ", ".join(hook_surfaces)
    return (
        "pwsh (PowerShell Core) was not found on this non-Windows host: the deposited hooks "
        f"({surfaces}) are installed but non-operational until you install it — {PWSH_INSTALL_URL}"
    )


def maybe_note_pwsh(report: InstallReport, hook_surfaces: Sequence[str]) -> None:
    """Append the `pwsh` unavailability note to `report` only when warranted.

    Gating (triple, with `is_windows()` first to short-circuit on Windows — INV-5): non-Windows
    host AND `pwsh` absent AND the plan deposited at least one hook surface. Otherwise no-op.
    Never raises (INV-1); `report.note()` is idempotent and non-fatal.
    """
    if (not is_windows()) and (not pwsh_available()) and hook_surfaces:
        report.note(pwsh_unavailability_note(hook_surfaces))
