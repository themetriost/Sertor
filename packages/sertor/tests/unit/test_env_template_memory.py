"""Anti-drift guard (feature 071 FEAT-009 + feature 072 FEAT-004, R-4): the `.env` templates carry
every conversation-memory knob, with capture OFF by default (privacy-by-default).

The knob list is **derived** from the source of `Settings.load()` (not a hand-kept mirror): every
`SERTOR_MEMORY*` / `SERTOR_EPISODIC*` env var that `load()` reads must appear (commented) in both
installer templates. A newly-added memory/episodic knob is therefore checked **automatically** —
closing the blind spot that let `SERTOR_MEMORY_SEMANTIC*` (FEAT-004) slip past the old hardcoded
list. `sertor` already depends on `sertor-core` at runtime, so importing `Settings` here adds no
new coupling.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from sertor_core.config.settings import Settings
from sertor_installer.resources import asset_path

_TEMPLATES = ("rag/env.local.tmpl", "rag/env.azure.tmpl")


def _memory_knobs_from_settings() -> tuple[str, ...]:
    """Every `SERTOR_MEMORY*` / `SERTOR_EPISODIC*` env var read by `Settings.load()` (derived).

    Extracts the memory/episodic env-var literals from the source of `Settings.load`. Any knob
    added to `load()` with one of these prefixes is picked up automatically — no mirror to drift.
    """
    source = inspect.getsource(Settings.load)
    knobs = set(re.findall(r"SERTOR_(?:MEMORY|EPISODIC)[A-Z_]*", source))
    assert knobs, "no memory/episodic knobs derived from Settings.load — derivation broke"
    return tuple(sorted(knobs))


_MEMORY_KNOBS = _memory_knobs_from_settings()


def _template_text(rel: str) -> str:
    return Path(str(asset_path(rel))).read_text(encoding="utf-8")


@pytest.mark.parametrize("template", _TEMPLATES)
@pytest.mark.parametrize("knob", _MEMORY_KNOBS)
def test_template_mentions_every_memory_knob(template: str, knob: str):
    assert knob in _template_text(template), f"{template} is missing memory knob {knob}"


@pytest.mark.parametrize("template", _TEMPLATES)
def test_memory_off_by_default(template: str):
    # No ACTIVE (uncommented) SERTOR_MEMORY*= line: capture/embedding must be opt-in.
    for line in _template_text(template).splitlines():
        stripped = line.strip()
        assert not stripped.startswith("SERTOR_MEMORY="), (
            f"{template} enables memory by default: {stripped!r}"
        )
