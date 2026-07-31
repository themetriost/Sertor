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
| **Sulcimen** | Il metodo: governance/SDLC, SpecKit, costituzione | `C:\Workspace\Git\Sulcimen` | **vuoto, non è un repo git** |
| **ProtoSertor** | Il prototipo congelato (4 approcci RAG su corpus FastAPI) | `C:\Workspace\Git\ProtoSertor` | **da creare** |

**E un quinto attore, deciso in D1 e non previsto dalla prima stesura:**

| | Cosa è | Repo | Stato |
|---|---|---|---|
| **Kaelen** | Il **motore d'installazione dell'ecosistema** + lo **schema del manifest di nodo**, oltre a ciò che già fa (orchestrazione workspace, matrice skill, probe) | `C:\Workspace\Git\Kaelen` | esistente — **spike Rust** (16.628 righe, 6 crate), non ancora un prodotto, ma nato per questo scopo |

> **SpecLift/SpecAudit non sono nostri** (D3): appartengono a **Sinthari**, che li distribuirà
> dichiarandosi nodo. Noi smettiamo di vendorarli — Sulcimen **non** li eredita.

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

## 3. Le sette decisioni — **SCIOLTE il 2026-07-31**

> **Tutte e sette decise dall'utente in sessione.** Le analisi che seguono restano come motivazione;
> gli esiti sono qui in testa e **prevalgono** su ogni raccomandazione scritta sotto.

| # | Decisione presa | Scostamento dalla raccomandazione |
|---|---|---|
| **D1** | **Kit unico e generico, casa = Kaelen.** Doppio canale: il nodo resta auto-installabile in superficie (`uvx --from git+…/<nodo> install`), ma **quel comando delega a Kaelen** — una sola implementazione, nessuna duplicazione | **Sì, sostanziale**: la casa non è un repo tecnico nuovo, è **Kaelen** |
| **D1b** | **Manifest nel nodo, motore in Kaelen.** Kaelen possiede motore + schema; ogni nodo porta il proprio `node.manifest.json`. Un nodo nuovo — anche di terzi — **non richiede di toccare Kaelen** | conforme |
| **D1c** | **Motore in Python dentro Kaelen** (riusa le 2.552 righe già testate e le 61 guardie). Rust resta per TUI, matrice skill, probe, apertura workspace. **Lo schema è letto da entrambi** | conforme |
| **D2** | **Thesmion reimplementa il kernel** (~200 righe: `log_event` + 2 errori) + **schema evento condiviso** e versionato | conforme |
| **D3** | **Sinthari si dichiara nodo e distribuisce SpecLift/SpecAudit.** Noi smettiamo di vendorare. **Provvisorio**: entreranno in un nodo dedicato più avanti | conforme (con riserva temporale) |
| **D4** | **Divisione per proprietà** + **refactoring semantico** delle pagine (i riferimenti puntano ai nodi, non assumono il monorepo) + **log invariati** (è storia) + **Could**: estrarre dai log le tracce di ciascun nodo | conforme, con tre aggiunte |
| **D5** | **`git filter-repo`** — storia preservata | conforme |
| **D6** | **Alias deprecati per una release**, con warning che nomina il sostituto; `upgrade` riscrive hook e blocchi | conforme |
| **D7** | **Ogni nodo decide quando e cosa installare.** Tendenza: tutti installano tutto, **salvo eccezioni** — la scelta resta del nodo, non imposta | conforme, con l'autonomia esplicitata |

### 3.0 La conseguenza che nessuna opzione aveva previsto: **Kaelen è il quinto attore**

D1 sposta il baricentro del piano. Non stiamo separando quattro prodotti e basta: stiamo **estraendo
il meccanismo d'installazione dell'intero ecosistema** e dandogli una casa che *esisteva già per quello
scopo*.

**Cosa Kaelen ha già** (spike, 16.628 righe Rust, 6 crate — non un prodotto, ma il modello è quello
giusto): enum `Agent` con `install_subpath()` (Claude → `.claude/skills`, Copilot → `.github/prompts`),
`SkillProbe` che rileva l'installato su disco, `SkillsMatrix` skill × workspace × agente **con gli
orfani**, un `dojo` come catalogo canonico, `GlobalScope` con i due locator per assistente.

**Il debito che questa decisione estingue, e che era già in essere:** quella conoscenza è **duplicata
oggi** fra `Agent::install_subpath` (Rust, Kaelen) e `AssistantId`/`Surface` (Python, kit). Due
implementazioni della stessa verità in due repo, e nulla le riconcilia. Con D1b entrambe leggono
**lo stesso manifest**: la duplicazione non viene "gestita", smette di esistere.

