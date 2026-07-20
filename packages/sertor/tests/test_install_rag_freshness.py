"""Tests for E10-FEAT-011: deterministic RAG-freshness enforcement via `sertor install rag`.

`install rag` now also deposits the freshness hook (`rag-freshness.py`, SessionEnd: re-index +
doctor + persist) plus a SessionStart signal (`rag-freshness-start.py` on Claude; a static native
prompt on Copilot CLI — W5). Portable (A-09): hooks are Python, run via `uv run --no-project
python`. Routed per-assistant (Claude `.claude/settings.json`, Copilot native
`.github/hooks/sertor-hooks.json`). Additive, isolated from memory-capture/rag-usage; the hook is
non-fatal (exit 0 always) and re-indexes unconditionally (skip delegated to the core, FR-002).
Mirrors the memory-capture hook pattern (FILE + SETTINGS_MERGE), no new ArtifactKind.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import ArtifactKind, LifecycleOp, WriteStrategy
from sertor_install_kit.assistant import AssistantId
from sertor_installer.install_rag import (
    _COPILOT_FRESHNESS_END_WIRING_SENTINEL,
    _COPILOT_FRESHNESS_START_WIRING_SENTINEL,
    _FRESHNESS_HOOK_TARGET,
    _FRESHNESS_START_TARGET,
    build_rag_plan,
    execute_rag_lifecycle,
    execute_rag_plan,
    sertor_owned_paths,
)
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
from sertor_installer.resources import asset_path

_FRESHNESS_HOOK_REL = ".claude/hooks/rag-freshness.py"
_FRESHNESS_START_REL = ".claude/hooks/rag-freshness-start.py"
_FRESHNESS_HOOK_REL_COPILOT = ".github/hooks/rag-freshness.py"
_FRESHNESS_START_REL_COPILOT = ".github/hooks/rag-freshness-start.py"
_SETTINGS_REL = ".claude/settings.json"
_COPILOT_WIRING_REL = ".github/hooks/sertor-hooks.json"


def _profile(target: Path, **opts) -> RagHostProfile:
    return RagHostProfile.from_options(RagInstallOptions(target_root=target, **opts))


def _run(target: Path, runner, assistant=AssistantId.CLAUDE, **opts):
    options = RagInstallOptions(target_root=target, **opts)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(
        profile, with_deps=options.with_deps, mcp_scope=options.mcp_scope, assistant=assistant
    )
    return execute_rag_plan(plan, profile, runner, assistant=assistant), profile


def _norm(rel: str) -> str:
    return rel.replace("\\", "/")


# --- US8-AC1: Claude deposit (script + wiring entries) ----------------------------------------

def test_freshness_hook_deposited_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert _FRESHNESS_HOOK_REL in files
    file_arts = [a for a in plan if a.kind is ArtifactKind.FILE]
    assert all(a.strategy is WriteStrategy.CREATE_IF_ABSENT for a in file_arts)


def test_freshness_start_deposited_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert _FRESHNESS_START_REL in files


def test_freshness_session_end_settings_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    sources = {a.source for a in settings}
    assert "rag/settings.rag-freshness.json" in sources
    end = [a for a in settings if a.source == "rag/settings.rag-freshness.json"]
    assert _norm(end[0].target_rel) == _SETTINGS_REL


def test_freshness_session_start_settings_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    sources = {a.source for a in settings}
    assert "rag/settings.rag-freshness-start.json" in sources


def test_freshness_isolated_from_memory_capture(tmp_path: Path):
    """The plan carries BOTH the memory-capture AND the rag-freshness SessionEnd as DISTINCT
    artifacts — not fused into a single script (FR-016)."""
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert ".claude/hooks/memory-capture.py" in files
    assert _FRESHNESS_HOOK_REL in files
    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    sources = {a.source for a in settings}
    assert "rag/settings.memory-capture.json" in sources
    assert "rag/settings.rag-freshness.json" in sources


def test_freshness_settings_merge_both_events_claude(tmp_path: Path, make_runner):
    """After install, `.claude/settings.json` carries both the SessionEnd and SessionStart
    freshness entries, alongside the pre-existing hooks (additive, FR-016/018)."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    end_cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])]
    assert any("rag-freshness.py" in c for c in end_cmds)
    start_cmds = [
        h["command"] for e in settings["hooks"]["SessionStart"] for h in e.get("hooks", [])
    ]
    assert any("rag-freshness-start.py" in c for c in start_cmds)
    # memory-capture still present (isolation)
    assert any("memory-capture.py" in c for c in end_cmds)


