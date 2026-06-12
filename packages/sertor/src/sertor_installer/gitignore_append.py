"""Append dedup di righe nel `.gitignore` host (FR-019, REQ-240/241).

Garantisce che gli artefatti rigenerabili del runtime (`.sertor/.venv/`, `.sertor/.index*`,
`.sertor/.env`) siano ignorati. Assente → crea con header + righe; presente → appende solo le righe
mancanti (dedup), senza duplicati e senza toccare le righe utente.
"""
from __future__ import annotations

from pathlib import Path

from sertor_installer.artifacts import Outcome

# Righe da garantire (rigenerabili / segreti del runtime `.sertor/`).
RUNTIME_IGNORES = (".sertor/.venv/", ".sertor/.index*", ".sertor/.env")
_HEADER = "# Sertor RAG runtime (sertor install rag)"


def append_gitignore(
    gitignore_path: Path, lines: tuple[str, ...] = RUNTIME_IGNORES
) -> tuple[Outcome, str]:
    """Appende `lines` mancanti al `.gitignore`, dedup per riga esatta (strip)."""
    if not gitignore_path.exists():
        body = "\n".join((_HEADER, *lines)) + "\n"
        gitignore_path.parent.mkdir(parents=True, exist_ok=True)
        gitignore_path.write_text(body, encoding="utf-8")
        return Outcome.CREATED, f"+{len(lines)} voci"

    existing_text = gitignore_path.read_text(encoding="utf-8")
    present = {line.strip() for line in existing_text.splitlines()}
    missing = [ln for ln in lines if ln not in present]
    if not missing:
        return Outcome.SKIPPED, "già presente"

    new_text = existing_text
    if not new_text.endswith("\n"):
        new_text += "\n"
    new_text += "\n".join((_HEADER, *missing)) + "\n"
    gitignore_path.write_text(new_text, encoding="utf-8")
    return Outcome.MERGED, f"+{len(missing)} voci"
