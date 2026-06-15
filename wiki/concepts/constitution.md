---
title: Costituzione di Sertor
type: concept
tags: [costituzione, governance, clean-code, clean-architecture, produzione, principio-x, host-agnostico, principio-xi]
created: 2026-05-31
updated: 2026-06-15 (v1.2.0 — Principio XI: consumo via vehicles CLI/MCP, no libreria a runtime)
sources: [".specify/memory/constitution.md", ".specify/templates/plan-template.md"]
---

# Costituzione di Sertor

La **Costituzione di Sertor** è il documento di governance che codifica i **11 principi vincolanti** del
progetto (Clean Architecture, qualità del codice, host-agnosticità del **Principio X** e consumo via
vehicles del **Principio XI**) sotto cui operano SpecKit e gli agenti; un **Constitution Check** ne fa
da gate al design. Fonte unica: `.specify/memory/constitution.md`. Ratificata v1.0.0 il 2026-05-31,
emendata a v1.1.0 il 2026-06-05 (aggiunta del Principio X), emendata a v1.1.1 il 2026-06-14 
(chiarimento Principio VII), emendata a v1.2.0 il 2026-06-15 (aggiunta del Principio XI).

## Cosa

Ratificata il **2026-05-31** la **Costituzione di Sertor v1.0.0** in
[`.specify/memory/constitution.md`](../../.specify/memory/constitution.md). È la **fonte unica dei
principi vincolanti** che governano il design, l'architettura e la governance di produzione di Sertor
(core + CLI).

**Emendamento v1.2.0 (2026-06-15):** aggiunto il **Principio XI — Consumo attraverso i vehicles
(CLI/MCP), non la libreria a runtime** per chiudere un gap di osservabilità: le operazioni invocate
direttamente via `build_indexer().index()` bypassano il wiring uniforme dei vehicles (config centralizzata,
osservabilità, error handling) e restano non tracciate (caso reale: re-index del corpus non comparve in
telemetria). Il Principio XI codifica che i consumatori a runtime (agenti, script, ospiti) devono
accedere alle capacità solo via CLI o MCP, con unica eccezione gli unit/integration test.

**Emendamento v1.1.0 (2026-06-05):** aggiunto il **Principio X — Capacità host-agnostiche** per
codificare operativamente la Mission (Sertor installabile su qualsiasi progetto ospite) e generalizzare
il confine repo-agnostico da core-libreria a tutte le capacità (motori RAG, skill wiki, rituali).
Vedi [[mission-vision]].

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

## I 11 principi (vincolanti)

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

### X. Capacità host-agnostiche (NUOVO 2026-06-05)
Ogni capacità di Sertor — nucleo, motori RAG, indicizzazione, skill wiki, rituali di orchestrazione —
**MUST essere disaccoppiata dal dominio/struttura dell'ospite**. L'ospite si configura, non si presume.
Nessuna assunzione hardcoded su percorsi, nomi, strutture cartelle ospite; ciò che varia fra ospiti
vive in configurazione, non nel corpo della capacità. Il dogfooding è strumentale: **non è licenza
per violare il confine**. **Test non-negoziabile:** una capacità opera su ospiti diversi (code+doc,
solo-doc, solo-code) senza modifiche al corpo — solo cambiando config.
→ **Mission (README), REQ-E1, CS-5, Principio I generalizzato**

