"""Test US1 — install != run (FR-023/SC-003).

Importing the CLI package or the `__main__` module must not trigger any RAG operation: no
call to `build_indexer`/`build_facade`/`build_baseline_engine` at import-time. Every operation
requires explicit invocation of a subcommand.
"""
from __future__ import annotations

import builtins
import importlib


def test_import_cli_package_has_no_side_effects(monkeypatch):
    calls: list[str] = []
    import sertor_core.composition as comp

    for name in ("build_indexer", "build_facade", "build_baseline_engine"):
        monkeypatch.setattr(comp, name, lambda *a, **k: calls.append("called"))

    real_import = builtins.__import__
    # clean re-import of CLI modules
    for mod in ("sertor_core.cli.__main__", "sertor_core.cli"):
        importlib.import_module(mod)
        importlib.reload(importlib.import_module(mod))

    assert calls == [], "l'import della CLI ha avviato un'operazione del core"
    assert real_import is builtins.__import__  # sentinel: no residual import hijack
