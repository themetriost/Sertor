# Tasks: Ciclo di vita dell'installer (upgrade e uninstall)

**Feature**: 048-lifecycle-installer · **Branch**: `048-lifecycle-installer`
**Input**: [spec.md](spec.md) · [plan.md](plan.md) · [research.md](research.md) ·
[data-model.md](data-model.md) · [contracts/install-report-extended.md](contracts/install-report-extended.md) ·
[contracts/cli-lifecycle.md](contracts/cli-lifecycle.md)

**Convenzione**: `- [ ] [TaskID] [P?] Descrizione — file toccati`. `[P]` = parallelizzabile
(file/aree diversi, nessuna dipendenza su task incompleti in corso). Ogni task riporta il path
esatto del/dei file modificati o creati.

**Nota tecnica chiave**: il pezzo fondante è la **Fase 2** (tassonomia + funzioni inverse nel kit
+ esecutore verbo-aware): blocca tutte le storie. La regola d'oro del design (D1/D2) è: **un solo
plan-builder per capacità, percorso col verbo**; le primitive inverse vivono **una volta nel kit** e
mai nei consumer.

**Pacchetti toccati**:
- `packages/sertor-install-kit/src/sertor_install_kit/` — sede unica delle primitive (FR-053)
- `packages/sertor/src/sertor_installer/` — consumer RAG/wiki
- `packages/sertor-flow/src/sertor_flow/` — consumer governance/SDLC
- `packages/sertor/tests/`, `packages/sertor-install-kit/tests/`, `packages/sertor-flow/tests/`
- `docs/install.md`

---

## Fase 1 — Setup

> Prereq leggeri: nessun file nuovo, solo verifica che la struttura di test e gli `__init__` siano
> pronti per i nuovi moduli del kit e i nuovi test nei tre pacchetti.

- [x] **T001** [P] Verifica che `packages/sertor-install-kit/tests/unit/` esista e abbia `__init__.py`;
  crea il file `packages/sertor-install-kit/tests/unit/test_lifecycle.py` (stub vuoto con un
  `pass` e il marker `# placeholder — tasks lifecycle`). Idem per
  `packages/sertor-install-kit/tests/integration/__init__.py` se assente.
  _File_: `packages/sertor-install-kit/tests/unit/test_lifecycle.py`

- [x] **T002** [P] Verifica che `packages/sertor/tests/unit/` esista e abbia `__init__.py`; crea gli stub
  `packages/sertor/tests/unit/test_cli_upgrade.py` e
  `packages/sertor/tests/unit/test_cli_uninstall.py` (placeholder). Idem per
  `packages/sertor/tests/unit/test_owned_paths.py`.
  _File_: `packages/sertor/tests/unit/test_cli_upgrade.py`,
  `packages/sertor/tests/unit/test_cli_uninstall.py`,
  `packages/sertor/tests/unit/test_owned_paths.py`

- [x] **T003** [P] Verifica che `packages/sertor-flow/tests/unit/` esista e abbia `__init__.py`; crea gli
  stub `packages/sertor-flow/tests/unit/test_cli_flow_upgrade.py` e
  `packages/sertor-flow/tests/unit/test_cli_flow_uninstall.py` (placeholder).
  _File_: `packages/sertor-flow/tests/unit/test_cli_flow_upgrade.py`,
  `packages/sertor-flow/tests/unit/test_cli_flow_uninstall.py`

- [x] **T004** Esegui `uv run pytest packages/sertor-install-kit/tests packages/sertor/tests
  packages/sertor-flow/tests -q` e verifica che la suite parta verde (stub non falliscono).
  Gate di entrata: nessuna regressione preesistente.
  _Nessun file modificato (verifica)._

---

## Fase 2 — Foundational: tassonomia, primitive inverse, esecutore verbo-aware

> **Bloccante per tutte le storie.** Tutto vive nel kit (stdlib-only). La logica di questo blocco
> NON dipende da `sertor-core`.

### 2A — Tassonomia: `LifecycleOp`, `Outcome` esteso, `InstallReport` esteso

- [x] **T005** Estendi `packages/sertor-install-kit/src/sertor_install_kit/artifacts.py`:
  - Aggiungi `enum LifecycleOp(str, Enum)` con membri `INSTALL = "install"` (default),
    `UPGRADE = "upgrade"`, `UNINSTALL = "uninstall"`.
  - Aggiungi a `Outcome` i membri `UPDATED = "updated"` e `REMOVED = "removed"`.
  - Nessun nuovo `ArtifactKind` né `WriteStrategy` (D1-B). Retrocompatibilità: tutti i
    call-site che usano `Outcome.CREATED/SKIPPED/MERGED/BLOCK/ERROR` restano invariati.
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/artifacts.py`

- [x] **T006** Estendi `packages/sertor-install-kit/src/sertor_install_kit/report.py`:
  - Aggiungi i contatori `updated: int = 0` e `removed: int = 0` a `InstallReport`.
  - Aggiorna `add(outcome)` per incrementare i nuovi contatori su `Outcome.UPDATED/REMOVED`.
  - `render_human()`: la riga di summary include `· N updated · M removed ·`; il titolo riflette
    il verbo (es. `sertor upgrade rag — target: …`).
  - `render_json()`: schema `install.report/1` esteso con `summary.updated` e `summary.removed`
    (additivo, retrocompat: nessun cambio di schema id, NFR-06). Le chiavi valgono `0` nei
    report d'install.
  - `exit_code()`: invariato.
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/report.py`

- [x] **T007** [P] Test di non-regressione e nuovi test tassonomia in
  `packages/sertor-install-kit/tests/unit/test_artifacts.py`:
  - `LifecycleOp.INSTALL` è il membro di default; `str(LifecycleOp.UPGRADE) == "upgrade"`.
  - `Outcome.UPDATED` e `Outcome.REMOVED` esistono e non modificano il valore degli esistenti.
  _File_: `packages/sertor-install-kit/tests/unit/test_artifacts.py`

- [x] **T008** [P] Test estesi in `packages/sertor-install-kit/tests/unit/test_report.py`:
  - `InstallReport` con `updated=2` e `removed=1` rende correttamente in `render_human()` e
    `render_json()`.
  - `render_json()` ha `schema == "install.report/1"` e `summary` con tutte e 7 le chiavi.
  - `add(Outcome.UPDATED)` incrementa `updated`; `add(Outcome.REMOVED)` incrementa `removed`.
  - Report d'install esistente (zero updated/removed): retrocompatibile (le nuove chiavi valgono 0).
  _File_: `packages/sertor-install-kit/tests/unit/test_report.py`

