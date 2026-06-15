"""Unit tests for `build_governance_plan` (T035): derivation, canonical order, exclusions."""
from __future__ import annotations

from pathlib import Path

from sertor_flow.install_governance import build_governance_plan
from sertor_flow.profile import build_governance_profile
from sertor_install_kit import ArtifactKind, WriteStrategy


def _plan(tmp_path: Path):
    profile = build_governance_profile(tmp_path)
    return build_governance_plan(profile)


def test_plan_derives_file_entries_from_asset_subtrees(tmp_path: Path):
    """The plan enumerates the FILE entries by walking assets/claude and assets/specify (FR-005)."""
    plan = _plan(tmp_path)
    claude_files = [a for a in plan if a.target_rel.startswith(".claude/")]
    specify_files = [
        a
        for a in plan
        if a.target_rel.startswith(".specify/")
        and a.kind is ArtifactKind.FILE
        and a.target_rel not in (".specify/NOTICE", ".specify/LICENSES/spec-kit-MIT.txt")
    ]
    # The dogfood subset ships a couple dozen assets; assert a real, non-trivial bundle.
    assert len(claude_files) >= 20
    assert len(specify_files) >= 20


def test_plan_adding_an_asset_changes_the_plan(tmp_path: Path, monkeypatch):
    """Adding an asset to the composition adds an artifact to the plan (FR-005)."""
    import sertor_flow.install_governance as ig

    real_iter = ig.iter_asset_dir

    def fake_iter(anchor, rel):
        yield from real_iter(anchor, rel)
        if rel == "claude":
            yield "skills/extra-skill/SKILL.md", "extra"

    baseline = len(_plan(tmp_path))
    monkeypatch.setattr(ig, "iter_asset_dir", fake_iter)
    augmented = build_governance_plan(build_governance_profile(tmp_path))
    assert len(augmented) == baseline + 1
    assert any(a.target_rel == ".claude/skills/extra-skill/SKILL.md" for a in augmented)


def test_plan_canonical_order(tmp_path: Path):
    """Order: claude/specify FILEs → constitution → generated → NOTICE/license → marker."""
    plan = _plan(tmp_path)
    kinds_targets = [(a.kind, a.target_rel, a.strategy) for a in plan]

    # constitution starter is a CONFIG with CREATE_IF_ABSENT
    constitution_idx = next(
        i for i, (k, t, _) in enumerate(kinds_targets) if t == ".specify/memory/constitution.md"
    )
    # generated init files are CONFIG/GENERATE_CONFIG
    init_idx = next(
        i for i, (k, t, s) in enumerate(kinds_targets) if t == ".specify/init-options.json"
    )
    notice_idx = next(i for i, (k, t, _) in enumerate(kinds_targets) if t == ".specify/NOTICE")
    marker_idx = next(
        i for i, (k, t, _) in enumerate(kinds_targets) if k is ArtifactKind.MARKER_BLOCK
    )

    # all claude/specify FILEs come before the constitution
    _file_prefixes = (
        ".claude/",
        ".specify/templates",
        ".specify/scripts",
        ".specify/extensions",
    )
    last_file_idx = max(
        i
        for i, (k, t, _) in enumerate(kinds_targets)
        if t.startswith(_file_prefixes)
    )
    assert last_file_idx < constitution_idx < init_idx < notice_idx < marker_idx


def test_generated_init_uses_config_generate_no_new_kind(tmp_path: Path):
    """Generated init/integration files use CONFIG + GENERATE_CONFIG (F10/F12: no new kind)."""
    plan = _plan(tmp_path)
    generated = [a for a in plan if a.strategy is WriteStrategy.GENERATE_CONFIG]
    assert generated, "expected generated init/integration artifacts"
    for a in generated:
        assert a.kind is ArtifactKind.CONFIG
    targets = {a.target_rel for a in generated}
    assert ".specify/init-options.json" in targets
    assert ".specify/integration.json" in targets


def test_feature_json_never_in_plan(tmp_path: Path):
    """The runtime-only `.specify/feature.json` is never an asset / artifact (DA-e)."""
    plan = _plan(tmp_path)
    assert all(not a.target_rel.endswith("feature.json") for a in plan)
    assert all(a.source is None or "feature.json" not in a.source for a in plan)


def test_marker_block_targets_claude_md(tmp_path: Path):
    """The SDLC ritual block targets CLAUDE.md."""
    plan = _plan(tmp_path)
    markers = [a for a in plan if a.kind is ArtifactKind.MARKER_BLOCK]
    assert len(markers) == 1
    assert markers[0].target_rel == "CLAUDE.md"
