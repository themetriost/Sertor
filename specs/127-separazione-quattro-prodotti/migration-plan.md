# Piano di migrazione — separazione di Sertor in quattro prodotti

> **Stato:** piano di dettaglio, **non** eseguito. Prodotto il 2026-07-31 su `master` = `c7a0f02`
> (`/VERSION` 0.4.1). Ogni numero qui dentro è **misurato sul repo**, non stimato.

## 0. Il bersaglio

Quattro prodotti indipendenti, ognuno **rilasciabile e installabile su un ospite terzo, host-agnostico
su Claude e Copilot CLI**, esattamente come Sertor oggi:

| Prodotto | Cosa è | Repo | Stato del folder |
|---|---|---|---|
| **Sertor** | Il RAG: retrieval, code-graph, memoria conversazioni, osservabilità, MCP | `C:\Workspace\Git\Sertor` | esistente (resta qui) |
| **Thesmion** | Il sistema-wiki: nucleo deterministico + layer agentico + rituale + gate | `C:\Workspace\Git\Thesmion` | **vuoto, non è un repo git** |
| **Sulcimen** | Il metodo: governance/SDLC, SpecKit, costituzione, SpecLift/SpecAudit | `C:\Workspace\Git\Sulcimen` | **vuoto, non è un repo git** |
| **ProtoSertor** | Il prototipo congelato (4 approcci RAG su corpus FastAPI) | `C:\Workspace\Git\ProtoSertor` | **da creare** |

**Vincolo trasversale (dal goal):** ogni nodo deve avere il proprio installer, i propri asset in forma
nativa per **entrambi** gli assistenti, le proprie guardie di parità, il proprio ciclo di rilascio
(`VERSION`/tag/Release/annuncio) e il proprio gate d'aggiornamento. *Nessun nodo può essere "quello che
si installa a mano".*

---

## 1. Inventario misurato

### 1.1 Codice di produzione (righe, `*.py` esclusi `__pycache__`)

| Area | Righe | Destinazione |
|---|---:|---|
| `src/sertor_core/services` | 5.484 | Sertor |
| `src/sertor_core/wiki_tools` | **3.146** | **Thesmion** |
| `src/sertor_core/adapters` | 2.270 | Sertor |
| `src/sertor_core/cli` | 2.122 | Sertor |
| `src/sertor_core/domain` | 1.101 | Sertor (+ kernel condiviso, §3.2) |
| `src/sertor_core/engines` | 469 | Sertor |
| `src/sertor_mcp` | 601 | Sertor |
| `packages/sertor` (installer wiki+rag) | 5.435 | **da spezzare** (§4.3) |
| `packages/sertor-install-kit` | 2.552 | **condiviso** (§3.1) |
| `packages/speclift` | 2.382 | Sulcimen |
| `packages/specaudit` | 1.534 | Sulcimen |
| `packages/sertor-flow` | 1.152 | Sulcimen |
| **Totale produzione** | **~30.485** | |

### 1.2 Artefatti non-codice (file tracciati in git: 1.695 totali)

| Area | File | Destinazione |
|---|---:|---|
| `specs/` | 601 (81 directory) | ripartiti, §4.6 |
| `wiki/` | 205 | ripartiti, §4.7 |
| `tests/` (root) | 174 | 131 Sertor · 21 Thesmion · 3 CI |
| `requirements/` | 105 (16 epiche) | ripartite, §4.5 |
| `prototype/` | 90 | **ProtoSertor** |
| `.claude/` | 40 | ripartiti per capability, §4.4 |
| `docs/` | 10 | ripartiti, §4.8 |
| `scripts/` | 4 | 3 Sertor · 1 per nodo |
| `eval/` | 3 | Sertor |
| `.github/workflows/` | 2 | replicati per nodo |

### 1.3 Test per prodotto

| Suite | File | Destinazione |
|---|---:|---|
| root `tests/` — RAG core | 131 | Sertor |
| root `tests/` — `wiki_tools`/rituale | **21** | Thesmion |
| root `tests/` — installer/CI/smoke | 3 | ripartiti |
| root `tests/` — fixture e `conftest` (i 19 restanti dei 174) | 19 | **duplicati**: ogni nodo ha bisogno delle proprie |
| `packages/sertor/tests` | 58 → **16 rag · 5 wiki · 37 di meccanismo** | i 37 seguono il **kit**, §3.1 |
| `packages/speclift/tests` | 33 | Sulcimen |
| `packages/sertor-flow/tests` | 26 | Sulcimen |
| `packages/sertor-install-kit/tests` | 24 | segue il kit (§3.1) |
| `packages/specaudit/tests` | 19 | Sulcimen |

---

## 2. I punti di sutura, misurati

Questa è la parte che decide la fattibilità. **Nessuna è una supposizione**: ogni riga è stata
verificata con `grep` sui sorgenti.

