"""`GovernanceProfile` + host inference (data-model §2, D7; feature 045).

The only point where the governance installer "inspects" the host: it infers the
script flavor from the running OS and pins the SpecKit version. The inferred
specifics are injected into the init/integration templates (see `generate.py`),
exactly as `config_gen.build_host_profile` does for the wiki. Defaults are NOT
hard-coded across the body — they live here (and in the templates), per Principle
VII (centralized configuration). No secrets.

The `assistant` field (feature 045) now drives (a) the targeting of the
Sertor-authored surfaces via `AssistantProfile` and (b) the launch of SpecKit
(`specify init --ai <assistant>`); it is validated against the kit's `AssistantId`
(unknown value → explicit `ConfigError`, Principle IV). The `speckit_version` is the
PINNED upstream release passed to `specify init` (config, not hard-coded sparse —
Principle VIII).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sertor_install_kit import AssistantId

# Pinned SpecKit version: `specify init` is launched at this upstream release
# (feature 045: launch-installer pivot). Single source of truth for the launch and
# for the generated init/integration files (Principle VIII, D7).
SPECKIT_VERSION = "0.8.18"

# Default target assistant when `--assistant` is absent (FR-002, aligned with FEAT-007).
DEFAULT_ASSISTANT = "claude"


def _infer_script(os_name: str | None = None) -> str:
    """Script flavor inferred from the OS: `ps` on Windows, `bash` elsewhere (D7).

    Both shell variants are shipped in the bundle regardless; this only selects the
    default recorded in the generated init/integration files.
    """
    name = os_name if os_name is not None else os.name
    return "ps" if name == "nt" else "bash"


@dataclass(frozen=True)
class GovernanceProfile:
    """Inferred host specifics, collected before generating the init/integration files.

    Analogous to `HostProfile` of the wiki. `target_root` is the host repo root;
    `assistant` is the AI integration (`claude`/`copilot`, feature 045) and drives
    targeting + the `specify init --ai <assistant>` launch; `script` is the inferred
    shell flavor (`ps`/`bash`), passed to `specify init --script`; `speckit_version`
    is the pinned upstream release. Pure value object, no secrets.

    The `assistant` value is validated against the kit's `AssistantId` at
    construction (unknown → explicit `ConfigError`, Principle IV).
    """

    target_root: Path
    assistant: str = DEFAULT_ASSISTANT
    script: str = "ps"
    speckit_version: str = SPECKIT_VERSION

    def __post_init__(self) -> None:
        # Validate the assistant against the kit's AssistantId (raises ConfigError on
        # an unknown value, listing the valid ones — Principle IV).
        AssistantId.from_str(self.assistant)


def build_governance_profile(
    target_root: Path,
    *,
    assistant: str = DEFAULT_ASSISTANT,
    script: str | None = None,
    speckit_version: str = SPECKIT_VERSION,
) -> GovernanceProfile:
    """Builds the `GovernanceProfile`, inferring `script` from the OS when not given (D7).

    `assistant` is validated against `AssistantId` (feature 045): an unknown value
    raises an explicit `ConfigError` before any side effect.
    """
    return GovernanceProfile(
        target_root=target_root,
        assistant=assistant,
        script=script if script is not None else _infer_script(),
        speckit_version=speckit_version,
    )
