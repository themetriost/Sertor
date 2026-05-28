"""Unit test del chunker code-aware (tree-sitter). Free, deterministico, nessun backend."""
from __future__ import annotations

from shared.chunking_code import DEFAULT_MAX_CHARS, code_chunks

SAMPLE = '''\
import os
from typing import Optional

CONST = 42


def top_level(x):
    """Una funzione di modulo."""
    return x + 1


class Service:
    """Un servizio di esempio."""

    def __init__(self, name):
        self.name = name

    def run(self, payload):
        return f"{self.name}:{payload}"
'''


def _chunks():
    ch = code_chunks(SAMPLE, "python")
    assert ch is not None
    return ch


def test_separa_per_simboli():
    kinds = {c["symbol_kind"] for c in _chunks()}
    assert {"module", "function", "class", "method"} <= kinds


def test_qualname_dei_metodi():
    quals = {c["qualname"] for c in _chunks() if c["symbol_kind"] == "method"}
    assert "Service.__init__" in quals
    assert "Service.run" in quals


def test_metodo_porta_contesto_classe():
    run = next(c for c in _chunks() if c["qualname"] == "Service.run")
    assert "class Service" in run["text"]      # contesto della classe prepeso
    assert "return f" in run["text"]           # corpo del metodo presente


def test_range_righe_validi():
    for c in _chunks():
        assert 1 <= c["start_line"] <= c["end_line"]


def test_nessun_chunk_sopra_il_limite():
    # tolleranza per la riga di contesto prepesa ai metodi
    assert all(len(c["text"]) <= DEFAULT_MAX_CHARS + 200 for c in _chunks())


def test_lingua_non_supportata_ritorna_none():
    assert code_chunks("fn main() {}", "rust") is None
