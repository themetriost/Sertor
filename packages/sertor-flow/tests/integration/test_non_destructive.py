"""US3 — non-distruttività di `sertor-flow install` (T040, FR-014).

File utente preesistenti (un agente con contenuto diverso, una costituzione già
presente) → l'install li lascia INTATTI (`skipped`), non sovrascrive mai.
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow.__main__ import main
from sertor_flow.install_governance import execute_governance_plan
from sertor_flow.profile import build_governance_profile
from tests.conftest import FakeSpecifyRunner


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

    report = execute_governance_plan(
        build_governance_profile(tmp_path), runner=FakeSpecifyRunner()
    )

    assert report.errors == 0
    assert agent.read_text(encoding="utf-8") == user_content        # preserved (non-destructive)
    # E2-FEAT-018: the outcome now HONESTLY says the present content diverges (left untouched),
    # instead of the misleading "skipped" that conflated identical with user-modified.
    assert (
        _outcome_for(report, ".claude/agents/requirements-analyst.md").outcome.value
        == "present_divergent"
    )


def test_preexisting_constitution_preserved(tmp_path: Path):
    """A pre-existing `.specify/memory/constitution.md` is never overwritten (FR-014)."""
    constitution = tmp_path / ".specify/memory/constitution.md"
    constitution.parent.mkdir(parents=True, exist_ok=True)
    user_content = "# Host's own constitution\nproject-specific principles\n"
    constitution.write_text(user_content, encoding="utf-8")

    report = execute_governance_plan(
        build_governance_profile(tmp_path), runner=FakeSpecifyRunner()
    )

    assert report.errors == 0
    assert constitution.read_text(encoding="utf-8") == user_content
    assert _outcome_for(report, ".specify/memory/constitution.md").outcome.value == "skipped"


def test_preexisting_plan_template_preserved(tmp_path: Path):
    """A host's customized `.specify/templates/plan-template.md` survives `specify init --force`
    (E15-FEAT-005/E10-FEAT-028): the installer backs it up and restores it around the launch, since
    `specify init` CLOBBERS it and it is not in the Sertor plan."""
    plan_tpl = tmp_path / ".specify/templates/plan-template.md"
    plan_tpl.parent.mkdir(parents=True, exist_ok=True)
    user_content = "# Plan Template\n## Constitution Check (mission-gate)\ncustom Sertor content\n"
    plan_tpl.write_text(user_content, encoding="utf-8")

    report = execute_governance_plan(
        build_governance_profile(tmp_path), runner=FakeSpecifyRunner()
    )

    assert report.errors == 0
    # The fake `specify init` clobbers plan-template.md; the installer restores the host's version.
    assert plan_tpl.read_text(encoding="utf-8") == user_content
    assert _outcome_for(report, ".specify/templates/plan-template.md").outcome.value == "updated"


def test_fresh_plan_template_left_upstream(tmp_path: Path):
    """On a fresh host (no pre-existing plan-template), the upstream one from `specify init` stays —
    no regression, no invented file, no restore outcome."""
    report = execute_governance_plan(
        build_governance_profile(tmp_path), runner=FakeSpecifyRunner()
    )

    assert report.errors == 0
    plan_tpl = tmp_path / ".specify/templates/plan-template.md"
    assert plan_tpl.read_text(encoding="utf-8") == "# speckit asset (mocked launch)\n"
    assert ".specify/templates/plan-template.md" not in [o.target_rel for o in report.outcomes]


def test_preexisting_init_options_preserved(tmp_path: Path, fake_runner):
    """A pre-existing generated file (`init-options.json`) is left as-is (skip-if-present)."""
    init = tmp_path / ".specify/init-options.json"
    init.parent.mkdir(parents=True, exist_ok=True)
    user_content = '{"integration": "custom", "mine": true}\n'
    init.write_text(user_content, encoding="utf-8")

    rc = main(["install", "--target", str(tmp_path)], runner=fake_runner)
    assert rc == 0
    assert init.read_text(encoding="utf-8") == user_content
