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
- **R-1:** eseguire i veri installer *sul repo* (non in sandbox) distruggerebbe artefatti curati
  (plan-template, forse altro non ancora mappato). *Mitigazione:* l'harness opera su **clone/sandbox**, mai
  sul repo; scoprire empiricamente ogni clobber (come per plan-template) prima di automatizzare.
- **R-2 (staleness inversa):** alcuni template sono **indietro** rispetto al dogfood (es. `wiki.config.toml.tmpl`
  senza `explainers`/`audit`/`strings`/`roles.vcs`/`rag`) → «fedeltà» potrebbe voler dire allineare il
  *template* alla realtà, non il contrario. *Mitigazione:* FEAT-006 decide direzione per-artefatto.
- **R-3:** over-engineering — inseguire la fedeltà bit-perfetta dove una divergenza-dev è legittima (es.
  `.mcp.json` venv per lo sviluppo monorepo). *Mitigazione:* «adotta **o** dichiara» (SC-4), non «adotta sempre».

## 7. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità | Stato |
|----|---------|--------------------|----------|-------|
| FEAT-001 | **Harness di process-fidelity** — test/CI che esegue i veri installer (`sertor install rag`/`wiki`, `sertor-flow install`) in **sandbox** (clone) e verifica corrispondenza col dogfood committato (o superset dichiarato); esercita merge/wiring/idempotenza/uninstall reali | Il cuore: «prodotto dal vero installer» senza distruggere il dogfood curato | **Must** | da decomporre |
| FEAT-002 | **Sync completo + guardie totali** — estendere `sertor_installer.sync` a `assets/rag/**` + `settings.hooks.json` + blocco SDLC; guardia byte per **ogni** asset distribuito | Chiude i buchi dell'asset-fidelity + il drift silenzioso | **Must** | ✅ **IMPLEMENTATA (2026-07-03)** — `sertor_installer.sync` esteso ai subtree byte RAG (`rag/{hooks,skills,agents}`); guardia **esaustiva auto-derivante** (`test_assets_rag_dogfood_sync`, 11 casi vs 3 fissi). Il sync ha **creato** i 3 asset mancanti (concierge · sertor-rag-usage-check · guided-setup → **assorbe F3-file**) e **riallineato** le 2 eval-skill dal fork IT al canon EN (**chiude E10-FEAT-025**); test `test_skill_eval_feedback` riconciliato al canon. 1065 unit verdi, ruff pulito, `sertor-core` invariato |
| FEAT-003 | **Artefatti RAG mancanti nel dogfood** — portare (o dichiarare assenti con motivo): hook `sertor-rag-usage-check.ps1` + wiring PreToolUse, skill `guided-setup`, agent `concierge`, `.sertor/sertor-cli-reference.md`, `.sertor/.sertor-version`, blocco `SERTOR:RAG-USAGE` in CLAUDE.md | Dogfoodiamo **tutto** il RAG, non un sottoinsieme | **Should** | 🔄 **file byte assorbiti da FEAT-002** (hook `sertor-rag-usage-check.ps1`, skill `guided-setup`, agent `concierge` ora nel dogfood via sync). **Resta il non-byte:** wiring PreToolUse in `settings.json`, `.sertor/sertor-cli-reference.md` + `.sertor/.sertor-version` (dest gitignorata), blocco `SERTOR:RAG-USAGE` in CLAUDE.md → **process-fidelity (FEAT-001)** |
| FEAT-004 | **Riconciliazione divergenze hand-authored** — `.mcp.json` (dev venv-form vs runtime `.sertor/`-form), `.sertor/.env`, blocchi CLAUDE.md (marker-block vs prosa italiana): per ciascuno **adotta la forma-client o dichiara la divergenza-dev** (+ guardia) | Nessuna divergenza silenziosa dogfood↔client | **Should** | da decomporre |
| FEAT-005 | **Installer preservante su `plan-template.md`** (≡ **E10-FEAT-028**, cross-ref) — backup/restore o replace-if-upstream attorno a `specify init --force` | Prerequisito per la process-fidelity **governance** (il dogfood può usare `sertor-flow install` senza perdere il mission-gate) | **Should** | 📋 (E10-FEAT-028) |
| FEAT-006 | **Template ↔ realtà (staleness inversa)** — allineare i template **indietro** rispetto al dogfood (`wiki.config.toml.tmpl`: `explainers`/`audit`/`strings`/`roles.vcs`/`rag`), o dichiarare le estensioni dogfood | Il template riflette la realtà che un client dovrebbe ricevere | **Could** | da decomporre |

*Fetta già consegnata:* **E10-FEAT-027** (SpecKit machinery via script isolato) — prima superficie resa fedele; l'harness FEAT-001 la assorbirà come caso.

## 8. Decisioni (risolte 2026-07-03)
- **Modello target = SANDBOX.** L'harness (FEAT-001) installa i veri installer su un **clone** del repo e
  confronta l'esito col dogfood committato — **non tocca mai il repo** (R-1). Il modello «il dogfood è un
  output d'install» è scartato per ora (esigerebbe preservazione totale prima; più rischioso).
- **Divergenze hand-authored = DICHIARA-O-ELIMINA per-artefatto.** Per ogni divergenza: se è una
  comodità-dev legittima (es. `.mcp.json` col venv monorepo) la si **dichiara** (dev≠client documentato +
  guardia); se accidentale la si **elimina** (il dogfood adotta la forma-client). Decisione caso-per-caso nel
  `plan` di FEAT-004. *(No «elimina tutto» — over-engineering; no «dichiara tutto» — nasconderebbe le accidentali.)*
- **Priorità = ASSET-FIDELITY PRIMA.** Prima **FEAT-002** (sync completo + guardie: chiude il drift silenzioso,
  cheap, è la fondazione del confronto dell'harness), poi FEAT-003, poi FEAT-001 (harness), FEAT-004/005/006 a
  seguire. FEAT-005 (`plan-template` preservante) resta piccolo e sblocca la governance quando serve.
