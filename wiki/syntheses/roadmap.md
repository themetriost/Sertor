---
title: Roadmap & stato di prodotto (pagina viva)
type: synthesis
tags: [roadmap, piano, stato, produzione, backlog]
created: 2026-06-03
updated: 2026-06-11 (ripresa CLI: DA-8 split installer/esecuzione — `sertor install <capacità>` vs console-script core `sertor-rag`; requirements `esecuzione` rinfrescati, prossimo passo SpecKit)
sources: ["requirements/sertor-core/epic.md", "requirements/sertor-cli/epic.md", "specs/**", ".specify/memory/constitution.md"]
---

# Roadmap & stato — Sertor

> **Pagina viva.** Quadro d'insieme dello stato reale. Si aggiorna a mano (sezione *Nuove funzionalità da
> discutere*) e quando una feature avanza nella pipeline SpecKit. Quando un'idea matura: backlog epica →
> `requirements → spec → plan → tasks → implement`.

<!-- EXEC:START -->
## ⚡ Executive summary (stato al 2026-06-11)

### 📊 Roadmap a colpo d'occhio

| Capacità | Pri | Stato |
|---|---|---|
| Nucleo retrieval (FEAT-001) | Must | ✅ master |
| Motore baseline (FEAT-002) | Must | ✅ master |
| Wiki LLM (FEAT-003) | Must | ✅ **completata 2026-06-10** (D 100% + N chiuse; N5/N9 → FEAT-007) |
| Server MCP (FEAT-MCP) | Should | ✅ master |
| RAG ibrido + reranking (FEAT-004) | Should | 📋 da decomporre |
| GraphRAG (FEAT-005) | Should | 📋 da decomporre |
| RAG agentico (FEAT-006) | Should | 📋 da decomporre |
| Manutenzione wiki (FEAT-007) | Should | 📋 da decomporre |
| CLI — feature `esecuzione` (`sertor-rag`) | — | 🔄 **in progress** (requirements rinfrescati 2026-06-11, prossimo: SpecKit) |
| CLI — installer (`sertor install <capacità>`) | — | 📋 da elicitare (DA-8; contenuto `install wiki` confermato) |

*Legenda:* ✅ su master · 🧪 operativo, consolidamento aperto · 📋 pianificato · 💀 ramo morto (non su master).

### 🔄 IN PROGRESS (dettaglio)

