---
title: Roadmap & stato di prodotto (pagina viva)
type: synthesis
tags: [roadmap, piano, stato, produzione, backlog]
created: 2026-06-03
updated: 2026-06-14 (hardening Should gruppo C — feature 019 cache embeddings + token nei log — implementata su branch, in attesa di PR) · 2026-06-13 (notte: FEAT-018 hardening retrieval Must ✅ su master, PR #32 — retry embedder + soglia/low_confidence; hardening resta IN PROGRESS perché Should/Could aperti) · 2026-06-13 (sera: + idea «Second brain cross-progetto»/Meta-Sertor → [[second-brain-cross-progetto]], da espandere · giornata: FEAT-006 ✅ composita · igiene radice host PR #26 · tema lingua completo PR #27/#28/#29) · 2026-06-12 (TRIPLA: PR #23/#24/#25)
sources: ["requirements/sertor-core/epic.md", "requirements/sertor-cli/epic.md", "specs/**", ".specify/memory/constitution.md"]
---

# Roadmap & stato — Sertor

> **Pagina viva.** Quadro d'insieme dello stato reale. Si aggiorna a mano (sezione *Nuove funzionalità da
> discutere*) e quando una feature avanza nella pipeline SpecKit. Quando un'idea matura: backlog epica →
> `requirements → spec → plan → tasks → implement`.

<!-- EXEC:START -->
## ⚡ Executive summary (stato al 2026-06-13)

### 📊 Roadmap a colpo d'occhio

