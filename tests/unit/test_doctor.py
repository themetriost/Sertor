"""Unit tests for the pure diagnosis service `services/doctor.py` (074, E12-FEAT-001).

All offline, synthetic inputs, no FS/network (Principio V, F.I.R.S.T.): the decision layer is pure,
so every verdict/rollup/exit-code is exercised with hand-built signals.
"""
from __future__ import annotations

import inspect
from pathlib import Path

from sertor_core.services import doctor as mod
from sertor_core.services.doctor import (
    AreaName,
    AreaReport,
    AreaStatus,
    ProbeStatus,
    Problem,
    ProviderProbe,
    Severity,
    assemble,
    check_config,
    check_mcp,
    check_provider,
    freshness_from_manifest,
)


class _State:
    """Minimal stand-in for `ManifestState`: only `.files` is read by `freshness_from_manifest`."""

    def __init__(self, files: dict[str, tuple[float, str, str]]):
        self.files = files


# --- check_config --------------------------------------------------------------------------------


def test_check_config_pass_no_missing():
    area = check_config([])
    assert area.status is AreaStatus.pass_
    assert area.problems == ()


def test_check_config_fail_one_missing():
    area = check_config(["AZURE_OPENAI_API_KEY"])
    assert area.status is AreaStatus.fail
    assert area.problems[0].code == "env_missing_key"
    assert area.problems[0].severity is Severity.CRITICAL
    assert "AZURE_OPENAI_API_KEY" in area.problems[0].fields


def test_check_config_fail_multiple_missing():
    keys = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_SEARCH_ENDPOINT"]
    area = check_config(keys)
    assert len(area.problems) == 3
    assert all(p.severity is Severity.CRITICAL for p in area.problems)


def test_check_config_fonte_unica():
    # Contract: the function accepts any list; empty → pass (no own key catalogue).
    assert check_config([]).status is AreaStatus.pass_


def test_check_config_fonte_unica_nessuna_lista_propria():
    # The module must not import env-key constants from settings.py nor hardcode a key list:
    # `check_config` derives everything from its `missing` argument (FR-004/A-001/US2-AC3).
    src = inspect.getsource(mod.check_config)
    assert "AZURE_OPENAI" not in src
    assert "AZURE_SEARCH" not in src
    # No import of settings constants at module level.
    assert "from sertor_core.config.settings import" not in inspect.getsource(mod)


# --- check_provider ------------------------------------------------------------------------------


def test_check_provider_pass_complete_no_probe():
    area = check_provider([], None)
    assert area.status is AreaStatus.pass_


def test_check_provider_fail_incomplete():
    area = check_provider(["AZURE_OPENAI_API_KEY"], None)
    assert area.status is AreaStatus.fail
    assert area.problems[0].severity is Severity.CRITICAL


def test_check_provider_warn_unreachable():
    probe = ProviderProbe(ProbeStatus.unreachable, "timeout")
    area = check_provider([], probe)
    assert area.status is AreaStatus.warn
    assert area.problems[0].severity is Severity.WARN
    assert area.problems[0].code == "provider_unreachable"


def test_check_provider_info_skipped():
    area = check_provider([], ProviderProbe(ProbeStatus.skipped, ""))
    assert area.status is AreaStatus.pass_
    assert area.detail["probe"] == "skipped"


def test_check_provider_pass_reachable():
    area = check_provider([], ProviderProbe(ProbeStatus.reachable, ""))
    assert area.status is AreaStatus.pass_
    assert area.detail["probe"] == "reachable"


def test_check_provider_inherits_provider_keys():
    # missing_provider is the provider-keys subset of validate_backend() → provider fail.
    area = check_provider(["AZURE_OPENAI_ENDPOINT"], None)
    assert area.status is AreaStatus.fail
    assert "AZURE_OPENAI_ENDPOINT" in area.problems[0].fields


# --- freshness_from_manifest ---------------------------------------------------------------------


def test_freshness_absent_manifest():
    area = freshness_from_manifest(None, [])
    assert area.status is AreaStatus.fail
    assert area.problems[0].code == "index_absent"
    assert "sertor-rag index ." in area.problems[0].remedy


def test_freshness_fresh_index():
    state = _State({"a.py": (100.0, "h", "v"), "b.md": (200.0, "h", "v")})
    stats = [(Path("a.py"), 100.0), (Path("b.md"), 200.0)]
    area = freshness_from_manifest(state, stats)
    assert area.status is AreaStatus.pass_
    assert area.detail["last_index"] is not None


