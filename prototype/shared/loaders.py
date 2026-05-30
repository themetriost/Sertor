"""Loaders del corpus attivo (`settings.corpus`): "fastapi" (demo del prototipo) o
"sertor" (dogfooding: il prototipo stesso — codice dei motori + doc + wiki)."""
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


# Segmenti di path esclusi dal corpus "sertor" (ambienti, indici, artefatti, corpus FastAPI).
_EXCLUDE = {".venv-grag", "site-packages", "grag", "raw",
            "__pycache__", ".git", ".pytest_cache", "node_modules"}

# Code-root del prototipo indicizzati nel corpus "sertor" (dogfooding).
_SERTOR_CODE_ROOTS = ("01-baseline", "02-hybrid-reranking", "03-graphrag", "04-agentic-rag", "shared")


def _excluded(rel: str) -> bool:
    parts = rel.split("/")
    return any(p in _EXCLUDE or p.startswith(".index") or p.startswith(".venv") for p in parts)


def load_code() -> list[Doc]:
    """Codice .py del corpus attivo. fastapi: package + esempi; sertor: i motori del prototipo."""
    if settings.corpus == "fastapi":
        base = settings.fastapi_dir
        docs: list[Doc] = []
        for sub, kind in (("fastapi", "code"), ("docs_src", "example")):
            for p in sorted((base / sub).rglob("*.py")):
                rel = p.relative_to(base).as_posix()
                docs.append(Doc(rel, _read(p),
                                {"path": rel, "source": "code", "kind": kind, "language": "python"}))
        return docs
    # corpus "sertor": i .py dei motori del prototipo, path relativi a settings.root (=prototype/)
    root = settings.root
    docs = []
    for cr in _SERTOR_CODE_ROOTS:
        for p in sorted((root / cr).rglob("*.py")):
            rel = p.relative_to(root).as_posix()
            if _excluded(rel):
                continue
            docs.append(Doc(rel, _read(p),
                            {"path": rel, "source": "code", "kind": "code", "language": "python"}))
    return docs


def load_docs() -> list[Doc]:
    """Markdown del corpus attivo. fastapi: docs/en; sertor: README/DEMOS/ESEMPI + 04 + wiki."""
    if settings.corpus == "fastapi":
        base = settings.fastapi_dir / "docs" / "en"
        docs: list[Doc] = []
        for p in sorted(base.rglob("*.md")):
            rel = p.relative_to(settings.fastapi_dir).as_posix()
            docs.append(Doc(rel, _read(p), {"path": rel, "source": "doc", "kind": "markdown"}))
        return docs
    # corpus "sertor": documentazione di prodotto + doc agentici + wiki del prototipo (congelato)
    root = settings.root
    paths: list[Path] = [root / f for f in ("README.md", "DEMOS.md", "ESEMPI.md") if (root / f).exists()]
    paths += sorted((root / "04-agentic-rag").rglob("*.md"))
    paths += sorted((root / "wiki").rglob("*.md"))
    docs = []
    for p in paths:
        rel = p.relative_to(root).as_posix()
        if _excluded(rel):
            continue
        docs.append(Doc(rel, _read(p), {"path": rel, "source": "doc", "kind": "markdown"}))
    return docs
