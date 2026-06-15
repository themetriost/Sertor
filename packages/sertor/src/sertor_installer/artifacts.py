"""Re-export of the installer domain entities, now migrated to `sertor-install-kit` (feature 037).

The entities (`Artifact`/`ArtifactKind`/`WriteStrategy`/`Outcome`/`ArtifactOutcome`) live in the
shared toolkit. This thin module preserves the historical import path `sertor_installer.artifacts`
used by `sertor`'s code and tests.
"""
from __future__ import annotations

from sertor_install_kit.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    Outcome,
    WriteStrategy,
)

__all__ = ["Artifact", "ArtifactKind", "ArtifactOutcome", "Outcome", "WriteStrategy"]
