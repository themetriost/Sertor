"""Tests for the report entities of `sertor configure` (feature 051, T-120).

Anti-leak (T-120-LEAK/-JSON) is the structural guarantee that a known secret never appears in
either render form (FR-013/SC-008). Pure, no I/O.
"""
from __future__ import annotations

import json

import pytest

from sertor_installer.configure_fields import FIELD_CATALOG, FieldStatus
from sertor_installer.configure_report import (
    ConfigProfile,
    ConfigureReport,
    FieldResolution,
    LiveCheckOutcome,
    ValidationOutcome,
)

_ENDPOINT = FIELD_CATALOG["AZURE_OPENAI_ENDPOINT"]
_APIKEY = FIELD_CATALOG["AZURE_OPENAI_API_KEY"]


def _report(*, complete=True, requested=False, ok=None, fields=(), notes=()):
    return ConfigureReport(
        target="/abs/host",
        profile=ConfigProfile("azure", "local"),
        fields=tuple(fields),
        validation=ValidationOutcome(complete, () if complete else ("AZURE_OPENAI_API_KEY",)),
        live_check=LiveCheckOutcome(requested, ok, ""),
        env_path=".sertor/.env",
        notes=tuple(notes),
    )


def test_profile_invalid_backend_raises():
    with pytest.raises(ValueError):
        ConfigProfile("foo", "local")


def test_profile_invalid_store_raises():
    with pytest.raises(ValueError):
        ConfigProfile("azure", "foo")


# --- anti-leak ---------------------------------------------------------------------------------


def test_no_secret_in_render_human():
    res = FieldResolution(_APIKEY, "sk-secret-1234", FieldStatus.SET, "flag")
    report = _report(fields=[res])
    assert "sk-secret-1234" not in report.render_human()


def test_no_secret_in_render_json():
    res = FieldResolution(_APIKEY, "sk-secret-1234", FieldStatus.SET, "flag")
    report = _report(fields=[res])
    assert "sk-secret-1234" not in report.render_json()


def test_secret_display_value_is_masked():
    res = FieldResolution(_APIKEY, "sk-secret-1234", FieldStatus.SET, "flag")
    assert res.display_value == "****1234"


def test_non_secret_display_value_is_clear():
    res = FieldResolution(_ENDPOINT, "https://x.openai.azure.com/", FieldStatus.SET, "flag")
    assert res.display_value == "https://x.openai.azure.com/"


# --- exit code ---------------------------------------------------------------------------------


def test_exit_code_complete_no_check():
    assert _report(complete=True, requested=False).exit_code() == 0


def test_exit_code_missing_fields():
    assert _report(complete=False).exit_code() == 1


def test_exit_code_probe_failed():
    assert _report(complete=True, requested=True, ok=False).exit_code() == 1


def test_exit_code_probe_ok():
    assert _report(complete=True, requested=True, ok=True).exit_code() == 0


def test_exit_code_probe_unavailable():
    # ok=None (honest degradation) → exit decided by static validation only.
    assert _report(complete=True, requested=True, ok=None).exit_code() == 0
    assert _report(complete=False, requested=True, ok=None).exit_code() == 1


# --- render ------------------------------------------------------------------------------------


def test_render_json_structure():
    res = FieldResolution(_ENDPOINT, "https://x/", FieldStatus.SET, "flag")
    payload = json.loads(_report(fields=[res]).render_json())
    assert set(payload) == {
        "target", "profile", "fields", "validation", "live_check", "env_path", "notes",
        "exit_code",
    }
    assert payload["profile"] == {"backend": "azure", "store": "local"}
    assert payload["fields"][0]["name"] == "AZURE_OPENAI_ENDPOINT"
    assert payload["exit_code"] == 0


def test_render_human_contains_profile():
    out = _report().render_human()
    assert "backend=azure" in out
    assert "store=local" in out


def test_render_human_lists_missing():
    out = _report(complete=False).render_human()
    assert "INCOMPLETE" in out
    assert "AZURE_OPENAI_API_KEY" in out


def test_render_human_no_fields_for_empty_profile():
    out = _report(fields=[]).render_human()
    assert "(none required" in out
