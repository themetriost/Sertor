"""Launch the SpecKit installer instead of vendoring it (feature 045, contracts/speckit-launch.md).

The launch-installer pivot: `sertor-flow` no longer ships copies of the SpecKit commands/agents and
`.specify/**`. It LAUNCHES `specify init` for the target assistant, which deposits the per-assistant
variant (Claude `.claude/...` · Copilot CLI `.github/prompts/`+`.github/agents/`; `.specify/` is
shared) at a PINNED upstream version. Our `copilot-cli` maps to spec-kit's `--ai copilot` (FEAT-012,
single point `_SPECKIT_AI_FLAG`). This is the only place that knows the spec-kit command — it sits
behind the kit's `CommandRunner` so tests mock it (no network).

DA-4 (design assumption, documented): the exact invocation. We launch via `uvx`, pulling the pinned
spec-kit release from its git tag, then run `specify init` in-place on the host root:

    uvx --from git+<SPECKIT_REPO>@v<version> specify init . --here --ai <assistant> \
        --script <ps|sh> --no-git --force

`--here` initialises into the current directory (the host root, `cwd`); `--no-git`/`--force` keep
install ≠ run (no git init) and avoid the interactive prompt. The flags are isolated here; if a host
needs a different invocation, this is the single point to adapt. Tests mock the `CommandRunner`, so
the precise flag set is asserted, not executed.

Idempotency (install ≠ run, non-destructive): if the expected layout is already on disk (re-run),
the launch is SKIPPED (not relaunched). Fail-fast (FR-004): tool absent / command failed / layout
missing → `InstallerError`, no partial success swallowed.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sertor_flow.profile import GovernanceProfile
from sertor_install_kit import (
    CommandRunner,
    InstallerError,
    Outcome,
    SubprocessRunner,
    log_event,
)

# The tool we launch and the pinned source (DA-4). `uvx` runs spec-kit's CLI `specify` from the
# pinned git tag without a global install.
SPECKIT_TOOL = "uvx"
SPECKIT_REPO = "git+https://github.com/github/spec-kit.git"

# `profile.script` flavor → spec-kit `--script` value (cross-platform: ps on Windows, sh on POSIX).
_SCRIPT_VALUE = {"ps": "ps", "bash": "sh", "sh": "sh"}

# Our `--assistant` value → the `--ai` value spec-kit 0.8.18 recognizes (FR-013/FR-015, SC-006).
# spec-kit has NO `copilot-cli`; our CLI target maps to upstream `copilot`. This is the SINGLE
# documented translation point — update ONLY this map if a future pinned spec-kit adds an
# `--ai copilot-cli` (VIN-01/A-2). Default-safe via `.get(assistant, assistant)`.
_SPECKIT_AI_FLAG = {"claude": "claude", "copilot-cli": "copilot"}

# Force UTF-8 in the launched `specify init`. spec-kit prints its banner via `rich` (box-drawing
# glyphs, etc.); on a legacy Windows console (code page cp1252) Python's stdout cannot encode them
# and `specify` aborts with a UnicodeEncodeError (exit 1) — independent of `--ai`. PYTHONUTF8=1 puts
# the interpreter in UTF-8 mode; PYTHONIOENCODING is a belt-and-suspenders fallback. Passed as an
# env OVERLAY so the child still inherits PATH and everything else.
_UTF8_ENV = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

# Per-assistant "marker" files that MUST exist after a successful launch (layout verification).
# Kept minimal: a SpecKit surface for the assistant + the shared `.specify/` machinery.
# NOTE (verified empirically against spec-kit v0.8.18): the Claude integration ships SKILLS
# (`.claude/skills/speckit-*/SKILL.md`), NOT slash-commands (`.claude/commands/speckit.*.md`) —
# spec-kit migrated Claude to agent skills. Copilot still ships prompts. If a future pinned
# spec-kit changes a layout again, this is the single point to update.
_EXPECTED_LAYOUT = {
    "claude": (
        ".claude/skills/speckit-specify/SKILL.md",
        ".specify/templates/plan-template.md",
    ),
    # Keyed by OUR assistant name (`copilot-cli`); the PATHS are the layout spec-kit produces for
    # `--ai copilot` (FEAT-012, FR-014/SC-007). The launch maps `copilot-cli`→`copilot`, so the
    # Copilot layout is what lands on disk; `_layout_present` recognizes the re-run (idempotency).
    "copilot-cli": (
        ".github/prompts/speckit.specify.prompt.md",
        ".specify/templates/plan-template.md",
    ),
}


def _expected_layout(assistant: str) -> tuple[str, ...]:
    return _EXPECTED_LAYOUT.get(assistant, (".specify/templates/plan-template.md",))


def _layout_present(root: Path, assistant: str) -> bool:
    """True when ALL expected layout markers for the assistant exist (idempotency/verify)."""
    return all((root / rel).exists() for rel in _expected_layout(assistant))


def build_specify_command(profile: GovernanceProfile) -> list[str]:
    """The `specify init` command for the profile's assistant/script at the pinned version (DA-4).

    Isolated so the precise invocation is testable and adaptable in one place.
    """
    script_value = _SCRIPT_VALUE.get(profile.script, "sh")
    ai_value = _SPECKIT_AI_FLAG.get(profile.assistant, profile.assistant)
    return [
        SPECKIT_TOOL,
        "--from",
        f"{SPECKIT_REPO}@v{profile.speckit_version}",
        "specify",
        "init",
        ".",
        "--here",
        "--ai",
        ai_value,
        "--script",
        script_value,
        "--no-git",
        "--force",
    ]


def launch_speckit(profile: GovernanceProfile, runner: CommandRunner | None = None) -> Outcome:
    """Obtains SpecKit by launching `specify init` for the assistant (contract speckit.launch/1).

    Returns `Outcome.CREATED` on a verified launch, `Outcome.SKIPPED` if the layout is already
    present (re-run). Raises `InstallerError` (fail-fast, no partial state) when spec-kit is absent,
    the command fails, or the produced layout is missing (FR-004). The `runner` is injected so tests
    mock it; production uses `SubprocessRunner`.
    """
    runner = runner if runner is not None else SubprocessRunner()
    root = profile.target_root
    assistant = profile.assistant

    # Idempotency: layout already present → do not relaunch (install ≠ run, non-destructive).
    if _layout_present(root, assistant):
        log_event(logging.INFO, "speckit_launch", assistant=assistant,
                   version=profile.speckit_version, outcome="skipped")
        return Outcome.SKIPPED

    # Fail-fast: spec-kit launcher unavailable → actionable error, nothing launched (FR-004).
    if not runner.is_available(SPECKIT_TOOL):
        log_event(logging.WARNING, "speckit_launch", assistant=assistant,
                   version=profile.speckit_version, outcome="error", reason="tool_absent")
        raise InstallerError(
            f"spec-kit launcher '{SPECKIT_TOOL}' is not available: install it (e.g. `pip install "
            f"uv`) and ensure it is on PATH, then re-run. SpecKit is obtained by launching "
            f"`specify init` ({SPECKIT_REPO}@v{profile.speckit_version}); no vendored copy shipped."
        )

    cmd = build_specify_command(profile)
    # Overlay UTF-8 env so spec-kit's rich banner does not crash on legacy Windows consoles.
    result = runner.run(cmd, root, env=_UTF8_ENV)
    if not result.ok:
        log_event(logging.WARNING, "speckit_launch", assistant=assistant,
                   version=profile.speckit_version, outcome="error", reason="command_failed",
                   returncode=result.returncode)
        raise InstallerError(
            f"`specify init` failed (exit {result.returncode}) for assistant '{assistant}'. "
            f"stderr: {result.stderr.strip()[:500]}"
        )

    # Verify the produced layout — a successful exit with a missing layout is still a failure.
    if not _layout_present(root, assistant):
        missing = [rel for rel in _expected_layout(assistant) if not (root / rel).exists()]
        log_event(logging.WARNING, "speckit_launch", assistant=assistant,
                   version=profile.speckit_version, outcome="error", reason="layout_missing")
        raise InstallerError(
            f"`specify init` reported success but the expected SpecKit layout for '{assistant}' is "
            f"missing: {', '.join(missing)}. The launch produced no usable governance scaffold."
        )

    log_event(logging.INFO, "speckit_launch", assistant=assistant,
               version=profile.speckit_version, outcome="created")
    return Outcome.CREATED