# --- install behaviour: script content / non-fatal --------------------------------------------

def test_freshness_hook_content(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    hook = tmp_path / _FRESHNESS_HOOK_REL
    assert hook.is_file()
    text = hook.read_text(encoding="utf-8")
    assert '"sertor-rag", "index"' in text   # delegates the re-index to the vehicle (list argv)
    assert '"sertor-rag", "doctor"' in text  # health verdict via the vehicle (list argv)
    assert "rag.health/1" in text            # writes the contract schema
    assert "_hooklib.run" in text            # non-fatal fail-safe runner (always exit 0)
    # E10-FEAT-034: `reason` accumulates ALL degraded areas (not just the first), and a failed
    # re-index forces `degraded` — the old `if not reason` first-wins logic must be gone.
    assert "degraded.append(" in text
    assert '"; ".join(' in text
    assert "reindex_failed" in text
    assert "if not reason:" not in text


def test_freshness_hook_non_blocking_design(tmp_path: Path, make_runner):
    """E10-FEAT-016 refinement: the FOREGROUND only RELAUNCHES this same script DETACHED in worker
    mode (`subprocess.Popen` via `_spawn_detached`, `--worker`), so the session close returns
    immediately — doctor AND index run off the critical path. The CLI is invoked via
    `uv run --project <root>/.sertor` (PATH-independent), never bare `uv run sertor-rag`."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    text = (tmp_path / _FRESHNESS_HOOK_REL).read_text(encoding="utf-8")
    # The foreground spawns a detached worker process (cross-OS).
    assert "subprocess.Popen" in text
    assert "_spawn_detached" in text
    assert "--worker" in text                # relaunches itself in worker mode
    # Vehicle invocations use the project-pinned form (PATH-independent, list argv), not bare uv.
    assert '"uv", "run", "--project"' in text
    assert "uv run sertor-rag" not in text   # the old bare form must be gone


def _script_body(text: str) -> str:
    """Return the hook source as-is. In the portable Python hook the positional-search tokens
    (`def _worker`, `if args.worker`, `_spawn_detached(`, `os.replace(`, the list-literal vehicle
    argv) appear ONLY in code, never in the module docstring, so no help-block stripping needed."""
    return text


def test_freshness_foreground_does_not_run_doctor_or_index_synchronously(
    tmp_path: Path, make_runner
):
    """E10-FEAT-016 refinement: the FOREGROUND branch must NOT run doctor + index synchronously —
    it only spawns the worker. The synchronous doctor/index calls live in the WORKER function
    (`_worker`, defined before the `if args.worker` dispatch); the foreground only does the detached
    `_spawn_detached` relaunch (after the dispatch), so they are never executed on the session-close
    path."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    body = _script_body((tmp_path / _FRESHNESS_HOOK_REL).read_text(encoding="utf-8"))
    worker_func = body.index("def _worker(")
    worker_dispatch = body.index("if args.worker")
    # The foreground detached spawn is the CALL to `_spawn_detached` in main() — its argv is built
    # from `sys.executable`, a token unique to that call (the `def _spawn_detached` definition and
    # the argparse `--worker` option both precede the dispatch, so we anchor on the call site).
    spawn_pos = body.index("sys.executable")
    # Worker function defined first, then the dispatch, then the foreground detached spawn.
    assert worker_func < worker_dispatch < spawn_pos
    # The synchronous vehicle calls (uv run, list argv) live inside the worker function, i.e. BEFORE
    # the dispatch — the foreground path (after the dispatch) never calls a vehicle directly.
    first_vehicle = body.index('"uv", "run", "--project"')
    assert worker_func < first_vehicle < worker_dispatch


def test_freshness_worker_reindex_before_doctor_before_state(tmp_path: Path, make_runner):
    """E10-FEAT-034: inside the WORKER the order is re-index (repair) → doctor (REMEASURE) → atomic
    state write, so the persisted verdict reflects health AFTER the repair (not the pre-repair
    measure that made the normal case cry wolf). The never-torn/absent invariant (DA-6) is preserved
    by the ATOMIC write (`os.replace`), not by writing early."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    body = _script_body((tmp_path / _FRESHNESS_HOOK_REL).read_text(encoding="utf-8"))
    index_pos = body.index('"sertor-rag", "index"')     # index vehicle argv (the repair, first)
    doctor_pos = body.index('"sertor-rag", "doctor"')   # doctor vehicle argv (the remeasure)
    state_write_pos = body.index("os.replace(")          # the atomic post-repair state write
    assert index_pos < doctor_pos < state_write_pos


def test_freshness_start_content(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    start = tmp_path / _FRESHNESS_START_REL
    assert start.is_file()
    text = start.read_text(encoding="utf-8")
    assert ".rag-health.json" in text   # reads the persisted state
    assert "_hooklib.run" in text       # non-fatal fail-safe runner (always exit 0)
    # D<->N (FR-014): the start hook INDUCES (mentions the command in the directive) but never
    # EXECUTES the re-index itself — there is no `uv run`/vehicle invocation in the script body.
    assert "uv run" not in text
    assert "sertor-rag index" in text   # present only inside the inducement directive


def test_freshness_hook_no_llm_no_sertor_core(tmp_path: Path, make_runner):
    """Principio XI + D<->N: the scripts never import the library nor invoke an LLM."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    for rel in (_FRESHNESS_HOOK_REL, _FRESHNESS_START_REL):
        text = (tmp_path / rel).read_text(encoding="utf-8").lower()
        assert "import sertor_core" not in text
        assert "openai" not in text and "anthropic" not in text


# --- US8-AC2: Copilot deposit (native format + parity) ----------------------------------------

def test_freshness_hook_deposited_copilot(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert _FRESHNESS_HOOK_REL_COPILOT in files


def test_freshness_start_NOT_deposited_copilot(tmp_path: Path):
    """W5: the Copilot SessionStart is a static prompt — NO `rag-freshness-start.py` script."""
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert _FRESHNESS_START_REL_COPILOT not in files
    assert _FRESHNESS_START_REL not in files


def test_freshness_end_wiring_copilot_native_format(tmp_path: Path, make_runner):
    _run(
        tmp_path, make_runner(), assistant=AssistantId.COPILOT_CLI,
        backend="azure", with_deps=False,
    )
    wiring = json.loads((tmp_path / _COPILOT_WIRING_REL).read_text(encoding="utf-8"))
    assert wiring["version"] == 1                       # native schema (R1/W1)
    assert "SessionEnd" in wiring["hooks"]
    entry = next(
        e for e in wiring["hooks"]["SessionEnd"] if "rag-freshness.py" in e.get("command", "")
    )
    assert entry["type"] == "command"
    assert "timeoutSec" in entry and "timeout" not in entry   # native field (W1)
    assert "shell" not in entry and "statusMessage" not in entry


def test_freshness_start_wiring_copilot_native_prompt(tmp_path: Path, make_runner):
    _run(
        tmp_path, make_runner(), assistant=AssistantId.COPILOT_CLI,
        backend="azure", with_deps=False,
    )
    wiring = json.loads((tmp_path / _COPILOT_WIRING_REL).read_text(encoding="utf-8"))
    assert "SessionStart" in wiring["hooks"]
    entry = next(e for e in wiring["hooks"]["SessionStart"] if e.get("type") == "prompt")
    assert "prompt" in entry and "command" not in entry      # W5: prompt payload, not command
    assert "rag-health.json" in entry["prompt"]
    assert "timeoutSec" in entry


def test_freshness_no_claude_format_on_copilot(tmp_path: Path, make_runner):
    """Parity (FEAT-011/049): no Claude-only fields leak into the Copilot wiring file."""
    _run(
        tmp_path, make_runner(), assistant=AssistantId.COPILOT_CLI,
        backend="azure", with_deps=False,
    )
    raw = (tmp_path / _COPILOT_WIRING_REL).read_text(encoding="utf-8")
    wiring = json.loads(raw)
    for event_entries in wiring["hooks"].values():
        for entry in event_entries:
            assert "shell" not in entry
            assert "statusMessage" not in entry
            assert "timeout" not in entry   # only timeoutSec


def test_copilot_wiring_sentinels_are_generated(tmp_path: Path):
    """The Copilot freshness wiring uses GENERATED sentinel sources, not static Claude assets."""
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    sources = {a.source for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE}
    assert _COPILOT_FRESHNESS_END_WIRING_SENTINEL in sources
    assert _COPILOT_FRESHNESS_START_WIRING_SENTINEL in sources


# --- lifecycle: owned paths / uninstall / upgrade ---------------------------------------------

def test_freshness_owned_files_claude():
    owned = sertor_owned_paths(AssistantId.CLAUDE)
    covered = owned.covered_targets()
    assert _FRESHNESS_HOOK_TARGET in covered
    assert _FRESHNESS_START_TARGET in covered


def test_freshness_owned_files_copilot():
    """W5: Copilot owns only the SessionEnd script, never a SessionStart `.py`."""
    owned = sertor_owned_paths(AssistantId.COPILOT_CLI)
    covered = owned.covered_targets()
    assert _FRESHNESS_HOOK_REL_COPILOT in covered
    assert _FRESHNESS_START_REL_COPILOT not in covered


def test_uninstall_removes_freshness_scripts(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert (tmp_path / _FRESHNESS_HOOK_REL).is_file()
    assert (tmp_path / _FRESHNESS_START_REL).is_file()

    profile = _profile(tmp_path, backend="azure", with_deps=False)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UNINSTALL, assistant=AssistantId.CLAUDE
    )
    assert not (tmp_path / _FRESHNESS_HOOK_REL).exists()
    assert not (tmp_path / _FRESHNESS_START_REL).exists()


def test_uninstall_removes_freshness_settings_preserving_user(tmp_path: Path, make_runner):
    settings_path = tmp_path / _SETTINGS_REL
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(
            {"hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}
        ),
        encoding="utf-8",
    )
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)

    profile = _profile(tmp_path, backend="azure", with_deps=False)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UNINSTALL, assistant=AssistantId.CLAUDE
    )
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    end_cmds = [h["command"] for e in settings["hooks"].get("SessionEnd", []) for h in e["hooks"]]
    assert "echo mine" in end_cmds                             # user hook preserved
    assert not any("rag-freshness.py" in c for c in end_cmds)  # ours removed


