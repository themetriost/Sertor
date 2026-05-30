"""Demo a pagamento — Tappa 3C: query GraphRAG (local search) sul grafo indicizzato.

Marcato `paid`: effettua una chiamata LLM ad Azure. Skippato salvo `--run-paid`.
La local search è la più economica (≈1 chiamata). Eseguire con:
    .venv/Scripts/python.exe -m pytest tests/test_graphrag_query.py --run-paid
"""
from __future__ import annotations

import pytest

from conftest import GRAG_PY, run


@pytest.mark.paid
def test_local_search(need_grag_artifacts):
    r = run(["-m", "graphrag", "query", "--root", "03-graphrag/grag",
             "--method", "local", "What is OAuth2PasswordBearer?"],
            py=GRAG_PY, extra_env={"LITELLM_LOCAL_MODEL_COST_MAP": "True"}, timeout=300)
    assert r.returncode == 0, r.stderr
    assert "oauth2passwordbearer" in r.stdout.lower()
