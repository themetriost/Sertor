"""Guard: the repo's line-ending policy is present and the dogfood matches the installer (E15).

Two invariants for `asset-install` (FEAT-001 scope B / FEAT-010):

1. **Policy present** — the repo root carries a `.gitattributes` that normalizes text to LF, so
   re-writing a file via the installer (which writes CRLF on Windows) produces a clean diff
   instead of a spurious line-ending churn (US3 / SC-2, Principio XII — keep the diff honest).
2. **Process-fidelity** — the dogfood's `.gitattributes` is byte-identical to the one the real
   `sertor install rag` deposits (`assets/rag/gitattributes`): its provenance is the install
   process, not a hand copy (SC-2 / REQ-008). Reading with universal newlines makes the check
   EOL-insensitive, mirroring the byte guards.

Offline F.I.R.S.T. (no network, no git subprocess).
"""
from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOGFOOD_GITATTRS = _REPO_ROOT / ".gitattributes"
_BUNDLED_ASSET = (
    _REPO_ROOT
    / "packages"
    / "sertor"
    / "src"
    / "sertor_installer"
    / "assets"
    / "rag"
    / "gitattributes"
)

_LF_RULE = "* text=auto eol=lf"


def test_repo_has_lf_policy():
    assert _DOGFOOD_GITATTRS.is_file(), "the repo root must carry a `.gitattributes`"
    assert _LF_RULE in _DOGFOOD_GITATTRS.read_text(encoding="utf-8"), (
        "the `.gitattributes` must normalize text to LF (`* text=auto eol=lf`)"
    )


def test_dogfood_gitattributes_matches_installer_asset():
    """The dogfood's `.gitattributes` is what `sertor install rag` deposits (process-fidelity)."""
    assert _BUNDLED_ASSET.is_file(), "the bundled `assets/rag/gitattributes` must exist"
    # read_text uses universal newlines → EOL-insensitive comparison (like the byte guards).
    dogfood = _DOGFOOD_GITATTRS.read_text(encoding="utf-8")
    asset = _BUNDLED_ASSET.read_text(encoding="utf-8")
    assert dogfood == asset, (
        "dogfood `.gitattributes` drifted from the installer asset (install rag is the source)"
    )