def test_upgrade_updates_freshness_script(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    hook = tmp_path / _FRESHNESS_HOOK_REL
    hook.write_text("# stale\n", encoding="utf-8")  # simulate an outdated installed copy

    profile = _profile(tmp_path, backend="azure", with_deps=False)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UPGRADE, assistant=AssistantId.CLAUDE
    )
    refreshed = hook.read_text(encoding="utf-8")
    assert '"sertor-rag", "index"' in refreshed   # upgraded to the bundled body (list argv)


def test_upgrade_delivers_postrepair_order(tmp_path: Path, make_runner):
    """E10-FEAT-034 (REQ-011): a host that UPGRADES receives the post-repair order (re-index BEFORE
    doctor BEFORE state write) — the guard asserts the upgrade OUTCOME, not just the asset form, so
    the fix actually reaches updating hosts (lesson E10-FEAT-032)."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    hook = tmp_path / _FRESHNESS_HOOK_REL
    hook.write_text("# stale, pre-FEAT-034 body\n", encoding="utf-8")

    profile = _profile(tmp_path, backend="azure", with_deps=False)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UPGRADE, assistant=AssistantId.CLAUDE
    )
    body = hook.read_text(encoding="utf-8")
    assert body.index('"sertor-rag", "index"') < body.index('"sertor-rag", "doctor"') < body.index(
        "os.replace("
    )


def test_freshness_install_idempotent(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    before = (tmp_path / _SETTINGS_REL).read_text(encoding="utf-8")
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    end_cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])]
    assert sum("rag-freshness.py" in c for c in end_cmds) == 1
    assert (tmp_path / _SETTINGS_REL).read_text(encoding="utf-8") == before


# --- asset form -------------------------------------------------------------------------------

def test_freshness_assets_present():
    end = Path(str(asset_path("rag/hooks/rag-freshness.py"))).read_text(encoding="utf-8")
    assert "rag.health/1" in end
    start = Path(str(asset_path("rag/hooks/rag-freshness-start.py"))).read_text(encoding="utf-8")
    assert ".rag-health.json" in start


# --- US9 (R-3): bundled <-> dogfood drift for the freshness hooks ------------------------------
#
# The former hardcoded `.ps1` name list here is subsumed by the AUTO-DERIVED guard
# `tests/unit/test_assets_rag_dogfood_sync.py`, which enumerates EVERY byte-copied
# `assets/rag/hooks/` asset (now the portable `.py` hooks, including rag-freshness{,-start} and
# version-check{,-start}) and asserts byte-parity with the dogfood `.claude/hooks/` copies — without
# a hardcoded list to keep in sync. Removed with the A-09 PowerShell→Python port.
