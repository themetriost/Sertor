"""Test the `sertor-rag doctor` handler end-to-end with the core mocked (074, US1..US7).

Every composition helper imported by `cli/__main__` is monkeypatched (no FS, no network, no server
started). The pure decision/format is exercised through the real handler so the exit-code gate,
`--online` opt-in, `--area` restriction, the observability event and secret redaction are covered.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.services.doctor import ProbeStatus, ProviderProbe


class _State:
    def __init__(self, files):
        self.files = files


_FRESH = _State({"a.py": (100.0, "h", "v")})


@pytest.fixture
def wired(monkeypatch):
    """Wire the handler to a healthy installation by default; each test overrides as needed."""
    settings = Settings(corpus="default", embed_provider="hash", store_backend="local")
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": settings))
    monkeypatch.setattr(cli, "enable_observability", lambda s: None)
    # default-healthy signals
    monkeypatch.setattr(Settings, "validate_backend", lambda self: [])
    monkeypatch.setattr(cli, "load_manifest_state", lambda s: _FRESH)
    monkeypatch.setattr(cli, "current_source_stats", lambda st, root: [])
    monkeypatch.setattr(cli, "read_mcp_registration", lambda root: True)
    monkeypatch.setattr(
        cli, "build_provider_probe",
        lambda s: ProviderProbe(ProbeStatus.reachable, ""),
    )
    return monkeypatch, settings


def _run(argv):
    return cli.main(argv)


# --- US1: quadro in un comando -------------------------------------------------------------------


def test_cmd_doctor_all_pass_exit_zero(wired, capsys):
    code = _run(["doctor"])
    out = capsys.readouterr().out
    assert "doctor: PASS" in out
    assert code == 0
    # the four areas reported (SC-001)
    for name in ("config", "provider", "index", "mcp"):
        assert name in out


def test_cmd_doctor_critical_exit_one(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(Settings, "validate_backend", lambda self: ["AZURE_OPENAI_API_KEY"])
    code = _run(["doctor"])
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert code == 1


def test_cmd_doctor_warn_exit_zero(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(cli, "read_mcp_registration", lambda root: False)  # mcp warn only
    code = _run(["doctor"])
    capsys.readouterr()
    assert code == 0


def test_cmd_doctor_json_flag(wired, capsys):
    code = _run(["doctor", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    obj = json.loads(out)
    assert obj["schema"] == "doctor.report/1"
    assert len(obj["areas"]) == 4


# --- US4: provider probe opt-in ------------------------------------------------------------------


def test_cmd_doctor_online_triggers_probe(wired):
    monkeypatch, _ = wired
    calls = {"n": 0}

    def _probe(s):
        calls["n"] += 1
        return ProviderProbe(ProbeStatus.reachable, "")

    monkeypatch.setattr(cli, "build_provider_probe", _probe)
    _run(["doctor", "--online"])
    assert calls["n"] == 1


def test_cmd_doctor_no_online_no_probe(wired):
    monkeypatch, _ = wired

    def _probe(s):
        raise AssertionError("probe must not run without --online")

    monkeypatch.setattr(cli, "build_provider_probe", _probe)
    code = _run(["doctor"])
    assert code == 0


def test_cmd_doctor_no_online_flag_probe_skipped(wired, capsys):
    _run(["doctor", "--json"])
    obj = json.loads(capsys.readouterr().out)
    provider = next(a for a in obj["areas"] if a["name"] == "provider")
    assert provider["detail"]["probe"] == "skipped"


def test_cmd_doctor_online_probe_unreachable_warn(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(
        cli, "build_provider_probe",
        lambda s: ProviderProbe(ProbeStatus.unreachable, "timeout"),
    )
    code = _run(["doctor", "--online", "--json"])
    obj = json.loads(capsys.readouterr().out)
    provider = next(a for a in obj["areas"] if a["name"] == "provider")
    assert provider["status"] == "warn"
    assert code == 0  # config complete → unreachable is warn, not fail


def test_cmd_doctor_online_probe_reachable_pass(wired, capsys):
    code = _run(["doctor", "--online", "--json"])
    obj = json.loads(capsys.readouterr().out)
    provider = next(a for a in obj["areas"] if a["name"] == "provider")
    assert provider["status"] == "pass"
    assert code == 0


# --- US5: MCP registration -----------------------------------------------------------------------


def test_cmd_doctor_mcp_not_registered_warn(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(cli, "read_mcp_registration", lambda root: False)
    _run(["doctor", "--json"])
    obj = json.loads(capsys.readouterr().out)
    mcp = next(a for a in obj["areas"] if a["name"] == "mcp")
    assert mcp["status"] == "warn"
    assert "sertor install rag" in mcp["problems"][0]["remedy"]


def test_cmd_doctor_mcp_registered_pass(wired, capsys):
    _run(["doctor", "--json"])
    obj = json.loads(capsys.readouterr().out)
    mcp = next(a for a in obj["areas"] if a["name"] == "mcp")
    assert mcp["status"] == "pass"


def test_cmd_doctor_mcp_stale_after_reindex_warn(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(
        cli, "current_source_stats", lambda st, root: [(Path("a.py"), 999.0)]
    )
    _run(["doctor", "--json"])
    obj = json.loads(capsys.readouterr().out)
    mcp = next(a for a in obj["areas"] if a["name"] == "mcp")
    assert mcp["status"] == "warn"
    assert mcp["problems"][0]["code"] == "mcp_stale_after_reindex"


def test_cmd_doctor_mcp_never_fail(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(cli, "read_mcp_registration", lambda root: False)
    _run(["doctor", "--json"])
    obj = json.loads(capsys.readouterr().out)
    mcp = next(a for a in obj["areas"] if a["name"] == "mcp")
    assert mcp["status"] != "fail"


# --- US2: config area reflects validate_backend() ------------------------------------------------


def test_cmd_doctor_config_area_reflects_validate_backend(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(
        Settings, "validate_backend",
        lambda self: ["AZURE_OPENAI_API_KEY", "AZURE_SEARCH_ENDPOINT"],
    )
    code = _run(["doctor", "--json"])
    obj = json.loads(capsys.readouterr().out)
    config = next(a for a in obj["areas"] if a["name"] == "config")
    assert config["status"] == "fail"
    fields = {f for p in config["problems"] for f in p["fields"]}
    assert {"AZURE_OPENAI_API_KEY", "AZURE_SEARCH_ENDPOINT"} <= fields
    assert code == 1


def test_cmd_doctor_local_provider_no_missing_keys(wired, capsys):
    # validate_backend()=[] (glove/hash local) → config pass.
    _run(["doctor", "--json"])
    obj = json.loads(capsys.readouterr().out)
    config = next(a for a in obj["areas"] if a["name"] == "config")
    assert config["status"] == "pass"


# --- US1: --area restriction ---------------------------------------------------------------------


def test_cmd_doctor_area_config_only(wired, capsys):
    monkeypatch, _ = wired
    called = {"mcp": 0, "stats": 0}
    monkeypatch.setattr(cli, "read_mcp_registration",
                        lambda root: called.__setitem__("mcp", called["mcp"] + 1) or True)
    monkeypatch.setattr(cli, "current_source_stats",
                        lambda st, root: called.__setitem__("stats", called["stats"] + 1) or [])
    _run(["doctor", "--area", "config", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert [a["name"] for a in obj["areas"]] == ["config"]
    assert called == {"mcp": 0, "stats": 0}


# --- US6/US1: exit gate + observability + redaction ----------------------------------------------


def test_exit_code_gate_critical(wired):
    monkeypatch, _ = wired
    monkeypatch.setattr(cli, "load_manifest_state", lambda s: None)  # index absent → critical
    assert _run(["doctor"]) == 1


def test_exit_code_gate_warn_zero(wired):
    monkeypatch, _ = wired
    monkeypatch.setattr(cli, "read_mcp_registration", lambda root: False)
    assert _run(["doctor"]) == 0


def test_json_and_human_equivalent(wired, capsys):
    code1 = _run(["doctor"])
    human = capsys.readouterr().out
    code2 = _run(["doctor", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code1 == code2 == 0
    assert data["overall"] == "pass"
    assert "doctor: PASS" in human


def test_secret_redacted_in_json(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(
        cli, "build_provider_probe",
        lambda s: ProviderProbe(ProbeStatus.unreachable, "auth failed sk-secretkey1234"),
    )
    _run(["doctor", "--online", "--json"])
    out = capsys.readouterr().out
    assert "sk-secretkey1234" not in out


def test_secret_redacted_in_human(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(
        cli, "build_provider_probe",
        lambda s: ProviderProbe(ProbeStatus.unreachable, "auth failed sk-secretkey1234"),
    )
    _run(["doctor", "--online"])
    out = capsys.readouterr().out
    assert "sk-secretkey1234" not in out


def test_cmd_doctor_emits_observability_event(wired, monkeypatch):
    events = []
    monkeypatch.setattr(cli, "log_event",
                        lambda level, op, **fields: events.append((op, fields)))
    _run(["doctor"])
    doctor_events = [e for e in events if e[0] == "doctor"]
    assert len(doctor_events) == 1
    fields = doctor_events[0][1]
    assert set(fields) == {"overall", "online", "n_fail", "n_warn", "n_pass", "areas"}
    # closed-cardinality labels, no free text / secret / path
    assert "=" in fields["areas"]


def test_cmd_doctor_no_secret_in_output(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(Settings, "validate_backend", lambda self: ["AZURE_OPENAI_API_KEY"])
    _run(["doctor"])
    human = capsys.readouterr().out
    _run(["doctor", "--json"])
    js = capsys.readouterr().out
    # key NAME is allowed (it's not a value); but no secret-shaped span
    assert "sk-" not in human and "sk-" not in js


# --- US7: offline-safe by default ----------------------------------------------------------------


def test_offline_no_flag_static_checks_complete(wired, capsys):
    monkeypatch, _ = wired

    def _probe(s):
        raise AssertionError("no probe without --online")

    monkeypatch.setattr(cli, "build_provider_probe", _probe)
    _run(["doctor", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert len(obj["areas"]) == 4


def test_offline_with_flag_probe_honest_degradation(wired, capsys):
    monkeypatch, _ = wired
    monkeypatch.setattr(
        cli, "build_provider_probe",
        lambda s: ProviderProbe(ProbeStatus.unreachable, "OSError: unreachable"),
    )
    code = _run(["doctor", "--online", "--json"])
    obj = json.loads(capsys.readouterr().out)
    provider = next(a for a in obj["areas"] if a["name"] == "provider")
    assert provider["detail"]["probe"] == "unreachable"
    assert code == 0  # not critical


def test_cmd_doctor_read_only(wired):
    # The handler never calls index/upsert factories — only read helpers are wired. Running it
    # twice yields the same exit code with no state change (idempotent, read-only).
    assert _run(["doctor"]) == _run(["doctor"]) == 0
