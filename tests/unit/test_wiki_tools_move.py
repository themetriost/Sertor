"""Test of `move` (feature 017): form-preserving link rewrite, dry-run, collision, recovery."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_core.wiki_tools.__main__ import main
from sertor_core.wiki_tools.lint import lint
from sertor_core.wiki_tools.move import move
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.structure import init_structure

_CONFIG = """\
profile = "code+doc"
language = "en"
root = "wiki"
index_file = "index.md"
log_file = "log.md"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"

[[taxonomy]]
name = "experiments"
dir = "experiments"
type = "experiment"
"""


def _wiki(tmp_path: Path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    p = load_profile(cfg)
    init_structure(p)
    return cfg, p


def _page(p, rel: str, body: str) -> Path:
    f = p.root_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    return f


def test_move_rewrites_path_form_links_same_stem(tmp_path):
    _, p = _wiki(tmp_path)
    _page(p, "concepts/a.md", "# A\n")
    b = _page(p, "concepts/b.md", "See [[a]], [[concepts/a]], [[concepts/a.md]], [[a|Alias]].\n")
    res = move(p, "concepts/a.md", "experiments/a.md")
    assert res.moved is True
    assert (p.root_path / "experiments/a.md").is_file()
    assert not (p.root_path / "concepts/a.md").exists()
    text = b.read_text("utf-8")
    # same stem ("a"): stem links remain; only path-form links change
    assert "[[a]]" in text and "[[a|Alias]]" in text
    assert "[[experiments/a]]" in text and "[[experiments/a.md]]" in text
    assert "[[concepts/a]]" not in text and "[[concepts/a.md]]" not in text


def test_move_rename_rewrites_stem_links(tmp_path):
    _, p = _wiki(tmp_path)
    _page(p, "concepts/a.md", "# A\n")
    b = _page(p, "concepts/b.md", "Link [[a]] and [[a|Alias]] and [[concepts/a]].\n")
    move(p, "concepts/a.md", "concepts/c.md")
    text = b.read_text("utf-8")
    assert "[[c]]" in text and "[[c|Alias]]" in text and "[[concepts/c]]" in text
    assert "[[a]]" not in text and "[[a|Alias]]" not in text


def test_move_rewrites_relative_md_link(tmp_path):
    _, p = _wiki(tmp_path)
    _page(p, "concepts/a.md", "# A\n")
    b = _page(p, "experiments/b.md", "Go [here](../concepts/a.md#sec) please.\n")
    move(p, "concepts/a.md", "concepts/c.md")
    text = b.read_text("utf-8")
    assert "(../concepts/c.md#sec)" in text


def test_move_dry_run_changes_nothing(tmp_path):
    _, p = _wiki(tmp_path)
    a = _page(p, "concepts/a.md", "# A\n")
    b = _page(p, "concepts/b.md", "[[concepts/a]]\n")
    before = b.read_bytes()
    res = move(p, "concepts/a.md", "experiments/a.md", dry_run=True)
    assert res.dry_run is True and res.rewritten          # plan computed
    assert a.is_file() and not (p.root_path / "experiments/a.md").exists()  # no move
    assert b.read_bytes() == before                       # no rewrite


def test_move_collision_errors_no_change(tmp_path):
    _, p = _wiki(tmp_path)
    _page(p, "concepts/a.md", "# A\n")
    dest = _page(p, "experiments/a.md", "# existing\n")
    before = dest.read_bytes()
    with pytest.raises(ConfigError):
        move(p, "concepts/a.md", "experiments/a.md")
    assert (p.root_path / "concepts/a.md").is_file()      # source intact
    assert dest.read_bytes() == before                    # destination not overwritten


def test_move_source_not_found_errors(tmp_path):
    _, p = _wiki(tmp_path)
    with pytest.raises(ConfigError):
        move(p, "concepts/ghost.md", "concepts/x.md")


def test_move_recovery_completes_rewrites(tmp_path):
    # Partial state: file ALREADY at destination, one link still points to the old form.
    _, p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "# A (already moved)\n")     # dest present
    b = _page(p, "concepts/b.md", "[[concepts/a]]\n")          # residual link
    res = move(p, "concepts/a.md", "experiments/a.md")        # src absent, dest present
    assert res.moved is False                                  # no move (recovery)
    assert "[[experiments/a]]" in b.read_text("utf-8")        # rewrite completed


def test_move_then_lint_no_broken_links(tmp_path):
    _, p = _wiki(tmp_path)
    _page(p, "concepts/a.md", "---\ntitle: A\ntype: concept\ntags: [x]\ncreated: 2026-01-01\n"
                              "updated: 2026-01-02\n---\n# A\n")
    _page(p, "concepts/b.md", "---\ntitle: B\ntype: concept\ntags: [x]\ncreated: 2026-01-01\n"
                              "updated: 2026-01-02\n---\nSee [[concepts/a]].\n")
    move(p, "concepts/a.md", "experiments/a.md")
    assert lint(p).broken_links == []


def test_move_cli_dispatch(tmp_path, capsys):
    cfg, p = _wiki(tmp_path)
    _page(p, "concepts/a.md", "# A\n")
    _page(p, "concepts/b.md", "[[concepts/a]]\n")
    rc = main(["move", "concepts/a.md", "experiments/a.md", "--config", str(cfg), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert payload["schema"] == "wiki.move/1" and payload["moved"] is True


def test_move_cli_requires_dest(tmp_path, capsys):
    cfg, _ = _wiki(tmp_path)
    rc = main(["move", "concepts/a.md", "--config", str(cfg)])
    assert rc == 1
    assert "error" in capsys.readouterr().err
