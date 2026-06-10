---
title: Roadmap & stato di prodotto (pagina viva)
type: synthesis
tags: [roadmap, piano, stato, produzione, backlog]
created: 2026-06-03
updated: 2026-06-10 (FEAT-003-N: N1 e N2 complete — distill generalizzata a tre ingressi, pagina diary-vs-graph; N5+N9 a FEAT-007; restano N3/N4/N6; feature 010 mergiata, PR #20; D-21 corpus unico)
sources: ["requirements/sertor-core/epic.md", "requirements/sertor-cli/epic.md", "specs/**", ".specify/memory/constitution.md"]
---

# Roadmap & stato — Sertor

> **Pagina viva.** Quadro d'insieme dello stato reale. Si aggiorna a mano (sezione *Nuove funzionalità da
> discutere*) e quando una feature avanza nella pipeline SpecKit. Quando un'idea matura: backlog epica →
> `requirements → spec → plan → tasks → implement`.

<!-- EXEC:START -->
## ⚡ Executive summary (stato al 2026-06-10)

### 📊 Roadmap a colpo d'occhio

| Capacità | Pri | Stato |
|---|---|---|
| Nucleo retrieval (FEAT-001) | Must | ✅ master |
| Motore baseline (FEAT-002) | Must | ✅ master |
| Wiki LLM (FEAT-003) | Must | 🧪 operativo · pezzi D chiusi (feature 010) · restano operazioni N |
| Server MCP (FEAT-MCP) | Should | ✅ master |
| RAG ibrido + reranking (FEAT-004) | Should | 📋 da decomporre |
| GraphRAG (FEAT-005) | Should | 📋 da decomporre |
| RAG agentico (FEAT-006) | Should | 📋 da decomporre |
| Manutenzione wiki (FEAT-007) | Should | 📋 da decomporre |
| CLI `sertor` | — | 💀 solo requirements (ramo morto) |

*Legenda:* ✅ su master · 🧪 operativo, consolidamento aperto · 📋 pianificato · 💀 ramo morto (non su master).

### 🔄 IN PROGRESS (dettaglio)

- *(nessuna voce in corso — scegliere il prossimo PLANNED)*. **Coda residua di sessione (2026-06-10):**
  riavviare il **server MCP** (nuova sessione: il processo live gira col codice pre-feature-010). La
  questione duplicati è **risolta con D-21** (modello a corpus unico: il wiki sta *dentro* il corpus
  primario by design, `SERTOR_EXTRA_CORPORA` rimossa; il fan-out resta per ospiti con corpora disgiunti).

### 📋 PLANNED (per priorità)
- **Wiki FEAT-003, operazioni-giudizio N:** N3 (generazione dal repo) · N4 (ingest → `sources/`) ·
  N6 (verità/autorità/obsolescenza). *(N2 chiusa il 2026-06-10 per generalizzazione di `distill`.)*
- **Nuovi motori RAG:** FEAT-004 ibrido+reranking · FEAT-005 GraphRAG · FEAT-006 agentico · FEAT-007 manutenzione wiki.
- **CLI `sertor`** (epica `sertor-cli`, da reimplementare su master) — **include il pezzo (2) `sertor wiki init`**:
  la capacità `init_structure` esiste già in `wiki_tools`, manca solo l'esposizione top-level → naturale dentro la
  rinascita della CLI · misurare la pertinenza (xfail).

### ✅ DONE (su `master`, le rilevanti)

- Nucleo retrieval (FEAT-001) · motore baseline (FEAT-002) · server MCP (FEAT-MCP).
- Wiki LLM (FEAT-003) operativo: nucleo deterministico `wiki_tools` + operazioni-giudizio come skills/playbook;
  `generate-from-diff` (N8), trigger manuale `/wiki` (D-19), gate eliminato (D-20), cartelle-input rimosse (D-18).
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
| FEAT-003 | Skill: creare/indicizzare l'LLM Wiki | Must | 🧪 operativo (D+N su master); scope snellito 2026-06-09 (D-18/19/20; N8 completa). **Pezzi codice D chiusi** (feature 010, `specs/010`, PR #20: query congiunta + `upsert-index` CLI — [[spec-010-query-congiunta-e-upsert-index]]). Restano le operazioni N3/N4/N6 (N2 chiusa 2026-06-10: `distill` generalizzata al brief di conversazione intera) | vedi sotto |
| — FEAT-003-D | …nucleo **deterministico** (`wiki_tools` + `wiki.config.toml`) | Must | ✅ | `specs/006` (PR #13), `src/sertor_core/wiki_tools` |
| — FEAT-003-N | …operazioni **assistite da LLM** (record/distill/lint/ingest) | Must | ✅ come **skills/playbook** (giudizio ≠ codice) | `.claude/skills/wiki-author`, `/wiki`, `wiki-curator` |
| FEAT-MCP | Server MCP di produzione (`sertor_mcp`, superficie su `build_facade`) | Should | ✅ | `specs/007` (PR #15) |
| FEAT-004 | Motore RAG **ibrido + reranking** | Should | 🔜 da decomporre | — |
| FEAT-005 | Motore RAG a **grafo / GraphRAG** *(riporta `find_symbol`/`who_calls` nel MCP)* | Should | 🔜 da decomporre | — |
| FEAT-006 | Motore RAG **agentico** (multi-step, query planning) | Should | 🔜 da decomporre | — |
| FEAT-007 | Skill: **mantenere il wiki vivo** (spider/lint) *(2026-06-10: assorbe da FEAT-003-N la N5 lint semantico — residuo: probe deterministici di freschezza — e la N9 lint organizzativo/reorg)* | Should | 🔜 da decomporre | — |
| FEAT-008 | Arricchimento bidirezionale **Wiki↔RAG** | Could | 💤 da decomporre | — |
| FEAT-009 | **Refresh incrementale** dell'indice (solo file cambiati) | Could | 💤 da decomporre | — |

### Epica `sertor-cli` (il veicolo) — **non consegnata**

| Feature | Stato | Dove |
|---|---|---|
| CLI "esecuzione" (`sertor` + `index`/`search`/`wiki index`) | 💀 **non su master**: requirements scritti, codice `sertor_cli` su ramo abbandonato | requirements ✅ · codice ✗ (`specs/004`) |
| Install selettivo su altri repo · wizard config · setup governance · PyPI | 💤 da decomporre/Won't ora | — |

> Oggi il prodotto si usa come **libreria** (`import sertor_core`) e via **server MCP**. La CLI `sertor`
> è solo *requirements*; se la si vuole, va **reimplementata su master** (il ramo vecchio non si recupera).

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
