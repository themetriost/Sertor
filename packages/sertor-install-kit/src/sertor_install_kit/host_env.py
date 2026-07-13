"""Host-environment probes for the installer (E2-FEAT-010, stdlib-only, offline, mockable).

Deterministic, **read-only** inspections of the host repository used to surface honest, *advisory*
install-time notes (Principio XII) WITHOUT changing what the installer does. A verdict here never
alters behaviour — it only decides whether an advisory note is shown — so a false positive/negative
is cheap. No network, no `sertor_core` import, bounded traversal (Principio X: host-agnostic).
"""
from __future__ import annotations

from pathlib import Path

# Directories that are NOT host sources (installer-owned, VCS, virtualenvs, deps) — pruned from the
# language probe so a host's OWN Python code is what decides the verdict, not Sertor's runtime.
_EXCLUDED_DIRS = frozenset(
    {".sertor", ".git", ".hg", ".svn", ".venv", "venv", "node_modules", ".claude", ".github",
     "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
)

# Root markers that make a host unambiguously a Python project regardless of file layout.
_PY_PROJECT_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg")


def is_python_host(root: Path, *, max_depth: int = 3) -> bool:
    """True if `root` looks like a Python project.

    A host is Python if it carries a root project marker (`pyproject.toml`/`setup.py`/`setup.cfg`)
    or contains at least one `.py` file within `max_depth` levels (installer/VCS/venv dirs pruned).
    Bounded on purpose (no full-tree walk on a huge monorepo). Advisory only.
    """
    for marker in _PY_PROJECT_MARKERS:
        if (root / marker).is_file():
            return True
    return _has_py_file(root, max_depth)


def _has_py_file(root: Path, max_depth: int) -> bool:
    """Bounded search for any `.py` file under `root` (depth-limited, excluded dirs pruned)."""
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            entries = list(directory.iterdir())
        except OSError:  # pragma: no cover - unreadable dir → treat as no match, never crash
            continue
        for entry in entries:
            if entry.is_file() and entry.suffix == ".py":
                return True
        if depth < max_depth:
            for entry in entries:
                if entry.is_dir() and entry.name not in _EXCLUDED_DIRS:
                    stack.append((entry, depth + 1))
    return False
