"""MCP server `sertor-rag` built on `sertor-core`.

Exposes the core retrieval as **7 MCP tools**: the 3 search tools (code / doc / combined —
using the engine selected by `SERTOR_ENGINE`, default hybrid BM25+RRF, FEAT-004) and the 4
structural navigation tools over the code-graph (`find_symbol`/`who_calls`/`related_docs`/
`get_context`, FEAT-005). Centralised configuration (`.env`: embeddings provider, store backend,
corpus, engine).

**Thin** consumer (Principio I): tools delegate to the `sertor_core` facade and format the
results; no retrieval logic is reimplemented. Retrieval observability is already emitted by the
core (the facade logs `retrieve`/`no_index`); a per-tool log is added here.

Startup (stdio): normally launched by the MCP client via `.mcp.json`
(`python -m sertor_mcp.server`).
"""
from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from functools import lru_cache
from typing import TypeVar

from mcp.server.fastmcp import FastMCP

from sertor_core.composition import (
    build_episodic_search,
    build_facade,
    build_graph_service,
    build_memory_reader,
    build_memory_semantic_index,
    enable_observability,
)
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import RetrievalResult, SymbolHit
from sertor_core.observability.logging import log_event
from sertor_core.observability.scrub import scrub_text
from sertor_core.services.episodic_search import SearchQuery
from sertor_core.services.memory_semantic import SemanticMemoryQuery

mcp = FastMCP(
    "sertor-rag",
    instructions=(
        "Retrieval over an indexed corpus (code + documentation) with the Sertor engine. "
        "Use search_code for implementations/symbols, search_docs for conceptual explanations, "
        "search_combined when both are needed (it returns the two labelled flows "
        "{\"docs\": [...], \"code\": [...]}). Always cite the file (path#chunk). "
        "For episodic memory of past sessions ('did we discuss X before?'), use memory_search "
        "(full-text by default; semantic=true searches by meaning), memory_list and memory_show — "
        "opt-in, off unless SERTOR_MEMORY is set (semantic needs SERTOR_MEMORY_SEMANTIC too); they "
        "return {\"status\": \"disabled\"} when off."
    ),
)

# Maximum length of the text preview for a result: limits the payload sent to the client
# (a server presentation parameter, not a core domain choice).
_PREVIEW = 300


@lru_cache(maxsize=1)
def _facade():
    """Core facade, built once from the configuration (`.env`) and reused."""
    return build_facade(Settings.load())


@lru_cache(maxsize=1)
def _graph():
    """Code-graph service (FEAT-005), memoized like the facade — orthogonal to the engine."""
    return build_graph_service(Settings.load())


@lru_cache(maxsize=1)
def _memory_reader():
    """Memory archive read surface, or `None` when memory is off (E4-FEAT-010, gate SERTOR_MEMORY).

    `lru_cache` memoizes `None` too: with the privacy gate off (default) the builder opens no file
    and the memory tools stay disabled at zero startup cost (they are not exercised in the warm-up).
    """
    return build_memory_reader(Settings.load())


@lru_cache(maxsize=1)
def _episodic():
    """Episodic full-text search, or `None` when memory is off (E4-FEAT-010, gate SERTOR_MEMORY)."""
    return build_episodic_search(Settings.load())


@lru_cache(maxsize=1)
def _memory_semantic():
    """Semantic memory search, or `None` unless BOTH gates are on (E4-FEAT-013, two-layer gate
    SERTOR_MEMORY + SERTOR_MEMORY_SEMANTIC).

    Mirrors the CLI: `build_memory_semantic_index` → `None` when either knob is off. Query path only
    (`allow_download=False`): the MCP is read-only, backfill stays on the CLI `index-semantic`.
    `lru_cache` memoizes `None` too → zero startup cost with the (default) gate off.
    """
    return build_memory_semantic_index(Settings.load(), allow_download=False)


def _fmt(r: RetrievalResult) -> dict:
    """`RetrievalResult` -> dict with stable fields; normalised and truncated preview."""
    flat = " ".join(r.text.split())
    return {
        "path": r.path,
        "source": r.doc_type.value,
        "chunk": r.chunk_id,
        "score": round(r.score, 4),
        "preview": flat if len(flat) <= _PREVIEW else flat[:_PREVIEW] + "…",
    }


_T = TypeVar("_T")


def _guard(tool: str, body: Callable[[], _T]) -> _T:
    """Run a tool body; on failure persist an error event (`mcp.<tool>.error`) then RE-RAISE.

    Visibility, not swallowing: the exception still reaches the MCP client unchanged, but the
    failure is also recorded in the observability store (reliability report) instead of vanishing
    at end-of-turn. This way a broken server (bad key, missing extra, store fault) is not masked
    when a caller degrades to other tools — the failure leaves a durable trace.
    """
    try:
        return body()
    except Exception as exc:
        log_event(logging.ERROR, f"mcp.{tool}.error",
                  error=type(exc).__name__, detail=scrub_text(str(exc)))
        raise


