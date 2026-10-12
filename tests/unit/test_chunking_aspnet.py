"""Test 140 — chunks of ASP.NET pages: markup (US1), inline symbols (US2), degradation (US4)."""
from __future__ import annotations

import logging
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import ChunkerKind, DocType, Document
from sertor_core.services.chunking.aspnet import PAGE_SENTINEL, RAZOR, WEBFORMS
from sertor_core.services.chunking.dispatch import chunk_document

S = Settings.load(env_file=None)
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "aspnet"


def _page(rel: str, language: str, text: str | None = None) -> Document:
    body = text if text is not None else (FIXTURES / rel).read_text(encoding="utf-8")
    return Document(id=rel, text=body, doc_type=DocType.CODE, language=language)


def _chunks(rel: str, language: str = WEBFORMS, text: str | None = None):
    return chunk_document(_page(rel, language, text), S)


def _syntactic(chunks):
    return [c for c in chunks if c.metadata.chunker is ChunkerKind.SYNTACTIC]


def _markup(chunks):
    return [c for c in chunks if c.metadata.chunker is ChunkerKind.SIZE_FALLBACK]


def _degraded(caplog):
    return [r for r in caplog.records if getattr(r, "operation", "") == "aspnet_page_degraded"]


# --- US1: the page is in the corpus and its markup is searchable ---------------------------------


def test_markup_only_page_yields_markup_chunks_and_no_event(caplog):
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        chunks = _chunks("Menu.ascx")
    assert chunks
    assert all(c.metadata.chunker is ChunkerKind.SIZE_FALLBACK for c in chunks)
    assert any("menu-principale" in c.text for c in chunks)
    assert not _degraded(caplog)


def test_markup_chunks_hold_the_markup_but_not_the_extracted_code():
    markup = _markup(_chunks("Default.aspx"))
    joined = "\n".join(c.text for c in markup)
    assert "OrdiniGrid" in joined
    assert "BindGrid" not in joined                       # clarify Q1: no double counting
    assert "<%= FormatTitolo() %>" in joined              # clarify Q3: expressions stay in markup


def test_expressions_never_form_a_chunk_of_their_own():
    syntactic = _syntactic(_chunks("Default.aspx"))
    assert all("FormatTitolo" not in c.text for c in syntactic)
    assert all("Eval(" not in c.text for c in syntactic)


def test_statements_outside_a_symbol_are_module_chunks():
    syntactic = _syntactic(_chunks("Default.aspx"))
    modules = [c for c in syntactic if c.metadata.node_type == "module"]
    assert len(modules) == 1
    assert "foreach (var riga in CaricaRighe())" in modules[0].text
    assert modules[0].metadata.start_line == 14


def test_page_chunks_carry_the_page_language():
    assert {c.metadata.language for c in _chunks("Default.aspx")} == {WEBFORMS}
    assert {c.metadata.language for c in _chunks("Counter.razor", RAZOR)} == {RAZOR}


def test_code_chunks_come_before_markup_chunks():
    kinds = [c.metadata.chunker for c in _chunks("Default.aspx")]
    first_markup = kinds.index(ChunkerKind.SIZE_FALLBACK)
    assert ChunkerKind.SYNTACTIC not in kinds[first_markup:]


def test_chunk_ids_are_stable_across_runs():
    first = [(c.id, c.text) for c in _chunks("Default.aspx")]
    second = [(c.id, c.text) for c in _chunks("Default.aspx")]
    assert first == second


# --- US2: inline symbols, at the real line --------------------------------------------------------


def _symbols(chunks) -> dict[str, int]:
    return {
        c.metadata.qualname: c.metadata.start_line
        for c in _syntactic(chunks)
        if c.metadata.symbol is not None
    }


def test_webforms_inline_methods_have_the_real_line_and_the_file_stem():
    assert _symbols(_chunks("Default.aspx")) == {
        "Default.Page_Load": 5,
        "Default.Helper": 9,
        "Default.Secondo": 18,                              # second script block
    }


def test_same_named_page_in_another_folder():
    assert _symbols(_chunks("Admin/Default.aspx")) == {"Default.Page_Load": 3}


def test_razor_inline_methods():
    assert _symbols(_chunks("Counter.razor", RAZOR)) == {"Counter.IncrementCount": 8}
    assert _symbols(_chunks("Index.cshtml", RAZOR)) == {"Index.CalcolaTitolo": 11}


def test_declared_classes_keep_their_plain_csharp_qualname():
    assert _symbols(_chunks("Handler.ashx")) == {
        "Handler": 4,
        "Handler.ProcessRequest": 6,
    }
    # The method starts at its `[WebMethod]` attribute (line 6): same rule as for `.cs` files.
    assert _symbols(_chunks("Api.asmx")) == {"Api": 4, "Api.Saluta": 6}


def test_sentinel_never_appears():
    for rel, language in (("Default.aspx", WEBFORMS), ("Counter.razor", RAZOR)):
        for chunk in _chunks(rel, language):
            assert chunk.metadata.symbol != PAGE_SENTINEL
            assert PAGE_SENTINEL not in chunk.text
            assert PAGE_SENTINEL not in (chunk.metadata.qualname or "")


def test_bom_does_not_move_the_lines():
    text = '﻿<%@ Page Language="C#" %>\n<script runat="server">\n    void ConBom() { }\n</script>\n'
    assert _symbols(_chunks("Bom.aspx", text=text)) == {"Bom.ConBom": 3}


# --- US4: what cannot be analysed is declared ----------------------------------------------------


def test_vb_page_is_indexed_as_text_with_an_event(caplog):
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        chunks = _chunks("Vecchia.aspx")
    assert chunks and not _syntactic(chunks)
    assert any("Sub Page_Load" in c.text for c in chunks)  # the whole text, code included
    events = _degraded(caplog)
    assert len(events) == 1
    assert events[0].path == "Vecchia.aspx"
    assert events[0].reason == "server_language"
    assert events[0].detail == "VB"


def test_malformed_csharp_is_indexed_as_text_with_an_event(caplog):
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        chunks = _chunks("Rotta.aspx")
    assert chunks and not _syntactic(chunks)
    events = _degraded(caplog)
    assert len(events) == 1
    assert events[0].path == "Rotta.aspx"
    assert events[0].reason == "parse_error"
    assert events[0].detail == "line 3"   # the broken line, not the <script> tag that encloses it


def test_valid_pages_emit_no_event(caplog):
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        _chunks("Default.aspx")
        _chunks("Site.master")
        _chunks("Index.cshtml", RAZOR)
        _chunks("Counter.razor", RAZOR)
    assert not _degraded(caplog)
