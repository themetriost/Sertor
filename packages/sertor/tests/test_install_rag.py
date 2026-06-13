"""Test dell'orchestrazione `install rag` (T016/T018/T020/T024/T025, M2, L1).

Usano `FakeCommandRunner` (fixture `make_runner`): nessuna rete, nessun `uv` reale.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions


def _run(target: Path, runner, **opts):
    options = RagInstallOptions(target_root=target, **opts)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=options.with_deps, mcp_scope=options.mcp_scope)
    return execute_rag_plan(plan, profile, runner), profile


def _uv_calls(runner) -> list[list[str]]:
    return [cmd for cmd, _ in runner.calls]


# --- US1: un comando, RAG pronto -------------------------------------------------------------

def test_full_install_azure(tmp_path: Path, make_runner):
    runner = make_runner()
    report, _ = _run(tmp_path, runner, backend="azure")
    assert report.exit_code() == 0
    assert (tmp_path / ".sertor" / ".env").is_file()
    assert (tmp_path / ".mcp.json").is_file()
    assert (tmp_path / ".gitignore").is_file()


def test_install_never_indexes(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    # install != run: nessun comando di indicizzazione/ricerca
    assert all("index" not in cmd and "search" not in cmd for cmd in _uv_calls(runner))
    # solo uv init + uv add (init con --name esplicito: `.sertor` non è un package name valido)
    assert any(cmd[:3] == ["uv", "init", "--bare"] for cmd in _uv_calls(runner))
    assert any(cmd[:2] == ["uv", "add"] for cmd in _uv_calls(runner))


def test_uv_add_includes_all_extras_azure(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    add = next(cmd for cmd in _uv_calls(runner) if cmd[:2] == ["uv", "add"])
    assert "sertor-core[azure,mcp,graph,rerank] @ git+" in add[2]


def test_env_excludes_dot_sertor(tmp_path: Path, make_runner):  # L1 / FR-020
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    env = (tmp_path / ".sertor" / ".env").read_text(encoding="utf-8")
    line = next(ln for ln in env.splitlines() if ln.startswith("SERTOR_EXCLUDE_PATTERNS="))
    assert ".sertor" in line


def test_no_wiki_artifacts_created(tmp_path: Path, make_runner):  # L1 / FR-021
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / "wiki").exists()


def test_corpus_in_env_and_mcp(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", corpus="mycorp")
    assert "SERTOR_CORPUS=mycorp" in (tmp_path / ".sertor" / ".env").read_text()
    assert "mycorp" in (tmp_path / ".mcp.json").read_text()


# --- US2: idempotenza e non distruttività ----------------------------------------------------

def test_idempotent_config_only(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    report2, _ = _run(tmp_path, runner, backend="azure", with_deps=False)
    assert report2.exit_code() == 0
    assert report2.created == 0  # tutto già presente
    assert all(o.outcome.value in ("skipped", "merged") for o in report2.outcomes)


def test_deps_skips_init_when_pyproject_exists(tmp_path: Path, make_runner):
    (tmp_path / ".sertor").mkdir()
    (tmp_path / ".sertor" / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    # nessun uv init (già inizializzato), solo uv add
    assert not any(cmd[:2] == ["uv", "init"] for cmd in _uv_calls(runner))
    assert any(cmd[:2] == ["uv", "add"] for cmd in _uv_calls(runner))


def test_uv_missing_failfast_no_sertor_dir(tmp_path: Path, make_runner):  # T020 / REQ-214
    runner = make_runner(available=False)
    report, _ = _run(tmp_path, runner, backend="azure")
    assert report.exit_code() == 1
    assert report.failed_step == ".sertor"
    assert not (tmp_path / ".sertor").exists()  # nessuno stato a metà
    assert not (tmp_path / ".mcp.json").exists()  # step successivi non eseguiti


def test_uv_add_failure_failfast(tmp_path: Path, make_runner):  # T020 / REQ-215
    runner = make_runner(fail_on="add")
    report, _ = _run(tmp_path, runner, backend="azure")
    assert report.exit_code() == 1
    assert report.failed_step == ".sertor"
    assert not (tmp_path / ".sertor" / ".env").exists()  # no rollback, ma step dopo non eseguiti


# --- US4: backend locale e flag --------------------------------------------------------------

def test_backend_local_env_and_extras(tmp_path: Path, make_runner):  # SC-006
    runner = make_runner()
    _run(tmp_path, runner, backend="local")
    env = (tmp_path / ".sertor" / ".env").read_text(encoding="utf-8")
    assert "RAG_BACKEND=local" in env and "AZURE_OPENAI" not in env
    add = next(cmd for cmd in _uv_calls(runner) if cmd[:2] == ["uv", "add"])
    assert "sertor-core[mcp,graph,rerank] @ git+" in add[2]  # niente azure


def test_optout_extras(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", include_graph=False, include_rerank=False)
    add = next(cmd for cmd in _uv_calls(runner) if cmd[:2] == ["uv", "add"])
    assert "sertor-core[azure,mcp] @ git+" in add[2]


def test_no_deps_skips_uv(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    assert runner.calls == []  # nessun comando uv
    assert (tmp_path / ".sertor" / ".env").is_file()  # ma lo scaffold c'è
    assert (tmp_path / ".mcp.json").is_file()


# --- feature 016 (FR-001/REQ-301): runtime confinato in .sertor/ ----------------------------

def test_rag_plan_no_runtime_file_in_root(tmp_path: Path):
    """FR-001: nessun artefatto del piano RAG in radice oltre `.mcp.json` e `.gitignore`.

    Guardia anti-regressione: un nuovo ArtifactKind che sbaglia `target_rel` (file di runtime in
    radice invece che sotto `.sertor/`) fa fallire questo test.
    """
    profile = RagHostProfile.from_options(RagInstallOptions(target_root=tmp_path, backend="azure"))
    allowed_root = {".mcp.json", ".gitignore"}
    for art in build_rag_plan(profile, with_deps=True):
        rel = art.target_rel.replace("\\", "/")
        top = rel.split("/", 1)[0]
        assert top == ".sertor" or rel in allowed_root, (
            f"artefatto in radice non consentito: {rel}"
        )


# --- US3 (feature 016): --mcp-scope project|local --------------------------------------------

def _calls(runner) -> list[list[str]]:
    return [cmd for cmd, _ in runner.calls]


def test_mcp_scope_project_writes_mcp_json(tmp_path: Path, make_runner):  # FR-004
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False, mcp_scope="project")
    assert (tmp_path / ".mcp.json").is_file()
    assert not any("claude" in cmd for cmd in _calls(runner))  # nessuna CLI client in project


def test_mcp_scope_local_registers_no_repo_file(tmp_path: Path, make_runner):  # FR-004/SC-003
    runner = make_runner()
    report, _ = _run(tmp_path, runner, backend="azure", with_deps=False, mcp_scope="local")
    assert report.exit_code() == 0
    assert not (tmp_path / ".mcp.json").exists()  # niente file nel repo
    assert any(cmd[:3] == ["claude", "mcp", "add-json"] for cmd in _calls(runner))


def test_mcp_scope_local_claude_missing_failfast(tmp_path: Path, make_runner):  # FR-005/SC-005
    runner = make_runner(claude_available=False)
    report, _ = _run(tmp_path, runner, backend="azure", with_deps=False, mcp_scope="local")
    assert report.exit_code() == 1
    assert report.failed_step == "(mcp: client registry)"
    assert not (tmp_path / ".mcp.json").exists()  # nessun file scritto silenziosamente
    assert not any("add-json" in cmd for cmd in _calls(runner))  # add non tentato


def test_mcp_scope_local_idempotent_skip(tmp_path: Path, make_runner):  # SC-006
    runner = make_runner(claude_has_server=True)
    report, _ = _run(tmp_path, runner, backend="azure", with_deps=False, mcp_scope="local")
    assert report.exit_code() == 0
    assert any(cmd[:3] == ["claude", "mcp", "get"] for cmd in _calls(runner))
    assert not any("add-json" in cmd for cmd in _calls(runner))  # già registrato → niente add


def test_invalid_mcp_scope_rejected(tmp_path: Path):
    with pytest.raises(ConfigError):
        RagInstallOptions(target_root=tmp_path, mcp_scope="bogus")


# --- M2 (SC-007): host non-Python NON toccato -----------------------------------------------

def test_non_python_host_sources_untouched(tmp_path: Path, make_runner):
    sln = tmp_path / "App.sln"
    csproj = tmp_path / "Foo.csproj"
    sln.write_text("Microsoft Visual Studio Solution File\n", encoding="utf-8")
    csproj.write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>\n", encoding="utf-8")
    sln_before, csproj_before = sln.read_text(), csproj.read_text()

    runner = make_runner()
    report, _ = _run(tmp_path, runner, backend="azure")

    assert report.exit_code() == 0
    assert sln.read_text() == sln_before  # sorgenti .NET immutati
    assert csproj.read_text() == csproj_before
    # le novità stanno solo in .sertor/ + .mcp.json/.gitignore in radice
    assert (tmp_path / ".sertor").is_dir()
    assert (tmp_path / ".mcp.json").is_file()
