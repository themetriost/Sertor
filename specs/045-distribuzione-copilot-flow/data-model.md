# Data Model — Distribuzione governance su Copilot (FEAT-009)

Entità toccate/aggiunte. Riuso massimo del seam FEAT-007. Tutto stdlib; nessun import di `sertor-core`.

## §1. Riuso da FEAT-007 (sertor-install-kit)

- **`AssistantId`** (`claude`/`copilot`), **`Surface`** (`INSTRUCTION_BLOCK`/`COMMAND`/`AGENT`/…),
  **`AssistantProfile`** (mappa Surface → contenitore per assistente). Invariati: questa feature li
  **consuma**. Per la governance le Surface rilevanti sono `INSTRUCTION_BLOCK` (blocco SDLC), `COMMAND`
  (skill `requirements`), `AGENT` (`requirements-analyst`, `configuration-manager`).
- **`surfaces.py` (renderer)**: **spostato** da `packages/sertor` al kit → fonte unica per il reso
  prompt-file/custom-agent, condiviso `sertor`↔`sertor-flow`.

## §2. `GovernanceProfile` (esistente — esteso)

Ha **già** il campo `assistant` (usato da `generate` per gli init file). Estensione: `assistant` ora
guida **anche** (a) il targeting delle superfici Sertor-authored via `AssistantProfile` e (b) il lancio
di spec-kit (`--ai <assistant>`). Aggiunge il riferimento alla **versione spec-kit pinnata** (config, non
hardcoded sparso — Principio VIII). `script` (`ps`/`sh`) già presente → passato a `specify init`.

## §3. `SpeckitLaunch` (nuovo — `sertor-flow/speckit_launch.py`)

Rappresenta l'**ottenimento di SpecKit lanciando il suo installer** (sostituisce il vendoring). Non un
value-object di dominio ma un'operazione confinata:
- **Input:** `assistant`, `script`, versione pinnata, `target_root`, `CommandRunner` (iniettato).
- **Effetto:** esegue `specify init` per l'assistente → deposita comandi/agenti SpecKit + `.specify/`.
- **Verifica:** controlla che il layout atteso per l'assistente esista; altrimenti errore.
- **Esiti:** `created` (lanciato), `skipped` (già presente → idempotenza), `error` (assente/fallito →
  `InstallerError`, fail-fast).
- **Confine:** unico punto che conosce il comando spec-kit; dietro `CommandRunner` (test = mock, niente
  rete). **Non** introduce dipendenza da `sertor-core`.

## §4. Plan della governance (rivisto — `build_governance_plan(profile)`)

Ordine canonico **dopo** il refactor:
1. **SpeckitLaunch** — ottiene comandi/agenti SpecKit + `.specify/` per l'assistente (era: FILE×N
   vendorati + `specify/**`).
2. **AGENT × N** Sertor-authored (`requirements-analyst`, `configuration-manager`) → resi via
   `AssistantProfile`.
3. **COMMAND** skill `requirements` → reso via `AssistantProfile`.
4. **CONFIG** costituzione-starter (assistant-agnostic, create-if-absent).
5. **CONFIG/GENERATE_CONFIG × M** init/integration generati (già per-assistant via `generate`).
6. **INSTRUCTION_BLOCK** blocco rituale SDLC → `CLAUDE.md` (claude) o `.github/copilot-instructions.md`
   (copilot), marker `SERTOR:SDLC-RITUAL`, idempotente.

I FILE Sertor-authored non sono più cablati su `.claude/...`: i target vengono dall'`AssistantProfile`.
NOTICE/LICENSE di spec-kit **rimossi** dal bundle (l'attribuzione viaggia con l'output di `specify
init`); resta eventuale NOTICE per gli asset Sertor-authored se necessario.

## §5. `ArtifactKind` / esiti (riuso)

Si riusano `FILE`/`MARKER_BLOCK`/`CONFIG` esistenti del kit + il nuovo step di **launch** (operazione via
`CommandRunner`, non una nuova `ArtifactKind` di scrittura-file). `InstallReport` espone l'**assistente
target** e l'esito del launch; i **gap** dichiarati esplicitamente (FR-011).
