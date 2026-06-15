"""Re-export of `merge_settings`, migrated to `sertor-install-kit` (feature 037).

Preserves the historical import path `sertor_installer.settings_merge`. Note: the merge now raises
the kit's `sertor_install_kit.errors.ConfigError` (a third-party error from `sertor-core` is not
involved here).
"""
from __future__ import annotations

from sertor_install_kit.settings_merge import merge_settings

__all__ = ["merge_settings"]
