"""End-to-end host smoke test (@integration) — install→index→doctor→search from git+url@master.

This is the CI-facing wrapper around the platform smoke script (`scripts/smoke.ps1` on Windows,
`scripts/smoke.sh` on POSIX). The script is the SINGLE SOURCE OF TRUTH for the flow (no logic is
duplicated here); the test merely invokes it and asserts on its contract:

  * exit code 0,
  * a final ``SMOKE_OK doctor=<pass|warn> documents=<N> results=<M>`` marker with N>0 and M>0.

Why a wrapper instead of re-implementing the flow in Python: the same script a developer runs by
hand is what CI runs, so they cannot drift. The script already drives the real installed
entry-points (`uvx --from git+url … sertor install rag`, then `uv run --project .sertor sertor-rag
…`), which is exactly what catches the integration bugs the offline suite misses (CLI
discoverability, cwd/index anchoring). It pulls ``master`` — the real distribution channel — so this
is a POST-MERGE / on-demand guardian, not a per-PR gate (it does not test the PR's own diff).

Target selection: by default the script runs on a NEUTRAL synthetic fixture it creates in a temp
dir. Set the optional env var ``SERTOR_SMOKE_TARGET`` to a path to an already-cloned repo and the
test forwards it to the script via ``-Target``/``--target`` — CI uses this to run on the dedicated
real-world target ``https://github.com/themetriost/PgnToFen`` (a C#/.NET project). The assertions
are identical for both modes.

Precondition (``uv``/``uvx`` in PATH + network) absent → ``pytest.skip`` (actionable, never a false
green). No ``sertor_core`` import (Principio XI): it exercises the artefacts, not the library.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Final marker the script prints on success (see scripts/smoke.{ps1,sh}).
_MARKER = re.compile(r"^SMOKE_OK doctor=(pass|warn) documents=(\d+) results=(\d+)", re.MULTILINE)


def _smoke_target() -> str | None:
    """Real-repo target from ``SERTOR_SMOKE_TARGET`` (CI: PgnToFen); None → synthetic fixture."""
    raw = os.environ.get("SERTOR_SMOKE_TARGET", "").strip()
    if not raw:
        return None
    target = Path(raw).expanduser()
    if not target.is_dir():
        pytest.skip(f"SERTOR_SMOKE_TARGET is not a directory: {raw}")
    return str(target.resolve())


def _smoke_command(target: str | None) -> list[str]:
    """Platform-specific invocation of the smoke script (ps1 on Windows, sh elsewhere).

    When ``target`` is set it is forwarded so the script runs on that real repo: ``-Target <path>``
    on Windows, ``master <path>`` (REF then TARGET positional) on POSIX. Without it the script falls
    back to its neutral synthetic fixture.
    """
    if sys.platform == "win32":
        script = SCRIPTS_DIR / "smoke.ps1"
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh is None:
            pytest.skip("no PowerShell (pwsh/powershell) in PATH — Windows smoke not runnable")
        cmd = [pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
        if target is not None:
            cmd += ["-Target", target]
        return cmd
    script = SCRIPTS_DIR / "smoke.sh"
    cmd = ["bash", str(script)]
    if target is not None:
        cmd += ["master", target]  # positional: REF then TARGET (see scripts/smoke.sh usage)
    return cmd


def _preconditions_or_skip() -> None:
    if shutil.which("uvx") is None or shutil.which("uv") is None:
        pytest.skip("uv/uvx not in PATH — host smoke (git+url install) not runnable")
    if sys.platform != "win32" and shutil.which("bash") is None:
        pytest.skip("bash not in PATH — POSIX smoke not runnable")


def test_host_smoke_install_index_doctor_search():
    """The smoke script installs from git+url@master and drives index→doctor→search to green.

    Asserts exit 0 and the SMOKE_OK marker with documents>0 (the cwd/anchor regression would yield
    documents=0) and results>0. On failure, the captured output is surfaced for diagnosis. Runs on
    ``SERTOR_SMOKE_TARGET`` if set (CI: PgnToFen), else on the neutral synthetic fixture.
    """
    _preconditions_or_skip()
    target = _smoke_target()
    script = (SCRIPTS_DIR / "smoke.ps1") if sys.platform == "win32" else (SCRIPTS_DIR / "smoke.sh")
    assert script.is_file(), f"smoke script missing: {script}"

    proc = subprocess.run(
        _smoke_command(target),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=900,  # git+url install + isolated venv sync + index/doctor/search (~1-2 min)
    )
    combined = proc.stdout + "\n" + proc.stderr
    assert proc.returncode == 0, (
        f"smoke script exited {proc.returncode}\n--- stdout/stderr ---\n{combined[-4000:]}"
    )
    match = _MARKER.search(combined)
    assert match, f"no SMOKE_OK marker in output\n--- stdout/stderr ---\n{combined[-4000:]}"
    documents = int(match.group(2))
    results = int(match.group(3))
    assert documents > 0, f"documents={documents} (expected > 0; cwd/anchor bug gives 0)"
    assert results > 0, f"results={results} (expected > 0)"


def test_no_sertor_core_import():
    """Principio XI — the smoke wrapper exercises artefacts, never imports the library."""
    text = Path(__file__).read_text(encoding="utf-8")
    offenders = [
        ln for ln in text.splitlines()
        if re.match(r"\s*(import|from)\s+sertor_core\b", ln)
    ]
    assert not offenders, f"violated Principio XI: import of sertor_core: {offenders}"
