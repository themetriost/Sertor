"""Smoke test — Tappa 3C: artefatti GraphRAG (parquet) col grafo a entity_types di dominio.

Legge gli artefatti col venv isolato (`.venv-grag`, che ha pandas/pyarrow). Verifica che
la tipizzazione di dominio abbia preso (tipi ⊆ tassonomia attesa) e che il grafo sia ricco.
"""
from __future__ import annotations

from conftest import GRAG_PY, run

DOMAIN_TYPES = {"class", "function", "data_model", "endpoint", "exception", "concept", "library"}

_PROBE = (
    "import pandas as pd;"
    "e=pd.read_parquet('03-graphrag/grag/output/entities.parquet');"
    "r=pd.read_parquet('03-graphrag/grag/output/relationships.parquet');"
    "ts=sorted({str(x).lower() for x in e['type'].dropna().unique() if str(x).strip()});"
    "print('ENTITIES', len(e));"
    "print('RELATIONSHIPS', len(r));"
    "print('TYPES', ','.join(ts))"
)


def _probe(need_grag_artifacts):
    r = run(["-c", _PROBE], py=GRAG_PY)
    assert r.returncode == 0, r.stderr
    out = {}
    for line in r.stdout.splitlines():
        k, _, v = line.partition(" ")
        out[k] = v
    return out


def test_grafo_dominio_ricco(need_grag_artifacts):
    """Il grafo di dominio ha molte entità e relazioni (run sul subset)."""
    out = _probe(need_grag_artifacts)
    assert int(out["ENTITIES"]) > 1000
    assert int(out["RELATIONSHIPS"]) > 2000


def test_tipi_sono_di_dominio(need_grag_artifacts):
    """I tipi di entità appartengono alla tassonomia di dominio (non più organization/event)."""
    out = _probe(need_grag_artifacts)
    types = {t for t in out["TYPES"].split(",") if t}
    extra = types - DOMAIN_TYPES
    assert not extra, f"tipi inattesi fuori tassonomia: {extra}"
    # i tipi-cardine devono essere presenti
    assert {"class", "function", "concept"} <= types
    # i tipi generici del run precedente NON devono comparire
    assert not ({"organization", "event", "geo", "person"} & types)
