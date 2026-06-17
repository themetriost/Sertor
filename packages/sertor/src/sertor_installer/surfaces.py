"""Per-assistant rendering of FILE surfaces — re-exported from the shared kit (feature 045).

The renderer was MOVED to `sertor_install_kit.surfaces` (feature 045) so `sertor` and `sertor-flow`
share one implementation (anti-drift/DRY). This module is a thin shim that re-exports the kit
functions, keeping the existing `sertor_installer.surfaces.<fn>` import sites unchanged
(non-regression FEAT-007).
"""
from __future__ import annotations

from sertor_install_kit.surfaces import (
    HookEntrySpec,
    render_copilot_hooks,
    render_custom_agent,
    render_prompt_file,
    split_frontmatter,
)

__all__ = [
    "split_frontmatter",
    "render_prompt_file",
    "render_custom_agent",
    "HookEntrySpec",
    "render_copilot_hooks",
]
