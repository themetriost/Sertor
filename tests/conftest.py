"""Fixture e gate di disponibilità per la suite di smoke test dimostrativi.

I test invocano gli **stessi comandi** documentati in `DEMOS.md` come sottoprocessi e
verificano output/return code. Questo li rende fedeli alle demo reali ed evita gli import
tra cartelle con nomi non-pacchetto (`01-baseline`, ...).

Gate: i test che richiedono un backend (Ollama, Azure) o artefatti (indice Chroma, grafo
AST, parquet GraphRAG, venv isolato) vengono **skippati** se l'ambiente non è pronto, così
la suite resta sempre eseguibile. I test a pagamento sono marcati `@pytest.mark.paid` e
skippati salvo `--run-paid`.
"""
from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
GRAG_PY = ROOT / "03-graphrag" / ".venv-grag" / "Scripts" / "python.exe"
INDEX_DIR = ROOT / "01-baseline" / ".index"
AST_GRAPH = ROOT / "03-graphrag" / ".index" / "code_graph.graphml"
GRAG_OUTPUT = ROOT / "03-graphrag" / "grag" / "output"


# --------------------------------------------------------------------------- helpers
def run(args: list[str], *, py: Path = VENV_PY, extra_env: dict | None = None,
        timeout: int = 300) -> subprocess.CompletedProcess:
    """Esegue uno script del repo col python indicato, da ROOT, con PYTHONPATH=ROOT."""
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run([str(py), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=timeout)


def ollama_up() -> bool:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    if not host.startswith("http"):
        host = "http://" + host
    # 0.0.0.0 è un indirizzo di bind (tutte le interfacce), non di connessione → usa loopback
    host = host.replace("0.0.0.0", "127.0.0.1")
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def azure_ready() -> bool:
    return bool(os.environ.get("AZURE_OPENAI_API_KEY")) and bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))


# --------------------------------------------------------------------------- pytest config
def pytest_addoption(parser):
    parser.addoption("--run-paid", action="store_true", default=False,
                     help="Esegui anche i test marcati 'paid' (chiamate API a pagamento).")


def pytest_configure(config):
    config.addinivalue_line("markers", "paid: il test effettua chiamate API a pagamento (skip salvo --run-paid)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-paid"):
        return
    skip_paid = pytest.mark.skip(reason="test a pagamento: usa --run-paid per eseguirlo")
    for item in items:
        if "paid" in item.keywords:
            item.add_marker(skip_paid)


# --------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def need_chroma():
    if not (INDEX_DIR / "chroma.sqlite3").exists():
        pytest.skip("indice Chroma assente: esegui `python 01-baseline/index.py --provider all`")


@pytest.fixture
def need_ollama():
    if not ollama_up():
        pytest.skip("Ollama non raggiungibile (avvia `ollama serve`)")


@pytest.fixture
def need_ast_graph():
    if not AST_GRAPH.exists():
        pytest.skip("grafo AST assente: esegui `python 03-graphrag/build_graph.py`")


@pytest.fixture
def need_grag_artifacts():
    if not (GRAG_OUTPUT / "entities.parquet").exists():
        pytest.skip("artefatti GraphRAG assenti: esegui l'indicizzazione (vedi DEMOS.md)")
    if not GRAG_PY.exists():
        pytest.skip("venv isolato GraphRAG assente (03-graphrag/.venv-grag)")
