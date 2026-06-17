"""Suite di validità-schema offline degli hook Copilot (FEAT-011, US7 / gruppo G / SC-007).

Per OGNI difetto rilevato dall'audit (version mancante, struttura annidata, campi Claude-only
`shell`/`statusMessage`, `timeout` invece di `timeoutSec`) un test che FALLISCE se reintrodotto.
Tutto OFFLINE: stdlib `json`, costruzione dei piani su `tmp_path`, nessun client Copilot, nessuna
rete (FR-026). Il caso d'oro è verificato sui file REALI prodotti dai due piani (wiki + rag).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_install_kit.assistant import AssistantId
from sertor_install_kit.surfaces import HookEntrySpec, render_copilot_hooks
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
from sertor_installer.install_wiki import build_install_plan, execute_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

_CLAUDE_ONLY_FIELDS = ("shell", "statusMessage", "timeout")


def assert_valid_copilot_hook_file(data: dict) -> None:
    """Asserts the Copilot hook wiring schema (contract `copilot-hook-schema.md` R1..R4).

    Reused by the real-plan tests and the anti-pattern tests: a single source of truth for "what a
    valid Copilot hook file looks like".
    """
    assert data.get("version") == 1, "R1: top-level version:1 missing"          # R1
    assert isinstance(data.get("hooks"), dict), "hooks must be an object"
    for event, entries in data["hooks"].items():
        assert isinstance(entries, list), f"{event}: entries must be a flat list"  # R2
        for entry in entries:
            assert "hooks" not in entry, f"{event}: nested hooks[] (Claude shape)"  # R2
            for bad in _CLAUDE_ONLY_FIELDS:
                assert bad not in entry, f"{event}: Claude-only field '{bad}'"      # R3/R4
            assert "timeoutSec" in entry, f"{event}: timeoutSec missing"            # R4
            # payload key follows the type: `prompt` for a prompt-hook, `command` otherwise
            assert "type" in entry
            payload_key = "prompt" if entry.get("type") == "prompt" else "command"
            assert payload_key in entry, f"{event}: payload field '{payload_key}' missing"


# --- the real plans produce valid files -------------------------------------------------------


def _wiki_wiring(tmp_path: Path, assistant: AssistantId) -> dict:
    profile = build_host_profile(tmp_path)
    execute_plan(build_install_plan(assistant), profile, assistant)
    return json.loads(
        (tmp_path / ".github/hooks/sertor-hooks.json").read_text(encoding="utf-8")
    )


def _rag_wiring(tmp_path: Path, make_runner, assistant: AssistantId) -> dict:
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=assistant)
    execute_rag_plan(plan, profile, make_runner(), assistant)
    return json.loads(
        (tmp_path / ".github/hooks/sertor-hooks.json").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("assistant", [AssistantId.COPILOT_CLI])
def test_real_wiki_wiring_is_schema_valid(tmp_path: Path, assistant: AssistantId):
    assert_valid_copilot_hook_file(_wiki_wiring(tmp_path, assistant))


@pytest.mark.parametrize("assistant", [AssistantId.COPILOT_CLI])
def test_real_rag_wiring_is_schema_valid(tmp_path: Path, make_runner, assistant: AssistantId):
    assert_valid_copilot_hook_file(_rag_wiring(tmp_path, make_runner, assistant))


# --- anti-pattern: each audit defect reintroduced → the validator fails (SC-007 scenario 1) ---


def _valid_sample() -> dict:
    return render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)])


def test_anti_pattern_missing_version_fails():
    broken = _valid_sample()
    del broken["version"]
    with pytest.raises(AssertionError):
        assert_valid_copilot_hook_file(broken)


def test_anti_pattern_nested_hooks_fails():
    broken = _valid_sample()
    broken["hooks"]["Stop"][0]["hooks"] = [{"command": "x"}]
    with pytest.raises(AssertionError):
        assert_valid_copilot_hook_file(broken)


def test_anti_pattern_shell_field_fails():
    broken = _valid_sample()
    broken["hooks"]["Stop"][0]["shell"] = "powershell"
    with pytest.raises(AssertionError):
        assert_valid_copilot_hook_file(broken)


def test_anti_pattern_status_message_fails():
    broken = _valid_sample()
    broken["hooks"]["Stop"][0]["statusMessage"] = "checking"
    with pytest.raises(AssertionError):
        assert_valid_copilot_hook_file(broken)


def test_anti_pattern_timeout_instead_of_timeoutsec_fails():
    broken = _valid_sample()
    broken["hooks"]["Stop"][0]["timeout"] = 10  # Claude name (and keep timeoutSec to isolate R3/R4)
    with pytest.raises(AssertionError):
        assert_valid_copilot_hook_file(broken)
