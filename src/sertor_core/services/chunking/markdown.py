"""Chunking della documentazione Markdown ai confini di heading (REQ-008).

Ogni sezione (da un heading fino al successivo di livello pari o superiore) diventa un chunk, con
la **gerarchia di sezione** (`heading_path`) come metadato. Il testo prima del primo heading
diventa un chunk di preambolo con `heading_path` vuoto.
"""
from __future__ import annotations

import re

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def markdown_chunks(text: str) -> list[dict]:
    """Spezza `text` Markdown per heading. Chunk: {text, heading_path, start_line, end_line}."""
    lines = text.split("\n")
    headings: list[tuple[int, int, str]] = []  # (line_index, level, title)
    for i, ln in enumerate(lines):
        m = _HEADING.match(ln)
        if m:
            headings.append((i, len(m.group(1)), m.group(2)))

    chunks: list[dict] = []

    # Preambolo prima del primo heading.
    first = headings[0][0] if headings else len(lines)
    preamble = "\n".join(lines[:first]).strip()
    if preamble:
        chunks.append({
            "text": "\n".join(lines[:first]),
            "heading_path": (),
            "start_line": 1,
            "end_line": first,
        })

    stack: list[tuple[int, str]] = []  # (level, title) degli antenati correnti
    for idx, (start, level, title) in enumerate(headings):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        heading_path = tuple(t for _, t in stack)
        end = (headings[idx + 1][0] - 1) if idx + 1 < len(headings) else len(lines) - 1
        chunks.append(
            {
                "text": "\n".join(lines[start : end + 1]),
                "heading_path": heading_path,
                "start_line": start + 1,
                "end_line": end + 1,
            }
        )
    return chunks
