"""Attribuzione MIT del vendoring spec-kit (T046, SC-007/REQ-022).

(a) gli asset di attribuzione esistono nel pacchetto: `assets/NOTICE` e
    `assets/LICENSES/spec-kit-MIT.txt`;
(b) `sertor-flow install` li deposita sull'ospite a `.specify/NOTICE` e
    `.specify/LICENSES/spec-kit-MIT.txt`.
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow.__main__ import main
from sertor_install_kit.resources import asset_path, read_asset_text

_ANCHOR = "sertor_flow"


def test_notice_and_license_present_in_package():
    """The attribution assets are bundled in the package."""
    assert asset_path(_ANCHOR, "NOTICE").is_file()
    assert asset_path(_ANCHOR, "LICENSES/spec-kit-MIT.txt").is_file()
    license_text = read_asset_text(_ANCHOR, "LICENSES/spec-kit-MIT.txt")
    assert "MIT" in license_text
    assert "Permission is hereby granted" in license_text


def test_install_deposits_attribution_on_host(tmp_path: Path):
    """The install deposits NOTICE + MIT license under `.specify/` (SC-007)."""
    rc = main(["install", "--target", str(tmp_path)])
    assert rc == 0

    notice = tmp_path / ".specify/NOTICE"
    license_file = tmp_path / ".specify/LICENSES/spec-kit-MIT.txt"
    assert notice.is_file()
    assert license_file.is_file()
    # Deposited byte-for-byte from the bundled assets.
    assert notice.read_text(encoding="utf-8") == read_asset_text(_ANCHOR, "NOTICE")
    assert license_file.read_text(encoding="utf-8") == read_asset_text(
        _ANCHOR, "LICENSES/spec-kit-MIT.txt"
    )
