"""CI smoke for the portable hooks (A-09, T018 / contract C6) — the REAL invocation vehicle.

The parity suite (`test_portable_hooks_parity.py`) runs the hooks via the test's own interpreter to
assert the observable contract offline. THIS suite instead drives each hook through the *actual*
host-facing vehicle — `uv run --no-project python <hook>.py [args]` — to prove it executes and
exits 0 on every OS, no `pwsh`/shell dependency. Marked `hooks_smoke` and run as a dedicated CI
matrix step (ubuntu + windows); `--no-project` isolates from this repo's `pyproject.toml` (T002).

The core guarantee here is EXIT 0 via the portable vehicle (SC-001/005); the per-assistant output
and state schemas are the parity suite's job — a couple of representative effects are re-checked to
catch a vehicle that runs but mangles I/O (e.g. an encoding/stdin regression only via `uv run`).
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.hooks_smoke

_ASSETS = Path(__file__).resolve().parents[1] / "src" / "sertor_installer" / "assets"
_RAG_HOOKS = _ASSETS / "rag" / "hooks"
_WIKI_HOOKS = _ASSETS / "claude" / "hooks"


def _hook_path(hook: str) -> Path:
    """Locate a hook `.py` — RAG hooks live under `rag/hooks/`, wiki hooks under `claude/hooks/`."""
    rag = _RAG_HOOKS / f"{hook}.py"
    return rag if rag.is_file() else _WIKI_HOOKS / f"{hook}.py"


def _run(hook: str, *, event: str | None, root: Path, args: list[str] | None = None):
    """Run a portable hook through the REAL vehicle: `uv run --no-project python <hook> [args]`.

    Full environ is inherited so `uv` is found on PATH; `CLAUDE_PROJECT_DIR` points the hook at the
    host root. `--no-project` ignores this repo's `pyproject.toml` (portable-from-anywhere, T002).
    """
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    cmd = ["uv", "run", "--no-project", "python", str(_hook_path(hook)), *(args or [])]
    return subprocess.run(
        cmd,
        input=event if event is not None else "",
        capture_output=True,
        text=True,
        env=env,
        timeout=120,  # first `uv run --no-project` may warm up an interpreter
    )


# --- PreToolUse: sertor-rag-usage-check (fail-open) ---------------------------------------------

def test_usage_check_runs_and_fails_open(tmp_path: Path):
    event = json.dumps({"tool_input": {"content": "import sertor_core as sc"}})
    r = _run("sertor-rag-usage-check", event=event, root=tmp_path, args=["--assistant", "claude"])
    assert r.returncode == 0
    assert r.stdout == ""              # fail-open: no stdout payload a host could read as `deny`
    assert "sertor_core" in r.stderr   # warning goes to stderr only


# --- SessionStart signals (state → stdout directive) --------------------------------------------

def test_rag_freshness_start_runs_and_induces_on_degraded(tmp_path: Path):
    (tmp_path / ".sertor").mkdir()
    (tmp_path / ".sertor" / ".rag-health.json").write_text(
        json.dumps({"schema": "rag.health/1", "verdict": "degraded", "reason": "index area: fail"}),
        encoding="utf-8",
    )
    r = _run("rag-freshness-start", event="{}", root=tmp_path, args=["--assistant", "claude"])
    assert r.returncode == 0
    assert "DEGRADED" in r.stdout and "sertor-rag index" in r.stdout


def test_version_check_start_runs_and_warns_on_behind(tmp_path: Path):
    (tmp_path / ".sertor").mkdir()
    (tmp_path / ".sertor" / ".version-check.json").write_text(
        json.dumps({"schema": "version.check/1", "verdict": "behind",
                    "installed": "0.1.0", "latest": "0.2.0"}),
        encoding="utf-8",
    )
    r = _run("version-check-start", event="{}", root=tmp_path, args=["--assistant", "claude"])
    assert r.returncode == 0
    assert "SERTOR UPDATE" in r.stdout


# --- SessionEnd / state-writing hooks (exit 0, no network) --------------------------------------

def test_version_check_runs_hermetic_from_fresh_cache(tmp_path: Path):
    """Seed a FRESH cache so the GET path is skipped — hermetic (no network) while still exercising
    the read→compare→write flow through the real vehicle."""
    (tmp_path / ".sertor").mkdir()
    (tmp_path / ".sertor" / ".sertor-version").write_text("0.1.0\n", encoding="utf-8")
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    (tmp_path / ".sertor" / ".version-check.json").write_text(
        json.dumps({"schema": "version.check/1", "verdict": "up-to-date",
                    "installed": "0.1.0", "latest": "0.1.0", "checked_at": now}),
        encoding="utf-8",
    )
    r = _run("version-check", event="{}", root=tmp_path, args=["--assistant", "claude"])
    assert r.returncode == 0
    state = json.loads((tmp_path / ".sertor" / ".version-check.json").read_text(encoding="utf-8"))
    assert state["schema"] == "version.check/1"


def test_memory_capture_runs_noop_when_disabled(tmp_path: Path):
    # SERTOR_MEMORY unset → privacy gate no-op; must still exit 0 through the vehicle.
    env_root = tmp_path
    r = _run("memory-capture", event="{}", root=env_root, args=["--assistant", "claude"])
    assert r.returncode == 0


def test_rag_freshness_foreground_detaches_and_returns(tmp_path: Path):
    """The foreground only spawns the detached worker and returns immediately — it must exit 0
    (the worker's re-index runs off the critical path; here `.sertor` is absent so the worker is a
    non-fatal no-op). Proves the cross-OS detach path (C5) does not hang or crash the vehicle."""
    event = json.dumps({"cwd": str(tmp_path)})
    r = _run("rag-freshness", event=event, root=tmp_path, args=["--assistant", "claude"])
    assert r.returncode == 0


# --- wiki hooks (per-assistant native output) ---------------------------------------------------

def test_wiki_session_start_runs_per_assistant(tmp_path: Path):
    r_claude = _run("wiki-session-start", event="{}", root=tmp_path, args=["--assistant", "claude"])
    assert r_claude.returncode == 0
    assert "SESSION START" in r_claude.stdout          # claude: directive on stdout

    r_copilot = _run("wiki-session-start", event="{}", root=tmp_path,
                     args=["--assistant", "copilot"])
    assert r_copilot.returncode == 0
    assert json.loads(r_copilot.stdout)["additionalContext"]  # copilot: JSON additionalContext


def test_wiki_pending_check_runs_noop_without_config(tmp_path: Path):
    # No wiki/wiki.config.toml under the root → nothing to scan → no output, exit 0.
    r = _run("wiki-pending-check", event="{}", root=tmp_path,
             args=["--mode", "Stop", "--assistant", "claude"])
    assert r.returncode == 0
    assert r.stdout.strip() == ""
