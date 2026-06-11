"""Test di `config_gen` (T021, US1): euristica source_dirs, language, validità load_profile (D7)."""
from __future__ import annotations

from pathlib import Path

from sertor_core.wiki_tools.profile import load_profile
from sertor_installer.config_gen import (
    build_host_profile,
    generate_wiki_config,
)


def test_infer_source_dirs_with_standard_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    profile = build_host_profile(tmp_path)
    assert profile.source_dirs == ["src", "docs"]


def test_infer_source_dirs_empty_repo_falls_back_to_dot(tmp_path: Path):
    profile = build_host_profile(tmp_path)
    assert profile.source_dirs == ["."]


def test_source_dirs_override_bypasses_heuristic(tmp_path: Path):
    (tmp_path / "src").mkdir()
    profile = build_host_profile(tmp_path, source_dirs_override=["app", "lib"])
    assert profile.source_dirs == ["app", "lib"]


def test_language_default_is_en(tmp_path: Path):
    profile = build_host_profile(tmp_path)
    assert profile.language == "en"
    assert 'language = "en"' in generate_wiki_config(profile)


def test_language_it(tmp_path: Path):
    profile = build_host_profile(tmp_path, language="it")
    assert 'language = "it"' in generate_wiki_config(profile)


def test_generated_config_passes_load_profile(tmp_path: Path):
    (tmp_path / "src").mkdir()
    profile = build_host_profile(tmp_path, language="it")
    config_text = generate_wiki_config(profile)
    config_path = tmp_path / "wiki.config.toml"
    config_path.write_text(config_text, encoding="utf-8")

    wiki_profile = load_profile(config_path)
    assert wiki_profile.language == "it"
    assert wiki_profile.root == "wiki"
    assert len(wiki_profile.taxonomy) == 5
    assert wiki_profile.source_dirs == ["src"]
    assert wiki_profile.rag.get("enabled") is False


def test_generated_config_source_dirs_serialized_as_toml_list(tmp_path: Path):
    profile = build_host_profile(tmp_path, source_dirs_override=["src", "docs"])
    config_text = generate_wiki_config(profile)
    assert 'source_dirs = ["src", "docs"]' in config_text


def test_generated_config_has_no_secrets(tmp_path: Path):
    """FR-019: il config generato non deve contenere segreti (api_key/endpoint/token)."""
    profile = build_host_profile(tmp_path, language="it")
    config_text = generate_wiki_config(profile).lower()
    for needle in ("api_key", "apikey", "endpoint", "token", "secret", "password"):
        assert needle not in config_text
