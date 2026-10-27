"""Schemi JSON dei contratti di SkillAuthor.

Fonte: specs/004-skill-authoring/contracts/; per agent-lint specs/005-agent-review/contracts/; per
agent-diff, agent-forms e le estensioni di review e ready specs/006-agent-authoring/contracts/.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

SCHEMA_NAMES = (
    "evals",
    "grading",
    "verdict",
    "review",
    "lint",
    "ready",
    "agent-lint",
    "agent-diff",
    "agent-forms",
)


@cache
def load_schema(name: str) -> dict:
    """Restituisce lo schema `<name>.schema.json` del pacchetto."""

    if name not in SCHEMA_NAMES:
        raise KeyError(f"schema sconosciuto: {name}")
    text = resources.files(__package__).joinpath(f"{name}.schema.json").read_text(encoding="utf-8")
    return json.loads(text)
