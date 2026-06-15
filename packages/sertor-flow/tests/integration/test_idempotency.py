"""US3 — idempotenza di `sertor-flow install` (T039, FR-017/SC-005).

Seconda esecuzione su un repo già installato → ogni artefatto è `skipped` e nulla
cambia sul filesystem (zero modifiche).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_flow.__main__ import main
from sertor_flow.install_governance import execute_governance_plan
from sertor_flow.profile import build_governance_profile
from tests.conftest import FakeSpecifyRunner


def _snapshot(root: Path) -> dict[str, bytes]:
    """Maps every file under `root` to its bytes (for byte-exact comparison)."""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture()
def installed(tmp_path: Path, fake_runner) -> Path:
    rc = main(["install", "--target", str(tmp_path)], runner=fake_runner)
    assert rc == 0
    return tmp_path


def test_second_run_all_skipped(installed: Path):
    """Re-install → no CREATED/MERGED/BLOCK, only SKIPPED (SC-005).

    The SpecKit launch is idempotent (layout present → skipped, no relaunch), so the second run is
    all-skipped including step 0.
    """
    profile = build_governance_profile(installed)
    report = execute_governance_plan(profile, runner=FakeSpecifyRunner())

    assert report.exit_code() == 0
    assert report.created == 0
    assert report.merged == 0
    assert report.block == 0
    assert report.errors == 0
    assert report.skipped == len(report.outcomes)
    assert all(o.outcome.value == "skipped" for o in report.outcomes)


def test_second_run_changes_nothing_on_disk(installed: Path):
    """Re-install is byte-for-byte a no-op on the filesystem (FR-017)."""
    before = _snapshot(installed)
    rc = main(["install", "--target", str(installed)], runner=FakeSpecifyRunner())
    assert rc == 0
    after = _snapshot(installed)
    assert before == after
