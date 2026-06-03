"""Fixtures condivise dei test del nucleo.

`sample_repo` copia il mini-repo versionato in una temp dir e vi **inietta** gli artefatti da
escludere (una `.venv/` e un file `*.key`): questi non sono versionati (sono in `.gitignore`),
quindi vengono creati a runtime per rendere il test di esclusione ripetibile su qualunque clone.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

_SAMPLE = Path(__file__).parent / "fixtures" / "sample_repo"
# Ciò che NON va copiato dal sorgente (verrà iniettato a runtime in modo deterministico).
_IGNORE = shutil.ignore_patterns(".venv", "venv", "*.key", "__pycache__")


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Un repo di esempio multilinguaggio + artefatti da escludere, in una temp dir."""
    root = tmp_path / "repo"
    shutil.copytree(_SAMPLE, root, ignore=_IGNORE)

    # Artefatti che l'ingestione deve escludere (REQ-002):
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
