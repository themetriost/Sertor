"""Test 140 — ingestion of ASP.NET pages (FR-001..FR-003)."""
from __future__ import annotations

from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType
from sertor_core.services.chunking.aspnet import RAZOR, WEBFORMS
from sertor_core.services.ingestion import discover

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "aspnet"


def test_the_seven_extensions_are_ingested_as_code_with_the_page_language():
    docs = {d.id: d for d in discover(FIXTURES, Settings.load(env_file=None))}
    expected = {
        "Default.aspx": WEBFORMS,
        "Menu.ascx": WEBFORMS,
        "Site.master": WEBFORMS,
        "Api.asmx": WEBFORMS,
        "Handler.ashx": WEBFORMS,
        "Index.cshtml": RAZOR,
        "Counter.razor": RAZOR,
    }
    for doc_id, language in expected.items():
        assert docs[doc_id].doc_type is DocType.CODE
        assert docs[doc_id].language == language


def test_code_behind_stays_csharp():
    docs = {d.id: d for d in discover(FIXTURES, Settings.load(env_file=None))}
    assert docs["Default.aspx.cs"].language == "c_sharp"


def test_nested_page_keeps_its_relative_path_as_id():
    ids = {d.id for d in discover(FIXTURES, Settings.load(env_file=None))}
    assert "Admin/Default.aspx" in ids
