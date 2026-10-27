"""ASP.NET pages (WebForms + Razor): projection onto C# views that keep the file's lines (140).

A page mixes markup with server-side C#. Instead of cutting it into fragments and remapping their
offsets, the page is **projected**: every character that is not server-side code becomes a space,
newlines stay where they are. The resulting C# view has exactly the lines of the original file, so
the existing C# chunker and graph extraction report the real line of every symbol by construction.

Three views come out of one scan (see `specs/140-pagine-aspnet/contracts/page-projection.md`):
- `chunk_view`: the code blocks — source of the syntactic chunks;
- `graph_view`: the code blocks plus the short expressions (`<%= x %>`) as `x;` statements —
  source of the `calls` edges (expressions produce edges, not chunks);
- `markup_view`: the page with the code blocks blanked — source of the size-based markup chunks.

Methods written outside any class (`<script runat="server">`, `@code`, `@functions`) are wrapped in
a sentinel class so the grammar sees them as methods; the sentinel never becomes a symbol and is
renamed to the file stem (`Default.aspx` -> `Default.Page_Load`). Pages that cannot be analysed (a
server language other than C#, C# with syntax errors) are indexed as text and reported with the
event `aspnet_page_degraded` (Principio XII).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import Document
from sertor_core.observability.logging import log_event
from sertor_core.services.chunking.code import code_chunks, syntax_error_line
from sertor_core.services.chunking.fallback import size_chunks

WEBFORMS = "webforms"
RAZOR = "razor"
PAGE_LANGUAGES = frozenset({WEBFORMS, RAZOR})

#: Name of the synthetic class that wraps methods written outside a class. Never a symbol.
PAGE_SENTINEL = "__page__"
_CSHARP = "c_sharp"
_CSHARP_NAMES = frozenset({"c#", "cs", "csharp"})

# --- region kinds: how each slice of the page renders in (chunk_view, graph_view, markup_view) ---
_MARKUP = "markup"            # blank, blank, keep
_HIDDEN = "hidden"            # blank, blank, blank (server comments, code delimiters)
_CODE = "code"                # keep,  keep,  blank
_EXPR = "expr"                # blank, `x;`,  keep  (short expression body)
_OPEN_TAG = "open_tag"        # `class __page__ {`, idem, blank (<script runat="server">)
_OPEN_KEYWORD = "open_kw"     # `class __page__`, idem, blank (@code / @functions keyword)
_CLOSE_TAG = "close_tag"      # `}`, `}`, blank (</script>)

_KEEP = object()
_BLANK = object()


@dataclass(frozen=True)
class PageProjection:
    """The three line-preserving views of a page, plus what the scan learned about it."""

    chunk_view: str
    graph_view: str
    markup_view: str
    server_language: str = "C#"
    has_code: bool = False

    @property
    def is_csharp(self) -> bool:
        return self.server_language.strip().lower() in _CSHARP_NAMES


def project_page(text: str, language: str) -> PageProjection:
    """Projects a page onto its three views. Pure, deterministic, never raises on the data."""
    if language == WEBFORMS:
        regions, server_language = _scan_webforms(text)
    elif language == RAZOR:
        regions, server_language = _scan_razor(text), "C#"
    else:
        raise ValueError(f"not an ASP.NET page language: {language!r}")
    chunk_view, graph_view, markup_view = _render(text, regions)
    has_code = any(kind in (_CODE, _OPEN_TAG, _OPEN_KEYWORD) for kind, _, _ in regions)
    return PageProjection(chunk_view, graph_view, markup_view, server_language, has_code)


def page_stem(path: str) -> str:
    """The file name without any extension: `Admin/Default.aspx` -> `Default`."""
    return PurePosixPath(path).name.split(".")[0]


def degradation(projection: PageProjection) -> tuple[str, str] | None:
    """`(reason, detail)` when the page can only be indexed as text, `None` otherwise.

    Shared by the chunker (which reports it) and the graph extraction (which skips the page without
    reporting twice), so the two always agree.
    """
    if not projection.is_csharp:
        return "server_language", projection.server_language
    if projection.has_code:
        line = syntax_error_line(projection.chunk_view, _CSHARP)
        if line is not None:
            return "parse_error", f"line {line}"
    return None


def page_raws(doc: Document, settings: Settings) -> list[tuple[dict, bool]]:
    """Raw chunks of a page as `(raw, is_syntactic)`: syntactic code chunks, then the markup chunks.

    A degraded page yields size-based chunks of the whole original text and emits
    `aspnet_page_degraded` (WARNING) naming the file and the reason.
    """
    projection = project_page(doc.text, doc.language)
    verdict = degradation(projection)
    code = []
    if verdict is None and projection.has_code:
        code = code_chunks(projection.chunk_view, _CSHARP, settings.chunk_size)
        if code is None:
            verdict = ("parse_error", "C# grammar unavailable")
    if verdict is not None:
        reason, detail = verdict
        log_event(
            logging.WARNING, "aspnet_page_degraded", path=doc.id, reason=reason, detail=detail
        )
        whole = size_chunks(doc.text, settings.chunk_size, settings.chunk_overlap)
        return [(raw, False) for raw in whole]

    stem = page_stem(doc.path)
    syntactic = [_without_sentinel(raw, stem) for raw in code if not _is_sentinel(raw)]
    markup = size_chunks(projection.markup_view, settings.chunk_size, settings.chunk_overlap)
    return [(raw, True) for raw in syntactic if raw["text"].strip()] + [
        (raw, False) for raw in markup
    ]


# --- chunk post-processing -----------------------------------------------------------------------


def _is_sentinel(raw: dict) -> bool:
    return raw.get("symbol") == PAGE_SENTINEL and raw.get("symbol_kind") == "class"


def _without_sentinel(raw: dict, stem: str) -> dict:
    """Renames the sentinel prefix to the file stem and removes its text from the chunk."""
    out = dict(raw)
    qualname = raw.get("qualname")
    prefix = f"{PAGE_SENTINEL}."
    if qualname and qualname.startswith(prefix):
        out["qualname"] = f"{stem}.{qualname[len(prefix):]}"
    text = raw["text"].replace(f"class {PAGE_SENTINEL} {{", "")
    text = text.replace(f"class {PAGE_SENTINEL}", "")
    out["text"] = "\n".join(line.rstrip() for line in text.split("\n"))
    return out


# --- rendering -----------------------------------------------------------------------------------


def _blank(segment: str) -> str:
    return re.sub(r"[^\n]", " ", segment)


def _newlines(segment: str) -> str:
    return "\n" * segment.count("\n")


def _piece(kind: str, segment: str, view: int) -> str:
    """The text a region contributes to view 0 (chunk), 1 (graph) or 2 (markup)."""
    if kind == _OPEN_TAG and view < 2:
        return f"class {PAGE_SENTINEL} {{" + _newlines(segment)
    if kind == _OPEN_KEYWORD and view < 2:
        return f"class {PAGE_SENTINEL}" + _newlines(segment)
    if kind == _CLOSE_TAG and view < 2:
        return "}" + _newlines(segment)
    if kind == _EXPR and view == 1:
        return segment + ";"
    keep = {
        _MARKUP: (False, False, True),
        _HIDDEN: (False, False, False),
        _CODE: (True, True, False),
        _EXPR: (False, True, True),
        _OPEN_TAG: (True, True, False),
        _OPEN_KEYWORD: (True, True, False),
        _CLOSE_TAG: (True, True, False),
    }[kind][view]
    return segment if keep else _blank(segment)


def _render(text: str, regions: list[tuple[str, int, int]]) -> tuple[str, str, str]:
    views: tuple[list[str], list[str], list[str]] = ([], [], [])
    for kind, start, end in _fill_gaps(regions, len(text)):
        segment = text[start:end]
        for view, out in enumerate(views):
            out.append(_piece(kind, segment, view))
    return tuple("".join(out) for out in views)  # type: ignore[return-value]


def _fill_gaps(regions: list[tuple[str, int, int]], length: int) -> list[tuple[str, int, int]]:
    """Covers the whole text: the slices no scanner claimed are markup."""
    out: list[tuple[str, int, int]] = []
    pos = 0
    for kind, start, end in sorted(regions, key=lambda r: r[1]):
        if start > pos:
            out.append((_MARKUP, pos, start))
        if end > start:
            out.append((kind, start, end))
        pos = max(pos, end)
    if pos < length:
        out.append((_MARKUP, pos, length))
    return out


# --- WebForms scanner ----------------------------------------------------------------------------

_SCRIPT_OPEN = re.compile(r"<script\b[^>]*\brunat\s*=\s*[\"']?server\b[^>]*>", re.IGNORECASE)
_SCRIPT_CLOSE = re.compile(r"</script\s*>", re.IGNORECASE)
_SERVER_TOKEN = re.compile(r"<%")
_LANGUAGE_ATTR = re.compile(r"\blanguage\s*=\s*[\"']?([\w#+.]+)", re.IGNORECASE)
_DIRECTIVE_NAME = re.compile(r"<%@\s*(\w+)", re.IGNORECASE)
_LANGUAGE_DIRECTIVES = frozenset({"page", "control", "master", "webhandler", "webservice"})
_CODE_FILE_DIRECTIVES = frozenset({"webhandler", "webservice"})
_EXPR_OPENERS = ("<%#:", "<%=", "<%:", "<%#")


def _scan_webforms(text: str) -> tuple[list[tuple[str, int, int]], str]:
    regions: list[tuple[str, int, int]] = []
    server_language = "C#"
    pos = 0
    while pos < len(text):
        script = _SCRIPT_OPEN.search(text, pos)
        token = _SERVER_TOKEN.search(text, pos)
        if script is None and token is None:
            break
        if script is not None and (token is None or script.start() < token.start()):
            pos, script_language = _scan_script(text, script, regions)
            if script_language and not _is_csharp_name(script_language):
                server_language = script_language
            continue
        pos, directive = _scan_server_token(text, token.start(), regions)
        if directive is None:
            continue
        name, language = directive
        if language and name in _LANGUAGE_DIRECTIVES:
            server_language = language
        if name in _CODE_FILE_DIRECTIVES:
            regions.append((_CODE, pos, len(text)))  # handler / web service: the rest is C#
            break
    return regions, server_language


def _scan_script(text: str, opening: re.Match, regions: list) -> tuple[int, str | None]:
    """`<script runat="server">…</script>` → wrapped code. Returns (next pos, language attr)."""
    language = _LANGUAGE_ATTR.search(opening.group(0))
    regions.append((_OPEN_TAG, opening.start(), opening.end()))
    closing = _SCRIPT_CLOSE.search(text, opening.end())
    if closing is None:
        regions.append((_CODE, opening.end(), len(text)))
        return len(text), language.group(1) if language else None
    regions.append((_CODE, opening.end(), closing.start()))
    regions.append((_CLOSE_TAG, closing.start(), closing.end()))
    return closing.end(), language.group(1) if language else None


def _scan_server_token(
    text: str, start: int, regions: list
) -> tuple[int, tuple[str, str | None] | None]:
    """One `<% … %>` token. Returns (next position, (directive name, language) or None)."""
    if text.startswith("<%--", start):
        end = text.find("--%>", start + 4)
        end = len(text) if end < 0 else end + 4
        regions.append((_HIDDEN, start, end))
        return end, None
    close = text.find("%>", start + 2)
    if close < 0:
        return len(text), None  # unterminated: the rest stays markup
    end = close + 2
    if text.startswith("<%@", start):
        regions.append((_MARKUP, start, end))
        directive = text[start:end]
        name = _DIRECTIVE_NAME.match(directive)
        language = _LANGUAGE_ATTR.search(directive)
        directive_name = name.group(1).lower() if name else ""
        return end, (directive_name, language.group(1) if language else None)
    if text.startswith("<%$", start):
        regions.append((_MARKUP, start, end))  # expression builder: configuration, not C#
        return end, None
    opener = next((o for o in _EXPR_OPENERS if text.startswith(o, start)), None)
    if opener is not None:
        regions.append((_MARKUP, start, start + len(opener)))
        regions.append((_EXPR, start + len(opener), close))
        regions.append((_MARKUP, close, end))
        return end, None
    regions.append((_HIDDEN, start, start + 2))
    regions.append((_CODE, start + 2, close))
    regions.append((_HIDDEN, close, end))
    return end, None


def _is_csharp_name(name: str) -> bool:
    return name.strip().lower() in _CSHARP_NAMES


# --- Razor scanner -------------------------------------------------------------------------------

_RAZOR_KEYWORD_BLOCK = re.compile(r"@(code|functions)\b(\s*)\{")
_RAZOR_MARKUP_LINE = re.compile(r"[ \t]*(<[A-Za-z/!]|@:)")


def _scan_razor(text: str) -> list[tuple[str, int, int]]:
    regions: list[tuple[str, int, int]] = []
    pos = text.find("@")
    while 0 <= pos < len(text):
        nxt = _scan_razor_transition(text, pos, regions)
        pos = text.find("@", nxt)
    return regions


def _scan_razor_transition(text: str, at: int, regions: list) -> int:
    """Handles one `@`; returns the position from which to look for the next one."""
    if text.startswith("@@", at):
        return at + 2  # escaped `@`: markup
    if at > 0 and (text[at - 1].isalnum() or text[at - 1] in "._-"):
        return at + 1  # e-mail address or similar: markup
    if text.startswith("@*", at):
        end = text.find("*@", at + 2)
        end = len(text) if end < 0 else end + 2
        regions.append((_HIDDEN, at, end))
        return end
    if text.startswith("@{", at):
        regions.append((_HIDDEN, at, at + 1))
        return _scan_razor_block(text, at + 1, regions)
    keyword = _RAZOR_KEYWORD_BLOCK.match(text, at)
    if keyword is not None:
        brace = keyword.end() - 1
        regions.append((_OPEN_KEYWORD, at, at + 1 + len(keyword.group(1))))
        regions.append((_CODE, at + 1 + len(keyword.group(1)), brace))
        return _scan_razor_block(text, brace, regions)
    return at + 1  # inline expression or directive (`@Model.X`, `@page`): markup


def _scan_razor_block(text: str, brace: int, regions: list) -> int:
    """Code from `{` to its matching `}`; markup lines inside the block are kept out of the code."""
    end, markup_lines = _match_block(text, brace)
    pos = brace
    for line_start, line_end in markup_lines:
        regions.append((_CODE, pos, line_start))
        regions.append((_MARKUP, line_start, line_end))
        pos = line_end
    regions.append((_CODE, pos, end))
    return end


def _match_block(text: str, brace: int) -> tuple[int, list[tuple[int, int]]]:
    """End (exclusive) of the C# block opened at `brace`, and the spans of its markup lines.

    Braces inside strings (`"…"`, `@"…"`, `'…'`), comments (`//`, `/* */`) and markup lines do not
    count. An unbalanced block runs to the end of the text.
    """
    depth = 0
    markup_lines: list[tuple[int, int]] = []
    i = brace
    n = len(text)
    while i < n:
        if i > brace and text[i - 1] == "\n" and _RAZOR_MARKUP_LINE.match(text, i):
            line_end = text.find("\n", i)
            line_end = n if line_end < 0 else line_end
            markup_lines.append((i, line_end))
            i = line_end
            continue
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1, markup_lines
        elif text.startswith("//", i):
            i = _line_end(text, i)
            continue
        elif text.startswith("/*", i):
            close = text.find("*/", i + 2)
            i = n if close < 0 else close + 2
            continue
        elif text.startswith('@"', i):
            i = _skip_verbatim_string(text, i + 2)
            continue
        elif ch in "\"'":
            i = _skip_string(text, i + 1, ch)
            continue
        i += 1
    return n, markup_lines


def _line_end(text: str, i: int) -> int:
    end = text.find("\n", i)
    return len(text) if end < 0 else end


def _skip_string(text: str, i: int, quote: str) -> int:
    """Past the closing `quote` of a regular string/char literal (escapes honoured, one line)."""
    while i < len(text) and text[i] != "\n":
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote:
            return i + 1
        i += 1
    return i


def _skip_verbatim_string(text: str, i: int) -> int:
    """Past the closing quote of a verbatim string (`""` is an escaped quote)."""
    while i < len(text):
        if text[i] == '"':
            if text.startswith('""', i):
                i += 2
                continue
            return i + 1
        i += 1
    return i
