# Requisiti — Asset-install: gli asset del dogfood depositati dai veri installer (process-fidelity)

<!-- Deriva da: E15-FEAT-001 scope B (rimandato dallo scope A in
     requirements/fedelta-dogfood/runtime-installato/requirements.md §4 "Fuori ambito", righe 48-49).
     Assorbe come fette: E15-FEAT-003 (residuo non-byte) e E15-FEAT-004 (riconciliazione divergenze). -->

## 1. Contesto e problema (perché)

Il dogfood di Sertor deve comportarsi come un **client Sertor fedele** — stessi file **e** stesso
processo d'install (missione E15, [[dogfood-fidelity]]). La **metà runtime** del detour è chiusa:
il runtime `.sertor/` installa `sertor-core` da `git=<repo>` HEAD (E15-FEAT-001 scope A / F1, `.mcp.json`
repointato / F7) e si re-locka a ogni merge (E15-FEAT-008 / F8). Resta aperta la **metà asset**.

La fedeltà degli asset ha **due assi** (epica §1):
- **asset-fidelity** (*stessi byte*) — **già chiusa** da E15-FEAT-002 (`sertor_installer.sync` esteso ai
  subtree RAG + guardia byte esaustiva `test_assets_rag_dogfood_sync`);
- **process-fidelity** (*prodotti eseguendo il vero installer*) — **assente**. Oggi gli asset host-facing
  del dogfood arrivano tramite **due scorciatoie dev-time**, non tramite il percorso d'install reale:
  1. `python -m sertor_installer.sync` (copia byte `assets/…` → `.claude/…`) — cfr.
     `packages/sertor/src/sertor_installer/sync.py`;
  2. lo script isolato `scripts/dev/materialize-speckit.ps1` per la machinery `.specify/` (E10-FEAT-027).

Sotto la **direttiva utente vincolante** ([[feedback_dogfood_solo_via_install_versionbump]]) queste
scorciatoie sono **interim**: la vera via di fedeltà è il **self-install eseguito SUL dogfood** (non in
sandbox). Il problema che questa feature chiude: gli asset del dogfood **non sono mai prodotti** dai veri
`sertor install rag`, `sertor install wiki`, `sertor-flow install` — quindi il **processo** (merge di
`settings.json`, inserzione dei blocchi marker in `CLAUDE.md`, wiring PreToolUse, deposito
`.sertor/sertor-cli-reference.md` / `.sertor/.sertor-version`, idempotenza, preservazione, uninstall)
**non è mai dogfoodato**; è testato solo su host sintetici in `tmp_path`.

**Ancoraggio (installer reali):** `packages/sertor/src/sertor_installer/install_rag.py`,
`install_wiki.py`, `packages/sertor-flow/src/sertor_flow/install_governance.py`; asset-blocchi
`assets/claude-md-block.md`, `assets/rag/claude-md-block-rag-usage.md`,
`packages/sertor-flow/.../assets/claude-md-block-sdlc.md`; hook `.claude/hooks/sertor-rag-usage-check.ps1`.

**Fatto empirico decisivo (spike 2026-07-03):** eseguire `sertor-flow install` sul dogfood **appende il
blocco marker SDLC/step-ritual ACCANTO alla prosa hand-written** di `CLAUDE.md` (duplicazione); il merge
di `.mcp.json` **salta se il server esiste**; `wiki.config` è **preservato**; `specify init --force`
clobbera **solo** `plan-template.md` (costituzione v1.4.0 **salva**, create-if-absent → E15-FEAT-005 già
mitiga). Questi non sono ipotesi: sono osservati.

## 2. Obiettivi e criteri di successo

- **O1 (process-fidelity asset).** Gli asset host-facing del dogfood sono **depositati** eseguendo i veri
  `sertor install rag`, `sertor install wiki`, `sertor-flow install` sul dogfood — non via sync/script.
- **O2 (nessuna regressione di fedeltà byte).** Dopo il self-install, gli asset restano **byte-conformi**
  a quelli che un client riceve (la guardia byte esistente non deve rompersi; anzi, deve valere sull'esito
  del **processo reale**, non del sync).
- **O3 (non distruttivo/idempotente).** Un self-install (o ri-install) sul repo vivo **non distrugge**
  artefatti curati (costituzione, prosa `CLAUDE.md`, `wiki.config` super-set, `.env` con la key Azure) ed
  è **ripetibile** (secondo giro = no-op o superset dichiarato).
