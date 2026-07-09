"""Parity tests for the portable Python hooks (A-09). Offline, host-agnostic.

Runs each hook as a subprocess (via the test's own Python — the hooks are stdlib-only, so any Python
runs them; the `uv run --no-project` invocation is exercised by the CI matrix smoke). Asserts the
observable contract the former `.ps1` produced: per-assistant output + state effects + fail-safe
(exit 0 always). This suite is the pre-merge parity gate (SC-002).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC
from pathlib import Path

import pytest

_ASSETS = Path(__file__).resolve().parents[1] / "src" / "sertor_installer" / "assets"
_HOOKS = _ASSETS / "rag" / "hooks"
_WIKI_HOOKS = _ASSETS / "claude" / "hooks"


def _hook_path(hook: str) -> Path:
    """Locate a hook `.py` — RAG hooks live under `rag/hooks/`, wiki hooks under `claude/hooks/`."""
    rag = _HOOKS / f"{hook}.py"
    return rag if rag.is_file() else _WIKI_HOOKS / f"{hook}.py"


def _run(hook: str, *, event: str | None, root: Path, assistant: str = "claude"):
    """Run a portable hook with `event` on stdin and `CLAUDE_PROJECT_DIR=root`."""
    env = {"CLAUDE_PROJECT_DIR": str(root), "PATH": _os_path()}
    return subprocess.run(
        [sys.executable, str(_hook_path(hook)), "--assistant", assistant],
        input=event if event is not None else "",
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _os_path() -> str:
    import os

    return os.environ.get("PATH", "")


# --- sertor-rag-usage-check (PreToolUse, fail-open) ----------------------------------------------

@pytest.mark.parametrize("assistant", ["claude", "copilot"])
def test_usage_check_warns_on_direct_import(tmp_path: Path, assistant):
    event = json.dumps({"tool_input": {"content": "import sertor_core as sc"}})
    r = _run("sertor-rag-usage-check", event=event, root=tmp_path, assistant=assistant)
    assert r.returncode == 0
    assert r.stdout == ""  # fail-open: NO stdout payload (Copilot could read it as deny)
    assert "sertor_core" in r.stderr  # warning on stderr only


def test_usage_check_skips_test_paths(tmp_path: Path):
    event = json.dumps({"tool_input": {"file_path": "tests/a.py", "content": "import sertor_core"}})
    r = _run("sertor-rag-usage-check", event=event, root=tmp_path)
    assert r.returncode == 0 and r.stdout == "" and r.stderr == ""  # test path → no warning


def test_usage_check_fail_open_on_no_import(tmp_path: Path):
    event = json.dumps({"tool_input": {"command": "ls -la"}})
    r = _run("sertor-rag-usage-check", event=event, root=tmp_path)
    assert r.returncode == 0 and r.stderr == ""


def test_usage_check_fail_open_on_empty_and_garbage(tmp_path: Path):
    for event in ("", "   ", "not json"):
        r = _run("sertor-rag-usage-check", event=event, root=tmp_path)
        assert r.returncode == 0 and r.stdout == ""


# --- rag-freshness-start (SessionStart, inducement) ----------------------------------------------

def _write_health(root: Path, verdict: str, reason: str = "index area: warn") -> None:
    d = root / ".sertor"
    d.mkdir(parents=True, exist_ok=True)
    (d / ".rag-health.json").write_text(
        json.dumps({"schema": "rag.health/1", "verdict": verdict, "reason": reason}), "utf-8"
    )


def test_freshness_start_induces_on_degraded(tmp_path: Path):
    _write_health(tmp_path, "degraded", reason="index area: warn")
    r = _run("rag-freshness-start", event="{}", root=tmp_path)
    assert r.returncode == 0
    assert "RAG HEALTH DEGRADED (index area: warn)" in r.stdout
    assert "`sertor-rag index .`" in r.stdout


def test_freshness_start_noop_on_healthy(tmp_path: Path):
    _write_health(tmp_path, "healthy")
    r = _run("rag-freshness-start", event="{}", root=tmp_path)
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_freshness_start_noop_on_absent(tmp_path: Path):
    r = _run("rag-freshness-start", event="{}", root=tmp_path)
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_freshness_start_noop_on_malformed(tmp_path: Path):
    d = tmp_path / ".sertor"
    d.mkdir()
    (d / ".rag-health.json").write_text("{ broken", encoding="utf-8")
    r = _run("rag-freshness-start", event="{}", root=tmp_path)
    assert r.returncode == 0 and r.stdout.strip() == ""  # malformed → no-op, non-fatal


# --- version-check-start (SessionStart, update notice) -------------------------------------------

def _write_vc(root: Path, verdict: str, installed="0.1.0", latest="9.9.9", dims=None) -> None:
    d = root / ".sertor"
    d.mkdir(parents=True, exist_ok=True)
    from datetime import datetime

    state = {"schema": "version.check/1", "verdict": verdict, "installed": installed,
             "latest": latest, "checked_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if dims:
        state["dimensions"] = dims
    (d / ".version-check.json").write_text(json.dumps(state), encoding="utf-8")


def test_version_check_start_notice_on_behind(tmp_path: Path):
    _write_vc(tmp_path, "behind", installed="0.1.0", latest="0.2.0", dims={"sertor": "0.1.0"})
    r = _run("version-check-start", event="{}", root=tmp_path)
    assert r.returncode == 0
    assert "SERTOR UPDATE AVAILABLE: installed 0.1.0, latest 0.2.0" in r.stdout
    assert "Installed dimensions: sertor 0.1.0." in r.stdout
    assert "`sertor upgrade`" in r.stdout


def test_version_check_start_noop_when_up_to_date(tmp_path: Path):
    _write_vc(tmp_path, "up-to-date")
    r = _run("version-check-start", event="{}", root=tmp_path)
    assert r.returncode == 0 and r.stdout.strip() == ""


# --- version-check (SessionEnd) — cache-reuse path, no network -----------------------------------

def test_version_check_verdict_behind_from_cache(tmp_path: Path):
    # Fresh cache (latest recorded now) + installed stamp older → verdict `behind`, NO network GET.
    _write_vc(tmp_path, "unknown", latest="0.2.0")  # fresh checked_at → cache reused
    (tmp_path / ".sertor" / ".sertor-version").write_text("0.1.0\n", encoding="utf-8")
    r = _run("version-check", event="{}", root=tmp_path)
    assert r.returncode == 0
    state = json.loads((tmp_path / ".sertor" / ".version-check.json").read_text(encoding="utf-8"))
    assert state["schema"] == "version.check/1"
    assert state["verdict"] == "behind"
    assert state["installed"] == "0.1.0" and state["latest"] == "0.2.0"
    assert state["dimensions"]["sertor"] == "0.1.0"


# --- wiki-session-start (SessionStart) -----------------------------------------------------------

def test_wiki_session_start_claude_directive(tmp_path: Path):
    (tmp_path / "wiki" / "log").mkdir(parents=True)
    (tmp_path / "wiki" / "log" / "2026-07-08.md").write_text("x", encoding="utf-8")
    r = _run("wiki-session-start", event="{}", root=tmp_path, assistant="claude")
    assert r.returncode == 0
    assert r.stdout.startswith("SESSION START")
    assert "wiki/log/2026-07-08.md" in r.stdout  # latest partition computed


def test_wiki_session_start_copilot_json(tmp_path: Path):
    r = _run("wiki-session-start", event="{}", root=tmp_path, assistant="copilot")
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert "additionalContext" in out and out["additionalContext"].startswith("SESSION START")


# --- delegating hooks: no-op / fail-safe paths (full path via dogfood + CI smoke) ----------------

def test_memory_capture_noop_when_disabled(tmp_path: Path, monkeypatch):
    import os as _os

    env = {"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": _os.environ.get("PATH", "")}
    r = subprocess.run([sys.executable, str(_HOOKS / "memory-capture.py")], input="{}",
                       capture_output=True, text=True, env=env, timeout=30)  # SERTOR_MEMORY unset
    assert r.returncode == 0 and r.stdout == ""  # privacy gate → silent no-op


def test_wiki_pending_check_noop_without_config(tmp_path: Path):
    r = _run("wiki-pending-check", event="{}", root=tmp_path)  # no wiki.config.toml
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_rag_freshness_foreground_returns_fast(tmp_path: Path):
    # Foreground spawns a detached worker and returns immediately (never blocks the session close).
    r = _run("rag-freshness", event="{}", root=tmp_path)
    assert r.returncode == 0  # the detached worker runs (and harmlessly fails) in the background


# --- fail-safe / stdin-guard (shared _hooklib) ---------------------------------------------------

def test_hooks_do_not_hang_without_stdin(tmp_path: Path):
    # No piped event: the hook must return promptly (stdin-guard), not block on read.
    for hook in ("sertor-rag-usage-check", "rag-freshness-start", "version-check-start",
                 "wiki-session-start"):
        r = _run(hook, event=None, root=tmp_path)
        assert r.returncode == 0


def test_hooklib_is_identical_in_both_bundles():
    # `_hooklib.py` ships in BOTH the RAG bundle (deposited by `install rag`) and the wiki bundle
    # (`install wiki`), so a wiki-only install still has it. Anti-drift: the two copies must match.
    rag = (_HOOKS / "_hooklib.py").read_text(encoding="utf-8")
    wiki = (_WIKI_HOOKS / "_hooklib.py").read_text(encoding="utf-8")
    assert rag == wiki, "the two `_hooklib.py` copies (rag/ and claude/) have drifted"