### 2B — Esecutore verbo-aware

- [x] **T009** Estendi `packages/sertor-install-kit/src/sertor_install_kit/executor.py`:
  - Firma aggiornata: `execute_plan(plan, apply, ..., op: LifecycleOp = LifecycleOp.INSTALL)`
    (backward compatible: default `INSTALL` → tutti i call-site esistenti invariati).
  - Il loop fail-fast no-rollback passa `op` al callback: `apply(artifact, op)`.
  - Alternativa thin: il consumer chiude su `op` nella sua `apply` — entrambe le forme sono
    accettabili; usare la forma che minimizza le modifiche ai call-site esistenti.
  - `InstallReport` ora include i campi `updated`/`removed` (da T006).
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/executor.py`

- [x] **T010** [P] Test in `packages/sertor-install-kit/tests/unit/test_executor.py`:
  - `execute_plan(..., op=LifecycleOp.INSTALL)` si comporta come prima (non-regressione).
  - `execute_plan(..., op=LifecycleOp.UNINSTALL)` passa `op` al callback e aggiorna correttamente
    i contatori `removed`.
  - `execute_plan(..., op=LifecycleOp.UPGRADE)` aggiorna `updated`.
  - Il fail-fast no-rollback resta invariato per ogni verbo.
  _File_: `packages/sertor-install-kit/tests/unit/test_executor.py`

### 2C — Primitive inverse pure nel kit (8 funzioni, duali 1:1 delle additive)

- [x] **T011** Estendi `packages/sertor-install-kit/src/sertor_install_kit/claude_md.py` con:
  - `remove_marker_block(path: Path, marker_start: str, marker_end: str) -> Outcome` — toglie
    SOLO il blocco tra i marker; il resto del file invariato byte-per-byte; marker assenti → `SKIPPED`;
    è l'inverso esatto di `write_marker_block`.
  - `update_marker_block(path: Path, content: str, marker_start: str, marker_end: str) -> Outcome`
    — se il contenuto dentro i marker differisce da `content`, lo sostituisce (`UPDATED`); uguale →
    `SKIPPED`; marker assenti → delega a `write_marker_block` (`BLOCK`).
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/claude_md.py`

- [x] **T012** [P] Test in `packages/sertor-install-kit/tests/unit/test_claude_md.py`:
  - `remove_marker_block`: fixture mista (testo utente prima + blocco Sertor + testo utente dopo)
    → solo il blocco sparisce, il resto byte-per-byte invariato.
  - `remove_marker_block`: marker assenti → `SKIPPED`, file invariato.
  - `remove_marker_block`: idempotenza — seconda chiamata su file senza blocco → `SKIPPED`.
  - `update_marker_block`: contenuto differisce → `UPDATED`, fuori-marker invariato.
  - `update_marker_block`: contenuto uguale → `SKIPPED`.
  - `update_marker_block`: marker assenti → `BLOCK` (comportamento di `write_marker_block`).
  _File_: `packages/sertor-install-kit/tests/unit/test_claude_md.py`

- [x] **T013** Estendi `packages/sertor-install-kit/src/sertor_install_kit/settings_merge.py` con:
  - `remove_settings_entries(path: Path, fragment: dict) -> tuple[Outcome, str]` — toglie SOLO
    le voci di hook il cui `command` compare nel fragment Sertor; le altre voci restano; riusa
    `_inner_commands` (logica già presente). Inverso di `merge_settings`.
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/settings_merge.py`

- [x] **T014** [P] Test in `packages/sertor-install-kit/tests/unit/test_settings_merge.py`:
  - Fixture settings con hook Sertor + hook utente → `remove_settings_entries` rimuove solo i
    Sertor-owned, gli altri restano invariati.
  - Settings senza voci Sertor → `SKIPPED`, file invariato.
  - Idempotenza: seconda chiamata → `SKIPPED`.
  _File_: `packages/sertor-install-kit/tests/unit/test_settings_merge.py`

- [x] **T015** Estendi `packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py` con:
  - `remove_gitignore_lines(path: Path, lines: tuple[str, ...] = RUNTIME_IGNORES) -> tuple[Outcome, str]`
    — toglie SOLO le linee note (`RUNTIME_IGNORES`) + l'header Sertor; le altre linee restano.
    Inverso di `append_gitignore`.
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py`

- [x] **T016** [P] Test in `packages/sertor-install-kit/tests/unit/test_gitignore_append.py`:
  - Fixture `.gitignore` con linee Sertor + linee utente → `remove_gitignore_lines` rimuove solo
    le linee Sertor, le linee utente restano invariate.
  - `.gitignore` senza linee Sertor → `SKIPPED`.
  - Robustezza a riformattazione: linee Sertor con whitespace extra → comunque rimosse.
  _File_: `packages/sertor-install-kit/tests/unit/test_gitignore_append.py`

