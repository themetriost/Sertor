"""A-17: `sertor_installer.sync --check` is a read-only drift gate (exit 1 iff any asset differs).

Hermetic: each test drives the sync CLI against its own tmp root, never the real dogfood `.claude/`.
"""
from __future__ import annotations

from pathlib import Path

from sertor_installer import sync


def test_check_exit_one_when_nothing_synced(tmp_path: Path):
    # A fresh root has no `.claude/` → every byte-copied asset "would be created" = drift → exit 1.
    assert sync.main(["--repo-root", str(tmp_path), "--check"]) == 1


def test_check_exit_zero_after_sync(tmp_path: Path):
    # Propagate the assets, then --check on the same root → all identical → exit 0.
    sync.main(["--repo-root", str(tmp_path)])
    assert sync.main(["--repo-root", str(tmp_path), "--check"]) == 0


def test_check_does_not_write(tmp_path: Path):
    # --check never mutates: a missing `.claude/` stays missing after a check.
    sync.main(["--repo-root", str(tmp_path), "--check"])
    assert not (tmp_path / ".claude").exists()
