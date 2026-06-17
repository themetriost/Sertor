# Research — Ciclo di vita dell'installer (upgrade e uninstall)

**Feature**: `048-lifecycle-installer` (FEAT-008, epica `sertor-cli`) | **Date**: 2026-06-17

**Scopo**: risolvere le 4 ambiguità di *come* segnalate dalla fase `specify` (§Assumptions della spec,
ultimo punto). Le 4 decisioni di prodotto (Q1–Q4) sono già chiuse nei requisiti §10 e **non** si
riaprono qui. Ogni decisione è ancorata al codice reale dei pacchetti installer
(`packages/sertor-install-kit/`, `packages/sertor/src/sertor_installer/`,
`packages/sertor-flow/src/sertor_flow/`) e alla procedura manuale `docs/install.md §10.1/§10.2`.

---

## Stato di partenza (ground truth)

Il kit espone oggi un meccanismo **solo additivo/creativo**:

- `Artifact(kind, source, target_rel, strategy)` + `ArtifactKind` {FILE, SETTINGS_MERGE, MARKER_BLOCK,
  STRUCTURE, CONFIG, DEPENDENCIES, ENV_MERGE, MCP_MERGE, GITIGNORE_APPEND, MCP_REGISTER} +
  `WriteStrategy` {CREATE_IF_ABSENT, MERGE_DEDUP, APPEND_BLOCK, INIT_STRUCTURE, GENERATE_CONFIG,
  BOOTSTRAP_DEPS, MERGE_ENV, MERGE_JSON, APPEND_LINES, REGISTER_CLI}
  (`artifacts.py`).
- `Outcome` {CREATED, SKIPPED, MERGED, BLOCK, ERROR} (`artifacts.py`); `InstallReport` aggrega i conteggi
  `created/skipped/merged/block/errors` e rende umano + JSON `install.report/1` (`report.py`).
- `execute_plan(plan, apply, target, capability, assistant)`: loop fail-fast no-rollback a callback
  (`executor.py`).
- Primitive additive: `write_marker_block` (`claude_md.py`), `merge_settings`, `merge_env`, `merge_mcp`,
  `append_gitignore` (con `RUNTIME_IGNORES`), `MCP_REGISTER` via `claude mcp add-json` (`install_rag.py`).
- I plan-builder canonici: `build_install_plan` (wiki, `install_wiki.py`), `build_rag_plan`
  (`install_rag.py`), `build_governance_plan` (`install_governance.py`, `sertor-flow`). Tutti
  parametrici sull'`AssistantProfile` (`assistant.py`) che è la **fonte unica** dei container
  per-assistente di ogni `Surface`.

**Non esiste oggi nessuna operazione inversa** (rimozione, sovrascrittura controllata, de-registrazione).
La procedura manuale è documentata in `docs/install.md §10.2` (tabella A/B/C/D + script PowerShell con
regex sui marker). Questa feature **produttivizza** quello script come comandi `upgrade`/`uninstall`,
una volta sola nel kit.

---

## D1 — Forma delle primitive inverse nel toolkit (ambiguità 1)

**Domanda**: nuove `WriteStrategy`/`ArtifactKind` "inverse" (UPDATE_IF_CHANGED, REMOVE, REMOVE_MARKER,
REMOVE_LINES, DEREGISTER_CLI) **vs** handler dedicati che derivano l'operazione inversa dal plan
d'install esistente.

### Opzioni considerate

