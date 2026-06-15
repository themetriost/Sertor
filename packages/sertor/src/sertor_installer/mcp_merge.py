"""Re-export of `merge_mcp`, migrated to `sertor-install-kit` (feature 037).

Preserves the historical import path `sertor_installer.mcp_merge`. The merge now raises the kit's
`sertor_install_kit.errors.ConfigError`.
"""
from __future__ import annotations

from sertor_install_kit.mcp_merge import merge_mcp

__all__ = ["merge_mcp"]
