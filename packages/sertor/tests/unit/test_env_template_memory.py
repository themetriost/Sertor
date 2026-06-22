"""Anti-drift guard (feature 071, FEAT-009, R-4): the `.env` templates carry the memory knobs.

The installer `.env` templates must surface every conversation-memory knob of `Settings`, with
capture OFF by default (privacy-by-default). If a future memory knob is added to `Settings` it must
be added here and to the templates, or this test fails.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_installer.resources import asset_path

# The conversation-memory knobs of `Settings` (mirror of settings.py: memory + episodic knobs).
_MEMORY_KNOBS = (
    "SERTOR_MEMORY",
    "SERTOR_MEMORY_ADAPTER",
    "SERTOR_MEMORY_RETENTION_DAYS",
    "SERTOR_MEMORY_SCRUB_PATTERNS",
    "SERTOR_MEMORY_CLAUDE_PROJECTS_DIR",
    "SERTOR_MEMORY_LIST_LIMIT",
    "SERTOR_EPISODIC_LIMIT",
    "SERTOR_EPISODIC_SNIPPET_TOKENS",
)

_TEMPLATES = ("rag/env.local.tmpl", "rag/env.azure.tmpl")


def _template_text(rel: str) -> str:
    return Path(str(asset_path(rel))).read_text(encoding="utf-8")


@pytest.mark.parametrize("template", _TEMPLATES)
@pytest.mark.parametrize("knob", _MEMORY_KNOBS)
def test_template_mentions_every_memory_knob(template: str, knob: str):
    assert knob in _template_text(template), f"{template} is missing memory knob {knob}"


@pytest.mark.parametrize("template", _TEMPLATES)
def test_memory_off_by_default(template: str):
    # No ACTIVE (uncommented) SERTOR_MEMORY= line: capture must be opt-in (privacy-by-default).
    for line in _template_text(template).splitlines():
        stripped = line.strip()
        assert not stripped.startswith("SERTOR_MEMORY="), (
            f"{template} enables memory by default: {stripped!r}"
        )
