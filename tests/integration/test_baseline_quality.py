"""Test US4 (qualità) — soglia hit@5 vs baseline prototipo (SC-002, DA-1/DA-3).

La soglia di accettazione si fissa alla misura reale (decisione "misurare prima"): finché manca un
ground-truth reale il test è `xfail`, documenta il criterio senza bloccare la pipeline.
"""
from __future__ import annotations

import pytest

from sertor_core.config.settings import Settings
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.engines.evaluation import evaluate
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

# ground-truth reale (query → file attesi) da fissare in fase di misura sul corpus di dogfooding
_GROUND_TRUTH: list[tuple[str, list[str]]] = []
_BASELINE_HIT_AT_5 = 0.67  # riferimento prototipo locale Ollama (DA-3); cloud ~0.80


@pytest.mark.integration
@pytest.mark.xfail(reason="ground-truth/baseline reali da fissare alla misura (DA-1/DA-3)",
                   strict=False)
def test_hit_at_5_meets_baseline():
    assert _GROUND_TRUTH, "ground-truth non ancora definito"
    settings = Settings.load(env_file=None)
    engine = BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), "quality", settings)
    report = evaluate(engine, _GROUND_TRUTH)
    assert report.hit_rate[5] >= _BASELINE_HIT_AT_5
