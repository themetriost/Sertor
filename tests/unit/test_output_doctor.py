"""Test the doctor output formatter `format_health_report` (074, F03/US6): human + JSON + scrub.

Pure: every case builds a synthetic `HealthReport`, no I/O. Verifies the stable schema
`doctor.report/1`, human/JSON informational equivalence, and that secrets are scrubbed in both.
"""
from __future__ import annotations

import json

from sertor_core.cli import output
from sertor_core.services.doctor import (
    AreaName,
    AreaReport,
    Problem,
    Severity,
    assemble,
)


def _healthy() -> object:
    areas = (
        AreaReport.of(AreaName.config, (), {"provider": "glove", "store": "local"}),
        AreaReport.of(AreaName.provider, (), {"probe": "skipped"}),
        AreaReport.of(AreaName.index, (), {"last_index": "2026-06-23T14:02:11Z"}),
        AreaReport.of(AreaName.mcp, (), {"registered": True}),
    )
    return assemble(areas, online=False)


def _critical(message: str = "missing AZURE_OPENAI_API_KEY") -> object:
    areas = (
        AreaReport.of(
            AreaName.config,
            (Problem(Severity.CRITICAL, "env_missing_key", message,
                     "set it in .sertor/.env", ("AZURE_OPENAI_API_KEY",)),),
        ),
        AreaReport.of(AreaName.provider, ()),
        AreaReport.of(AreaName.index, ()),
        AreaReport.of(AreaName.mcp, ()),
    )
    return assemble(areas, online=False)


# --- human ---------------------------------------------------------------------------------------


def test_format_health_report_human_all_pass():
    out = output.format_health_report(_healthy())
    assert "doctor: PASS" in out
    assert out.count("pass") >= 4


def test_format_health_report_human_critical():
    out = output.format_health_report(_critical())
    assert "FAIL" in out
    assert "AZURE_OPENAI_API_KEY" in out
    assert "set it in .sertor/.env" in out


# --- JSON schema ---------------------------------------------------------------------------------


def test_format_health_report_json_schema():
    out = json.loads(output.format_health_report(_healthy(), json_out=True))
    assert out["schema"] == "doctor.report/1"
    assert out["overall"] == "pass"
    assert out["online"] is False
    assert out["exit_code"] == 0
    assert len(out["areas"]) == 4


def test_json_schema_stable_keys():
    out = json.loads(output.format_health_report(_critical(), json_out=True))
    assert set(out.keys()) == {"schema", "overall", "online", "exit_code", "areas"}


def test_json_areas_always_four_in_order():
    out = json.loads(output.format_health_report(_healthy(), json_out=True))
    assert [a["name"] for a in out["areas"]] == ["config", "provider", "index", "mcp"]


def test_json_exit_code_redundant_consistent():
    report = _critical()
    out = json.loads(output.format_health_report(report, json_out=True))
    assert out["exit_code"] == report.exit_code() == 1


# --- scrub ---------------------------------------------------------------------------------------


def test_format_health_report_json_scrubbed():
    report = _critical(message="leaked sk-abcdefghij in the config")
    out = json.loads(output.format_health_report(report, json_out=True))
    msg = out["areas"][0]["problems"][0]["message"]
    assert "sk-abcdefghij" not in msg
    assert "[REDACTED]" in msg


def test_format_health_report_human_scrubbed():
    report = _critical(message="leaked sk-abcdefghij in the config")
    out = output.format_health_report(report)
    assert "sk-abcdefghij" not in out


# --- equivalence ---------------------------------------------------------------------------------


def test_format_health_report_equivalence():
    report = _critical()
    human = output.format_health_report(report)
    data = json.loads(output.format_health_report(report, json_out=True))
    # Same areas, same problem codes/messages reflected in both renderings.
    assert data["overall"] == "fail"
    assert "FAIL" in human
    code_msg = data["areas"][0]["problems"][0]["message"]
    assert code_msg in human