def _run(
    tool: str,
    search: Callable[[str, int], list[RetrievalResult]],
    query: str,
    k: int,
) -> list[dict]:
    """Runs a facade search, formats the results and emits a surface-level log (or error event)."""
    def _body() -> list[dict]:
        results = [_fmt(r) for r in search(query, k)]
        log_event(logging.INFO, f"mcp.{tool}", k=k, results=len(results))
        return results
    return _guard(tool, _body)


@mcp.tool()
def search_code(query: str, k: int = 5) -> list[dict]:
    """Search the source CODE: implementations, functions, classes, usages."""
    return _run("search_code", _facade().search_code, query, k)


@mcp.tool()
def search_docs(query: str, k: int = 5) -> list[dict]:
    """Search the Markdown DOCUMENTATION: explanations, guides, decisions, specs, wiki."""
    return _run("search_docs", _facade().search_docs, query, k)


@mcp.tool()
def search_combined(query: str, k: int = 6) -> dict:
    """Search CODE + DOCS together: when both implementation and explanation are needed.

    Returns the two labelled flows `{"docs": [...], "code": [...]}` (070): the documentation flow
    (the *why*) and the code flow (the *what*), each rank-ordered with its OWN top-k (separate
    budget). A key is always present, with `[]` when its flow is empty. Each element keeps the
    citable `path#chunk` form (`_fmt`).
    """
    def _body() -> dict:
        docs, code = _facade().search_combined(query, k)
        out = {
            "docs": [_fmt(r) for r in docs],
            "code": [_fmt(r) for r in code],
        }
        log_event(
            logging.INFO,
            "mcp.search_combined",
            k=k,
            docs=len(out["docs"]),
            code=len(out["code"]),
        )
        return out
    return _guard("search_combined", _body)


# --- Structural navigation (FEAT-005): thin surfaces over the code-graph -----------------------

def _hit_dict(hit: SymbolHit) -> dict:
    """`SymbolHit` -> citable dict (`ref = path#qualname`, consistent with path#chunk)."""
    return {"path": hit.path, "line": hit.line, "kind": hit.kind,
            "qualname": hit.qualname, "ref": hit.ref}


@mcp.tool()
def find_symbol(name: str) -> list[dict]:
    """Where the symbol (class/function/method) is DEFINED: path, line, kind, qualname.

    Exact lookup on the code-graph, without similarity retrieval. Empty list = symbol
    absent from the graph; explicit error = graph not built (run index first).
    """
    def _body() -> list[dict]:
        hits = [_hit_dict(h) for h in _graph().find_symbol(name)]
        log_event(logging.INFO, "mcp.find_symbol", results=len(hits))
        return hits
    return _guard("find_symbol", _body)


@mcp.tool()
def who_calls(name: str) -> list[dict]:
    """WHO CALLS the symbol: direct callers in the corpus (`calls` edges of the code-graph)."""
    def _body() -> list[dict]:
        hits = [_hit_dict(h) for h in _graph().who_calls(name)]
        log_event(logging.INFO, "mcp.who_calls", results=len(hits))
        return hits
    return _guard("who_calls", _body)


@mcp.tool()
def related_docs(name: str) -> list[dict]:
    """Which DOCUMENTS mention the symbol (`mentions` edges doc→symbol)."""
    def _body() -> list[dict]:
        docs = [{"path": p, "ref": p} for p in _graph().related_docs(name)]
        log_event(logging.INFO, "mcp.related_docs", results=len(docs))
        return docs
    return _guard("related_docs", _body)


@mcp.tool()
def get_context(name: str) -> dict:
    """Multi-hop CONTEXT of the symbol: definitions + callers + callees + bases + linked docs."""
    def _body() -> dict:
        bundle = _graph().get_context(name)
        out = {
            "definitions": [_hit_dict(h) for h in bundle.definitions],
            "callers": [_hit_dict(h) for h in bundle.callers],
            "callees": [_hit_dict(h) for h in bundle.callees],
            "bases": [_hit_dict(h) for h in bundle.bases],
            "docs": list(bundle.docs),
        }
        log_event(logging.INFO, "mcp.get_context", results=len(out["definitions"]))
        return out
    return _guard("get_context", _body)


