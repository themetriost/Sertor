"""Test of `sertor-wiki-tools` `--config` auto-discovery (feature 016, T010).

Verifies profile resolution when `--config` is omitted: `./wiki.config.toml` then
`./wiki/wiki.config.toml` (with root = CWD), and `ConfigError` if neither is present. No network;
CWD is simulated with `monkeypatch.chdir`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_core.wiki_tools.__main__ import _resolve_config, main
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.structure import init_structure

_CONFIG = """\
profile = "code+doc"
language = "it"
root = "wiki"
index_file = "index.md"
log_file = "log.md"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
"""


def _init(cfg_path: Path, root_override: Path) -> None:
    cfg_path.write_text(_CONFIG, encoding="utf-8")
    init_structure(load_profile(cfg_path, root_override=root_override))


def _scan_schema(capsys) -> str:
    return json.loads(capsys.readouterr().out.splitlines()[-1])["schema"]


def test_discovery_config_in_root(tmp_path, monkeypatch, capsys):
    _init(tmp_path / "wiki.config.toml", tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["scan", "--json"]) == 0
    assert _scan_schema(capsys) == "wiki.scan/1"


def test_discovery_config_in_wiki_subdir(tmp_path, monkeypatch, capsys):
    (tmp_path / "wiki").mkdir()
    _init(tmp_path / "wiki" / "wiki.config.toml", tmp_path)
    monkeypatch.chdir(tmp_path)
    # config only in wiki/: auto root = CWD → relative paths resolve from the host root
    assert main(["scan", "--json"]) == 0
    assert _scan_schema(capsys) == "wiki.scan/1"


def test_discovery_none_found_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["scan", "--json"]) == 1
    assert "error" in capsys.readouterr().err


def test_explicit_config_bypasses_discovery(tmp_path, monkeypatch, capsys):
    other = tmp_path / "custom"
    other.mkdir()
    _init(other / "wiki.config.toml", other)
    monkeypatch.chdir(tmp_path)  # CWD without config
    assert main(["scan", "--config", str(other / "wiki.config.toml"), "--json"]) == 0
    assert _scan_schema(capsys) == "wiki.scan/1"


def test_resolve_config_order_and_root(tmp_path, monkeypatch):
    """Unit test of the resolver + host-agnostic assertion (F4): only paths relative to CWD."""
    monkeypatch.chdir(tmp_path)
    # no config → explicit error
    with pytest.raises(ConfigError):
        _resolve_config(None, None)
    # only in wiki/ → relative path + auto root = "."
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "wiki.config.toml").write_text("x", encoding="utf-8")
    assert _resolve_config(None, None) == ("wiki/wiki.config.toml", ".")
    # explicit --root wins over auto-setting
    assert _resolve_config(None, "/custom/root") == ("wiki/wiki.config.toml", "/custom/root")
    # config in root takes precedence over subdirectory
    (tmp_path / "wiki.config.toml").write_text("x", encoding="utf-8")
    assert _resolve_config(None, None) == ("wiki.config.toml", None)
    # explicit --config bypasses discovery
    assert _resolve_config("altrove/x.toml", None) == ("altrove/x.toml", None)
    # host-agnostic: returned paths are relative to CWD, no absolute reference to Sertor
    cfg, _root = _resolve_config(None, None)
    assert not Path(cfg).is_absolute()
