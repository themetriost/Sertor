"""Orchestrazione di `sertor install rag` (data-model §4, plan 015).

`build_rag_plan` enumera gli artefatti nell'ordine canonico (DEPENDENCIES → ENV_MERGE → MCP_MERGE →
GITIGNORE_APPEND); `execute_rag_plan` esegue sequenzialmente con **fail-fast no-rollback** (come
`install_wiki.execute_plan`): al primo errore di dominio registra l'esito di errore, valorizza
`failed_step` e si ferma; gli artefatti già scritti restano (il re-run li trova → skipped/merged).

**install ≠ run**: il passo DEPENDENCIES esegue solo `uv init`/`uv add` (mai indicizzazione). Il
runtime vive isolato in `<target>/.sertor/`; `.mcp.json` e `.gitignore` stanno in radice host. Layer
sottile (Principio I): `uv` è dietro il `CommandRunner` iniettabile.
"""
from __future__ import annotations

import json

from sertor_core.domain.errors import ConfigError, SertorError
from sertor_installer.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    Outcome,
    WriteStrategy,
)
from sertor_installer.command_runner import CommandRunner
from sertor_installer.env_merge import merge_env
from sertor_installer.gitignore_append import append_gitignore
from sertor_installer.mcp_merge import merge_mcp
from sertor_installer.rag_profile import RagHostProfile
from sertor_installer.report import InstallReport
from sertor_installer.resources import read_asset_text

_UV = "uv"


class DependencyError(SertorError):
    """Bootstrap delle dipendenze fallito: `uv` assente o `uv init`/`uv add` non riuscito."""


def build_rag_plan(profile: RagHostProfile, with_deps: bool = True) -> list[Artifact]:
    """Lista ordinata di `Artifact` (DEPENDENCIES saltato se `with_deps=False`)."""
    plan: list[Artifact] = []
    if with_deps:
        plan.append(
            Artifact(ArtifactKind.DEPENDENCIES, None, ".sertor", WriteStrategy.BOOTSTRAP_DEPS)
        )
    plan.append(
        Artifact(
            ArtifactKind.ENV_MERGE,
            f"rag/env.{profile.backend}.tmpl",
            ".sertor/.env",
            WriteStrategy.MERGE_ENV,
        )
    )
    plan.append(
        Artifact(
            ArtifactKind.MCP_MERGE,
            "rag/mcp.server.json.tmpl",
            ".mcp.json",
            WriteStrategy.MERGE_JSON,
        )
    )
    plan.append(
        Artifact(ArtifactKind.GITIGNORE_APPEND, None, ".gitignore", WriteStrategy.APPEND_LINES)
    )
    return plan


def _apply_deps(profile: RagHostProfile, runner: CommandRunner) -> ArtifactOutcome:
    """`BOOTSTRAP_DEPS`: `uv init --bare` (se manca pyproject) + `uv add` dentro `.sertor/`.

    Verifica `uv` PRIMA di creare `.sertor/` (REQ-214: evita stato a metà). Mai indicizza.
    """
    if not runner.is_available(_UV):
        raise DependencyError(
            "`uv` non è disponibile sul PATH: installalo (https://docs.astral.sh/uv/) e riesegui"
        )
    sertor_dir = profile.sertor_dir
    sertor_dir.mkdir(parents=True, exist_ok=True)
    already = (sertor_dir / "pyproject.toml").exists()
    if not already:
        res = runner.run([_UV, "init", "--bare"], cwd=sertor_dir)
        if not res.ok:
            raise DependencyError(f"`uv init` fallito: {res.stderr.strip() or res.returncode}")
    spec = profile.dep_spec()
    res = runner.run([_UV, "add", spec], cwd=sertor_dir)
    if not res.ok:
        raise DependencyError(f"`uv add` fallito: {res.stderr.strip() or res.returncode}")
    outcome = Outcome.SKIPPED if already else Outcome.CREATED
    return ArtifactOutcome(".sertor", outcome, f"uv add {spec}")


def _apply_env(profile: RagHostProfile) -> ArtifactOutcome:
    """`MERGE_ENV`: `.sertor/.env` da template per backend (segreti vuoti), merge additivo."""
    rendered = read_asset_text(f"rag/env.{profile.backend}.tmpl").format(corpus=profile.corpus)
    outcome, detail = merge_env(profile.sertor_dir / ".env", rendered)
    return ArtifactOutcome(".sertor/.env", outcome, detail)


def _apply_mcp(profile: RagHostProfile) -> ArtifactOutcome:
    """`MERGE_JSON`: server `sertor-rag` in `.mcp.json` (radice host), merge additivo."""
    entry = json.loads(read_asset_text("rag/mcp.server.json.tmpl").format(corpus=profile.corpus))
    outcome, detail = merge_mcp(profile.target_root / ".mcp.json", entry)
    return ArtifactOutcome(".mcp.json", outcome, detail)


def _apply_gitignore(profile: RagHostProfile) -> ArtifactOutcome:
    """`APPEND_LINES`: voci runtime nel `.gitignore` (radice host), dedup."""
    outcome, detail = append_gitignore(profile.target_root / ".gitignore")
    return ArtifactOutcome(".gitignore", outcome, detail)


def execute_rag_plan(
    plan: list[Artifact], profile: RagHostProfile, runner: CommandRunner
) -> InstallReport:
    """Esegue il piano con fail-fast no-rollback. Ritorna l'`InstallReport` (capability=rag)."""
    report = InstallReport(target=str(profile.target_root), capability="rag")
    for art in plan:
        try:
            if art.kind is ArtifactKind.DEPENDENCIES:
                outcome = _apply_deps(profile, runner)
            elif art.kind is ArtifactKind.ENV_MERGE:
                outcome = _apply_env(profile)
            elif art.kind is ArtifactKind.MCP_MERGE:
                outcome = _apply_mcp(profile)
            elif art.kind is ArtifactKind.GITIGNORE_APPEND:
                outcome = _apply_gitignore(profile)
            else:  # pragma: no cover — kind ignoto è un bug, non un input
                raise ConfigError(f"kind di artefatto non gestito: {art.kind}")
        except SertorError as exc:
            report.add(ArtifactOutcome(art.target_rel, Outcome.ERROR, str(exc)))
            break  # fail-fast: stop al primo errore di dominio (no rollback)
        report.add(outcome)
    return report
