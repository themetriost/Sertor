# Research — Ridurre l'altitude dei blocchi CLAUDE.md + fonte unica «How to invoke» (E10-FEAT-021)

**Feature**: `079-altitude-claude-md` · **Branch**: `079-altitude-claude-md` · **Data**: 2026-06-30

Questa fase risolve gli **ignoti di *come*** (le forche residue DA-D-r1..r4 della spec) e fissa
l'ancoraggio reale (asset, wiring, guardie) verificato via MCP `sertor-rag` + `Read`. Le forche di
*cosa* (DA-1 scope root, DA-2 strategia) sono già **RISOLTE** nella spec e non si riaprono.

> **Nota dogfooding/MCP.** Apertura: MCP `sertor-rag` interrogato — `search_code("install_governance
> build plan marker block SDLC ritual claude-md-block")` ha restituito i test del piano SDLC
> (`packages/sertor-flow/tests/...`), **nessun errore tool**. Il resto dell'ancoraggio (numeri di riga,
> closure dei test) è stato verificato con `Read`/`Grep` su file di posizione nota (eccezione MCP-first
> per fatti puntuali). Nessun guasto MCP da segnalare.

---

## Ancoraggio verificato (dato di partenza, non da progettare)

| Elemento | Posizione reale (verificata) |
|---|---|
| Wiki block (`SERTOR:WIKI-RITUAL`, 71 righe) | `packages/sertor/src/sertor_installer/assets/claude-md-block.md` |
| RAG block (`SERTOR:RAG-USAGE`, 72 righe) | `packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md` |
| SDLC block (`SERTOR:SDLC-RITUAL`, 65 righe) | `packages/sertor-flow/src/sertor_flow/assets/claude-md-block-sdlc.md` |
| «How to invoke» copia 1 (full, +Windows note) | `rag/claude-md-block-rag-usage.md:12-38` |
| «How to invoke» copia 2 (full, +Windows note) | `rag/skills/guided-setup/SKILL.md:52-78` |
| «How to invoke» copia 3 (runtime-only, +Windows note) | `claude/skills/wiki-author/wiki-playbook.md:93-112` |
| Wiring RAG block (MARKER_BLOCK) | `install_rag.py:79-80,429-436` (`_RAG_USAGE_BLOCK`, `APPEND_BLOCK`) |
| Wiring wiki block | `install_wiki.py:440` (`SharedEdit … "SERTOR:WIKI-RITUAL"`) |
| Wiring SDLC block | `install_governance.py:65-66` (`MARKER_START_SDLC`/`_END_SDLC`) |
| Deposito skill RAG (FILE byte-copy) | `install_rag.py:317-333` `_skill_artifacts`, `:459-462` |
| Owned paths RAG (coverage manifest) | `install_rag.py:777-846` (`.sertor` owned_dir, skill owned_dirs) |
| Guardia parità + closure | `packages/sertor/tests/test_assets_copilot_parity.py` |
| Guardia footgun `uv run` / guide presence | `packages/sertor/tests/test_assets_cli_invocation.py` |
| Guardia sync dogfood↔bundle | `tests/unit/test_assets_sync.py` (copre **solo** `assets/claude/**`) |

**Occorrenze esaustive di «How to invoke» negli asset** (`Grep`): le 3 sedi dichiarate + **due
mini-note di 3 righe** negli asset eval (`rag/skills/eval-suite-author/SKILL.md:31-33`,
`rag/skills/eval-feedback/SKILL.md:30-32`) del tipo «How to invoke `sertor-rag`» — **NON** la sezione
completa (niente Windows note, niente livello-installer, niente footgun `--project`/`--directory`).
Sono fuori dalla triplicazione dichiarata (spec §1) e fuori ambito (spec Out-of-Scope «contenuto delle
skill al di là della sezione How to invoke»); **residuo minore tracciato** sotto (R-eval).

---

## DA-D-r3 — Conferma formale: il blocco SDLC NON contiene «How to invoke» (RISOLTA)

Lettura integrale di `claude-md-block-sdlc.md` (righe 1–65): il blocco contiene **solo** le fasi del
flusso SpecKit (requirements→…→implement), il *Constitution Check* gate, l'*Error discipline — fix,
don't suppress*, e la *Version control discipline*. **Nessuna** sezione «How to invoke», **nessuna**
sintassi di invocazione CLI, **nessuna** Windows note. Confermato: **REQ-008/009 non riguardano il
blocco SDLC**; la triplicazione coinvolge solo RAG block + `guided-setup` + `wiki-playbook`.

