"""Test US1 — install ≠ run (FR-023/SC-003).

Importare il package CLI o il modulo `__main__` non deve produrre alcuna operazione RAG: nessuna
chiamata a `build_indexer`/`build_facade`/`build_baseline_engine` a import-time. Ogni operazione
richiede l'invocazione esplicita di un sottocomando.
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
    # re-import pulito dei moduli CLI
    for mod in ("sertor_core.cli.__main__", "sertor_core.cli"):
        importlib.import_module(mod)
        importlib.reload(importlib.import_module(mod))

    assert calls == [], "l'import della CLI ha avviato un'operazione del core"
    assert real_import is builtins.__import__  # sentinella: nessun import hijack residuo
