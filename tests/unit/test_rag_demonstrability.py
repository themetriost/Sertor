"""RAG demonstrability — content capture + TUI view (feature 064, FEAT-015).

Pure tests (offline): the content-fields helper (opt-in + scrub), the hit/miss/abstained verdict,
and the RAG tab rendering. The opt-in default-off and scrub are the privacy guards.
"""
from __future__ import annotations

from sertor_core.domain.entities import DocType, ObservedEvent, RetrievalResult
from sertor_core.observability.live import render_rag_report, retrieval_verdict
from sertor_core.services.retrieval import content_fields


def _r(text: str, path: str, score: float) -> RetrievalResult:
    return RetrievalResult(text=text, path=path, chunk_id=f"{path}#0", doc_type=DocType.DOC,
                           score=score)


# --- content_fields (opt-in + scrub) ----------------------------------------------------------

def test_content_fields_disabled_is_empty():
    """Default off: no query/snippet/preview captured (privacy-by-default, REQ-002)."""
    assert content_fields("secret question", [_r("body", "a.md", 0.9)], 5, enabled=False) == {}


def test_content_fields_enabled_carries_query_preview_snippet():
    out = content_fields("how does chunking work", [_r("the chunk body", "chunking.md", 0.812)],
                         5, enabled=True)
    assert out["query"] == "how does chunking work"
    assert out["results_preview"] == ["chunking.md|0.812"]
    assert out["snippet"] == "the chunk body"


def test_content_fields_scrubs_secrets_in_query_and_snippet():
    """REQ-003: secrets are scrubbed from the captured content."""
    out = content_fields("use sk-ABCDEFGH12345678 please",
                         [_r("token=sk-SECRET99999999 here", "x.md", 0.5)], 5, enabled=True)
    assert "sk-ABCDEFGH12345678" not in out["query"] and "[REDACTED]" in out["query"]
    assert "sk-SECRET99999999" not in out["snippet"]


def test_content_fields_empty_results_has_no_snippet():
    out = content_fields("q", [], 5, enabled=True)
    assert out["results_preview"] == [] and "snippet" not in out


# --- verdict (hit / miss / abstained) ---------------------------------------------------------

def test_verdict_hit():
    assert retrieval_verdict({"results": 3}) == "hit"
    assert retrieval_verdict({"fused_k": 5}) == "hit"


def test_verdict_miss_vs_abstained():
    assert retrieval_verdict({"results": 0}) == "miss"
    assert retrieval_verdict({"results": 0, "abstained": True}) == "abstained"
    assert retrieval_verdict({"fused_k": 0, "abstained": False}) == "miss"


# --- render_rag_report ------------------------------------------------------------------------

def test_render_rag_empty_has_call_to_action():
    text = render_rag_report([])
    assert "No RAG content" in text and "SERTOR_OBSERVABILITY_CONTENT" in text


def test_render_rag_shows_query_verdict_and_mcp():
    events = [
        ObservedEvent(ts=1_700_000_000.0, operation="hybrid_query",
                      fields={"fused_k": 2, "query": "what is RRF", "abstained": False,
                              "results_preview": ["hybrid.md|0.7"], "snippet": "RRF fuses ranks"}),
        ObservedEvent(ts=1_700_000_001.0, operation="mcp.search_code", fields={"query": "embed"}),
    ]
    text = render_rag_report(events)
    assert "what is RRF" in text and "hit" in text         # query + verdict
    assert "hybrid.md|0.7" in text and "RRF fuses ranks" in text  # top result + snippet
    assert "mcp.search_code" in text and "embed" in text   # MCP op + its query arg


def test_render_rag_without_content_query_field_is_ignored():
    """A retrieval event WITHOUT a `query` field (content off) is not shown in the RAG view."""
    events = [ObservedEvent(ts=1_700_000_000.0, operation="hybrid_query", fields={"fused_k": 3})]
    assert "No RAG content" in render_rag_report(events)
