---
title: Requisito e2e dell'LLM Wiki (feature llm-wiki, FEAT-010)
type: synthesis
tags: [wiki, llm-wiki, requisiti, feat-010, karpathy, consolidamento]
created: 2026-06-04
updated: 2026-06-04
sources: ["requirements/sertor-core/llm-wiki/requirements.md", "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"]
---

# Requisito e2e dell'LLM Wiki — Sertor (FEAT-010)

**Stato**: ✅ READY — approvato per il design (iterazione 13, 13 decisioni risolte).

**Relazione con il lavoro esistente**: **consolida e supersede FEAT-003** creazione+indicizzazione; ne **assorbe** struttura/record/distill/idempotenza (invariati) e **override** esplicito su ingest/sources e indicizzazione. FEAT-003 è storico; `llm-wiki` è il riferimento canonico.

---

## Visione

Portare capacità RAG su **qualunque repository** in modo riproducibile, con **una sola verità interrogabile**: i sorgenti (il *come*) e la documentazione/wiki (il *perché*) coesistono nello stesso corpus. La documentazione nuova vive **accanto ai sorgenti** tramite l'**LLM Wiki end-to-end**: dalla produzione (manuale e automatica) alla manutenzione, all'indicizzazione, fino all'interrogazione. Il **codice è opzionale** — LLM Wiki + RAG funzionano anche per **progetti senza codice**.

---

## Il modello di riferimento: LLM Wiki di Karpathy

**Fonte**: gist *[karpathy/llm-wiki.md](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)* (4 apr 2026).

**Idea centrale**: anziché ri-scoprire conoscenza a ogni query, l'LLM **costruisce e mantiene un wiki persistente** — file `.md` interconnessi che **stanno tra l'utente e le fonti grezze**. La conoscenza è compilata una volta e tenuta aggiornata: cross-reference e contraddizioni sono già stati segnalati.

**Tre livelli**:
1. **Fonti grezze (raw)** — documenti immutabili (articoli, paper, codice). L'LLM le **legge ma non modifica**.
2. **Il wiki** — cartella di `.md` di proprietà dell'LLM (le scrive e mantiene).
3. **Lo schema** — configurazione (es. `CLAUDE.md`) che definisce struttura, convenzioni, workflow.

**File chiave**:
- `index.md` — catalogo globale (link + summary per pagina).
- `log.md` — registro append-only (`## [YYYY-MM-DD] operazione | titolo`).
- **Pagine** — `.md` con wikilink `[[...]]`, frontmatter (tag, date, conteggio fonti).

**Operazioni**:
- **Ingest** — l'utente mette una fonte, l'LLM la processa: legge, scrive pagina-sommario, **aggiorna index**, pagine collegate (potenzialmente 10–15 pagine toccate), appende log.
- **Query** — l'LLM cerca via index, sintetizza con citazioni; risposte valide → archiviate come nuove pagine (no dispersione chat).
- **Lint** — health-check: contraddizioni, claim superate, pagine orfane, cross-reference mancanti.

**Principi**: immutabilità raw · separazione ruoli (umano = sourcing/domande; LLM = lavoro ingrato: riassumere, cross-ref, archiviare) · manutenzione a costo ~zero · niente abbandono · pagine self-contained.

---

## Mappatura: Karpathy ↔ Sertor

| Aspetto | Karpathy | Sertor | Note |
|---------|----------|--------|------|
| **Convenzioni** | index.md + log.md, frontmatter, wikilink | Identiche | ✓ Allineate |
| **Operazioni** | create / ingest / query / lint | Primitive [[skill-wiki-feat003]]; mancava orchestrazione agentica | ◐ Parziale (D-2 la colma) |
| **Una sola verità** | Wiki separato dalle fonti | Wiki + codice insieme, **collezioni separate, query congiunta** (D-3) | ⚠️ Estensione |
| **Source of truth** | Raw esterno unico | **Stratificata**: codice/test → comportamento; discussioni/SpecKit/`manual_edited/` → perché (D-4) | ⚠️ Estensione |
| **Superficie** | Obsidian (navigazione umana) | RAG / CLI / MCP (programmatica); Obsidian ancora valida | ⚠️ Estensione (D-13) |
| **Esecuzione** | LLM scrive a mano | Skill agentica orchesta FEAT-003, invocata al commit dal configuration-manager (D-2, D-8) | ⚠️ Estensione |
| **Prerequisito codice** | Sì, progetti sorgenti | **No** — wiki+RAG per progetti senza codice (D-9) | ⚠️ Estensione |