**Corollario sul blocco SDLC (REQ-001/016).** Il blocco è **già a sola direttiva comportamentale
standing**: non possiede dettaglio lookup-on-demand da estrarre. La «riduzione» di REQ-001 è quindi un
**no-op di contenuto** per questo blocco (REQ-016 ne impone la *conservazione* integrale del minimo).
Decisione: **il blocco SDLC NON viene modificato nel contenuto** (riduce la superficie di rischio sul
pacchetto `sertor-flow`); è coperto dalla sola **guardia di non-reintroduzione** (vedi DA-D-r4). CS-1
(altitude totale < 208 righe) è raggiunto dai soli blocchi RAG + wiki (vedi stima sotto).

---

## DA-D-r1 — Dove vive il reference unico «How to invoke + Windows note» (RISOLTA → Opzione A)

### Opzioni valutate
- **(A)** nuovo asset dedicato nel bundle RAG (`rag/sertor-cli-reference.md`), depositato da `sertor
  install rag`, citato per nome dal RAG block e da `guided-setup`.
- **(B)** la sezione resta in `guided-setup/SKILL.md` come fonte designata; gli altri la citano.
- **(C)** la sezione diventa parte del `wiki-playbook.md` (bundle wiki); gli altri la citano lì.

### Vincolo dominante: **closure per-capacità** (REQ-003/007, NFR-5)
La guardia di closure (`test_assets_copilot_parity.py`) impone che **ogni asset citato per nome in un
body sia depositato dal piano della STESSA capacità**. Le tre sedi appartengono a **capacità diverse e
installabili in isolamento**:
- RAG block + `guided-setup` → depositati da **`sertor install rag`**.
- `wiki-playbook` → depositato da **`sertor install wiki`** (può essere installato **senza** RAG).

Quindi una sede canonica nel bundle RAG (A) è raggiungibile da RAG block + `guided-setup` (stessa
capacità → closure OK), **ma non** dal `wiki-playbook` su un install solo-wiki (pointer morto → viola
REQ-007/NFR-5). Opzione (B) ha lo stesso difetto. Opzione (C) inverte il problema (il RAG block citerebbe
un asset wiki → morto su install solo-RAG) ed è peggiore (il RAG block è always-on e RAG è la capacità
primaria delle regole di invocazione, REQ-007).

### Riframe decisivo: il vincolo cross-capacità tocca **solo** il `wiki-playbook` (un Should)
Tra i **tre blocchi always-on**, **solo il RAG block** cita il reference di invocazione. Il blocco wiki
cita il **wiki playbook** (stessa capacità wiki, REQ-014); il blocco SDLC non cita nulla. Quindi
REQ-007 («su install solo-wiki/solo-governance nessun pointer morto») è soddisfatto **per costruzione**
per i blocchi: l'unico blocco che cita il reference (RAG) viaggia con RAG. La tensione cross-capacità
resta **solo** per il `wiki-playbook`, che **non è un blocco** ma payload di skill, e la cui dedup è
**REQ-009 (Should)**.

### Decisione: **Opzione A** + reference nel **runtime host-agnostico `.sertor/`**
- **Asset canonico (UNICA fonte):** `packages/sertor/src/sertor_installer/assets/rag/sertor-cli-reference.md`.
- **Deposito:** `build_rag_plan` aggiunge un `Artifact(FILE, "rag/sertor-cli-reference.md",
  ".sertor/sertor-cli-reference.md", CREATE_IF_ABSENT)`. Target **host-agnostico** (`.sertor/` è
  identico su Claude e Copilot → un solo target per entrambi gli assistenti); copertura owned via
  l'owned_dir `.sertor` già esistente (`install_rag.py:835`); rimosso in blocco con `.sertor` su
  uninstall; **aggiornato su upgrade** come gli altri owned-file in `.sertor/` (gemello hook
  `memory-capture`/`rag-freshness`). Nessun nuovo `ArtifactKind`/`WriteStrategy`/Surface/seam del kit.
- **Citazione per nome** (REQ-002, host-agnostico): RAG block e `guided-setup` citano
  ``sertor-cli-reference.md`` (basename) → closure verificata sul piano RAG (basename in
  `{Path(t).name for t in rag_plan_targets}`).
