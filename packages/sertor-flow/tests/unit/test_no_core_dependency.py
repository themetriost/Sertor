"""US2 — indipendenza dal dominio RAG: né `sertor-flow` né `sertor-install-kit`
dipendono da `sertor-core` (NFR-2, FR-007/SC-004, T037).

Tre guardie:
1. **scan statico degli import**: nessun modulo di `sertor_flow`/`sertor_install_kit`
   importa `sertor_core` (AST walk dei sorgenti — robusto anche se il venv condiviso
   rende `sertor_core` importabile per il dogfood).
2. **dipendenze dichiarate**: i `pyproject.toml` dei due pacchetti non elencano
   `sertor-core` tra le `dependencies`.
3. **(F5/NFR-2, guardia positiva)** `sertor_flow` NON ridefinisce i primitivi del
   kit (no `claude_md.py`, `artifacts.py`, `report.py`, `executor.py`, merge,
   `command_runner.py`, `resources.py`): vengono dal kit, non duplicati.
"""
from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

import pytest

# Roots of the two source trees (this test lives in packages/sertor-flow/tests/unit/).
_FLOW_SRC = Path(__file__).resolve().parents[2] / "src" / "sertor_flow"
_KIT_SRC = (
    Path(__file__).resolve().parents[3] / "sertor-install-kit" / "src" / "sertor_install_kit"
)
_FLOW_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
_KIT_PYPROJECT = Path(__file__).resolve().parents[3] / "sertor-install-kit" / "pyproject.toml"


def _imported_modules(source: str) -> set[str]:
    """Top-level dotted names imported by a Python source (via AST)."""
    names: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.level == 0:
                names.add(node.module)
    return names


def _py_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


@pytest.mark.parametrize("root", [_FLOW_SRC, _KIT_SRC], ids=["sertor_flow", "sertor_install_kit"])
def test_no_static_import_of_sertor_core(root: Path):
    """No module under the package imports `sertor_core` (AST scan, SC-004)."""
    offenders: list[str] = []
    for path in _py_files(root):
        for mod in _imported_modules(path.read_text(encoding="utf-8")):
            if mod == "sertor_core" or mod.startswith("sertor_core."):
                offenders.append(f"{path}: imports {mod}")
    assert not offenders, "sertor_core must not be imported here:\n" + "\n".join(offenders)


@pytest.mark.parametrize(
    "pyproject", [_FLOW_PYPROJECT, _KIT_PYPROJECT], ids=["sertor-flow", "sertor-install-kit"]
)
def test_sertor_core_not_declared_as_dependency(pyproject: Path):
    """Neither package lists `sertor-core` among its runtime dependencies (FR-007)."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", [])
    normalized = [d.split(">=")[0].split("==")[0].split("[")[0].strip().lower() for d in deps]
    assert "sertor-core" not in normalized
    assert "sertor_core" not in normalized
    # Also reject a workspace source entry that would silently wire the core in.
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    assert "sertor-core" not in sources
    assert "sertor_core" not in sources


# Kit primitives that `sertor_flow` MUST consume (not duplicate) — F5 positive guard.
_KIT_OWNED_MODULES = (
    "claude_md.py",
    "artifacts.py",
    "report.py",
    "executor.py",
    "resources.py",
    "command_runner.py",
    "settings_merge.py",
    "env_merge.py",
    "mcp_merge.py",
    "gitignore_append.py",
)


@pytest.mark.parametrize("module", _KIT_OWNED_MODULES)
def test_flow_does_not_redefine_kit_primitives(module: str):
    """`sertor_flow` does not re-implement a kit primitive (F5/NFR-2): it imports it."""
    assert not (_FLOW_SRC / module).exists(), (
        f"sertor_flow/{module} must come from sertor_install_kit, not be duplicated"
    )


def test_sertor_core_not_required_at_import_time():
    """Importing the governance modules does not eagerly pull in `sertor_core`.

    We import the flow modules and assert none of them registered `sertor_core` as a
    dependency at module level (the AST scan above is the authority; this is a runtime
    cross-check that the import graph stays clean).
    """
    import sertor_flow.generate  # noqa: F401
    import sertor_flow.install_governance  # noqa: F401
    import sertor_flow.profile  # noqa: F401

    flow_and_kit = [
        name
        for name in sys.modules
        if name.startswith("sertor_flow") or name.startswith("sertor_install_kit")
    ]
    for name in flow_and_kit:
        module = sys.modules[name]
        deps = getattr(module, "__dict__", {})
        assert "sertor_core" not in {
            getattr(v, "__name__", None) for v in deps.values()
        }, f"{name} references sertor_core at module level"
