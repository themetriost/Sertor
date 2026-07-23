---
title: sertor-install-kit — il toolkit di installazione condiviso
type: tech
tags: [installer, toolkit, stdlib, host-agnostico, deterministic, packages]
created: 2026-06-15
updated: 2026-07-23
sources: ["packages/sertor-install-kit/", "specs/037-governance-sertor-flow/research.md", "specs/037-governance-sertor-flow/plan.md"]
---

# `sertor-install-kit` — il toolkit di installazione

Il **motore di installazione** riusabile e zero-dipendenza, estratto dal nucleo di `sertor`
(packages/sertor) e distribuito come pacchetto separato (`packages/sertor-install-kit`, modulo
`sertor_install_kit`). È il **secondo consumatore reale** che giustifica l'estrazione (Principio
III: niente speculativo).

## Che cos'è

Un toolkit **stdlib-only** (nessuna dipendenza esterna, nemmeno da `sertor-core`) che fornisce i
blocchi costruttivi per installare artefatti di sviluppo su un repository ospite:

- **Artefatti e strategie di scrittura** (`Artifact`/`ArtifactKind`/`WriteStrategy`/`Outcome`): la
  tassonomia di cosa si installa (file, merge di JSON/YAML/shell script, marker block).
- **Accesso asset parametrico** (`resources.py` via `importlib.resources`): lettura da package-data con
  radice asset parametrica (il kit non conosce Sertor; ogni consumatore fornisce i propri asset).
- **Scrittore di blocchi a marker** (`claude_md.write_marker_block`): generalizzato per supportare
  marker arbitrari (il kit non conosce i marker wiki, ognuno li fornisce).
- **Merge primitivi**: deduplicazione intelligente per `settings.json`, `.env`, `.mcp.json`,
  `.gitignore` senza perdita di contenuto esistente.
- **Esecutore di piano generico** (`execute_plan`): loop fail-fast no-rollback che consuma un piano
  di artefatti + una callback di applicazione (il consumatore fornisce il dispatch per-`kind`).
- **Errori e logging** (`InstallerError`/`ConfigError`, `log_event` stdlib): osservabilità
  minimalista (Principio IX, senza dipendere dal core).
- **Validazione** (`path_traversal_check`): prevenzione vulnerabilità durante merge e link.

## Perché esiste

Costituisce la metà **meccanica** (deterministica, testabile senza LLM) del processo di
installazione. Finché era soltanto in `sertor` era pensato per il RAG; quando [[sertor-flow]] ha
chiesto di installare SDLC **senza** il core di retrieval (REQ-002), l'estrazione è diventata
necessaria:

- **DRY (NFR-2):** un solo luogo dove vive la logica di merge/marker/executor.
- **Decoupling:** `sertor-flow` dipende dal kit, non da `sertor-core`. `sertor` dipende da
  entrambi (RAG + toolkit).
- **Topologia:** `sertor-core` (RAG) → niente dipendenze aggiuntive; `sertor` (wiki + rag)
  → kit + core; `sertor-flow` (governance) → kit.

## Cosa contiene

### Core components

**`artifacts.py`** — Tassonomia degli artefatti:
- `ArtifactKind` enum: `FILE`, `SETTINGS_MERGE`, `MARKER_BLOCK`, `STRUCTURE`, `CONFIG`,
  `DEPENDENCIES`, `ENV_MERGE`, `MCP_MERGE`, `GITIGNORE_APPEND` (feature 015, runtime RAG in
  `.sertor/`) e `MCP_REGISTER` (feature 016, registra il server nel client — nessun file nel repo).
- `WriteStrategy` enum: `CREATE_IF_ABSENT`, `MERGE_DEDUP`, `APPEND_BLOCK`, `INIT_STRUCTURE`,
  `GENERATE_CONFIG`, `BOOTSTRAP_DEPS`, `MERGE_ENV`, `MERGE_JSON`, `APPEND_LINES`, `REGISTER_CLI`.
- `LifecycleOp` (StrEnum, feature 048): `INSTALL`, `UPGRADE`, `UNINSTALL` — verbo del ciclo di vita,
  **ortogonale** a `ArtifactKind` (lo stesso piano è percorso con verbi diversi; `INSTALL` è il default).
- `Artifact`: dataclass `frozen` `(kind, source, target_rel, strategy)` con validazione
  path-traversal in `__post_init__` (`target_rel` sempre relativo, mai `..`).
- `Outcome` enum: `CREATED`/`SKIPPED`/`MERGED`/`BLOCK`/`ERROR` + `UPDATED`/`REMOVED` (feature 048,
  upgrade/uninstall) + `PRESENT_DIVERGENT` (E2-FEAT-018: path posseduto presente ma con contenuto
  divergente, lasciato intatto — distinto da `SKIPPED` "identico"). `ArtifactOutcome` è la dataclass
  che accoppia `(target_rel, outcome, detail)`.

