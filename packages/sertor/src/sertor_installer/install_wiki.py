"""Orchestrazione di `sertor install wiki`: `InstallPlan` + esecuzione (data-model §3, D8).

`build_install_plan` enumera gli assets bundlati (MAI numeri fissi: il piano deriva dalla
composizione del bundle, F1/F8) producendo la lista ordinata di `Artifact`. `execute_plan` esegue
sequenzialmente con fail-fast (REQ-125, D8): al primo `ERROR` si ferma, `failed_step` valorizzato,
gli artefatti già scritti restano (no rollback). Layer **sottile** (Principio I): delega a
`claude_md`, `settings_merge`, `config_gen` e a `sertor_core.wiki_tools` per la struttura.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_core.domain.errors import ConfigError, SertorError
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.structure import init_structure
from sertor_installer import claude_md, config_gen, settings_merge
from sertor_installer.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    Outcome,
    WriteStrategy,
)
from sertor_installer.config_gen import HostProfile
from sertor_installer.report import InstallReport
from sertor_installer.resources import iter_asset_dir, read_asset_text

# Asset speciali (non-FILE): nomi relativi a `assets/`.
_SETTINGS_FRAGMENT = "settings.hooks.json"
_CLAUDE_MD_BLOCK = "claude-md-block.md"
_CONFIG_TEMPLATE = "wiki.config.toml.tmpl"

_SETTINGS_TARGET = ".claude/settings.json"
_CLAUDE_MD_TARGET = "CLAUDE.md"
# La config del wiki vive DENTRO `wiki/` (feature 016, igiene radice host): radice ospite pulita.
# Gli strumenti la localizzano via convenzione `--config wiki/wiki.config.toml --root .` o via
# auto-discovery del CLI (`wiki_tools/__main__`).
_CONFIG_TARGET = "wiki/wiki.config.toml"


def build_install_plan() -> list[Artifact]:
    """Lista ordinata di `Artifact` (data-model §3). Enumera i FILE dagli assets `claude/`.

    Ordine canonico: FILE×N (skill/command/agent/hook) → SETTINGS_MERGE → MARKER_BLOCK → CONFIG →
    STRUCTURE. I FILE non sono cablati: si scoprono percorrendo `assets/claude/` (F1/F8).
    """
    plan: list[Artifact] = []

    # 1. FILE × N — tutti i file sotto assets/claude/ → .claude/<...>
    for rel_path, _content in iter_asset_dir("claude"):
        plan.append(
            Artifact(
                kind=ArtifactKind.FILE,
                source=f"claude/{rel_path}",
                target_rel=f".claude/{rel_path}",
                strategy=WriteStrategy.CREATE_IF_ABSENT,
            )
        )

    # 2. SETTINGS_MERGE
    plan.append(
        Artifact(
            kind=ArtifactKind.SETTINGS_MERGE,
            source=_SETTINGS_FRAGMENT,
            target_rel=_SETTINGS_TARGET,
            strategy=WriteStrategy.MERGE_DEDUP,
        )
    )
    # 3. MARKER_BLOCK
    plan.append(
        Artifact(
            kind=ArtifactKind.MARKER_BLOCK,
            source=_CLAUDE_MD_BLOCK,
            target_rel=_CLAUDE_MD_TARGET,
            strategy=WriteStrategy.APPEND_BLOCK,
        )
    )
    # 4. CONFIG (generato da HostProfile, source = template)
    plan.append(
        Artifact(
            kind=ArtifactKind.CONFIG,
            source=_CONFIG_TEMPLATE,
            target_rel=_CONFIG_TARGET,
            strategy=WriteStrategy.GENERATE_CONFIG,
        )
    )
    # 5. STRUCTURE (delega a init_structure; nessun source-asset)
    plan.append(
        Artifact(
            kind=ArtifactKind.STRUCTURE,
            source=None,
            target_rel="wiki/",
            strategy=WriteStrategy.INIT_STRUCTURE,
        )
    )
    return plan


def _resolve(target_root: Path, target_rel: str) -> Path:
    """Risolve un `target_rel` sotto `target_root` (i path sono già validati come relativi)."""
    return target_root / target_rel


def _apply_file(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`CREATE_IF_ABSENT`: copia byte-per-byte dell'asset; esiste → skip (file-per-file)."""
    dest = _resolve(target_root, art.target_rel)
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "già presente")
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    dest.write_text(read_asset_text(art.source), encoding="utf-8")
    return ArtifactOutcome(art.target_rel, Outcome.CREATED)


