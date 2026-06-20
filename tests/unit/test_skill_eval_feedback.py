"""Structural guards for the eval-feedback skill (065, TASK-021, US3).

Verifies the skill exists, every write passes through the CLI vehicle, there is no automatic mode
(no inferred/implicit persistence), and the body is host-agnostic. Also checks `amend_case`'s
public signature supports the use the skill expects.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from sertor_core.services.eval import suite_io

_ROOT = Path(__file__).resolve().parents[2]
_SKILL = _ROOT / ".claude" / "skills" / "eval-feedback" / "SKILL.md"


@pytest.fixture(scope="module")
def body() -> str:
    return _SKILL.read_text(encoding="utf-8")


def test_skill_exists(body):
    assert body.strip()


def test_invokes_cli_vehicle(body):
    assert "sertor-rag eval add-case" in body


def test_never_imports_core_library(body):
    assert "import sertor_core" not in body


def test_no_automatic_mode(body):
    # every write must require explicit confirmation (REQ-051)
    lowered = body.lower()
    assert "conferma esplicita" in lowered or "azione esplicita" in lowered
    assert "mai inferire" in lowered or "inferire" in lowered


def test_handles_missing_case(body):
    # REQ-052: offer to create a new case when the query has none
    assert "assente" in body.lower()


def test_host_agnostic(body):
    assert "C:\\Workspace" not in body
    lowered = body.lower()
    assert "opus" not in lowered and "haiku" not in lowered and "sonnet" not in lowered


def test_amend_case_signature_supports_skill_use():
    sig = inspect.signature(suite_io.amend_case)
    params = sig.parameters
    assert "query" in params
    assert "expected" in params
    assert "kind" in params
