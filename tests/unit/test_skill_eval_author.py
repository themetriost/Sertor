"""Structural guards for the eval-suite-author skill (065, TASK-018, US2).

Not a live LLM run: verifies the skill body exists, drives writes through the CLI vehicle, never
mentions importing the core library, and is host-agnostic (no Sertor paths, no model names).
"""
from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SKILL = _ROOT / ".claude" / "skills" / "eval-suite-author" / "SKILL.md"


@pytest.fixture(scope="module")
def body() -> str:
    return _SKILL.read_text(encoding="utf-8")


def test_skill_exists(body):
    assert body.strip()


def test_invokes_cli_vehicle(body):
    assert "sertor-rag eval add-case" in body


def test_uses_validate_path_primitive(body):
    assert "sertor-rag eval validate-path" in body


def test_never_imports_core_library(body):
    # The skill must drive writes through the CLI vehicle, never the library directly.
    assert "import sertor_core" not in body
    assert "build_facade(" not in body
    assert "build_indexer(" not in body


def test_handles_unindexed_corpus(body):
    assert "sertor-rag index ." in body


def test_host_agnostic_no_sertor_paths(body):
    # the skill must not assume Sertor's own layout (Principio X)
    assert "src/sertor_core/" not in body
    assert "C:\\Workspace" not in body


def test_no_claude_model_names(body):
    lowered = body.lower()
    assert "opus" not in lowered
    assert "haiku" not in lowered
    assert "sonnet" not in lowered
