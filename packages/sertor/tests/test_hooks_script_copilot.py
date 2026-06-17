"""Output dei hook script per evento/assistente (FEAT-011, US2 / gruppo G / SC-002, SC-008).

Invoca i due script `.ps1` con `pwsh` (saltato se assente — offline-safe) e verifica il contratto
`hook-output-contract.md`: output NATIVO per assistente, mai dual-field, preToolUse fail-open su
Copilot. I percorsi degli script sono gli asset reali del pacchetto.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from sertor_installer.resources import asset_path

_PWSH = shutil.which("pwsh") or shutil.which("powershell")
pytestmark = pytest.mark.skipif(_PWSH is None, reason="PowerShell not available")

_WIKI_SCRIPT = asset_path("claude/hooks/wiki-pending-check.ps1")
_SESSION_SCRIPT = asset_path("claude/hooks/wiki-session-start.ps1")
_RAG_SCRIPT = asset_path("rag/hooks/sertor-rag-usage-check.ps1")


def _run(script: Path, args: list[str], stdin: str = "", cwd: Path | None = None):
    """Runs a hook script; returns (returncode, stdout, stderr). Empty cwd → a temp with no wiki."""
    proc = subprocess.run(
        [_PWSH, "-NoProfile", "-File", str(script), *args],
        input=stdin, capture_output=True, text=True, cwd=str(cwd) if cwd else None,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _seed_pending_wiki(root: Path) -> None:
    """Creates a host where `sertor-wiki-tools scan` would report pending work is not required:
    these tests focus on the OUTPUT SHAPE, so we drive the script via its no-config exit-0 path or
    via a minimal config. Here we simply ensure no config → the script exits 0 with no output, which
    is the common branch; the SHAPE assertions that need a message use the session-start script
    (which always emits) instead."""
    # intentionally no wiki config: pending-check exits 0 silently (offline-safe)


# --- wiki-session-start.ps1: always emits a directive (SC-003 / O4 / O6) ----------------------


def test_session_start_claude_emits_plain_directive(tmp_path: Path):
    rc, out, _ = _run(_SESSION_SCRIPT, ["-Assistant", "claude"], cwd=tmp_path)
    assert rc == 0
    assert out.strip()                       # a directive on stdout
    # claude branch is NOT JSON additionalContext
    assert "additionalContext" not in out


# NB (FEAT-012): the VS Code SessionStart `additionalContext` mechanism (`wiki-session-start.ps1`
# `-Assistant copilot`) is no longer wired by any install plan — the Copilot CLI uses a native
# `type:"prompt"` hook instead. The script asset is kept only for the Claude branch (above).


# --- wiki-pending-check.ps1: exit 0, native per event (O3 / O5 / O6) ---------------------------


def test_pending_check_claude_exits_zero(tmp_path: Path):
    rc, out, _ = _run(_WIKI_SCRIPT, ["-Mode", "Stop", "-Assistant", "claude"], cwd=tmp_path)
    assert rc == 0
    # no host config → no output; the shape (systemMessage, never decision) is covered by the
    # source-level test below for the case where a message is produced.


def test_pending_check_copilot_session_end_exits_zero(tmp_path: Path):
    rc, out, _ = _run(
        _WIKI_SCRIPT, ["-Mode", "SessionEnd", "-Assistant", "copilot"], cwd=tmp_path
    )
    assert rc == 0
    # sessionEnd on copilot must never write a JSON payload Copilot would consume on stdout (O5)
    assert out.strip() == "" or "systemMessage" not in out


# --- sertor-rag-usage-check.ps1: fail-open on Copilot, exit 0 even on malformed stdin (O2) -----


def test_rag_usage_copilot_malformed_stdin_exits_zero(tmp_path: Path):
    rc, out, _ = _run(_RAG_SCRIPT, ["-Assistant", "copilot"], stdin="{ not json", cwd=tmp_path)
    assert rc == 0                            # fail-open: never blocks
    assert "deny" not in out                  # no payload Copilot reads as decision:"deny"


def test_rag_usage_copilot_empty_stdin_exits_zero(tmp_path: Path):
    rc, out, _ = _run(_RAG_SCRIPT, ["-Assistant", "copilot"], stdin="", cwd=tmp_path)
    assert rc == 0
    assert out.strip() == ""


# --- source-level no-dual-field guard (offline, no pwsh needed for the shape) -----------------


def test_no_dual_field_in_pending_check_source():
    """SC-008: the script never emits both `systemMessage` and `decision`/`reason` in one branch."""
    src = _WIKI_SCRIPT.read_text(encoding="utf-8")
    # the copilot Stop branch uses decision/reason; the claude branch uses systemMessage. They are
    # mutually exclusive branches — assert no single line carries both Claude and Copilot fields.
    for line in src.splitlines():
        has_claude = "systemMessage" in line
        has_copilot = "decision" in line or "additionalContext" in line
        assert not (has_claude and has_copilot), f"dual-field line: {line.strip()}"
