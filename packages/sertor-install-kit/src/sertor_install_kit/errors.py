"""Domain exceptions for the install kit (Principio IV: explicit errors, no silent None).

The kit is stdlib-only and MUST NOT depend on `sertor-core`: it therefore owns its own exception
base, `InstallerError`, instead of `sertor_core.domain.errors.SertorError`. Third-party errors that
cross the kit boundary (for the kit, `sertor-core` IS a third party) are wrapped in these exceptions
by the consumer at the boundary (D3), so `execute_plan` can catch `InstallerError` for fail-fast.
"""
from __future__ import annotations


class InstallerError(Exception):
    """Root of all install-kit domain exceptions."""


class ConfigError(InstallerError):
    """Missing or inconsistent configuration/input.

    Same signature as the core's `ConfigError` (`message`, optional `key`) so the migrated
    primitives (`Artifact` validation, merge) keep their call sites unchanged.
    """

    def __init__(self, message: str, *, key: str | None = None):
        self.key = key
        super().__init__(message if key is None else f"{message} (key: {key})")
