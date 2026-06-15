# Implementation Plan: Distribuzione su GitHub Copilot (parità di assistente) — pacchetto `sertor`

**Branch**: `044-distribuzione-copilot` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/044-distribuzione-copilot/spec.md`

## Summary

Rendere installabili su **GitHub Copilot** le superfici del pacchetto `sertor` (server MCP `sertor-rag`
+ sistema-wiki) con **parità funzionale piena**, introducendo un **assistente target** nell'installer.
Approccio (vedi `research.md`, DA-2): **ibrido = riuso del contenuto + traduzione del contenitore**. Il
*contenuto* (testo del blocco rituale, corpo dei comandi/skill, persona dell'agente, script degli hook,
entry del server MCP) resta **fonte unica**; un **profilo-assistente** nel `sertor-install-kit` ne
**rende** la forma concreta per assistente (Claude → `.claude/**`,`.mcp.json`,`CLAUDE.md`; Copilot →
`.github/**`,`.vscode/mcp.json`,`.github/copilot-instructions.md`). I plan-builder
(`build_install_plan`/`build_rag_plan`) diventano **parametrici sull'assistente** invece di cablare
`.claude/...`. Il targeting vive nel kit per essere **riusato da `sertor-flow`/FEAT-009**.

## Technical Context

**Language/Version**: Python ≥ 3.11 (pacchetti installer `sertor`, `sertor-install-kit`).

**Primary Dependencies**: `sertor-install-kit` (stdlib-only: `importlib.resources`, `json`, `pathlib`).
**Nessuna nuova dipendenza runtime per FEAT-007** (il pivot launch-installer di spec-kit è FEAT-009).

**Storage**: filesystem del repo ospite (file di configurazione/asset). Nessun DB.

**Testing**: `pytest` (`packages/sertor/tests`, `packages/sertor-install-kit/tests`) con host simulato in
`tmp_path`; `ruff`. Misura di parità = test che verifica la mappatura superficie→artefatto per i due
assistenti (SC-002).

**Target Platform**: cross-platform (Windows + POSIX). Gli script hook restano duali `.ps1` + `.sh`.

**Project Type**: CLI/installer in uv-workspace (pacchetti multipli sotto `packages/`).

**Performance Goals**: installazione rapida (ordine di secondi, escluso il bootstrap `uv` già esistente
in `install rag`); nessun percorso a costo elevato introdotto.

**Constraints**: install ≠ run; non distruttivo/idempotente per artefatto; segreti mai versionati; CLI di
esecuzione assistant-agnostic; degradazione onesta sui gap (dichiarati, non taciuti).

**Scale/Scope**: poche superfici (MCP · blocco istruzioni · comandi/skill wiki · agente · hook) × 2
assistenti (`claude`, `copilot`); Codex fuori taglio.

## Constitution Check

*GATE: Pre-Phase 0 — PASS. Re-check post-design (Phase 1) in fondo.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il design tocca solo i pacchetti installer
  (`sertor`/`sertor-install-kit`); `sertor_core` resta invariato. Il kit resta stdlib-only e non importa
  SDK. **PASS.**
- [x] **II — Boundary & local-first:** nessuna nuova dipendenza esterna né scelta cloud per FEAT-007;
  l'assistente è una superficie d'ospite, non un provider. **PASS.**
- [x] **III — YAGNI & unità piccole:** si **riusano** le `ArtifactKind`/merge esistenti dove possibile
  (MARKER_BLOCK su `copilot-instructions.md`; SETTINGS_MERGE su `.github/hooks/*.json`; MCP_MERGE
  parametrizzato per `.vscode/mcp.json`); si aggiunge il minimo (profilo-assistente + reso prompt-file/
  custom-agent). Codex **non** anticipato. **PASS.**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** fail-fast no-rollback dell'executor preservato; i gap
  di parità sono **dichiarati** (FR-016), nessun `None`/skip silenzioso. **PASS.**
- [x] **V — Testabilità & misure:** test con host in `tmp_path` (pattern `test_install_wiki/rag`); la
  **parità** è misurata da un test di copertura superficie-per-superficie (SC-002). **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** MARKER_BLOCK idempotente, FILE create-if-absent, merge
  dedup; install ≠ run (FR-018); coesistenza claude+copilot senza doppio-trigger (edge case). **PASS.**
- [x] **VII — Leggibilità:** vocabolario di dominio (`assistant`, `surface`, `render`, `target`). **PASS.**
- [x] **VIII — Configurabilità centralizzata:** l'assistente target è un **parametro** (`--assistant`),
  default documentato; nessun path d'assistente hardcoded nel corpo (passa nel profilo). **PASS.**
- [x] **IX — Osservabilità:** l'install emette già `log_event` via il kit; gli eventi includono
  l'assistente target. **PASS.**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** questa feature **è** l'estensione del Principio X
  all'**assistente ospite**: l'assistente si **configura**, non si presume; le superfici per-assistente
  vivono nel profilo, non nel corpo. **PASS (embodiment).**
- [x] **XI — Consumo via vehicles:** wira il **vehicle MCP** per Copilot; l'hook anti-bypass Principio XI
  viene portato anche lato Copilot. Nessun accesso diretto a `sertor_core` introdotto. **PASS.**

Nessuna violazione → **Complexity Tracking vuoto**.

> **Nota anti-drift (Principio III/VI, REQ-021/FR-021):** dove gli asset Copilot non sono generabili 1:1
> dal contenuto Claude (frontmatter prompt-file/custom-agent diverso), si adotta il pattern già in uso
> per `.claude/` (asset come fonte canonica + **test di guardia** che impedisce la deriva), non una
> seconda copia mantenuta a mano senza rete di sicurezza.

## Project Structure

### Documentation (this feature)

```text
specs/044-distribuzione-copilot/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisione DA-2 (riuso vs traduzione) + sotto-decisioni per superficie
├── data-model.md        # Phase 1 — AssistantProfile, Surface, mappatura per-assistente
├── contracts/           # Phase 1 — contratto CLI --assistant + contratto mappatura superfici
├── quickstart.md        # Phase 1 — installare su un ospite Copilot e verificare
└── tasks.md             # Phase 2 (/speckit-tasks — non creato qui)
```

### Source Code (repository root)

```text
packages/sertor-install-kit/src/sertor_install_kit/
├── assistant.py          # NUOVO: AssistantId/AssistantProfile — mappa Surface → (target, formato, strategy)
├── mcp_merge.py          # ESTESO: root-key parametrico (mcpServers ↔ servers) + target parametrico
├── claude_md.py          # riuso write_marker_block (target/markers già parametrici)
└── settings_merge.py     # riuso merge_settings su file JSON arbitrario (es. .github/hooks/*.json)

packages/sertor/src/sertor_installer/
├── install_wiki.py       # build_install_plan(assistant) — plan parametrico sull'assistente
├── install_rag.py        # build_rag_plan(assistant, ...) — idem
├── __main__.py           # CLI: opzione --assistant claude|copilot (default documentato)
├── surfaces.py           # NUOVO (opz.): reso prompt-file/custom-agent da contenuto condiviso
└── assets/
    ├── claude/** , rag/** , claude-md-block*.md   # fonte canonica esistente (Claude)
    └── copilot/**                                  # NUOVO: asset/reso Copilot (o generati) + guardia

packages/sertor/tests/  ·  packages/sertor-install-kit/tests/
└── test_install_*_copilot.py , test_assistant_profile.py , test_surface_parity.py   # NUOVI
```

**Structure Decision**: si estendono i due pacchetti installer esistenti; il **profilo-assistente** sta
nel `sertor-install-kit` (condiviso con `sertor-flow`/FEAT-009). Nessun nuovo pacchetto.

## Complexity Tracking

*Nessuna violazione del Constitution Check → sezione vuota.*
