"""Test FEAT-008 — meccanica del log: rotazione giornaliera, append curato, scan, migrate.

Offline F.I.R.S.T. (`tmp_path`, no rete). Copre SC-001..SC-005 della spec 008-meccanica-log.
"""
from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.registry import append_log, migrate_log, update_log_index
from sertor_core.wiki_tools.scan import scan
from sertor_core.wiki_tools.structure import init_structure

_CONFIG_ROT = """\
profile = "code+doc"
language = "it"
root = "wiki"
log_file = "log.md"
log_dir = "log"
log_format = "## [{date}] {op} | {title}"
source_dirs = ["src"]
exclude = [".venv*", "__pycache__"]

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"

[strings]
pending = "Pendenti: {n}"
clean = "Allineato"
"""

_CONFIG_SINGLE = """\
profile = "code+doc"
language = "it"
root = "wiki"
log_file = "log.md"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
"""

_MONO_LOG = """\
# Log

Registro append-only (preambolo, non una voce).

## [2026-05-30] setup | Apertura
- bullet a

## [2026-06-07] record | Primo del 7
corpo del primo

## [2026-06-07] lint | Secondo del 7
- ok

## [2026-06-08] record | Oggi
"""


def _profile(tmp_path: Path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG_ROT, encoding="utf-8")
    p = load_profile(cfg)
    init_structure(p)
    return p


def _set_mtime(path: Path, ts: float) -> None:
    os.utime(path, (ts, ts))


# --- US1: append curato + rotazione implicita -------------------------------------------------

def test_append_creates_daily_partition_with_body(tmp_path):
    # SC-001 (file della sua data) + SC-002 (corpo curato non riformattato).
    p = _profile(tmp_path)
    res = append_log(p, "record", "Primo", on_date=date(2026, 6, 8), body="Lead.\n- **X:** y")
    assert res.written is True and res.created is True
    assert res.partition == "log/2026-06-08.md"
    text = p.partition_path(date(2026, 6, 8)).read_text("utf-8")
    assert "## [2026-06-08] record | Primo" in text
    assert "Lead.\n- **X:** y" in text  # corpo preservato verbatim


def test_second_entry_same_day_appends(tmp_path):
    p = _profile(tmp_path)
    append_log(p, "record", "A", on_date=date(2026, 6, 8))
    res = append_log(p, "lint", "B", on_date=date(2026, 6, 8))
    assert res.created is False and res.written is True
    text = p.partition_path(date(2026, 6, 8)).read_text("utf-8")
    assert "## [2026-06-08] record | A" in text and "## [2026-06-08] lint | B" in text


def test_append_idempotent_on_heading(tmp_path):
    # SC-004 + DA-5: identità = heading; ri-append con corpo diverso → no-op.
    p = _profile(tmp_path)
    append_log(p, "record", "A", on_date=date(2026, 6, 8), body="corpo 1")
    snap = p.partition_path(date(2026, 6, 8)).read_text("utf-8")
    res = append_log(p, "record", "A", on_date=date(2026, 6, 8), body="corpo 2 diverso")
    assert res.written is False
    assert p.partition_path(date(2026, 6, 8)).read_text("utf-8") == snap


def test_append_routes_by_date(tmp_path):
    p = _profile(tmp_path)
    append_log(p, "record", "A", on_date=date(2026, 6, 8))
    append_log(p, "record", "B", on_date=date(2026, 6, 9))
    assert p.partition_path(date(2026, 6, 8)).is_file()
    assert p.partition_path(date(2026, 6, 9)).is_file()


# --- US4: indice delle partizioni -------------------------------------------------------------

def test_partition_index_lists_days_idempotent(tmp_path):
    p = _profile(tmp_path)
    append_log(p, "record", "A", on_date=date(2026, 6, 8))
    append_log(p, "record", "B", on_date=date(2026, 6, 9))
    idx = p.log_index_path.read_text("utf-8")
    assert "[2026-06-08](2026-06-08.md)" in idx and "[2026-06-09](2026-06-09.md)" in idx
    before = idx
    assert update_log_index(p) is False  # già aggiornato → no-op
    assert p.log_index_path.read_text("utf-8") == before