- **CLI — feature `esecuzione` (`sertor-rag index/search`)** — *cosa:* CLI di esecuzione RAG come
  console-script del core (DA-8: `sertor` resta riservato all'installer `sertor install <capacità>`).
  *Dove:* `requirements/sertor-cli/esecuzione/requirements.md` (rev. 2026-06-11: REQ-001→`sertor-rag`,
  gruppo D rimosso, REQ-041 precisato) + epica `requirements/sertor-cli/epic.md` (DA-8). *Prossimo
  passo:* avviare il flusso SpecKit (`/speckit-specify` → branch + PR, policy produzione). *Blocchi:*
  nessuno.

### 📋 PLANNED (per priorità)
- **FEAT-004 ibrido+reranking** — candidato naturale: migliora la qualità di `search_code` (debolezza
  nota) e la ricetta è già in casa (BM25+vector fusi con RRF, ingerita da [[llm-wiki-v2-agentmemory]]).
- **FEAT-005 GraphRAG · FEAT-006 agentico** — gli altri due motori, da decomporre.
- **FEAT-007 manutenzione wiki** — parte con dote ricca: probe di freschezza (ex N5), helper
  `move`-con-link (ex N9), op *reconcile* delle obsolescenze (idea utente 2026-06-10), seed
  `structure init` localizzato.
- **CLI — installer `sertor install <capacità>`** (DA-8, da elicitare con `/requirements`): primo
  taglio `sertor install wiki` — skill wiki + step ritual nel CLAUDE.md ospite + `wiki.config.toml` +
  `structure init` + tooling di indicizzazione configurato, mai indicizzazione automatica.
- **Misurare la pertinenza** (chiudere i 2 xfail con ground-truth reale).

### ✅ DONE (su `master`, le rilevanti)

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

## Stato in breve (al 2026-06-10)

- **Su `master`** (l'unico asset reale): nucleo di retrieval + motore baseline + **wiki** (metà
  deterministica `wiki_tools` **in codice** + metà giudizio **come skills/playbook** in `.claude/`) +
  **server MCP** + **query congiunta multi-collezione** e `upsert-index` in CLI (feature 010), più i
  lavori abilitanti (meccanica log, decoupling store/embeddings, regola di re-index).
- **Dogfooding di produzione VIVO**: corpus `sertor` (207 doc / 1778 chunk, **wiki incluso** come
  documentazione — modello a corpus unico, D-21), embeddings Azure `text-embedding-3-large` + Chroma
  locale in `.index-sertor/`. Servito dal server MCP `sertor-rag`. La collezione `wiki__*` resta come
  capacità esercitabile (rag-sync), senza consumatori.
- **Rami abbandonati (NON su `master` → non contano come asset):** la **CLI `sertor`** (`specs/004` — su
  master ci sono solo i *requirements*, zero codice `sertor_cli`) e i tentativi *in codice* di FEAT-003-N
  (`specs/003`/`005`, superati dall'approccio a skills). Oggi il prodotto è usabile come **libreria + MCP**,
  **non** come CLI.
- Qualità: **159 test verdi** (+2 xfail di misura), ruff pulito; ogni feature su master passata col
  **Constitution Check** (costituzione v1.1.0, 10 principi).

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
| FEAT-004 | Motore RAG **ibrido + reranking** | Should | 🔜 da decomporre | — |
| FEAT-005 | Motore RAG a **grafo / GraphRAG** *(riporta `find_symbol`/`who_calls` nel MCP)* | Should | 🔜 da decomporre | — |
| FEAT-006 | Motore RAG **agentico** (multi-step, query planning) | Should | 🔜 da decomporre | — |
| FEAT-007 | Skill: **mantenere il wiki vivo** (spider/lint) *(2026-06-10: assorbe da FEAT-003-N la N5 lint semantico — residuo: probe deterministici di freschezza — e la N9 lint organizzativo/reorg)* | Should | 🔜 da decomporre | — |
| FEAT-008 | Arricchimento bidirezionale **Wiki↔RAG** | Could | 💤 da decomporre | — |
| FEAT-009 | **Refresh incrementale** dell'indice (solo file cambiati) | Could | 💤 da decomporre | — |

### Epica `sertor-cli` (il veicolo) — **non consegnata**, ripresa il 2026-06-11

**DA-8 (2026-06-11) — split installer/esecuzione:** `sertor` = solo **install** (`sertor install
<capacità>`); l'**esecuzione** vive nei console-script del core (`sertor-rag` nuovo, `sertor-wiki-tools`
già su master).

| Feature | Stato | Dove |
|---|---|---|
| CLI "esecuzione" (**`sertor-rag`** + `index`/`search`) | 🔄 **in progress**: requirements rinfrescati (rev. 2026-06-11), prossimo passo SpecKit; il vecchio codice `sertor_cli` (`specs/004`) resta ramo morto | requirements ✅ · codice da fare |
| Installer `sertor install <capacità>` (primo taglio: `install wiki`, contenuto in DA-8) | 📋 da elicitare (`/requirements`) | epica §9 DA-8 |
| Wizard config · setup governance · PyPI | 💤 da decomporre/Won't ora | — |

> Oggi il prodotto si usa come **libreria** (`import sertor_core`) e via **server MCP**. Il vecchio
> ramo CLI (`specs/004`) non si recupera: la feature `esecuzione` si reimplementa su master come
> `sertor-rag`.

## Lavori abilitanti già mergiati (non sono FEAT d'epica)

| Spec | Cosa | Esito |
|---|---|---|
| `specs/008` | Meccanica del log del wiki (rotazione giornaliera + `append-log` curato + `migrate`) | ✅ PR #18 |
| `specs/009` | **Decoupling store ↔ provider di embeddings** (`SERTOR_STORE_BACKEND`) + `AzureEmbedder` v1 | ✅ PR #19 → ha abilitato l'indice dogfood `sertor` |

## Roadmap per fasi

- **✅ Fatto (master):** Nucleo · Baseline · Wiki (deterministico `wiki_tools` + operazioni LLM come skills) · Server MCP · Decoupling store · Indice dogfood `sertor` (vivo via MCP).
- **💀 NON su master (rami abbandonati — non contano):** CLI `sertor` (`specs/004`) · tentativi *in codice* di FEAT-003-N (`specs/003`/`005`, superati dalle skills). Da rifare su master se servono.
- **🔜 Prossimo (Should):** RAG ibrido+reranking (FEAT-004) · GraphRAG (FEAT-005) · RAG agentico (FEAT-006) · Manutenzione wiki (FEAT-007).
- **💤 Dopo (Could):** Arricchimento Wiki↔RAG (FEAT-008) · Refresh incrementale indice (FEAT-009).

---

## 🧭 Nuove funzionalità da discutere (sezione a mano)

> Idee **prima** che diventino feature formali. Stati: 💡 idea · 🗣️ in discussione · 👍 approvata (→ decomporre) · ❌ scartata.

| Idea | Valore / perché | Note / vincoli | Stato |
|------|-----------------|----------------|-------|
| **Misurare la pertinenza** (chiudere gli `xfail`) con ground-truth reale | Trasforma "funziona" in "misurato" (Principio V); confronto provider | Serve set query→file atteso; baseline = prototipo | 🗣️ in discussione |
| Migliorare la **qualità `search_code`** (oggi debole su query architetturali) | Il retrieval di codice è il caso d'uso primario | Naturale candidato per FEAT-004 (ibrido) / FEAT-005 (grafo) | 🗣️ in discussione |
| Promuovere **PowerShell / T-SQL / PL-SQL** da fallback a chunking sintattico | Qualità di chunking per questi linguaggi | Validare node-type tree-sitter; incrementale | 💡 idea |
| **Logging come strategia runtime** (osservabilità porta+adapter scelta a runtime) | Oggi la CLI non instrada i log da nessuna parte | Refactor deterministico → SpecKit | 💡 idea |
| **Seed di `structure init` localizzato** (usare `language`/`[strings]` della config) | Finding dell'esercizio N3 su spec-kit: seed in italiano su ospite `en` | Fix D piccolo in `wiki_tools`; candidato FEAT-007 | 💡 idea |

---

## Questioni aperte (tenute così, per ora)

- **Soglie di pertinenza**: non fissate a priori; da misurare su ground-truth reale (DA-003 / DA-1·3).
- **Numerazione**: epica FEAT-NNN ≠ `specs/NNN` (vedi banner sopra) — non riconciliarle a forza, documentare.
- **Server MCP & nuovo indice**: dopo ogni feature che cambia il codice del server serve un **riavvio** del subprocess MCP per servirlo.

## Come mantenere questa pagina

- Brainstorming → a mano in *Nuove funzionalità da discutere*.
- Avanzamento feature → aggiorna *Mappa delle feature & stato reale* (o lo fa il `wiki-curator` quando registra).
- Idea matura → backlog epica + `/requirements` → `/speckit-*`.

## Riferimenti

Sintesi per feature: [[implementazione-nucleo-retrieval]] · [[motore-baseline-feat002]] ·
[[nucleo-wiki-deterministico-feat003d]] · [[server-mcp-produzione-feat-mcp]] · [[meccanica-log-feat008]] ·
[[store-backend-disaccoppiato-feat009]] · [[spec-010-query-congiunta-e-upsert-index]] ·
[[architettura-wiki-llm]] · [[constitution]] · [[corpus-index-naming]].
