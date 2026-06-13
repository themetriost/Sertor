"""Adapter `CodeGraph` on networkx with a persisted JSON artifact (FEAT-005).

Deliberate asymmetry (research G1): `build()` is pure JSON serialisation — it works WITHOUT
the `graph` extra, so `index()` always produces the artifact; NAVIGATION imports networkx
lazily and, if the extra is missing, raises an actionable `ConfigError` (DA-5).

The artifact lives in `<index_dir>/graph/<corpus>.json` — namespaced by corpus ONLY: the graph
does not depend on the embedding provider (research G5). Versioned format `sertor.graph/1`,
atomic write (tmp+rename). Two absence semantics: graph not built →
`GraphNotFoundError`; symbol absent → empty results (FR-007/FR-017).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from collections import Counter
from pathlib import Path

from sertor_core.domain.entities import (
    ContextBundle,
    GraphData,
    GraphNode,
    SymbolHit,
)
from sertor_core.domain.errors import ConfigError, GraphNotFoundError
from sertor_core.observability.logging import log_event

_FORMAT = "sertor.graph/1"
_SYMBOL_KINDS = ("class", "function", "method")


class NetworkxCodeGraph:
    """`CodeGraph` on nx.DiGraph lazily loaded from the JSON artifact."""

    def __init__(
        self,
        index_dir: Path | str,
        corpus: str,
        *,
        limits: tuple[int, int, int] = (10, 8, 8),
    ):
        self._dir = Path(index_dir) / "graph"
        self._corpus = corpus
        self._limits = limits  # (definitions, relations, docs) for get_context (FR-016)
        # per-corpus cache: (DiGraph, nodes by id, name→ids index) — invalidated by build/reset.
        self._cache: dict[str, tuple] = {}

    def _artifact(self, corpus: str) -> Path:
        return self._dir / f"{corpus}.json"

    # --- build (without extra, FR-005/FR-008) ----------------------------------------------------

    def build(self, corpus: str, data: GraphData) -> None:
        started = time.perf_counter()
        self._dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": _FORMAT,
            "corpus": corpus,
            "coverage": {lang: list(kinds) for lang, kinds in data.coverage},
            "nodes": [
                {"id": n.id, "kind": n.kind, "name": n.name, "path": n.path,
                 "line": n.line, "qualname": n.qualname}
                for n in data.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "type": e.type} for e in data.edges
            ],
        }
        fd, tmp_name = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.replace(tmp_name, self._artifact(corpus))
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        self._cache.pop(corpus, None)
        # The adapter emits the event: it knows the path and counts (FR-026, fix analyze I1).
        log_event(
            logging.INFO,
            "graph_build",
            corpus=corpus,
            graph_path=str(self._artifact(corpus)),
            nodes_by_kind=dict(Counter(n.kind for n in data.nodes)),
            edges_by_type=dict(Counter(e.type for e in data.edges)),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    # --- lazy loading (with extra, DA-5) ---------------------------------------------------------

    def _load(self):
        if self._corpus in self._cache:
            return self._cache[self._corpus]
        artifact = self._artifact(self._corpus)
        if not artifact.exists():
            raise GraphNotFoundError(
                "graph not found: build it (index) before querying",
                corpus=self._corpus,
            )
        try:
            import networkx as nx
        except ImportError as exc:
            raise ConfigError(
                "code-graph navigation requires the extra: "
                'uv add "sertor-core[graph]"',
                key="graph",
            ) from exc
        try:
            payload = json.loads(artifact.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"corrupt graph artifact: {artifact} — rebuild it with a re-index",
            ) from exc
        if payload.get("format") != _FORMAT:
            raise ConfigError(
                f"unrecognised graph format ({payload.get('format')!r}): "
                f"{artifact} — rebuild it with a re-index",
            )
        graph = nx.DiGraph()
        by_id: dict[str, GraphNode] = {}
        name_index: dict[str, list[str]] = {}
        for item in payload.get("nodes", []):
            node = GraphNode(item["id"], item["kind"], item["name"], item["path"],
                             item.get("line"), item.get("qualname"))
            by_id[node.id] = node
            graph.add_node(node.id)
            if node.kind in _SYMBOL_KINDS:
                name_index.setdefault(node.name, []).append(node.id)
        for item in payload.get("edges", []):
            graph.add_edge(item["source"], item["target"], type=item["type"])
        for ids in name_index.values():
            ids.sort()
        self._cache[self._corpus] = (graph, by_id, name_index)
        return self._cache[self._corpus]

    # --- navigation (FR-013..018) ----------------------------------------------------------------

    @staticmethod
    def _hit(node: GraphNode) -> SymbolHit:
        qual = node.qualname or node.name
        return SymbolHit(path=node.path, line=node.line, kind=node.kind,
                         qualname=qual, ref=f"{node.path}#{qual}")

    def _symbol_ids(self, name: str) -> list[str]:
        _, _, name_index = self._load()
        return name_index.get(name, [])

    def _logged(self, operation: str, symbol: str, results: int, started: float) -> None:
        log_event(
            logging.INFO,
            "graph_query",
            graph_operation=operation,
            symbol=symbol,
            results=results,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    def find_symbol(self, name: str) -> list[SymbolHit]:
        started = time.perf_counter()
        _, by_id, _ = self._load()
        hits = sorted((self._hit(by_id[nid]) for nid in self._symbol_ids(name)),
                      key=lambda h: h.ref)
        self._logged("find_symbol", name, len(hits), started)
        return hits

    def _incoming(self, name: str, edge_type: str) -> list[GraphNode]:
        graph, by_id, _ = self._load()
        targets = set(self._symbol_ids(name))
        sources = {
            src for target in targets
            for src, _, data in graph.in_edges(target, data=True)
            if data.get("type") == edge_type
        }
        return [by_id[s] for s in sorted(sources) if s in by_id]

    def _outgoing(self, name: str, edge_type: str) -> list[GraphNode]:
        graph, by_id, _ = self._load()
        sources = set(self._symbol_ids(name))
        targets = {
            dst for source in sources
            for _, dst, data in graph.out_edges(source, data=True)
            if data.get("type") == edge_type
        }
        return [by_id[t] for t in sorted(targets) if t in by_id]

    def who_calls(self, name: str) -> list[SymbolHit]:
        started = time.perf_counter()
        hits = [self._hit(n) for n in self._incoming(name, "calls")]
        self._logged("who_calls", name, len(hits), started)
        return hits

    def related_docs(self, name: str) -> list[str]:
        started = time.perf_counter()
        docs = sorted(n.path for n in self._incoming(name, "mentions") if n.kind == "doc")
        self._logged("related_docs", name, len(docs), started)
        return docs

    def get_context(self, name: str) -> ContextBundle:
        started = time.perf_counter()
        defs_limit, rel_limit, docs_limit = self._limits
        bundle = ContextBundle(
            definitions=tuple(self.find_symbol(name)[:defs_limit]),
            callers=tuple(self._hit(n) for n in self._incoming(name, "calls")[:rel_limit]),
            callees=tuple(self._hit(n) for n in self._outgoing(name, "calls")[:rel_limit]),
            bases=tuple(self._hit(n) for n in self._outgoing(name, "inherits")[:rel_limit]),
            docs=tuple(sorted(n.path for n in self._incoming(name, "mentions")
                              if n.kind == "doc")[:docs_limit]),
        )
        self._logged("get_context", name, len(bundle.definitions), started)
        return bundle

    # --- state -----------------------------------------------------------------------------------

    def exists(self, corpus: str) -> bool:
        return self._artifact(corpus).exists()

    def reset(self, corpus: str) -> None:
        self._artifact(corpus).unlink(missing_ok=True)  # absent = no-op
        self._cache.pop(corpus, None)
