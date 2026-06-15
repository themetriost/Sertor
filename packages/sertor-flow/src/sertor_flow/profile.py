"""`GovernanceProfile` + host inference (data-model §2, D7).

The only point where the governance installer "inspects" the host: it infers the
script flavor from the running OS and pins the SpecKit version. The inferred
specifics are injected into the init/integration templates (see `generate.py`),
exactly as `config_gen.build_host_profile` does for the wiki. Defaults are NOT
hard-coded across the body — they live here (and in the templates), per Principle
VII (centralized configuration). No secrets.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Pinned SpecKit version: the vendored assets (skills/agents/templates/scripts) come
# from this upstream release. It is the single source of truth for the generated
# init/integration files (D7).
SPECKIT_VERSION = "0.8.18"

# Only `claude` is supported for the MVP (D7); kept as a field so the surface is
# ready to extend.
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
    `assistant` is the AI integration (only `claude` in the MVP); `script` is the
    inferred shell flavor (`ps`/`bash`); `speckit_version` is the pinned upstream
    version. Pure value object, no secrets.
    """

    target_root: Path
    assistant: str = DEFAULT_ASSISTANT
    script: str = "ps"
    speckit_version: str = SPECKIT_VERSION


def build_governance_profile(
    target_root: Path,
    *,
    assistant: str = DEFAULT_ASSISTANT,
    script: str | None = None,
    speckit_version: str = SPECKIT_VERSION,
) -> GovernanceProfile:
    """Builds the `GovernanceProfile`, inferring `script` from the OS when not given (D7)."""
    return GovernanceProfile(
        target_root=target_root,
        assistant=assistant,
        script=script if script is not None else _infer_script(),
        speckit_version=speckit_version,
    )
