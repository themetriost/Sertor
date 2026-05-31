---
title: Costituzione di Sertor v1.0.0 (ratificata)
type: synthesis
tags: [costituzione, governance, clean-code, clean-architecture, produzione]
created: 2026-05-31
updated: 2026-05-31
sources: [".specify/memory/constitution.md", ".specify/templates/plan-template.md"]
---

# Costituzione di Sertor v1.0.0 (ratificata)

## Cosa

Ratificata il **2026-05-31** la **Costituzione di Sertor v1.0.0** in
[`.specify/memory/constitution.md`](../../.specify/memory/constitution.md). È la **fonte unica dei
principi vincolanti** che governano il design, l'architettura e la governance di produzione di Sertor
(core + CLI).

## Origine

Derivata da zero (ignorando le bozze del prototipo, fase di exploration). Fonti:

- **Due wiki di riferimento esterni** (clonati in
  `C:\Workspace\Git\ExternalRepos\`):
  - Wiki **Clean Code** (principi di leggibilità, naming, gestione errori, Boy Scout Rule)
  - Wiki **Clean Architecture** (Dependency Rule, plugin architecture, confine tra strati, testabilità)
- **Allineamento ai requisiti Sertor:**
  - Epiche sertor-core e sertor-cli ([`requirements/sertor-core/epic.md`](../../requirements/sertor-core/epic.md),
    [`requirements/sertor-cli/epic.md`](../../requirements/sertor-cli/epic.md))
  - Requisiti trasversali REQ-E* (E1…E7), 3 feature Must (FEAT-001/002/003)
  - Criteri di successo (CS), obiettivi (OBJ), vincoli di scenario (SC)
  - Decomposizione Must (vedi [[decomposizione-must-core]])
- **Sinergia centrale:** "core riusabile come libreria, indipendente dalla CLI, provider
  intercambiabili via config" → **Dependency Rule** + **Plugin Architecture**; "production-grade" →
  **disciplina Clean Code**.

## I 9 principi (vincolanti)

### I. Core a dipendenze verso l'interno
**NON-NEGOZIABILE.** La libreria core è il prodotto. Non importa SDK provider (Azure/OpenAI) né CLI.
Adapter e CLI dipendono dalle astrazioni del core, non il contrario. Confine architetturale duro.
→ **REQ-E1, CS-5**

### II. Provider/backend intercambiabili dietro boundary; local-first
Scelta backend via config unica (non hardcoded). Cloud (incl. Azure) configurabile. Vector store
solo dove serve (non forzato ovunque). Local-first = eseguibile senza Azure.
→ **REQ-E2/E4/E7, CS-7**

### III. Semplicità giustificata (YAGNI) e unità piccole
Niente astrazioni senza evidenza di riuso. SRP (Single Responsibility), DRY (Don't Repeat Yourself).
Dipendenze pesanti isolabili in moduli separati. Complessità aggiunta solo se il valore è provato.
→ **Clean Code Ch. 3–5**

### IV. Gestione errori esplicita; niente null silenzioso
**NON-NEGOZIABILE.** Eccezioni di dominio ricche di contesto. Mai stato parziale o fallimento
silenzioso. Fallback locale quando applicabile.
→ **FEAT-002 REQ-004, FEAT-003 REQ-043, Clean Code Ch. 7**

### V. Testabilità e qualità provata da misure
Test F.I.R.S.T. (Fast, Isolated, Repeatable, Self-checking, Timely). Core completamente mockabile.
Retrieval misurato in hit@k, MRR; baseline = prototipo (corpora pubblici, ground-truth).
TDD raccomandato non imposto.
→ **CS-1/CS-4, OBJ-2/6**

### VI. Idempotenza, determinismo, non-distruttività
Re-run stabile (senza effetti laterali). `install` ≠ `run`. No overwrite silenzioso di artefatti.
Grafo/indice preservati se già presenti; refresh esplicito.
→ **REQ-E6, CLI CS-2, SC-3b**

### VII. Leggibilità come comunicazione
Naming di dominio retrieval (es. `retriever`, `ranker`, `corpus_loader` non `fetch_data`).
Boy Scout Rule: lascia il codice più leggibile di come l'hai trovato.
→ **Clean Code Ch. 1–2, 4**

### VIII. Configurabilità centralizzata del core
Tutte le scelte di runtime via config unica, nessun default hardcoded. Config = **single source of
truth** per provider, modelli, threshold, percorsi. CLI eredita e specializza.
→ **REQ-030, CS-4**

### IX. Osservabilità: tutto loggato a runtime
Retrieval, creazione embeddings, indicizzazione emettono **log strutturati:** operazione, provider
scelto, conteggi (doc/chunk), dimensione embedding, tempi, errori. **Nessun segreto nei log.**
→ **FEAT-001 REQ-031, FEAT-002 NFR-007, FEAT-003 RNF-004**

## Sezioni aggiuntive nella Costituzione

- **Sicurezza, segreti e provenienza** (REQ-E5): no hardcoded secret, `.env` only,
  provenance tracking su corpus.
- **Governance:** branch + PR post-ratifica, Constitution Check gate in planning, semantic versioning.

## Governance dopo la ratifica

A partire dal prossimo step di design:

- **Branching:** niente più push diretti su `master`/`main`; tutti gli step su branch feature,
  PR con review (almeno un approver).
- **Gate Constitution Check:** incluso in [`plan.md`](../../.specify/templates/plan-template.md)
  (Phase 0 e Phase 1). Domande-checkpoint:
  - ✓ Il design rispetta il Principle I (core indipendente)?
  - ✓ Sono testati Principle IV (errori espliciti) e VI (idempotenza)?
  - ✓ Provider intercambiabili? Log strutturati?
- **Emendamenti:** modifiche ai 9 principi via PR + semantic versioning (`v1.0.0` → `v1.1.0` minor,
  `v2.0.0` breaking).
- **Responsabilità:** DRI di costituzione = design lead (inizialmente tu).

## Impatto immediato

- Vincola il **design dei Must (FEAT-001/002/003)** della fase imminente.
- **Principle I** e **IV** sono gate non-negoziabili (falliscono Constitution Check se non soddisfatti).
- Semplifica discussioni future: "questo non soddisfa Principle X" chiude il dibattito.

## Riferimenti

- **Fonte unica:** [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) (v1.0.0)
- **Template planning:** [`.specify/templates/plan-template.md`](../../.specify/templates/plan-template.md)
  (Constitution Check integrato)
- **Requisiti allineati:**
  - [[epiche-sertor-core-e-cli]] — structure epiche
  - [[decomposizione-must-core]] — come i Must plasmano da Principle I–IX
  - [[ruolo-wiki-da-w1]] — vi contribuisce Principle VII (leggibilità, comunicazione)
  - [[hook-sessionstart-wiki]] — realizzazione di osservabilità (Principle IX, contesto iniettato)
