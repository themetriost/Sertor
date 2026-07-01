"""Tests for `install rag` orchestration (T016/T018/T020/T024/T025, M2, L1).

Use `FakeCommandRunner` (fixture `make_runner`): no network, no real `uv`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_install_kit.artifacts import LifecycleOp
from sertor_install_kit.assistant import AssistantId
from sertor_installer.install_rag import (
    build_rag_plan,
    execute_rag_lifecycle,
    execute_rag_plan,
)
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions


def _run(target: Path, runner, *, assistant: AssistantId = AssistantId.CLAUDE, **opts):
    options = RagInstallOptions(target_root=target, **opts)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(
        profile, with_deps=options.with_deps, mcp_scope=options.mcp_scope, assistant=assistant
    )
    return execute_rag_plan(plan, profile, runner, assistant=assistant), profile


def _uv_calls(runner) -> list[list[str]]:
    return [cmd for cmd, _ in runner.calls]


# --- US1: one command, RAG ready -------------------------------------------------------------

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
    # install != run: no indexing/search commands
    assert all("index" not in cmd and "search" not in cmd for cmd in _uv_calls(runner))
    # only uv init + uv add (init with explicit --name: `.sertor` is not a valid package name)
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


def test_no_wiki_artifacts_created(tmp_path: Path, make_runner):  # L1 / FR-021 / E12 (R-3)
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    # `install rag` deposits the RAG-usage hook + eval/usability skills + the concierge agent under
    # `.claude/` but NEVER the wiki scaffold (the wiki-author skill, the `/wiki` command, the wiki
    # structure/config, the `wiki-curator` agent). The assertion is "no WIKI artifact", not "no
    # agent" — the rag plan now legitimately deposits the `concierge` agent (E12).
    assert not (tmp_path / "wiki").exists()
    assert not (tmp_path / ".claude" / "skills" / "wiki-author").exists()
    assert not (tmp_path / ".claude" / "commands").exists()
    assert not (tmp_path / ".claude" / "agents" / "wiki-curator.md").exists()
    # The eval skills (065) and the usability skill + concierge agent (E12) ARE part of the RAG
    # capability, by contrast.
    assert (tmp_path / ".claude" / "skills" / "eval-suite-author" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "eval-feedback" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "guided-setup" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "agents" / "concierge.md").exists()


def test_corpus_in_env_and_mcp(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", corpus="mycorp")
    assert "SERTOR_CORPUS=mycorp" in (tmp_path / ".sertor" / ".env").read_text()
    assert "mycorp" in (tmp_path / ".mcp.json").read_text()


# --- US2: idempotence and non-destructiveness ------------------------------------------------

def test_idempotent_config_only(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    report2, _ = _run(tmp_path, runner, backend="azure", with_deps=False)
    assert report2.exit_code() == 0
    assert report2.created == 0  # everything already present
    assert all(o.outcome.value in ("skipped", "merged") for o in report2.outcomes)


def test_deps_skips_init_when_pyproject_exists(tmp_path: Path, make_runner):
    (tmp_path / ".sertor").mkdir()
    (tmp_path / ".sertor" / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    # no uv init (already initialized), only uv add
    assert not any(cmd[:2] == ["uv", "init"] for cmd in _uv_calls(runner))
    assert any(cmd[:2] == ["uv", "add"] for cmd in _uv_calls(runner))


def test_uv_missing_failfast_no_sertor_dir(tmp_path: Path, make_runner):  # T020 / REQ-214
    runner = make_runner(available=False)
    report, _ = _run(tmp_path, runner, backend="azure")
    assert report.exit_code() == 1
    assert report.failed_step == ".sertor"
    assert not (tmp_path / ".sertor").exists()  # no partial state
    assert not (tmp_path / ".mcp.json").exists()  # subsequent steps not executed


def test_uv_add_failure_failfast(tmp_path: Path, make_runner):  # T020 / REQ-215
    runner = make_runner(fail_on="add")
    report, _ = _run(tmp_path, runner, backend="azure")
    assert report.exit_code() == 1
    assert report.failed_step == ".sertor"
    assert not (tmp_path / ".sertor" / ".env").exists()  # no rollback; subsequent steps not run


# --- US4: local backend and flags ------------------------------------------------------------

def test_backend_local_env_and_extras(tmp_path: Path, make_runner):  # SC-006
    runner = make_runner()
    _run(tmp_path, runner, backend="local")
    env = (tmp_path / ".sertor" / ".env").read_text(encoding="utf-8")
    assert "SERTOR_EMBED_PROVIDER=glove" in env and "AZURE_OPENAI" not in env
    add = next(cmd for cmd in _uv_calls(runner) if cmd[:2] == ["uv", "add"])
    assert "sertor-core[mcp,graph,rerank] @ git+" in add[2]  # no azure


def test_optout_extras(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", include_graph=False, include_rerank=False)
    add = next(cmd for cmd in _uv_calls(runner) if cmd[:2] == ["uv", "add"])
    assert "sertor-core[azure,mcp] @ git+" in add[2]


def test_no_deps_skips_uv(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    assert runner.calls == []  # no uv commands
    assert (tmp_path / ".sertor" / ".env").is_file()  # but the scaffold is present
    assert (tmp_path / ".mcp.json").is_file()


# --- feature 016 (FR-001/REQ-301): runtime confined to .sertor/ -----------------------------

def test_rag_plan_no_runtime_file_in_root(tmp_path: Path):
    """FR-001: no RAG plan artifact in root beyond `.mcp.json` and `.gitignore`.

    Anti-regression guard: a new ArtifactKind that sets the wrong `target_rel` (runtime file in
    root instead of under `.sertor/`) will fail this test.
    """
    profile = RagHostProfile.from_options(RagInstallOptions(target_root=tmp_path, backend="azure"))
    # Runtime stays under `.sertor/`; host-facing governance artifacts (feature 042: CLAUDE.md
    # block + `.claude/` hook + settings) are allowed in root, like `install wiki`.
    allowed_root = {".mcp.json", ".gitignore", "CLAUDE.md"}
    allowed_top = {".sertor", ".claude"}
    for art in build_rag_plan(profile, with_deps=True):
        rel = art.target_rel.replace("\\", "/")
        top = rel.split("/", 1)[0]
        assert top in allowed_top or rel in allowed_root, (
            f"artifact in root not allowed: {rel}"
        )


# --- US3 (feature 016): --mcp-scope project|local -------------------------------------------

def _calls(runner) -> list[list[str]]:
    return [cmd for cmd, _ in runner.calls]


def test_mcp_scope_project_writes_mcp_json(tmp_path: Path, make_runner):  # FR-004
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False, mcp_scope="project")
    assert (tmp_path / ".mcp.json").is_file()
    assert not any("claude" in cmd for cmd in _calls(runner))  # no client CLI call in project scope


def test_mcp_scope_local_registers_no_repo_file(tmp_path: Path, make_runner):  # FR-004/SC-003
    runner = make_runner()
    report, _ = _run(tmp_path, runner, backend="azure", with_deps=False, mcp_scope="local")
    assert report.exit_code() == 0
    assert not (tmp_path / ".mcp.json").exists()  # no file in the repo
    assert any(cmd[:3] == ["claude", "mcp", "add-json"] for cmd in _calls(runner))


def test_mcp_scope_local_claude_missing_failfast(tmp_path: Path, make_runner):  # FR-005/SC-005
    runner = make_runner(claude_available=False)
    report, _ = _run(tmp_path, runner, backend="azure", with_deps=False, mcp_scope="local")
    assert report.exit_code() == 1
    assert report.failed_step == "(mcp: client registry)"
    assert not (tmp_path / ".mcp.json").exists()  # no file written silently
    assert not any("add-json" in cmd for cmd in _calls(runner))  # add not attempted


def test_mcp_scope_local_idempotent_skip(tmp_path: Path, make_runner):  # SC-006
    runner = make_runner(claude_has_server=True)
    report, _ = _run(tmp_path, runner, backend="azure", with_deps=False, mcp_scope="local")
    assert report.exit_code() == 0
    assert any(cmd[:3] == ["claude", "mcp", "get"] for cmd in _calls(runner))
    assert not any("add-json" in cmd for cmd in _calls(runner))  # already registered → no add


def test_invalid_mcp_scope_rejected(tmp_path: Path):
    with pytest.raises(ConfigError):
        RagInstallOptions(target_root=tmp_path, mcp_scope="bogus")


# --- M2 (SC-007): non-Python host NOT touched -----------------------------------------------

def test_non_python_host_sources_untouched(tmp_path: Path, make_runner):
    sln = tmp_path / "App.sln"
    csproj = tmp_path / "Foo.csproj"
    sln.write_text("Microsoft Visual Studio Solution File\n", encoding="utf-8")
    csproj.write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>\n", encoding="utf-8")
    sln_before, csproj_before = sln.read_text(), csproj.read_text()

    runner = make_runner()
    report, _ = _run(tmp_path, runner, backend="azure")

    assert report.exit_code() == 0
    assert sln.read_text() == sln_before  # .NET sources unchanged
    assert csproj.read_text() == csproj_before
    # new files are only in .sertor/ + .mcp.json/.gitignore in root
    assert (tmp_path / ".sertor").is_dir()
    assert (tmp_path / ".mcp.json").is_file()


# ============================================================ E12 guided-setup: deposit (US8)

from sertor_installer.resources import read_asset_text  # noqa: E402

_SKILL_SRC = "rag/skills/guided-setup/SKILL.md"
_AGENT_SRC = "rag/agents/concierge.md"


def _skill_body() -> str:
    return read_asset_text(_SKILL_SRC)


def _agent_body() -> str:
    return read_asset_text(_AGENT_SRC)


def _frontmatter(text: str) -> str:
    """Leading `---`-fenced frontmatter block of a markdown asset (empty if absent)."""
    if not text.startswith("---"):
        return ""
    return text.split("---", 2)[1]


def test_guided_setup_skill_deposited_claude(tmp_path: Path, make_runner):  # US8-AC1
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", assistant=AssistantId.CLAUDE)
    assert (tmp_path / ".claude" / "skills" / "guided-setup" / "SKILL.md").is_file()


def test_guided_setup_skill_deposited_copilot(tmp_path: Path, make_runner):  # US8-AC1
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", assistant=AssistantId.COPILOT_CLI)
    assert (tmp_path / ".github" / "skills" / "guided-setup" / "SKILL.md").is_file()


def test_guided_setup_body_byte_identical(tmp_path: Path, make_runner):  # US8-AC2 parity
    rc = make_runner()
    rco = make_runner()
    claude_root = tmp_path / "claude"
    copilot_root = tmp_path / "copilot"
    claude_root.mkdir()
    copilot_root.mkdir()
    _run(claude_root, rc, backend="azure", assistant=AssistantId.CLAUDE)
    _run(copilot_root, rco, backend="azure", assistant=AssistantId.COPILOT_CLI)
    claude_skill = (claude_root / ".claude" / "skills" / "guided-setup" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    copilot_skill = (copilot_root / ".github" / "skills" / "guided-setup" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert claude_skill == copilot_skill  # skills are byte-copied (no `.agent.md` render)


def test_concierge_agent_deposited_claude(tmp_path: Path, make_runner):  # US8-AC1
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", assistant=AssistantId.CLAUDE)
    dest = tmp_path / ".claude" / "agents" / "concierge.md"
    assert dest.is_file()
    # Claude byte-copy → the `model: sonnet` pin is preserved.
    assert "model: sonnet" in _frontmatter(dest.read_text(encoding="utf-8"))


def test_concierge_agent_deposited_copilot(tmp_path: Path, make_runner):  # US8-AC1 / R-1
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", assistant=AssistantId.COPILOT_CLI)
    dest = tmp_path / ".github" / "agents" / "concierge.agent.md"
    assert dest.is_file()
    # E2-FEAT-015: Copilot custom-agent → `render_custom_agent` substitutes the POLICY
    # model-id (never a bare Claude alias — FEAT-011/049 non-regression).
    from sertor_install_kit.model_policy import resolve_model

    front = _frontmatter(dest.read_text(encoding="utf-8"))
    assert f"model: {resolve_model('concierge')}" in front


def test_concierge_copilot_frontmatter_no_claude_names(tmp_path: Path, make_runner):  # US8-AC3
    """No Claude product/model name leaks into the Copilot frontmatter — EXCEPT the policy
    `model:` line itself, which legitimately carries an id containing the substring "claude"
    (E2-FEAT-015, e.g. `claude-haiku-4.5`, a NATIVE Copilot model id, not a Claude alias)."""
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", assistant=AssistantId.COPILOT_CLI)
    text = (tmp_path / ".github" / "agents" / "concierge.agent.md").read_text(encoding="utf-8")
    fm = _frontmatter(text)
    non_model_lines = "\n".join(
        ln for ln in fm.splitlines() if not ln.strip().startswith("model:")
    )
    for name in ("Claude", "Opus", "Haiku", "claude"):
        assert name not in non_model_lines, (
            f"Claude product/model name {name!r} leaked into Copilot frontmatter "
            f"(outside model:)"
        )
    model_line = next(ln for ln in fm.splitlines() if ln.strip().startswith("model:"))
    value = model_line.split(":", 1)[1].strip()
    assert value not in {"haiku", "sonnet", "opus"}


def test_concierge_lifecycle_uninstall_claude(tmp_path: Path, make_runner):  # W6
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False, assistant=AssistantId.CLAUDE)
    dest = tmp_path / ".claude" / "agents" / "concierge.md"
    assert dest.is_file()
    profile = RagHostProfile.from_options(
        RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    )
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, runner, LifecycleOp.UNINSTALL, assistant=AssistantId.CLAUDE
    )
    assert not dest.exists()  # concierge is an owned_file → removed on uninstall


def test_concierge_lifecycle_uninstall_copilot(tmp_path: Path, make_runner):  # W6
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False, assistant=AssistantId.COPILOT_CLI)
    dest = tmp_path / ".github" / "agents" / "concierge.agent.md"
    assert dest.is_file()
    profile = RagHostProfile.from_options(
        RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    )
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    execute_rag_lifecycle(
        plan, profile, runner, LifecycleOp.UNINSTALL, assistant=AssistantId.COPILOT_CLI
    )
    assert not dest.exists()


def test_concierge_upgrade_copilot_render_aware(tmp_path: Path, make_runner):  # W7
    runner = make_runner()
    profile = RagHostProfile.from_options(
        RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    )
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    # simulate a stale Copilot agent (raw Claude source with the `model:` pin) to force an upgrade
    dest = tmp_path / ".github" / "agents" / "concierge.agent.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("---\nname: concierge\nmodel: sonnet\n---\nold body\n", encoding="utf-8")
    execute_rag_lifecycle(
        plan, profile, runner, LifecycleOp.UPGRADE, assistant=AssistantId.COPILOT_CLI
    )
    from sertor_install_kit.model_policy import resolve_model

    fm = _frontmatter(dest.read_text(encoding="utf-8"))
    # upgrade re-rendered the agent: the stale Claude `model: sonnet` is replaced by the
    # policy id (E2-FEAT-015, US6 idempotence/lifecycle).
    assert f"model: {resolve_model('concierge')}" in fm
    assert "model: sonnet" not in fm


# ===================================================== E12 guided-setup: concierge routing (US9)

def test_concierge_routes_to_guided_setup():  # US9-AC1
    assert "guided-setup" in _agent_body()


def test_concierge_has_single_branch():  # US9-AC2 anti scope-creep
    body = _agent_body()
    for forbidden in ("config-recommender", "search-diagnose", "FEAT-004", "FEAT-007"):
        assert forbidden not in body, f"concierge stub must not reference {forbidden!r}"


def test_concierge_body_host_agnostic():  # RNF-2 / lesson 056
    # Body only (the `model:` pin lives in the frontmatter, by-target).
    body = _agent_body().split("---", 2)[2]
    assert ".claude/" not in body
    assert "/wiki" not in body and "/requirements" not in body
    for name in ("Claude", "Opus", "Haiku", "CLAUDE.md"):
        assert name not in body


def test_concierge_model_pin_in_frontmatter_only():  # agent-concierge contract §Vincoli
    text = _agent_body()
    assert "model: sonnet" in _frontmatter(text)
    body = text.split("---", 2)[2]
    assert "model:" not in body  # the pin is not in the body


# ============================================ E12 guided-setup: skill content (US1-US7, static)

_VEHICLES = ("sertor install", "sertor configure --set", "sertor-rag doctor", "sertor-rag index")


def test_skill_flow_six_steps_in_order():  # US1-AC1
    body = _skill_body()
    # Match the section HEADINGS (`## Step N`), not bare "Step N" (which a step may cite in prose).
    markers = [f"## Step {n}" for n in range(1, 7)]
    positions = [body.find(m) for m in markers]
    assert all(p >= 0 for p in positions), "all six steps must be present as headings"
    assert positions == sorted(positions), "steps must appear in order"


def test_skill_cites_all_vehicles_by_command_name():  # US1-AC1
    body = _skill_body()
    for vehicle in _VEHICLES:
        assert vehicle in body, f"vehicle {vehicle!r} not cited by command name"


def test_skill_no_core_import_no_reimplementation():  # US1 / FR-001/FR-013
    body = _skill_body()
    assert "import sertor_core" not in body
    assert "build_facade" not in body and "build_indexer" not in body
    # the hard boundary is stated explicitly
    assert "build_*" in body or "build_" in body  # names the forbidden factories


def test_skill_verify_via_doctor_gate():  # US1-AC2 / US5-AC1
    body = _skill_body()
    assert "Step 6" in body
    verify_section = body[body.find("Step 6"):]
    assert "sertor-rag doctor" in verify_section


def test_skill_provider_three_signals():  # US2-AC1 / FR-004 / D-3
    body = _skill_body().lower()
    assert "credential" in body  # cloud creds signal
    assert "airgapped" in body  # airgapped signal
    assert "semantic" in body or "natural-language" in body or "nl" in body  # NL signal


def test_skill_provider_local_options_and_confirm():  # US2-AC1/AC3
    body = _skill_body()
    assert "glove" in body and "hash" in body  # local options
    assert "confirm" in body.lower()  # propose + confirm
    assert "automatic" in body.lower() or "never select" in body.lower()


def test_skill_secrets_secure_path_no_print():  # US3-AC1/AC2 / FR-006
    body = _skill_body()
    assert "sertor configure --set" in body
    low = body.lower()
    assert "never print" in low or "not print" in low or "never printed" in low
    assert "getpass" in low or "secure" in low  # secure prompt


def test_skill_secret_already_present_not_reasked():  # US3-AC3
    low = _skill_body().lower()
    assert "already present" in low and ("re-ask" in low or "not re-ask" in low)


def test_skill_glove_download_announced_before_index():  # US4-AC1/AC2 / FR-007
    body = _skill_body()
    assert "822" in body  # one-time GloVe download size announced
    low = body.lower()
    assert "before" in low and "cache" in low  # announce before index; cache → no announce


def test_skill_verify_fail_loud():  # US5-AC2 / FR-003 / Principle XII
    body = _skill_body()
    low = body.lower().replace("*", "")  # strip markdown emphasis (`**not**` → `not`)
    assert "area" in low and "remedy" in low  # area + remedy on failure
    assert "not declare success" in low  # honest failure (never assume "done")


def test_skill_forbids_done_without_doctor():  # RNF-4 (E10-FEAT-022: rule lives inline in Step 6)
    # The redundant "What NOT to do" section was removed (E10-FEAT-022, FR-004/006); the rule
    # "no 'done' without a green doctor" survives inline in Step 6 — Verify.
    body = _skill_body()
    assert "What NOT to do" not in body  # the duplicated trailing section is gone
    verify = body[body.find("## Step 6"):].lower()
    assert "green" in verify and "doctor" in verify  # forbids declaring done without a green doctor
    assert "not declare success" in verify.replace("*", "")


def test_skill_consent_gate_read_only_vs_mutation():  # US6-AC1/AC2 / FR-008
    body = _skill_body()
    assert "Consent gate" in body
    low = body.lower()
    assert "read-only" in low and "confirmation" in low
    assert "do not confirm" in low or "not confirm" in low  # stop if no confirmation


def test_skill_idempotence_detect_via_doctor_json():  # US7-AC1/AC2 / FR-009
    body = _skill_body()
    assert "sertor-rag doctor --json" in body
    low = body.lower()
    assert "already configured" in low or "already verified" in low
    assert "re-scaffold" in low or "do not re-scaffold" in low or "only the missing" in low


def test_skill_no_claude_container_leak():  # RNF-2 / R-1
    body = _skill_body()
    assert ".claude/" not in body
    assert "/wiki" not in body
    for name in ("Claude Code", "Opus", "Haiku", "$ARGUMENTS"):
        assert name not in body
