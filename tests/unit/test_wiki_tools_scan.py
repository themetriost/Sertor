"""Test US1 — scan del lavoro pendente; SC-001 (host-agnostico) e SC-003 (parità hook)."""
from __future__ import annotations

import os
import time
from pathlib import Path

from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.scan import scan

_DOC_ONLY = Path(__file__).parents[1] / "fixtures" / "doc_only_host" / "wiki.config.toml"

_CONFIG = """\
profile = "code+doc"
language = "it"
root = "wiki"
log_file = "log.md"
source_dirs = ["src", "specs"]
exclude = [".venv*", "__pycache__"]

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"

[strings]
pending = "Pendenti: {n}"
clean = "Allineato"
"""


def _make_host(tmp_path: Path) -> Path:
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "log.md").write_text("# log\n\n## [2026-06-01] record | seed\n", "utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "specs").mkdir()
    return cfg


def _set_mtime(path: Path, ts: float) -> None:
    os.utime(path, (ts, ts))


def test_scan_counts_files_newer_than_log(tmp_path):
    cfg = _make_host(tmp_path)
    old = time.time() - 1000
    new = time.time() + 1000
    _set_mtime(tmp_path / "wiki" / "log.md", old)
    src_new = tmp_path / "src" / "fresh.py"
    src_new.write_text("x = 1\n", "utf-8")
    _set_mtime(src_new, new)
    src_old = tmp_path / "src" / "stale.py"
    src_old.write_text("y = 2\n", "utf-8")
    _set_mtime(src_old, old - 10)

    result = scan(load_profile(cfg))
    assert result.schema == "wiki.scan/1"
    assert result.pending == 1
    assert result.message == "Pendenti: 1"
    assert set(result.dirs_scanned) == {"src", "specs"}


def test_scan_clean_when_nothing_newer(tmp_path):
    cfg = _make_host(tmp_path)
    new = time.time() + 5000
    _set_mtime(tmp_path / "wiki" / "log.md", new)
    f = tmp_path / "src" / "old.py"
    f.write_text("z = 3\n", "utf-8")
    _set_mtime(f, time.time() - 1000)
    result = scan(load_profile(cfg))
    assert result.pending == 0
    assert result.message == "Allineato"


def test_scan_no_log_means_everything_pending(tmp_path):
    cfg = _make_host(tmp_path)
    (tmp_path / "wiki" / "log.md").unlink()
    (tmp_path / "src" / "a.py").write_text("a\n", "utf-8")
    (tmp_path / "specs" / "b.md").write_text("b\n", "utf-8")
    result = scan(load_profile(cfg))
    assert result.anchor is None
    assert result.pending == 2


def test_scan_respects_exclude(tmp_path):
    cfg = _make_host(tmp_path)
    old = time.time() - 1000
    _set_mtime(tmp_path / "wiki" / "log.md", old)
    venv = tmp_path / "src" / ".venv-core" / "junk.py"
    venv.parent.mkdir(parents=True)
    venv.write_text("junk\n", "utf-8")
    _set_mtime(venv, time.time() + 1000)
    result = scan(load_profile(cfg))
    assert result.pending == 0  # .venv* escluso


def test_sc001_same_scan_on_doc_only_host_unchanged_code(tmp_path):
    # SC-001: lo STESSO scan gira sull'ospite doc-only cambiando solo la config.
    result = scan(load_profile(_DOC_ONLY))
    assert result.schema == "wiki.scan/1"
    assert result.dirs_scanned == ["docs"]  # source-dir diversa, dalla config
    assert "wiki" in result.message.lower() or "work" in result.message.lower()


def test_sc003_parity_with_hook_logic(tmp_path):
    # SC-003: a parità di condizioni il conteggio replica l'euristica mtime dell'hook
    # (file con mtime > mtime(log) contano; gli altri no).
    cfg = _make_host(tmp_path)
    anchor = time.time()
    _set_mtime(tmp_path / "wiki" / "log.md", anchor)
    for i, delta in enumerate((-50, -10, 10, 100, 200)):
        f = tmp_path / "specs" / f"f{i}.md"
        f.write_text("x\n", "utf-8")
        _set_mtime(f, anchor + delta)
    expected = sum(1 for delta in (-50, -10, 10, 100, 200) if delta > 0)
    result = scan(load_profile(cfg))
    assert result.pending == expected