def _apply_settings(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`MERGE_DEDUP`: merge additivo del frammento hook (D5)."""
    dest = _resolve(target_root, art.target_rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    fragment = json.loads(read_asset_text(art.source))
    outcome, detail = settings_merge.merge_settings(dest, fragment)
    return ArtifactOutcome(art.target_rel, outcome, detail)


def _apply_marker(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`APPEND_BLOCK`: blocco a marker idempotente nel `CLAUDE.md` (D4).

    L'outcome di CLAUDE.md è SEMPRE `block` quando il blocco viene scritto, anche se il file è
    creato ex novo (F11); `skipped` solo se il blocco era già presente.
    """
    dest = _resolve(target_root, art.target_rel)
    assert art.source is not None
    block_content = read_asset_text(art.source)
    outcome = claude_md.write_ritual_block(dest, block_content)
    detail = "sezione step-ritual inserita" if outcome is Outcome.BLOCK else "blocco già presente"
    return ArtifactOutcome(art.target_rel, outcome, detail)


def _apply_config(target_root: Path, art: Artifact, profile: HostProfile) -> ArtifactOutcome:
    """`GENERATE_CONFIG`: genera `wiki.config.toml` da template + HostProfile; esiste → skip."""
    dest = _resolve(target_root, art.target_rel)
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "già presente")
    dest.parent.mkdir(parents=True, exist_ok=True)  # `wiki/` può non esistere ancora (feature 016)
    dest.write_text(config_gen.generate_wiki_config(profile), encoding="utf-8")
    detail = f"language={profile.language}, source_dirs={','.join(profile.source_dirs)}"
    return ArtifactOutcome(art.target_rel, Outcome.CREATED, detail)


def _apply_structure(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`INIT_STRUCTURE`: delega a `init_structure` del core (idempotente). Serve la config.

    Con la config in `wiki/` (feature 016) i path relativi (`root="wiki"`, `source_dirs`) vanno
    risolti dalla radice ospite, non dalla cartella della config → `root_override=target_root`.
    """
    config_path = _resolve(target_root, _CONFIG_TARGET)
    wiki_profile = load_profile(config_path, root_override=target_root)
    result = init_structure(wiki_profile)
    detail = f"{len(result.created)} create, {len(result.skipped_existing)} esistenti"
    outcome = Outcome.CREATED if result.created else Outcome.SKIPPED
    return ArtifactOutcome(art.target_rel, outcome, detail)


def execute_plan(plan: list[Artifact], profile: HostProfile) -> InstallReport:
    """Esegue il piano sequenzialmente con fail-fast (REQ-125, D8).

    Al primo `ERROR` (eccezione di dominio sollevata da un passo) registra l'esito di errore,
    valorizza `failed_step` e si ferma: gli artefatti già scritti restano (no rollback).
    """
    report = InstallReport(target=str(profile.target_root))
    root = profile.target_root

    for art in plan:
        try:
            if art.kind is ArtifactKind.FILE:
                outcome = _apply_file(root, art)
            elif art.kind is ArtifactKind.SETTINGS_MERGE:
                outcome = _apply_settings(root, art)
            elif art.kind is ArtifactKind.MARKER_BLOCK:
                outcome = _apply_marker(root, art)
            elif art.kind is ArtifactKind.CONFIG:
                outcome = _apply_config(root, art, profile)
            elif art.kind is ArtifactKind.STRUCTURE:
                outcome = _apply_structure(root, art)
            else:  # pragma: no cover — kind ignoto è un bug, non un input
                raise ConfigError(f"kind di artefatto non gestito: {art.kind}")
        except SertorError as exc:
            report.add(ArtifactOutcome(art.target_rel, Outcome.ERROR, str(exc)))
            break  # fail-fast: stop al primo errore di dominio
        report.add(outcome)

    return report
