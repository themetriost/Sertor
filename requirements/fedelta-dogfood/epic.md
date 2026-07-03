# Epica — Fedeltà dogfood↔client (il dogfood prodotto e verificato dai veri installer)

> **Origine:** audit di fedeltà 2026-07-03 (3 ricognitori: RAG · wiki · governance) nato dalla domanda
> dell'utente «il punto era su *tutto* Sertro — abbiamo fatto su tutto?» dopo E10-FEAT-027 (che ha reso
> fedele la **sola** fetta SpecKit). Sintesi in [[audit-fedelta-dogfood-2026-07-03]].

## 1. Visione e problema (perché)

Il workspace di Sertor fa **dogfooding** del proprio prodotto, ma **non è un client fedele di sé** in modo
uniforme. La fedeltà ha **due livelli**, e oggi il dogfood copre solo (in parte) il primo:

- **Asset-fidelity** — il dogfood *possiede gli stessi file* che un client riceve. Meccanismo:
  `python -m sertor_installer.sync` (copia `assets/claude/**` → `.claude/**`) + guardie. **Parziale/disuniforme:**
  il sync copre **solo** `assets/claude/**` — **non** `assets/rag/**` (hook/skill RAG copiati a mano),
  **non** `settings.hooks.json`, **non** il blocco SDLC; solo 3 hook RAG + gli asset wiki hanno una guardia
  byte → **drift silenzioso possibile** sul resto.
- **Process-fidelity** — il dogfood è *prodotto eseguendo i veri installer* (`sertor install rag`/`wiki`,
  `sertor-flow install`), esercitando merge/wiring/idempotenza/uninstall reali. **Assente ovunque:** il
  processo d'install non è **mai** esercitato sul dogfood; è testato solo su host sintetici in `tmp_path`.

E10-FEAT-027 ha chiuso l'unica superficie che non aveva **nessuno** dei due (la machinery SpecKit, che non
è nemmeno un asset bundlato). Restano scoperte: (a) i buchi dell'asset-fidelity, (b) la process-fidelity su
**tutte** le superfici. La missione: *il dogfood deve comportarsi come un client Sertor fedele — stessi
file **e** stesso processo d'install — su RAG + wiki + governance.*

## 2. Ambito

### In ambito
- **Process-fidelity**: esercitare i veri installer contro il dogfood (o un suo clone sandbox) e verificare
  la corrispondenza, su tutte e tre le superfici.
- **Asset-fidelity completa**: estendere sync + guardie a **ogni** asset distribuito (RAG incluso, settings,
  SDLC block), chiudendo il drift silenzioso.
- **Colmare gli artefatti RAG mancanti** nel dogfood (oggi non dogfoodati affatto).
- **Riconciliare le divergenze hand-authored** (`.mcp.json`, `.env`, blocchi CLAUDE.md marker vs prosa,
  config wiki super-set): per ciascuna, adottare la forma-client **o** dichiarare la divergenza-dev.
- **Rendere gli installer preservanti** dove il re-install sul dogfood distruggerebbe artefatti curati
  (oggi noto: `plan-template.md`).

### Fuori ambito
- Riscrivere gli installer o cambiare il comando `specify init` (si **consuma** il percorso esistente,
  estendendolo solo dove serve per la preservazione).
- Il layout **Copilot** del dogfood (il dogfood è Claude; la fedeltà Copilot è verificata da test dedicati).
- Cambi a `sertor-core`.

## 3. Criteri di successo (misurabili, tech-agnostici)

- **SC-1 (process-fidelity):** esiste un harness ripetibile che esegue i veri installer in sandbox e
  verifica che l'esito **combaci** con lo stato committato del dogfood (o ne sia un superset dichiarato);
  gira in CI, offline dove possibile.
- **SC-2 (asset-fidelity completa):** **ogni** asset distribuito (Claude + RAG + settings + SDLC) ha una
  guardia byte dogfood↔bundle; 0 asset senza guardia.
- **SC-3 (copertura RAG):** gli artefatti RAG che un client riceve sono **presenti** nel dogfood (o la loro
  assenza è dichiarata con motivo).
- **SC-4 (divergenze riconciliate):** per ogni artefatto hand-authored divergente, esiste una decisione
  esplicita (forma-client adottata **o** divergenza-dev dichiarata e guardata).
- **SC-5 (idempotenza preservante):** un vero `sertor(-flow) install` ri-eseguito sul dogfood **non**
  distrugge artefatti curati (verificato, non assunto).
- **SC-6:** `sertor-core` invariato; nessun asset **distribuito** reso Sertor-specifico (Principio X).

## 4. Stakeholder e attori
- **Manutentore/agente del dogfood** — vuole che dogfood == client (fiducia nel dogfooding).
- **CI** — coglie sia il drift di asset sia le regressioni di process-fidelity.
- **Ospiti reali** — beneficiano: il percorso d'install è davvero esercitato prima di raggiungerli.