- [x] **T017** Estendi `packages/sertor-install-kit/src/sertor_install_kit/mcp_merge.py` con:
  - `remove_mcp_server(path: Path, server_name: str = "sertor-rag", root_key: str = "mcpServers") -> tuple[Outcome, str]`
    — toglie SOLO la voce del server nominato; se era l'unica → rimuove il file intero (`REMOVED`);
    altri server preservati. Inverso di `merge_mcp`.
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/mcp_merge.py`

- [x] **T018** [P] Test in `packages/sertor-install-kit/tests/unit/test_mcp_merge.py`:
  - MCP con `sertor-rag` + altri server → `remove_mcp_server` rimuove solo `sertor-rag`, altri
    restano.
  - MCP con solo `sertor-rag` → file rimosso, outcome `REMOVED`.
  - MCP senza `sertor-rag` → `SKIPPED`.
  - `root_key` parametrico: funziona sia per `mcpServers` (Claude) sia per `servers` (Copilot).
  _File_: `packages/sertor-install-kit/tests/unit/test_mcp_merge.py`

- [x] **T019** Crea `packages/sertor-install-kit/src/sertor_install_kit/lifecycle.py` con le primitive
  non aggiunte ai file additivi esistenti:
  - `update_file_if_changed(dest: Path, content: bytes | str) -> Outcome` — confronta byte; se
    differente → sovrascrive (`UPDATED`); uguale → `SKIPPED`; assente → crea (`CREATED`).
  - `remove_path(dest: Path) -> Outcome` — rimuove file o albero; assente → `SKIPPED`
    (idempotenza); non tocca nulla fuori da `dest`.
  - `deregister_mcp_client(runner: CommandRunner, server_name: str = "sertor-rag") -> Outcome`
    — esegue `claude mcp remove <server_name>` via `runner`; client assente sul PATH →
    solleva `McpRegistrationError` con comando manuale di fallback (FR-024, US3 sc.2).
  - `execute_lifecycle(plan, owned, apply_fn, op, target, dry_run, capability, assistant)` —
    orchestratore verbo-aware: (1) percorre il plan con `apply_fn(artifact, op)` raccogliendo
    gli esiti; (2) se `op == UPGRADE`: fase obsoleti — scansiona disco per path in
    `owned.owned_dirs ∪ owned.owned_files` non prodotti dal plan corrente → `remove_path`
    (o skip+avviso se path non in `owned_*`, FR-013); (3) se `dry_run=True` non scrive nulla
    (proietta gli esiti). Ritorna `InstallReport` esteso.
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/lifecycle.py` (NUOVO)

- [x] **T020** [P] Test in `packages/sertor-install-kit/tests/unit/test_lifecycle.py`:
  - `update_file_if_changed`: contenuto differisce → `UPDATED`; uguale → `SKIPPED`; file assente
    → `CREATED`.
  - `remove_path`: file esiste → rimosso, `REMOVED`; directory con contenuto → rimossa in blocco,
    `REMOVED`; assente → `SKIPPED`.
  - `remove_path`: idempotenza (seconda chiamata su path assente → `SKIPPED`).
  - `deregister_mcp_client`: runner mockato che simula assenza del client →
    `McpRegistrationError` con messaggio azionabile e comando manuale.
  - `execute_lifecycle` con `dry_run=True`: nessun file scritto (0 byte cambiati su disco),
    report proietta gli esiti attesi.
  - `execute_lifecycle` con `op=UPGRADE`, fase obsoleti: file su disco in `owned_dirs` ma
    assente dal plan → rimosso; path non in `owned_*` → `SKIPPED` + avviso (FR-013).
  _File_: `packages/sertor-install-kit/tests/unit/test_lifecycle.py`

### 2D — Esportazione superficie pubblica del kit

- [x] **T021** Aggiorna `packages/sertor-install-kit/src/sertor_install_kit/__init__.py`:
  riesporta i nuovi simboli pubblici: `LifecycleOp`, `Outcome.UPDATED`, `Outcome.REMOVED`,
  `remove_marker_block`, `update_marker_block`, `remove_settings_entries`,
  `remove_gitignore_lines`, `remove_mcp_server`, `update_file_if_changed`, `remove_path`,
  `deregister_mcp_client`, `execute_lifecycle`.
  _File_: `packages/sertor-install-kit/src/sertor_install_kit/__init__.py`

- [x] **T022** **GATE Foundational**: `uv run pytest packages/sertor-install-kit/tests -q` verde;
  `uv run ruff check packages/sertor-install-kit`. Non procedere alle storie se questo fallisce.
  _Nessun file modificato (verifica)._

---

## Fase 3 — User Story 1: Rimuovere il runtime e gli asset standalone (P1, MVP uninstall)

> **Independent Test (US1)**: su ospite di riferimento con la capacità `rag` installata, eseguire
> `sertor uninstall rag`; verificare che `.sertor/` sia sparita, gli asset standalone Sertor-owned
> rimossi, e il report elenchi ogni artefatto con esito `removed`. Idempotenza: seconda esecuzione →
> tutti `skipped`, exit `0`.

### 3A — `sertor_owned_paths` per `rag` e `wiki` (consumer `packages/sertor`)

- [x] **T023** Aggiungi `sertor_owned_paths(assistant: str) -> SertorOwnedPaths` a
  `packages/sertor/src/sertor_installer/install_rag.py`:
  - Importa (o definisce inline) `SertorOwnedPaths`, `SharedEdit`, `SharedEditKind` dal kit
    (se non già nel kit, aggiungili a `lifecycle.py` o `artifacts.py`).
  - `owned_dirs`: `(".sertor",)` (tipo A — rimosso in blocco, FR-030).
  - `owned_files`: i file standalone Sertor-owned per il profilo assistente (hook `.ps1`,
    eventuali file renderizzati) derivati dalle costanti esistenti (es. `_RAG_HOOK_TARGET`
    risolto via `AssistantProfile`).
  - `shared_edits`: `(SharedEdit("CLAUDE.md", MARKER, "SERTOR:RAG-USAGE"), SharedEdit(".claude/settings.json", SETTINGS, ...), SharedEdit(".gitignore", GITIGNORE, RUNTIME_IGNORES), SharedEdit(".mcp.json", MCP_ENTRY, "sertor-rag"))`
    per il profilo `claude`; analoghi per `copilot`/`copilot-cli` via `AssistantProfile`.
  - I path derivano dalle **stesse costanti** del plan-builder, non da valori hardcoded separati.
  _File_: `packages/sertor/src/sertor_installer/install_rag.py`

- [x] **T024** Aggiungi `sertor_owned_paths(assistant: str) -> SertorOwnedPaths` a
  `packages/sertor/src/sertor_installer/install_wiki.py`:
  - `owned_dirs`: `("wiki", ".claude/skills/wiki-author")` (dir wiki rimossa solo con
    `--purge-wiki`, FR-027 — la funzione dichiara la dir; il gate `--purge-wiki` è nel CLI).
  - `owned_files`: i file wiki standalone per assistente (hook wiki, comandi wiki,
    agente `wiki-curator`, `wiki/wiki.config.toml`).
  - `shared_edits`: `(SharedEdit("CLAUDE.md", MARKER, "SERTOR:WIKI-RITUAL"), SharedEdit(".claude/settings.json", SETTINGS, ...))`.
  _File_: `packages/sertor/src/sertor_installer/install_wiki.py`