- **(A) Nuovi `ArtifactKind`/`WriteStrategy` inversi.** Si aggiungono enum-member e si costruiscono
  *piani inversi* fatti di artefatti "rimuovi-questo". Pro: simmetrico con l'install. Contro:
  **raddoppia la tassonomia** (ogni kind d'install vorrebbe il suo gemello inverso), introduce stati
  ambigui (un `Artifact` REMOVE non ha `source`), e soprattutto **duplica la fonte di verità** — il
  plan d'install e il plan inverso possono divergere. Viola III (YAGNI: 5 enum-member nuovi) e l'intento
  DRY del kit.
- **(B) Una `Operation` (verbo) ortogonale + handler `apply` per-verbo, sullo STESSO plan d'install.**
  Il plan-builder resta UNO (quello d'install, già fonte di verità degli artefatti). Si introduce un
  **verbo d'operazione** (`INSTALL` | `UPGRADE` | `UNINSTALL`) passato all'esecutore; per ogni
  `ArtifactKind` esiste **una funzione inversa nel kit** che sa, dato l'artefatto e il verbo, cosa fare
  (aggiornare/rimuovere/de-registrare). Pro: una sola tassonomia, una sola lista di artefatti per
  capacità, nessuna divergenza possibile per costruzione (SC-010); le primitive inverse sono funzioni
  pure stdlib nel kit (NFR-07). Contro: l'esecutore deve sapere il verbo (cambio di firma, additivo e
  retrocompatibile via default `INSTALL`).

### Decisione — (B), con queste forme concrete

1. **Nuovo enum `LifecycleOp`** nel kit (`artifacts.py`): `INSTALL` (default), `UPGRADE`, `UNINSTALL`.
   È il verbo ortogonale agli `ArtifactKind`; **nessun nuovo `ArtifactKind`/`WriteStrategy` inverso**
   (D1 chiude le 5 strategie ipotizzate nei requisiti §7 "Dipendenze" → **scartate**).

2. **Estendere `Outcome`** con `UPDATED = "updated"` e `REMOVED = "removed"` (data-model §Entità della
   spec lo richiede esplicitamente). `InstallReport` guadagna i conteggi `updated`/`removed` e li rende
   in umano + JSON (schema `install.report/1` **esteso, non un secondo schema** — NFR-06).

3. **Funzioni inverse pure nel kit**, una per famiglia di artefatto (stdlib-only):
   - `remove_marker_block(path, marker_start, marker_end) -> Outcome` — toglie SOLO il blocco delimitato,
     preserva il resto byte-per-byte; marker assenti → no-op osservabile (`SKIPPED`). È l'inverso esatto
     di `write_marker_block`.
   - `update_marker_block(path, content, marker_start, marker_end) -> Outcome` — se il contenuto dentro i
     marker differisce dal bundle, lo sostituisce (fuori dai marker invariato → `UPDATED`); uguale →
     `SKIPPED`; assente → delega a `write_marker_block` (→ `BLOCK`).
   - `remove_settings_entries(path, fragment) -> (Outcome, detail)` — toglie SOLO le voci di hook il cui
     `command` compare nel fragment Sertor; se il file resta senza hook Sertor-owned ma con altri,
     preserva; se diventa vuoto/solo-Sertor, comportamento documentato (vedi sotto). Inverso di
     `merge_settings` (riusa `_inner_commands`).
   - `remove_gitignore_lines(path, lines=RUNTIME_IGNORES) -> (Outcome, detail)` — toglie SOLO le linee
     note + l'header `_HEADER`; altre linee invariate. Inverso di `append_gitignore`.
   - `remove_mcp_server(path, server_name, root_key) -> (Outcome, detail)` — toglie SOLO la voce
     `sertor-rag`; se era l'unica → rimuove il file (FR-025); altri server preservati. Inverso di
     `merge_mcp`.
   - `deregister_mcp_client(runner, server_name) -> Outcome` — `claude mcp remove sertor-rag`; client
     assente sul PATH → `McpRegistrationError` con comando manuale (FR-024 / US3 scenario 2). Inverso di
     `_apply_mcp_register`.
   - `update_file_if_changed(dest, content) -> Outcome` — confronta byte; differente → sovrascrive
     (`UPDATED`); uguale → `SKIPPED`; assente → crea (`CREATED`). Per gli asset standalone (FILE).
   - `remove_path(dest) -> Outcome` — rimuove file o albero (`.sertor/`); assente → `SKIPPED`. Per i
     tipi A/B.

4. **L'esecutore diventa verbo-aware** ma in modo *thin*: `execute_plan(plan, apply, ..., op=INSTALL)`
   passa `op` al callback `apply(artifact, op)` (o, equivalentemente, il consumer chiude su `op`). Il
   loop fail-fast no-rollback resta invariato. Il `capability`/`assistant` del report restano.

**Perché (B) e non (A):** (B) tiene **una sola tassonomia** e **una sola lista di artefatti per
capacità** (il plan-builder d'install). Le funzioni inverse sono il duale 1:1 delle primitive additive
già nel kit — *stesso file, stessa logica di riconoscimento* (marker string note, `_inner_commands`,
`RUNTIME_IGNORES`, `server_name`). Questo rende **impossibile la divergenza** richiesta da SC-010/FR-053
e tiene la tassonomia piccola (III). (A) avrebbe creato un universo parallelo di artefatti inversi da
mantenere allineato a mano — esattamente il rischio R-05.

---

## D2 — Dove derivare i plan di upgrade/uninstall (ambiguità 2)

**Domanda**: dove/come derivare i plan inversi dai plan-builder esistenti (`build_rag_plan`,
`build_install_plan`, `build_governance_plan`) come UNICA fonte di verità.

### Decisione

**Riusare lo STESSO plan-builder d'install, percorrendolo con il verbo.** Non esiste un secondo
plan-builder: il plan d'install (lista ordinata di `Artifact`) È la dichiarazione canonica di "cosa
appartiene a questa capacità per questo assistente". Upgrade e uninstall costruiscono **lo stesso plan**
(`build_rag_plan(profile, assistant=...)`, ecc.) e lo eseguono col verbo corrispondente; il dispatch
`apply(artifact, op)` mappa ogni `ArtifactKind` alla sua funzione inversa.

Conseguenze concrete:

- **Upgrade.** Per ogni artefatto del plan: FILE → `update_file_if_changed`; MARKER_BLOCK →
  `update_marker_block`; MCP_MERGE/MERGE_JSON, SETTINGS_MERGE, GITIGNORE_APPEND, ENV_MERGE →
  **idempotenti additivi già esistenti** (upgrade non sovrascrive valori env, NFR-05; aggiunge solo
  chiavi/server/linee mancanti). DEPENDENCIES → `uv add` idempotente (già nel plan). Poi la **fase
  obsoleti** (D3): tutto ciò che sta su disco sotto un path Sertor-owned ma NON è prodotto dal plan
  corrente viene rimosso (`remove_path` / `remove_mcp_server` / `remove_marker_block`).
- **Uninstall.** Per ogni artefatto del plan si applica la sua funzione inversa (A/B → `remove_path`;
  C marker → `remove_marker_block`; C settings → `remove_settings_entries`; C gitignore →
  `remove_gitignore_lines`; D → `deregister_mcp_client` o `remove_mcp_server`). Il `.sertor/` (tipo A)
  è rimosso in blocco (FR-030) anche se nel plan compare come singolo `DEPENDENCIES`/`ENV_MERGE`: il
  diff a posteriori dei path Sertor-owned (D3) marca `.sertor/` come radice posseduta.
- **Cambio assistente (US5/FR-016).** Si costruisce il plan per il **nuovo** assistente e il set di
  path Sertor-owned per il **vecchio**; gli artefatti del vecchio non presenti nel nuovo plan e non
  condivisi (non nell'intersezione dei path) sono obsoleti → rimossi. Il diff a posteriori (D3) è
  esattamente il meccanismo.

**Collocazione del codice.** Le primitive inverse e l'esecutore verbo-aware vivono **una volta nel kit**
(`sertor-install-kit`, FR-053/FR-043). I consumer (`sertor_installer`, `sertor_flow`) aggiungono solo:
(a) il dispatch `apply(artifact, op)` esteso ai verbi UPGRADE/UNINSTALL (gli handler inversi chiamano le
funzioni del kit); (b) i comandi CLI. **Nessuna primitiva di rimozione vive nei consumer.**

---

## D3 — Forma della dichiarazione statica dei path Sertor-owned (ambiguità 3)

**Domanda**: forma concreta della lista statica di path Sertor-owned per il diff a posteriori (Q2),
senza manifest persistente (FR-017).

### Vincolo

Deve coprire: (1) identificare gli **obsoleti** in upgrade; (2) garantire che `remove_path` non tocchi
mai nulla fuori dal perimetro Sertor (FR-013/FR-031/FR-050); (3) supportare il cambio-assistente
(intersezione vecchio/nuovo). La lista è **piccola e co-localizzata coi plan-builder** (assunzione dei
requisiti §7).

### Decisione — funzione `sertor_owned_paths(capability, assistant) -> SertorOwnedPaths`

Una **funzione pura per-capacità**, accanto a ciascun plan-builder (consumer), che ritorna un value
object con due insiemi dichiarati staticamente:

```text
SertorOwnedPaths(
    owned_dirs:  tuple[str, ...]   # alberi interamente Sertor (rimuovibili in blocco) — es. ".sertor",
                                   #   "wiki" (solo se --purge-wiki), ".claude/skills/wiki-author"
    owned_files: tuple[str, ...]   # singoli file standalone Sertor-owned — es. il hook .ps1, i
                                   #   prompt/agent renderizzati
    shared_edits: tuple[SharedEdit, ...]  # file CONDIVISI con porzione Sertor: (path, kind, key)
                                   #   kind ∈ {MARKER, SETTINGS, GITIGNORE, MCP_ENTRY}
)
```

- I path provengono **dalle stesse costanti già nel codice** (`_RAG_HOOK_TARGET`,
  `_CLAUDE_MD_TARGET`, `MARKER_START_RAG/SDLC/WIKI`, `RUNTIME_IGNORES`, i target risolti
  dall'`AssistantProfile`). La funzione **non duplica** valori: li deriva dal plan-builder + profilo,
  classificandoli in dir/file/shared. È la "vista statica" del plan, non una seconda sorgente.
- **Diff a posteriori (obsoleti):** `obsolete = (path su disco sotto owned_dirs/owned_files del set
  storico/cross-assistant) − (path prodotti dal plan corrente)`. Un path che esiste su disco ma è in
  `owned_*` e NON nel plan corrente → obsoleto. Un path **non in `owned_*`** → mai rimosso, avviso
  (FR-013).
- **Cross-assistant:** `sertor_owned_paths(cap, old) ∪ sertor_owned_paths(cap, new)` dà l'unione; gli
  obsoleti del vecchio = `owned(old) − owned(new) − plan(new)`; i path comuni (intersezione) restano
  (FR-016).
- **Niente manifest:** il "cosa era installato" è ri-derivato dal codice ad ogni run (la lista
  statica + scansione del disco). Per il cambio assistente NON serve sapere quale fosse il vecchio: si
  passa `--assistant` (nuovo) e l'upgrade considera obsoleti gli `owned_*` degli **altri** assistenti
  presenti sul disco. Questo soddisfa US5 senza stato persistente.

**Manutenzione (rischio R-02/R-06).** `sertor_owned_paths` vive **accanto** al plan-builder, e un test
di invariante (`test_owned_paths_cover_plan`) verifica che **ogni** `target_rel` prodotto dal plan
ricada in `owned_dirs ∪ owned_files ∪ shared_edits`: se un domani si aggiunge un artefatto al plan
senza dichiararne la proprietà, il test rompe. Questo è il guard-rail che tiene la lista aggiornata
(sostituisce il manifest col costo di un test).

---

## D4 — Conferma interattiva vs `--yes` nei contesti non interattivi (ambiguità 4)

**Domanda**: comportamento deterministico della conferma per `--purge-wiki` quando non c'è un TTY
(CI), e in generale.

### Vincolo

FR-027/028: `--purge-wiki` non rimuove il wiki senza consenso esplicito; mostra n. pagine + dimensione;
richiede conferma interattiva **o** `--yes`; **non** combinabile con `--dry-run`. La spec (US6 scenario
3) e l'edge case "purge senza conferma" impongono determinismo.

### Decisione — regola deterministica, mai prompt-che-blocca-la-CI

1. **`--purge-wiki` SENZA `--yes`:**
   - Se **stdin è un TTY** (`sys.stdin.isatty()`): mostra il conteggio (pagine + byte approssimati) e
     chiede conferma interattiva (`y/N`); risposta diversa da sì → **niente cancellazione**, il resto
     dell'uninstall wiki procede (la dir wiki è preservata), exit `0`.
   - Se **stdin NON è un TTY** (CI, pipe): **NON** si blocca su un prompt. La cancellazione **non
     avviene** (default sicuro), si emette un avviso azionabile («wiki preservato: passa `--yes` per
     confermare la rimozione in un contesto non interattivo»), il resto dell'uninstall procede, exit
     `0`. *(Conservativo: in dubbio, NON si distrugge dato utente — coerente con FR-050/R-03.)*
2. **`--purge-wiki --yes`:** consenso già dato → mostra comunque il conteggio (informativo, SC-009),
   poi rimuove la dir wiki (`remove_path`), outcome `removed`.
3. **`--purge-wiki --dry-run`:** **rifiutato** (usage error, exit `2`) — FR-028 esplicito ("non
   combinabile"). Messaggio azionabile.
4. **Ambito del flag:** `--purge-wiki` ha senso solo per la capacità `wiki` (e per l'aggregato che
   include wiki). Su `uninstall rag`/`governance` è ignorato/rifiutato come usage error.

**Perché:** rende il comando **deterministico e CI-safe** (nessun hang su prompt in pipeline) senza mai
sacrificare la protezione del dato (R-03): il default in assenza di TTY-conferma o `--yes` è
*preservare*. È la stessa filosofia dei merge additivi (in dubbio non distruggere).

---

## Allineamento ai principi (sintesi)

- **III YAGNI:** una sola tassonomia (`LifecycleOp` verbo + 2 nuovi `Outcome`), niente kind inversi;
  funzioni inverse = duale 1:1 delle additive esistenti. Manifest scartato (Q2 già deciso).
- **IV errori espliciti:** `--purge-wiki --dry-run` → usage error; client MCP assente →
  `McpRegistrationError` con fallback manuale; obsoleto fuori perimetro → avviso, non crash.
- **VI idempotenza/non-distruttività:** re-run stabile (uninstall su pulito = tutti `skipped`); upgrade
  su allineato = `0 updated`; rimozione SOLO di porzioni Sertor nei file condivisi (byte-per-byte
  altrove); install≠run (mai indicizza, FR-051).
- **IX osservabilità:** `log_event(operation="upgrade"/"uninstall", capability, counts)` a fine
  operazione (FR-007), schema report esteso, niente segreti nel report (FR-053).
- **X host-agnostico:** path/marker via `AssistantProfile` + costanti, nessuna assunzione sull'ospite;
  opera solo nella `--target`.
- **XI consumo via vehicles:** i comandi sono nei vehicles CLI (`sertor`, `sertor-flow`); non importano
  `sertor_core` a runtime (l'uninstall wiki conta pagine via filesystem stdlib, non via la libreria).
  La fase wiki d'install tocca `sertor-core` solo in `_apply_structure` (boundary già wrappato); la
  rimozione del wiki è pura `remove_path`, nessun import del core.
- **`sertor-flow` non dipende da `sertor-core`/`sertor` (FR-045/FR-055):** le primitive inverse stanno
  nel kit stdlib-only; `sertor-flow` le consuma come già fa per le additive.
