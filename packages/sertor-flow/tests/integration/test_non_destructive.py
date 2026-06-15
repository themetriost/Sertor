"""US3 — non-distruttività di `sertor-flow install` (T040, FR-014).

File utente preesistenti (un agente con contenuto diverso, una costituzione già
presente) → l'install li lascia INTATTI (`skipped`), non sovrascrive mai.
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow.__main__ import main


def _outcome_for(report, target_rel: str):
    for o in report.outcomes:
        if o.target_rel == target_rel:
            return o
    raise AssertionError(f"no outcome for {target_rel}")


def test_preexisting_agent_preserved(tmp_path: Path):
    """A user-modified `.claude/agents/requirements-analyst.md` is left untouched."""
    agent = tmp_path / ".claude/agents/requirements-analyst.md"
    agent.parent.mkdir(parents=True, exist_ok=True)
    user_content = "# MY OWN requirements-analyst\nuser customization\n"
    agent.write_text(user_content, encoding="utf-8")

    from sertor_flow.install_governance import execute_governance_plan
    from sertor_flow.profile import build_governance_profile

    report = execute_governance_plan(build_governance_profile(tmp_path))

    assert report.errors == 0
    assert agent.read_text(encoding="utf-8") == user_content
    assert _outcome_for(report, ".claude/agents/requirements-analyst.md").outcome.value == "skipped"


def test_preexisting_constitution_preserved(tmp_path: Path):
    """A pre-existing `.specify/memory/constitution.md` is never overwritten (FR-014)."""
    constitution = tmp_path / ".specify/memory/constitution.md"
    constitution.parent.mkdir(parents=True, exist_ok=True)
    user_content = "# Host's own constitution\nproject-specific principles\n"
    constitution.write_text(user_content, encoding="utf-8")

    from sertor_flow.install_governance import execute_governance_plan
    from sertor_flow.profile import build_governance_profile

    report = execute_governance_plan(build_governance_profile(tmp_path))

    assert report.errors == 0
    assert constitution.read_text(encoding="utf-8") == user_content
    assert _outcome_for(report, ".specify/memory/constitution.md").outcome.value == "skipped"


def test_preexisting_init_options_preserved(tmp_path: Path):
    """A pre-existing generated file (`init-options.json`) is left as-is (skip-if-present)."""
    init = tmp_path / ".specify/init-options.json"
    init.parent.mkdir(parents=True, exist_ok=True)
    user_content = '{"integration": "custom", "mine": true}\n'
    init.write_text(user_content, encoding="utf-8")

    rc = main(["install", "--target", str(tmp_path)])
    assert rc == 0
    assert init.read_text(encoding="utf-8") == user_content
