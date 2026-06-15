"""Re-export of `append_gitignore`, migrated to `sertor-install-kit` (feature 037)."""
from __future__ import annotations

from sertor_install_kit.gitignore_append import RUNTIME_IGNORES, append_gitignore

__all__ = ["append_gitignore", "RUNTIME_IGNORES"]
