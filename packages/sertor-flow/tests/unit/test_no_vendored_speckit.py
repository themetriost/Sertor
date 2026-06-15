"""US1 guard — the bundle no longer vendors SpecKit (T010, feature 045).

After the launch-installer pivot, `sertor-flow` obtains SpecKit by launching `specify init`, so the
bundled `assets/` MUST NOT contain SpecKit copies anymore: no `claude/skills/speckit-*`, no
`claude/agents/speckit-*`, no `specify/**`. The Sertor-authored surfaces (requirements,
requirements-analyst, configuration-manager) and the constitution-starter remain. This guard fails
if a SpecKit asset is re-introduced (regression to vendoring).
"""
from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable


def _assets() -> Traversable:
    return files("sertor_flow") / "assets"


def _exists(rel: str) -> bool:
    node: Traversable = _assets()
    for part in rel.split("/"):
        node = node / part
    return node.is_dir() or node.is_file()


def _children(rel: str) -> list[str]:
    node: Traversable = _assets()
    for part in rel.split("/"):
        node = node / part
    if not node.is_dir():
        return []
    return [c.name for c in node.iterdir()]


def test_no_vendored_speckit_skills():
    """No `assets/claude/skills/speckit-*` directories remain."""
    offenders = [name for name in _children("claude/skills") if name.startswith("speckit-")]
    assert not offenders, f"vendored speckit skills must be removed: {offenders}"


def test_no_vendored_speckit_agents():
    """No `assets/claude/agents/speckit-*.md` files remain."""
    offenders = [name for name in _children("claude/agents") if name.startswith("speckit-")]
    assert not offenders, f"vendored speckit agents must be removed: {offenders}"


def test_no_vendored_specify_tree():
    """The whole `assets/specify/**` machinery is gone (now from `specify init`)."""
    assert not _exists("specify"), "assets/specify/** must be removed (obtained via launch)"


def test_sertor_authored_surfaces_remain():
    """Sertor-authored surfaces are kept (not removed by the pivot)."""
    assert _exists("claude/skills/requirements/SKILL.md")
    assert _exists("claude/agents/requirements-analyst.md")
    assert _exists("claude/agents/configuration-manager.md")
    assert _exists("constitution-starter.md")
    assert _exists("claude-md-block-sdlc.md")
