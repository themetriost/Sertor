"""Mocks of the domain ports for core tests, without cloud or network access (NFR-01).

`FakeEmbedder` is deterministic (same text → same vector) to exercise idempotency;
`InMemoryStore` implements `VectorStore` with in-memory cosine similarity.
"""
from __future__ import annotations

import hashlib
import math

from sertor_core.domain.entities import (
    ContextBundle,
    DocType,
    EmbeddedChunk,
    GraphData,
    LexicalEntry,
    RetrievalResult,
    SymbolHit,
)
from sertor_core.domain.errors import GraphNotFoundError


class FakeEmbedder:
    """Fake and deterministic embedding provider (small dimension)."""

    def __init__(self, dim: int = 8, batch_size: int = 64):
        self.name = f"fake:{dim}"
        self.dim = dim
        self.batch_size = batch_size
        self.calls = 0

    def _vector(self, text: str) -> list[float]:
        out: list[float] = []
        i = 0
        # Expands a deterministic digest to `dim` components.
        while len(out) < self.dim:
            h = hashlib.sha256(f"{i}:{text}".encode()).digest()
            for b in h:
                out.append(b / 255.0)
                if len(out) >= self.dim:
                    break
            i += 1
        return out

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self.calls += 1
        return [self._vector(t) for t in texts]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class InMemoryStore:
    """In-memory vector store with cosine similarity; namespaced by collection."""

    def __init__(self) -> None:
        # collection -> {chunk_id: (vector, payload)}
        self._data: dict[str, dict[str, tuple[list[float], dict]]] = {}

    def upsert(self, collection: str, records: list[EmbeddedChunk]) -> None:
        coll = self._data.setdefault(collection, {})
        for r in records:
            coll[r.chunk_id] = (r.vector, r.payload)  # idempotent: replaces on same ids

    def query(
        self,
        collection: str,
        vector: list[float],
        k: int,
        doc_type: str = "both",
    ) -> list[RetrievalResult]:
        coll = self._data.get(collection)
        if not coll:
            return []
        scored: list[tuple[float, str, dict]] = []
        for cid, (vec, payload) in coll.items():
            if doc_type != "both" and payload.get("doc_type") != doc_type:
                continue
            scored.append((_cosine(vector, vec), cid, payload))
        scored.sort(key=lambda t: t[0], reverse=True)
        results: list[RetrievalResult] = []
        for score, cid, payload in scored[: max(0, k)]:
            results.append(
                RetrievalResult(
                    text=payload.get("text", ""),
                    path=payload.get("path", ""),
                    chunk_id=cid,
                    doc_type=DocType(payload.get("doc_type", "code")),
                    score=score,
                    metadata=payload.get("metadata"),
                )
            )
        return results

    def delete(self, collection: str, ids: list[str]) -> None:
        coll = self._data.get(collection)
        if not coll:
            return
        for cid in ids:
            coll.pop(cid, None)

    def reset(self, collection: str) -> None:
        self._data.pop(collection, None)   # rebuild-from-scratch (idempotent)

    def exists(self, collection: str) -> bool:
        return bool(self._data.get(collection))

    def list_collections(self) -> list[str]:
        return sorted(self._data)


class InMemoryLexicalIndex:
    """`LexicalIndex` in memory for hybrid engine tests (NFR-03): no file system.

    Elementary but deterministic lexical ranking: counts query token occurrences in the text
    (lowercase), ties resolved by `chunk_id` — sufficient to exercise fusion and policy.
    """

    def __init__(self) -> None:
        self._data: dict[str, list[LexicalEntry]] = {}

    def build(self, collection: str, entries: list[LexicalEntry]) -> None:
        self._data[collection] = list(entries)  # full replacement (idempotent)

    def query(
        self, collection: str, query: str, k: int, doc_type: str = "both"
    ) -> list[str]:
        if k <= 0:
            return []
        entries = self._data.get(collection, [])
        if doc_type != "both":
            entries = [e for e in entries if e.doc_type == doc_type]
        tokens = query.lower().split()
        scored = []
        for e in entries:
            text = e.text.lower()
            score = sum(text.count(t) for t in tokens)
            if score > 0:
                scored.append((score, e.chunk_id))
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [cid for _, cid in scored[:k]]

    def lookup(self, collection: str, chunk_ids: list[str]) -> list[LexicalEntry]:
        by_id = {e.chunk_id: e for e in self._data.get(collection, [])}
        return [by_id[cid] for cid in chunk_ids if cid in by_id]

    def exists(self, collection: str) -> bool:
        return collection in self._data

    def reset(self, collection: str) -> None:
        self._data.pop(collection, None)


