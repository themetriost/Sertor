"""Test di guardia anti-drift assets ⇄ `.claude/` (T031, D2).

Fonte canonica = gli assets nel pacchetto `sertor_installer`; `.claude/` del repo è il **derivato**
mantenuto allineato da `python -m sertor_installer.sync`. Questo test confronta ogni file di
`assets/claude/**` con il corrispondente in `.claude/`: se divergono (senza una giustificazione
nell'allowlist), il drift diventa un errore CI.

**Allowlist (differenze ammesse, D3).** Il `.claude/` di sviluppo può reintrodurre `uv run` davanti
ai console-script (l'ospite generico non assume `uv`; lo sviluppo del monorepo sì). La
normalizzazione qui sotto neutralizza quella differenza prima del confronto. Allo stato attuale il
sync propaga gli assets *as-is* (senza `uv run`), quindi le copie sono identiche; l'allowlist resta
documentata per il caso in cui lo sviluppo reintroduca `uv run`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_installer.resources import iter_asset_dir

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLAUDE = _REPO_ROOT / ".claude"


def _normalize(text: str) -> str:
    """Neutralizza la differenza ammessa (allowlist): `uv run sertor-wiki-tools` ↔ script."""
    return text.replace("uv run sertor-wiki-tools", "sertor-wiki-tools")


@pytest.mark.parametrize("rel_path,content", list(iter_asset_dir("claude")))
def test_asset_matches_claude(rel_path: str, content: str):
    dest = _CLAUDE / rel_path
    assert dest.is_file(), (
        f".claude/{rel_path} manca: esegui `python -m sertor_installer.sync` per propagarlo"
    )
    actual = dest.read_text(encoding="utf-8")
    assert _normalize(actual) == _normalize(content), (
        f".claude/{rel_path} è andato in drift rispetto agli assets bundlati. "
        f"Fonte canonica = assets; esegui `python -m sertor_installer.sync`."
    )
