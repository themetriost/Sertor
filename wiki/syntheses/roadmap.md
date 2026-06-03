---
title: Roadmap & Piano di prodotto (pagina viva)
type: synthesis
tags: [roadmap, piano, stato, produzione, backlog]
created: 2026-06-03
updated: 2026-06-03
sources: ["requirements/sertor-core/epic.md", "requirements/sertor-cli/epic.md", ".specify/memory/constitution.md"]
---

# Roadmap & Piano — Sertor

> **Pagina viva.** Tienila aperta come quadro d'insieme. Si aggiorna in due modi:
> a **mano** (soprattutto la sezione *Nuove funzionalità da discutere*, per il brainstorming) e in
> automatico quando una feature avanza nella pipeline SpecKit. Quando un'idea matura, passa dal
> brainstorming al **flusso requisiti → spec → plan → tasks → implement**.

## Visione

Portare capacità **RAG** (ricerca semantica su codice + documentazione) su **qualunque repository**,
in modo riproducibile e production-grade. **Una sola verità interrogabile**: sorgenti (il *come*) e
documentazione/wiki (il *perché*) coesistono nello stesso corpus; la documentazione nuova vive
**accanto ai sorgenti** tramite l'LLM Wiki. Local-first ↔ cloud via configurazione; riusabile come
libreria, esposto via **CLI** e **MCP**.

## Stato in breve (al 2026-06-03)

- **MVP del core completo e in `master`**: nucleo + motore baseline + skill LLM Wiki.
- Esposto via **CLI `sertor`** e via **server MCP** (sul motore nuovo).
- **Dogfooding di produzione** attivo: Sertor indicizza sé stesso (Azure embeddings + Chroma locale).
- Qualità: **108 test verdi (+2 xfail)**, **9 PR** mergiate, **Costituzione 9/9** su ogni feature.

## Mappa delle feature & stato

Legenda: ✅ in produzione (master) · 🔜 prossima (Should) · 💤 dopo (Could/Won't ora) · 🧪 in corso

### Epica `sertor-core` (primaria — la libreria è il prodotto)

| Feature | Pri | Stato |
|---|---|---|
| FEAT-001 Nucleo di retrieval (ingestione, chunking, embeddings, vector store, facade) | Must | ✅ |
| FEAT-002 Motore RAG vettoriale (baseline) | Must | ✅ |
| FEAT-003 Skill LLM Wiki (crea + indicizza) | Must | ✅ |
| FEAT-004 RAG ibrido + reranking | Should | 🔜 da decomporre |
| FEAT-005 RAG a grafo / GraphRAG | Should | 🔜 da decomporre *(riporta i tool `find_symbol`/`who_calls`/… nel MCP)* |
| FEAT-006 RAG agentico (multi-step) | Should | 🔜 da decomporre |
| FEAT-007 Skill: mantenere il wiki (lint/indice/distill) | Should (prioritizzata) | 🧪 in lavorazione — decomposta |
| FEAT-008 Arricchimento bidirezionale Wiki↔RAG | Could | 💤 da decomporre |
| FEAT-009 Refresh incrementale dell'indice | Could | 💤 da decomporre |

### Epica `sertor-cli` (secondaria — il veicolo)

| Feature | Stato |
|---|---|
| CLI "esecuzione" (entry-point `sertor` + `index`/`search`/`wiki index` + osservabilità) | ✅ |
| FEAT-CLI-002 installazione selettiva su altri repo | 🔜 da decomporre |
| FEAT-CLI-003 wizard di configurazione (completo) | 🧪 parziale (lettura config fatta) |
| FEAT-CLI-005 setup governance | 💤 da decomporre |
| FEAT-CLI-006 distribuzione PyPI | 💤 Won't (per ora) |

### Integrazioni / operazioni

| Voce | Stato |
|---|---|
| Server MCP `sertor-rag` sul motore nuovo (search_code/docs/combined) | ✅ |
| Dogfooding di produzione (corpus `production`, Azure) | ✅ |
| Costituzione v1.0.0 + pipeline SpecKit | ✅ |

## Roadmap per fasi

- **✅ Fatto (in produzione):** Nucleo · Baseline · Skill Wiki · CLI `sertor` · Server MCP · Dogfooding Azure.
- **🔜 Prossimo (Should):** RAG ibrido+reranking (FEAT-004) · GraphRAG (FEAT-005) · RAG agentico (FEAT-006) · Manutenzione wiki (FEAT-007) · CLI install selettivo.
- **💤 Dopo (Could / Won't ora):** Arricchimento Wiki↔RAG (FEAT-008) · Refresh incrementale (FEAT-009) · CLI wizard config · Distribuzione PyPI.

---

## 🧭 Nuove funzionalità da discutere (sezione a mano)

> Aggiungi qui le idee **prima** che diventino feature formali. Quando un'idea è condivisa e matura,
> spostala nel backlog dell'epica (`requirements/<epica>/epic.md`) e avvia il flusso SpecKit.
> Stati proposti: 💡 idea · 🗣️ in discussione · 👍 approvata (→ decomporre) · ❌ scartata.

| Idea | Valore / perché | Note / vincoli | Stato |
|------|-----------------|----------------|-------|
| Indicizzare il **prototipo** in un corpus separato (`SERTOR_CORPUS=prototype`) | Interrogare prototipo e produzione distintamente col motore nuovo | Riusa CLI; nessun codice nuovo | 💡 idea |
| **Misurare la pertinenza** (chiudere gli `xfail`) con un ground-truth reale | Trasforma "funziona" in "misurato" (Principio V); confronto provider | Serve un set query→file atteso; baseline = prototipo | 🗣️ in discussione |
| Promuovere **PowerShell / T-SQL / PL-SQL** da fallback a chunking sintattico | Qualità di chunking migliore per questi linguaggi | Validare i node-type tree-sitter; incrementale (REQ-011) | 💡 idea |
| Vorrei che la parte di CLI fosse disponibile anche tramite MCP o skill, una volta installato Sertor devo avere la possibilita' di indicizzare/configurare etc etc anche attraverso una agente e anche essendo guidato nelle scelte, una sorta di wizard agentico  | Alto | note | da discutere | | | |
| <!-- aggiungi una riga: idea | valore | note | stato --> | | | |

---

## Questioni aperte (decise di tenere così, per ora)

- **Soglie di pertinenza**: non fissate a priori; da misurare su ground-truth reale (DA-003 / DA-1·3).
- **PowerShell/SQL**: oggi chunking dimensionale di fallback (rischio R-N2 mitigato); sintattico = incremento.

## Come mantenere questa pagina

- Brainstorming/idee → a mano nella sezione *Nuove funzionalità da discutere*.
- Avanzamento feature → aggiorna la tabella *Mappa delle feature & stato* (o lascia che lo faccia il
  `wiki-keeper` quando registra un'attività).
- Idea matura → backlog epica + `/requirements` (decomposizione EARS) → `/speckit-*` (spec→plan→tasks→implement).

## Riferimenti

Sintesi per feature: [[implementazione-nucleo-retrieval]] · [[motore-baseline-feat002]] ·
[[skill-wiki-feat003]] · [[cli-esecuzione-feat004]] · [[piano-nucleo-retrieval]] ·
[[decomposizione-must-core]] · [[costituzione-v1]] · [[ruolo-wiki-da-w1]] ·
esperimento: [[dogfooding-produzione-cli]].
