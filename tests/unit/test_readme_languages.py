"""Reconciler: the core README lists every extension the ingestion indexes (140, Principio XIV).

The README section «What enters the corpus» is prose describing `_EXT_LANG`. Prose cannot be derived
from code, so this test is the named reconciler that reports the divergence instead of letting the
copy go stale in silence.
"""
from __future__ import annotations

from pathlib import Path

from sertor_core.services.ingestion import _EXT_LANG

README = Path(__file__).resolve().parents[2] / "src" / "sertor_core" / "README.md"


def test_every_indexed_extension_is_documented():
    text = README.read_text(encoding="utf-8")
    missing = sorted(ext for ext in _EXT_LANG if f"`{ext}`" not in text)
    assert not missing, f"extensions indexed but not listed in {README.name}: {missing}"


def test_the_false_fallback_claim_is_gone():
    assert "Any other language falls back without error" not in README.read_text(encoding="utf-8")
