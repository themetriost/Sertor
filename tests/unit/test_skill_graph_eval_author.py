"""Static invariants of the eval-suite-author skill for graph-case genesis (066, TASK-B03).

No LLM, only file checks: the skill must cite the deterministic vehicles, never import the core,
stay host-agnostic (no Sertor-specific absolute paths, no Claude model names), and mark the D vs N
boundary (approval, not automatic persistence).
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SKILL_FILES = (
    _REPO_ROOT / ".claude" / "skills" / "eval-suite-author" / "SKILL.md",
    _REPO_ROOT
    / "packages" / "sertor" / "src" / "sertor_installer"
    / "assets" / "rag" / "skills" / "eval-suite-author" / "SKILL.md",
)


@pytest.fixture(params=_SKILL_FILES, ids=["dogfood", "distributed"])
def skill_body(request) -> str:
    path = request.param
    assert path.exists(), f"skill file missing: {path}"
    return path.read_text(encoding="utf-8")


def test_cites_graph_eval_vehicles(skill_body):
    assert "graph-eval validate-ref" in skill_body
    assert "graph-eval add-case" in skill_body


def test_no_core_import(skill_body):
    assert "import sertor_core" not in skill_body
    assert "from sertor_core" not in skill_body


def test_no_sertor_specific_absolute_path(skill_body):
    assert "src/sertor_core/" not in skill_body


def test_no_claude_model_names(skill_body):
    for name in ("Opus", "Haiku", "Sonnet"):
        assert name not in skill_body


def test_marks_approval_boundary(skill_body):
    lowered = skill_body.lower()
    assert "approv" in lowered  # approve / approvazione / approval
