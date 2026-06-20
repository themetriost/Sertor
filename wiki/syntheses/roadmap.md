---
title: Roadmap & stato di prodotto (pagina viva)
type: synthesis
tags: [roadmap, piano, stato, produzione, backlog]
created: 2026-06-03
updated: 2026-06-20 (E5 retrieval-qualita — FEAT-001 **riformulata e decomposta** in requisiti EARS: da «comando metriche» a **ciclo di vita di una suite di valutazione del progetto ospite** (genesi interattiva/LLM-assistita → artefatto-dato versionato → run ripetibile via vehicle → non-regressione + feedback esplicito); l'harness `evaluate` esiste già nel core ma sepolto nei test → la feature lo promuove host-side; promosse FEAT-008 genesi LLM + FEAT-009 feedback; DA-Q-a risolta; prossimo `/speckit-plan`) · 2026-06-19 (robustezza staleness server MCP — ChromaStore auto-refresh PR #89 + code-graph auto-reload PR #90; rituale MCP-first + smoke test del RAG; disciplina MCP-first propagata agli ospiti; + canonizzata la numerazione epiche E1..E11 nella tabella) · 2026-06-19 (FEAT-010 debito-tecnico — host-agnosticità asset governance asse Sertor↔ospite: neutralizzati i project-coupling negli asset distribuiti da `sertor-flow` (`requirements-analyst` hardcodava i tool `mcp__sertor-rag__*`; `configuration-manager` usava "workspace RAG" + cartelle-prototipo come scope-esempi) → RAG-opzionale-via-discovery, scope generici; ri-sync `.claude/`; pin di regressione; sertor-flow 134 verdi; emerso dalla domanda «distribuiamo configuration-manager?»; branch `059`) · 2026-06-19 (FEAT-009 debito-tecnico — bug distribuzione: la costituzione-starter NEUTRA non arrivava sull'ospite, shadowata dal placeholder di spec-kit (`specify init` lo crea, il nostro CONFIG create-if-absent faceva skip); fix **replace-if-placeholder** in `sertor-flow` + rifinitura principi neutri (Replaceable Details, Consume Through Stable Interfaces; v0.2.0); mock conftest reso fedele (depositava il placeholder); sertor-flow 132·kit 131·sertor 292 verdi; branch `058`) · 2026-06-19 (FEAT-001 debito-tecnico — parità Copilot CLI RIFATTA col meccanismo NATIVO agent-skills `.github/skills/wiki-author/` (SKILL.md dispatcher che assorbe `/wiki` + payload byte-copiato co-locato), abbandonati custom-agent-skill/`.github/sertor/`/`{SKILL_DIR}`; verificata LIVE su Copilot CLI reale (Spike): tool nativo `skill` invoca `wiki-author`, legge il playbook co-locato, 8 operazioni; PR #80 pronta) · 2026-06-17 (FEAT-001 packaging distribuibile `git+url` ✅ DONE — PR #68: LICENSE MIT + versione unica + metadati + suite di verifica build/install, Constitution 11/11; **unica casella Must di `sertor-cli` chiusa**. + Robustezza chunking: tetto del chunk al budget token dell'embedder, PR #69/#70 — bug del re-index dogfood, cap in token con tiktoken/fallback; corpus re-indicizzato pulito. Incrementale FEAT-009 confermato corretto end-to-end) · 2026-06-16 (EXEC ristrutturato per leggibilità: due tabelle disgiunte e adiacenti — ✅ capacità consegnate (feature) + 📋 le 11 epiche per stato; le 6 nuove epiche ora nella tabella epiche, niente più mescolanza feature↔epiche) · 2026-06-16 (FEAT-009 refresh incrementale dell'indice ✅ DONE — merge `3ec47f1` su master: manifest SQLite, incrementale di default, upsert/delete mirati + BM25/grafo dal manifest, lock single-writer, gate di equivalenza verde, 596 test, Constitution 11/11; ultimo residuo reale di sertor-core chiuso) · 2026-06-16 (FEAT-009 requirements decomposti → `/speckit-plan` — 18 REQ EARS, MoSCoW, decisioni F1/F2, 5 DA aperte; prior-art CocoIndex/LlamaIndex/LangChain consultate) · 2026-06-16 (backlog audit → roadmap: 6 nuove epiche dal censimento del non-fatto — retrieval-qualita · backend-store-scala · ingestione-estesa · conoscenza-schema-sql · second-brain · debito-tecnico; leak minori promossi nelle epiche esistenti; EXEC table + PLANNED riorganizzati) · 2026-06-15 (Principio XI realizzato end-to-end A-D: auto-wire composition + ospite istruzioni/hook + bundle coerenza, PRs #61/#62/#63) · 2026-06-14 (FEAT-003 aggancio distillazione all'archivio ✅ master PR #51 — MVP memoria completo+acceso, loop cattura→distill chiuso; SERTOR_MEMORY=true sul dogfood) · 2026-06-14 (MVP osservabilità ✅ master F1→F4 PR #34/35/36/38; memory conversazioni epica decomposte FEAT-001/002) · 2026-06-14 (hardening Should gruppo C — feature 019 cache embeddings + token nei log — implementata su branch, in attesa di PR) · 2026-06-13 (notte: FEAT-018 hardening retrieval Must ✅ su master, PR #32 — retry embedder + soglia/low_confidence; hardening resta IN PROGRESS perché Should/Could aperti) · 2026-06-13 (sera: + idea «Second brain cross-progetto»/Meta-Sertor → [[second-brain-cross-progetto]], da espandere · giornata: FEAT-006 ✅ composita · igiene radice host PR #26 · tema lingua completo PR #27/#28/#29) · 2026-06-12 (TRIPLA: PR #23/#24/#25)
sources: ["requirements/sertor-core/epic.md", "requirements/sertor-cli/epic.md", "specs/**", ".specify/memory/constitution.md", "requirements/memoria-conversazioni/epic.md"]
---

# Roadmap & stato — Sertor

> **Pagina viva.** Quadro d'insieme dello stato reale. Si aggiorna a mano (sezione *Nuove funzionalità da
> discutere*) e quando una feature avanza nella pipeline SpecKit. Quando un'idea matura: backlog epica →
> `requirements → spec → plan → tasks → implement`.

<!-- EXEC:START -->
## ⚡ Executive summary (stato al 2026-06-19)

### ✅ Capacità consegnate (feature su `master`)

| Capacità (feature) | Epica |
|---|---|
| Nucleo retrieval · motore baseline · Wiki LLM · server MCP | `sertor-core` |
| RAG ibrido+reranking (default) · code-graph · agentico & Wiki↔RAG (compositi) | `sertor-core` |
| **Refresh incrementale dell'indice** (FEAT-009, 2026-06-16) | `sertor-core` |
| Hardening retrieval (Must + Should gruppo C: retry · soglia · cache embeddings) | `sertor-core` |
| CLI `sertor-rag` · installer `sertor install wiki`/`rag` | `sertor-cli` |
| **Packaging distribuibile** `git+url` (FEAT-001, LICENSE+metadati+build verificata, 2026-06-17) | `sertor-cli` |
| **Ciclo di vita installer** — `upgrade`/`uninstall` per `sertor` e `sertor-flow` (FEAT-008, 2026-06-17) | `sertor-cli` |
| Governance SDLC — pacchetto separato `sertor-flow` | `sertor-cli` |
| Distribuzione Copilot (VS Code + CLI) — FEAT-007+009 + **hardening nativo FEAT-011** ✅ *(verifica empirica VS Code/MCP CLI = follow-up)* | `sertor-cli` |
| Igiene radice host · tema lingua (tutto il prodotto in EN) | `sertor-cli` |
| MVP osservabilità F1–F4 (**accesa** sul dogfood) · **export OTel + visibilità RAG nella TUI** (FEAT-005/013/014/015, 2026-06-19) | `osservabilita` |
| MVP memoria: cattura→ricerca→CLI/hook→distillazione (**acceso**) | `memoria-conversazioni` |

*Dettaglio (PR, date, numeri) nella sezione ✅ DONE in fondo alla pagina.*

### 📋 Le 11 epiche (per stato)

> **⚠️ Nessuna epica è "finita" finché TUTTE le sue feature non sono consegnate.** Le 4 storiche hanno
> il **nucleo su `master`** ma residui aperti (tranne `sertor-core`, ormai completa); le altre 7 sono
> **da fare**. Una *feature* (`FEAT-NNN`) vive **dentro** un'epica — le capacità già consegnate stanno
> nella tabella sopra, qui c'è il quadro a livello di epica.

