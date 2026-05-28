"""Smoke test — Tappa 2: hybrid retrieval (BM25 sparse gratis; hybrid gated)."""
from __future__ import annotations

import re

from conftest import run

_RANK = re.compile(r"(?m)^\d+\. \[")


def test_bm25_sparse_simbolo_esatto(need_chroma):
    """BM25 (sparse) trova il simbolo esatto `OAuth2PasswordBearer` nel file security.

    Lessicale puro: nessun embedding/rete → eseguibile offline e deterministico.
    È il punto di forza del ramo sparse (query a simboli esatti del codice).
    """
    r = run(["02-hybrid-reranking/hybrid.py", "OAuth2PasswordBearer",
             "--provider", "ollama", "--mode", "sparse", "-k", "5"])
    assert r.returncode == 0, r.stderr
    assert "oauth2" in r.stdout.lower()


def test_hybrid_fusione_shape(need_chroma, need_ollama):
    """La fusione hybrid (dense+BM25 via RRF) gira e restituisce k risultati ben formati."""
    r = run(["02-hybrid-reranking/hybrid.py", "how to enable CORS",
             "--provider", "ollama", "--mode", "hybrid", "-k", "5"])
    assert r.returncode == 0, r.stderr
    assert len(_RANK.findall(r.stdout)) == 5