- [x] **T025** [P] Test di invariante **`plan ⊆ owned`** in `packages/sertor/tests/unit/test_owned_paths.py`:
  - Per ogni coppia `(capacità, assistente)` tra quelli supportati (`rag`/`wiki` ×
    `claude`/`copilot`/`copilot-cli`): costruisci il plan-builder, raccogli tutti i
    `target_rel`; verifica che ognuno cada in `owned_dirs ∪ owned_files ∪ {e.target_rel for e
    in shared_edits}` (FR-017, D3).
  - Se un `target_rel` del plan non è coperto → il test deve fallire con un messaggio nominante
    l'artefatto non coperto (guard-rail che sostituisce il manifest).
  _File_: `packages/sertor/tests/unit/test_owned_paths.py`

### 3B — Dispatch `apply(artifact, op)` per uninstall RAG/wiki

- [x] **T026** Estendi il callback `apply(artifact, op)` in
  `packages/sertor/src/sertor_installer/install_rag.py` per coprire `op=UNINSTALL`:
  - `FILE` / tipo B standalone → `remove_path(target)`.
  - `MARKER_BLOCK` → `remove_marker_block(target, MARKER_START_RAG, MARKER_END_RAG)`.
  - `SETTINGS_MERGE` → `remove_settings_entries(target, fragment)`.
  - `GITIGNORE_APPEND` → `remove_gitignore_lines(target)`.
  - `MCP_MERGE` (scope `project`) → `remove_mcp_server(target, "sertor-rag", root_key)`.
  - `MCP_REGISTER` (scope `local`) → `deregister_mcp_client(runner, "sertor-rag")`.
  - `ENV_MERGE` / `DEPENDENCIES` — coperti dalla rimozione in blocco di `.sertor/`; il dispatch
    li ignora (o li marca `SKIPPED`) poiché `.sertor/` è rimosso come `owned_dir`.
  - Per `op=INSTALL`: comportamento attuale invariato (non-regressione, NFR-3).
  _File_: `packages/sertor/src/sertor_installer/install_rag.py`

- [x] **T027** Estendi analogamente il callback `apply` in
  `packages/sertor/src/sertor_installer/install_wiki.py` per `op=UNINSTALL`:
  - `FILE` standalone → `remove_path(target)`.
  - `MARKER_BLOCK` → `remove_marker_block(target, MARKER_START_WIKI, MARKER_END_WIKI)`.
  - `SETTINGS_MERGE` → `remove_settings_entries(target, fragment)`.
  - `STRUCTURE` (dir wiki) → skip (`SKIPPED`) salvo `--purge-wiki` (il flag viene dal CLI,
    non dal dispatch: il dispatch wiki non rimuove `wiki/` di default).
  - Per `op=INSTALL`: comportamento attuale invariato.
  _File_: `packages/sertor/src/sertor_installer/install_wiki.py`

### 3C — Gate non-regressione install