def test_freshness_stale_index():
    state = _State({"a.py": (100.0, "h", "v")})
    stats = [(Path("a.py"), 150.0)]  # modified after last index
    area = freshness_from_manifest(state, stats)
    assert area.status is AreaStatus.warn
    assert area.problems[0].code == "index_stale"
    assert area.problems[0].remedy


def test_freshness_deleted_file_triggers_stale():
    state = _State({"a.py": (100.0, "h", "v")})
    stats = [(Path("a.py"), 0.0)]  # 0.0 = deleted/unreadable fallback
    area = freshness_from_manifest(state, stats)
    assert area.status is AreaStatus.warn


def test_freshness_no_files_in_manifest():
    state = _State({})
    area = freshness_from_manifest(state, [])
    assert area.status is AreaStatus.pass_


def test_freshness_last_index_in_detail():
    state = _State({"a.py": (100.0, "h", "v")})
    area = freshness_from_manifest(state, [(Path("a.py"), 100.0)])
    val = area.detail["last_index"]
    assert isinstance(val, str)
    assert val.endswith("Z")


def test_freshness_stale_remedy_mentions_reindex():
    state = _State({"a.py": (100.0, "h", "v")})
    area = freshness_from_manifest(state, [(Path("a.py"), 500.0)])
    assert "sertor-rag index ." in area.problems[0].remedy


def test_freshness_no_false_positive_on_unchanged():
    state = _State({"a.py": (100.0, "h", "v")})
    area = freshness_from_manifest(state, [(Path("a.py"), 100.0)])
    assert area.status is AreaStatus.pass_


# --- check_mcp -----------------------------------------------------------------------------------


def test_check_mcp_registered_fresh():
    area = check_mcp(registered=True, index_stale=False)
    assert area.status is AreaStatus.pass_


def test_check_mcp_not_registered():
    area = check_mcp(registered=False, index_stale=False)
    assert area.status is AreaStatus.warn
    assert area.problems[0].code == "mcp_not_registered"
    assert "sertor install rag" in area.problems[0].remedy


def test_check_mcp_stale_after_reindex():
    area = check_mcp(registered=True, index_stale=True)
    assert area.status is AreaStatus.warn
    assert area.problems[0].code == "mcp_stale_after_reindex"


def test_check_mcp_never_critical():
    for reg in (True, False):
        for stale in (True, False):
            area = check_mcp(registered=reg, index_stale=stale)
            assert area.status is not AreaStatus.fail


# --- assemble / HealthReport ---------------------------------------------------------------------


def _pass(name: AreaName) -> AreaReport:
    return AreaReport.of(name, ())


def _critical(name: AreaName) -> AreaReport:
    return AreaReport.of(name, (Problem(Severity.CRITICAL, "x", "m", "r"),))


def _warn(name: AreaName) -> AreaReport:
    return AreaReport.of(name, (Problem(Severity.WARN, "x", "m", "r"),))


def test_assemble_all_pass():
    report = assemble(tuple(_pass(n) for n in AreaName), online=False)
    assert report.overall is AreaStatus.pass_
    assert report.is_healthy() is True
    assert report.exit_code() == 0


def test_assemble_one_critical():
    areas = (_critical(AreaName.config), _pass(AreaName.provider),
             _pass(AreaName.index), _pass(AreaName.mcp))
    report = assemble(areas, online=False)
    assert report.overall is AreaStatus.fail
    assert report.exit_code() == 1


def test_assemble_warn_only():
    areas = (_pass(AreaName.config), _pass(AreaName.provider),
             _pass(AreaName.index), _warn(AreaName.mcp))
    report = assemble(areas, online=False)
    assert report.overall is AreaStatus.warn
    assert report.exit_code() == 0


def test_assemble_order():
    # Pass areas in scrambled order → canonical (config, provider, index, mcp).
    areas = (_pass(AreaName.mcp), _pass(AreaName.index),
             _pass(AreaName.provider), _pass(AreaName.config))
    report = assemble(areas, online=False)
    assert [a.name for a in report.areas] == [
        AreaName.config, AreaName.provider, AreaName.index, AreaName.mcp
    ]


def test_assemble_subset_preserves_order():
    report = assemble((_pass(AreaName.config),), online=False)
    assert [a.name for a in report.areas] == [AreaName.config]


def test_area_status_rollup_critical():
    area = AreaReport.of(
        AreaName.config,
        (Problem(Severity.CRITICAL, "x", "m", "r"), Problem(Severity.WARN, "y", "m", "r")),
    )
    assert area.status is AreaStatus.fail
