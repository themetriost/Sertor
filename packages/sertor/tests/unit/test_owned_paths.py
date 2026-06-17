"""Invariant `plan ⊆ owned` (T025, D3, FR-017): the static ownership covers every plan target.

This guard-rail replaces a persisted manifest: if a plan artifact's `target_rel` is not declared in
`sertor_owned_paths`, the test fails naming the uncovered artifact — so adding a plan artifact
without declaring its ownership cannot slip through silently.
"""
from __future__ import annotations

import pytest

from sertor_install_kit.assistant import AssistantId
from sertor_installer.install_rag import build_rag_plan
from sertor_installer.install_rag import sertor_owned_paths as rag_owned
from sertor_installer.install_wiki import build_install_plan
from sertor_installer.install_wiki import sertor_owned_paths as wiki_owned
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

_ASSISTANTS = [AssistantId.CLAUDE, AssistantId.COPILOT, AssistantId.COPILOT_CLI]


def _covered(target_rel: str, owned) -> bool:
    """A plan target is covered if it equals or is nested under any owned dir/file/shared edit."""
    rel = target_rel.replace("\\", "/")
    for declared in owned.covered_targets():
        d = declared.replace("\\", "/").rstrip("/")
        if rel == d or rel.startswith(d + "/"):
            return True
    return False


@pytest.mark.parametrize("assistant", _ASSISTANTS)
def test_rag_plan_subset_of_owned(tmp_path, assistant):
    opts = RagInstallOptions(target_root=tmp_path, backend="azure")
    profile = RagHostProfile.from_options(opts)
    plan = build_rag_plan(profile, mcp_scope="project", assistant=assistant)
    owned = rag_owned(assistant)
    uncovered = [a.target_rel for a in plan if not _covered(a.target_rel, owned)]
    assert uncovered == [], f"rag/{assistant.value}: uncovered plan targets {uncovered}"


@pytest.mark.parametrize("assistant", _ASSISTANTS)
def test_rag_plan_local_scope_subset_of_owned(tmp_path, assistant):
    opts = RagInstallOptions(target_root=tmp_path, backend="azure", mcp_scope="local")
    profile = RagHostProfile.from_options(opts)
    plan = build_rag_plan(profile, mcp_scope="local", assistant=assistant)
    owned = rag_owned(assistant)
    # MCP_REGISTER uses a sentinel label, not a repo path → it is not a filesystem target.
    uncovered = [
        a.target_rel for a in plan
        if not _covered(a.target_rel, owned) and not a.target_rel.startswith("(")
    ]
    assert uncovered == [], f"rag/{assistant.value} local: uncovered {uncovered}"


@pytest.mark.parametrize("assistant", _ASSISTANTS)
def test_wiki_plan_subset_of_owned(assistant):
    plan = build_install_plan(assistant)
    owned = wiki_owned(assistant)
    # STRUCTURE target is "wiki/" — covered by the owned_dir "wiki".
    uncovered = [a.target_rel for a in plan if not _covered(a.target_rel, owned)]
    assert uncovered == [], f"wiki/{assistant.value}: uncovered plan targets {uncovered}"


def test_cross_assistant_intersection_keeps_shared(tmp_path):
    """The intersection of owned paths across assistants is preserved in a cross-assistant upgrade.

    FR-016: artifacts common to A and B (e.g. the standalone hook script for copilot vs copilot-cli)
    are not removed when switching between them.
    """
    copilot = rag_owned(AssistantId.COPILOT)
    copilot_cli = rag_owned(AssistantId.COPILOT_CLI)
    shared = copilot.covered_targets() & copilot_cli.covered_targets()
    # Copilot and Copilot-CLI share the `.github/**` host surfaces (only the MCP container differs).
    assert ".github/hooks/sertor-rag-usage-check.ps1" in shared