- **O4 (sync interim ritirato o retrocesso a guardia).** Una volta che il self-install è la via, il ruolo
  di `sertor_installer.sync` come *via di fedeltà* è **chiuso** (resta al più come guardia/dev-tooling,
  esplicitamente marcato).

**Criteri di successo (misurabili, tech-agnostici):**
- **SC-1:** esiste una procedura **ripetibile e documentata** che esegue i 3 veri installer sul dogfood e
  lascia il repo in uno stato **committabile** (nessun artefatto curato perso, nessuna duplicazione).
- **SC-2:** per **ogni** asset host-facing del dogfood si può dimostrare che è **prodotto dal processo
  d'install** (non depositato a mano) — 0 asset host-facing la cui unica provenienza è il sync/script.
- **SC-3:** `CLAUDE.md` del dogfood contiene i blocchi marker (RAG-USAGE, SDLC) **una sola volta**, senza
  duplicazione con la prosa hand-written; un ri-install non li duplica.
- **SC-4:** un self-install ripetuto è **idempotente** (verificato, non assunto): secondo giro senza diff
  distruttivo.
- **SC-5:** i residui **non-byte** (wiring PreToolUse in `settings.json`, `.sertor/sertor-cli-reference.md`,
  `.sertor/.sertor-version`, blocco `SERTOR:RAG-USAGE`) sono **presenti** nel dogfood via il processo (o la
  loro assenza è **dichiarata** con motivo).
- **SC-6:** per ogni **divergenza hand-authored** residua (`.mcp.json`, `.env`, marker-block vs prosa)
  esiste una **decisione esplicita**: forma-client adottata **o** divergenza-dev dichiarata e guardata.
- **SC-7:** `sertor-core` **invariato**; nessun asset **distribuito** reso Sertor-specifico (Principio X).

## 3. Stakeholder e attori
- **Agente/manutentore del dogfood** — vuole fiducia piena nel dogfooding: dogfood == client su asset **e**
  processo.
- **CI** — coglie sia il drift di asset (guardia byte) sia le regressioni di process-fidelity.
- **Ospiti reali** — beneficiano: il percorso d'install è **davvero esercitato** (merge/wiring/idempotenza)
  prima di raggiungerli — bug come la duplicazione marker-block emergono qui, non sull'ospite.

## 4. Ambito

### In ambito
- Eseguire i **tre veri installer** (`sertor install rag`, `sertor install wiki`, `sertor-flow install`)
  **sul dogfood** e portare il repo a uno stato committabile fedele.
- **Riconciliare** le divergenze che l'esecuzione fa emergere (assorbe E15-FEAT-004): duplicazione
  marker-block vs prosa in `CLAUDE.md`, `.mcp.json`, `.env`.
- **Colmare** i residui non-byte che un client riceve (assorbe E15-FEAT-003): wiring PreToolUse,
  `.sertor/sertor-cli-reference.md`, `.sertor/.sertor-version`, blocco `SERTOR:RAG-USAGE`.
- **Rendere preservanti/idempotenti** gli installer dove il ri-install sul dogfood distruggerebbe curato
  (oltre a `plan-template.md` già coperto da FEAT-005): mappare empiricamente ogni clobber prima di
  automatizzare.
- **Ritirare** il ruolo del sync come via di fedeltà (retrocederlo a guardia o rimuoverlo).
- Una **guardia/verifica** che l'esito del processo combaci con lo stato committato del dogfood.

### Fuori ambito
- Riscrivere gli installer o cambiare il comando `specify init` (si **consuma** il percorso esistente,
  estendendolo solo dove serve per la preservazione — come già fatto in FEAT-005).
- Il layout **Copilot** del dogfood (il dogfood è Claude; la fedeltà Copilot è coperta da test dedicati).
- Il **runtime** `.sertor/` (core/MCP/venv) — già chiuso da FEAT-001 scope A / F1 / F7 / F8.
- Cambi a `sertor-core`.
- Numeri di versione / auto-updater (E2-FEAT-013) = ospiti esterni, non il dogfood.

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous).** The dogfood's host-facing assets (`.claude/` hooks·skills·agents, `.specify/`
  machinery, `CLAUDE.md` marker blocks, `settings.json` hook/PreToolUse wiring, `.sertor/sertor-cli-reference.md`,
  `.sertor/.sertor-version`) shall be produced by executing the real installers (`sertor install rag`,
  `sertor install wiki`, `sertor-flow install`) on the dogfood, not by `sertor_installer.sync` nor by
  `scripts/dev/materialize-speckit.ps1`.
