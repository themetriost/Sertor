"""Test US5 (qualità) — precision@k su corpus ground-truth, baseline = prototipo (SC-004, DA-003).

La soglia di accettazione si fissa quando il baseline reale è disponibile (decisione "misurare
prima", DA-003). Finché manca, il test è marcato `xfail`: documenta il criterio senza bloccare la
pipeline. La struttura (corpus → query note → chunk attesi → precision@k) è già pronta.
"""
from __future__ import annotations

import pytest

from sertor_core.services.retrieval import RetrievalFacade
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

# (query, chunk_id atteso fra i top-k). Da sostituire con un corpus ground-truth reale.
_GROUND_TRUTH: list[tuple[str, str]] = []

_BASELINE_PRECISION_AT_5 = 0.67  # riferimento prototipo locale Ollama (da confermare con misura)


@pytest.mark.integration
@pytest.mark.xfail(reason="ground-truth e baseline reali da fissare in fase di misura (DA-003)",
                   strict=False)
def test_precision_at_5_meets_baseline():
    assert _GROUND_TRUTH, "corpus ground-truth non ancora definito"
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    facade = RetrievalFacade(emb, store, "ground-truth", default_k=5)

    hits_ok = 0
    for query, expected_id in _GROUND_TRUTH:
        ids = {h.chunk_id for h in facade.search_combined(query, k=5)}
        hits_ok += 1 if expected_id in ids else 0
    precision = hits_ok / len(_GROUND_TRUTH)
    assert precision >= _BASELINE_PRECISION_AT_5
