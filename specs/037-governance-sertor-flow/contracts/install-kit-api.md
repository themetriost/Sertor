# Contract — Toolkit condiviso `sertor_install_kit` (`install-kit/1`)

Il seam tra `sertor` (wiki/rag) e `sertor-flow` (governance). È il **motore di installazione** estratto,
**senza dipendenza da `sertor-core`** (vincolo cardine, FR-002/NFR-1/NFR-2).

## Superficie pubblica (riusata da entrambi i consumatori)

### Tipi (da `sertor_install_kit.artifacts`)
`Artifact`, `ArtifactKind`, `WriteStrategy`, `Outcome`, `ArtifactOutcome` — invariati rispetto
all'odierno `sertor_installer.artifacts`.

### Errori (da `sertor_install_kit.errors`)
- `InstallerError(Exception)` — base degli errori di dominio del kit.
- `ConfigError(InstallerError)` — input/configurazione non valida.

### Report (da `sertor_install_kit.report`)
`InstallReport(target, capability)` con `add(outcome)`, `failed_step`, resa umana + `render_json()`
(metodo esistente, **non** rinominato — F1). `capability` è argomento obbligatorio (default `"wiki"`
rimosso — F4).

### Asset (da `sertor_install_kit.resources`)
`asset_path(rel)`, `read_asset_text(rel)`, `iter_asset_dir(rel)` — **parametrizzati sull'anchor del
pacchetto chiamante** (il kit deve poter leggere gli asset di `sertor` *o* di `sertor-flow`):
la firma accetta l'anchor/package del consumatore (es. `iter_asset_dir(anchor, rel)`), oppure il
consumatore passa un `Traversable` radice. *(Dettaglio risolto in implementazione; requisito: nessun
hardcoding di `sertor_installer` come anchor.)*

### Merge non distruttivi
`merge_settings(path, fragment)`, `merge_env(path, rendered)`, `merge_mcp(path, entry)`,
`append_gitignore(path)` — additivi, dedup, mai sovrascrivono valori utente (FR-016).

### Blocco a marker (da `sertor_install_kit.claude_md`) — **generalizzato (D4)**
`write_marker_block(path, content, marker_start, marker_end) -> Outcome`
- assente → crea con solo il blocco → `BLOCK`
- presente, marker assenti → append (separatore) → `BLOCK`
- presente, marker presenti → invariato → `SKIPPED`
- preservazione byte-per-byte fuori dai marker.
- `sertor`(wiki) passa i marker `SERTOR:WIKI-RITUAL`; `sertor-flow` passa `SERTOR:SDLC-RITUAL`.

### Esecutore (da `sertor_install_kit.executor`) — **generalizzato (D5)**
`execute_plan(plan: list[Artifact], apply: Callable[[Artifact], ArtifactOutcome]) -> InstallReport`
- itera il piano in ordine; `apply` (fornita dal consumatore) deposita l'artefatto e ritorna l'esito,
  sollevando `InstallerError` in caso di errore.
- **fail-fast no-rollback:** primo `InstallerError` → esito `ERROR` + `failed_step` + stop; artefatti
  già scritti restano.

### Osservabilità (da `sertor_install_kit.observability`)
`log_event(level, operation, **fields)` — log strutturato su `logging` stdlib, **nessun segreto**
(Principio IX), senza dipendere dal core.

### Comandi esterni (da `sertor_install_kit.command_runner`)
`CommandRunner` (`is_available`, `run`) — usato da `sertor` (rag); non necessario alla governance MVP.

## Invariante di non-regressione (rischio principale del plan)

Dopo l'estrazione, `sertor` (packages/sertor) DEVE restare verde: i suoi `install_wiki`/`install_rag`
importano i simboli dal kit invece che da `sertor_installer.*`, e avvolgono gli errori di
`sertor_core.wiki_tools` in `InstallerError` al boundary (D3). La suite test esistente di
`packages/sertor` è il gate di regressione.