## 5. Vincoli, assunzioni e dipendenze
- **Verificato (2026-07-03):** `specify init --force` è **create-if-absent** su `constitution.md` (la v1.4.0
  sopravvive) ma **clobbera** `plan-template.md`; `feature.json` non è toccato. → il rischio governance è
  ristretto a `plan-template.md` (FEAT-005).
- **Asset-sync odierno:** `sertor_installer.sync` copre solo `assets/claude/**`; guardie: `test_assets_sync`
  (wiki+claude), `test_assets_rag_dogfood_sync` (3 hook RAG).
- **Config runtime dogfood** (`.sertor/.env`, `.mcp.json`) è **dev-form** (venv monorepo), non la
  runtime-form `.sertor/` che un client ottiene — riconciliazione = FEAT-004.
- **Dipendenza:** rete per `uvx` quando l'harness esercita `sertor-flow install`/`specify init`.

## 6. Rischi
- **R-1 (col nuovo modello, il self-install gira SUL dogfood):** un `sertor(-flow) install` sul repo può
  distruggere artefatti curati (`plan-template.md` verificato; altro da mappare). *Mitigazione:* **installer
  preservanti (FEAT-005)** + scoperta **empirica** di ogni clobber prima di automatizzare il self-install
  (FEAT-001/008); la costituzione v1.4.0 è già verificata **salva**.
- **R-2 (staleness inversa):** alcuni template sono **indietro** rispetto al dogfood (es. `wiki.config.toml.tmpl`
  senza `explainers`/`audit`/`strings`/`roles.vcs`/`rag`) → «fedeltà» potrebbe voler dire allineare il
  *template* alla realtà, non il contrario. *Mitigazione:* FEAT-006 decide direzione per-artefatto.
- **R-3 (attrito del self-install ad ogni merge):** bump+install ad ogni merge aggiunge un passo al rituale
  post-merge. *Mitigazione:* meccanizzarlo (FEAT-008, hook/script), tenerlo veloce; i **test** restano
  sull'editable (nessun re-install per il ciclo di sviluppo — solo il runtime dogfood usa l'installato).

## 7. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità | Stato |
|----|---------|--------------------|----------|-------|
| FEAT-001 | **Il dogfood prodotto dal vero `sertor install`, tracking HEAD (self-install)** — il runtime `.sertor/` del dogfood installa `sertor-core` da `git=<repo>` a **HEAD** + gli asset via il processo reale (merge/wiring/deposit); ad ogni merge su `master` si **re-locka a HEAD** (`uv lock --upgrade`), così l'agente gira sull'ultimo master **installato**. **NON** un confronto sandbox: il dogfood *È* l'output d'install. | Il **cuore** del nuovo modello: process-fidelity piena, zero ambiguità repo-source↔installato | **Must** | 🔄 **RIORIENTATA (2026-07-03)** da «harness sandbox» a «self-install tracking HEAD» (direttiva utente; spike conferma runtime=uv-project-HEAD). Da decomporre. Dipende da FEAT-005 |
| FEAT-007 | **Runtime del dogfood sull'installato (repoint `.sertor/`)** — `.mcp.json`, hook e i puntatori runtime del dogfood passano dal venv monorepo (`.venv`) alla runtime-form installata (`.sertor/`), come un client | Elimina l'ambiguità repo-source↔installato nel runtime (assorbe la parte `.mcp.json` di FEAT-004) | **Should** | da decomporre (segue FEAT-001) |
| FEAT-008 | **Rituale post-merge: re-lock `.sertor/` a HEAD** — cablare nel rituale (e/o hook post-merge) il passo «`uv lock --upgrade` nel runtime `.sertor/` → il dogfood tira il master appena mergiato» ad ogni merge, **prima** di re-index/smoke | Rende la cadenza decisa **meccanica**, non discrezionale (confine D↔N) | **Should** | da decomporre |
| FEAT-002 | **Sync completo + guardie totali** — estendere `sertor_installer.sync` a `assets/rag/**` + `settings.hooks.json` + blocco SDLC; guardia byte per **ogni** asset distribuito | Chiude i buchi dell'asset-fidelity + il drift silenzioso | **Must** | ✅ **IMPLEMENTATA (2026-07-03)** — `sertor_installer.sync` esteso ai subtree byte RAG (`rag/{hooks,skills,agents}`); guardia **esaustiva auto-derivante** (`test_assets_rag_dogfood_sync`, 11 casi vs 3 fissi). Il sync ha **creato** i 3 asset mancanti (concierge · sertor-rag-usage-check · guided-setup → **assorbe F3-file**) e **riallineato** le 2 eval-skill dal fork IT al canon EN (**chiude E10-FEAT-025**); test `test_skill_eval_feedback` riconciliato al canon. 1065 unit verdi, ruff pulito, `sertor-core` invariato |
| FEAT-003 | **Artefatti RAG mancanti nel dogfood** — portare (o dichiarare assenti con motivo): hook `sertor-rag-usage-check.ps1` + wiring PreToolUse, skill `guided-setup`, agent `concierge`, `.sertor/sertor-cli-reference.md`, `.sertor/.sertor-version`, blocco `SERTOR:RAG-USAGE` in CLAUDE.md | Dogfoodiamo **tutto** il RAG, non un sottoinsieme | **Should** | 🔄 **file byte assorbiti da FEAT-002** (hook `sertor-rag-usage-check.ps1`, skill `guided-setup`, agent `concierge` ora nel dogfood via sync). **Resta il non-byte:** wiring PreToolUse in `settings.json`, `.sertor/sertor-cli-reference.md` + `.sertor/.sertor-version` (dest gitignorata), blocco `SERTOR:RAG-USAGE` in CLAUDE.md → **process-fidelity (FEAT-001)** |
| FEAT-004 | **Riconciliazione divergenze hand-authored** — `.mcp.json` (dev venv-form vs runtime `.sertor/`-form), `.sertor/.env`, blocchi CLAUDE.md (marker-block vs prosa italiana): per ciascuno **adotta la forma-client o dichiara la divergenza-dev** (+ guardia) | Nessuna divergenza silenziosa dogfood↔client | **Should** | da decomporre |
| FEAT-005 | **Installer preservante su `plan-template.md`** (≡ **E10-FEAT-028**, cross-ref) — backup/restore o replace-if-upstream attorno a `specify init --force` | Prerequisito per la process-fidelity **governance** (il dogfood può usare `sertor-flow install` senza perdere il mission-gate) | **Should** | 📋 (E10-FEAT-028) |
| FEAT-006 | **Template ↔ realtà (staleness inversa)** — allineare i template **indietro** rispetto al dogfood (`wiki.config.toml.tmpl`: `explainers`/`audit`/`strings`/`roles.vcs`/`rag`), o dichiarare le estensioni dogfood | Il template riflette la realtà che un client dovrebbe ricevere | **Could** | da decomporre |