- **REQ-002 (Event-driven).** When the real installers run on the dogfood, the resulting asset bytes shall
  remain conformant to what a client receives (the existing byte guard shall pass against the install
  outcome, not against the sync outcome).
- **REQ-003 (Event-driven).** When `sertor-flow install` inserts the SDLC/step-ritual marker block into
  `CLAUDE.md`, the block shall appear **exactly once** and shall **not be duplicated** alongside the
  pre-existing hand-written prose.
- **REQ-004 (Event-driven).** When `sertor install rag` inserts the `SERTOR:RAG-USAGE` marker block and the
  PreToolUse wiring into `settings.json`, both shall be present in the dogfood after the install.
- **REQ-005 (Event-driven).** When a real installer runs on the dogfood, it shall **preserve** curated
  artifacts it does not own — the constitution `v1.4.0`, the hand-written `CLAUDE.md` prose, the
  super-set `wiki.config.toml`, and `.env` (Azure key) — leaving them byte-unchanged.
- **REQ-006 (Event-driven).** When a real installer is re-run on the already-installed dogfood, it shall be
  **idempotent** — no duplication and no destructive diff on curated artifacts (a declared superset is
  acceptable, silent loss is not).
- **REQ-007 (Unwanted behaviour).** If a real installer on the dogfood would **clobber** a curated artifact
  (as `specify init --force` does to `plan-template.md`), then the installer shall preserve it
  (backup/restore or replace-if-upstream, per the FEAT-005 mechanism) and report the outcome honestly.
- **REQ-008 (Ubiquitous).** For every host-facing asset in the dogfood there shall be a way to demonstrate
  its provenance is the **install process** (not a hand copy); an asset whose only provenance is the
  sync/script shall be treated as **debt**, not as fidelity.
- **REQ-009 (Ubiquitous).** For every residual hand-authored divergence (`.mcp.json`, `.env`, marker-block
  vs prose) there shall be an **explicit decision** recorded — client-form adopted **or** dev-divergence
  declared and guarded — with no silent divergence.
- **REQ-010 (Event-driven).** When the self-install becomes the fidelity path, `sertor_installer.sync`'s
  role as *fidelity vehicle* shall be **retired** — removed or explicitly demoted to a guard/dev-tool and
  marked as such.
- **REQ-011 (Ubiquitous).** The change shall leave `sertor-core` unmodified and shall make **no distributed
  asset** Sertor-specific (Principle X) — only the dogfood's own state and, where strictly needed for
  preservation, the installers' host-agnostic non-destructive behaviour change.
- **REQ-012 (Unwanted behaviour).** If running the installers on the live repo risks an unrecoverable
  destructive change, then the procedure shall provide a **safe rehearsal / reversibility** path (e.g.
  branch + verifiable diff before commit) so no curated state is lost irreversibly.

## 6. Requisiti non funzionali
- **NFR-1 (idempotenza reale):** l'idempotenza è **verificata** eseguendo due volte, non assunta (SC-4).
- **NFR-2 (osservabilità dell'esito):** ogni install sul dogfood produce un esito **ispezionabile** (report
  installer / diff git) che dice cosa ha depositato/preservato/saltato — coerente con Principio XII
  (fail-loud, esito onesto).
- **NFR-3 (rete):** il self-install richiede rete (`uvx` per `specify init`, `uv` per il runtime) —
  dichiarato; la procedura non è offline.
- **NFR-4 (confine dev↔dogfood):** i **test** continuano a girare sull'editable `.venv` (`uv run pytest`),
  invariati; il self-install tocca lo **stato del dogfood**, non il ciclo di sviluppo.
- **NFR-5 (reversibilità operativa):** la procedura è eseguita in modo da poter **ispezionare il diff prima
  del commit** (branch + review), data la natura distruttiva sul repo vivo.

## 7. Vincoli, assunzioni e dipendenze
- **Dipendenza soddisfatta:** E15-FEAT-005 ✅ (installer preservante `plan-template.md`) — prerequisito per
  eseguire `sertor-flow install` senza perdere il mission-gate.
