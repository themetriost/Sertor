"""Tests for `.mcp.json` merge: creation, preservation, idempotence, malformed (kit ConfigError)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError
from sertor_install_kit.mcp_merge import (
    merge_mcp,
    remove_mcp_server,
    update_mcp_server,
)

ENTRY = {
    "command": "uv",
    "args": ["run", "--directory", ".sertor", "python", "-m", "sertor_mcp.server"],
    "env": {"SERTOR_CORPUS": "myapp"},
}


def test_create(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    outcome, _ = merge_mcp(mcp, ENTRY)
    assert outcome is Outcome.CREATED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert data["mcpServers"]["sertor-rag"]["command"] == "uv"


def test_preserve_other_servers(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"altro": {"command": "x"}}}), encoding="utf-8")
    outcome, _ = merge_mcp(mcp, ENTRY)
    assert outcome is Outcome.MERGED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["mcpServers"] and "sertor-rag" in data["mcpServers"]


def test_idempotent_skip(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    merge_mcp(mcp, ENTRY)
    outcome, _ = merge_mcp(mcp, ENTRY)
    assert outcome is Outcome.SKIPPED


def test_malformed_raises(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        merge_mcp(mcp, ENTRY)


# ---------------------------------------------------------------- feature 044: parametric root_key

def test_default_root_key_is_mcpservers(tmp_path: Path):
    """Retro-compat: absent `root_key` keeps the historical `mcpServers` root."""
    mcp = tmp_path / ".mcp.json"
    merge_mcp(mcp, ENTRY)
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "mcpServers" in data and "sertor-rag" in data["mcpServers"]


# NB (FEAT-012): the VS Code `servers` root-key is no longer reachable from any profile (the VS
# Code target was removed). The `root_key` parameter of `merge_mcp` remains a generic kit primitive,
# so we keep coverage of its parametricity using a neutral, non-VS-Code root key.
def test_parametric_root_key_create(tmp_path: Path):
    """`merge_mcp` honors an arbitrary `root_key` (parametricity of the kit primitive)."""
    mcp = tmp_path / "custom" / "mcp.json"
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="customRoot")
    assert outcome is Outcome.CREATED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "customRoot" in data and data["customRoot"]["sertor-rag"]["command"] == "uv"
    assert "mcpServers" not in data


def test_parametric_root_key_preserves_others(tmp_path: Path):
    mcp = tmp_path / "custom" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text(json.dumps({"customRoot": {"altro": {"command": "x"}}}), encoding="utf-8")
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="customRoot")
    assert outcome is Outcome.MERGED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["customRoot"] and "sertor-rag" in data["customRoot"]


def test_parametric_root_key_idempotent(tmp_path: Path):
    mcp = tmp_path / "custom" / "mcp.json"
    merge_mcp(mcp, ENTRY, root_key="customRoot")
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="customRoot")
    assert outcome is Outcome.SKIPPED


def test_parametric_root_key_malformed_raises(tmp_path: Path):
    mcp = tmp_path / "custom" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{nope", encoding="utf-8")
    with pytest.raises(ConfigError):
        merge_mcp(mcp, ENTRY, root_key="customRoot")


# --- feature 048: remove_mcp_server (T018) ------------------------------------------------------


def test_remove_mcp_server_keeps_others(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(
        json.dumps({"mcpServers": {"altro": {"command": "x"}, "sertor-rag": ENTRY}}),
        encoding="utf-8",
    )
    outcome, _ = remove_mcp_server(mcp)
    assert outcome is Outcome.REMOVED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["mcpServers"]
    assert "sertor-rag" not in data["mcpServers"]


def test_remove_mcp_server_only_server_removes_file(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    merge_mcp(mcp, ENTRY)  # file = {mcpServers: {sertor-rag}}
    outcome, detail = remove_mcp_server(mcp)
    assert outcome is Outcome.REMOVED
    assert detail == "file removed"
    assert not mcp.exists()


def test_remove_mcp_server_absent_skips(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"altro": {"command": "x"}}}), encoding="utf-8")
    outcome, _ = remove_mcp_server(mcp)
    assert outcome is Outcome.SKIPPED


def test_remove_mcp_server_missing_file_skips(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    outcome, _ = remove_mcp_server(mcp)
    assert outcome is Outcome.SKIPPED


def test_remove_mcp_server_parametric_root_key(tmp_path: Path):
    mcp = tmp_path / "custom" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text(
        json.dumps({"customRoot": {"altro": {"command": "x"}, "sertor-rag": ENTRY}}),
        encoding="utf-8",
    )
    outcome, _ = remove_mcp_server(mcp, root_key="customRoot")
    assert outcome is Outcome.REMOVED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["customRoot"] and "sertor-rag" not in data["customRoot"]


# --- E2-FEAT-022: identity by CONTENT, not by presence -------------------------------------------
#
# A `.mcp.json` registering `sertor-rag` with a broken invocation used to be skipped by every
# install AND every upgrade ("server already present"). On node Kaelen that entry carried
# `uv run --directory .sertor`, which moved the working directory so the server resolved an EMPTY
# index inside the runtime: every query returned `[]` — an absence, not an error — for about a
# month, while each upgrade reported success. Install stays non-destructive but now NAMES the
# divergence; `update_mcp_server` is the verb that repairs it.

_BROKEN = {
    "command": "uv",
    "args": ["run", "--directory", ".sertor", "python", "-m", "sertor_mcp.server"],
    "env": {"SERTOR_CORPUS": "myapp"},
}
_SHIPPED = {
    "command": "uv",
    "args": ["run", "--project", ".sertor", "python", "-m", "sertor_mcp.server"],
    "env": {"SERTOR_CORPUS": "myapp"},
}


def _host(tmp_path: Path, entry: dict) -> Path:
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"sertor-rag": entry}}), encoding="utf-8")
    return mcp


def test_install_reports_present_divergent_and_does_not_touch_the_file(tmp_path: Path):
    mcp = _host(tmp_path, _BROKEN)
    before = mcp.read_text(encoding="utf-8")
    outcome, detail = merge_mcp(mcp, _SHIPPED)
    assert outcome is Outcome.PRESENT_DIVERGENT
    assert "differs" in detail and "sertor upgrade rag" in detail
    assert mcp.read_text(encoding="utf-8") == before, "install must stay non-destructive"


def test_install_still_skips_when_the_entry_is_identical(tmp_path: Path):
    outcome, detail = merge_mcp(_host(tmp_path, _SHIPPED), _SHIPPED)
    assert outcome is Outcome.SKIPPED and "already present" in detail


def test_upgrade_rewires_a_divergent_entry_in_place(tmp_path: Path):
    mcp = _host(tmp_path, _BROKEN)
    outcome, detail = update_mcp_server(mcp, _SHIPPED)
    assert outcome is Outcome.UPDATED and "re-wired" in detail
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert data["mcpServers"]["sertor-rag"] == _SHIPPED
    assert "--directory" not in data["mcpServers"]["sertor-rag"]["args"]


def test_upgrade_preserves_other_servers_while_rewiring(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(
        json.dumps({"mcpServers": {"altro": {"command": "x"}, "sertor-rag": _BROKEN}}),
        encoding="utf-8",
    )
    assert update_mcp_server(mcp, _SHIPPED)[0] is Outcome.UPDATED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert data["mcpServers"]["altro"] == {"command": "x"}


def test_upgrade_is_idempotent_on_an_aligned_host(tmp_path: Path):
    outcome, detail = update_mcp_server(_host(tmp_path, _SHIPPED), _SHIPPED)
    assert outcome is Outcome.SKIPPED and "already current" in detail


def test_upgrade_adds_the_server_when_absent(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"altro": {"command": "x"}}}), encoding="utf-8")
    assert update_mcp_server(mcp, _SHIPPED)[0] is Outcome.MERGED


def test_upgrade_creates_the_file_when_absent(tmp_path: Path):
    assert update_mcp_server(tmp_path / ".mcp.json", _SHIPPED)[0] is Outcome.CREATED


def test_upgrade_refuses_a_malformed_file(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        update_mcp_server(mcp, _SHIPPED)


# --- E2-FEAT-022: the host's configuration is NOT ours to overwrite -------------------------------
#
# Reconciling the entry wholesale was the first attempt, and it silently reset `SERTOR_CORPUS` to
# the target directory's name on every upgrade — pointing the server at a collection that does not
# exist, which is the exact failure (a RAG answering nothing) this feature repairs. Found by running
# the real installer on a throwaway host, not by the unit tests: the invocation and the corpus fail
# in opposite directions, so they cannot share one rule.

_SHIPPED_DEFAULT_CORPUS = {
    "command": "uv",
    "args": ["run", "--project", ".sertor", "python", "-m", "sertor_mcp.server"],
    "env": {"SERTOR_CORPUS": "derived-from-dirname"},
}


def test_upgrade_preserves_a_custom_corpus_while_fixing_the_invocation(tmp_path: Path):
    host = dict(_BROKEN)
    host["env"] = {"SERTOR_CORPUS": "miocorpus"}
    mcp = _host(tmp_path, host)

    assert update_mcp_server(mcp, _SHIPPED_DEFAULT_CORPUS)[0] is Outcome.UPDATED
    entry = json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]["sertor-rag"]
    assert entry["args"] == _SHIPPED_DEFAULT_CORPUS["args"], "the invocation IS ours to fix"
    assert entry["env"]["SERTOR_CORPUS"] == "miocorpus", "the corpus is NOT ours to overwrite"


def test_upgrade_is_a_noop_when_only_the_corpus_differs(tmp_path: Path):
    """A host with its own corpus and the right invocation is already correct — do not churn it."""
    host = dict(_SHIPPED_DEFAULT_CORPUS)
    host["env"] = {"SERTOR_CORPUS": "miocorpus"}
    assert update_mcp_server(_host(tmp_path, host), _SHIPPED_DEFAULT_CORPUS)[0] is Outcome.SKIPPED


def test_install_does_not_cry_divergent_over_a_custom_corpus(tmp_path: Path):
    """`PRESENT_DIVERGENT` must mean «the invocation differs», not «you chose your own corpus»."""
    host = dict(_SHIPPED_DEFAULT_CORPUS)
    host["env"] = {"SERTOR_CORPUS": "miocorpus"}
    assert merge_mcp(_host(tmp_path, host), _SHIPPED_DEFAULT_CORPUS)[0] is Outcome.SKIPPED


def test_upgrade_adds_shipped_env_keys_the_host_lacks(tmp_path: Path):
    """Additive per key: a new shipped knob reaches the host, existing values are left alone."""
    host = dict(_SHIPPED_DEFAULT_CORPUS)
    host["env"] = {"SERTOR_CORPUS": "miocorpus"}
    shipped = dict(_SHIPPED_DEFAULT_CORPUS)
    shipped["env"] = {"SERTOR_CORPUS": "derived-from-dirname", "SERTOR_NEW_KNOB": "on"}
    assert update_mcp_server(_host(tmp_path, host), shipped)[0] is Outcome.UPDATED
    env = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"][
        "sertor-rag"
    ]["env"]
    assert env == {"SERTOR_CORPUS": "miocorpus", "SERTOR_NEW_KNOB": "on"}


def test_upgrade_preserves_an_extra_key_the_host_added(tmp_path: Path):
    host = dict(_BROKEN)
    host["timeout"] = 120
    mcp = _host(tmp_path, host)
    update_mcp_server(mcp, _SHIPPED)
    assert json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]["sertor-rag"]["timeout"] == 120