- **Contenuto:** la sezione «How to invoke Sertor's commands» a **due livelli** (runtime CLIs via `uv
  run --project .sertor` + installer via `uvx --from "git+…"`) **+ Windows note** `pywin32`, integrale
  e host-agnostica (nessun `.claude/`, nessuno slash-command, nessun nome modello/prodotto Claude).

### `wiki-playbook` (REQ-009, Should) — risoluzione **closure-safe**, senza pointer morto
Il `wiki-playbook` **rimuove** la sottosezione duplicata «How to invoke the runtime CLIs» + Windows
note (righe 93–112) e **mantiene** la forma minima di invocazione già presente al §2
(`uv run --project .sertor sertor-wiki-tools <op>`, righe 88–91), sufficiente all'auto-contenimento
della capacità wiki su un install solo-wiki. **NON** cita ``sertor-cli-reference.md`` per nome (sarebbe
un pointer morto sul piano wiki → closure rossa): aggiunge invece una **frase condizionale senza token
di file** («the Sertor RAG capability, when installed, ships a fuller CLI reference…») che **non**
entra nello scope della closure (`_BACKTICK_REF` matcha solo `…\.md/ps1/toml/json`). Effetto: la
**sezione completa + Windows note** vive in **esattamente un** asset (`sertor-cli-reference.md`) →
**CS-2 soddisfatto**; la triplicazione è eliminata; nessun pointer morto (REQ-007/NFR-5). Si conserva
una **riga di chiarimento PATH** nel playbook (auto-contenimento wiki-only).

> **Perché non depositare il reference anche da `install wiki`** (per far citare il filename al
> playbook): introdurrebbe **ownership condivisa di un file fra due capacità** (`.sertor/…` o copia nel
> payload wiki), con coordinamento di uninstall/upgrade non banale (rimuovere su uninstall-wiki
> ucciderebbe il pointer del RAG block se RAG è ancora installato) e/o **duplicazione della fonte** (due
> copie nel tree → la deriva che la feature combatte). Per un **Should** è sproporzionato; la
> risoluzione condizionale soddisfa lo **spirito** di REQ-009 (uccide la duplicazione) rispettando i
> **Must** REQ-007/NFR-5. *(Tracciato: l'eventuale full-dedup del playbook via deposito cross-capacità
> è un'estensione futura, non necessaria al done.)*

---

## DA-D-r2 — Criterio qualitativo «direttiva breve + pointer» (RISOLTA, no soglia numerica)

Criterio **qualitativo** (REQ-001/NFR-6), misurabilità **ex-post** (CS-1). **Nessuna soglia in righe**
(il budget gate deterministico è **FEAT-024**). Regola di taglio per i tre blocchi:

> **Tenere inline = direttiva comportamentale standing** (una regola che l'agente DEVE seguire in
> *ogni* sessione, a prescindere dall'operazione). **Spostare a pointer = lookup-on-demand** (sintassi
> esatta, enumerazioni, note di troubleshooting) che l'agente cerca *quando serve*.

**Blocco RAG (`claude-md-block-rag-usage.md`) — REQ-015.**
- *Tenere (standing):* usa i **vehicles** (CLI/MCP) e **mai importare `sertor_core`**; **search-first,
  read-second** (con l'esempio comune `uv run --project .sertor sertor-rag search`, che mantiene anche
  la forma robusta richiesta da `test_invoking_assets_carry_robust_form`); **errore MCP = segnale, non
  rumore**; **gate privacy memoria** (`SERTOR_MEMORY=false` di default, comandi no-op).
- *Spostare (lookup) → pointer a `sertor-cli-reference.md`:* la sezione «How to invoke Sertor's
  commands» (runtime CLIs vs installer, `--project` NOT `--directory`, fallback al venv, chiarimento
  «not on PATH ≠ not installed») **+ Windows note** `pywin32`.

**Blocco wiki (`claude-md-block.md`) — REQ-014.**
- *Tenere (standing):* **golden rule** (documentare ogni cosa di rilievo); **outline del rituale di
  step** (record/distill/lint/explainer) con le **regole di delega** (record→curator; distill/lint→main
  flow); **confine D↔N** (meccanico vs giudizio); **quando registrare** (allo stesso commit dello
  step); **DoD asset host-agnostici** (parità).
- *Aggiungere:* **riferimento per nome al `wiki-playbook.md`** (REQ-014).
- *Spostare (lookup) → al wiki playbook (citato per nome):* l'**enumerazione delle operazioni wiki**
  (record/distill/ingest/query/lint/reorg/generate/rag-sync/structure) e le **Conventions** (frontmatter,
  backlink, naming, formato voce di log) — già presenti nel playbook, ridondanti always-on.

**Blocco SDLC (`claude-md-block-sdlc.md`) — REQ-016.**
- *Tenere (tutto è standing):* fasi SpecKit in ordine; constitution gate; error discipline; version
  control discipline. **Nessun lookup da estrarre → contenuto invariato** (DA-D-r3).

### Stima ex-post di CS-1 (non vincolante, misurabile)
| Blocco | Prima | Dopo (stima) | Δ |
|---|---|---|---|
| RAG | 72 | ~48 | −24 |
| Wiki | 71 | ~53 | −18 |
| SDLC | 65 | 65 | 0 |
| **Totale always-on** | **208** | **~166** | **−~42** |

Il dettaglio estratto vive in `sertor-cli-reference.md` (**on-demand**, ~30 righe) + nel playbook
(già esistente). Totale always-on **misurabilmente < 208** → CS-1 ✓ (criterio qualitativo + misura).

---

## DA-D-r4 — Forma della guardia di non-reintroduzione (RISOLTA → assert testuale + closure)

**Assert testuale** sufficiente per il contratto di non-reintroduzione (REQ-012); il check semantico
è eccessivo. La guardia (estensione delle suite esistenti, non un nuovo pacchetto) verifica:

1. **Assenza inline** (REQ-012): i blocchi `claude-md-block.md` e `claude-md-block-rag-usage.md`
   (pacchetto `sertor`) **non** contengono l'heading «How to invoke Sertor's commands» né la Windows
   note (`pywin32_bootstrap`) né il pattern installer `uvx --from`. Per il blocco SDLC
   (`sertor-flow`), assert gemello (lettura via `kit_read("sertor_flow", …)`).
2. **Fonte unica** (CS-2): l'heading «How to invoke Sertor's commands» + i pattern di invocazione a
   due livelli + la Windows note esistono in **esattamente uno** asset distribuito
   (`sertor-cli-reference.md`).
3. **Pointer presente** (REQ-015): il RAG block contiene il riferimento per nome
   ``sertor-cli-reference.md``; il blocco wiki contiene ``wiki-playbook.md`` (REQ-014).
4. **Closure** (REQ-010, NFR-5): estensione di `test_assets_copilot_parity.py` — ogni body RAG (RAG
   block via MARKER_BLOCK + `guided-setup`) che cita ``sertor-cli-reference.md`` lo trova **depositato**
   dal piano RAG (per entrambi gli assistenti); negativo: un piano che non lo deposita fa fallire.
5. **Rework** dei test che oggi *richiedono* la sezione inline (`test_assets_cli_invocation.py`):
   - `test_canonical_guide_present_where_first_invoked` → asserisce la guida completa in
     `sertor-cli-reference.md` (non più nel RAG block / `guided-setup`), e che le altre sedi portino il
     **pointer** non la copia.
   - `test_wiki_playbook_ships_runtime_invocation_guide` → asserisce la forma robusta minima (§2) +
     **assenza** della sottosezione duplicata «How to invoke the runtime CLIs» + Windows note.
   - `test_rag_usage_block_uv_run_replaces_bare_search` → **resta verde** (l'esempio search-first
     `uv run --project .sertor sertor-rag search` è conservato).
   - `_CANONICAL_GUIDE_ASSETS` aggiornato; **aggiunto** `sertor-cli-reference.md` agli asset coperti
     dal footgun-check (`_INVOKING_ASSETS`, mai `uv run` nudo / `--directory`).

---

## Impatto sul sync dogfood (CS-6)

`tests/unit/test_assets_sync.py` copre **solo** `assets/claude/**`. Tra i file toccati, **solo** il
`wiki-playbook.md` vive sotto `assets/claude/skills/wiki-author/` → richiede
`python -m sertor_installer.sync` per riallineare `.claude/skills/wiki-author/wiki-playbook.md`
(byte-parità). Gli altri asset toccati stanno sotto `assets/` (top-level) o `assets/rag/` → **non**
sincronizzati in `.claude/` (nessun re-sync). Il blocco SDLC (`sertor-flow`) non è modificato.

---

## Residui tracciati (promozione, no sepoltura in `specs/`)
- **R-eval** — le due mini-note di 3 righe «How to invoke `sertor-rag`» in `eval-suite-author` /
  `eval-feedback`: forma minima (no sezione/Windows note), fuori dalla triplicazione dichiarata. *Could*
  opzionale: convertirle in pointer al reference. Non espande lo scope; appartiene alla pulizia stile
  skill → **FEAT-022** (cross-ref).
- **R-wiki-full-dedup** — full-dedup del `wiki-playbook` via deposito cross-capacità del reference: non
  necessaria al done (REQ-009 soddisfatto nello spirito); estensione futura, non promossa (nessuna
  capacità nuova).
- Cross-ref già a casa durevole: budget altitude CI → **FEAT-024**; stub `assets/copilot/**` →
  **FEAT-023**; pulizia stile skill → **FEAT-022**.

---

## Esito ricerca
Tutti gli ignoti di *come* (DA-D-r1..r4) sono **RISOLTI** senza `NEEDS CLARIFICATION` residui. Il
cambiamento è **additivo/igiene host-facing**, **ZERO** `sertor_core` (Principio XI): tocca solo asset
`.md`, un `Artifact` FILE nel plan-builder RAG (`install_rag.py`, installer host-facing — non core), le
copie dogfood `.claude/` e le guardie di test.
