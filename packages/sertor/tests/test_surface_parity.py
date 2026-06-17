"""Surface parity tests (feature 044, SC-002; surface-mapping.md prop.1 + prop.5).

For each capability in scope (`wiki`, `rag`), the set of host-facing surfaces produced for
`copilot-cli` must cover those produced for `claude` (or declare a gap; there are none in scope).
Plus the coexistence edge case: installing both assistants on the same host leaves both
configurations present without a double instruction block. The VS Code (`copilot`) target was
removed (FEAT-012) — parity is now verified on the two remaining targets.
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.assistant import AssistantId
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_rag import build_rag_plan
from sertor_installer.install_wiki import build_install_plan, execute_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions


def _wiki_kinds(assistant: AssistantId) -> set[str]:
    return {a.kind.value for a in build_install_plan(assistant)}


def _rag_kinds(assistant: AssistantId, tmp_path: Path) -> set[str]:
    profile = RagHostProfile.from_options(
        RagInstallOptions(target_root=tmp_path, backend="azure")
    )
    return {a.kind.value for a in build_rag_plan(profile, with_deps=True, assistant=assistant)}


# ---------------------------------------------------------------- prop.1: coverage

def test_wiki_copilot_cli_covers_claude_surfaces():
    claude = _wiki_kinds(AssistantId.CLAUDE)
    copilot = _wiki_kinds(AssistantId.COPILOT_CLI)
    # every artifact KIND present for claude has a rendering for copilot-cli (no silent omission)
    assert claude <= copilot, f"wiki surfaces missing for copilot-cli: {claude - copilot}"


def test_rag_copilot_cli_covers_claude_surfaces(tmp_path: Path):
    claude = _rag_kinds(AssistantId.CLAUDE, tmp_path / "a")
    copilot = _rag_kinds(AssistantId.COPILOT_CLI, tmp_path / "b")
    assert claude <= copilot, f"rag surfaces missing for copilot-cli: {claude - copilot}"


# ---------------------------------------------------------------- prop.5: coexistence

def test_claude_and_copilot_coexist_no_double_block(tmp_path: Path):
    profile_c = build_host_profile(tmp_path)
    execute_plan(build_install_plan(AssistantId.CLAUDE), profile_c, AssistantId.CLAUDE)
    profile_g = build_host_profile(tmp_path)
    execute_plan(build_install_plan(AssistantId.COPILOT_CLI), profile_g, AssistantId.COPILOT_CLI)

    # both instruction containers exist, each with its own single block
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    copilot_md = (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert claude_md.count("SERTOR:WIKI-RITUAL START") == 1
    assert copilot_md.count("SERTOR:WIKI-RITUAL START") == 1
    # the two configurations live in distinct trees
    assert (tmp_path / ".claude").is_dir()
    assert (tmp_path / ".github").is_dir()
