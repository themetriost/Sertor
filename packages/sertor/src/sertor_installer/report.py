"""Re-export of `InstallReport`, now migrated to `sertor-install-kit` (feature 037).

Preserves the historical import path `sertor_installer.report`. Note (F4): `capability` is now a
**required** argument of `InstallReport` — `sertor`'s call sites (wiki/rag) pass it explicitly.
"""
from __future__ import annotations

from sertor_install_kit.report import InstallReport

__all__ = ["InstallReport"]