| Capacità | Pri | Stato |
|---|---|---|
| Nucleo retrieval (FEAT-001) | Must | ✅ master |
| Motore baseline (FEAT-002) | Must | ✅ master |
| Wiki LLM (FEAT-003) | Must | ✅ **completata 2026-06-10** (D 100% + N chiuse; N5/N9 → FEAT-007) |
| Server MCP (FEAT-MCP) | Should | ✅ master |
| RAG ibrido + reranking (FEAT-004) | Should | ✅ **master (2026-06-12, PR #24)** — motore di default |
| GraphRAG / code-graph (FEAT-005) | Should | ✅ **master (2026-06-12, PR #25)** — i 4 tool MCP tornati |
| RAG agentico (FEAT-006) | Should | ✅ **soddisfatta in forma composita (2026-06-13)** — il sistema MCP+agente È agentic RAG; agenzia incorporata = dote differita (Could) |
| Manutenzione wiki (FEAT-007) | Should | ✅ **master (2026-06-13, PR #30)** — `move`/`reconcile`/`collect`+status; gruppi A(Won't)/E/F/B/C/D tutti chiusi |
| CLI — feature `esecuzione` (`sertor-rag`) | — | ✅ **master (2026-06-11, PR #21)** |
| CLI — installer (`sertor install`) | — | ✅ `wiki` (PR #22) + **`rag` su master (2026-06-12)** — validato live su Kaelen; `governance` = stub |
| **Hardening produzione (retrieval)** | — | 🔄 **IN PROGRESS** — Must ✅ su master (PR #32); Should gruppo C (cache embeddings + token log, feature 019) ✅ **su master (PR #33)**; restano i Could in `requirements/sertor-core/hardening-produzione/` |
| Distribuzione multi-assistente: GitHub Copilot (+ Codex Could) | — | 👍 **da decomporre** (decisione utente 2026-06-12) |
| Tema lingua (tutto il prodotto in inglese) | — | ✅ **completato totale (2026-06-13, PR #27/#28/#29/#31)**: codice (72 .py: docstring/commenti/**errori**), test (75 .py: commenti/docstring), documentazione di prodotto (README + `docs/`), asset installer, CLI, seed it/en. Restano IT **per scelta**: `wiki/`, `specs/`, `requirements/`, `CLAUDE.md`, `prototype/` (congelato) |
| Igiene radice ospite (installer, asse DOVE) | — | ✅ **master (2026-06-13, PR #26)** — config in `wiki/` + auto-discovery, `--mcp-scope` |
| **Collaborazione multiutente/enterprise** (asse CHI, workflow) | — | 📋 **EPICA aperta, differita (2026-06-12)** — `requirements/multiutente/epic.md`; da affrontare quando il caso d'uso team è concreto |

*Legenda:* ✅ su master · 🧪 operativo, consolidamento aperto · 📋 pianificato · 💀 ramo morto (non su master).

### 🔄 IN PROGRESS (dettaglio)

- **Osservabilità e pannello di controllo (epica)** — *cosa:* rendere Sertor trasparente su sé stesso
  (log/costo/cache/salute corpus) con un pannello TUI e i numeri persistiti. *Dove:*
  `requirements/osservabilita/` (epica nuova). *Stato:* epica + MVP **interamente a requisiti**
  (F1→F4 decomposte, 76 REQ EARS); decisioni di prodotto fissate (privacy-by-default a strati, stima €
  a Should). *In corso:* **SpecKit su F1 «strato di osservabilità persistente»** — branch
  `020-osservabilita-persistente`, **F1 IMPLEMENTATA sul branch** (SpecKit completo specify→implement,
  Constitution PASS 10/10, 406 root + 85 packages test verdi, ruff pulito; **non ancora mergiata**):
  cattura via `logging.Handler` (`EventPersistenceHandler`, additivo/non-fatale/redazione gratis), store
  SQLite `observability.sqlite`, 7ª porta `ObservabilityStore`, manopola `SERTOR_OBSERVABILITY` (default
  off), guardia di re-entrancy. *Prossimo passo:* PR di F1 **oppure** decomporre/implementare F2 (consuma
  lo store). *A seguire:* F3→F4. *In parallelo (quando si vuole):*
  decomporre l'epica **memoria conversazioni** (nodo: cattura host-specifica).

### 📋 PLANNED (per priorità)
- **Agenzia RAG incorporata — dote differita (Could)**: la capacità agentic RAG è ✅ **soddisfatta
  in forma composita** (MCP + agente, vedi DONE). Resta opzionale l'**agenzia incorporata nel core**
  (`sertor-rag ask` per umani/script senza assistente, digest MCP per economia di contesto, porta
  `LLMProvider`) — 36 REQ elicitati in `requirements/sertor-core/motore-agentico/` (banner di
  rinvio): si riapre se uno di quei casi d'uso diventa prioritario.
- **Distribuzione multi-assistente (👍 utente, 2026-06-12)** — tutto il consegnato utilizzabile
  anche da **GitHub Copilot** (Must: MCP nei client Copilot + traduzione delle superfici
  agentiche dell'installer con target assistant) e da **Codex** (Could: AGENTS.md + MCP); CLI già
  assistant-agnostic. Nuova FEAT-007 dell'epica CLI; estende il Principio X all'assistente ospite.
- **`sertor install governance`** — l'ultimo taglio dell'installer ancora stub. *(`install rag` ✅ DONE, 2026-06-12.)*
- **Eval comparativa live su provider reale** (REQ-051 con Azure, marker `cloud`) — il confronto
  strict è in CI; la misura col provider forte resta esercizio opzionale.

### ✅ DONE (su `master`, le rilevanti)

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

### Epica `sertor-cli` (il veicolo) — **non consegnata**, ripresa il 2026-06-11

**DA-8 (2026-06-11) — split installer/esecuzione:** `sertor` = solo **install** (`sertor install
<capacità>`); l'**esecuzione** vive nei console-script del core (`sertor-rag` nuovo, `sertor-wiki-tools`
già su master).

| Feature | Stato | Dove |
|---|---|---|
| CLI "esecuzione" (**`sertor-rag`** + `index`/`search`) | ✅ **su master (2026-06-11, PR #21)** — `src/sertor_core/cli/`, SpecKit `specs/011`; il vecchio `specs/004` resta ramo morto superato | requirements ✅ · codice ✅ |
| Installer **`sertor install wiki`** (pacchetto `sertor` distinto, uv workspace) | ✅ **su master (2026-06-11, PR #22)** — `packages/sertor/`, SpecKit `specs/012`; validato live su ospite reale; `install rag`/`governance` stub | requirements ✅ · codice ✅ |
| Localizzazione asset (tema lingua) · wizard config · `install rag`/`governance` · PyPI | 💤 da gestire/decomporre | tema lingua 👍 (2026-06-11) |

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
| **Pannello di controllo (TUI) di osservabilità** | Vedere log, consumo (token/€), #chunk, **hit/miss della cache** e fare report. Sertor già emette log strutturati ricchi ma effimeri | **Epica aperta** `requirements/osservabilita/epic.md` (10 feature MoSCoW, 2 strati: osservabilità persistente nel core + pannello TUI). Fork decisi: **superficie = TUI** (web=Could fase 2), **dati = store SQLite locale + export OTel opzionale**. Assorbe «logging come strategia runtime» e i Could **H9/H10** dell'hardening. MVP = FEAT-001→004 (persisti→aggrega→TUI live→report) **+ stima € (Should, DA-O-g risolta)**. Privacy fissata (DA-O-d): **privacy-by-default a strati** (metriche di default · testo opt-in · semantico opt-in ulteriore). Restano domande di design (cattura "live", retention, innesto su `log_event`) | 👍 **epica aperta, da decomporre** (utente, 2026-06-14) |
| **Memoria conversazioni (terzo livello / episodica, pattern Hermes)** | Archiviare TUTTE le conversazioni come tier grezzo episodico, interrogabile nei casi speciali («ne avevamo già parlato?»); è il tassello mancante sotto il diario del wiki, fonte grezza per la distillazione | **Epica aperta** `requirements/memoria-conversazioni/epic.md` (8 feature MoSCoW). Distinta dall'osservabilità (conoscenza ≠ telemetria), **privacy condivisa** (privacy-by-default, FTS locale, semantico opt-in). MVP = cattura + ricerca episodica locale. **Nodo:** la cattura è host-specifica (Claude Code → harness) → si lega alla distribuzione multi-assistente. Mappa Hermes↔Sertor in epic.md | 👍 **epica aperta, da decomporre, in parallelo** (utente, 2026-06-14) |
| **Second brain cross-progetto** (il «Sertor dei Sertor» / Meta-Sertor) | Conoscenza condivisa e di più alto livello su TUTTI i propri contesti: condividere esperienze/metodologie, scambiarsi skill/agenti, **sintetizzare asset nuovi** da più progetti. Sertor da autore a **giardiniere della flotta** | Sertor ricorsivo (L0/L1/L2); riusa feature 010 (fan-out) + installer + Principio X; nuovo = confine di **promozione** (giudizio) + **verifica/parametrizzazione** asset + trust/decay. Pagina-visione con diagrammi: [[second-brain-cross-progetto]] | 💡 **idea, DA ESPANDERE** (2026-06-13) |
| **Misurare la pertinenza** (chiudere gli `xfail`) con ground-truth reale | Trasforma "funziona" in "misurato" (Principio V); confronto provider | Serve set query→file atteso; baseline = prototipo | 🗣️ in discussione |
| Migliorare la **qualità `search_code`** (oggi debole su query architetturali) | Il retrieval di codice è il caso d'uso primario | Naturale candidato per FEAT-004 (ibrido) / FEAT-005 (grafo) | 🗣️ in discussione |
| Promuovere **PowerShell / T-SQL / PL-SQL** da fallback a chunking sintattico | Qualità di chunking per questi linguaggi | Validare node-type tree-sitter; incrementale | 💡 idea |
| **Logging come strategia runtime** (osservabilità porta+adapter scelta a runtime) | Oggi la CLI non instrada i log da nessuna parte | Refactor deterministico → SpecKit | 💡 idea |
| **Tema lingua** (asset installer in inglese, contenuto in lingua host) | Coerenza dell'esperienza su ospiti non-italiani | **Implementato 2026-06-13** (pass mirato): asset+CLI host-facing in inglese + guardia. Residuo: seed localization it/en (D3) + traduzione graduale delle error-string profonde/docstring | ✅ **fatto (asset); seed = follow-up)** |
| **Distribuzione multi-assistente: GitHub Copilot (+ Codex Could)** | Le capacità non devono dipendere da un solo assistente: MCP nei client Copilot + superfici agentiche tradotte (copilot-instructions/prompt files; Codex: AGENTS.md) | Nuova FEAT-007 epica CLI; distinto da DA-6 (Copilot lì è provider LLM); CLI già assistant-agnostic | 👍 **da decomporre** (utente, 2026-06-12) |
| **Adapter VectorStore per PGVector / MongoDB su Azure** | Ibrido e retrieval su store cloud alternativi ad AI Search (il motore ibrido è già store-agnostico via porte) | Nuovi adapter della porta `VectorStore` (+ eventuale delega ibrida nativa per Atlas Search); feature separata da FEAT-004 | 💡 idea (da DA-2 FEAT-004, 2026-06-11) |
| **Timeout espliciti su embed/query (server MCP e adapter)** | L'hang della prima query MCP è stato diagnosticato e **risolto** (causa vera: init pigro di Chroma nella prima tool call parcheggiava il task su Windows → warm-up eager in `main()`, **hotfix PR #23**, vedi [[mcp-server]]); i timeout generici restano una rifinitura di robustezza | Timeout configurabile in `Settings` + eccezione di dominio | 💡 idea ridimensionata (hang risolto 2026-06-12) |
| **Igiene radice ospite** (feature `sertor-cli`, asse **DOVE**) | Radice ospite ordinata: `wiki.config.toml`→`wiki/`, `.sertor/` unica sede del runtime, meccanismo `--mcp-scope project\|local`, residenti inevitabili a root documentati | Consegnata: `specs/016`, PR #26 (auto-discovery CLI + `MCP_REGISTER` + fix Sertor one-shot). | ✅ **su master (2026-06-13)** |
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