### XI. Consumo attraverso i vehicles (CLI/MCP), non la libreria a runtime (NUOVO 2026-06-15)
I consumatori a runtime — agenti LLM, script, ospiti, automazioni — **MUST accedere alle capacità di
Sertor solo attraverso i suoi vehicles**: la **CLI** (`sertor-rag`, `sertor-wiki-tools`) oppure il
**server MCP**. MUST NOT importare e invocare `sertor_core` direttamente a runtime (es. via
`build_indexer().index(...)`). **Unica eccezione: gli unit/integration test**, che verificano la
libreria isolata (è come il Principio I/V garantiscono testabilità in isolamento).
Razionale: i vehicles cablano in modo **uniforme** i comportamenti trasversali — osservabilità
(`enable_observability`), configurazione centralizzata (Principio VIII), avvolgimento errori
(Principio IV), redazione segreti. L'accesso diretto bypassa tutto: caso reale, un re-index via
`build_indexer().index()` non viene tracciato in telemetria perché salta `enable_observability`
(cablato solo nei vehicles). Confinare il consumo ai vehicles rende ogni operazione osservabile e
configurata coerentemente.
→ **Principio VIII/IX (osservabilità e configurazione coerenti), FEAT-019/020/021/022/023 (hardening)**

## Sezioni aggiuntive nella Costituzione

- **Sicurezza, segreti e provenienza** (REQ-E5): no hardcoded secret, `.env` only,
  provenance tracking su corpus.
- **Governance:** branch + PR post-ratifica, Constitution Check gate in planning, semantic versioning.

## Governance

In produzione la costituzione impone:

- **Branching:** niente push diretti su `master`/`main` per il codice di feature; ogni feature su branch +
  PR con review (almeno un approver).
- **Gate Constitution Check:** incluso in [`plan.md`](../../.specify/templates/plan-template.md)
  (Phase 0 e Phase 1). Domande-checkpoint:
  - ✓ Il design rispetta il Principle I (core indipendente)?
  - ✓ Sono testati Principle IV (errori espliciti) e VI (idempotenza)?
  - ✓ Provider intercambiabili? Log strutturati?
- **Emendamenti:** modifiche ai 10 principi via PR + semantic versioning (`v1.0.0` → `v1.1.0` minor,
  `v2.0.0` breaking).
- **Responsabilità:** DRI di costituzione = design lead.

## Perché vincola

- Vincola il **design di ogni feature** via il gate Constitution Check in `plan.md`.
- **Principio I** e **IV** sono gate non-negoziabili (falliscono il Check se non soddisfatti).
- Chiude i dibattiti di design su basi condivise: "questo non soddisfa il Principio X" è un argomento, non
  un'opinione.

## Versioning e emendamenti

- **v1.0.0** — 2026-05-31, ratificata (9 principi).
- **v1.1.0** — 2026-06-05, emendamento MINOR (aggiunto Principio X — host-agnosticità).
- **v1.1.1** — 2026-06-14, emendamento PATCH (chiarimento Principio VII): funzioni piccole e a bassa
  profondità di annidamento, **guard clause / early return preferiti** alla nidificazione profonda; il
  **single-exit dogmatico (SESE) non è richiesto** — il problema è il *nesting*, non i `return` multipli.
  Allinea la regola alla pratica del codebase (Clean Code). Origine: refactor di `_resolve_config`.
- **v1.2.0** — 2026-06-15, emendamento MINOR (aggiunto Principio XI — consumo via vehicles CLI/MCP,
  no libreria a runtime): chiude gap di osservabilità; le operazioni via `build_indexer().index()` 
  bypassano il wiring dei vehicles e non vengono tracciate. Documento: 
  [`../.specify/memory/constitution.md`](../../.specify/memory/constitution.md).

## Riferimenti

- **Fonte unica:** [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) (v1.2.0)
- **Template planning:** [`.specify/templates/plan-template.md`](../../.specify/templates/plan-template.md)
  (Constitution Check integrato, gate "X — Host-agnostico" aggiunto)
- **Requisiti allineati:**
  - [[epiche-sertor-core-e-cli]] — structure epiche
  - [[decomposizione-must-core]] — come i Must plasmano da Principle I–IX
  - [[wiki-role-da-w1]] — vi contribuisce Principle VII (leggibilità, comunicazione)
  - [[sessionstart-hook]] — realizzazione di osservabilità (Principle IX, contesto iniettato)
  - [[mission-vision]] — Principio X come traduzione operativa di Mission/Vision
