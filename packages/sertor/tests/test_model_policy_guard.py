"""Real-asset + coherence guard for the model-policy profile (E2-FEAT-015).

Builds the THREE real install plans (rag/concierge, wiki/wiki-curator, governance/
{requirements-analyst,configuration-manager,requirements}) for `AssistantId.COPILOT_CLI` and
renders each `.agent.md` via the plan's OWN render function (no filesystem writes, no
`specify`/`CommandRunner` mocking needed — mirrors `test_assets_copilot_parity.py`'s pattern).
Asserts:
  - each of the 5 rendered `.agent.md` carries `model:` == the policy value for that agent,
    never a bare Claude alias (contract C3, R10/R11);
  - `IN_SCOPE_AGENTS` == exactly the 5 names the three plans deposit (contract C5, R15);
  - a synthetic incomplete profile makes each plan-BUILDER raise `ModelPolicyError` naming
    the missing agent, BEFORE any artifact is written (contract C3, R12).

Offline (RNF-7): `tmp_path` only, no network, no subprocess.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_install_kit.assistant import AssistantId
from sertor_install_kit.errors import ModelPolicyError
from sertor_install_kit.model_policy import IN_SCOPE_AGENTS, resolve_model
from sertor_installer.install_rag import _render_rag_file, build_rag_plan
from sertor_installer.install_wiki import _render_for_target as _wiki_render
from sertor_installer.install_wiki import build_install_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
from sertor_installer.surfaces import split_frontmatter


def _model_value(front: str) -> str | None:
    for line in front.splitlines():
        if line.strip().startswith("model:"):
            return line.split(":", 1)[1].strip()
    return None


def _rag_plan(tmp_path: Path):
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    return build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)


def _governance_plan(tmp_path: Path):
    # Lazy import: sertor-flow is a sibling package (no runtime dependency from sertor),
    # mirrors test_assets_copilot_parity.py's `_governance_plan`.
    from sertor_flow.install_governance import build_governance_plan
    from sertor_flow.profile import build_governance_profile

    profile = build_governance_profile(tmp_path, assistant="copilot-cli")
    return build_governance_plan(profile)


def _rendered_agent_frontmatters(tmp_path: Path) -> dict[str, str]:
    """(agent_name -> rendered frontmatter) for the 5 `.agent.md` targets, via each plan's
    own render function — no filesystem writes."""
    from sertor_flow.install_governance import _render_for_target as _gov_render

    out: dict[str, str] = {}
    for art in _rag_plan(tmp_path / "rag"):
        if art.target_rel.endswith(".agent.md"):
            name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
            out[name] = split_frontmatter(_render_rag_file(art))[0]
    for art in build_install_plan(AssistantId.COPILOT_CLI):
        if art.target_rel.endswith(".agent.md"):
            name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
            out[name] = split_frontmatter(_wiki_render(art))[0]
    for art in _governance_plan(tmp_path / "gov"):
        if art.target_rel.endswith(".agent.md"):
            name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
            out[name] = split_frontmatter(_gov_render(art))[0]
    return out


# --- C3/R10/R11: all 5 rendered .agent.md carry the policy model, never a bare alias -------


def test_all_five_agents_get_explicit_policy_model(tmp_path: Path):
    frontmatters = _rendered_agent_frontmatters(tmp_path)
    assert set(frontmatters) == IN_SCOPE_AGENTS, (
        f"rendered agents {sorted(frontmatters)} != IN_SCOPE_AGENTS {sorted(IN_SCOPE_AGENTS)}"
    )
    for name, front in frontmatters.items():
        value = _model_value(front)
        assert value == resolve_model(name), (
            f"{name}: model {value!r} != policy {resolve_model(name)!r}"
        )
        assert value not in {"haiku", "sonnet", "opus"}, (
            f"{name}: bare Claude alias leaked: {value!r}"
        )


# --- C5/R15: IN_SCOPE_AGENTS coincides exactly with the deposited agent set ----------------


def test_in_scope_agents_matches_deposited_agents(tmp_path: Path):
    frontmatters = _rendered_agent_frontmatters(tmp_path)
    assert set(frontmatters) == IN_SCOPE_AGENTS


def test_policy_pins_five_model_ids():
    """Pin (regression on accidental edits)."""
    assert resolve_model("concierge") == "claude-haiku-4.5"
    assert resolve_model("configuration-manager") == "claude-haiku-4.5"
    assert resolve_model("requirements-analyst") == "claude-sonnet-4.6"
    assert resolve_model("requirements") == "claude-sonnet-4.6"
    assert resolve_model("wiki-curator") == "claude-sonnet-4.6"


# --- C3/R12: fail-loud on an incomplete profile, BEFORE any artifact is written ------------


def test_incomplete_profile_fails_rag_plan_naming_concierge(tmp_path: Path, monkeypatch):
    import sertor_install_kit.model_policy as mp

    monkeypatch.delitem(mp._MODEL_POLICY, "concierge")
    with pytest.raises(ModelPolicyError, match="concierge"):
        _rag_plan(tmp_path)


def test_incomplete_profile_fails_wiki_plan_naming_wiki_curator(monkeypatch):
    import sertor_install_kit.model_policy as mp

    monkeypatch.delitem(mp._MODEL_POLICY, "wiki-curator")
    with pytest.raises(ModelPolicyError, match="wiki-curator"):
        build_install_plan(AssistantId.COPILOT_CLI)


def test_incomplete_profile_fails_governance_plan_naming_agent(tmp_path: Path, monkeypatch):
    import sertor_install_kit.model_policy as mp
    from sertor_flow.install_governance import build_governance_plan
    from sertor_flow.profile import build_governance_profile

    monkeypatch.delitem(mp._MODEL_POLICY, "requirements-analyst")
    profile = build_governance_profile(tmp_path, assistant="copilot-cli")
    with pytest.raises(ModelPolicyError, match="requirements-analyst"):
        build_governance_plan(profile)