| # | Sutura | Misura reale | Difficoltà |
|---|---|---|---|
| S1 | `wiki_tools` → `observability.logging.log_event` | **11 import** | media — serve un `log_event` proprio |
| S2 | `wiki_tools` → `domain.errors.{ConfigError,SertorError}` | **5 import** | bassa — 2 classi |
| S3 | `wiki_tools` → `config.settings.Settings` | **1 import lazy** (solo in `indexing.py`) | bassa |
| S4 | `wiki_tools` → `composition.build_indexer` | **1 import lazy** (rag-sync) | bassa — già iniettabile |
| S5 | `install-kit` → `sertor_core` | **ZERO** (le 2 occorrenze sono commenti che dichiarano l'indipendenza) | nessuna |
| S6 | `sertor-flow` → `sertor_core` | **ZERO** (dipende solo dal kit) | nessuna |
| S7 | `speclift`/`specaudit` → core | stdlib; `speclift/adapters/rag_sertor.py` (Adapter A) è **dormiente** | bassa |
| S8 | `prototype/` → `sertor_core` | **ZERO import** | nessuna |
| S9 | `installer sertor` → core + kit | `install_wiki.py` importa `wiki_tools.{profile,structure}` | media — segue Thesmion |

**La conclusione che il piano sfrutta:** i tre nodi non-RAG sono **già quasi separati**. Sulcimen
(`sertor-flow`) e ProtoSertor (`prototype/`) hanno **zero** accoppiamento; Thesmion ne ha **quattro**,
di cui due lazy e uno (S4) è *per definizione* l'integrazione col RAG. Il taglio più costoso è
**S1** (il logging), non l'architettura.

### 2.1 Il caso S4 — il rag-sync è già progettato per il taglio

`wiki_tools/indexing.py::index_wiki` ha già: import **lazy** del composition root, parametro
`indexer_factory` iniettabile, e **no-op dichiarato** se `rag.enabled=false`. Cioè: Thesmion può
dipendere da Sertor **come extra opzionale** (`thesmion[rag]`), e senza quell'extra il comando
`index` risponde «disabilitato», non esplode. *La dipendenza è già invertita nel design; il piano deve
solo renderla esplicita nel packaging.*

---

## 3. Le sette decisioni di design (con raccomandazione)

Queste vanno sciolte **prima** di muovere un file. Per ognuna do la raccomandazione e il perché;
sono decisioni tue, ma il piano assume la raccomandazione.

### D1 — `sertor-install-kit`: chi lo possiede? ⭐ **la decisione che struttura tutto**

Il kit (2.552 righe, stdlib-only, zero dipendenze) è il **motore di installazione** usato da tutti e
tre gli installer: tassonomia `Artifact`/`ArtifactKind`, `AssistantId` (claude · copilot-cli),
`Surface`, merge di `settings.json`/`.mcp.json`/`.env`, `lifecycle` (install/upgrade/uninstall),
`model_policy`, `sync`, `report`.

| Opzione | Pro | Contro |
|---|---|---|
| **(a) Repo proprio, quarto pacchetto tecnico** ⭐ | una sola implementazione; ogni nodo lo pinna a una versione; l'host-agnosticità (il *cuore* del vincolo del goal) ha **un solo posto in cui essere corretta** | un repo in più da rilasciare; i tre nodi devono aggiornarsi quando cambia |
| (b) Vendorato in ciascun nodo con guardia di parità | zero dipendenze cross-repo; è il precedente già adottato per `_hooklib.py` (byte-identico ×3 con guardia) | tre copie di 2.552 righe che divergono; una correzione di portabilità va applicata tre volte |
| (c) Resta in Sertor, gli altri dipendono da `git+url` Sertor | zero lavoro iniziale | **Thesmion e Sulcimen dipenderebbero da Sertor per esistere** — nega la separazione |

**Raccomandazione: (a)**, con nome neutro (proposta: **`agentkit-install`** o `install-kit`, non
`sertor-*`). Motivo decisivo: il goal chiede che *ogni* nodo sia host-agnostico su due assistenti; la
logica che rende host-agnostico **è** il kit. Con (b) la promessa «host-agnostico» diventa tre
promesse indipendenti che nessuno riconcilia — è esattamente il difetto già distillato in
[[pratica-standing-vs-pratica-distribuita]]. Con (c) la separazione è finta.

> **La prova numerica, trovata verificando questo piano.** Dei 58 test di `packages/sertor/tests`,
> solo 21 riguardano una capability (16 rag + 5 wiki): gli altri **37 sono guardie di meccanismo** —
> `assets_copilot_parity`, `surface_parity`, `portable_hooks_parity`, `schema_copilot_frontmatter`,
> `schema_copilot_hooks`, `model_policy_guard`, `host_agnostic`, `settings_merge`, `claude_md`,
> `copilot_hook_presence`, `assets_english`, `assets_hook_breadcrumb`… Sono **esattamente le guardie
> che verificano il vincolo del goal**. Con D1-b andrebbero triplicate o spartite arbitrariamente; con
> D1-a restano dove vive ciò che verificano. *Il kit non è un dettaglio di packaging: è il luogo in cui
> «host-agnostico su Claude e Copilot» è una proprietà verificata invece che una promessa ripetuta.*

> **Nota:** il precedente `_hooklib.py` (245 righe, duplicato ×3 con guardia) resta valido per un
> payload *piccolo e stabile*. 2.552 righe di logica di installazione non sono quel caso.

### D2 — Il kernel condiviso (S1+S2+S3): logging, errori, config

Thesmion ha bisogno di `log_event`, `ConfigError`/`SertorError`, e (solo per il rag-sync) `Settings`.

| Opzione | Valutazione |
|---|---|
| **(a) Thesmion reimplementa le 3 primitive** ⭐ | `log_event` è un wrapper su `logging` con campi strutturati; gli errori sono 2 classi. Costo stimato **~150-200 righe**. Zero dipendenze. |
| (b) Un pacchetto `*-common` condiviso | quarto pacchetto tecnico per 200 righe: sproporzionato |
| (c) Il kit ospita anche queste primitive | il kit è *installazione*, non runtime: mescolare i due concerns è un errore di altitudine |

**Raccomandazione: (a).** Le primitive sono piccole e stabili; duplicarle costa meno che accoppiare
due prodotti. **Vincolo:** il formato degli eventi deve restare **compatibile** (stesso nome campo,
stesso schema JSON), perché entrambi scrivono nell'osservabilità dell'ospite.

### D3 — SpecLift e SpecAudit: dove vanno?

Sono la pipeline diff→requisiti EARS ancorati (2.382 + 1.534 righe, epica E14). Vivono nel repo come
**vendored self-host**, e la loro distribuzione è già tracciata come *«casa: `sertor-flow`»*
(E14-FEAT-002, tuttora aperta: 3.916 righe **non installabili da nessuno**).

**Raccomandazione: Sulcimen.** Sono strumenti di *metodo* (requisiti, audit di conformità
spec↔codice), non di retrieval. La loro casa era già stata decisa: la separazione la realizza.
*Effetto collaterale positivo:* E14-FEAT-002 smette di essere un debito e diventa parte della
definizione di Sulcimen.

### D4 — Il wiki del dogfood (205 pagine): si divide o resta?

**Raccomandazione: si divide, con criterio di proprietà, e ogni nodo nasce con il proprio wiki**
(che è il dogfood di Thesmion). Il criterio, in ordine di precedenza:

1. **Pagine di prodotto** → seguono il prodotto (es. `hybrid-retrieval` → Sertor; `wiki-tools`,
   `ritual-check`, `daily-distill-floor`, `wiki-guard` → Thesmion; `sertor-flow`, `speclift`,
   `constitution` → Sulcimen).
2. **Record datati e log** (58 log + 35 experiments) → **restano in Sertor** come archivio storico
   (sono la cronaca del monorepo; spezzarli per data è arbitrario e distruggerebbe i riferimenti).
   I nuovi nodi partono con un log vuoto: `## [data] setup | nascita del nodo`.
3. **Pagine-lezione trasversali** (`guardia-verde-non-e-una-misura`, `il-rimedio-ricade-nel-difetto`,
   `riassunto-invecchia-senza-riconciliatore`, `identita-per-presenza-o-per-contenuto`,
   `potere-retrospettivo-di-una-guardia`, `host-agnostico-non-e-risolvibile`,
   `riuso-che-eredita-il-presupposto`, `default-masked-defect`, `deterministic-vs-judgment`, …):
   **copiate in tutti i nodi che le applicano**, con nota di provenienza. Sono conoscenza di
   ingegneria, non di prodotto: il costo della copia è minore del costo di renderle irraggiungibili.
   *(Alternativa da valutare in futuro: un quinto nodo «second brain» — è già l'idea E9, §8.)*

### D5 — La storia git

**Raccomandazione: `git filter-repo` con `--path` per i sottoalberi migrati**, non copia piatta.
Motivo: 601 file di `specs/` e 205 pagine wiki hanno una storia che **è** la loro giustificazione
(perché una decisione è stata presa). Perdere quella storia significa che il primo `git log` su
Thesmion racconta «tutto creato oggi», che è falso e non riparabile dopo.

Procedura per nodo: clone → `filter-repo --path <sottoalberi>` → riscrittura dei path (`--path-rename`)
→ push su un remote nuovo. **Il repo Sertor resta intatto**; la rimozione dei file migrati avviene in
una PR normale, dopo la verifica del nodo nuovo.

### D6 — Nome dei pacchetti Python e dei comandi

| Nodo | Pacchetto | CLI | MCP |
|---|---|---|---|
| Sertor | `sertor-core` (invariato) | `sertor-rag` (invariato), `sertor` (installer, **solo `rag`**) | `sertor-rag` (invariato) |
| Thesmion | `thesmion-core` | `thesmion-tools` (era `sertor-wiki-tools`), `thesmion` (installer) | — (non ne ha bisogno) |
| Sulcimen | `sulcimen` | `sulcimen` (era `sertor-flow`), + `speclift`, `specaudit` | — |
| ProtoSertor | — (non è un pacchetto) | script esistenti | — |

**Compatibilità:** `sertor-wiki-tools` e `sertor install wiki` restano come **alias deprecati** per
una release (avviso che nomina il sostituto), poi rimossi. Motivo: gli ospiti reali (Acta, Kaelen,
Noetix, …) li hanno cablati in hook e istruzioni; romperli in silenzio è il difetto E10-FEAT-064.

### D7 — Il dogfood incrociato (chi installa chi)

**Raccomandazione: ogni nodo è client degli altri**, che è la prova più forte di host-agnosticità:

| Nodo | Installa | Perché |
|---|---|---|
| Sertor | Thesmion (wiki) + Sulcimen (SDLC) | ha bisogno di wiki e metodo |
| Thesmion | Sertor (rag, per il proprio corpus) + Sulcimen | dogfood del rag-sync (S4) su un ospite **vero** |
| Sulcimen | Sertor + Thesmion | idem |
| ProtoSertor | Sertor (rag, come corpus congelato) | è già oggi il corpus di dogfooding |

*Effetto:* dal giorno del taglio, ogni nodo **è** un ospite terzo per gli altri due — la condizione
che finora abbiamo dovuto simulare con host usa-e-getta.

---

## 4. Matrice artefatto → destinazione (completa)

### 4.1 `src/sertor_core/`

| Modulo | Righe | → | Nota |
|---|---:|---|---|
| `adapters/`, `engines/`, `services/`, `config/`, `composition.py` | ~11.000 | **Sertor** | il RAG, invariato |
| `domain/{entities,ports,memory,agent_context}.py` | ~900 | **Sertor** | |
| `domain/errors.py` | ~200 | **Sertor** + **copia ridotta in Thesmion** | S2: 2 classi |
| `observability/{store,capture,scrub,otel,tui,live}.py` | ~2.000 | **Sertor** | |
| `observability/logging.py` | ~100 | **Sertor** + **copia in Thesmion** | S1: 11 call-site |
| `cli/` | 2.122 | **Sertor** | CLI `sertor-rag` |
| `wiki_tools/` (17 moduli) | **3.146** | **Thesmion** | il nucleo deterministico |
| `sertor_mcp/` | 601 | **Sertor** | |

**Dettaglio `wiki_tools/` (tutti e 17 vanno in Thesmion):** `__main__`, `collect`, `contracts`,
`coverage`, `distill_audit`, `frontmatter`, `indexing`*, `lint`, `move`, `profile`, `reconcile`,
`registry`, `ritual_check`, `scan`, `structure`, `vcs`, `__init__`.
*`indexing.py` = il rag-sync: diventa `thesmion[rag]` (S4).

### 4.2 `packages/` esistenti

| Package | → | Azione |
|---|---|---|
| `sertor-install-kit` | **repo proprio** (D1) | rinomina neutra; i tre installer lo pinnano |
| `sertor-flow` | **Sulcimen** | rinomina `sulcimen`; già zero-accoppiato (S6) |
| `speclift` | **Sulcimen** | de-vendoring: diventa membro del workspace Sulcimen |
| `specaudit` | **Sulcimen** | idem |
| `sertor` (installer) | **da spezzare** → §4.3 | |

### 4.3 Lo split dell'installer `packages/sertor` (5.435 righe)

| Modulo | Righe | → |
|---|---:|---|
| `install_rag.py` | 1.324 | **Sertor** |
| `configure.py` + `configure_fields.py` + `configure_report.py` | 689 | **Sertor** (configura `.env` del RAG) |
| `rag_profile.py` | 98 | **Sertor** |
| `install_wiki.py` | 713 | **Thesmion** |
| `config_gen.py` | 66 | **Thesmion** (genera `wiki.config.toml`) |
| `__main__.py` | 633 | **da spezzare in due** — `sertor` (verbi rag) e `thesmion` (verbi wiki); i verbi `upgrade`/`uninstall`/`doctor` sono per-nodo |
| `sync.py`, `resources.py`, `surfaces.py`, `artifacts.py`, `claude_md.py`, `settings_merge.py`, `report.py`, `mcp_merge.py`, `gitignore_append.py`, `env_merge.py`, `command_runner.py` | ~230 | **duplicati sottili in entrambi** (sono 6-30 righe ciascuno: adattatori verso il kit) |

### 4.4 Asset host-facing (`.claude/` + bundle) — la parte che rende vero «host-agnostico»

| Asset | Oggi | → |
|---|---|---|
| `skills/wiki-author/**` (12 file: SKILL, playbook, page/log/wiki-craft, 9 `ops/`) | `assets/claude/skills/` | **Thesmion** |
| `agents/wiki-curator.md` | `assets/claude/agents/` | **Thesmion** |
| `commands/wiki.md` | `assets/claude/commands/` | **Thesmion** |
| `hooks/{wiki-guard,wiki-pending-check,wiki-session-start,distill-floor}.py` | `assets/claude/hooks/` | **Thesmion** |
| `wiki.config.toml.tmpl` | `assets/` | **Thesmion** |
| blocco `SERTOR:WIKI-RITUAL` (CLAUDE.md righe 716-828) | `assets/claude-md-block.md` | **Thesmion** → `THESMION:RITUAL` |
| `skills/{guided-setup,eval-suite-author,eval-feedback}` | `assets/rag/skills/` | **Sertor** |
| `agents/concierge.md` | `assets/rag/agents/` | **Sertor** |
| `hooks/{rag-freshness,rag-freshness-start,version-check,version-check-start,memory-capture,sertor-rag-usage-check}.py` | `assets/rag/hooks/` | **Sertor** |
| `env.{local,azure}.tmpl`, `mcp.server.json.tmpl`, `settings.*.json` (6), `sertor-cli-reference.md`, `gitattributes` | `assets/rag/` | **Sertor** |
| blocco `SERTOR:RAG-USAGE` (righe 664-714) | `assets/rag/claude-md-block-rag-usage.md` | **Sertor** |
| `agents/{configuration-manager,requirements-analyst}.md`, `skills/requirements/` | `sertor-flow/assets/claude/` | **Sulcimen** |
| `constitution-starter.md`, `init-options.json.tmpl`, `integrations/*.tmpl`, blocco `SERTOR:SDLC-RITUAL` (righe 587-662) | `sertor-flow/assets/` | **Sulcimen** |
| `skills/speckit-*` (**9**) | machinery SpecKit | **Sulcimen** (li installa già) |
| `hooks/_hooklib.py` (245 righe) | duplicato ×3 byte-identico | **duplicato in tutti e tre**, con la guardia di parità già esistente |
| `skills/{acta,speclift,specaudit}` | — | `acta` → resta locale (nodo esterno); `speclift`/`specaudit` → **Sulcimen** |

### 4.5 `requirements/` (16 epiche, 105 file)

| Epica | → | Nota |
|---|---|---|
| `sertor-core`, `sertor-cli`, `retrieval-qualita`, `osservabilita`, `memoria-conversazioni`, `backend-store-scala`, `ingestione-estesa`, `conoscenza-schema-sql` | **Sertor** | 8 epiche |
| `evoluzione-modello-wiki` (E16) | **Thesmion** | interamente wiki |
| `speclift` (E14) | **Sulcimen** | |
| `usabilita` (E12), `documentazione-marketing` (E13), `debito-tecnico` (E10), `fedelta-dogfood` (E15), `multiutente` (E11), `second-brain` (E9) | **da spezzare per riga** | ogni FEAT segue la capability che nomina |

> **⚠️ Attenzione, ed è il lavoro più delicato di tutta la migrazione — con un dato che cambia le
> proporzioni.** Ho classificato le **67 righe FEAT di E10** per parola chiave: **43 nominano il
> wiki**, 13 il RAG, 11 la governance. Cioè **E10 `debito-tecnico` è in maggioranza debito di
> Thesmion**, non di Sertor — il contrario di quanto suggerirebbe il nome del repo che la ospita.
> *(La classificazione lessicale ha falsi positivi — «log» dentro «logging» — quindi il numero va
> confermato a mano; l'ordine di grandezza no.)*
>
> Conseguenza per il piano: **Thesmion nasce ereditando la maggior parte del debito aperto**, e il suo
> backlog non è un file vuoto da riempire ma il pezzo più grosso della ripartizione. Le 26 voci aperte
> di E10 vanno lette **una per una con verdetto scritto** (F4.6): assegnarle male significa perderle,
> ed è esattamente il difetto già pagato il 30/07 quando un classificatore lessicale sbagliò in
> entrambi i versi su un campo `Stato`.

### 4.6 `specs/` (81 directory, 601 file)

Classificazione di partenza (euristica sui nomi, **da confermare a mano**): **26 Sertor · 11 Thesmion
· 5 Sulcimen · 31 installer/distribuzione (da ripartire per capability) · 8 dubbie**.

Le 8 dubbie, già risolte a giudizio: `010-query-congiunta` → Sertor · `046-refresh-incrementale` →
Sertor · `069-qualita-fusione-code-doc` → Sertor · `070-search-combined-strutturato` → Sertor ·
`096-doc-utente-mvp` → **replicata** (ogni nodo ha le sue docs) · `113-freshness-postrepair-lock` →
Sertor · `123-ancora-derivata-scan` → **Thesmion** · `124-copertura-changeset-scan` → **Thesmion**.

**Regola per le 31 «installer»:** una spec di distribuzione segue la **capability che distribuisce**
(`012-sertor-install-wiki` → Thesmion; `015-sertor-install-rag` → Sertor; `045-distribuzione-copilot-flow`
→ Sulcimen); quelle sul **meccanismo** (`044-distribuzione-copilot`, `048-lifecycle-installer`,
`056-parita-asset-copilot`, `082-parity-guard-budget`, `083-default-model-policy`, `095-portable-hooks`)
seguono il **kit** (D1).

### 4.7 `wiki/` (205 pagine) — criterio in D4

Ripartizione **verificata** (classificate una per una le 60 pagine di `concepts/` + `tech/`):

| Area | File | Ripartizione |
|---|---:|---|
| `concepts/` + `tech/` | **60** | **25 Sertor** · **7 Thesmion** · **5 Sulcimen** · **10 kit/distribuzione** · **13 trasversali** (§D4.3) |
| `log/` | 58 | **Sertor** (archivio storico del monorepo) |
| `experiments/` | 35 | **Sertor** (record datati) |
| `sources/` | 28 | **Sertor** (+ `karpathy-llm-wiki`, `llm-wiki-v2-agentmemory` → **Thesmion**: sono le fonti *fondative* del sistema-wiki) |
| `syntheses/` | 12 | `architettura-wiki-llm`, `sistema-wiki-fonte-unica`, `lint-semantico-host-agnostico`, `lint-organizzativo-e-reorg` → **Thesmion**; `roadmap`+`storico-roadmap` → **una nuova per nodo**; audit datati → Sertor |
| `explainers/` | 10 | seguono la capability spiegata |

**Dettaglio delle 7 pagine Thesmion** (concepts+tech): `wiki-tools`, `ritual-check`, `wiki-guard`,
`daily-distill-floor`, `step-ritual`, `diary-vs-graph`, `wiki-role-da-w1`.
**Delle 5 Sulcimen:** `constitution`, `sertor-flow`, `speclift`, `specaudit`,
`product-plane-vs-fixture-plane`.
**Le 10 «kit/distribuzione»** (`assistant-targeting`, `installer-lifecycle`, `sertor-install-kit`,
`sertor-installer`, `identita-hook-nel-merge`, `auto-update-version-check`, `dogfooding`,
`dogfood-fidelity`, `esito-sull-host-vs-forma-dell-asset`, `host-agnostico-non-e-risolvibile`)
seguono **D1**: se il kit diventa un prodotto, sono la sua documentazione.
**Le 13 trasversali** (`guardia-verde-non-e-una-misura`, `potere-retrospettivo-di-una-guardia`,
`il-rimedio-ricade-nel-difetto`, `riassunto-invecchia-senza-riconciliatore`,
`identita-per-presenza-o-per-contenuto`, `riuso-che-eredita-il-presupposto`, `default-masked-defect`,
`fail-loud-fix-cause`, `deterministic-vs-judgment`, `pratica-standing-vs-pratica-distribuita`,
`audit-codice-morto`, `mission-vision`, `sessionstart-hook`) sono **conoscenza di ingegneria**: copiate
in ogni nodo che le applica, con nota di provenienza.

### 4.8 `docs/` (10 file) e radice

| File | → |
|---|---|
| `install.md` (914 righe) | **spezzato in tre**: la §5 (wiki) → Thesmion; §6+§2+§3+§4 (rag) → Sertor; §8 (SDLC) → Sulcimen; §0/§1/§9/§10 (meccanismo) **replicate e adattate** in ciascuno |
| `install-claude.md`, `install-copilot.md` | **replicati** per nodo (quick-start per assistente) |
| `getting-started.md`, `retrieval.md`, `reference.md`, `tutorial.md`, `troubleshooting.md`, `why-sertor.md`, `README.md` | **Sertor** (+ equivalenti nuovi per gli altri nodi) |
| `README.md`, `CHANGELOG.md`, `VERSION`, `LICENSE` | **uno per nodo** (nuovi per i tre) |
| `CLAUDE.md` (828 righe) | **spezzato**: prosa dogfood → resta in Sertor ridotta; i 3 blocchi marker seguono le capability; ogni nodo nasce con il proprio |
| `.mcp.json`, `.env.example` | **Sertor** (+ ogni nodo riceve quello di Sertor **installando** la capability rag) |
| `pyproject.toml`, `uv.lock` | uno per nodo |
| `Sertor.code-workspace` | Sertor (+ uno per nodo) |
| `.gitignore`, `.gitattributes` | replicati e adattati |
| `scripts/smoke.{ps1,sh}` | **replicati per nodo** (ognuno testa il proprio installer) |
| `scripts/dev/relock-runtime.ps1` | **replicato per nodo** (dogfood che insegue HEAD) |
| `scripts/dev/materialize-speckit.ps1` | **Sulcimen** |
| `eval/` (3 file) | **Sertor** |
| `.github/workflows/{ci,upgrade-smoke-full}.yml` | **replicati per nodo**, con le suite del nodo |

---

## 5. Il piano, in fasi

Ordine scelto per **rischio crescente** e per lasciare `master` sempre verde. Ogni fase ha un
**criterio d'uscita falsificabile**.

### F0 — Preparazione (nessun file spostato)

| Step | Azione | Uscita |
|---|---|---|
| F0.1 | Sciogliere D1–D7 con l'utente; registrare le decisioni in questo documento | 7 decisioni scritte |
| F0.2 | Creare `C:\Workspace\Git\ProtoSertor`; `git init` sui tre folder; creare i 3 repo remoti | 4 remote raggiungibili |
| F0.3 | **Congelare il perimetro**: nessuna nuova feature sui sottoalberi in migrazione finché F5 non chiude | dichiarato nell'EXEC |
| F0.4 | Fotografare la baseline: `ruff` + le **7 suite** (2.534 test) verdi su `master`, e salvare i numeri | baseline scritta |

### F1 — ProtoSertor (il taglio a rischio zero, che rompe il ghiaccio)

Perché primo: **zero import** verso il core (S8), 90 file, nessun asset host-facing, nessun installer.
È la prova che la procedura `filter-repo` + verifica funziona, pagata sul caso più semplice.

| Step | Azione | Uscita |
|---|---|---|
| F1.1 | `filter-repo --path prototype/ --path-rename prototype/:` su un clone | storia dei 90 file preservata (`git log` non vuoto) |
| F1.2 | `README.md` proprio: cos'è, che è **congelato**, come si interroga | presente |
| F1.3 | `.env.example`, `requirements.txt` del prototipo | presenti |
| F1.4 | Installare **Sertor rag** su ProtoSertor (è il suo corpus) e ricostruire l'indice | `search_code` risponde su ProtoSertor |
| F1.5 | In Sertor: rimuovere `prototype/`, aggiornare `CLAUDE.md` (sezione *Riferirsi al prototipo*), `.mcp.json` (corpus), `wiki.config.toml` | 7 suite verdi |
| **Uscita F1** | il RAG di dogfooding interroga ProtoSertor **da un altro repo**, e Sertor non contiene più `prototype/` | |

### F2 — Il kit (D1): estrarre il motore di installazione

| Step | Azione | Uscita |
|---|---|---|
| F2.1 | `filter-repo --path packages/sertor-install-kit/` → repo proprio | 24 test verdi nel nuovo repo |
| F2.2 | Rinomina neutra del pacchetto + `VERSION`/`CHANGELOG`/CI propri | pubblicabile via `git+url` |
| F2.3 | In Sertor: `sertor` e `sertor-flow` puntano al kit **esterno** pinnato | 7 suite verdi |
| F2.4 | Guardia: nessun `import sertor_install_kit` residuo da path locale | grep = 0 |
| **Uscita F2** | il kit è un prodotto a sé, i due installer lo consumano pinnato, la CI di Sertor è verde | |

### F3 — Sulcimen (il nodo già indipendente)

Perché prima di Thesmion: **zero accoppiamento** col core (S6), e porta con sé `speclift`/`specaudit`
chiudendo E14-FEAT-002.

| Step | Azione | Uscita |
|---|---|---|
| F3.1 | `filter-repo --path packages/sertor-flow/ --path packages/speclift/ --path packages/specaudit/ --path .specify/` | storia preservata |
| F3.2 | Workspace `uv` proprio: `sulcimen` + `speclift` + `specaudit`; rinomina CLI con alias deprecato (D6) | 26+33+19 = **78 test verdi** |
| F3.3 | Asset: agenti (`configuration-manager`, `requirements-analyst`), skill (`requirements`, `speckit-*`, `speclift`, `specaudit`), `constitution-starter`, blocco `SDLC-RITUAL` → `SULCIMEN:RITUAL` | parity guard claude↔copilot verde |
| F3.4 | **Ripartizione requirements/specs**: E14 intera + le righe SDLC di E10/E12/E13/E15, **una per una con verdetto scritto** | ogni riga assegnata, zero orfane |
| F3.5 | `docs/` proprie (install + quick-start ×2 assistenti), `README`, `VERSION` 0.1.0, `CHANGELOG` | doc utente completa |
| F3.6 | CI propria: test + lint + **smoke d'installazione** su 4 combinazioni (2 OS × 2 assistenti) | 4 verdi |
| F3.7 | `scripts/smoke.{ps1,sh}` + `upgrade-smoke-full.yml` adattati; **gate d'aggiornamento** con esiti nominati | esiti asseriti, zero `n/a` |
| F3.8 | Sulcimen installa sé stesso (dogfood) + Sertor + Thesmion (quando esisterà) | `.sertor/`, `.thesmion/` presenti |
| F3.9 | In Sertor: rimuovere i 3 package e `.specify/`, installare Sulcimen come **ospite** | 7 suite verdi (meno le 78 migrate) |
| **Uscita F3** | `uvx --from git+…Sulcimen sulcimen install --assistant claude,copilot-cli` funziona su un host pulito, verificato dallo smoke | |

### F4 — Thesmion (il taglio con le quattro suture)

| Step | Azione | Uscita |
|---|---|---|
| F4.1 | **Prima del taglio**: in Sertor, isolare S1/S2 dietro un modulo `wiki_tools/_kernel.py` (log_event + errori) — **rifattorizzazione interna a Sertor, CI verde**, così il taglio successivo è meccanico | 21 test wiki verdi, 0 import diretti da `observability`/`domain` in `wiki_tools` |
| F4.2 | `filter-repo`: `src/sertor_core/wiki_tools/` + i **21 test** + `packages/sertor/src/sertor_installer/install_wiki.py`+`config_gen.py` + le 4 test-suite wiki del package | storia preservata |
| F4.3 | Pacchetto `thesmion-core`; CLI `thesmion-tools` (alias `sertor-wiki-tools` deprecato); installer `thesmion install` | 25 test verdi |
| F4.4 | S4: `indexing.py` → extra `thesmion[rag]`; **senza l'extra** `index` risponde «disabilitato» e non esplode | test dei due rami |
| F4.5 | Asset: skill `wiki-author` (12 file), agente `wiki-curator`, comando `wiki`, 4 hook + `_hooklib`, `wiki.config.toml.tmpl`, blocco `THESMION:RITUAL` | parity guard verde |
| F4.6 | Ripartizione: E16 intera + **le righe wiki di E10 (≈43 su 67, misurate)** + 11 spec + le 7 pagine-entità + 4 syntheses + 2 sources fondative | zero orfane; conteggio prima/dopo che torna |
| F4.7 | `docs/`, `README`, `VERSION` 0.1.0, `CHANGELOG`; CI + smoke 4 combinazioni + gate d'aggiornamento | 4 verdi, esiti nominati |
| F4.8 | Thesmion installa Sertor (rag) per il proprio wiki → **prova reale di S4 su un ospite terzo** | `thesmion-tools index` popola una collezione |
| F4.9 | In Sertor: rimuovere `wiki_tools/` + i 21 test + `install_wiki.py`; **installare Thesmion come ospite**; il wiki di Sertor continua a funzionare *dall'esterno* | 7 suite verdi; rituale invariato |
| **Uscita F4** | il gate `wiki-guard` e il rituale funzionano su Sertor **essendo installati da Thesmion**, non essendone parte | |

### F5 — Sertor, ripulito

| Step | Azione | Uscita |
|---|---|---|
| F5.1 | `sertor install` perde il verbo `wiki` (alias deprecato che **rimanda a Thesmion**, non fallisce muto) | test dell'alias |
| F5.2 | `CLAUDE.md` riscritto: prosa dogfood ridotta al RAG; i blocchi wiki/SDLC ora arrivano **installati** | budget righe rispettato |
| F5.3 | `docs/install.md` ridotta al RAG, con rimandi ai due nodi | doc coerente |
| F5.4 | EXEC/roadmap: tre roadmap separate + una vista federata | nessuna contraddizione |
| **Uscita F5** | Sertor = solo RAG, e riceve wiki e metodo come **un ospite qualsiasi** | |

### F6 — La verifica che vale più di tutte

| Step | Azione | Criterio |
|---|---|---|
| F6.1 | Host usa-e-getta pulito: installare **tutti e tre** i nodi, per **entrambi** gli assistenti | 3 × 2 = 6 install verdi |
| F6.2 | `upgrade` da versione precedente per ciascun nodo | esiti nominati, zero `n/a` |
| F6.3 | Conflitti fra nodi: `settings.json`, `.mcp.json`, `CLAUDE.md`, `.gitignore` scritti da **tre installer diversi** | nessuna sovrascrittura; ogni blocco è posseduto dal suo marker |
| F6.4 | `uninstall` di un nodo **non** rompe gli altri due | i due restanti restano verdi |
| **Uscita F6** | il criterio del goal è dimostrato, non affermato | |

### F7 — Federazione e chiusura

| Step | Azione |
|---|---|
| F7.1 | Annunciare i tre nodi nuovi sulla bacheca Acta (canale *Releases*) |
| F7.2 | Aggiornare i nodi esterni che usano Sertor (Acta, Kaelen, Noetix, Sinthari, …): l'`upgrade` deve dire **cosa è diventato cosa** |
| F7.3 | Rilascio coordinato: Sertor `0.5.0` (breaking: perde `wiki`), Thesmion/Sulcimen `0.1.0`, kit `0.1.0` |
| F7.4 | Rimuovere gli alias deprecati **una release dopo**, non subito |

---

## 6. Rilascio host-agnostico: la checklist che ogni nodo deve superare

Derivata da ciò che Sertor ha **già** e che il goal impone di replicare. Un nodo non è «fatto» finché
non ha tutte e dodici:

| # | Requisito | Verifica |
|---|---|---|
| 1 | Installer proprio con `install`/`upgrade`/`uninstall` | test di lifecycle |
| 2 | `--assistant claude,copilot-cli` (+ `all`) | test parametrico ×2 |
| 3 | Asset in forma **nativa** per ciascun assistente (nessun hack di compat) | parity guard |
| 4 | Hook portabili (`uv run --no-project python`, niente PowerShell) | smoke hook |
| 5 | Blocco istruzioni a marker, posseduto e ri-generabile | test idempotenza |
| 6 | `settings.json`/`.mcp.json` **merge**, mai sovrascrittura | test di merge con contenuto altrui |
| 7 | `VERSION` + `CHANGELOG` + tag + Release *latest* | rilascio verificato via API |
| 8 | Auto-updater (SessionStart/End) che avvisa e **non** aggiorna da solo | test dei due stati |
| 9 | Smoke d'installazione su 2 OS × 2 assistenti | 4 job verdi |
| 10 | **Gate d'aggiornamento** con esiti nominati e zero `n/a` | log letti, non exit code |
| 11 | Doc utente (`install.md` + quick-start per assistente) | presente e allineata |
| 12 | Dogfood: il nodo installa sé stesso dal proprio installer | `doctor` verde |

---

## 7. Rischi, con mitigazione

| # | Rischio | Perché è concreto | Mitigazione |
|---|---|---|---|
| R1 | **Le righe di E10/E15 vanno perse** nella ripartizione | 26 voci aperte, trasversali per costruzione; un classificatore lessicale sbaglia in entrambi i versi (già misurato il 30/07) | F3.4/F4.6: verdetto **scritto** per ogni riga; conteggio prima/dopo che deve tornare |
| R2 | **Il rituale si spezza durante F4** | il gate `wiki-guard` blocca lo Stop; se Thesmion non è ancora installabile, Sertor resta senza rituale | F4.9 **dopo** F4.8: si rimuove solo quando l'installazione dall'esterno è verificata |
| R3 | **Tre installer si pestano** sugli stessi file dell'ospite | `settings.json`, `CLAUDE.md`, `.mcp.json` scritti da tre sorgenti | F6.3 è un criterio d'uscita, non un controllo finale; ogni blocco ha marker distinto |
| R4 | **La storia git si perde** | 601 spec + 205 pagine la cui giustificazione **è** la storia | D5: `filter-repo`, mai copia piatta; verifica `git log` non vuoto su file campione |
| R5 | **Il kit diverge** in tre copie (se si sceglie D1-b) | è già successo con pratiche standing non distribuite | D1-a: un solo kit; se si sceglie (b), guardia di parità byte obbligatoria |
| R6 | **Gli ospiti esterni si rompono** (Acta, Kaelen, Noetix, …) hanno cablato `sertor install wiki` e `sertor-wiki-tools` | sono comandi in hook e istruzioni, non solo in doc | D6: alias deprecati per una release, con avviso che **nomina** il sostituto |
| R7 | **Il dogfood perde fedeltà** durante la transizione | per un periodo Sertor ha il wiki «a metà» | F4 è atomica per fase: o il wiki è dentro, o è installato — mai in mezzo |
| R8 | **Il CHANGELOG/EXEC di ogni nodo nasce vuoto** e la storia sembra inesistente | è la stessa malattia di [[riassunto-invecchia-senza-riconciliatore]] | ogni nodo nasce con una voce di log «nascita del nodo» che **punta** all'archivio in Sertor |

---

## 8. Cosa questo piano **non** decide (e va deciso dopo)

1. **Il nome del kit** (D1): `agentkit-install`, `install-kit`, altro — è un nome pubblico.
2. **Se le pagine-lezione meritano un quinto nodo** (il «second brain» dell'epica E9): il piano le
   **copia** in ciascun nodo, che è la scelta reversibile; unificarle in un nodo proprio è una
   decisione successiva e non blocca nulla.
3. **La sorte di E11 `multiutente`** (6 voci, 0 consegnate): riguarda tutti e tre i nodi.
4. **Se ProtoSertor debba restare privato** mentre gli altri sono pubblici.

---

## 9. Ordine consigliato e stima di sforzo relativo

| Fase | Rischio | Sforzo relativo | Reversibile? |
|---|---|---|---|
| F0 preparazione | nullo | 1× | sì |
| F1 ProtoSertor | **basso** (zero import) | 1× | sì |
| F2 kit | basso | 2× | sì |
| F3 Sulcimen | medio (78 test, 3 package) | 4× | sì, finché F3.9 non gira |
| F4 Thesmion | **alto** (4 suture + il rituale che ci gira sopra) | 6× | sì, finché F4.9 non gira |
| F5 Sertor ripulito | medio | 2× | no (è la conseguenza) |
| F6 verifica | basso | 2× | — |
| F7 federazione | basso | 1× | — |

**Il punto di non ritorno è F4.9**, non prima. Fino a lì ogni fase lascia `master` verde e il
monorepo funzionante.

---

## 10. Vista per nodo — cosa riceve ciascuno

### Sertor (resta, si alleggerisce)

**Codice:** `adapters` · `services` · `engines` · `domain` · `config` · `observability` ·
`composition` · `cli` (2.122) · `sertor_mcp` (601) · installer `install_rag`+`configure` (2.111)
≈ **15.000 righe**.
**Test:** 131 (root) + 16 (installer rag).
**Asset:** 3 skill (guided-setup, eval-suite-author, eval-feedback) · 1 agente (concierge) · 6 hook ·
6 `settings.*.json` · 2 template `.env` · `mcp.server.json.tmpl` · `sertor-cli-reference.md` · blocco
`SERTOR:RAG-USAGE`.
**Backlog:** 8 epiche intere + ~13 righe di E10 + le righe RAG di E12/E13/E15.
**Wiki:** 25 pagine-entità + 58 log + 35 experiments + 26 sources (l'archivio storico).
**Perde:** `wiki_tools/` (3.146) · `prototype/` (90 file) · 3 package (5.068) · `.specify/`.

### Thesmion (nuovo — il sistema-wiki)

**Codice:** `wiki_tools/` (3.146) + `install_wiki`+`config_gen` (779) + kernel proprio (~200, D2)
≈ **4.100 righe**.
**Test:** 21 (root) + 5 (installer wiki) = **26**.
**Asset:** skill `wiki-author` (12 file, incluso il playbook) · agente `wiki-curator` · comando
`wiki` · 4 hook + `_hooklib` · `wiki.config.toml.tmpl` · blocco `THESMION:RITUAL`.
**Backlog:** E16 intera + **~43 righe di E10** (il pezzo più grosso della ripartizione).
**Wiki:** 7 pagine-entità + 4 syntheses + 2 sources fondative + le 13 trasversali (copiate).
**Dipendenza opzionale:** `thesmion[rag]` → Sertor, solo per il rag-sync (S4).

### Sulcimen (nuovo — il metodo)

**Codice:** `sertor-flow` (1.152) + `speclift` (2.382) + `specaudit` (1.534) ≈ **5.068 righe**.
**Test:** 26 + 33 + 19 = **78**.
**Asset:** 2 agenti (configuration-manager, requirements-analyst) · skill `requirements` +
**9** `speckit-*` + `speclift` + `specaudit` · `constitution-starter` · template `.specify/` ·
manifest d'integrazione · blocco `SULCIMEN:RITUAL`.
**Backlog:** E14 intera + ~11 righe di E10 + le righe SDLC di E12/E13/E15.
**Chiude un debito noto:** E14-FEAT-002 (3.916 righe oggi non installabili da nessuno).

### ProtoSertor (nuovo — il congelato)

**Contenuto:** 90 file tracciati (4 approcci RAG, `shared/`, wiki storico, 8 test, `raw/`).
**Codice:** nessuna dipendenza da `sertor_core` (S8) → taglio a costo zero.
**Non ha:** installer, asset, CI di rilascio. **È un corpus**, non un prodotto installabile: riceve
Sertor-rag come ospite e resta di sola lettura.

### Il kit (D1-a — se accolta la raccomandazione)

**Codice:** 2.552 righe. **Test:** 24 propri + **37 guardie di meccanismo** ereditate da
`packages/sertor/tests`. **È il luogo dove «host-agnostico su Claude e Copilot» viene verificato.**

---

## 11. Criteri di completamento (falsificabili)

1. Su un host pulito: `install` dei tre nodi × 2 assistenti = **6 installazioni verdi**, `doctor`/gate
   verdi per ciascuno.
2. `upgrade` da release precedente per ciascun nodo: **esiti nominati, zero `n/a`**, letti dai log.
3. Il conteggio delle voci di backlog **prima** e **dopo** la ripartizione coincide (nessuna riga
   persa): oggi **110 aperte**.
4. `git log` su un file campione per nodo mostra la storia **precedente** alla migrazione.
5. Sertor non contiene più `wiki_tools/`, `prototype/`, `packages/sertor-flow`, `packages/speclift`,
   `packages/specaudit`, `.specify/` — e le sue suite restano verdi.
6. Il rituale di step su Sertor funziona **essendo installato da Thesmion**.
7. Ogni nodo ha superato le **dodici** voci della checklist §6.
