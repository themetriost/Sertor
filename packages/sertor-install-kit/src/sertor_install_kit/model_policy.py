"""Versioned model-policy profile for Copilot CLI custom-agents (E2-FEAT-015).

Single source of truth, agent -> model-ID, shared by `sertor` and `sertor-flow` without
either depending on `sertor-core` (the kit is the one dependency both already share). Bump
a model-ID by editing ONE entry here (RNF-2/CS-3); bump `MODEL_POLICY_VERSION` when the bump
is a deliberate POLICY change (FR-007/NFR-004), not merely a persona/body edit elsewhere.
"""
from __future__ import annotations

from sertor_install_kit.errors import ModelPolicyError

MODEL_POLICY_VERSION = "1"

# Fonte unica agente -> model-ID (FR-005). Default ragionato iniziale (spec §Policy):
# meccanico/dispatcher -> economico/veloce; scrittura/reasoning/sintesi -> capace.
_MODEL_POLICY: dict[str, str] = {
    "concierge": "claude-haiku-4.5",
    "configuration-manager": "claude-haiku-4.5",
    "requirements-analyst": "claude-sonnet-4.6",
    "requirements": "claude-sonnet-4.6",
    "wiki-curator": "claude-sonnet-4.6",
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
