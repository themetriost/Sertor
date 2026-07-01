"""G3 — filtro sorgenti: spec/requisiti sempre fuori; doc opzionali; codice/config sempre dentro."""

from __future__ import annotations

from speclift.config import DEFAULT_CONFIG
from speclift.domain.models import Changeset, FileChange
from speclift.stages.filter_sources import excluded_notes, filter_source_files


def _cs(*paths: str) -> Changeset:
    return Changeset(
        ref="HEAD",
        kind="commit",
        files=[FileChange(path=p, change_type="modified") for p in paths],
    )


def _kept(changeset: Changeset) -> set[str]:
    return {f.path for f in changeset.files}


def test_spec_and_requirements_always_excluded():
    cs = _cs(
        "specs/011-x/spec.md",
        "specs/011-x/tasks.md",
        "requirements/foo/requirements.md",
        ".specify/feature.json",
        "src/app.py",
    )
    kept, excluded = filter_source_files(cs, DEFAULT_CONFIG, include_docs=True)  # anche con doc ON
    assert _kept(kept) == {"src/app.py"}
    assert {p for p, _ in excluded} == {
        "specs/011-x/spec.md",
        "specs/011-x/tasks.md",
        "requirements/foo/requirements.md",
        ".specify/feature.json",
    }
    assert all(reason == "specifica/requisiti" for _, reason in excluded)


def test_code_and_config_always_included():
    cs = _cs("src/app.py", "crates/core/lib.rs", "pyproject.toml", "config/app.json", "settings.yaml")
    kept, excluded = filter_source_files(cs, DEFAULT_CONFIG, include_docs=False)
    assert _kept(kept) == {
        "src/app.py",
        "crates/core/lib.rs",
        "pyproject.toml",
        "config/app.json",
        "settings.yaml",
    }
    assert excluded == []


def test_docs_excluded_by_default():
    cs = _cs("README.md", "CLAUDE.md", "docs/guide.rst", "src/app.py")
    kept, excluded = filter_source_files(cs, DEFAULT_CONFIG, include_docs=False)
    assert _kept(kept) == {"src/app.py"}
    assert {p for p, _ in excluded} == {"README.md", "CLAUDE.md", "docs/guide.rst"}
    assert all(reason == "documentazione" for _, reason in excluded)


def test_docs_included_when_flag_on():
    cs = _cs("README.md", "docs/guide.rst", "src/app.py")
    kept, excluded = filter_source_files(cs, DEFAULT_CONFIG, include_docs=True)
    assert _kept(kept) == {"README.md", "docs/guide.rst", "src/app.py"}
    assert excluded == []


def test_spec_excluded_even_with_docs_on():
    """Spec/requisiti restano fuori anche col flag doc: sono categorie diverse."""
    cs = _cs("specs/x/spec.md", "README.md")
    kept, _ = filter_source_files(cs, DEFAULT_CONFIG, include_docs=True)
    assert _kept(kept) == {"README.md"}


def test_excluded_notes_summarizes():
    notes = excluded_notes([("specs/x/spec.md", "specifica/requisiti"), ("README.md", "documentazione")])
    assert len(notes) == 1
    assert "specs/x/spec.md" in notes[0]
    assert "README.md" in notes[0]
    assert excluded_notes([]) == []
