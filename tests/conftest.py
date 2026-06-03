"""Fixtures condivise dei test del nucleo.

`sample_repo` copia il mini-repo versionato in una temp dir e vi **inietta** gli artefatti da
escludere (una `.venv/` e un file `*.key`): questi non sono versionati (sono in `.gitignore`),
quindi vengono creati a runtime per rendere il test di esclusione ripetibile su qualunque clone.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import pytest

from tests.fixtures.mocks import FakeEmbedder, FakeLLM, InMemoryStore


@pytest.fixture(autouse=True)
def _isolate_environ():
    """Isola `os.environ` tra i test.

    `Settings.load()` usa `load_dotenv(override=True)`, che muta `os.environ` in modo permanente
    leggendo il `.env` dello sviluppatore. Senza ripristino, la config locale (RAG_BACKEND=azure)
    inquinerebbe i test sui default. Salva e ripristina l'ambiente dopo ogni test.
    """
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


@pytest.fixture(autouse=True)
def _reset_sertor_logger():
    """Isola lo stato del logger `sertor_core` tra i test.

    La CLI (`observability.configure`) muta il logger globale (handler/level/propagate); senza
    ripristino, `caplog` (che si appoggia alla propagazione verso root) si romperebbe nei test
    successivi. Salva e ripristina lo stato dopo ogni test.
    """
    lg = logging.getLogger("sertor_core")
    saved_handlers, saved_level, saved_propagate = list(lg.handlers), lg.level, lg.propagate
    yield
    lg.handlers = saved_handlers
    lg.setLevel(saved_level)
    lg.propagate = saved_propagate

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


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def wiki_sandbox(tmp_path: Path) -> Path:
    """Una radice wiki inizializzata in temp (mai il wiki di produzione, RNF-002/R-W5)."""
    from sertor_core.wiki.structure import create_wiki

    root = tmp_path / "wiki"
    create_wiki(root, today="2026-06-03")
    return root


@pytest.fixture
def wiki_with_issues(wiki_sandbox: Path) -> Path:
    """Wiki sandbox con problemi noti per il lint (FEAT-007): link rotto, orfano, fuori-indice, contraddizione."""  # noqa: E501
    fm = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
          "updated: 2026-06-03\nsources: []\n---\n\n# {t}\n\n")
    # alpha: orfana, fuori indice, con un link rotto [[ghost]] (e uno valido [[beta]])
    (wiki_sandbox / "concepts" / "alpha.md").write_text(
        fm.format(t="Alpha") + "Vedi [[beta]] e anche [[ghost]] (rotto).\n", encoding="utf-8")
    # beta: referenziata da alpha (non orfana) ma fuori indice
    (wiki_sandbox / "concepts" / "beta.md").write_text(
        fm.format(t="Beta") + "Pagina beta.\n", encoding="utf-8")
    # contraddizione marcata (come la inserisce ingest di FEAT-003)
    (wiki_sandbox / "concepts" / "contraddetta.md").write_text(
        fm.format(t="Contraddetta") + "> ⚠️ Contraddizione (fonte [[beta]]): valori divergenti.\n",
        encoding="utf-8")
    return wiki_sandbox
