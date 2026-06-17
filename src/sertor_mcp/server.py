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

from sertor_core.composition import build_facade, build_graph_service, enable_observability
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import RetrievalResult, SymbolHit
from sertor_core.observability.logging import log_event

mcp = FastMCP(
    "sertor-rag",
    instructions=(
        "Retrieval over an indexed corpus (code + documentation) with the Sertor engine. "
        "Use search_code for implementations/symbols, search_docs for conceptual explanations, "
        "search_combined when both are needed. Always cite the file (path#chunk)."
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
                  error=type(exc).__name__, detail=str(exc))
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
def search_combined(query: str, k: int = 6) -> list[dict]:
    """Search CODE + DOCS together: when both implementation and explanation are needed."""
    return _run("search_combined", _facade().search_combined, query, k)


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
        log_event(logging.ERROR, "mcp.self_test.error", error=type(exc).__name__, detail=str(exc))
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
        # wiki/log/2026-06-17). Start the server regardless: `_facade()` is not cached on failure, so
        # the first tool call retries and the actionable error surfaces through `_guard` as a tool
        # error — not as a dropped connection.
        log_event(logging.ERROR, "mcp.warmup.error", error=type(exc).__name__, detail=str(exc))
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