# --- Conversation memory (E4-FEAT-010): read-only parity with the CLI memory read commands --------
#
# Three thin tools over the SAME core services the CLI uses (MemoryArchive.list_recent/get,
# EpisodicSearch.search), gated by SERTOR_MEMORY exactly like the CLI. When memory is OFF (the
# privacy default) the builders return None and the tool returns an explicit `disabled` state —
# never an empty list (which would masquerade as "no results") and never a raised error (which would
# flood mcp.*.error for the default config). Read-only: no capture/write path here.

_MEMORY_DISABLED = {
    "status": "disabled",
    "hint": "set SERTOR_MEMORY=true in .sertor/.env to enable conversation memory",
}

# Semantic search on: memory is enabled but the semantic layer is not (E4-FEAT-013). Distinct from
# `_MEMORY_DISABLED` so the agent knows WHICH knob to flip — never a silent fallback to full-text.
_SEMANTIC_DISABLED = {
    "status": "disabled",
    "hint": "set SERTOR_MEMORY_SEMANTIC=true in .sertor/.env and backfill with "
            "`sertor-rag memory index-semantic` to enable semantic search",
}


def _turn_dict(turn) -> dict:
    """A `TranscriptTurn` -> dict (full text: this is 'show the session', not a preview)."""
    return {"index": turn.index, "role": turn.role, "ts": turn.ts, "text": turn.text}


@mcp.tool()
def memory_list(limit: int = 0) -> dict:
    """List recent archived conversation sessions (most recent first).

    Returns `{"status": "ok", "sessions": [{session_key, captured_at, turn_count}, ...]}`, or
    `{"status": "disabled", ...}` when conversation memory is off (opt-in, SERTOR_MEMORY). Use a
    `session_key` from here with `memory_show`. `limit <= 0` uses the configured default.
    """
    def _body() -> dict:
        reader = _memory_reader()
        if reader is None:
            return _MEMORY_DISABLED
        lim = limit if limit and limit > 0 else Settings.load().memory_list_limit
        sessions = [
            {"session_key": s.session_key, "captured_at": s.captured_at,
             "turn_count": s.turn_count}
            for s in reader.list_recent(lim)
        ]
        log_event(logging.INFO, "mcp.memory_list", results=len(sessions))
        return {"status": "ok", "sessions": sessions}
    return _guard("memory_list", _body)


@mcp.tool()
def memory_show(session_key: str) -> dict:
    """Show one archived conversation session by its key: its turns (index, role, ts, text).

    Returns `{"status": "ok", "session": {...turns...}}`, `{"status": "ok", "session": null}` when
    the key is unknown, or `{"status": "disabled", ...}` when memory is off. Get a key from
    `memory_list` or `memory_search`.
    """
    def _body() -> dict:
        reader = _memory_reader()
        if reader is None:
            return _MEMORY_DISABLED
        session = reader.get(session_key)
        if session is None:
            log_event(logging.INFO, "mcp.memory_show", found=0)
            return {"status": "ok", "session": None}
        out = {
            "session_key": session.session_key,
            "project_id": session.project_id,
            "captured_at": session.captured_at,
            "adapter_kind": session.adapter_kind,
            "turns": [_turn_dict(t) for t in session.turns],
        }
        log_event(logging.INFO, "mcp.memory_show", found=1, turns=len(out["turns"]))
        return {"status": "ok", "session": out}
    return _guard("memory_show", _body)


def _memory_hit_dict(h) -> dict:
    """A memory hit (full-text OR semantic — same six fields) -> dict."""
    return {"session_key": h.session_key, "captured_at": h.captured_at, "role": h.role,
            "turn_index": h.turn_index, "snippet": h.snippet, "score": round(h.score, 4)}


def _semantic_search(query: str, k: int) -> dict:
    """Semantic branch of `memory_search` (E4-FEAT-013): search by meaning, behind the 2-layer gate.

    `None` from the builder means a knob is off — distinguished via `memory_enabled` so the disabled
    state names the RIGHT knob (SERTOR_MEMORY vs SERTOR_MEMORY_SEMANTIC); NEVER a silent fallback to
    full-text (parity with the CLI `--semantic`).
    """
    settings = Settings.load()
    index = _memory_semantic()
    if index is None:
        return _MEMORY_DISABLED if not settings.memory_enabled else _SEMANTIC_DISABLED
    results = index.search(
        SemanticMemoryQuery(
            text=query,
            limit=k if k and k > 0 else settings.memory_semantic_limit,
        )
    )
    hits = [_memory_hit_dict(h) for h in results.hits]
    # SemanticMemorySearch already emits its event with the query HASHED (never in clear).
    log_event(logging.INFO, "mcp.memory_search", semantic=True, results=len(hits))
    return {"status": "ok", "hits": hits}


