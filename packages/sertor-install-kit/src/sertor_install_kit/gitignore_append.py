"""Dedup-append of lines to the host `.gitignore` (FR-019, REQ-240/241).

Ensures that regenerable runtime artifacts (`.sertor/.venv/`, `.sertor/.index*`,
`.sertor/.env`) are ignored. Absent → create with header + lines; present → append only
missing lines (dedup), without duplicates and without touching user lines.
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.artifacts import Outcome

# Lines to guarantee (regenerable / secrets of the `.sertor/` runtime).
RUNTIME_IGNORES = (".sertor/.venv/", ".sertor/.index*", ".sertor/.env")
_HEADER = "# Sertor RAG runtime (sertor install rag)"


def append_gitignore(
    gitignore_path: Path, lines: tuple[str, ...] = RUNTIME_IGNORES
) -> tuple[Outcome, str]:
    """Appends missing `lines` to `.gitignore`, dedup by exact line (stripped)."""
    if not gitignore_path.exists():
        body = "\n".join((_HEADER, *lines)) + "\n"
        gitignore_path.parent.mkdir(parents=True, exist_ok=True)
        gitignore_path.write_text(body, encoding="utf-8")
        return Outcome.CREATED, f"+{len(lines)} entries"

    existing_text = gitignore_path.read_text(encoding="utf-8")
    present = {line.strip() for line in existing_text.splitlines()}
    missing = [ln for ln in lines if ln not in present]
    if not missing:
        return Outcome.SKIPPED, "already present"

    new_text = existing_text
    if not new_text.endswith("\n"):
        new_text += "\n"
    new_text += "\n".join((_HEADER, *missing)) + "\n"
    gitignore_path.write_text(new_text, encoding="utf-8")
    return Outcome.MERGED, f"+{len(missing)} entries"


def remove_gitignore_lines(
    gitignore_path: Path, lines: tuple[str, ...] = RUNTIME_IGNORES
) -> tuple[Outcome, str]:
    """Removes ONLY the Sertor lines (`lines` + the `_HEADER`) — inverse of `append_gitignore`.

    User lines are preserved. Matching is by stripped content (robust to reformatting: extra
    surrounding whitespace still matches, FR-023). The header is removed only when it is on its own
    line. Absent file / no Sertor line present → `(SKIPPED, "no Sertor lines")` (idempotency). If,
    after removal, the file is empty/whitespace-only, it is deleted (`REMOVED`).
    """
    if not gitignore_path.exists():
        return Outcome.SKIPPED, "no Sertor lines"

    existing_text = gitignore_path.read_text(encoding="utf-8")
    targets = {ln.strip() for ln in (_HEADER, *lines)}
    kept: list[str] = []
    removed = 0
    for raw_line in existing_text.splitlines():
        if raw_line.strip() in targets:
            removed += 1
            continue
        kept.append(raw_line)

    if removed == 0:
        return Outcome.SKIPPED, "no Sertor lines"

    remaining = "\n".join(kept)
    if remaining.strip() == "":
        gitignore_path.unlink()
        return Outcome.REMOVED, f"-{removed} lines"
    # Preserve a trailing newline (the file had one if it was non-empty and well-formed).
    gitignore_path.write_text(remaining + "\n", encoding="utf-8")
    return Outcome.REMOVED, f"-{removed} lines"
