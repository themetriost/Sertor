"""Test of `reconcile` (feature 017): read-only detection of `status: superseded` pages."""
from __future__ import annotations

import json
from pathlib import Path

from sertor_core.wiki_tools.__main__ import main
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.reconcile import reconcile
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
"""


def _wiki(tmp_path: Path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    p = load_profile(cfg)
    init_structure(p)
    return cfg, p


def _page(p, rel: str, body: str) -> None:
    f = p.root_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")


def test_reconcile_lists_only_superseded(tmp_path):
    _, p = _wiki(tmp_path)
    _page(p, "concepts/old.md", "---\ntitle: Old\ntype: concept\nstatus: superseded\n"
                                "updated: 2026-01-02\nsuperseded_by: concepts/new.md\n---\nOld.\n")
    _page(p, "concepts/new.md", "---\ntitle: New\ntype: concept\n---\nNew.\n")
    res = reconcile(p)
    assert res.clean is False
    assert [c["path"] for c in res.candidates] == ["concepts/old.md"]
    c = res.candidates[0]
    assert c["status"] == "superseded"
    assert c["superseded_by"] == "concepts/new.md"
    assert c["updated"] == "2026-01-02"
    assert c["reason"] == "status: superseded"


def test_reconcile_clean_when_none(tmp_path):
    _, p = _wiki(tmp_path)
    _page(p, "concepts/a.md", "---\ntitle: A\ntype: concept\n---\nA.\n")
    res = reconcile(p)
    assert res.candidates == [] and res.clean is True


def test_reconcile_is_read_only(tmp_path):
    _, p = _wiki(tmp_path)
    _page(p, "concepts/old.md", "---\ntitle: Old\nstatus: superseded\n---\nbody\n")
    _page(p, "concepts/a.md", "---\ntitle: A\n---\nbody\n")
    before = {f: f.read_bytes() for f in p.root_path.rglob("*.md")}
    reconcile(p)
    after = {f: f.read_bytes() for f in p.root_path.rglob("*.md")}
    assert before == after  # no file created/modified/deleted


def test_reconcile_cli_contract(tmp_path, capsys):
    cfg, p = _wiki(tmp_path)
    _page(p, "concepts/old.md", "---\ntitle: Old\nstatus: superseded\n---\nbody\n")
    rc = main(["reconcile", "--config", str(cfg), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert payload["schema"] == "wiki.reconcile/1"
    assert payload["clean"] is False and len(payload["candidates"]) == 1
