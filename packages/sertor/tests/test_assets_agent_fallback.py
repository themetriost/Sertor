"""Guard B: the shell agents STOP on a missing asset instead of proceeding blind (E10-FEAT-019).

`concierge`, `wiki-curator` and `requirements-analyst` are thin *shells*: their real procedure
lives in a skill/playbook they read at runtime. If that asset is not deposited (a broken install, a
host without it), the agent must STOP and tell the user, not improvise. This suite asserts each body
carries the stable fallback tokens (host-agnostic, byte-identical across hosts), so the guard fails
if the fallback is ever removed.

Offline (no `uv`, no network): reads the canonical bundled bodies directly from disk.
"""
from __future__ import annotations

import pathlib

# tests/ → sertor → packages → repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

_AGENT_PATHS = {
    "concierge": _REPO_ROOT
    / "packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md",
    "wiki-curator": _REPO_ROOT
    / "packages/sertor/src/sertor_installer/assets/claude/agents/wiki-curator.md",
    "requirements-analyst": _REPO_ROOT
    / "packages/sertor-flow/src/sertor_flow/assets/claude/agents/requirements-analyst.md",
}

# Stable tokens the fallback rule must carry, per agent (data-model §3).
_EXPECTED_TOKENS = {
    "concierge": ("STOP", "guided-setup", "cannot be resolved or read"),
    "wiki-curator": ("STOP", "wiki-playbook", "cannot be resolved or read"),
    "requirements-analyst": ("STOP", "requirements", "cannot be resolved or read"),
}


def _agent_bodies() -> list[tuple[str, pathlib.Path, str]]:
    """(name, path, text) for the three shell agents. Anti-vacuity: exactly three, all present."""
    out: list[tuple[str, pathlib.Path, str]] = []
    for name, path in _AGENT_PATHS.items():
        assert path.is_file(), f"{name}: missing canonical body at {path}"
        out.append((name, path, path.read_text(encoding="utf-8")))
    assert len(out) == 3, out
    return out


def test_agent_fallback_tokens_present():
    """B: every shell agent body contains the stable STOP-on-missing-asset tokens."""
    for name, path, text in _agent_bodies():
        for token in _EXPECTED_TOKENS[name]:
            assert token in text, f"{name} ({path}): token '{token}' missing from the fallback rule"


def test_meta_fallback_assertion_fails_without_stop():
    """Anti-vacuity: a body missing the `STOP` token fails the token assertion."""
    synthetic = "Read the guided-setup skill if it cannot be resolved or read, just proceed."
    assert "STOP" not in synthetic  # → the per-token assertion above would fail for such a body