---

## Decisioni consolidate (17 totali)

### Struttura e input (D-1, D-6)

- **D-1** — `wiki/manual_edited/`: file Markdown scritti dall'umano, intoccabili dall'automazione (letti come fonte/contesto, indicizzati separatamente per poi compilare pagine derive). Contenuto compilato in pagine wiki derivate, file sorgente resta immutato (analogo raw immutabile di Karpathy).
  
- **D-6** — **Modello a due classi**: 
  - **Input** (LLM legge, non scrive): codice · test · SpecKit · log discussioni · `manual_edited/` (versionato) · **`ingested_sources/`** (non versionato, ex `sources/`, new role).
  - **Wiki generato** (LLM scrive): `concepts/` · `tech/` · `experiments/` · `syntheses/` · `index.md` · `log.md`.

### Generazione e indicizzazione (D-3, D-5, D-7)

- **D-3** — **Due momenti distinti**:
  - **(a) Generazione** — modello Karpathy (linguaggio naturale, concetti linkati, incrementale), da insieme di fonti-input configurabile.
  - **(b) Indicizzazione/retrieval** — RAG su wiki generato + codice (collezioni separate, query congiunta, peso paritario nel momento di query).
  
- **D-5** — **Refresh git-driven**: al commit, wiki si aggiorna elaborando changeset dall'ultimo commit (watermark). Git è prerequisito. Fonti versionate (codice, test, SpecKit, log, `manual_edited/`) → refresh al commit; `ingested_sources/` non versionato → trigger manuale.

- **D-7** — **Retrieval puro Karpathy**: RAG indicizza **solo** wiki generato + codice. Cartelle input (`manual_edited/`, `ingested_sources/`) **NON** indicizzate (interroghi il compilato, non il raw).

### Autorità e conflitti (D-4)