**La divisione di responsabilità che ne risulta:**

| Chi | Cosa fa | Perché lì |
|---|---|---|
| **Kaelen / `engine/` (Python)** | esegue install/upgrade/uninstall leggendo il manifest | riusa 2.552 righe testate + 61 guardie; il canale `uvx` è già il prerequisito accettato |
| **Kaelen / `schema/`** | possiede e versiona `node.manifest.v1.json` e `observability.event.v1.json` | il contratto è **dato**, non codice — leggibile da Rust e Python |
| **Kaelen / `crates/` (Rust)** | TUI, matrice skill, probe, orfani, apertura workspace | è ciò che già fa bene, e che al kit manca: il kit **deposita**, Kaelen **osserva** |
| **Ogni nodo** | porta `node.manifest.json` + gli asset + un **guscio** di comando | il nodo resta padrone di ciò che distribuisce |

**Il lavoro nuovo che questa decisione introduce, e che va dimensionato onestamente:** trasformare
**2.627 righe di piani in codice** (`install_rag.py` 1.324 · `install_wiki.py` 713 · `install_governance.py`
590) in **dati dichiarativi**. È il pezzo più sostanziale dell'intera migrazione, e non era nel piano
originale.

### 3.0.1 Due questioni aperte che le decisioni hanno generato

