"""End-to-end host smoke test (@integration) — install (+runtime for rag) from git+url@master.

This is the CI-facing wrapper around the platform smoke script (`scripts/smoke.ps1` on Windows,
`scripts/smoke.sh` on POSIX). The script is the SINGLE SOURCE OF TRUTH for each flow (no logic is
duplicated here); the test merely invokes it for an `(assistant, capability)` pair and asserts on
its contract:

  * exit code 0,
  * a final ``SMOKE_OK assistant=<a> capability=<c> ...`` marker; for ``rag`` the marker also
    carries ``documents=<N> results=<M>`` with N>0 and M>0 (the cwd/anchor regression yields N=0).

MATRIX: {claude, copilot-cli} x {rag, wiki, flow}.
  * rag   — installs the RAG capability, then drives index→doctor→search (CLI runtime).
  * wiki  — installs the wiki system (deposit-only: skill/agent/hooks/config/scaffold/ritual block).
  * flow  — installs the governance/SDLC bundle via ``sertor-flow`` (deposit-only; ``specify init``
            needs NETWORK + the pinned spec-kit).

Why a wrapper instead of re-implementing the flow in Python: the same script a developer runs by
hand is what CI runs, so they cannot drift. The script drives the real installed entry-points
(``uvx --from git+url … sertor install <cap>`` / ``sertor-flow install``), which is exactly what
catches the integration bugs the offline suite misses (CLI discoverability, cwd/index anchoring,
per-assistant asset routing). The install ref is ``SERTOR_SMOKE_REF`` (default ``master``); CI sets
it to the PR branch (A-10), so on a PR the smoke installs the PR's OWN diff — a true pre-merge gate,
not just a post-merge guardian. On push/dispatch it stays on ``master`` (the distribution channel).

Target selection: by default the script runs on a NEUTRAL synthetic fixture it creates in a temp
dir. For ``rag`` ONLY, set the optional env var ``SERTOR_SMOKE_TARGET`` to a path to an
already-cloned repo and the test forwards it to the script — CI uses this to run rag on the
dedicated real-world target ``https://github.com/themetriost/PgnToFen`` (a C#/.NET project).
``wiki`` and ``flow`` always use the synthetic fixture (deposit-only, target-agnostic).

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

ASSISTANTS = ("claude", "copilot-cli")
CAPABILITIES = ("rag", "wiki", "flow")

# Final marker the script prints on success (see scripts/smoke.{ps1,sh}). The trailing fields are
# capability-specific (rag carries documents/results), so the common prefix is matched here.
_MARKER = re.compile(
    r"^SMOKE_OK assistant=(?P<assistant>\S+) capability=(?P<capability>\S+)(?P<rest>.*)$",
    re.MULTILINE,
)
_RAG_FIELDS = re.compile(r"documents=(?P<documents>\d+) results=(?P<results>\d+)")


def _smoke_target(capability: str) -> str | None:
    """Real-repo target from ``SERTOR_SMOKE_TARGET`` (CI: PgnToFen) — rag only; else synthetic.

    Only the ``rag`` capability indexes content, so the real target is meaningful only there. The
    deposit-only capabilities (``wiki``/``flow``) always use the synthetic fixture.
    """
    if capability != "rag":
        return None
    raw = os.environ.get("SERTOR_SMOKE_TARGET", "").strip()
    if not raw:
        return None
    target = Path(raw).expanduser()
    if not target.is_dir():
        pytest.skip(f"SERTOR_SMOKE_TARGET is not a directory: {raw}")
    return str(target.resolve())


def _smoke_ref() -> str:
    """Git ref the smoke installs from (A-10). ``SERTOR_SMOKE_REF`` (default ``master``): CI sets it
    to the PR branch so a PR's smoke tests the PR's OWN diff (a true pre-merge gate), not master."""
    return os.environ.get("SERTOR_SMOKE_REF", "master").strip() or "master"


def _smoke_command(
    assistant: str, capability: str, target: str | None, from_ref: str | None = None,
) -> list[str]:
    """Platform-specific invocation of the smoke script (ps1 on Windows, sh elsewhere).

    The assistant/capability are passed as flags; ``target`` (rag only) is forwarded so the script
    runs on that real repo. The git ref to install from is ``_smoke_ref()`` — ``-Ref`` on Windows,
    the leading positional ``REF`` on POSIX (the script parses positionals and flags independently).

    ``from_ref`` selects the **upgrade** flow (E15-FEAT-012): the script installs that release
    first, upgrades to ``ref``, then asserts the outcomes. Omitted → install-only, unchanged.
    """
    ref = _smoke_ref()
    if sys.platform == "win32":
        script = SCRIPTS_DIR / "smoke.ps1"
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh is None:
            pytest.skip("no PowerShell (pwsh/powershell) in PATH — Windows smoke not runnable")
        cmd = [pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
        cmd += ["-Ref", ref, "-Assistant", assistant, "-Capability", capability]
        if target is not None:
            cmd += ["-Target", target]
        if from_ref:
            cmd += ["-FromRef", from_ref]
        return cmd
    script = SCRIPTS_DIR / "smoke.sh"
    cmd = ["bash", str(script), ref]  # positional REF
    if target is not None:
        cmd += [target]  # positional TARGET (REF then TARGET — see scripts/smoke.sh usage)
    cmd += ["--assistant", assistant, "--capability", capability]
    if from_ref:
        cmd += ["--from-ref", from_ref]
    return cmd


def _previous_release() -> str | None:
    """The last published release, **derived** from the public reference — never hand-written.

    Principle XIV applied to the verification itself: a list of versions in a CI file would be a
    copy of a fact that lives elsewhere, and it would age exactly like every other copy this project
    has paid for. `None` when no tag is reachable (shallow clone, or a repo before release 1).

    ``SERTOR_SMOKE_FROM_REF`` overrides the derivation — that is how the on-demand workflow drives a
    **long jump** (a host several versions behind), the condition in which the pin defect actually
    surfaced. An override is a parameter, not a hardcoded version that would age.
    """
    override = os.environ.get("SERTOR_SMOKE_FROM_REF", "").strip()
    if override:
        return override
    proc = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    tag = proc.stdout.strip()
    return tag or None


def _preconditions_or_skip() -> None:
    if shutil.which("uvx") is None or shutil.which("uv") is None:
        pytest.skip("uv/uvx not in PATH — host smoke (git+url install) not runnable")
    if sys.platform != "win32" and shutil.which("bash") is None:
        pytest.skip("bash not in PATH — POSIX smoke not runnable")


@pytest.mark.parametrize("assistant", ASSISTANTS)
@pytest.mark.parametrize("capability", CAPABILITIES)
def test_host_smoke(assistant: str, capability: str):
    """The smoke script installs from git+url@<ref> for (assistant, capability) and asserts green.

    For ``rag`` it also drives index→doctor→search and asserts documents>0 (the cwd/anchor
    regression would yield documents=0) and results>0. For ``wiki``/``flow`` it asserts the deposit
    marker. On failure the captured output is surfaced for diagnosis.
    """
    _preconditions_or_skip()
    target = _smoke_target(capability)
    script = (SCRIPTS_DIR / "smoke.ps1") if sys.platform == "win32" else (SCRIPTS_DIR / "smoke.sh")
    assert script.is_file(), f"smoke script missing: {script}"

    proc = subprocess.run(
        _smoke_command(assistant, capability, target),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        # git+url install + isolated venv sync; flow additionally pulls spec-kit via specify init.
        timeout=1200,
    )
    combined = proc.stdout + "\n" + proc.stderr
    assert proc.returncode == 0, (
        f"smoke script exited {proc.returncode}\n--- stdout/stderr ---\n{combined[-4000:]}"
    )
    match = _MARKER.search(combined)
    assert match, f"no SMOKE_OK marker in output\n--- stdout/stderr ---\n{combined[-4000:]}"
    assert match.group("assistant") == assistant, "marker assistant mismatch"
    assert match.group("capability") == capability, "marker capability mismatch"

    if capability == "rag":
        fields = _RAG_FIELDS.search(match.group("rest"))
        assert fields, f"rag marker missing documents/results\n{combined[-2000:]}"
        documents = int(fields.group("documents"))
        results = int(fields.group("results"))
        assert documents > 0, f"documents={documents} (expected > 0; cwd/anchor bug gives 0)"
        assert results > 0, f"results={results} (expected > 0)"


@pytest.mark.integration
@pytest.mark.parametrize("assistant", ASSISTANTS)
def test_host_upgrade_smoke(assistant: str):
    """E15-FEAT-012 — the host STARTS from the previous release, upgrades, and the outcomes hold.

    This is the verb the hosts actually run and that nothing exercised: of ~14 real field defects,
    13 sit in the delivery surface and all 7 installer ones need a **pre-existing older
    installation** to show up — a clean host cannot see any of them, by construction.

    Deliberately `rag` only: it is the capability where 7 of 7 installer defects were born, and the
    automatic path must stay cheap enough that nobody wants to switch it off (risk R-1). The full
    perimeter is the manually-triggerable path, and that exclusion is declared, not forgotten.

    Exit code 2 from the script means an **environment impediment** (previous release unreachable,
    no network) — not a product defect, so it skips instead of failing red. Collapsing the two is
    what teaches people to ignore a gate.
    """
    _preconditions_or_skip()
    from_ref = _previous_release()
    if from_ref is None:
        pytest.skip("no reachable release tag — upgrade smoke needs a published starting point")

    proc = subprocess.run(
        _smoke_command(assistant, "rag", _smoke_target("rag"), from_ref=from_ref),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=1800,  # two full installs plus an upgrade
    )
    combined = proc.stdout + "\n" + proc.stderr
    if proc.returncode == 2 or "SMOKE_ENV:" in combined:
        pytest.skip(f"environment impediment, not a product defect:\n{combined[-1500:]}")
    assert proc.returncode == 0, (
        f"upgrade smoke exited {proc.returncode}\n--- stdout/stderr ---\n{combined[-4000:]}"
    )
    assert f"upgrade={from_ref}->" in combined, (
        f"no upgrade marker in output\n--- stdout/stderr ---\n{combined[-4000:]}"
    )

    # Exit code 0 says the script did not fail. It does NOT say the outcomes were asserted: every
    # one of them sits behind a precondition (`.sertor/` exists, the hook was deposited, the file is
    # there) and takes a printed `n/a` branch when the precondition is absent. A run where all of
    # them went `n/a` exits 0 and reads exactly like a run where all of them held.
    #
    # So the wrapper demands them by NAME. `hook-single:*` is deliberately absent from the list: it
    # is conditional on the stem appearing at all, and demanding it would assert the fixture rather
    # than the host. This is the guard against this gate quietly becoming vacuous — which is a
    # different failure from it going red, and the one nobody notices.
    required = (
        "pin-moved",
        "host-config-preserved",
        "mcp-invocation-shape",
        "no-stale-divergence",
        "version-derived-from-runtime",
        "health-green",
    )
    missing = [name for name in required if f"OK   {name}" not in combined]
    assert not missing, (
        f"the upgrade ran green without asserting {missing} — each was skipped or never reached, "
        f"so this pass measured less than it appears to\n--- stdout/stderr ---\n{combined[-4000:]}"
    )

    # Printed so a GREEN run also shows what held: the assertion above makes vacuity impossible,
    # this makes the evidence readable without re-running (visible under `-s`, which CI passes).
    print("\n".join(ln for ln in combined.splitlines() if "[upgrade] " in ln or "SMOKE_OK" in ln))


def test_no_sertor_core_import():
    """Principio XI — the smoke wrapper exercises artefacts, never imports the library."""
    text = Path(__file__).read_text(encoding="utf-8")
    offenders = [
        ln for ln in text.splitlines()
        if re.match(r"\s*(import|from)\s+sertor_core\b", ln)
    ]
    assert not offenders, f"violated Principio XI: import of sertor_core: {offenders}"
