"""Size-based fallback chunking (REQ-009).

Used when the syntactic chunker does not cover the language, or for generic text. Splits the
content into windows of `chunk_size` characters with `overlap` overlap, respecting line boundaries
(never cuts mid-line). Never raises an error: guarantees coverage of any file.
"""
from __future__ import annotations


def size_chunks(text: str, chunk_size: int = 1600, overlap: int = 200) -> list[dict]:
    """Size-based windows on line boundaries. Chunk: {text, start_line, end_line} (1-based)."""
    if not text.strip():
        return []
    chunk_size = max(1, chunk_size)
    overlap = max(0, min(overlap, chunk_size - 1))

    lines = text.split("\n")
    chunks: list[dict] = []
    start = 0
    n = len(lines)
    while start < n:
        size = 0
        end = start
        while end < n and (size == 0 or size + len(lines[end]) + 1 <= chunk_size):
            size += len(lines[end]) + 1
            end += 1
        chunks.append(
            {"text": "\n".join(lines[start:end]), "start_line": start + 1, "end_line": end}
        )
        if end >= n:
            break
        # Overlap: step back some lines to cover ~overlap characters.
        back = 0
        ov = 0
        while end - back - 1 > start and ov < overlap:
            ov += len(lines[end - back - 1]) + 1
            back += 1
        start = end - back if back else end
    return chunks