*Consegnate ma **interim** sotto il nuovo modello:* **E10-FEAT-027** (SpecKit via script isolato) e
**FEAT-002** (sync esteso) hanno reso fedeli gli **asset** (asset-fidelity) — restano validi come guardie/
dev-tooling, ma la **via di fedeltà** passa ora al self-install (FEAT-001): la SpecKit reale arriverà da
`sertor-flow install` (FEAT-001+FEAT-005), non dallo script; il sync-come-fedeltà si depreca.

## 8. Decisioni (2026-07-03)
- **Modello target = REAL-INSTALL, il dogfood traccia HEAD** *(direttiva utente — **supera** la scelta
  «sandbox»)*. Il **runtime del dogfood** (ciò che l'agente usa: MCP · hook · skill · SpecKit · asset) gira
  **solo sulla versione INSTALLATA** via `sertor install`/`sertor-flow install`. Il runtime `.sertor/` è un
  progetto `uv` che installa `sertor-core` da **`git=<repo>` a HEAD** (verificato nello spike) → il dogfood è
  sempre sull'ultimo **master mergiato**. Il dogfood **È** l'output d'install, non un confronto sandbox.
  *«Non voglio più dare spazio ad ambiguità.»* Fonte: [[feedback_dogfood_solo_via_install_versionbump]].
  - **Numeri di versione + auto-updater (E2-FEAT-013) = ospiti esterni, NON il dogfood:** gli ospiti pinnano
    release taggate e si aggiornano via l'auto-updater; il dogfood segue HEAD.
  - **Cadenza:** **re-lock `.sertor/` a HEAD (`uv lock --upgrade`) → re-index/smoke** **ad ogni merge su
    `master`** (nuovo passo del rituale post-merge, FEAT-008).
  - **Confine dev↔dogfood:** **test/sviluppo** sull'editable workspace (`.venv`, `uv run pytest`); **runtime
    dell'agente** **solo sull'installato**.
- **Divergenze del RUNTIME = ELIMINA (non dichiara).** `.mcp.json` e i puntatori runtime devono usare la
  **forma-client installata** (`.sertor/` runtime), non il venv monorepo → si **eliminano** (FEAT-004/007). La
  «dichiara-o-elimina» resta solo per divergenze **puramente di sviluppo** che non toccano il runtime dogfood.
- **Sync/script = INTERIM (non più la via di fedeltà).** `sertor_installer.sync` (FEAT-002) e lo script SpecKit
  isolato (FEAT-027) restano utili come **guardie/dev-tooling**, ma la fedeltà ora passa dall'**install reale**;
  il sync-come-fedeltà si **deprecca** quando il self-install (FEAT-001) è in piedi.
- **Priorità = ASSET-FIDELITY PRIMA.** Prima **FEAT-002** (sync completo + guardie: chiude il drift silenzioso,
  cheap, è la fondazione del confronto dell'harness), poi FEAT-003, poi FEAT-001 (harness), FEAT-004/005/006 a
  seguire. FEAT-005 (`plan-template` preservante) resta piccolo e sblocca la governance quando serve.