- **D-4** — **Verità stratificata**:
  - Autorità su **comportamento** → codice/test.
  - Autorità su **perché** → discussioni/SpecKit/`manual_edited/`.
  - Conflitti su `manual_edited/` → human-in-the-loop (segnala, chiede all'utente).
  - Obsolescenza pagina = contraddice comportamento (codice/test) **o** decisione registrata (SpecKit/`manual_edited/`).

### Esecuzione e trigger (D-2, D-8, D-11, D-16)

- **D-2** — **Layer agentico** (skill + hook) popola/mantiene wiki riusando primitivi FEAT-003 (`create_wiki`/`record`/`ingest`/`distill`/`index_wiki`) + orchestrazione agentica. Editing manuale confinato a `manual_edited/`.

- **D-8** — **Skill distinta** dal versioning; invocata **al commit** da configuration-manager; esecuzione sincrona (output in stesso commit) o fallback asincrono (commit follow-up). **Contratto portabile** (client-agnostico): "al commit, col changeset".

- **D-11** — **Ingest** importa documentazione esterna in `ingested_sources/` (creazione/on-demand/update). **Import ≠ compile**: ingest popola input, generazione compila in concetti.

- **D-16** — **Comando setup** (`sertor wiki init`): crea struttura, installa binding trigger al commit, ingest iniziale opzionale.

### Scope e no-code (D-9, D-10, D-12, D-13)

- **D-9** — **No-code**: LLM Wiki + RAG valgono anche per progetti senza codice. Codice è una fonte-input opzionale.

- **D-10** — **Questo documento è autorità e2e**, consolida FEAT-003 (assorbe struttura/record/distill/idempotenza) e **supersede** (override su ingest/sources e indicizzazione). FEAT-003 è storico.

- **D-12** — **Tre superfici** (skill primaria + CLI + MCP) per operazioni on-demand (ingest, query, rigenerazione, manutenzione, setup).

- **D-13** — **Query via RAG**; navigazione umana via Obsidian/editor; **nessuna superficie wiki-nativa dedicata** (future/optional).

### Manutenzione e gate (D-14, D-17)

- **D-14** — **Lint + freschezza** (link rotti, orfani, copertura, contraddizioni, obsolescenza). Trigger: al commit (incrementale su changeset), on-demand (full), periodico (full).

- **D-17** — **Gate bloccante** al commit: se problemi sopra soglia, blocca commit, avvisa utente, propone soluzioni (incl. "ignora e committa" tracciato).

### Distillazione e consolidamento (D-15)

- **D-15** — **Distill non è operazione separata**: artefatti (spec, plan, ADR) sono fonti-input della generazione; ammessa modalità mirata on-demand.

---

## 42 Requisiti funzionali (EARS) + 10 Criteri di successo

**Bozza** (status: ready per design SpecKit).

### Famiglie di requisiti

1. **Popolamento agentico** (FR-001..007) — layer agentico, riuso FEAT-003, ingest/record/query/distill event-driven, protezione `manual_edited/`.
2. **Generazione + indicizzazione** (FR-008..011) — formato naturale, fonti configurabili, collezioni separate, refresh indipendente.
3. **Verità stratificata** (FR-012..017) — autorità su comportamento/perché, gerarchia default/configurabile, conflitto human-in-the-loop, obsolescenza.
4. **Fonti e trigger** (FR-018..022) — refresh al commit, git prerequisito, `ingested_sources/`, trigger manuale, esclusione binari.
5. **Perimetro retrieval** (FR-023..024) — RAG wiki+codice, input non indicizzati.
6. **Esecuzione + no-code** (FR-025..029) — skill distinta, invocazione al commit, trigger portabile, setup rilascia binding, no assunzione codice.
7. **Ingest** (FR-030..031) — popola `ingested_sources/`, import ≠ compile.
8. **Superfici** (FR-032) — skill/CLI/MCP per on-demand.
9. **Query + navigazione** (FR-033..034) — via RAG, Markdown navigabile.
10. **Manutenzione** (FR-035..038) — lint strutturale, freschezza, incrementale al commit, full on-demand/periodico.
11. **Distill + setup** (FR-039..040) — distill modalità generazione, setup crea+trigger+ingest.
12. **Gate al commit** (FR-041..042) — bloccante, avviso, soluzioni, override tracciato.

**Criteri di successo** (SC-001..010):
- Changeset limitato a pagine collegate (D-5).
- Input mai nel RAG (D-7).
- Risultati wiki + codice insieme (D-3).
- Gate bloccante + soluzioni (D-17).
- Funziona senza codice (D-9).
- Idempotenza strutturale (FEAT-003 RE-050/051).
- Stessa operazione da skill/CLI/MCP (D-12).
- Binding installato da setup (D-8).
- Obsolescenza rilevata (D-4).
- Ingest separa import/compile (D-11).

---

## Consolidamento

**Questo requisito consolida il seguente lavoro precedente:**

- **FEAT-003 Skill LLM Wiki** ([[skill-wiki-feat003]]): assorbe struttura (`concepts/`, `tech/`, `experiments/`, `syntheses/`, `index.md`, `log.md`), convenzioni (frontmatter, wikilink, kebab-case), operazioni (`create_wiki`, `record`, `distill`), idempotenza. **Override** su ingest e indicizzazione.

- **FEAT-007 Skill: mantenere il wiki** (branch `spec/005`, lint-semantico): **assorbito** come tema T5 (manutenzione: lint strutturale + freschezza). La semantica auto-fix è stata **abbandonata** (troppo rumorosa); il gate è human-in-the-loop (D-17).

---

## Prossimi passi

1. **SpecKit**: skill `/requirements` genera EARS formali, MoSCoW, NFR, rischi, dipendenze su questo documento.
2. **Design**: decomposizione feature in FEAT-010 stessa (o più feature secondo MoSCoW), specification SpecKit.
3. **Implementation**: libreria `sertor_core.wiki` estesa (D-1/D-6/D-14), skill agentica di orchestrazione, binding trigger per Claude Code.

---

## Backlink

[[skill-wiki-feat003]] · [[decomposizione-must-core]] · [[roadmap]] · [[costituzione-v1]] · [[ruolo-wiki-da-w1]]