- **Dipendenza soddisfatta:** E15-FEAT-002 ✅ (guardia byte esaustiva) — la verifica di corrispondenza
  post-install si appoggia a questa guardia (ora valutata sull'esito del processo).
- **Assunzione (spike, verificata):** `specify init --force` è create-if-absent sulla costituzione ma
  clobbera `plan-template.md`; l'unico clobber curato noto è quello (mappare gli altri empiricamente prima
  di automatizzare — R-1).
- **Vincolo:** operazione **distruttiva sul repo vivo** (muta `.claude/`, `CLAUDE.md`, `settings.json`) →
  eseguire su branch, ispezionare, poi committare (mai su master diretto).
- **Vincolo (direttiva utente):** il self-install gira **SUL dogfood**, non in sandbox; il dogfood traccia
  HEAD ([[feedback_dogfood_solo_via_install_versionbump]]).
- **Relazione con FEAT-009:** il fix template `.mcp.json` `--directory`→`--project` (E15-FEAT-009) conviene
  **prima** di questa feature, altrimenti il vero install depositerebbe la forma sbagliata di `.mcp.json`
  (dipendenza soft: da chiarire in plan).

## 8. Rischi
- **R-1 (clobber non mappato):** un installer distrugge un artefatto curato non ancora identificato.
  *Mitigazione:* scoperta **empirica** su branch (diff ispezionato) prima di automatizzare; installer
  preservanti (REQ-007) estesi caso per caso; costituzione già verificata salva.
- **R-2 (duplicazione marker-block):** il caso già osservato (SDLC block accanto alla prosa) — se non
  risolto, ogni install duplica. *Mitigazione:* REQ-003 + decisione DA-1 (riconcilia prosa→marker o
  installer preservante).
- **R-3 (perdita di superset dogfood):** `wiki.config` / config del dogfood sono **avanti** al template
  (staleness inversa, cfr. FEAT-006) → un install potrebbe retrocederli. *Mitigazione:* REQ-005 (preserva
  ciò che c'è); coordinare con FEAT-006.
- **R-4 (attrito operativo):** eseguire 3 installer a ogni bump aggiunge attrito. *Mitigazione:* procedura
  documentata/meccanizzabile; distinta dal ciclo di sviluppo (i test restano sul `.venv`).
- **R-5 (irreversibilità):** un errore sul repo vivo perde stato curato. *Mitigazione:* REQ-012 / NFR-5
  (branch + diff + review pre-commit).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-007, REQ-011, REQ-012.
- **Should:** REQ-004, REQ-006, REQ-008, REQ-009, NFR-1, NFR-2, NFR-5.
- **Could:** REQ-010 (ritiro sync — dipende dalla maturità del self-install), NFR-4 (già vero, da
  preservare).

## 10. Domande aperte
- **DA-1 [design→specify/plan]:** come gestire la **duplicazione marker-block-vs-prosa** in `CLAUDE.md`?
  Opzioni: (a) installer preservante/idempotente sul block (replace-if-marker come FEAT-005); (b)
  riconciliare la **prosa hand-written del dogfood a forma-marker** (il dogfood adotta la forma-client, i
  blocchi diventano gli unici proprietari di quelle sezioni); (c) dichiarare la prosa come divergenza-dev.
  *Raccomandazione preliminare:* (b) — è la più fedele al modello «dogfood = client».
- **DA-2 [plan]:** **ordine** di esecuzione dei 3 installer (`sertor-flow install` → `sertor install rag`
  → `sertor install wiki`?) e loro interazioni (chi tocca `settings.json`, chi `CLAUDE.md`).
- **DA-3 [plan]:** come **verificare la corrispondenza** post-install — riusare la guardia byte FEAT-002
  contro l'esito del processo? aggiungere un confronto processo↔committato? un harness CI?
- **DA-4 [scope]:** che ne è del **sync interim** una volta che il self-install è la via — rimuovere
  `sertor_installer.sync`, o retrocederlo a sola-guardia? (REQ-010, Could).
- **DA-5 [dipendenza]:** **E15-FEAT-009** (`.mcp.json` `--directory`→`--project`) va chiuso **prima**?
  (soft-dependency: altrimenti l'install deposita la forma sbagliata).
- **DA-6 [scope]:** i **residui non-byte** (`.sertor/sertor-cli-reference.md`, `.sertor/.sertor-version`)
  hanno dest **gitignorata** — vanno dogfoodati come presenza runtime o basta dichiararli prodotti
  dall'install a runtime? (SC-5).

---

**Commit proposto:** `docs(requirements): E15 asset-install (FEAT-001 scope B) — process-fidelity degli asset via veri installer`