1. **Riferimenti cross-nodo nel wiki.** D4 chiede il refactoring semantico, ma oggi le pagine si citano
   con `[[wikilink]]`, che dopo la separazione attraverserebbero i confini dei repo e il lint li
   vedrebbe **rotti**. Serve una convenzione (proposta: wikilink solo intra-nodo; per i cross-nodo un
   link markdown all'URL del repo, con il nome del nodo esplicito — `[Thesmion · ritual-check](…)`).
   *Da confermare.*
2. **Il guscio deve procurarsi Kaelen.** `uvx --from git+…/Sertor sertor install rag` deve poter
   invocare il motore in Kaelen: serve decidere se il guscio dichiara Kaelen come dipendenza pinnata
   (più semplice, versione fissa e riproducibile) o lo risolve a runtime (più flessibile, un punto di
   rete in più). *Da confermare al momento dell'implementazione di F2.*

---

### Le analisi originali (motivazione delle scelte sopra)

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

> ⚠️ **Superato in parte da [`file-inventory.md`](file-inventory.md).** I numeri qui sotto vengono da
> una classificazione **lessicale** (per titolo). La verifica **file per file** delle 44 pagine di
> `concepts/` dà una ripartizione diversa — **19 `SER` · 6 `THE` · 3 `SUL` · 2 `SIN` · 4 `KAE` ·
> 10 `TRA`** — e ha corretto quattro assegnazioni che il titolo suggeriva male (`dogfooding` e
> `mission-vision` sono di Sertor, non trasversali; `fail-loud-fix-cause` e
> `product-plane-vs-fixture-plane` sono **principi costituzionali** → Sulcimen). Vale l'inventario.

Ripartizione **da classificazione lessicale** (60 pagine di `concepts/` + `tech/`):

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

### F1 — ProtoSertor (il taglio a rischio zero, che rompe il ghiaccio) — **DETTAGLIATA**

Perché primo: **zero import** verso il core (S8), 90 file tracciati, nessun asset host-facing, nessun
installer, nessuna guardia che ci gira sopra. È la prova che la procedura `filter-repo` + verifica
funziona, pagata sul caso più semplice.

#### Tre scoperte fatte misurando, che cambiano gli step

1. **Il corpus `raw/` NON è in git.** `.gitignore` ha `prototype/raw/*` + `!prototype/raw/README.md`:
   in git c'è **solo il README**. Su disco ci sono **973 file / 34 MB** (il corpus FastAPI). `filter-repo`
   porta 90 file e **lascia indietro il corpus**: va copiato a parte, o il nuovo repo nasce con un
   prototipo che non può essere eseguito né indicizzato.
2. **Il RAG sul prototipo non è attivo oggi.** L'unico indice presente è `.index`; `.index-prototype`
   **non esiste**. Quindi non c'è nessun indice da migrare, e F1 è ancora più semplice del previsto.
3. **`CLAUDE.md` afferma il falso su questo punto** (righe 32-33): dice che il server MCP è puntato sul
   prototipo (`SERTOR_CORPUS=prototype`), mentre `.mcp.json` dice `sertor`. È **prosa always-loaded**,
   letta a ogni sessione → ottava istanza di [[riassunto-invecchia-senza-riconciliatore]]. **Va
   corretta comunque**, indipendentemente dalla migrazione.

#### Stato dell'esecuzione (2026-07-31)

**F1.0 → F1.4 ESEGUITE.** `C:\Workspace\Git\ProtoSertor` esiste: commit `4e7c143`, **82 file
tracciati**, **35 commit** (34 di storia estratta, il più vecchio del **2026-05-28**), corpus
`raw/` copiato (973 file / 34 MB, ignorato correttamente), **zero contaminazione** verificata con
`diff` fra l'atteso e il reale. Nessun remote: il repo è locale.
**Restano F1.5 → F1.10.** Il punto attuale è **reversibile**: Sertor non è stato toccato.

Le cinque trappole incontrate sono distillate in [[cosa-non-viaggia-in-una-migrazione]] — vanno lette
**prima** di F2, F3 e F4, che ripeteranno la stessa procedura su sottoalberi più intrecciati.

#### Gli step

| # | Azione | Comando / dettaglio | Verifica d'uscita |
|---|---|---|---|
| **F1.0** | Creare il repo vuoto | `mkdir C:\Workspace\Git\ProtoSertor` + repo remoto | `git remote` raggiungibile |
| **F1.1** | Estrarre con la storia — **⚠️ non basta `--path prototype/`** | l'isolamento (`104e666`, 30/05) fu una **RINOMINA**: `--path prototype/` da solo preserva **3 commit**. La storia vera (**36 commit**) sta sotto i path in radice. Includere: `prototype/` · `01-baseline/` · `02-hybrid-reranking/` · `03-graphrag/` · `04-agentic-rag/` · `shared/` · `raw/` · `DEMOS.md` · `ESEMPI.md` · `requirements.txt` · `.env.example`. **Escludere** `wiki/`, `tests/`, `README.md` **e `.env.example`**: collidono con la radice di oggi (rispettivamente 547 e 139 commit di produzione; `.env.example` è il template delle manopole — **quarta collisione, trovata verificando path per path prima di lanciare**). I quattro file arrivano comunque via `--path prototype/`: manca solo la loro storia anteriore al 30/05 | `git log` mostra **36 commit**; **controllo anti-contaminazione**: `git ls-files \| grep -E "^(src/\|packages/\|specs/\|requirements/)" ` **deve dare 0** |
| **F1.2** | **Portare il corpus `raw/`** (non è in git) | copia diretta di `prototype/raw/` → `ProtoSertor/raw/`; `.gitignore` proprio che lo esclude di nuovo | 973 file / 34 MB presenti; `git status` pulito |
| **F1.3** | Autonomia del repo | `README.md` (cos'è · **congelato** · come si esegue e si interroga) · `.env.example` · `requirements.txt` · `.gitignore` (da quello di Sertor, righe 47-66, ripulite del prefisso `prototype/`) | i 4 file presenti |
| **F1.4** | Il wiki del prototipo — **⚠️ 9 file su 20 NON vanno a ProtoSertor** | verificato file per file (vedi [`file-inventory.md`](file-inventory.md) §1.3): **11** restano al prototipo · **6 → Sulcimen** (proposta di costituzione, EARS, SpecKit, requirements-engineering, flusso requisiti→implementazione, panorama strumenti) · **3 → Sertor** (`architettura-attuale`, `architettura-target`, **`epica-sertor-cli`** — antenato di `requirements/sertor-cli/`) | i 3+6 file **non** sono nel repo nuovo; `wiki/index.md` di ProtoSertor riscritto senza i rimandi ai 9 |
| **F1.5** | Verifica che sia **eseguibile** | eseguire uno dei 4 approcci (es. `01-baseline/index.py --provider …`) | almeno un percorso gira, o il README dichiara cosa serve |
| **F1.6** | ProtoSertor riceve il RAG come **ospite** | `uvx --from git+…/Sertor sertor install rag` sul nuovo repo + `sertor-rag index .` | `search_code` risponde **da ProtoSertor**, non da Sertor |
| **F1.7** | In Sertor: **rimuovere** `prototype/` | `git rm -r prototype/` in una PR normale (il repo sorgente non è mai stato toccato da `filter-repo`) | 7 suite verdi, `ruff` pulito |
| **F1.8** | In Sertor: **ripulire i riferimenti operativi** — **5** punti (non 4: il quinto emerso dalla verifica file-per-file) | `.gitignore` (righe 47-66) · `pyproject.toml` (esclusione lint, riga 133) · `CLAUDE.md` (**10 occorrenze**; la sezione *Riferirsi al prototipo* va **riscritta**, non cancellata — già fatto il 31/07) · **`.claude/commands/derive-entity-types.md` riga 23**, che invoca `shared/derive_entity_types.py`: path **inesistente dal 30/05**, quindi il comando è **rotto da due mesi** → correggerlo o ritirarlo · nessun cambio a `wiki.config.toml` (non lo nomina) | grep operativi = 0; il comando `derive-entity-types` **funziona** o è dichiaratamente ritirato |
| **F1.9** | I **67 riferimenti narrativi** in `specs/`/`requirements/`/`wiki/` **NON si toccano** | sono storia: citano il prototipo come contesto di decisioni passate, e restano veri | nessuna modifica (deliberata, dichiarata qui) |
| **F1.10** | Rituale: record + distill(≈no) + lint; PR e merge | | lint strutturale pulito |

> **Uscita F1 (falsificabile):** ProtoSertor è un repo con **storia**, **corpus eseguibile** e **RAG
> proprio** che risponde; Sertor non contiene più `prototype/`, le sue 7 suite sono verdi, e nessun
> riferimento operativo pende. La procedura `filter-repo` è stata provata end-to-end **prima** di
> applicarla dove ci girano sopra i gate.

> **Rischi specifici di F1** — bassi, ma nominati: (a) *dimenticare `raw/`* → il repo nasce inerte;
> mitigazione: F1.2 è uno step a sé con verifica numerica. (b) *`filter-repo` non installato* → è un
> tool separato da git; verificarlo in F0. (c) *cancellare la sezione del `CLAUDE.md` invece di
> riscriverla* → il prototipo continuerebbe a esistere senza che nulla dica dove: è l'errore di
> [[host-agnostico-non-e-risolvibile]] (un riferimento tolto non è un riferimento risolto).

### F2 — **Kaelen diventa il motore dell'ecosistema** (D1 · D1b · D1c)

> **È la fase più grossa e quella che il piano originale non aveva.** Non sposta soltanto codice:
> trasforma **2.627 righe di piani in codice** in **dati dichiarativi**, e fa sì che Rust e Python
> leggano la stessa verità invece di codificarla due volte.

| Step | Azione | Uscita |
|---|---|---|
| F2.1 | `filter-repo --path packages/sertor-install-kit/` → `Kaelen/engine/` (Python), con i suoi **24 test** + le **37 guardie di meccanismo** prese da `packages/sertor/tests` | 61 test verdi dentro Kaelen |
| F2.2 | **Progettare `schema/node.manifest.v1.json`**: cos'è un nodo (identità, artefatti, surface per agente, hook, blocchi a marker, merge, lifecycle, template `.env`) | schema versionato + validatore |
| F2.3 | **Convertire i tre piani in manifest, uno alla volta** — `install_rag` (1.324) · `install_wiki` (713) · `install_governance` (590) | per ciascuno: **test di equivalenza** — l'installazione via manifest produce lo **stesso esito su host** di quella via codice |
| F2.4 | Il motore esegue **dal manifest**; le 37 guardie girano invariate sul nuovo percorso | 37 verdi senza modifiche alle asserzioni |
| F2.5 | **Kaelen/Rust legge lo stesso schema** per `SkillProbe`/`SkillsMatrix`: `Agent::install_subpath` smette di codificare i path, li **deriva** dal manifest | la duplicazione Rust↔Python **non esiste più** (guardia: nessun path d'assistente hardcoded nei due linguaggi) |
| F2.6 | I **gusci** dei nodi (`sertor install …`) delegano al motore in Kaelen; decidere se Kaelen è dipendenza pinnata o risolta a runtime (§3.0.1) | l'ospite vede lo stesso comando di prima |
| F2.7 | `schema/observability.event.v1.json` (serve a D2) | Sertor e Thesmion lo rispettano |
| **Uscita F2** | un nodo si installa **da manifest**, via il motore unico in Kaelen, con **esito identico** a oggi — dimostrato dal test di equivalenza, non affermato | |

> **Il criterio che rende questa fase falsificabile:** non «il motore funziona», ma **«installare via
> manifest lascia l'host nello stesso stato di installare via codice»** — confronto dell'esito su host
> usa-e-getta, prima e dopo. È la lezione di [[esito-sull-host-vs-forma-dell-asset]] applicata alla
> propria migrazione.

### F3 — Sulcimen (il nodo già indipendente)

Perché prima di Thesmion: **zero accoppiamento** col core (S6), e porta con sé `speclift`/`specaudit`
chiudendo E14-FEAT-002.

| Step | Azione | Uscita |
|---|---|---|
| F3.0 | **D3:** rimuovere il vendoring di `speclift`/`specaudit` da Sertor; **Sinthari** si dichiara nodo (manifest F2.2) e li distribuisce. *Provvisorio: entreranno in un nodo dedicato* | 3.916 righe installabili **dal proprietario**; E14-FEAT-002 chiusa |
| F3.1 | `filter-repo --path packages/sertor-flow/ --path .specify/` | storia preservata |
| F3.2 | Pacchetto `sulcimen` proprio; rinomina CLI con alias deprecato (D6) | **26 test verdi** |
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
| **F2 Kaelen motore + manifest** | **alto** — 2.627 righe di piani da rendere dati, due linguaggi da riconciliare | **8×** *(era 2× quando era «estrarre il kit»)* | sì, finché i gusci non delegano |
| F3 Sulcimen | basso (26 test, 1 package) *(era medio: SpecLift/SpecAudit sono usciti con D3)* | 2× | sì, finché F3.9 non gira |
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

**Codice:** `sertor-flow` (1.152 righe). *SpecLift/SpecAudit **non** entrano: sono di Sinthari (D3).*
**Test:** **26**.
**Asset:** 2 agenti (configuration-manager, requirements-analyst) · skill `requirements` +
**9** `speckit-*` · `constitution-starter` · template `.specify/` · manifest d'integrazione ·
blocco `SULCIMEN:RITUAL`.
**Backlog:** ~11 righe di E10 + le righe SDLC di E12/E13/E15. *(E14 segue SpecLift a Sinthari.)*

### Kaelen (esistente — diventa il motore, D1)

**Codice:** `engine/` Python (2.552 righe migrate) + `schema/` (manifest + evento) + `crates/` Rust
già presenti (16.628, spike).
**Test:** 24 propri del kit + **37 guardie di meccanismo** ereditate.
**Cosa possiede:** l'unica implementazione di install/upgrade/uninstall dell'ecosistema, lo schema che
definisce *cos'è un nodo*, e la vista di flotta (matrice skill × workspace × agente, orfani).
**Wiki:** le 10 pagine di installazione/distribuzione (`assistant-targeting`, `installer-lifecycle`,
`identita-hook-nel-merge`, `esito-sull-host-vs-forma-dell-asset`, …).
**Il debito che estingue:** la conoscenza «dove va una skill per Claude/Copilot» smette di esistere in
due linguaggi.

### Sinthari (esistente — non nostro)

Si dichiara nodo con il proprio manifest e distribuisce **SpecLift** e **SpecAudit**. Noi smettiamo di
vendorare (−3.916 righe, −52 test dal nostro perimetro). **Provvisorio:** i due entreranno in un nodo
dedicato più avanti.

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

**Aggiunti dalle decisioni del 2026-07-31:**

8. **Equivalenza del motore:** installare un nodo **da manifest** lascia l'host nello **stesso stato**
   dell'installazione via codice — confrontato su host usa-e-getta, per tutte e tre le capability.
9. **La duplicazione è estinta, non gestita:** nessun path d'assistente (`.claude/skills`,
   `.github/prompts`) compare hardcoded né in Rust né in Python — entrambi lo derivano dallo schema.
   *Verifica: un grep che deve dare zero.*
10. **Kaelen è generico davvero:** un nodo **di terzi**, con solo il proprio manifest, si installa
    **senza modificare Kaelen**. *Verifica: un nodo finto costruito apposta, installato end-to-end.*
11. **Nessun ospite si rompe:** gli hook installati che invocano `sertor-wiki-tools` continuano a
    funzionare per una release, emettendo il warning che nomina il sostituto (D6). *Verifica: un host
    con l'installazione vecchia che NON aggiorna — il gate deve continuare a bloccare, non a tacere.*
12. **Sinthari distribuisce i propri strumenti:** SpecLift/SpecAudit installabili dal proprietario, e
    zero vendoring residuo nei nostri repo. *Verifica: grep su `VENDORING.md` = 0.*