@mcp.tool()
def memory_search(query: str, k: int = 0, semantic: bool = False) -> dict:
    """Search the conversation archive: 'have we talked about X before? how did it end?'.

    `semantic=false` (default) → local full-text FTS5 (no cloud, no LLM). `semantic=true` → search
    by MEANING (FEAT-013), behind the opt-in SERTOR_MEMORY + SERTOR_MEMORY_SEMANTIC. Returns
    `{"status": "ok", "hits": [{session_key, captured_at, role, turn_index, snippet, score}, ...]}`
    (most relevant first), or `{"status": "disabled"}` when the relevant knob is off (the hint names
    which one). Open a hit's session with `memory_show`. `k <= 0` uses the default.
    """
    def _body() -> dict:
        if semantic:
            return _semantic_search(query, k)
        search = _episodic()
        if search is None:
            return _MEMORY_DISABLED
        settings = Settings.load()
        results = search.search(
            SearchQuery(
                text=query,
                limit=k if k and k > 0 else settings.episodic_limit,
                snippet_tokens=settings.episodic_snippet_tokens,
            )
        )
        hits = [_memory_hit_dict(h) for h in results.hits]
        # EpisodicSearch already emits `episodic_search` with the query HASHED (never in clear).
        log_event(logging.INFO, "mcp.memory_search", results=len(hits))
        return {"status": "ok", "hits": hits}
    return _guard("memory_search", _body)


def _self_test() -> bool:
    """Exercise the end-to-end search path ONCE at startup so latent faults surface at connect
    time, not at the first real query.

    A trivial search drives both the embedding provider (catches a bad/rotated key → http 401) and
    the lexical/engine path (catches a missing extra → `No module named 'rank_bm25'`) and the store.
    A missing index is NOT a failure (the core degrades to an empty list): only a real fault raises.
    Non-fatal and LOUD: on failure it records an error event AND prints a diagnostic to stderr (so a
    broken server is visible at reconnect), but never blocks startup. Returns True on success.
    """
    try:
        _facade().search_code("__healthcheck__", k=1)
    except Exception as exc:  # noqa: BLE001 — diagnostic probe, must not crash the server
        log_event(logging.ERROR, "mcp.self_test.error",
                  error=type(exc).__name__, detail=scrub_text(str(exc)))
        print(f"[sertor-rag] self-test FAILED: {type(exc).__name__}: {exc}",
              file=sys.stderr, flush=True)
        return False
    log_event(logging.INFO, "mcp.self_test", status="ok")
    return True


def main() -> None:
    """Starts the MCP server on the stdio transport.

    The facade is built **before** starting the stdio loop (eager warm-up): Chroma's lazy
    initialisation inside the first tool call stalls the response on Windows — the task does not
    resume until stdin receives another event (diagnosis 2026-06-12: first session query hung
    indefinitely, unblocked only by cancel). Cost: ~1s at startup, within the client connection
    timeout (30s). Same warm-up for the code-graph (FEAT-005, R-7): loading is TOLERANT —
    a missing graph or absent extra do not prevent startup (the explicit error arrives at the
    tool call, DA-5).
    """
    # persist events if SERTOR_OBSERVABILITY=true (no-op otherwise)
    enable_observability(Settings.load())
    try:
        _facade()  # eager warm-up (Windows hang fix)
        try:
            _graph().find_symbol("__warmup__")  # load artifact + networkx, if available
        except Exception:  # noqa: BLE001 — graph warm-up best-effort, never blocking for startup
            pass
        _self_test()  # end-to-end probe: surface a bad key / missing extra at connect time, loudly
    except Exception as exc:  # noqa: BLE001 — warm-up must NEVER prevent the server from starting
        # A configuration fault (e.g. AZURE_OPENAI_ENDPOINT/API_KEY missing in .sertor/.env) raised
        # by build_facade()/build_embedder() would otherwise crash the process before mcp.run(), and
        # the client only sees an opaque "-32000 Connection closed" (verified on Copilot CLI 1.0.63,
        # wiki/log/2026-06-17). Start the server regardless: `_facade()` is not cached on failure,
        # so the first tool call retries and the actionable error surfaces through `_guard` as a
        # tool error — not as a dropped connection.
        log_event(logging.ERROR, "mcp.warmup.error",
                  error=type(exc).__name__, detail=scrub_text(str(exc)))
        print(
            f"[sertor-rag] startup warm-up FAILED ({type(exc).__name__}: {exc}). "
            "The server will start, but RAG tools will keep returning this error until the "
            "configuration is fixed (e.g. set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in "
            ".sertor/.env).",
            file=sys.stderr, flush=True,
        )
    mcp.run()


if __name__ == "__main__":
    main()
