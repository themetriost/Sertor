"""Test US4 — registri idempotenti; SC-002 (re-run identico, niente duplicati/timestamp)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.registry import append_log, upsert_index
from sertor_core.wiki_tools.structure import init_structure

_CONFIG = """\
profile = "code+doc"
language = "it"
root = "wiki"
index_file = "index.md"
log_file = "log.md"
log_format = "## [{date}] {op} | {title}"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
"""


def _profile(tmp_path: Path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    p = load_profile(cfg)
    init_structure(p)
    return p


def test_append_log_writes_formatted_entry(tmp_path):
    p = _profile(tmp_path)
    wrote = append_log(p, "record", "Prima voce", on_date=date(2026, 6, 5))
    assert wrote.written is True
    content = p.log_path.read_text("utf-8")
    assert "## [2026-06-05] record | Prima voce" in content


def test_append_log_is_idempotent(tmp_path):
    # SC-002: stessa voce due volte → nessun duplicato, file invariato la seconda volta.
    p = _profile(tmp_path)
    append_log(p, "record", "X", on_date=date(2026, 6, 5))
    first = p.log_path.read_text("utf-8")
    mtime_first = p.log_path.stat().st_mtime_ns

    wrote2 = append_log(p, "record", "X", on_date=date(2026, 6, 5))
    assert wrote2.written is False
    assert p.log_path.read_text("utf-8") == first  # contenuto identico
    assert p.log_path.stat().st_mtime_ns == mtime_first  # nessun timestamp modificato


def test_append_log_requires_existing_log(tmp_path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    p = load_profile(cfg)  # struttura non inizializzata → log assente
    with pytest.raises(ConfigError):
        append_log(p, "record", "X")


def test_upsert_index_inserts_then_idempotent(tmp_path):
    p = _profile(tmp_path)
    wrote = upsert_index(p, "concepts/rag.md", "Retrieval-Augmented Generation")
    assert wrote is True
    assert "[[concepts/rag.md]] — Retrieval-Augmented Generation" in p.index_path.read_text("utf-8")

    mtime = p.index_path.stat().st_mtime_ns
    wrote2 = upsert_index(p, "concepts/rag.md", "Retrieval-Augmented Generation")
    assert wrote2 is False  # stessa identità + stesso sommario → no-op
    assert p.index_path.stat().st_mtime_ns == mtime


def test_upsert_index_updates_changed_summary_without_duplicating(tmp_path):
    p = _profile(tmp_path)
    upsert_index(p, "concepts/rag.md", "vecchio")
    upsert_index(p, "concepts/rag.md", "nuovo")
    content = p.index_path.read_text("utf-8")
    assert content.count("[[concepts/rag.md]]") == 1  # id stabile: una sola riga
    assert "nuovo" in content and "vecchio" not in content


def test_sc002_full_rerun_is_identical(tmp_path):
    # SC-002 trasversale: due esecuzioni identiche dell'intera sequenza → output identico.
    p = _profile(tmp_path)
    append_log(p, "record", "Step", on_date=date(2026, 6, 5))
    upsert_index(p, "concepts/rag.md", "RAG")
    snapshot_log = p.log_path.read_text("utf-8")
    snapshot_index = p.index_path.read_text("utf-8")

    append_log(p, "record", "Step", on_date=date(2026, 6, 5))
    upsert_index(p, "concepts/rag.md", "RAG")
    assert p.log_path.read_text("utf-8") == snapshot_log
    assert p.index_path.read_text("utf-8") == snapshot_index