| # | Epica | Stato | Residuo / 1° passo |
|---|---|---|---|
| **E1** | [`sertor-core`](../../requirements/sertor-core/epic.md) | ✅ completa | — (agenzia incorporata ❌ abbandonata by design) · *robustezza staleness: ChromaStore auto-refresh PR #89 + code-graph auto-reload PR #90, 2026-06-19* |
| **E2** | [`sertor-cli`](../../requirements/sertor-cli/epic.md) | 🔄 nucleo su master | ergonomia installer · Codex · PyPI · `configure --check` (probe live, deferred) *(packaging ✅ + lifecycle ✅ + hardening Copilot FEAT-011 ✅ + wizard config ✅ + Copilot CLI-only ✅ + verifica empirica Copilot LIVE ✅, 2026-06-17)* |
| **E3** | [`osservabilita`](../../requirements/osservabilita/epic.md) | 🔄 MVP su master | **export OTel FEAT-005 ✅** + arricchimento span FEAT-013 ✅ + TUI tabella FEAT-014 ✅ + **visibilità RAG/dimostrabilità FEAT-015 ✅** (PR #88) · drift FEAT-012 · metriche aggregate · stima € (Should) · web · CSV/MD |
| **E4** | [`memoria-conversazioni`](../../requirements/memoria-conversazioni/epic.md) | 🔄 MVP acceso | ricerca semantica · remember-this · retention · **distribuzione installer (Must)** · multi-assist |
| **E5** | 🆕 [`retrieval-qualita`](../../requirements/retrieval-qualita/epic.md) | 🔄 FEAT-001 implementata | **suite di valutazione host-side** (`sertor-rag eval` + gate non-regressione + skill) — branch `065`, SpecKit completo, **718 verdi**, in attesa review/merge |
| **E6** | 🆕 [`backend-store-scala`](../../requirements/backend-store-scala/epic.md) | 📋 aperta | adapter PGVector (Should) |
| **E7** | 🆕 [`ingestione-estesa`](../../requirements/ingestione-estesa/epic.md) | 📋 aperta | chunking SQL → **sblocca** schema-SQL |
| **E8** | 🆕 [`conoscenza-schema-sql`](../../requirements/conoscenza-schema-sql/epic.md) | 📋 aperta | bloccata a monte da `ingestione-estesa` |
| **E9** | 🆕 [`second-brain`](../../requirements/second-brain/epic.md) | 📋 da espandere | decidere bivi §9 prima di decomporre |
| **E10** | 🆕 [`debito-tecnico`](../../requirements/debito-tecnico/epic.md) | 🔄 in progress | **CI Linux (FEAT-003, Should)** — unico residuo Should; il resto è Could *(unif. venv ✅ · host-agnosticità asset **FEAT-001 ✅** PR #80 · **FEAT-009 ✅** PR #82 · **FEAT-010 ✅** PR #83 · **disciplina MCP-first agli ospiti ✅** PR #90, 2026-06-19)* |
| **E11** | [`multiutente`](../../requirements/multiutente/epic.md) | 📋 differita | finché il caso d'uso team non è concreto |

*Legenda:* ✅ completa · 🔄 nucleo consegnato, residui aperti · 📋 da fare · 🆕 nuova (2026-06-16). *Numerazione `E1`..`E11`: vista standing per epica (E1 nucleo `sertor-core`, E11 `multiutente` differita); E1–E4 storiche, E5–E10 dal backlog audit 2026-06-16.*

### 🔄 IN PROGRESS (dettaglio)

> **Implementata su branch `065-ground-truth-valutazione`, in attesa di review/merge:** FEAT-001
> `retrieval-qualita` (suite di valutazione host-side). **Dove:** `specs/065-ground-truth-valutazione/`
> (SpecKit completo) + `src/sertor_core/services/eval/` + `sertor-rag eval` + skill `eval-suite-author`/
> `eval-feedback`. **Pipeline SpecKit:** ✅ requirements → ✅ specify → ⏭️ clarify saltato (forche di design
> risolte con l'utente) → ✅ plan (Constitution 11/11) → ✅ tasks (24) → ✅ **implement (718 non-cloud verdi,
> 3 skip packaging noti, ruff clean)**. **Cosa fa:** `eval run` misura hit-rate@k/MRR sulla suite TOML
> versionata (`eval/suite.toml`) col dettaglio per-query e fa **gate di non-regressione** su baseline+tolleranza
> (exit 1 sotto soglia); `add-case`/`validate-path` primitive per le skill; `--compare` confronta 2 config.
> **Decisioni:** suite TOML (writer minimale stdlib, 0 nuove dipendenze) in `eval/` versionato · baseline su
> file + tolleranza · run via vehicle (Principio XI, factory `build_eval_runner`/`build_indexed_docs`) ·
> estensione core non-breaking (`EvalReport.per_query`/`QueryOutcome`) · genesi/feedback = **skill** vehicle-only
> (FEAT-008/009, «LLM»=agente, il core non chiama mai un LLM) cablate in `build_rag_plan` (installabili). **Prossimo
> passo:** review → merge su `master` → re-index dogfood + smoke test MCP (rituale). **Scoperta in implement:**
> `derive-entity-types` non esiste nel repo e il rag-installer non depositava skill → eval-skill cablate come
> native-skill dual-target (Claude `.claude/skills/` + Copilot `.github/skills/`).

**Altri candidati a valore = Must aperti** (non ancora iniziati):

- **Memoria → distribuzione via installer (Must, `memoria-conversazioni`)** — la memoria è *accesa* sul
  dogfood ma **non installabile su un ospite**: chiude il corollario "una feature è completa solo se
  installabile". *Primo passo:* decomporre la feature installer (riusa `sertor-install-kit`).
- **Retrieval-qualità → suite di valutazione host-side (Must, `retrieval-qualita`, FEAT-001 decomposta
  2026-06-20)** — manca la base per **misurare** la qualità del RAG (Principio V). Riformulata da
  «comando metriche» a **ciclo di vita di una suite del progetto ospite**: genesi (interattiva +
  LLM-assistita, da approvare) → artefatto-dato versionato (query→atteso) → run ripetibile via vehicle
  (hit@k/MRR) → **non-regressione** (riferimento + gate) + feedback esplicito. L'harness `evaluate` esiste
  già nel core (oggi sepolto nei test): la feature lo **promuove** a capacità host-side. *Requisiti EARS
  pronti* (`requirements/retrieval-qualita/ground-truth-valutazione/`); *primo passo:* `/speckit-plan`.

*(Le capacità già consegnate stanno in ✅ Capacità consegnate sopra e in ✅ DONE in fondo.)*

### 📋 PLANNED (per priorità)

> **Riorganizzato il 2026-06-16 dal [backlog audit](backlog-audit-2026-06-15.md):** tutto il non-fatto è
> ora raggruppato in epiche con casa durevole. Sei **nuove epiche** danno casa al materiale orfano; le
> epiche esistenti restano sotto.

**Nuove epiche (aperte, da decomporre quando prioritarie):**
- **Qualità del retrieval** (`retrieval-qualita`) — *primo passo a valore:* ground-truth + metriche
  (Must). Poi search_code architetturale, calibrazione soglie, eval `cloud` (Should); tecniche avanzate
  HyDE/filtro-metadata/contextual-retrieval (Could, ex `hardening-produzione` H7/H8/H11).
- **Backend store & scala** (`backend-store-scala`) — *primo passo:* adapter PGVector (Should). Poi
  Mongo/Atlas, indici multi-provider, fan-out su >2 corpora, scala del code-graph (Could).
- **Ingestione estesa** (`ingestione-estesa`) — repo remoti via URL, formati non-testo (PDF/DOCX/notebook),
  chunking PS/T-SQL/PL-SQL/Bash, no-code-first (Could). **Sblocca** la conoscenza-schema SQL.
- **Conoscenza-schema SQL** (`conoscenza-schema-sql`) — schema nel corpus (Should) + schema-graph + fusione
  col codice applicativo (Could). **Bloccata a monte** dal chunking SQL di `ingestione-estesa`.
- **Second-brain / Meta-Sertor** (`second-brain`) — **da espandere:** MVP = catalogo flotta + query
  federata (quasi solo wiring); poi harvest/promote, trust, asset-registry. Bivi §9 (solo/team, meta-corpus
  vs fan-out, meta-grafo, nome) **da decidere prima di decomporre**.
- **Debito tecnico & igiene** (`debito-tecnico`, interna) — host-agnosticità asset residui, unif. venv,
  CI Linux (Should); plugin rituale portabile, igiene wiki, selettività bundle `sertor-flow` (Could).

**Epiche esistenti, in attesa:**
- **Sertor-core — ✅ nessun residuo aperto** — l'**agenzia incorporata** è **❌ abbandonata by design**
  (2026-06-16, «non ci serve»; l'agentic RAG è già ✅ composito via MCP+agente). *(FEAT-009 ✅ DONE merge
  `3ec47f1`; FEAT-008 Wiki↔RAG ✅ composita.)* L'epica primaria del prodotto è sostanzialmente **completa**.
- **Memoria — Should/Could** — FEAT-004 (ricerca semantica opt-in), FEAT-005 (remember-this), FEAT-006
  (retention), FEAT-007 (ponte second-brain), **FEAT-009 distribuzione via installer (Must/debito)**,
  FEAT-008 (cattura multi-assistente), FEAT-010 (parità MCP `show`/`list`). *(FEAT-003 ✅ DONE.)*
- **Osservabilità 2 — Should/Could** — export OTel (FEAT-005), metriche aggregate (FEAT-006), **stima €
  (FEAT-007, Should, non fatto)**, web mode, trend qualità, metriche graph/wiki, export CSV/MD (FEAT-011).
- **Distribuzione/CLI — Could (Must chiuso)** — *packaging del pacchetto ✅ FEAT-001 DONE (PR #68) e
  lifecycle upgrade/uninstall ✅ FEAT-008 DONE (PR #71), entrambi 2026-06-17*;
  restano: wizard config (FEAT-003, Should), ergonomia installer (FEAT-010), **Codex** (FEAT-007/009
  Could, non avviato per scelta utente), PyPI (Won't) — gating sulla **licenza MIT scelta** per i
  pacchetti (PyPI pubblico resta da aprire).
- **Multiutente** — epica differita finché il caso d'uso team non è concreto.
- **Agenzia RAG incorporata** — ❌ **abbandonata by design (2026-06-16, decisione utente)**: l'agentic RAG
  è già ✅ composito (MCP+agente) e un agente nel core con modello minore non lo migliorerebbe; i 36 REQ in
  `sertor-core/motore-agentico/` restano **elicitazione storica**, non pianificata.

### ✅ DONE (su `master`, le rilevanti)

- **🛠️ Robustezza staleness del server MCP — fix gemelli + disciplina (PR #89/#90, 2026-06-19)** — il
  server MCP, tenendo client/artefatti a vita lunga, serviva risultati **stantii** dopo un re-index
  (scoperto via **dogfooding**: `search_code`/`search_docs` in `InternalError` sul filtro `where` mentre
  `search_combined` reggeva; `find_symbol` a righe vecchie). Un client fresco sul disco funzionava →
  difetto nel **processo**, non nei dati. Due fix di **auto-guarigione**: **ChromaStore** ricrea il
  client posseduto (`clear_system_cache` + retry una volta) su errore di query (PR #89);
  **NetworkxCodeGraph** ricarica l'artefatto su cambio `(mtime_ns, size)` (PR #90) — nessun riavvio.
  + **rituale**: regola **MCP-first** (apertura dello step) + **smoke test del RAG** (punto 8, chiusura),
  e la disciplina MCP-first **propagata agli ospiti** nel blocco host `SERTOR:RAG-USAGE` (corollario
  installabile). core 600 · sertor 293 verdi, ruff pulito; validato live (Chroma auto-heal confermato
  senza reconnect; code-graph fresco dopo reconnect, auto-reload coperto dai test). Robustezza **E1** +
  governance/host **E10**.

- **🔧 Fix uninstall: file hook Copilot dedicato cancellato se vuoto (PR #77, 2026-06-17)** — `sertor
  uninstall` lasciava `.github/hooks/sertor-hooks.json` come guscio `{"version":1}` dopo aver rimosso
  le entry Sertor. `remove_settings_entries(delete_if_empty=)` ora cancella il file **dedicato** quando
  resta senza contenuto; il file **condiviso** `.claude/settings.json` è sempre preservato (cancella
  solo quando non resta nulla — un hook utente residuo mantiene il file). 3 test; kit 131 · sertor 282.
  *Emerso dalla verifica empirica su Spike. Chiude l'item 4 del programma utente (1·2·4 completo).*

- **🚢 Consolidamento Copilot CLI-only (FEAT-012 `sertor-cli`, feature 052, PR #76, 2026-06-17)** —
  la distribuzione Copilot ha **un solo target = la CLI**. Rimosso `AssistantId.COPILOT` (VS Code) dal
  `sertor-install-kit` + profilo + rami di resa (`.vscode/mcp.json`, prompt-file come veicolo comandi);
  **`--assistant copilot` ora è un errore esplicito** che nomina `copilot-cli`. **Naming uniforme**
  `claude|copilot-cli` su `sertor` e `sertor-flow` (rinomina diretta). Skill **`requirements`** resa
  come **custom-agent** su CLI (non più prompt-file). **Mapping** `copilot-cli → --ai copilot` (upstream
  spec-kit) in un punto unico (`_SPECKIT_AI_FLAG`) + `_EXPECTED_LAYOUT` per l'idempotenza. Docs allineate
  + nota di migrazione VS Code. Elimina il footgun VS Code↔CLI e l'incoerenza di naming emersi dalla
  verifica empirica. **530 test verdi** (kit 128 · sertor 282 · sertor-flow 120), Constitution 11/11,
  **`sertor-core` invariato**, non-regressione Claude verde. *Chiude l'item 2 del programma utente.*

- **🚢 Wizard di configurazione `sertor configure [rag]` (FEAT-003 `sertor-cli`, feature 051, PR #75, 2026-06-17)** —
  chiude la **causa-radice UX** del RAG non configurato (il `-32000` su Copilot CLI quando mancano le chiavi):
  un comando guidato porta `.sertor/.env` da segreti vuoti a pronto **senza editor**. Risoluzione per-campo
  CI-safe (flag→env/esistente→prompt-se-TTY→default; campo mancante senza TTY → errore che lo nomina, niente
  scrittura parziale); campi richiesti da **fonte unica** `Settings.validate_backend()` (test di copertura
  catalogo↔validatore, no drift); scrittura **additiva non-distruttiva** (`merge_env`, overwrite gated);
  **segreti** via `getpass`, mascherati ovunque da `mask_secret` (anti-leak su entità/umano/JSON/stdout);
  validazione statica; report umano + `--json`. Default coerente col **decoupling FEAT-009** (backend azure
  → store `local`/Chroma, embeddings Azure + Chroma locale — confermato dall'utente; "azure ovunque" scartato).
  install≠run; install/upgrade/uninstall invariati. Pipeline SpecKit completa; **293 test**, Constitution
  11/11. **Follow-up:** `--check` (probe live, US5) **deferred** → richiede un nuovo `sertor-rag check` in
  `sertor-core` (Principio XI: il wizard usa il vehicle, non importa `build_embedder`); oggi il flag c'è e
  degrada onestamente.

- **🔧 Fix runtime Copilot + verifica empirica LIVE (PR #74, branch 050, 2026-06-17)** — la **verifica
  empirica** della distribuzione Copilot su un **ospite reale** (Copilot CLI 1.0.63) ha chiuso il loop
  «installato≠funzionante» e scoperto **3 difetti** che i test offline di FEAT-011 non coprivano (uno li
  *codificava*): (1) il server MCP crashava `-32000 Connection closed` su config incompleta → warm-up
  protetto, ora parte e l'errore è azionabile al tool-call; (2) SessionStart usava `command` invece di
  `prompt` (Copilot lo ignorava) → campo corretto + dedup/idempotenza/uninstall sul payload `prompt`;
  (3) `description` del custom-agent non quotata → un `:` rompeva lo YAML e `wiki-author` non si caricava
  → quoting `_yaml_scalar`. **Confermato LIVE:** `.mcp.json` auto-caricato in sessione interattiva,
  `sertor-rag` connesso (7 tool), 3 agent caricati; con creds mancanti il server resta connesso con
  errore azionabile (niente `-32000`). Test che pinnano i fix (+ guard sugli asset veri). Suite verde
  (kit 127 · sertor 221 · root 583 · packaging 2). **Lezione:** i test offline non bastano per superfici
  di un tool esterno → la verifica sul client reale è parte del «done». *Decisioni: distribuzione
  Copilot CLI-only + naming `copilot-cli` + governance prompt→custom-agent → da decomporre.*

- **🚢 Hardening compatibilità Copilot — schema nativo (FEAT-011 `sertor-cli`, feature 049, PR #73, 2026-06-17)** —
  corregge la falsa "parità piena" di FEAT-007/009 emersa da un **audit dogfooding** su Copilot CLI
  1.0.63 (hook in formato Claude → file scartato; comandi prompt-file ignorati dalla CLI). Principio
  **nativo, niente hack** ([[feedback nativo no-hack]]): nuovo `render_copilot_hooks` + `HookEntrySpec`
  generano hook in **formato Copilot** (`version:1`, entry piatte, `powershell`/`bash`, `timeoutSec`)
  al posto degli asset Claude-format **rimossi**; gli script `.ps1` condivisi emettono il **contratto
  nativo per assistente** via `-Assistant` (sessionStart→`additionalContext`, agentStop→`decision:allow`
  non-bloccante, preToolUse **fail-open**); comandi **per-target** (VS Code prompt-file `agent:`, Copilot
  CLI **custom-agent**); `model:` omesso; **suite di validità-schema offline** che fallisce se un bug
  dell'audit rientra. Estensione **mirata** del seam `AssistantProfile`/`Surface` (non revisione profonda,
  YAGNI). Pipeline SpecKit completa; **Constitution 11/11**; **453 test verdi** (kit 126 · sertor 219 ·
  sertor-flow 108); `sertor-core` invariato, `sertor-flow` senza dipendenza dal core. **Gap dichiarato
  (mai parità piena):** SessionStart VS Code `[ASSUNTO-VSC]` + target MCP CLI da **verificare
  empiricamente** su ospite reale (follow-up). [[assistant-targeting]] aggiornato.

- **🚢 Ciclo di vita installer — `upgrade`/`uninstall` (FEAT-008 `sertor-cli`, feature 048, PR #71, 2026-06-17)** —
  l'installer acquista i verbi di **ciclo di vita** oltre al primo install: `sertor upgrade`/`uninstall`
  (tutto-in-uno **e** per-capacità, Q3) e i simmetrici `sertor-flow upgrade`/`uninstall` (Q4 — governance
  in ambito). Le **primitive di ciclo di vita vivono una volta sola nel `sertor-install-kit`**: verbo
  ortogonale `LifecycleOp{INSTALL/UPGRADE/UNINSTALL}` + outcome `UPDATED`/`REMOVED` + **funzioni inverse
  pure** duali 1:1 delle additive (D1 — scartato il raddoppio di `WriteStrategy`/`ArtifactKind`), riuso
  degli **stessi plan-builder** percorsi col verbo (D2 — nessun secondo plan-builder), tracciatura degli
  obsoleti via **diff a posteriori** `sertor_owned_paths` + **test invariante `plan ⊆ owned`** al posto
  di un manifest (Q2). `--purge-wiki` opt-in **CI-safe** (D4 — senza TTY né `--yes` il `wiki/` è
  preservato; `--purge-wiki --dry-run` = usage error). Report `install.report/1` **esteso in modo
  additivo** (no secondo schema). Invariante duro preservato: **`sertor-flow` senza dipendenza da
  `sertor-core`/`sertor`** (verificato via AST + guard di simmetria a 0 divergenze). Pipeline SpecKit
  completa specify→implement; **Constitution 11/11** pre/post senza deroghe; **393 test verdi**
  (kit 108 · sertor 180 · sertor-flow 105), ruff pulito. `docs/install.md §10` produttivizzato
  (comandi automatici via primaria, script manuale → fallback). **Chiude l'ultima Could rilevante
  dell'epica `sertor-cli`** (restano wizard config Should + ergonomia FEAT-010 + Codex + PyPI).

- **🚢 Packaging distribuibile `git+url` (FEAT-001 `sertor-cli`, feature 047, PR #68, 2026-06-17)** —
  chiude l'**unica casella Must rimasta** dell'epica `sertor-cli`: la distribuzione interim `git+url`
  diventa un percorso di prima classe, coerente e **verificato**. File **`LICENSE` MIT** in radice + ogni
  pacchetto (incluso nelle wheel via PEP 639); **versione unica** da `/VERSION` (dynamic hatchling) sui 4
  pyproject; **metadati di distribuzione** (urls/classifiers/keywords) su `sertor`/`sertor-flow`
  (install-kit esonerato, DA-P4); suite **`tests/integration/test_packaging.py`** (stdlib+subprocess, no
  import `sertor_core`, marker `integration`) che prova licenza→metadati→build→**install pulito reale**.
  Decisioni DA-P1..P4: versione allineata · `uv` primario+gate / `pip` best-effort documentato (→FEAT-010)
  · `sertor-core`/`install-kit` = dipendenze interne. Pipeline SpecKit completa; install pulito `uv`
  validato live (2 passed), `pip` xfail documentato; **Constitution 11/11**. PyPI resta FEAT-006 (Won't).
- **🛠️ Robustezza chunking — tetto del chunk al budget token dell'embedder (PR #69 + #70, 2026-06-17)** —
  bug emerso dal **dogfooding** del re-index post-merge: i chunker strutturali (markdown per heading,
  codice per simbolo) potevano emettere un chunk oltre il limite dell'embedder (`CLAUDE.md` 8357 tok >
  8192 di text-embedding-3-large → `http 400`), bloccando ogni re-index. Fix in due passi: #69 cap
  iniziale, #70 **cap in TOKEN** (`SERTOR_MAX_CHUNK_TOKENS`, default 8191 — usa la finestra piena del
  large invece di frammentare le sezioni coerenti), conteggio preciso con **tiktoken** dietro l'extra
  opzionale `tokenizer` (lazy) + **fallback per carattere** offline-safe; `_logic_version` aggiornato
  (FR-013). Corpus re-indicizzato pulito (max chunk 8191 tok, 0 oversized). *L'indicizzazione incrementale
  FEAT-009 si è confermata corretta end-to-end nello stesso giro.*

- **🚢 Refresh incrementale dell'indice (FEAT-009, feature 046, merge `3ec47f1`, 2026-06-16)** — chiude
  l'**ultimo residuo reale di `sertor-core`** (resta solo l'agenzia incorporata, Could differita).
  `index()` è ora **incrementale di default**: un **manifest SQLite** namespaced `(corpus, provider)`
  ricorda `mtime+content_hash+logic_version` e conserva le unità derivate (Document/Chunk); i file cambiati
  sono riprocessati con **upsert/delete mirati** sul vector store (`VectorStore.delete` già esistente) e
  **BM25+code-graph ricostruiti dal manifest** (decisione utente F1 — niente re-chunk/re-read degli
  invariati). Safeguard: **fallback automatico al full** su manifest assente/incompatibile, `--full` reset
  sicuro, invalidazione su cambio-logica, **lock single-writer** (`IndexLockedError`), riconciliazione
  off-default (`SERTOR_INDEX_RECONCILE_EVERY`, decisione F2/clarify), conteggi delta osservabili. Manifest =
  store concreto **senza nuova porta** (come EmbeddingCache). Pipeline SpecKit completa specify→implement,
  guidata da **ricerca prior-art** (CocoIndex/LlamaIndex/LangChain); **gate di equivalenza** incrementale≡full
  (byte-identico) verde; **596 test** non-cloud verdi, ruff pulito, **Constitution PASS 11/11 senza deroghe**.
  Genera la feature osservabilità **FEAT-012 drift-detection** (il segnale per il trigger della riconciliazione).

- **🚢 Distribuzione Copilot della governance/SDLC — `sertor-flow` (FEAT-009, feature 045, PR #65, 2026-06-15)** —
  **chiude la distribuzione multi-assistente Copilot end-to-end** (con FEAT-007). `sertor-flow install
  --assistant claude|copilot` porta il metodo SDLC anche su Copilot. **Pivot vendoring→launch-installer**
  ([[sertor-flow]]): SpecKit non più vendorato — `sertor-flow` lancia `specify init --ai <assistant>`
  (versione pinnata, via `CommandRunner`, fail-fast se assente), asset `speckit-*`/`specify/**` rimossi
  dal bundle; refactor del path **anche per Claude** (non-regressione verificata, `specify` mockato).
  Superfici Sertor-authored (`requirements-analyst`/`configuration-manager`/skill `requirements`/blocco
  SDLC) tradotte per Copilot via [[assistant-targeting]]; **renderer spostato nel `sertor-install-kit`**
  (condiviso `sertor`↔`sertor-flow`, anti-drift; `sertor` reimporta via shim). Costituzione
  assistant-agnostica. Invariante dura preservata: **nessuna dipendenza `sertor-flow`→`sertor-core`**.
  Constitution **11/11** con **1 deroga tracciata** (II: fetch install-time spec-kit, governance≠RAG);
  kit 49 · sertor 132 · sertor-flow 87 verdi, ruff pulito.
- **🚢 Distribuzione su GitHub Copilot — pacchetto `sertor` (FEAT-007, feature 044, PR #64, 2026-06-15)** —
  prima realizzazione della **parità di assistente** ([[assistant-targeting]]): l'installer `sertor`
  porta le superfici del pacchetto `sertor` (server MCP + sistema-wiki) anche su **GitHub Copilot** con
  `sertor install <cap> --assistant claude|copilot` (default `claude`, non-regressione verificata).
  Estende il **Principio X** all'assistente ospite. Design DA-2 = **ibrido (riuso contenuto + traduzione
  contenitore)**: nuovo seam `AssistantId`/`Surface`/`AssistantProfile` nel **`sertor-install-kit`** (lo
  riuserà FEAT-009), plan-builder parametrici, `merge_mcp` con `root_key` retro-compatibile. Copilot →
  MCP `.vscode/mcp.json`, istruzioni `.github/copilot-instructions.md`, prompt-file/custom-agent **resi
  da fonte unica** (+ guardia anti-drift), hook `.github/hooks/sertor-hooks.json` con **script riusati
  identici**. Invarianti: install≠run, non distruttivo, idempotente, CLI assistant-agnostic, segreti non
  versionati, gap dichiarati. Constitution **11/11**; kit 49 · sertor 132 verdi, ruff pulito. *Ambito
  solo `sertor`; governance `sertor-flow` = FEAT-009 (planned).*
- **🚢 Principio XI realizzato end-to-end (enforcement A-D, PRs #61/#62/#63, specs/041-043, 2026-06-15)** —
  il **Principio XI — Consumo via vehicles (CLI/MCP), non la libreria a runtime** è implementato in
  profondità (difesa in 4 livelli) e cablato sui sistemi ospiti. (A) **Auto-wire nel composition root:**
  helper `_wire_runtime` nelle 5 factory consumer-entry cabla config/osservabilità/error-handling
  uniformemente, chiudendo il gap del re-index via libreria non tracciato (658 eventi su 6163 in
  telemetria). (B+C) **Lato ospite:** blocco CLAUDE.md istruzione + hook PreToolUse rileva l'uso diretto
  della libreria → warning fail-open. (D) **Coerenza bundle:** `sertor-flow` usa plan-template generico
  upstream (intenzione non-drift, a differenza degli script gated del dogfood). Constitution PASS 11/11;
  suite verde (root 564 · kit 37 · sertor 104 · sertor-flow 107).

- **🚢 Governance/SDLC come pacchetto `sertor-flow` (FEAT-005, feature 037, PR #56, 2026-06-15)** —
  l'apparato di metodo di sviluppo (SpecKit + requisiti + delega git + costituzione + rituale) è ora
  **installabile su qualunque ospite** come pacchetto separato, ortogonale al RAG e **senza dipendenza
  da `sertor-core`**. Tre pezzi: (1) **`sertor-install-kit`** — motore di installazione **estratto** in
  un toolkit condiviso stdlib-only (artifacts/resources/report/claude_md/merge/executor/sync +
  errors/observability), riusato anche da `sertor`; (2) **`sertor`** repointato sul kit (re-export shim,
  non-regressione mantenuta); (3) **`sertor-flow`** — CLI `sertor-flow install`, thin consumer, bundle 68
  asset (SpecKit vendored MIT 0.8.18 + requirements/configuration-manager + costituzione-starter neutra +
  blocco SDLC a marker distinti + NOTICE). `sertor install governance` → puntatore. install≠run,
  idempotente, non-distruttivo, offline. SpecKit completo; Constitution PASS 10/10; full-suite verde
  (root 560 · kit 37 · sertor 86 · sertor-flow 106). 7 DA risolte in sessione. *Distill entità +
  re-index in corso.*

- **🚢 Memoria conversazioni — FEAT-003 aggancio distillazione all'archivio (feature 036, PR #51,
  2026-06-14)** — chiude il loop **cattura→distillazione** dell'epica: l'archivio episodico diventa
  una **fonte recuperabile** per la modalità «from conversation» di `distill` (finora solo teorica,
  pretendeva un brief a mano). Comandi *thin consumer* `sertor-rag memory show <key>` (transcript
  intero, umano/`--json`, non troncato) e `memory list` (sessioni recenti). Core additivo: riuso di
  `MemoryArchive.get` + nuovo `list_recent`, **nessuna nuova porta** (factory `build_memory_reader`
  gated). `distill.md` aggiornato. **Vincolo cardine FR-013:** distillazione dall'archivio sempre su
  sessione mirata, su invocazione esplicita — mai sull'intero archivio, mai automatica (cattura
  economica e distillazione costosa restano disaccoppiate; l'archivio è BACKUP, non RAM). Constitution
  PASS 10/10, 558 test non-cloud verdi (31 nuovi), additivo puro. *Provato live* sul dogfood. Nuova
  pagina [[feat-036-aggancio-distillazione]].
- **🚢 Memoria conversazioni — superficie CLI + hook SessionEnd (feature 035, PR #49, 2026-06-14)** —
  rende l'MVP memoria **usabile dal terminale e automatico**: comandi *thin consumer*
  `sertor-rag memory archive` (idempotente) e `memory search "..."` (filtri temporali, umano/`--json`)
  + **hook Claude Code `SessionEnd`** (`.claude/hooks/memory-capture.ps1`) che cattura a fine sessione,
  **non-bloccante/non-fatale**, **gated** su `SERTOR_MEMORY` (off → comando con errore azionabile, hook
  no-op). Comandi host-agnostici, hook host-specifico (Principio X). Core FEAT-001/002 invariato.
  Constitution PASS 10/10, 12 test, 527 non-cloud verdi. *Provato live* (`memory search "GraphRAG"` →
  turni reali). *Resta:* accendere `SERTOR_MEMORY` per attivarla.
- **🚢 Memoria conversazioni — FEAT-002 ricerca episodica full-text (feature 033, PR #47, 2026-06-14)** —
  chiude l'**MVP memoria** ([[ricerca-episodica-fts5]]): l'archivio di FEAT-001 è ora **interrogabile**
  («ne avevamo già parlato?»). Componente concreto `EpisodicSearch` (no porta) su **SQLite FTS5 nativo**
  (`bm25()`+`snippet()`, tabella virtuale `turns_fts` mantenuta da trigger di sync), ricerca a grana di
  **turno** con citazione (sessione, ruolo, snippet, score) + filtro temporale; **sola lettura** sui dati
  (indice FTS derivato/ricostruibile), stdlib-only, **zero cloud** nel percorso query (privacy by design),
  query **hashata** nei log. Constitution PASS 10/10, 27 test, 515 non-cloud verdi. *Provato live* sul
  dogfood (5062 turni). *Resta:* superficie CLI (PLANNED) + ricerca semantica FEAT-004 (Should).
- **🚢 Memoria conversazioni — FEAT-001 cattura & archiviazione (feature 031, PR #45, 2026-06-14)** —
  il **tier grezzo episodico** che mancava ([[memoria-conversazioni]]): 8ª porta
  `TranscriptCaptureAdapter` + adapter Claude-Code (legge i JSONL di sessione `~/.claude/projects/…`),
  store concreto `MemoryArchive` (SQLite `<index_dir>/memory.sqlite`, conservato, idempotente,
  granularità **ibrida** sessione+turni per FEAT-002), `scrub_text` (segreti rimossi dal contenuto),
  servizio orchestrante, 5 manopole, wiring lazy/gated. **Privacy-by-default** (`SERTOR_MEMORY` off).
  SpecKit completo, Constitution PASS 10/10, 29/29 task, 488 test non-cloud verdi. *Manca:* superficie
  d'avvio (PLANNED) + ricerca FEAT-002 (PLANNED). NB: nuove pagine [[transcript-capture-adapter-e-storage]],
  [[scrub-segreti-in-contenuto]], explainer [[memoria-negli-agenti]].
- **🚢 Osservabilità accesa + errori MCP segnalati (PR #40/#43, 2026-06-14)** — `enable_observability`
  cablato nei consumatori CLI/MCP e **acceso sul dogfood** (`SERTOR_OBSERVABILITY=true`, 11 eventi
  catturati); ogni errore del server MCP ora persiste come evento `mcp.<tool>.error` + self-test
  end-to-end allo startup (sarebbe emerso subito il 401/`rank_bm25` di oggi). Governance anti-fallback
  silenzioso negli agenti che usano `sertor-rag`.
- **🚢 MVP Osservabilità e pannello di controllo (epica `osservabilita`, F1→F4, PR #34/#35/#36/#38,
  2026-06-14)** — Sertor è ora **trasparente su sé stesso** ([[il-pannello-di-controllo]]): **F1** strato
  persistente (store SQLite `observability.sqlite` + 7ª porta `ObservabilityStore`, cattura via
  `logging.Handler`, `SERTOR_OBSERVABILITY` default off) → **F2** servizio `ObservabilityReports` (5
  report cache/costo/salute/latenze/affidabilità da `query_events`, funzioni pure) → **F3** pannello TUI
  vista live (`sertor-rag observe`, auto-aggiornante, extra `[tui]` Textual isolato) → **F4** report
  sfogliabili a schede (Live/Cache/Cost/Corpus, tasto `t` intervallo all/7g/24h, freschezza). Privacy-by-
  default (solo metriche, mai testo). Architettura: modello/aggregazione **puri** nel core + guscio
  Textual sottile; sola lettura; degradazione onesta. Constitution PASS 10/10 ×4; ~470+85 test verdi.
  *Restano Should/Could:* export OTel · metriche aggregate · stima € · web mode. Più: **fix `wiki/wiki/`**
  (PR #37) — resolver wiki reso cwd-indipendente.
- **🚢 Cache embeddings + token nei log (hardening gruppo C, feature 019, PR #33, 2026-06-14)** — chiude
  i due Should del costo d'indicizzazione ([[indexing-and-retrieval]]): `CachingEmbedder` (decoratore
  della porta `EmbeddingProvider`, servizi invariati) + `EmbeddingCache` (store SQLite
  `<index_dir>/embed_cache.sqlite`, chiave `(model, sha256)`, vettori float64 esatti → indice
  byte-equivalente, degrado non-fatale); wiring solo sul percorso d'indicizzazione, manopola
  `SERTOR_EMBED_CACHE` (default off). + token nei log (`embeddings` con `usage.total_tokens`/
  `prompt_eval_count`, omesso se assente) e fix redazione segreti per-parola. SpecKit completo, 395+85
  test verdi, Constitution 10/10. Cache **attivata sul dogfood**. NB: nuova **area wiki `explainers/`**
  (descrizioni per non tecnici) consegnata nella stessa PR.
- **🚢 Manutenzione wiki deterministica (FEAT-007, feature 017, PR #30, 2026-06-13)** — chiude
  l'ultimo Should del core ([[wiki-tools]]): `sertor-wiki-tools move` (sposta/rinomina una pagina e
  riscrive i link entranti — wikilink form-preserving + relativi, `--dry-run`, recovery,
  `wiki.move/1`), `reconcile` (detection read-only delle pagine `status: superseded` +
  `superseded_by`, `wiki.reconcile/1`), `collect`+campo `status`; trigger periodico = doc (scheduler
  ospite). stdlib-only, offline, non-distruttivo; 434 test verdi, Constitution 10/10 senza deroghe.
  I gruppi della dote FEAT-007 sono tutti chiusi: A (probe) Won't · E (seed)/F (asset EN) consegnati
  a parte (PR #27/#28/#29) · B/C/D qui. Primo uso reale: riconciliata `pulizia-pycache-e-diagnosi-mcp`.
- **🚢 Igiene radice host (feature 016, PR #26, 2026-06-13)** — radice ospite pulita e prevedibile
  ([[sertor-installer]]): `wiki.config.toml` spostato in `wiki/` con **auto-discovery** nel CLI
  (`./wiki.config.toml` poi `./wiki/wiki.config.toml`, root=CWD) così le invocazioni ad-hoc non si
  rompono; `sertor install rag --mcp-scope project|local` (5° `ArtifactKind` `MCP_REGISTER` via
  `claude mcp add-json --scope local` dietro `CommandRunner`, idempotente, fail-fast); `.sertor/`
  confermata unica sede runtime + doc dei residenti inevitabili (`docs/install.md §7`). Fix Sertor
  one-shot (config + asset ri-sync); retrocompat ospiti esterni fuori ambito (D4). 410 test verdi,
  Constitution 10/10 senza deroghe; SpecKit completo specify→implement in giornata.
- **🧩 Agentic RAG in forma composita (FEAT-006, 2026-06-13)** — la quarta modalità RAG **esiste
  senza codice nuovo da scrivere**: il sistema [server MCP a 7 tool] + [agente client frontier]
  pianifica, seleziona i tool, itera e cita — *è* agentic RAG. Decisione utente: nessun motore
  incorporato da costruire (un loop con un modello minore non migliorerebbe l'orchestratore
  frontier). I «4 motori» dell'epica si chiudono così: vettoriale + ibrido + code-graph +
  agentico (composito). L'**agenzia incorporata** nel core resta dote differita (vedi PLANNED).
- **🚢 Installer `sertor install rag` (feature 015, 2026-06-12, su master)** — la **capacità RAG su un
  ospite con UN comando** ([[sertor-installer]]): scaffold config (`.env`/`.mcp.json`/`.gitignore`) +
  bootstrap dipendenze via `uv` in un **runtime isolato `<host>/.sertor/`** (i sorgenti host, anche
  non-Python come .NET, non vengono "pythonizzati"); riusa il backbone di `install wiki` (4 nuovi
  ArtifactKind, `CommandRunner` mockabile). install ≠ run, idempotente, segreti vuoti. **Validato live
  su un repo reale** (`uvx … sertor install rag` su Kaelen → `sertor-rag index` 150 doc/1755 chunk,
  Azure `text-embedding-3-large`). **Finding chiave:** il "bug" di distribuzione `uvx` era una
  **diagnosi errata** — `uv` risolve `sertor-core` scoprendo il workspace dal git, nessun fix
  necessario (FR-024 ✅); il fix ipotizzato avrebbe rotto il dev (revocato). Bug reale trovato live e
  fixato (`uv init --name`, `.sertor` non è un package name valido). Lavorato su `master` (bugfix
  autorizzato); 76 (pacchetto) + 321 (root) test verdi. SpecKit completo requirements→implement.
- **🚢 Motore a grafo / code-graph strutturale (FEAT-005, feature 014, PR #25, 2026-06-12 sera)**
  — terza capacità RAG, ortogonale ai motori ([[code-graph]]): porta `CodeGraph` (sesta), build
  integrato in `index()` (mai grafo stantio), artefatto JSON per corpus, copertura per-linguaggio
  DICHIARATA e verificata sui 10 linguaggi; **i 4 tool MCP storici sono tornati**
  (find_symbol/who_calls/related_docs/get_context, superficie a 7 tool). Misure: recall 1.00 sul
  ground-truth reale, precisione 1.00 sul mini-corpus; dogfood live 1.180 nodi/1.202 calls,
  query <0.1ms. SpecKit completo in serata; 321+38 test.
- **🚢 Motore RAG ibrido + reranking (FEAT-004, feature 013, PR #24, 2026-06-12)** — seconda
  modalità RAG e **nuovo default** ([[hybrid-retrieval]]): BM25 (porta `LexicalIndex`, sidecar
  atomico) + denso fusi con RRF; degradazione onesta sui corpora pre-ibrido (REQ-034); reranking
  FlashRank come extra `rerank` lazy; consumatori MCP/CLI invariati (strategia iniettata).
  **Chiusi i 2 xfail storici** (strict: simboli hit@5 0.00→1.00; +rerank MRR 0.939). SpecKit
  completo in giornata; 273+38 test; dogfood live validato (ibrido in 666ms).
- **Hotfix server MCP (PR #23, 2026-06-12)** — risolto l'hang della prima query di sessione su
  Windows (init pigro di Chroma parcheggiava il task fino al prossimo evento stdin): warm-up eager
  della facade in `main()`; prima chiamata da 51+ min appesa → 0.6s; metodo di troubleshooting
  documentato in [[mcp-server]]. 222 test verdi.
- **Installer `sertor install wiki` (feature 012, PR #22, 2026-06-11 sera)** — il pacchetto
  **`sertor` distinto** (uv workspace) che porta il sistema-wiki su qualunque ospite
  ([[sertor-installer]]): non distruttivo per artefatto, idempotente, install≠run, assets
  package-data come fonte canonica (`.claude/` = derivato + test di guardia). **Validato live su un
  repo ospite reale** (hook utente preservati, wiki operativo, re-run idempotente). 221+38 test.
  Guida: `docs/install.md`. Aperto: tema lingua (PLANNED).
- **CLI di esecuzione RAG `sertor-rag` (feature 011, PR #21, 2026-06-11)** — terza superficie del
  core ([[sertor-rag-cli]]): `index`/`search` dal terminale, osservabilità a runtime, validazione
  statica del backend. SpecKit completo in giornata (specify→plan→tasks→analyze→implement); suite
  **204 passed + 2 xfail**; SC-008: risultati CLI ≡ server MCP. DA-8: `sertor` resta riservato
  all'installer (PLANNED).
- Nucleo retrieval (FEAT-001) · motore baseline (FEAT-002) · server MCP (FEAT-MCP).
- **Wiki LLM (FEAT-003) COMPLETATA (2026-06-10)** — l'ultimo Must dell'epica: nucleo deterministico
  `wiki_tools` + operazioni-giudizio come skills/playbook. Nella giornata di chiusura: N1 riconciliata,
  N2 (`distill` a 3 ingressi → [[diary-vs-graph]]), N3 (`generate` a 2 ingressi + preset profondità,
  esercitata leggera+media su spec-kit), N4 (`ingest` → prime pagine `sources/`: gist Karpathy + v2),
  N6 (gerarchia di verità + supersession nel playbook §4, SC-009 su pagina pycache); N5/N9 → FEAT-007.
- **Query congiunta multi-collezione + `upsert-index` in CLI** (feature 010, `specs/010`, PR #20 mergiata il
  2026-06-10): capacità di fan-out su più corpora (`SERTOR_EXTRA_CORPORA`, fail-fast su provider eterogenei) +
  write-back dell'indice cablato. I pezzi D di FEAT-003 sono chiusi. **D-21 (stesso giorno):** modello
  standard = **corpus unico** (il wiki vive dentro l'ospite by design → già nel corpus primario); il fan-out
  resta per ospiti con corpora disgiunti.
- Lavori abilitanti: decoupling store↔embeddings (`specs/009`) · meccanica log (`specs/008`) · indice dogfood
  `sertor` vivo via MCP · **regola standing di re-index dei corpora** a fine step (2026-06-10, mitiga la
  FEAT-009 d'epica).
- **Startup di sessione**: hook SessionStart **sottile** (direttiva-`Read`, ~630 B) che fa caricare roadmap/index/log
  al flusso principale e mostrare l'executive summary — supera il cap ~10K del canale-hook (verificato in sessione 2026-06-09).
<!-- EXEC:END -->

## Visione

Portare capacità **RAG** (ricerca semantica su codice + documentazione) su **qualunque repository**, in modo
riproducibile e production-grade. **Una sola verità interrogabile**: sorgenti (il *come*) e doc/wiki (il
*perché*) coesistono nello stesso corpus; la doc nuova vive **accanto ai sorgenti** via LLM Wiki. Local-first
↔ cloud per configurazione; riusabile come **libreria**, esposta via **CLI** e **MCP**.

## ⚠️ Due numerazioni (da non confondere)

- **`FEAT-NNN` (epica)** = capacità di prodotto nel backlog (`requirements/sertor-core/epic.md`).
- **`specs/NNN`** = ordine **sequenziale** di implementazione. NON coincide con l'epica: `specs/008`
  (meccanica del log) e `specs/009` (decoupling store) sono **lavori abilitanti** sul nucleo/wiki-tools,
  **non** le FEAT-008/009 dell'epica (arricchimento Wiki↔RAG / refresh incrementale, ancora da decomporre).

## Stato in breve (al 2026-06-11)

- **Su `master`** (l'unico asset reale): nucleo di retrieval + motore baseline + **wiki** (metà
  deterministica `wiki_tools` **in codice** + metà giudizio **come skills/playbook** in `.claude/`) +
  **server MCP** + **query congiunta multi-collezione** e `upsert-index` in CLI (feature 010) +
  **CLI di esecuzione RAG `sertor-rag`** (feature 011, [[sertor-rag-cli]]) + **installer
  `sertor install wiki`** (feature 012, [[sertor-installer]], pacchetto distinto in workspace), più
  i lavori abilitanti (meccanica log, decoupling store/embeddings, regola di re-index).
- **Dogfooding di produzione VIVO**: corpus `sertor` (207 doc / 1778 chunk, **wiki incluso** come
  documentazione — modello a corpus unico, D-21), embeddings Azure `text-embedding-3-large` + Chroma
  locale in `.index-sertor/`. Servito dal server MCP `sertor-rag`. La collezione `wiki__*` resta come
  capacità esercitabile (rag-sync), senza consumatori.
- **Rami abbandonati (NON su `master` → non contano come asset):** il vecchio tentativo CLI
  (`specs/004`, superato dalla feature 011 reimplementata su master) e i tentativi *in codice* di
  FEAT-003-N (`specs/003`/`005`, superati dall'approccio a skills). Oggi il prodotto è usabile come
  **libreria + server MCP + CLI `sertor-rag`**; manca l'**installer** `sertor install <capacità>` (DA-8).
- Qualità: **359 test verdi** (321 root + 38 pacchetto `sertor`; **zero xfail**: i 2 storici di
  misura sono strict dal 2026-06-12), ruff pulito su src/tests/packages; ogni feature su master
  passata col **Constitution Check** (costituzione v1.1.0, 10 principi).

## Mappa delle feature (epica `sertor-core`) & stato reale

Legenda: ✅ su master · 🧪 operativo, consolidamento formale aperto · 💀 ramo morto (non su master) · 🔜 prossima (Should) · 💤 dopo (Could)

| ID epica | Feature | Pri | Stato | Dove |
|---|---|---|---|---|
| FEAT-001 | Nucleo di retrieval (ingestione, chunking code-aware, embeddings, vector store, facade) | Must | ✅ | `specs/001`, `src/sertor_core` |
| FEAT-002 | Motore RAG vettoriale (baseline) | Must | ✅ | `specs/002`, `engines/baseline` |
| FEAT-003 | Skill: creare/indicizzare l'LLM Wiki | Must | ✅ **COMPLETATA (2026-06-10)**: D al 100% (feature 010 inclusa — [[spec-010-query-congiunta-e-upsert-index]]) + N tutte chiuse (N1/N2/N3/N4/N6/N8 ✅, dettaglio nel tracker) o riassegnate (N5/N9 → FEAT-007; N7 ⛔ D-20) | vedi sotto |
| — FEAT-003-D | …nucleo **deterministico** (`wiki_tools` + `wiki.config.toml`) | Must | ✅ | `specs/006` (PR #13), `src/sertor_core/wiki_tools` |
| — FEAT-003-N | …operazioni **assistite da LLM** (record/distill/lint/ingest) | Must | ✅ come **skills/playbook** (giudizio ≠ codice) | `.claude/skills/wiki-author`, `/wiki`, `wiki-curator` |
| FEAT-MCP | Server MCP di produzione (`sertor_mcp`, superficie su `build_facade`) | Should | ✅ | `specs/007` (PR #15) |
| FEAT-004 | Motore RAG **ibrido + reranking** | Should | ✅ **master (2026-06-12, PR #24)** — nuovo default ([[hybrid-retrieval]]); xfail storici chiusi strict | `specs/013`, `engines/hybrid`, `adapters/lexical` + `adapters/rerank` |
| FEAT-005 | Motore RAG a **grafo / GraphRAG** *(riporta `find_symbol`/`who_calls` nel MCP)* | Should | ✅ **master (2026-06-12, PR #25)** — code-graph strutturale ([[code-graph]]); promessa dei 4 tool mantenuta | `specs/014`, `services/graph_extraction`, `adapters/graph` |
| FEAT-006 | Motore RAG **agentico** (multi-step, query planning) | Should | ✅ **soddisfatta in forma composita (2026-06-13)** — MCP+agente = agentic RAG; agenzia incorporata = dote Could differita | composito (MCP + agente client) |
| FEAT-007 | Skill: **mantenere il wiki vivo** (spider/lint) *(2026-06-10: assorbe da FEAT-003-N la N5 lint semantico — residuo: probe deterministici di freschezza — e la N9 lint organizzativo/reorg)* | Should | 🔜 da decomporre | — |
| FEAT-008 | Arricchimento bidirezionale **Wiki↔RAG** | Could | 💤 da decomporre | — |
| FEAT-009 | **Refresh incrementale** dell'indice (solo file cambiati) | Could | 💤 da decomporre | — |

### Epica `sertor-cli` (il veicolo) — **nucleo consegnato**, aggiornata il 2026-06-17

**DA-8 (2026-06-11) — split installer/esecuzione:** `sertor` = solo **install** (`sertor install
<capacità>`) + **ciclo di vita** (`upgrade`/`uninstall`, FEAT-008); l'**esecuzione** vive nei
console-script del core (`sertor-rag`, `sertor-wiki-tools`).

Legenda: ✅ consegnata · 🔄 parziale (nucleo fatto, residuo aperto) · 📋 da decomporre · 💤 Won't.

| ID | Feature | Pri | Stato |
|---|---|---|---|
| FEAT-001 | CLI installabile + **packaging distribuibile** `git+url` | Must | ✅ esecuzione `sertor-rag` (PR #21) + packaging LICENSE/versione/metadati/build (PR #68, 2026-06-17) |
| FEAT-002 | Installazione selettiva delle capacità (`install wiki`/`rag`/`governance`) | Must | ✅ `install wiki` (PR #22) · `install rag` (live su Kaelen) · `governance` = puntatore a `sertor-flow` |
| FEAT-003 | **Configurazione** (provider LLM + vector DB; **wizard**) | Should | ✅ **CONSEGNATA (PR #75, 2026-06-17)** — `sertor configure [rag]`: CI-safe, scrittura `.env` non-distruttiva, validazione statica, anti-leak segreti. `--check`/US5 deferred (→ `sertor-rag check` core) |
| FEAT-004 | Comando esecuzione RAG (`index`/`search`) | Should | ✅ feature `esecuzione` (PR #21) |
| FEAT-005 | Setup governance (skill/agenti SDLC + requisiti) | Should | ✅ pacchetto separato `sertor-flow` (PR #56) |
| FEAT-007 | Distribuzione **Copilot** — pacchetto `sertor` (wiki+rag) | Must | ✅ consegnata (PR #64/#66); schema sanato FEAT-011 (PR #73); **consolidata CLI-only FEAT-012 (PR #76)** — VS Code rimosso, verificata live |
| FEAT-009 | Distribuzione **Copilot** — governance `sertor-flow` | Must | ✅ consegnata (PR #65); schema sanato FEAT-011; **CLI-only FEAT-012** (naming `copilot-cli`, `requirements` custom-agent) |
| **FEAT-012** | **Consolidamento Copilot CLI-only** (rimozione VS Code, naming uniforme, `requirements` custom-agent, mapping upstream) | Should | ✅ **CONSEGNATA (PR #76, 2026-06-17)** — 530 test, Constitution 11/11, core invariato |
| **FEAT-008** | **Ciclo di vita installer** — `upgrade`/`uninstall` (sertor + sertor-flow) | Could | ✅ **CONSEGNATA (PR #71, 2026-06-17)** — primitive nel kit, diff a posteriori, `--purge-wiki` CI-safe ([[installer-lifecycle]]) |
| **FEAT-011** | **Hardening compatibilità Copilot** — schema nativo (hook `version:1`/flat/`powershell`; output `.ps1` per-assistente; comandi via custom-agent su CLI; frontmatter `agent:`/no `model:`; suite validità-schema) | Must | ✅ **CONSEGNATA (PR #73, 2026-06-17)** — 453 test verdi, no-hack nativo. ⚠️ **Gap dichiarato:** SessionStart VS Code `[ASSUNTO-VSC]` + MCP CLI da **verificare empiricamente** su ospite reale (follow-up) |
| FEAT-010 | **Ergonomia & portabilità** (fallback `pip` · avviso target non-Python · hook Linux `sh` · install multi-target · reviewer clean-code) | Could | 📋 **in coda** (dopo FEAT-003 wizard + refactor CLI-only; decisione utente 2026-06-17) |
| FEAT-006 | Distribuzione pubblica **PyPI** | Won't | 💤 rinviata (gating: licenza MIT scelta) |

> **Stato epica:** nucleo consegnato (packaging FEAT-001 + lifecycle FEAT-008 + **hardening compat
> Copilot FEAT-011**, PR #73). La conformità allo schema nativo Copilot è sanata (hook/output/comandi/
> frontmatter); **resta da verificare empiricamente sul client reale** il SessionStart VS Code
> (`[ASSUNTO-VSC]`) e il target MCP della CLI → **follow-up** (vedi §Nuove funzionalità). Altro
> residuo: **FEAT-003 wizard config** (Should), **FEAT-010 ergonomia** (Could, da decomporre),
> **Codex** (Could, non avviato), **PyPI** (Won't).

> Oggi il prodotto si usa come **libreria** (`import sertor_core`), via **server MCP** e via
> **CLI `sertor-rag`** ([[sertor-rag-cli]]). Il vecchio ramo CLI (`specs/004`) è definitivamente
> superato dalla feature 011.

## Lavori abilitanti già mergiati (non sono FEAT d'epica)

| Spec | Cosa | Esito |
|---|---|---|
| `specs/008` | Meccanica del log del wiki (rotazione giornaliera + `append-log` curato + `migrate`) | ✅ PR #18 |
| `specs/009` | **Decoupling store ↔ provider di embeddings** (`SERTOR_STORE_BACKEND`) + `AzureEmbedder` v1 | ✅ PR #19 → ha abilitato l'indice dogfood `sertor` |

## Roadmap per fasi

- **✅ Fatto (master):** Nucleo · Baseline · Wiki (deterministico `wiki_tools` + operazioni LLM come skills) · Server MCP · CLI di esecuzione `sertor-rag` (feature 011) · Decoupling store · Indice dogfood `sertor` (vivo via MCP e CLI).
- **💀 NON su master (rami abbandonati — non contano):** CLI `sertor` (`specs/004`) · tentativi *in codice* di FEAT-003-N (`specs/003`/`005`, superati dalle skills). Da rifare su master se servono.
- **🔜 Prossimo (Should):** Manutenzione wiki (FEAT-007) · Distribuzione multi-assistente (FEAT-007 CLI). *(FEAT-006 agentico ✅ soddisfatta in forma composita: MCP+agente è agentic RAG; agenzia incorporata = dote Could differita.)*
- **💤 Dopo (Could):** Arricchimento Wiki↔RAG (FEAT-008) · Refresh incrementale indice (FEAT-009).

---

## 🧭 Nuove funzionalità da discutere (sezione a mano)

> Idee **prima** che diventino feature formali. Stati: 💡 idea · 🗣️ in discussione · 👍 approvata (→ decomporre) · ❌ scartata.

| Idea | Valore / perché | Note / vincoli | Stato |
|------|-----------------|----------------|-------|
| **`sertor-rag check` — probe di connettività del vehicle** (epica `sertor-core`) | Verifica «le credenziali/il provider funzionano davvero» senza un indice: serve a `sertor configure --check` (FEAT-003 US5) e in generale come health-check. Oggi `sertor-rag` ha solo `index`/`search`/`observe`/`memory`; `search` richiede un indice → inadatto a freddo | Comando di `sertor-core` (vehicle, Principio XI): embed di prova via il provider configurato, esito + errore azionabile, niente scrittura. Sblocca `--check`/US5 del wizard (oggi degradato onestamente) | 👍 **follow-up tracciato (2026-06-17)** — da promuovere a FEAT di `sertor-core` |
| **Verifica empirica della distribuzione Copilot su ospite reale** | FEAT-011 conforme *offline*; la prova che **funzioni davvero** si ha solo sul client reale (spirito «installato≠funzionante») | **FATTA END-TO-END** su Copilot CLI 1.0.63 (log interattivi): **MCP** connesso (7 tool), **tutti gli agent** caricati (wiki + governance + 10 speckit), **tutti e 4 gli hook** scattano (SessionStart/PreToolUse/Stop/SessionEnd — Stop/SessionEnd silenziosi se nessun pending). Scoperti+risolti 3 bug (PR #74); il log pre-fix conteneva `prompt hook prompt is required` → conferma del fix. Discovery: config di progetto caricata solo in sessione INTERATTIVA, non in `-p`. | ✅ **fatto end-to-end (2026-06-17, PR #74)** |
| **Refactor distribuzione Copilot CLI-only** (decisioni utente 2026-06-17) | Eliminare il footgun VS Code↔CLI e l'incoerenza di naming; supporto nativo pieno di un solo target | drop VS Code · naming `copilot-cli` uniforme · `requirements` custom-agent · mapping upstream in un punto | ✅ **fatto → FEAT-012 (PR #76, 2026-06-17)** |
| **Rilevamento attivo dei gap di documentazione** (codice→wiki generativo) | Il residuo *genuino* di FEAT-008: oggi il legame codice↔doc è **passivo** (lo interroghi con `get_context`/`related_docs`), manca il **generativo** — il RAG/code-graph che rileva **entità di codice senza pagina wiki** e le **propone** al `wiki-author` | Scorporato dalla chiusura di FEAT-008 (✅ composita, verificata live 2026-06-16). Casa candidata: feature wiki dedicata o `debito-tecnico` FEAT-005 (igiene-wiki). Riusa il [[code-graph]] (`find_symbol`/`related_docs`) + lint C | 💡 **idea, scorporata da FEAT-008** (2026-06-16) |
| **Pannello di controllo (TUI) di osservabilità** | Vedere log, consumo (token/€), #chunk, **hit/miss della cache** e fare report. Sertor già emette log strutturati ricchi ma effimeri | **Epica aperta** `requirements/osservabilita/epic.md` (10 feature MoSCoW, 2 strati: osservabilità persistente nel core + pannello TUI). Fork decisi: **superficie = TUI** (web=Could fase 2), **dati = store SQLite locale + export OTel opzionale**. Assorbe «logging come strategia runtime» e i Could **H9/H10** dell'hardening. MVP = FEAT-001→004 (persisti→aggrega→TUI live→report) **+ stima € (Should, DA-O-g risolta)**. Privacy fissata (DA-O-d): **privacy-by-default a strati** (metriche di default · testo opt-in · semantico opt-in ulteriore). Restano domande di design (cattura "live", retention, innesto su `log_event`) | 👍 **epica aperta, da decomporre** (utente, 2026-06-14) |
| **Memoria conversazioni (terzo livello / episodica, pattern Hermes)** | Archiviare TUTTE le conversazioni come tier grezzo episodico, interrogabile nei casi speciali («ne avevamo già parlato?»); è il tassello mancante sotto il diario del wiki, fonte grezza per la distillazione | **Epica aperta** `requirements/memoria-conversazioni/epic.md` (8 feature MoSCoW). Distinta dall'osservabilità (conoscenza ≠ telemetria), **privacy condivisa** (privacy-by-default, FTS locale, semantico opt-in). MVP = cattura + ricerca episodica locale. **Nodo:** la cattura è host-specifica (Claude Code → harness) → si lega alla distribuzione multi-assistente. Mappa Hermes↔Sertor in epic.md | 👍 **epica aperta, da decomporre, in parallelo** (utente, 2026-06-14) |
| **Second brain cross-progetto** (il «Sertor dei Sertor» / Meta-Sertor) | Conoscenza condivisa e di più alto livello su TUTTI i propri contesti: condividere esperienze/metodologie, scambiarsi skill/agenti, **sintetizzare asset nuovi** da più progetti. Sertor da autore a **giardiniere della flotta** | Sertor ricorsivo (L0/L1/L2); riusa feature 010 (fan-out) + installer + Principio X; nuovo = confine di **promozione** (giudizio) + **verifica/parametrizzazione** asset + trust/decay. Pagina-visione con diagrammi: [[second-brain-cross-progetto]] | 👍 **promossa a epica `second-brain` (2026-06-16)** — resta DA ESPANDERE (bivi §9) |
| **Misurare la pertinenza** (chiudere gli `xfail`) con ground-truth reale | Trasforma "funziona" in "misurato" (Principio V); confronto provider | Serve set query→file atteso; baseline = prototipo | 👍 **promossa a epica `retrieval-qualita` FEAT-001 (2026-06-16)** |
| Migliorare la **qualità `search_code`** (oggi debole su query architetturali) | Il retrieval di codice è il caso d'uso primario | Naturale candidato per FEAT-004 (ibrido) / FEAT-005 (grafo) | 👍 **promossa a epica `retrieval-qualita` FEAT-003 (2026-06-16)** |
| Promuovere **PowerShell / T-SQL / PL-SQL** da fallback a chunking sintattico | Qualità di chunking per questi linguaggi | Validare node-type tree-sitter; incrementale | 👍 **promossa a epica `ingestione-estesa` FEAT-003 (2026-06-16)** (+ Bash) |
| **Logging come strategia runtime** (osservabilità porta+adapter scelta a runtime) | Oggi la CLI non instrada i log da nessuna parte | Refactor deterministico → SpecKit | 💡 idea |
| **Tema lingua** (asset installer in inglese, contenuto in lingua host) | Coerenza dell'esperienza su ospiti non-italiani | **Implementato 2026-06-13** (pass mirato): asset+CLI host-facing in inglese + guardia. Residuo: seed localization it/en (D3) + traduzione graduale delle error-string profonde/docstring | ✅ **fatto (asset); seed = follow-up)** |
| **Distribuzione multi-assistente: GitHub Copilot (+ Codex Could)** | Le capacità non devono dipendere da un solo assistente: MCP nei client Copilot + superfici agentiche tradotte (copilot-instructions/prompt files; Codex: AGENTS.md) | Nuova FEAT-007 epica CLI; distinto da DA-6 (Copilot lì è provider LLM); CLI già assistant-agnostic. **Decomposta** in `distribuzione-copilot/requirements.md` (22 REQ, parità piena, ambito wiki+rag) | ✅ **decomposta (2026-06-15)** → `/speckit-specify` |
| **Adapter VectorStore per PGVector / MongoDB su Azure** | Ibrido e retrieval su store cloud alternativi ad AI Search (il motore ibrido è già store-agnostico via porte) | Nuovi adapter della porta `VectorStore` (+ eventuale delega ibrida nativa per Atlas Search); feature separata da FEAT-004 | 👍 **promossa a epica `backend-store-scala` FEAT-001/002 (2026-06-16)** |
| **Conoscenza-schema SQL come corpus interrogabile** | Interrogare «dov'è un dato, quale tabella/vista/stored-procedure/query usare per accedervi», **fuso col corpus di codice+doc**. Prior art mostra un buco: nessuno unisce schema+SP+query-buone+codice applicativo in un endpoint unico — ed è lo spazio di Sertor | Mappa sull'architettura: nuovo sorgente d'ingestione (DDL/viste/SP) nel corpus unico + **schema-graph parallelo al [[code-graph]]** (lineage via `who_calls`). **Prerequisito:** parsing sintattico T-SQL/PL-SQL (oggi esclusi R-N2). Ricognizione completa in [[conoscenza-schema-sql-rag]] (DataHub/WrenAI/Vanna/RASL/SchemaGraphSQL). Domande aperte: introspezione live vs parsing statico file-based, confine col Text-to-SQL, cattura pattern d'accesso | 👍 **promossa a epica `conoscenza-schema-sql` (2026-06-16)** — scope aperto in §9 |
| **Distribuzione della memoria via installer** (FEAT-009 epica memoria) | Per la regola «feature completa = installabile» (CLAUDE.md), l'MVP memoria **non è completo** finché un ospite non lo riceve via `sertor install`: manopole `.env` (`SERTOR_MEMORY`/`_LIST_LIMIT`/`SERTOR_EPISODIC_*`), hook `memory-capture.ps1` + voce `SessionEnd` negli asset, cenno nel `claude-md-block` | **Recupera il rinvio A-009 di FEAT-035** (era appeso solo in `specs/035-…`, mai promosso — primo frutto della regola di promozione out-of-scope). Owner installer = epica `sertor-cli`; si combina con la distribuzione multi-assistente (FEAT-008) | 👍 **debito di completamento, da decomporre** (utente, 2026-06-14) |
| **Timeout espliciti su embed/query (server MCP e adapter)** | L'hang della prima query MCP è stato diagnosticato e **risolto** (causa vera: init pigro di Chroma nella prima tool call parcheggiava il task su Windows → warm-up eager in `main()`, **hotfix PR #23**, vedi [[mcp-server]]); i timeout generici restano una rifinitura di robustezza | Timeout configurabile in `Settings` + eccezione di dominio | 💡 idea ridimensionata (hang risolto 2026-06-12) |
| **Igiene radice ospite** (feature `sertor-cli`, asse **DOVE**) | Radice ospite ordinata: `wiki.config.toml`→`wiki/`, `.sertor/` unica sede del runtime, meccanismo `--mcp-scope project\|local`, residenti inevitabili a root documentati | Consegnata: `specs/016`, PR #26 (auto-discovery CLI + `MCP_REGISTER` + fix Sertor one-shot). | ✅ **su master (2026-06-13)** |
| **Leak minori recuperati dall'audit out-of-scope (2026-06-14)** | Voci rinviate rimaste appese nelle spec, ora tracciate per non perderle (regola «out-of-scope si promuovono», CLAUDE.md) | (1) **Installer lifecycle** upgrade+uninstall → FEAT-008 `sertor-cli`; (2) **ingestione estesa** repo remoti URL + formati non-testo → FEAT-010 `sertor-core`; (3) **GraphRAG "alla Microsoft"** (knowledge-graph LLM, da `specs/014`) — contingente alla decisione LLM-nel-core; (4) **parità MCP** per `memory show/list` (da `specs/036`); (5) **export CSV/MD** dei report osservabilità (da `specs/023`, distinto dall'export OTel già FEAT-005) | 💡 **idee tracciate, da prioritizzare** (audit 2026-06-14) |
| 🐞 **Residuo uninstall: `.claude/` orfano vuoto** (lifecycle installer, `sertor-cli`) | `sertor uninstall rag --assistant claude` lascia un `.claude/` orfano (`settings.json`=`{}` + `hooks/` vuota) su un host che non aveva `.claude/`. Stessa classe del bug chiuso da **PR #77** (guscio vuoto), ma sul file `.claude/settings.json` CONDIVISO (che PR #77 preserva di proposito) | Emerso dalla **verifica empirica su Spike** (2026-06-18, test install Claude/Copilot dell'unificazione venv). Fix gemello di PR #77: estendere `delete_if_empty` al `settings.json` condiviso quando è vuoto E creato da Sertor (distinguere user-created è il nodo). Casa: lifecycle `sertor-cli` | 👍 **bug tracciato, da fixare** (2026-06-18) |
| **Collaborazione multiutente / enterprise** (asse **CHI** — ora EPICA propria) | Non è un tema di installer: è **workflow** (cosa/quando condividere, collaborazione su RAG+wiki, ownership, governance leggera) | **Epica aperta** `requirements/multiutente/epic.md` (6 feature M01..M06, 7 domande aperte DA-M-a..g). La bozza `installer-multiutente` ne è la fetta-installer (FEAT-M01, congelata). **Da affrontare in seguito**, quando il caso d'uso team è concreto. | 📋 **epica aperta, differita** (utente, 2026-06-12) |

---

## Questioni aperte (tenute così, per ora)

- **Licenza di Sertor (DA APRIRE):** Sertor **non è ancora licenziato**. Scelta da prendere — incide su
  riusabilità (la mission è "framework installabile ovunque"), su cosa possiamo bundlare e su come gli
  ospiti possono usarlo. Candidati tipici: **MIT/Apache-2.0** (permissive, massima adozione — coerenti
  con local-first e con l'idea di strumento riusabile), vs copyleft (GPL/AGPL, più protettive ma
  attritive per l'adozione). Nota emersa il 2026-06-14 valutando l'integrazione con Langfuse (MIT
  core)/Phoenix (Elastic License 2.0, non-OSI)/Grafana (AGPLv3): integrarli **via OpenTelemetry** non
  contagia Sertor; il vincolo morderebbe solo se li *incorporassimo*. La scelta della licenza propria
  resta indipendente e da fare prima di una distribuzione pubblica (PyPI).
- **Soglie di pertinenza**: non fissate a priori; da misurare su ground-truth reale (DA-003 / DA-1·3).
- **Numerazione**: epica FEAT-NNN ≠ `specs/NNN` (vedi banner sopra) — non riconciliarle a forza, documentare.
- **Server MCP & nuovo indice**: dopo ogni feature che cambia il codice del server serve un **riavvio** del subprocess MCP per servirlo.

## Come mantenere questa pagina

- Brainstorming → a mano in *Nuove funzionalità da discutere*.
- Avanzamento feature → aggiorna *Mappa delle feature & stato reale* (o lo fa il `wiki-curator` quando registra).
- Idea matura → backlog epica + `/requirements` → `/speckit-*`.

## Riferimenti

Sintesi per feature: [[hybrid-retrieval]] · [[implementazione-nucleo-retrieval]] · [[motore-baseline-feat002]] ·
[[nucleo-wiki-deterministico-feat003d]] · [[server-mcp-produzione-feat-mcp]] · [[meccanica-log-feat008]] ·
[[store-backend-disaccoppiato-feat009]] · [[spec-010-query-congiunta-e-upsert-index]] ·
[[sertor-rag-cli]] · [[architettura-wiki-llm]] · [[constitution]] · [[corpus-index-naming]].
