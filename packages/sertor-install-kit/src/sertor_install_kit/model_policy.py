"""Versioned model-policy profile for Copilot CLI custom-agents (E2-FEAT-015).

Single source of truth, agent -> model-ID, shared by `sertor` and `sertor-flow` without
either depending on `sertor-core` (the kit is the one dependency both already share). Bump
a model-ID by editing ONE entry here (RNF-2/CS-3); bump `MODEL_POLICY_VERSION` when the bump
is a deliberate POLICY change (FR-007/NFR-004), not merely a persona/body edit elsewhere.
"""
from __future__ import annotations

from sertor_install_kit.errors import ModelPolicyError

MODEL_POLICY_VERSION = "2"

# Fonte unica agente -> model-ID (FR-005). v2 (2026-10-12): famiglia Claude 5.5, abbinamento
# allineato agli alias `model:` degli asset Claude (concierge -> sonnet, wiki-curator -> haiku).
_MODEL_POLICY: dict[str, str] = {
    "concierge": "claude-sonnet-5.5",
    "configuration-manager": "claude-haiku-5.5",
    "requirements-analyst": "claude-sonnet-5.5",
    "requirements": "claude-sonnet-5.5",
    "wiki-curator": "claude-haiku-5.5",
}

IN_SCOPE_AGENTS: frozenset[str] = frozenset(_MODEL_POLICY)


def resolve_model(agent_name: str) -> str:
    """Returns the policy model-ID for `agent_name`; fail-loud if uncovered (FR-008).

    Raises `ModelPolicyError` naming the missing agent — never a silent `None`/default
    (Principio IV/XII). Deterministic (RNF-3): same name + same profile version -> same id.
    """
    try:
        return _MODEL_POLICY[agent_name]
    except KeyError:
        raise ModelPolicyError(
            f"model-policy profile (v{MODEL_POLICY_VERSION}) has no entry "
            f"for in-scope agent {agent_name!r}"
        ) from None