**`resources.py`** — Accesso a package-data:
- `iter_asset_dir(anchor_module, asset_root)`: scansiona ricorsivamente gli asset dentro un
  modulo, restituendo `(rel_path, bytes_content)`. Parametrico per `anchor_module` (il consumatore
  dice "leggi da `sertor_flow.assets`" o "`sertor_installer.assets`").

**`claude_md.py`** — Scrittore di blocchi a marker:
- `write_marker_block(path, content, marker_start, marker_end)`: generalizzazione di
  `write_ritual_block`. Tre casi identici: assente → crea; presente-senza-marker → append;
  presente-con-marker → skip (idempotente, byte-per-byte fuori dai marker).

**`merge.py` (suite)** — Merge intelligenti per formati comuni:
- `settings_merge()`: unisce JSON dict mantenendo structure profonda. Caso critico: deduplicazione
  intelligente degli hook per lo **stem dello script** (vedi [[identita-hook-nel-merge]]), non per
  la stringa del comando (che è resa mutabile).
- `env_merge()`: accomoda `.env` senza sovrascrivere chiavi esitenti.
- `mcp_merge()`: preserva altri server MCP, aggiunge il nuovo senza duplicare.
- `gitignore_append()`: dedup per-linea, append inerte se già presente.

**`executor.py`** — Orchestratore generico:
- `execute_plan(plan: List[Artifact], apply: Callable[[Artifact], ArtifactOutcome]) ->
  InstallReport`: fail-fast, cattura `InstallerError`, arresta al primo errore, lascia gli
  artefatti già scritti. La callback `apply` è fornita dal consumatore e chiude su contesto
  (target_root, logging, runner).

**`errors.py`** — Base di eccezioni installer:
- `InstallerError(Exception)`: radice.
- `ConfigError(InstallerError)`: assente configurazione/asset.
- `PathTraversalError(InstallerError)`: tentativo path escaping.

**`observability.py`** — Logging strutturato minimale:
- `log_event(level, operation, **fields)`: wrapper `logging.Logger.log` che struttura i campi
  in `extra` dict. Niente redazione (già fatta a call-site); niente rete. Sufficiente per
  Principio IX.

### Report

**`report.py`**:
- `InstallReport`: namedtuple con conteggi `created`/`skipped`/`merged`/`block`/`error` +
  `first_error_step` + lista artefatti con esiti. Rendering JSON (`schema: install.report/1`) e
  umano.

## Interfaccia

```python
# Esperienza d'uso (da sertor o sertor-flow)

from sertor_install_kit import (
    Artifact, ArtifactKind, WriteStrategy, ArtifactOutcome, Outcome,
    execute_plan, log_event, InstallerError
)

# Costruire il piano (il consumatore lo fa, il kit non conosce i dettagli)
# `target_rel` è SEMPRE relativo a --target (mai assoluto, mai `..`).
plan = [
    Artifact(
        kind=ArtifactKind.FILE,
        source=".claude/skills/my-skill/skill.md",
        target_rel=".claude/skills/my-skill/skill.md",
        strategy=WriteStrategy.CREATE_IF_ABSENT,
    ),
    Artifact(
        kind=ArtifactKind.SETTINGS_MERGE,
        source=".claude/settings.json",
        target_rel=".claude/settings.json",
        strategy=WriteStrategy.MERGE_DEDUP,
    ),
    # …
]

# Eseguire (il consumatore fornisce apply)
def apply_artifact(artifact: Artifact) -> ArtifactOutcome:
    # Il consumatore sa come leggere gli asset e come scrivere
    # (legge da resources, chiama merge_*, write_marker_block, …)
    try:
        # apply logic
        return ArtifactOutcome(target_rel=artifact.target_rel, outcome=Outcome.CREATED)
    except InstallerError as e:
        log_event(logging.ERROR, operation="install", error=str(e))
        raise

report = execute_plan(plan, apply_artifact)
print(report)  # JSON o umano
```

## Proprietà

- **Stdlib-only:** `logging`, `json`, `pathlib`, `importlib.resources`. Nessuna dipendenza
  esterna.
- **Host-agnostico (Principio X):** nessun riferimento a Sertor, progetti ospiti, linguaggi,
  path assoluti. Tutto parametrico.
- **Deterministico:** niente LLM, niente rete, niente I/O casuale. Testabile con mock semplici.
- **Non distruttivo:** merge intelligente, skip se esiste, never overwrite senza `REPLACE`
  esplicito.
- **Idempotente:** rieseguire il piano produce lo stesso esito.

## Backlink

- [[sertor-installer]] — il consumatore RAG+wiki che dipende dal kit + core.
- [[sertor-flow]] — il consumatore governance che dipende dal kit (non dal core).
- [[deterministic-vs-judgment]] — il kit è la metà meccanica pura.
- [[thin-consumer]] — `sertor` e `sertor-flow` sono thin consumer del kit.