class FakeCodeGraph:
    """`CodeGraph` in memory for tests (NFR-03): two distinct absences, no networkx.

    Built on `GraphData`; the active corpus is the one passed to the constructor (like the real
    adapter, which receives corpus/limits from the composition root).
    """

    def __init__(self, corpus: str = "fake", *, limits: tuple[int, int, int] = (10, 8, 8)):
        self._corpus = corpus
        self._limits = limits
        self._data: dict[str, GraphData] = {}

    def build(self, corpus: str, data: GraphData) -> None:
        self._data[corpus] = data  # full replacement (idempotent)

    def _graph(self) -> GraphData:
        if self._corpus not in self._data:
            raise GraphNotFoundError(
                "graph not found: build it (index) before querying",
                corpus=self._corpus,
            )
        return self._data[self._corpus]

    def _hit(self, node) -> SymbolHit:
        qual = node.qualname or node.name
        return SymbolHit(path=node.path, line=node.line, kind=node.kind,
                         qualname=qual, ref=f"{node.path}#{qual}")

    def _symbols(self, name: str) -> list:
        return [n for n in self._graph().nodes
                if n.name == name and n.kind in ("class", "function", "method")]

    def find_symbol(self, name: str) -> list[SymbolHit]:
        return sorted((self._hit(n) for n in self._symbols(name)), key=lambda h: h.ref)

    def _by_id(self) -> dict:
        return {n.id: n for n in self._graph().nodes}

    def who_calls(self, name: str) -> list[SymbolHit]:
        ids = {n.id for n in self._symbols(name)}
        by_id = self._by_id()
        callers = {e.source for e in self._graph().edges if e.type == "calls" and e.target in ids}
        return sorted((self._hit(by_id[c]) for c in callers if c in by_id), key=lambda h: h.ref)

    def related_docs(self, name: str) -> list[str]:
        ids = {n.id for n in self._symbols(name)}
        by_id = self._by_id()
        docs = {e.source for e in self._graph().edges
                if e.type == "mentions" and e.target in ids}
        return sorted(by_id[d].path for d in docs if d in by_id)

    def get_context(self, name: str) -> ContextBundle:
        defs_limit, rel_limit, docs_limit = self._limits
        ids = {n.id for n in self._symbols(name)}
        by_id = self._by_id()
        callees = {e.target for e in self._graph().edges
                   if e.type == "calls" and e.source in ids}
        bases = {e.target for e in self._graph().edges
                 if e.type == "inherits" and e.source in ids}
        return ContextBundle(
            definitions=tuple(self.find_symbol(name)[:defs_limit]),
            callers=tuple(self.who_calls(name)[:rel_limit]),
            callees=tuple(sorted((self._hit(by_id[c]) for c in callees if c in by_id),
                                 key=lambda h: h.ref))[:rel_limit],
            bases=tuple(sorted((self._hit(by_id[b]) for b in bases if b in by_id),
                               key=lambda h: h.ref))[:rel_limit],
            docs=tuple(self.related_docs(name)[:docs_limit]),
        )

    def exists(self, corpus: str) -> bool:
        return corpus in self._data

    def reset(self, corpus: str) -> None:
        self._data.pop(corpus, None)
