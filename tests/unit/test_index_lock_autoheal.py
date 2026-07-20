"""Unit tests for the index-lock auto-heal (E10-FEAT-035).

A crashed, detached `rag-freshness` worker can die mid-re-index and leave `.index.lock` holding a
**dead PID**; before this fix every subsequent `index()` failed with `IndexLockedError` until the
lockfile was removed by hand (observed live 2026-07-17, PID 33516). The lock now auto-heals: a
lockfile whose recorded PID is confirmed dead is reclaimed; a live PID (or an ambiguous lockfile)
still locks. Reclaiming is observable (Principio XII). Cross-OS liveness never perturbs the process.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys

import pytest

from sertor_core.domain.errors import IndexLockedError
from sertor_core.services import indexing
from sertor_core.services.indexing import _IndexLock, _pid_alive

_LOCK = ".index.lock"


def _dead_pid() -> int:
    """A PID that has certainly exited — spawned and reaped, so it is not a zombie."""
    proc = subprocess.Popen([sys.executable, "-c", ""])
    proc.wait()
    return proc.pid


# --- _pid_alive: cross-OS liveness, never perturbs the process (REQ-010) -----------------------

def test_pid_alive_self_is_true():
    assert _pid_alive(os.getpid()) is True


def test_pid_alive_dead_is_false():
    assert _pid_alive(_dead_pid()) is False


def test_pid_alive_nonpositive_is_false():
    assert _pid_alive(0) is False
    assert _pid_alive(-1) is False


# --- auto-heal in _IndexLock -------------------------------------------------------------------

def test_reclaims_stale_lock_with_dead_pid(tmp_path, monkeypatch, caplog):
    """A lockfile holding a dead PID is reclaimed → the run acquires the lock (REQ-007)."""
    monkeypatch.setattr(indexing, "_pid_alive", lambda pid: False)
    idx = tmp_path / "idx"
    idx.mkdir()
    (idx / _LOCK).write_text("33516", encoding="utf-8")  # a crashed worker's dead PID
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        with _IndexLock(idx):
            assert (idx / _LOCK).exists()  # now held by us
    # REQ-009: the reclaim is observable, not silent.
    assert any(getattr(r, "operation", "") == "index.lock.reclaimed" for r in caplog.records)


def test_live_pid_still_raises_index_locked(tmp_path, monkeypatch):
    """A lockfile whose PID is alive still locks — single-writer guard preserved (REQ-008)."""
    monkeypatch.setattr(indexing, "_pid_alive", lambda pid: True)
    idx = tmp_path / "idx"
    idx.mkdir()
    (idx / _LOCK).write_text(str(os.getpid()), encoding="utf-8")
    with pytest.raises(IndexLockedError):
        with _IndexLock(idx):
            pass


@pytest.mark.parametrize("holder", ["", "   ", "not-a-pid", "12x3"])
def test_ambiguous_lockfile_is_not_reclaimed(tmp_path, monkeypatch, holder):
    """An empty/garbage lockfile is NOT stolen even if liveness would say 'dead' — it may be a live
    run between `create` and the PID `write` (conservative fail-loud, REQ-008, R-1)."""
    monkeypatch.setattr(indexing, "_pid_alive", lambda pid: False)
    idx = tmp_path / "idx"
    idx.mkdir()
    (idx / _LOCK).write_text(holder, encoding="utf-8")
    with pytest.raises(IndexLockedError):
        with _IndexLock(idx):
            pass


def test_clean_acquire_and_release(tmp_path):
    """No pre-existing lock → acquire, and the lockfile is removed on exit (non-regression)."""
    idx = tmp_path / "idx"
    idx.mkdir()
    with _IndexLock(idx):
        assert (idx / _LOCK).exists()
    assert not (idx / _LOCK).exists()
