"""Shared fixtures for the core tests.

`sample_repo` copies the versioned mini-repo into a temp dir and **injects** the artifacts to
be excluded (a `.venv/` and a `*.key` file): these are not versioned (they are in `.gitignore`),
so they are created at runtime to make the exclusion test repeatable on any clone.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

_SAMPLE = Path(__file__).parent / "fixtures" / "sample_repo"
# What must NOT be copied from the source (will be injected at runtime deterministically).
_IGNORE = shutil.ignore_patterns(".venv", "venv", "*.key", "__pycache__")


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """A multilanguage sample repo with artifacts to exclude, in a temp dir."""
    root = tmp_path / "repo"
    shutil.copytree(_SAMPLE, root, ignore=_IGNORE)

    # Artifacts that ingestion must exclude (REQ-002):
    venv_file = root / ".venv" / "lib" / "junk.py"
    venv_file.parent.mkdir(parents=True, exist_ok=True)
    venv_file.write_text("def excluded():\n    return True\n", encoding="utf-8")
    (root / "secret.key").write_text("SECRET-API-KEY\n", encoding="utf-8")
    return root


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder(dim=8)


@pytest.fixture
def memory_store() -> InMemoryStore:
    return InMemoryStore()
