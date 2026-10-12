"""Test 140 — projection of ASP.NET pages onto line-preserving C# views (page-projection)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.services.chunking.aspnet import (
    PAGE_SENTINEL,
    RAZOR,
    WEBFORMS,
    page_stem,
    project_page,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "aspnet"
PAGES = {
    "Default.aspx": WEBFORMS,
    "Admin/Default.aspx": WEBFORMS,
    "Menu.ascx": WEBFORMS,
    "Site.master": WEBFORMS,
    "Api.asmx": WEBFORMS,
    "Handler.ashx": WEBFORMS,
    "Vecchia.aspx": WEBFORMS,
    "Rotta.aspx": WEBFORMS,
    "Index.cshtml": RAZOR,
    "Counter.razor": RAZOR,
}


def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _line(view: str, number: int) -> str:
    return view.split("\n")[number - 1]


# --- T002: the line invariant ---------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_view_keeps_the_lines_of_the_file(name):
    text = _text(name)
    projection = project_page(text, PAGES[name])
    for view in (projection.chunk_view, projection.graph_view, projection.markup_view):
        assert view.count("\n") == text.count("\n")


@pytest.mark.parametrize(
    ("text", "language", "method_line"),
    [
        (
            '<script\n    runat="server"\n    type="text/c#">\n    void F() { }\n</script\n>\n',
            WEBFORMS,
            4,
        ),
        ("<h1>x</h1>\n@code\n{\n    void F() { }\n}\n", RAZOR, 4),
    ],
)
def test_multiline_openers_keep_the_lines(text, language, method_line):
    """The fixtures open every block on one line: this case proves the wrapper keeps `\\n`."""
    projection = project_page(text, language)
    for view in (projection.chunk_view, projection.graph_view, projection.markup_view):
        assert view.count("\n") == text.count("\n")
    assert "void F()" in _line(projection.chunk_view, method_line)


def test_unknown_language_is_a_programming_error():
    with pytest.raises(ValueError, match="python"):
        project_page("x", "python")


def test_page_stem_drops_every_extension():
    assert page_stem("Admin/Default.aspx") == "Default"
    assert page_stem("Views/_Layout.cshtml") == "_Layout"
    assert page_stem("Default.aspx.cs") == "Default"


# --- T003: WebForms constructs -------------------------------------------------------------------


def test_webforms_script_block_is_wrapped_in_the_sentinel_class():
    projection = project_page(_text("Default.aspx"), WEBFORMS)
    assert _line(projection.chunk_view, 4).strip() == f"class {PAGE_SENTINEL} {{"
    assert "protected void Page_Load" in _line(projection.chunk_view, 5)
    assert _line(projection.chunk_view, 10).strip() == "}"
    assert projection.has_code


def test_webforms_markup_is_blank_in_the_code_views_and_kept_in_the_markup_view():
    projection = project_page(_text("Default.aspx"), WEBFORMS)
    assert "OrdiniGrid" not in projection.chunk_view
    assert "OrdiniGrid" not in projection.graph_view
    assert "OrdiniGrid" in projection.markup_view


def test_webforms_code_is_blank_in_the_markup_view():
    projection = project_page(_text("Default.aspx"), WEBFORMS)
    assert "BindGrid" not in projection.markup_view
    assert "foreach" not in projection.markup_view
    assert "foreach (var riga in CaricaRighe())" in projection.chunk_view


def test_webforms_directive_stays_markup_and_server_comment_disappears():
    projection = project_page(_text("Default.aspx"), WEBFORMS)
    assert "<%@ Page" in _line(projection.markup_view, 1)
    assert _line(projection.chunk_view, 1).strip() == ""
    assert "Pagina di prova" not in projection.markup_view
    assert "Pagina di prova" not in projection.chunk_view


def test_webforms_expressions_go_to_the_graph_view_only():
    projection = project_page(_text("Default.aspx"), WEBFORMS)
    assert "FormatTitolo" not in projection.chunk_view
    assert "FormatTitolo() ;" in _line(projection.graph_view, 13)
    assert "<%= FormatTitolo() %>" in _line(projection.markup_view, 13)
    assert 'Eval("Nome") ;' in _line(projection.graph_view, 15)


def test_webforms_expression_builder_is_markup():
    text = (
        '<%@ Page Language="C#" %>\n'
        '<asp:Literal Text="<%$ Resources:Titolo %>" runat="server" />\n'
    )
    projection = project_page(text, WEBFORMS)
    assert "Resources" not in projection.chunk_view
    assert "Resources" not in projection.graph_view
    assert "<%$ Resources:Titolo %>" in projection.markup_view
    assert not projection.has_code


def test_webforms_markup_only_page_has_no_code():
    projection = project_page(_text("Menu.ascx"), WEBFORMS)
    assert not projection.has_code
    assert projection.chunk_view.strip() == ""
    assert "menu-principale" in projection.markup_view


@pytest.mark.parametrize("name", ["Handler.ashx", "Api.asmx"])
def test_handler_and_web_service_are_code_after_the_directive(name):
    text = _text(name)
    projection = project_page(text, WEBFORMS)
    assert projection.has_code
    assert _line(projection.chunk_view, 1).strip() == ""
    assert "public class" in projection.chunk_view
    assert PAGE_SENTINEL not in projection.chunk_view
    assert projection.markup_view.strip().startswith("<%@")


def test_server_language_comes_from_the_directive():
    assert project_page(_text("Default.aspx"), WEBFORMS).server_language == "C#"
    vb = project_page(_text("Vecchia.aspx"), WEBFORMS)
    assert vb.server_language == "VB"
    assert not vb.is_csharp


def test_server_language_comes_from_the_script_tag_too():
    text = '<script runat="server" language="vb">\n  Sub X()\n  End Sub\n</script>\n'
    assert project_page(text, WEBFORMS).server_language == "vb"
    text_cs = '<script language="C#" runat="server">\n  void X() { }\n</script>\n'
    assert project_page(text_cs, WEBFORMS).is_csharp


def test_unterminated_constructs_do_not_raise():
    for text in ("<% if (x) {", '<script runat="server">\nvoid F() { }', "<%-- mai chiuso"):
        projection = project_page(text, WEBFORMS)
        assert projection.chunk_view.count("\n") == text.count("\n")


# --- T004: Razor constructs ----------------------------------------------------------------------


def test_razor_code_block_is_wrapped():
    projection = project_page(_text("Counter.razor"), RAZOR)
    assert _line(projection.chunk_view, 5).strip() == f"class {PAGE_SENTINEL} {{"
    assert "private void IncrementCount()" in _line(projection.chunk_view, 8)
    assert _line(projection.chunk_view, 13).strip() == "}"
    assert projection.has_code


def test_razor_inline_expressions_and_attributes_stay_markup():
    projection = project_page(_text("Counter.razor"), RAZOR)
    assert "@onclick" in projection.markup_view
    assert "@count" in projection.markup_view
    assert "onclick" not in projection.chunk_view


def test_razor_statement_block_blanks_its_markup_lines_in_the_code_views():
    projection = project_page(_text("Index.cshtml"), RAZOR)
    assert "CalcolaTitolo();" in _line(projection.chunk_view, 3)
    assert _line(projection.chunk_view, 5).strip() == ""
    assert "<p>Righe caricate</p>" in _line(projection.markup_view, 5)
    assert "ViewData" not in _line(projection.markup_view, 3)


def test_razor_functions_block_ignores_braces_in_strings_and_comments():
    projection = project_page(_text("Index.cshtml"), RAZOR)
    assert _line(projection.chunk_view, 10).strip() == f"class {PAGE_SENTINEL} {{"
    assert "string CalcolaTitolo()" in _line(projection.chunk_view, 11)
    assert _line(projection.chunk_view, 16).strip() == "}"


def test_razor_email_escaped_at_and_comments():
    projection = project_page(_text("Index.cshtml"), RAZOR)
    assert "info@esempio.it" in projection.markup_view
    assert "@@" in projection.markup_view
    assert "commento razor" not in projection.markup_view
    assert "commento razor" not in projection.chunk_view


def test_razor_verbatim_string_with_brace_does_not_close_the_block():
    text = '@code {\n    string s = @"a } ""b"" {";\n    void F() { }\n}\n<p>dopo</p>\n'
    projection = project_page(text, RAZOR)
    assert "void F()" in _line(projection.chunk_view, 3)
    assert _line(projection.chunk_view, 4).strip() == "}"
    assert "dopo" in projection.markup_view
    assert "dopo" not in projection.chunk_view


def test_razor_unbalanced_block_runs_to_the_end_without_raising():
    text = "@{\n    var x = 1;\n<p>fine</p>\n"
    projection = project_page(text, RAZOR)
    assert projection.chunk_view.count("\n") == text.count("\n")
    assert "var x = 1;" in projection.chunk_view
