"""Smoke test — Tappa 1: baseline dense retrieval (gated su Ollama + indice Chroma).

Verifica che la pipeline dense giri e produca output ben formato. La *qualità* del
retrieval (hit-rate@k, MRR) per provider è misurata da `01-baseline/evaluate.py` e
documentata nel wiki — non è oggetto dello smoke test (il provider locale è il più debole).
"""
from __future__ import annotations

import re

from conftest import run

_RANK = re.compile(r"(?m)^\d+\. \[")


def test_dense_retrieval_shape(need_chroma, need_ollama):
    """La similarity search dense restituisce esattamente k risultati ben formati."""
    r = run(["01-baseline/search.py", "declare a request body with a Pydantic model",
             "--provider", "ollama", "-k", "5"])
    assert r.returncode == 0, r.stderr
    assert len(_RANK.findall(r.stdout)) == 5
    # ogni hit espone sorgente/tipo e un path
    assert "[doc/" in r.stdout or "[code/" in r.stdout
