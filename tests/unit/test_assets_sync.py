"""Guard test against assets ⇄ `.claude/` drift (T031, D2).

Canonical source = assets in the `sertor_installer` package; the repo's `.claude/` is the
**derived** copy kept in sync by `python -m sertor_installer.sync`. This test compares each file in
`assets/claude/**` with its counterpart in `.claude/`: if they diverge (without a justification
in the allowlist), the drift becomes a CI error.

**Allowlist (permitted differences, D3).** The development `.claude/` may reintroduce `uv run`
before console-scripts (a generic host does not assume `uv`; monorepo development does). The
normalization below neutralizes that difference before comparison. Currently the sync propagates
assets *as-is* (without `uv run`), so copies are identical; the allowlist is documented for the
case where development reintroduces `uv run`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_installer.resources import iter_asset_dir

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLAUDE = _REPO_ROOT / ".claude"


def _normalize(text: str) -> str:
    """Neutralize the permitted difference (allowlist): `uv run sertor-wiki-tools` ↔ script."""
    return text.replace("uv run sertor-wiki-tools", "sertor-wiki-tools")


@pytest.mark.parametrize("rel_path,content", list(iter_asset_dir("claude")))
def test_asset_matches_claude(rel_path: str, content: str):
    dest = _CLAUDE / rel_path
    assert dest.is_file(), (
        f".claude/{rel_path} manca: esegui `python -m sertor_installer.sync` per propagarlo"
    )
    actual = dest.read_text(encoding="utf-8")
    assert _normalize(actual) == _normalize(content), (
        f".claude/{rel_path} è andato in drift rispetto agli assets bundlati. "
        f"Fonte canonica = assets; esegui `python -m sertor_installer.sync`."
    )
