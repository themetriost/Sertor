"""Test US1 — caricamento/validazione del profilo dell'ospite (FR-001, Principio IV/X)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_core.wiki_tools.profile import load_profile

_DOC_ONLY = Path(__file__).parents[1] / "fixtures" / "doc_only_host" / "wiki.config.toml"
_SERTOR = Path(__file__).parents[2] / "wiki" / "wiki.config.toml"  # feature 016: config in wiki/


def _write(tmp: Path, body: str) -> Path:
    cfg = tmp / "wiki.config.toml"
    cfg.write_text(body, encoding="utf-8")
    return cfg


def test_load_valid_profile_from_disk():
    p = load_profile(_DOC_ONLY)
    assert p.profile == "doc-only"
    assert p.language == "en"
    assert p.root == "knowledge"
    assert p.source_dirs == ["docs"]
    assert {e.name for e in p.taxonomy} == {"guides", "reference"}
    assert p.rag.get("enabled") is False


def test_sertor_default_profile_is_external_file():
    # Il default = profilo Sertor è un FILE esterno, non costanti nel codice (Principio X).
    p = load_profile(_SERTOR)
    assert p.profile == "code+doc"
    assert p.language == "it"
    assert p.root == "wiki"
    assert "src" in p.source_dirs


def test_missing_config_raises_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_profile(tmp_path / "assente.toml")


def test_malformed_toml_raises_config_error(tmp_path):
    cfg = _write(tmp_path, "this is not = valid = toml [[[")
    with pytest.raises(ConfigError):
        load_profile(cfg)


def test_missing_required_field_raises(tmp_path):
    cfg = _write(tmp_path, 'language = "it"\nroot = "wiki"\n')  # niente taxonomy
    with pytest.raises(ConfigError):
        load_profile(cfg)


def test_missing_root_raises(tmp_path):
    cfg = _write(
        tmp_path,
        'language = "it"\n[[taxonomy]]\nname="c"\ndir="c"\ntype="concept"\n',
    )
    with pytest.raises(ConfigError):
        load_profile(cfg)


def test_root_override_changes_resolution(tmp_path):
    cfg = _write(
        tmp_path,
        'language = "it"\nroot = "wiki"\n[[taxonomy]]\nname="c"\ndir="c"\ntype="concept"\n',
    )
    other = tmp_path / "altrove"
    other.mkdir()
    p = load_profile(cfg, root_override=other)
    assert p.root_path == other / "wiki"


def test_taxonomy_dir_missing_is_skipped_not_error(tmp_path):
    cfg = _write(
        tmp_path,
        'language = "it"\nroot = "wiki"\n'
        '[[taxonomy]]\nname="c"\ndir="concepts"\ntype="concept"\n'
        '[[taxonomy]]\nname="t"\ndir="tech"\ntype="tech"\n',
    )
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)  # 'tech' assente sul disco
    p = load_profile(cfg)
    present = {e.name for e in p.existing_taxonomy()}
    assert present == {"c"}  # 'tech' (dir mancante) saltata, non errore


def test_duplicate_taxonomy_names_raise(tmp_path):
    cfg = _write(
        tmp_path,
        'language = "it"\nroot = "wiki"\n'
        '[[taxonomy]]\nname="c"\ndir="c"\ntype="concept"\n'
        '[[taxonomy]]\nname="c"\ndir="d"\ntype="concept"\n',
    )
    with pytest.raises(ConfigError):
        load_profile(cfg)
