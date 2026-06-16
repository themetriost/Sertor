"""GATE — incremental ≡ full equivalence (046, FEAT-009, T021, SC-002/FR-012).

The cardinal safeguard: after a run that modified, deleted and added a file, the index produced by
the **incremental** path (vector store + BM25 sidecar + code-graph) must be **identical** to the one
produced by a **full rebuild** on the same source. Offline: Chroma + mock embedder, no cloud.

It also checks the cost win (SC-001): the incremental run re-embeds far fewer chunks than the full.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from sertor_core.adapters.graph.networkx_graph import NetworkxCodeGraph
from sertor_core.adapters.lexical.bm25 import Bm25LexicalIndex
from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.config.settings import Settings
from sertor_core.services.index_manifest import IndexManifest
from sertor_core.services.indexing import IndexingService
from tests.fixtures.mocks import CountingEmbedder

pytestmark = pytest.mark.integration

COLL = "equiv__counting"
CORPUS = "equiv"

# Initial corpus: a handful of python modules that call each other (exercises the code-graph) plus
# a markdown doc (exercises mentions + the markdown chunker).
_INITIAL = {
    "alpha.py": "def alpha():\n    return beta()\n",
    "beta.py": "def beta():\n    return 1\n",
    "gamma.py": "def gamma():\n    return alpha()\n",
    "doc.md": "# Guide\n\nThe `alpha` function calls `beta`.\n",
}
# The mutation applied between full-seed and the incremental run:
#   - alpha.py MODIFIED, beta.py DELETED, delta.py ADDED, gamma.py + doc.md UNCHANGED.
_MUTATED = {
    "alpha.py": "def alpha():\n    return delta()\n",  # modified (now calls delta)
    "gamma.py": "def gamma():\n    return alpha()\n",   # unchanged
    "delta.py": "def delta():\n    return 42\n",        # added
    "doc.md": "# Guide\n\nThe `alpha` function calls `beta`.\n",  # unchanged
}


def _write_corpus(root: Path, files: dict[str, str]) -> None:
    for existing in root.glob("*"):
        if existing.is_file():
            existing.unlink()
    for rel, text in files.items():
        (root / rel).write_text(text, encoding="utf-8")


def _settings(index_dir: Path, incremental: bool) -> Settings:
    return replace(
        Settings.load(env_file=None),
        index_dir=index_dir,
        corpus=CORPUS,
        index_incremental=incremental,
    )


def _service(index_dir: Path, embedder, incremental: bool) -> IndexingService:
    settings = _settings(index_dir, incremental)
    return IndexingService(
        embedder,
        ChromaStore(persist_dir=index_dir),
        COLL,
        settings,
        lexical=Bm25LexicalIndex(index_dir),
        graph=NetworkxCodeGraph(index_dir, CORPUS),
        manifest=IndexManifest(index_dir),
    )


# --------------------------------------------------------------------- state extraction

def _vector_state(index_dir: Path) -> dict[str, tuple[tuple[float, ...], dict]]:
    """Map chunk_id -> (vector, metadata) from the Chroma collection (order-independent)."""
    import chromadb

    client = chromadb.PersistentClient(path=str(index_dir))
    coll = client.get_collection(name=COLL)
    got = coll.get(include=["embeddings", "metadatas"])
    out: dict[str, tuple[tuple[float, ...], dict]] = {}
    for cid, vec, meta in zip(got["ids"], got["embeddings"], got["metadatas"], strict=True):
        out[cid] = (tuple(round(float(x), 6) for x in vec), dict(meta or {}))
    return out


def _bm25_entries(index_dir: Path) -> set[tuple]:
    """Set of BM25 sidecar entries (order-independent: the build order may differ)."""
    sidecar = index_dir / "lexical" / f"{COLL}.json"
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    return {
        (e["chunk_id"], e["path"], e["doc_type"], e["text"]) for e in data["entries"]
    }


def _graph_artifact(index_dir: Path) -> dict:
    """Nodes+edges of the code-graph artifact (already sorted by extract_graph)."""
    artifact = index_dir / "graph" / f"{CORPUS}.json"
    data = json.loads(artifact.read_text(encoding="utf-8"))
    return {
        "nodes": sorted(tuple(sorted(n.items())) for n in data["nodes"]),
        "edges": sorted(tuple(sorted(e.items())) for e in data["edges"]),
    }


# --------------------------------------------------------------------- the gate

def test_incremental_equals_full(tmp_path):
    inc_dir = tmp_path / "incremental"
    full_dir = tmp_path / "full"
    inc_repo = tmp_path / "repo_inc"
    full_repo = tmp_path / "repo_full"
    inc_repo.mkdir()
    full_repo.mkdir()

    # --- INCREMENTAL branch: seed full, then mutate + incremental run ---------------------------
    inc_embedder = CountingEmbedder(dim=12, name="counting")
    inc_svc = _service(inc_dir, inc_embedder, incremental=True)
    _write_corpus(inc_repo, _INITIAL)
    inc_svc.index(inc_repo)                       # full seed (no manifest yet)
    inc_embedder.embedded.clear()
    _write_corpus(inc_repo, _MUTATED)
    inc_report = inc_svc.index(inc_repo)          # incremental refresh
    assert inc_report.mode == "incremental"
    assert inc_report.updated == 1 and inc_report.removed == 1 and inc_report.added == 1
    incremental_embedded = len(inc_embedder.embedded)

    # --- FULL branch: index the mutated source from scratch -------------------------------------
    full_embedder = CountingEmbedder(dim=12, name="counting")
    full_svc = _service(full_dir, full_embedder, incremental=False)
    _write_corpus(full_repo, _MUTATED)
    full_report = full_svc.index(full_repo, rebuild=True)
    assert full_report.mode == "full"
    full_embedded = len(full_embedder.embedded)

    # --- EQUIVALENCE (FR-012): the three artifacts are identical --------------------------------
    assert _vector_state(inc_dir) == _vector_state(full_dir)
    assert _bm25_entries(inc_dir) == _bm25_entries(full_dir)
    assert _graph_artifact(inc_dir) == _graph_artifact(full_dir)

    # --- COST WIN (SC-001): incremental re-embeds strictly fewer chunks than the full -----------
    assert incremental_embedded < full_embedded


def test_incremental_query_coherent_after_refresh(tmp_path):
    """A query over the incrementally refreshed index returns the fresh state (no stale chunk)."""
    inc_dir = tmp_path / "q_inc"
    repo = tmp_path / "q_repo"
    repo.mkdir()
    svc = _service(inc_dir, CountingEmbedder(dim=12, name="counting"), incremental=True)
    _write_corpus(repo, _INITIAL)
    svc.index(repo)
    _write_corpus(repo, _MUTATED)
    svc.index(repo)

    state = _vector_state(inc_dir)
    chunk_ids = set(state)
    # beta.py was deleted: none of its chunks survive.
    assert not any(cid.startswith("beta.py#") for cid in chunk_ids)
    # delta.py was added; alpha.py + gamma.py + doc.md remain.
    assert any(cid.startswith("delta.py#") for cid in chunk_ids)
    assert any(cid.startswith("alpha.py#") for cid in chunk_ids)
