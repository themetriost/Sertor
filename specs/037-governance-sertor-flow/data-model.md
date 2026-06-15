# Data Model — `sertor-flow`

Entità del dominio dell'installer. Sono **value object puri** (niente SDK), in gran parte **migrati**
dal `sertor_installer` esistente al toolkit condiviso `sertor_install_kit`; le novità sono marcate.

## Entità del toolkit (`sertor_install_kit`) — migrate, riusate da tutti i bundle

### `Artifact` (migrato, invariato)
Unità che l'installer deposita. Campi: `kind: ArtifactKind`, `source: str | None`, `target_rel: str`
(sempre relativa al target; validazione anti path-traversal in `__post_init__`), `strategy:
WriteStrategy`.

### `ArtifactKind` (migrato, **esteso**)
Natura dell'artefatto. Valori già esistenti riusati: `FILE`, `MARKER_BLOCK`, `CONFIG`,
`SETTINGS_MERGE`, `ENV_MERGE`, `MCP_MERGE`, `GITIGNORE_APPEND`, `DEPENDENCIES`, `MCP_REGISTER`,
`STRUCTURE`. **Nuovo per sertor-flow:** `GENERATE_INIT` (genera i file init/integration per-host, D7) —
oppure riuso di `CONFIG` con sorgente diversa (decisione di dettaglio in implementazione; preferito
`CONFIG` se la semantica «genera-da-template-se-assente» basta).

### `WriteStrategy` (migrato, invariato)
Regola di scrittura non distruttiva associata al `kind`: `CREATE_IF_ABSENT`, `MERGE_DEDUP`,
`APPEND_BLOCK`, `INIT_STRUCTURE`, `GENERATE_CONFIG`, `BOOTSTRAP_DEPS`, `MERGE_ENV`, `MERGE_JSON`,
`APPEND_LINES`, `REGISTER_CLI`.

### `Outcome` (migrato, invariato)
Esito di un singolo artefatto: `CREATED`, `SKIPPED`, `MERGED`, `BLOCK`, `ERROR`.

### `ArtifactOutcome` (migrato, invariato)
`target_rel: str`, `outcome: Outcome`, `detail: str | None`.

### `InstallReport` (migrato, **generalizzato**)
Resoconto dell'installazione: `target: str`, `capability: str` (es. `"governance"`), lista di
`ArtifactOutcome`, eventuale `failed_step`. Forma leggibile + serializzazione JSON (FR-018/FR-020).

### `InstallerError` / `ConfigError` (**nuovo**, D3)
Base d'eccezione del kit (sostituisce la dipendenza da `sertor_core.domain.errors`). `ConfigError`
ne è sottoclasse. `execute_plan` cattura `InstallerError` per il fail-fast.

### `CommandRunner` (migrato, invariato)
Astrazione mockabile per invocare comandi esterni (`is_available`, `run`). Per la governance MVP è
**non necessaria** (nessun bootstrap dipendenze / registrazione MCP): resta nel kit per `sertor` (rag).

## Entità nuove di `sertor-flow` (`sertor_flow`)

### `GovernanceProfile` (**nuovo**)
Specifiche host inferite prima della generazione, analogo a `HostProfile` del wiki. Campi:
`target_root: Path`, `assistant: str = "claude"`, `script: str` (inferito dall'OS: `ps` su Windows,
`bash` altrove), `speckit_version: str` (pinnato, es. `"0.8.18"`). Alimenta i template init/integration
(D7). Niente segreti.

### Il «bundle di governance» (concetto, non una classe)
La composizione completa (all-or-nothing) degli asset distribuiti, **derivata** camminando
`assets/claude/**` e `assets/specify/**` + gli asset speciali (starter costituzione, blocco SDLC,
init generati, NOTICE). Il piano (`list[Artifact]`) si **deriva** dalla composizione (FR-005), non da
un conteggio fisso.

## Piano d'installazione governance (ordine canonico)

`build_governance_plan(profile) -> list[Artifact]`:
1. `FILE × N` — tutti i file sotto `assets/claude/**` → `.claude/**` (CREATE_IF_ABSENT) — skill/agenti
   SpecKit (vendored) + requirements + configuration-manager.
2. `FILE × N` — tutti i file sotto `assets/specify/**` → `.specify/**` (CREATE_IF_ABSENT) — templates,
   scripts (ps+bash), extensions/git, workflows.
3. `CONFIG` (starter costituzione) → `.specify/memory/constitution.md` (CREATE_IF_ABSENT, skip se
   esiste — FR-014).
4. `GENERATE_INIT` × M → `.specify/init-options.json`, `.specify/integration.json`,
   `.specify/integrations/*.manifest.json` (generati da `GovernanceProfile`, D7).
5. `FILE` (attribuzione) → `.specify/NOTICE` (+ `LICENSES/spec-kit-MIT.txt`) — REQ-022.
6. `MARKER_BLOCK` (blocco rituale SDLC) → `CLAUDE.md` (marker SDLC distinti — D4).

> **Escluso dal piano** (DA-e): lo stato runtime `.specify/feature.json` non è un asset.

## Invarianti / regole di validazione

- **Non distruttività (FR-014/016):** ogni `target_rel` relativa, no `..`; `FILE`=CREATE_IF_ABSENT
  (esiste→SKIPPED); init generati = skip se presenti; `CLAUDE.md`=blocco a marker (presente→SKIPPED).
- **Idempotenza (FR-017):** seconda esecuzione → tutti SKIPPED, zero modifiche.
- **Derivazione del piano (FR-005):** la lista artefatti riflette il contenuto degli asset (test:
  aggiungere un asset cambia il piano).
- **Indipendenza dal core (FR-002):** nessun simbolo importato da `sertor_core` in `sertor_flow` né nel
  kit (test: import isolato del kit/sertor-flow senza sertor_core installabile, o guardia statica
  sugli import).
- **Attribuzione (FR-022/SC-007):** `NOTICE`/licenza MIT presenti nel pacchetto e depositati sull'ospite.
- **Generato valido (D7):** i file init/integration generati devono essere consumabili dalle skill
  SpecKit (stesso schema di `init-options.json`/`integration.json` reali).
