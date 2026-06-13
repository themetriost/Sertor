"""Test US2 — idempotent and non-destructive structure init (FR-003, SC-006)."""
from __future__ import annotations

from pathlib import Path

from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.structure import init_structure, validate

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

[[taxonomy]]
name = "tech"
dir = "tech"
type = "tech"
"""


def _profile(tmp_path: Path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    return load_profile(cfg)


def test_init_creates_structure(tmp_path):
    p = _profile(tmp_path)
    res = init_structure(p)
    assert res.schema == "wiki.structure/1"
    assert (tmp_path / "wiki" / "concepts").is_dir()
    assert (tmp_path / "wiki" / "tech").is_dir()
    assert (tmp_path / "wiki" / "index.md").is_file()
    assert (tmp_path / "wiki" / "log.md").is_file()
    assert "concepts" in res.created and "index.md" in res.created


def test_init_is_idempotent(tmp_path):
    p = _profile(tmp_path)
    init_structure(p)
    res2 = init_structure(p)
    assert res2.created == []  # second run: nothing new
    assert set(res2.skipped_existing) >= {"concepts", "tech", "index.md", "log.md"}


def test_init_is_non_destructive(tmp_path):
    # SC-006: pre-existing user index/log are not touched.
    p = _profile(tmp_path)
    (tmp_path / "wiki").mkdir()
    user_index = tmp_path / "wiki" / "index.md"
    user_log = tmp_path / "wiki" / "log.md"
    user_index.write_text("CONTENUTO UTENTE INDEX\n", "utf-8")
    user_log.write_text("CONTENUTO UTENTE LOG\n", "utf-8")

    res = init_structure(p)
    assert user_index.read_text("utf-8") == "CONTENUTO UTENTE INDEX\n"
    assert user_log.read_text("utf-8") == "CONTENUTO UTENTE LOG\n"
    assert "index.md" in res.skipped_existing
    assert "log.md" in res.skipped_existing


def test_validate_reports_missing_frontmatter(tmp_path):
    p = _profile(tmp_path)
    init_structure(p)
    (tmp_path / "wiki" / "concepts" / "rag.md").write_text(
        "---\ntitle: RAG\ntype: concept\n---\nManca created/updated/tags.\n", "utf-8"
    )
    res = validate(p)
    pages = {d["page"]: d["missing"] for d in res.missing_frontmatter}
    assert "concepts/rag.md" in pages
    assert set(pages["concepts/rag.md"]) == {"tags", "created", "updated"}


def test_validate_reports_naming_violation(tmp_path):
    p = _profile(tmp_path)
    init_structure(p)
    (tmp_path / "wiki" / "tech" / "BadName.md").write_text(
        "---\ntitle: X\ntype: tech\ntags: [a]\ncreated: 2026-01-01\nupdated: 2026-01-02\n---\nok\n",
        "utf-8",
    )
    res = validate(p)
    assert any(v["page"] == "tech/BadName.md" for v in res.naming_violations)


# --- D3: seed localized for the host language (content = host language, English fallback) -----

def _profile_lang(tmp_path: Path, language: str):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(
        f'profile = "code+doc"\nlanguage = "{language}"\nroot = "wiki"\n'
        'index_file = "index.md"\nlog_file = "log.md"\n\n'
        '[[taxonomy]]\nname = "concepts"\ndir = "concepts"\ntype = "concept"\n',
        encoding="utf-8",
    )
    return load_profile(cfg)


def test_seed_localized_english(tmp_path):
    init_structure(_profile_lang(tmp_path, "en"))
    assert "Wiki index. Updated by the log operations." in \
        (tmp_path / "wiki" / "index.md").read_text("utf-8")
    assert "Append-only wiki log." in (tmp_path / "wiki" / "log.md").read_text("utf-8")


def test_seed_localized_italian(tmp_path):
    init_structure(_profile_lang(tmp_path, "it"))
    assert "Indice del wiki." in (tmp_path / "wiki" / "index.md").read_text("utf-8")


def test_seed_unknown_language_falls_back_to_english(tmp_path):
    init_structure(_profile_lang(tmp_path, "fr"))   # language not in table → English
    assert "Wiki index." in (tmp_path / "wiki" / "index.md").read_text("utf-8")


def test_seed_language_subtag_normalized(tmp_path):
    init_structure(_profile_lang(tmp_path, "it-IT"))   # subtag → `it`
    assert "Indice del wiki." in (tmp_path / "wiki" / "index.md").read_text("utf-8")