# --- US2: scan ancora sulla partizione più recente (parità hook) ------------------------------

def test_scan_anchors_on_latest_partition(tmp_path):
    # SC-003: il pendente si conta rispetto alla partizione più recente, non a un file unico.
    p = _profile(tmp_path)
    append_log(p, "record", "old", on_date=date(2026, 6, 1))
    append_log(p, "record", "new", on_date=date(2026, 6, 8))
    anchor = time.time()
    _set_mtime(p.partition_path(date(2026, 6, 1)), anchor - 500)
    _set_mtime(p.partition_path(date(2026, 6, 8)), anchor)

    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    fresh = src / "fresh.py"
    fresh.write_text("x\n", "utf-8")
    _set_mtime(fresh, anchor + 100)
    stale = src / "stale.py"
    stale.write_text("y\n", "utf-8")
    _set_mtime(stale, anchor - 100)

    res = scan(p)
    assert res.schema == "wiki.scan/1"  # contratto invariato
    assert res.pending == 1  # solo fresh è più recente della partizione più recente


def test_scan_no_partitions_means_everything_pending(tmp_path):
    p = _profile(tmp_path)  # nessuna partizione ancora creata
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    (src / "a.py").write_text("a\n", "utf-8")
    res = scan(p)
    assert res.anchor is None and res.pending == 1


# --- US3: migrate (split retroattivo) ---------------------------------------------------------

def test_migrate_splits_by_date_preserving_order(tmp_path):
    # SC-005: una partizione per data distinta; più voci stessa data → stessa partizione, in ordine.
    p = _profile(tmp_path)
    p.log_path.write_text(_MONO_LOG, encoding="utf-8")
    res = migrate_log(p)
    assert res.migrated_entries == 4
    assert set(res.created) == {"2026-05-30.md", "2026-06-07.md", "2026-06-08.md"}
    d7 = p.partition_path(date(2026, 6, 7)).read_text("utf-8")
    assert "## [2026-06-07] record | Primo del 7" in d7
    assert "## [2026-06-07] lint | Secondo del 7" in d7
    assert d7.index("Primo del 7") < d7.index("Secondo del 7")  # ordine preservato


def test_migrate_idempotent_and_non_destructive(tmp_path):
    p = _profile(tmp_path)
    p.log_path.write_text(_MONO_LOG, encoding="utf-8")
    migrate_log(p)
    res2 = migrate_log(p)
    assert res2.migrated_entries == 0 and res2.created == []
    assert set(res2.skipped) == {"2026-05-30.md", "2026-06-07.md", "2026-06-08.md"}
    assert p.log_path.is_file()  # monolitico non cancellato (non distruttivo)


def test_collect_and_lint_exclude_log_partitions(tmp_path):
    # Le partizioni di log non sono pagine: collect/lint non devono enumerarle né flaggarle
    # (regressione da attivazione: le wikilink-esempio nelle vecchie voci → falsi 'broken').
    from sertor_core.wiki_tools.collect import collect
    from sertor_core.wiki_tools.lint import lint

    p = _profile(tmp_path)
    append_log(p, "record", "voce", on_date=date(2026, 6, 8),
               body="esempio di sintassi [[wikilink-finto]] dentro una voce di log")
    rels = {pg["rel_path"] for pg in collect(p).pages}
    assert not any(r.startswith("log/") for r in rels)  # partizioni + indice-log esclusi
    broken = lint(p).broken_links
    assert not any(b.get("page", "").startswith("log/") for b in broken)


def test_migrate_requires_rotation(tmp_path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG_SINGLE, encoding="utf-8")
    p = load_profile(cfg)
    init_structure(p)
    with pytest.raises(ConfigError):
        migrate_log(p)
