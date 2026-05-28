"""Loaders del corpus campione (raw/fastapi): codice ed esempi (.py) e doc (.md)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.config import settings


@dataclass
class Doc:
    id: str          # path relativo, identificatore stabile
    text: str
    metadata: dict


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def load_code() -> list[Doc]:
    """File Python del package (`fastapi/`) e degli esempi (`docs_src/`)."""
    base = settings.fastapi_dir
    docs: list[Doc] = []
    for sub, kind in (("fastapi", "code"), ("docs_src", "example")):
        for p in sorted((base / sub).rglob("*.py")):
            rel = p.relative_to(base).as_posix()
            docs.append(Doc(rel, _read(p),
                            {"path": rel, "source": "code", "kind": kind, "language": "python"}))
    return docs


def load_docs() -> list[Doc]:
    """Documentazione Markdown in inglese (`docs/en/`)."""
    base = settings.fastapi_dir / "docs" / "en"
    docs: list[Doc] = []
    for p in sorted(base.rglob("*.md")):
        rel = p.relative_to(settings.fastapi_dir).as_posix()
        docs.append(Doc(rel, _read(p), {"path": rel, "source": "doc", "kind": "markdown"}))
    return docs