- [x] **T028** **GATE**: `uv run pytest packages/sertor/tests -q` verde dopo T026/T027 (il comportamento
  d'install esistente NON deve cambiare). Punto di verifica prima di procedere al CLI.
  _Nessun file modificato (verifica)._

### 3D — Test US1

- [x] **T029** [P] Test unit uninstall RAG in `packages/sertor/tests/unit/test_cli_uninstall.py`:
  - Mocka il filesystem con fixture: ospite con `.sertor/` presente + asset standalone Sertor-owned
    + file condivisi con porzioni Sertor.
  - `sertor uninstall rag` → report con `.sertor/` in `removed`, asset standalone in `removed`,
    porzioni dei file condivisi rimosse (byte-per-byte).
  - Idempotenza: seconda esecuzione su ospite già pulito → tutti `skipped`, exit `0` (FR-026,
    SC-005).
  - `--dry-run`: nessun file scritto, report proietta esiti `removed` (FR-001/FR-029, SC-006).
  - `--json`: output conforme a `install.report/1` esteso con `summary.removed` > 0
    (FR-002, contratto `install-report-extended.md`).
  _File_: `packages/sertor/tests/unit/test_cli_uninstall.py`

- [x] **T030** [P] Test unit uninstall wiki in `packages/sertor/tests/unit/test_cli_uninstall.py`:
  - `sertor uninstall wiki` senza `--purge-wiki` → dir `wiki/` preservata; altri artefatti wiki
    rimossi (FR-027, US6 sc.1).
  - Ospite senza nessun artefatto wiki → tutti `skipped`, exit `0` (idempotenza, FR-026).
  _File_: `packages/sertor/tests/unit/test_cli_uninstall.py`

---

## Fase 4 — User Story 2: Pulizia dei file condivisi (P1)

> **Independent Test (US2)**: su file condivisi (CLAUDE.md con blocco marker + `.gitignore` con
> linee Sertor + settings con hook Sertor + .mcp.json con sertor-rag) eseguire l'uninstall e
> verificare con confronto byte-per-byte che solo le porzioni Sertor siano sparite.

- [x] **T031** [P] Test in `packages/sertor-install-kit/tests/unit/test_lifecycle.py` (sezione
  file condivisi):
  - Fixture `CLAUDE.md` con blocco `SERTOR:RAG-USAGE` preceduto e seguito da paragrafi utente →
    `remove_marker_block` → solo il blocco rimosso, paragrafi utente invariati byte-per-byte.
  - Fixture `.claude/settings.json` con hook Sertor + hook utente → `remove_settings_entries` →
    solo gli hook Sertor rimossi, hook utente invariati.
  - Fixture `.gitignore` con linee Sertor + regole utente → `remove_gitignore_lines` → solo linee
    Sertor rimosse.
  - Fixture `.mcp.json` con `sertor-rag` + server utente → `remove_mcp_server` → solo voce
    `sertor-rag` rimossa, altri server invariati.
  - Fixture `.mcp.json` con solo `sertor-rag` → file rimosso (`REMOVED`).
  _File_: `packages/sertor-install-kit/tests/unit/test_lifecycle.py`

- [x] **T032** [P] Test edge-case non-distruttività in
  `packages/sertor-install-kit/tests/unit/test_lifecycle.py`:
  - File condiviso senza marker Sertor (utente li ha cancellati) → `remove_marker_block` →
    `SKIPPED`, file invariato (no-op osservabile, non errore).
  - `.gitignore` con linee Sertor riformattate (whitespace diverso) → le linee sono comunque
    rimosse (robustezza alla riformattazione, FR-023).
  - Settings con voci di hook miste (Sertor + non-Sertor) → rimosse solo le Sertor-owned.
  _File_: `packages/sertor-install-kit/tests/unit/test_lifecycle.py`

---

## Fase 5 — User Story 3: De-registrazione MCP dal client (P1)

> **Independent Test (US3)**: su ospite con RAG installato con scope `local`, eseguire `sertor
> uninstall rag`; verificare che la de-registrazione del server MCP venga invocata; se il client
> non è disponibile, verificare che il comando si fermi con messaggio azionabile e fallback manuale.

- [x] **T033** Test de-registrazione MCP in `packages/sertor/tests/unit/test_cli_uninstall.py`:
  - `sertor uninstall rag` con MCP scope `local`: il `CommandRunner` mockato riceve la chiamata
    `claude mcp remove sertor-rag`; outcome `REMOVED` (FR-024, US3 sc.1).
  - `CommandRunner` mockato simula client non disponibile (`McpRegistrationError`) → il comando
    si ferma (fail-fast) con messaggio azionabile che include il comando manuale di fallback
    (FR-024, US3 sc.2).
  - `--dry-run` con MCP scope `local`: nessuna de-registrazione eseguita, report proietta
    `removed` per la voce MCP.
  _File_: `packages/sertor/tests/unit/test_cli_uninstall.py`

---

## Fase 6 — User Story 6: Protezione del wiki e consenso esplicito (P1)

> **Independent Test (US6)**: eseguire `sertor uninstall wiki` senza flag → dir wiki preservata,
> altri artefatti rimossi. Poi eseguire con `--purge-wiki` → mostra conteggio + richiede consenso;
> con `--purge-wiki --yes` → wiki rimosso. Con `--purge-wiki --dry-run` → usage error, exit 2.

- [x] **T034** Implementa la logica `--purge-wiki` in
  `packages/sertor/src/sertor_installer/__main__.py` (nella gestione del sotto-comando
  `uninstall`, con le regole D4 deterministiche):
  - Senza `--purge-wiki`: dir `wiki/` marcata `SKIPPED`; altri artefatti wiki rimossi.
  - `--purge-wiki --dry-run`: usage error (exit `2`) con messaggio azionabile (FR-028, D4).
  - `--purge-wiki --yes`: mostra conteggio pagine + dimensione approssimativa (stdlib `os.walk`),
    poi `remove_path("wiki/")` → `REMOVED`.
  - `--purge-wiki` senza `--yes` + TTY: prompt `y/N`; risposta negativa → wiki preservato,
    exit `0`.
  - `--purge-wiki` senza `--yes` + no TTY (`sys.stdin.isatty() == False`): NON blocca su prompt;
    wiki preservato; avviso azionabile («usa `--yes`»); exit `0`.
  - `--purge-wiki` su `sertor uninstall rag`/`governance`: usage error (flag valido solo per
    `wiki`/aggregato, D4).
  _File_: `packages/sertor/src/sertor_installer/__main__.py`

- [x] **T035** [P] Test `--purge-wiki` in `packages/sertor/tests/unit/test_cli_uninstall.py`:
  - Tutte le combinazioni della tabella D4: senza flag / con `--yes` / senza TTY / `--dry-run`
    (→ exit 2) / su capacità sbagliata (→ exit 2).
  - Verifica che il conteggio pagine mostrato sia corretto (US6 sc.2, SC-009).
  - Verifica che `--purge-wiki --dry-run` produca exit `2` (usage error) senza rimuovere nulla.
  _File_: `packages/sertor/tests/unit/test_cli_uninstall.py`

---

## Fase 7 — User Story 7: Dry-run trasversale (P1)

> **Independent Test (US7)**: eseguire upgrade e uninstall con `--dry-run`; verificare che lo
> stato del filesystem sia immutato (0 byte cambiati) e il report descriva ogni operazione che
> sarebbe stata eseguita con i conteggi proiettati.

- [x] **T036** [P] Test dry-run in `packages/sertor/tests/unit/test_cli_upgrade.py` e
  `packages/sertor/tests/unit/test_cli_uninstall.py`:
  - `sertor upgrade rag --dry-run`: nessun file scritto (0 byte cambiati), report contiene esiti
    proiettati `updated`/`removed`/`skipped` (FR-001/FR-015, SC-006).
  - `sertor uninstall rag --dry-run`: nessuna rimozione o modifica, report descrive cosa sarebbe
    rimosso (FR-001/FR-029, SC-006).
  - In entrambi i casi: `exit_code() == 0` (anche se ci sarebbero errori proiettati → dry-run
    è sempre informativo, non fail-fast su errori proiettati).
  - Verifica che `execute_lifecycle` con `dry_run=True` non chiami le funzioni inverse
    reali (mock conta le chiamate).
  _File_: `packages/sertor/tests/unit/test_cli_upgrade.py`,
  `packages/sertor/tests/unit/test_cli_uninstall.py`

---

## Fase 8 — User Story 4: Upgrade di un'installazione (P2)

> **Independent Test (US4)**: su ospite con versione installata, eseguire `sertor upgrade` con
> bundle che differisce (asset cambiato + blocco marker cambiato + artefatto rimosso dal bundle);
> verificare asset sovrascritto, blocco aggiornato, obsoleto rimosso, artefatti allineati `skipped`.

### 8A — Dispatch `apply(artifact, op)` per upgrade RAG/wiki

- [x] **T037** Estendi il callback `apply(artifact, op)` in
  `packages/sertor/src/sertor_installer/install_rag.py` per coprire `op=UPGRADE`:
  - `FILE` → `update_file_if_changed(target, source_content)`.
  - `MARKER_BLOCK` → `update_marker_block(target, content, MARKER_START_RAG, MARKER_END_RAG)`.
  - `SETTINGS_MERGE` / `GITIGNORE_APPEND` / `MCP_MERGE` / `ENV_MERGE` / `DEPENDENCIES` →
    additivi idempotenti esistenti (FR-014; i valori `.sertor/.env` mai sovrascritti, NFR-05).
  - `MCP_REGISTER` → idempotente (skip se già registrato).
  - `FILE` allineato (contenuto uguale) → `SKIPPED` (FR-014).
  _File_: `packages/sertor/src/sertor_installer/install_rag.py`

- [x] **T038** Estendi analogamente `apply` in
  `packages/sertor/src/sertor_installer/install_wiki.py` per `op=UPGRADE`:
  - `FILE` → `update_file_if_changed`.
  - `MARKER_BLOCK` → `update_marker_block`.
  - `STRUCTURE` → no-op (idempotente, la struttura wiki è già presente).
  - `SETTINGS_MERGE` → additivo idempotente.
  _File_: `packages/sertor/src/sertor_installer/install_wiki.py`

### 8B — CLI sottocomando `upgrade`

- [x] **T039** Aggiungi il sotto-comando `sertor upgrade [wiki|rag|governance ...] [--assistant]
  [--dry-run] [--json]` in `packages/sertor/src/sertor_installer/__main__.py`:
  - Argomento capacità 0..N: nessun argomento → aggregato (tutte: `wiki rag governance`).
  - `governance` → messaggio-puntatore a `sertor-flow upgrade` (nessuna dipendenza tra pacchetti,
    come `sertor install governance`).
  - Wiring a `execute_lifecycle(plan, owned, apply_fn, op=UPGRADE, ...)`.
  - `--dry-run`: delega a `execute_lifecycle` con `dry_run=True`.
  - `--json`: stampa `render_json()`.
  - `log_event(operation="upgrade", capability=..., assistant=..., updated=..., removed=...,
    skipped=..., errors=...)` a fine comando (FR-007).
  _File_: `packages/sertor/src/sertor_installer/__main__.py`

### 8C — Test US4

- [x] **T040** [P] Test unit in `packages/sertor/tests/unit/test_cli_upgrade.py`:
  - Fixture ospite con versione precedente: asset standalone con contenuto vecchio → upgrade →
    `UPDATED`; asset allineato → `SKIPPED` (FR-010/FR-014, SC-003).
  - Blocco marker con contenuto vecchio → upgrade → `UPDATED`; contenuto uguale → `SKIPPED`
    (FR-011).
  - `--dry-run`: nessun file sovrascritto, report proietta `updated`/`skipped` (FR-015, SC-006).
  - `--json`: schema `install.report/1` con `summary.updated > 0` (FR-002).
  - Upgrade su ospite già allineato: `0 updated`, `0 removed`, exit `0` (SC-005, idempotenza).
  _File_: `packages/sertor/tests/unit/test_cli_upgrade.py`

- [x] **T041** [P] Test fase obsoleti in `packages/sertor/tests/unit/test_cli_upgrade.py`:
  - Artefatto su disco sotto path Sertor-owned ma assente dal bundle corrente → rimosso, `REMOVED`
    (FR-012).
  - Path su disco non in `sertor_owned_paths` → `SKIPPED` + avviso (FR-013, edge case US4 sc.5).
  _File_: `packages/sertor/tests/unit/test_cli_upgrade.py`

---

## Fase 9 — User Story 5: Cambio assistente target (P2)

> **Independent Test (US5)**: su ospite installato per assistente A, eseguire `sertor upgrade
> --assistant B`; verificare che gli artefatti specifici di A non condivisi siano rimossi, quelli
> di B aggiunti, e gli artefatti comuni a A e B restino invariati.

- [x] **T042** [P] Test cambio assistente in `packages/sertor/tests/unit/test_cli_upgrade.py`:
  - Simula ospite installato per `claude` (artefatti `claude`-specifici su disco).
  - Esegui upgrade con `--assistant copilot`.
  - Verifica: artefatti specifici di `claude` non condivisi con `copilot` → `REMOVED`;
    artefatti `copilot`-specifici → `CREATED`/`UPDATED`; artefatti comuni → `SKIPPED`
    (FR-016, SC-004).
  - Verifica che `sertor_owned_paths("rag", "claude") ∩ sertor_owned_paths("rag", "copilot")` dia
    i path comuni che non vengono rimossi (invarianza degli artefatti condivisi, FR-016).
  _File_: `packages/sertor/tests/unit/test_cli_upgrade.py`

---

## Fase 10 — User Story 8: Uninstall e upgrade aggregati (P2)

> **Independent Test (US8)**: su ospite con wiki, rag e governance installati, eseguire
> `sertor uninstall` senza argomento; verificare equivalenza con `sertor uninstall wiki rag
> governance` e report aggregato.

- [x] **T043** Implementa l'uninstall aggregato in `packages/sertor/src/sertor_installer/__main__.py`:
  - `sertor uninstall` senza argomento → sequenza `uninstall wiki` + `uninstall rag` +
    messaggio-puntatore `governance` → report aggregato (contatori sommati, `capability="all"`,
    FR-032).
  - Analogamente per `sertor upgrade` senza argomento (aggregato).
  - La forma per-capacità (`sertor uninstall rag`) continua a operare su una sola capacità.
  _File_: `packages/sertor/src/sertor_installer/__main__.py`

- [x] **T044** [P] Test aggregato in `packages/sertor/tests/unit/test_cli_uninstall.py` e
  `packages/sertor/tests/unit/test_cli_upgrade.py`:
  - `sertor uninstall` senza argomento → equivalente a `uninstall wiki rag governance` (FR-032,
    US8 sc.1).
  - `sertor uninstall rag` → solo `rag` rimossa, wiki e governance intatti (US8 sc.2).
  - Report aggregato contiene esiti concatenati e conteggi sommati.
  _File_: `packages/sertor/tests/unit/test_cli_uninstall.py`,
  `packages/sertor/tests/unit/test_cli_upgrade.py`

---

## Fase 11 — User Story 9: Ciclo di vita governance `sertor-flow` (P2)

> **Independent Test (US9)**: su ospite con governance installata, eseguire `sertor-flow upgrade`
> e `sertor-flow uninstall`; verificare stessa semantica di `sertor` (asset aggiornati, blocco
> SDLC rinfrescato, obsoleti rimossi; solo blocco SDLC rimosso dai file condivisi; idempotenza;
> stesso schema di report). Invariante: `sertor-flow` non importa `sertor-core` né `sertor`.

### 11A — `sertor_owned_paths` per governance

- [x] **T045** Aggiungi `sertor_owned_paths(assistant: str) -> SertorOwnedPaths` a
  `packages/sertor-flow/src/sertor_flow/install_governance.py`:
  - `owned_dirs`: `(".specify",)` (da `specify init`, FR-041).
  - `owned_files`: artefatti Sertor-authored installati dalla governance (`requirements-analyst.md`,
    `configuration-manager.md`, skill `requirements`, ecc., derivati dai path nel plan-builder).
  - `shared_edits`: `(SharedEdit("CLAUDE.md", MARKER, "SERTOR:SDLC-RITUAL"),)`.
  - Constitution starter (`CREATE_IF_ABSENT`) → non sovrascritta in upgrade.
  - **Invariante**: `sertor-flow` non dipende da `sertor-core`/`sertor` (FR-045/FR-055).
  _File_: `packages/sertor-flow/src/sertor_flow/install_governance.py`

- [x] **T046** [P] Test di invariante `plan ⊆ owned` per governance in
  `packages/sertor-flow/tests/unit/test_cli_flow_uninstall.py` (o file test dedicato):
  - Per ogni coppia `(governance, assistente)` supportata: ogni `target_rel` del plan-builder
    deve cadere in `owned_dirs ∪ owned_files ∪ {e.target_rel for e in shared_edits}`.
  _File_: `packages/sertor-flow/tests/unit/test_cli_flow_uninstall.py`

### 11B — Dispatch `apply(artifact, op)` per governance e CLI `sertor-flow`

- [x] **T047** Estendi il callback `apply(artifact, op)` in
  `packages/sertor-flow/src/sertor_flow/install_governance.py` per `op=UNINSTALL` e `op=UPGRADE`:
  - `op=UNINSTALL`: `FILE` → `remove_path`; `MARKER_BLOCK` (SDLC) → `remove_marker_block`;
    `CONFIG` costituzione → `SKIPPED` (CREATE_IF_ABSENT, non sovrascrivibile in uninstall).
  - `op=UPGRADE`: `FILE` → `update_file_if_changed`; `MARKER_BLOCK` → `update_marker_block`;
    `CONFIG` costituzione → `SKIPPED` (non sovrascrivere, FR-040).
  - Primitive dal kit (FR-053); **nessun import di `sertor-core`/`sertor`** (FR-045).
  _File_: `packages/sertor-flow/src/sertor_flow/install_governance.py`

- [x] **T048** Aggiungi i sotto-comandi `sertor-flow upgrade [--assistant] [--dry-run] [--json]`
  e `sertor-flow uninstall [--assistant] [--dry-run] [--json]` in
  `packages/sertor-flow/src/sertor_flow/__main__.py`:
  - Stessa semantica di `sertor upgrade`/`uninstall` (FR-042).
  - `runner` iniettabile (per mock di `claude mcp remove` / `specify` nei test).
  - `log_event(operation="upgrade"|"uninstall", capability="governance", ...)` a fine comando.
  - Report conforme allo stesso schema `install.report/1` esteso.
  _File_: `packages/sertor-flow/src/sertor_flow/__main__.py`

### 11C — Test US9

- [x] **T049** [P] Test unit in `packages/sertor-flow/tests/unit/test_cli_flow_upgrade.py`:
  - Upgrade governance: asset Sertor-authored cambiato → `UPDATED`; blocco SDLC in CLAUDE.md
    aggiornato → `UPDATED`; artefatto obsoleto → `REMOVED` (FR-040).
  - Constitution starter → `SKIPPED` (non sovrascritta in upgrade).
  - Upgrade su ospite allineato → `0 updated`, exit `0` (idempotenza, SC-005).
  _File_: `packages/sertor-flow/tests/unit/test_cli_flow_upgrade.py`

- [x] **T050** [P] Test unit in `packages/sertor-flow/tests/unit/test_cli_flow_uninstall.py`:
  - Fixture CLAUDE.md con blocco `SERTOR:SDLC-RITUAL` + contenuto utente → `uninstall` →
    solo il blocco SDLC rimosso, resto invariato (FR-041, US9 sc.2).
  - Ospite senza artefatti governance → tutti `skipped`, exit `0` (FR-044, US9 sc.3).
  - `--dry-run`: nessuna modifica, report proietta esiti (FR-042).
  _File_: `packages/sertor-flow/tests/unit/test_cli_flow_uninstall.py`

- [x] **T051** [P] Test invariante no-core-dependency in
  `packages/sertor-flow/tests/unit/test_cli_flow_uninstall.py` (o nel test esistente
  `test_no_core_dependency.py` se presente):
  - I nuovi percorsi di upgrade/uninstall non introducono import di `sertor_core` né `sertor`
    (scan statico + verifica `pyproject.toml`, FR-045/FR-055, SC-010).
  _File_: `packages/sertor-flow/tests/unit/test_cli_flow_uninstall.py`

---

## Fase 12 — Polish e Cross-Cutting

> Invarianti di sistema, osservabilità, documentazione, gate finale.

- [x] **T052** [P] Aggiorna `docs/install.md` sezione `§10`: sostituisci la procedura manuale come via
  primaria con i comandi automatici (`sertor upgrade`/`sertor uninstall`, `sertor-flow
  upgrade`/`sertor-flow uninstall`); relega lo script PowerShell manuale a "fallback/storico" con
  avviso che è soggetto a drift. Mantieni la tabella A/B/C/D come riferimento dei tipi di artefatto.
  _File_: `docs/install.md`

- [x] **T053** [P] Test di osservabilità in `packages/sertor/tests/unit/test_cli_upgrade.py` e
  `test_cli_uninstall.py`:
  - Al termine di `upgrade` e `uninstall`, `log_event` riceve `operation="upgrade"` o
    `"uninstall"`, con i campi `capability`, `assistant`, `updated`, `removed`, `skipped`,
    `errors` (FR-007, contratto `cli-lifecycle.md §D`).
  - Nessun segreto nei campi dell'evento (FR-053).
  _File_: `packages/sertor/tests/unit/test_cli_upgrade.py`,
  `packages/sertor/tests/unit/test_cli_uninstall.py`

- [x] **T054** [P] Test invarianti di sistema in `packages/sertor/tests/unit/test_cli_uninstall.py`:
  - `FR-051 install≠run`: il percorso di upgrade e uninstall non avvia mai indicizzazione RAG
    (nessun import di `build_indexer`/`build_facade`/engine; verifica statica).
  - `FR-050 non-distruttività`: file con contenuto non-Sertor in posizione Sertor-owned →
    sopravvive invariato tranne le porzioni a marker (es. file con blocco marker Sertor + testo
    proprio → solo blocco rimosso).
  - `FR-033`: l'uninstall opera solo nella `--target` corrente, nessuna operazione cross-utente.
  _File_: `packages/sertor/tests/unit/test_cli_uninstall.py`

- [x] **T055** [P] Test exit code in `packages/sertor/tests/unit/test_cli_uninstall.py` e
  `test_cli_upgrade.py`:
  - Operazione completata (anche se tutto `skipped`) → exit `0` (FR-005).
  - Errore di dominio su un artefatto (fail-fast) → exit `1`, `failed_step` nominato nel report
    (FR-004/FR-005).
  - Usage error (flag incompatibili, es. `--purge-wiki --dry-run`) → exit `2` (FR-005).
  _File_: `packages/sertor/tests/unit/test_cli_upgrade.py`,
  `packages/sertor/tests/unit/test_cli_uninstall.py`

- [x] **T056** [P] Test di simmetria `sertor`/`sertor-flow` (SC-010) in
  `packages/sertor-install-kit/tests/unit/test_lifecycle.py`:
  - Per ogni primitiva inversa del kit (`remove_marker_block`, `remove_settings_entries`,
    `remove_gitignore_lines`, `remove_mcp_server`, `deregister_mcp_client`,
    `update_file_if_changed`, `remove_path`): verifica che la funzione sia importabile dal kit e
    che non esista una copia divergente in `sertor_installer` né in `sertor_flow` (scan import).
  - **0** divergenze d'implementazione tra `sertor` e governance (SC-010).
  _File_: `packages/sertor-install-kit/tests/unit/test_lifecycle.py`

- [x] **T057** **GATE FINALE**: `uv run pytest packages/sertor-install-kit/tests packages/sertor/tests
  packages/sertor-flow/tests -q` tutto verde; `uv run ruff check packages/sertor-install-kit
  packages/sertor packages/sertor-flow`.
  _Nessun file modificato (verifica)._

- [x] **T058** Aggiorna lo stato in `requirements/sertor-cli/epic.md`: FEAT-008 → consegnata (da fare
  al merge su master).
  _File_: `requirements/sertor-cli/epic.md`

---

## Grafo delle dipendenze

```
Fase 1 (T001-T004)
       │
       ▼
Fase 2 Foundational (T005-T022) ─────────────────────────────────┐
       │                                                          │
       ▼                                                          │
Fase 3 US1 (T023-T030) ──────────────────────────────────────┐   │
       │                                                      │   │
       ├──► Fase 4 US2 (T031-T032) [parallela a F5,F6,F7]   │   │
       ├──► Fase 5 US3 (T033)      [parallela]               │   │
       ├──► Fase 6 US6 (T034-T035) [parallela]               │   │
       └──► Fase 7 US7 (T036)      [parallela]               │   │
                                                              │   │
Fase 8 US4 (T037-T041) ← dipende da Fase 3                  │   │
       │                                                      │   │
       ▼                                                      │   │
Fase 9 US5 (T042) ← dipende da Fase 8                        │   │
       │                                                      │   │
Fase 10 US8 (T043-T044) ← dipende da Fase 3+8               │   │
       │                                                      │   │
Fase 11 US9 (T045-T051) ← dipende da Fase 2 (kit); [P vs    │   │
             F8/F9/F10 — tocca pacchetto diverso]            │   │
       │                                                      │   │
       └──────────────────────────────────────────────────── ▼   │
Fase 12 Polish (T052-T058) ← dipende da tutto               └───┘
```

**Ordine vincolante**:
Fase 1 → Fase 2 (GATE T022) → Fase 3 (GATE T028) → Fase 4/5/6/7 (parallele tra loro) →
Fase 8 → Fase 9 → Fase 10 → Fase 11 (parallela a 8/9/10 se il kit è verde) → Fase 12 (GATE T057).

---

## Parallelizzazioni esplicite

- **Fase 1**: T001, T002, T003 in parallelo (file/pacchetti diversi); T004 dopo tutti e tre.
- **Fase 2A**: T007, T008 in parallelo (test distinti, file diversi) dopo T005/T006.
- **Fase 2C**: T011/T012, T013/T014, T015/T016, T017/T018, T019/T020 sono 5 coppie
  (funzione + test) parallelizzabili tra loro (file diversi nel kit).
- **Fase 3**: T023 e T024 in parallelo (install_rag vs install_wiki); T029/T030 in parallelo
  (test su capacità diverse).
- **Fasi 4, 5, 6, 7**: i task di queste fasi (T031-T036) sono tutti paralleli tra loro dopo la
  Fase 3 (file/capacità diversi).
- **Fase 8**: T037 e T038 in parallelo (install_rag vs install_wiki); T040/T041 in parallelo.
- **Fase 11**: può procedere in parallelo con Fasi 8/9/10 perché tocca `sertor-flow` (pacchetto
  distinto), una volta che Fase 2 è verde.
- **Fase 12**: T052, T053, T054, T055, T056 in parallelo (file/aspetti diversi); T057 dopo tutti.

---

## Strategia MVP / incrementale

**MVP (Fase 2 + Fase 3)** — T005 → T030:
Consegna `sertor uninstall rag/wiki` funzionante (rimozione runtime, asset standalone, file
condivisi, idempotenza, dry-run, report). Questo è il taglio minimo di valore (US1 = P1).
Le Fasi 4/5/6/7 sono test di precisione/sicurezza (US2/US3/US6/US7, tutte P1) che completano
la correttezza prima di passare alle storie P2.

**Incremento 1 (Fasi 4-7)** — test di precisione P1 (US2/US3/US6/US7):
Non aggiungono codice nuovo (le primitive del kit coprono già US2/US3), ma verificano la
non-distruttività byte-per-byte, la de-registrazione MCP, la protezione del wiki e il dry-run.
Parallelizzabili tra loro: sono tutti test su codice già scritto.

**Incremento 2 (Fase 8-10)** — upgrade e aggregato P2 (US4/US5/US8):
`sertor upgrade` (US4), cambio assistente (US5), aggregato tutto-in-uno (US8). Dipende da Fase 3
per le funzioni inverse, che riusa per il verbo `UPGRADE`.

**Incremento 3 (Fase 11)** — governance lifecycle P2 (US9):
`sertor-flow upgrade`/`uninstall`. Parallelizzabile con Incremento 2 (pacchetto separato).
Invariante critico: zero dipendenze da `sertor-core`/`sertor`.

**Finish (Fase 12)** — polish, documentazione, gate finale.
