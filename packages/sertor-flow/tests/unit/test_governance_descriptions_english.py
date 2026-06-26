"""Anti-regression: governance asset `description:` frontmatter is English (E12-FEAT-013).

The `description:` is the field a host's main flow reads to decide whether to invoke a skill/agent.
From an English-speaking main flow, an Italian description undertriggers (the trigger phrases never
match). FEAT-013 (audit ISSUE-02) rewrote the `requirements` skill and the `requirements-analyst` /
`configuration-manager` agents to trigger-rich English. This pin fails if a future edit reintroduces
Italian into those descriptions, by detecting common Italian function-word spies.

Scope: ONLY the `description:` line (not the body — body language is governed elsewhere). Offline,
pure asset reads. A meta-test guards the spy heuristic against false positives on English text.
"""
from __future__ import annotations

from sertor_install_kit import read_asset_text

_ANCHOR = "sertor_flow"
_GOVERNANCE_BODIES = (
    "claude/agents/configuration-manager.md",
    "claude/agents/requirements-analyst.md",
    "claude/skills/requirements/SKILL.md",
)

# Italian function-word spies (surrounded by spaces so substrings inside English words don't match,
# e.g. "perfect" must not hit " per "). These appear in virtually any Italian sentence but in no
# normal English one; a description containing one is almost certainly Italian.
_ITALIAN_SPIES = (
    " che ",
    " della ",
    " per ",
    " requisiti ",
    " del ",
    " con ",
    " una ",
    " sul ",
)


def _description_line(rel: str) -> str:
    """The raw `description:` frontmatter value of an asset (may be a quoted YAML scalar)."""
    text = read_asset_text(_ANCHOR, rel)
    for line in text.splitlines():
        if line.startswith("description:"):
            return line
    raise AssertionError(f"no description: line in {rel}")


def test_governance_descriptions_are_not_italian():
    offenders: list[str] = []
    for rel in _GOVERNANCE_BODIES:
        desc = _description_line(rel).lower()
        for spy in _ITALIAN_SPIES:
            if spy in desc:
                offenders.append(f"{rel} → Italian spy {spy!r}")
    assert not offenders, f"Italian leaked into governance descriptions: {offenders}"


def test_italian_spy_heuristic_meta():
    """Meta: the heuristic flags Italian and leaves English alone (no false positive)."""
    italian = "description: analista dei requisiti che trasforma un'idea per il design del progetto"
    english = (
        "description: turns a raw idea into structured requirements. use it whenever requirements "
        "must be written. triggers on 'write the requirements' or starting a new feature."
    )
    assert any(spy in italian.lower() for spy in _ITALIAN_SPIES), "should detect Italian"
    assert not any(spy in english.lower() for spy in _ITALIAN_SPIES), "should not flag English"
