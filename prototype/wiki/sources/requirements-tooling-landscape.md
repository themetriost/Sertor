---
title: "Panorama strumenti Requirements Engineering (mid-2026) — ricerca avversariale"
type: source
tags: [requirements, speckit, ears, tooling, ricerca, gap-analysis, community-feedback]
created: 2026-05-30
updated: 2026-05-30
sources:
  - github.com/github/spec-kit
  - github.com/github/spec-kit/issues/1527
  - github.com/github/spec-kit/issues/1047
  - github.com/bmad-code-org/BMAD-METHOD
  - github.com/bmad-code-org/BMAD-METHOD/issues/1235
  - kiro.dev/docs/specs/feature-specs/
  - alistairmavin.com/ears/
  - buildermethods.com/prd-creator
  - github.com/Fission-AI/OpenSpec
  - github.com/sbhavani/speckit-agents
  - martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
---

# Panorama strumenti Requirements Engineering (mid-2026) — ricerca avversariale

## Sintesi esecutiva

Deep-research su strumenti di **Requirements Engineering** (fase a monte della governance di design) nel mid-2026, con focus su gap riconosciuti dalla community e benchmark di maturità. **Il gap confermato:** GitHub Spec-Kit non copre l'elicitazione e formalizzazione requisiti (intake idea → PRD), ed è riconosciuto dalla community (issue #1527 gen 2026, ancora aperta); il workspace Sertor decide di **costruire uno strumento proprio e standalone**, agnostico rispetto a SpecKit downstream.

---

## Il gap: Spec-Kit NON copre Requirements (evidence)

### Issue ufficiale GitHub Spec-Kit

- **Issue #1527** (gen 2026, **ancora aperta**, no maintainer response): "Add native `/speckit.prd` command — requirements intake & PRD generation upstream of `/speckit-specify`"
  - Titolo: "Native `/speckit.prd` — coverage of idea → PRD phase".
  - Richiesta community: "Spec-Kit parte da `/specify` (constitution check, brainstorm di spec) ma NON ha una fase **PRD-native** (visione, problema, KPI, stakeholder). Mancano 2–3 step upstream di specify. Questo è un artefatto di progetto critico per la governance."
  - Maintainer silence: a 5 mesi, nessuna risposta ufficiale (pattern confermato per richieste con scope "meta-governance").

- **Issue #1047** (correlata, più vecchia): "Requirements capture before constitution check?" — discussione ancora aperta su dove collocare i requisiti.

### Implicazione

Spec-Kit è un framework **spec-driven** (design-centric), NON un framework **requirements-driven** (elicitazione-centric). Non è un design flaw; è una scelta di scope. **Opportunità:** riempire il gap upstream con uno strumento autonomo.

---

## Panoramica degli strumenti (mid-2026)

### 1. BMAD-METHOD — pipeline completa (Analyst → PM → Architect)

**Maturità:** molto alta (~48.3k★ su GitHub, v6.8.0 del 25 maggio 2026)

**Scope:** pipeline **molto più ampia** di requirements. Flusso: **Brainstorming → Brief → PRD → PRFAQ → Feature design → Specification → Development**. Accoppiato a Claude Code come skill nativo.

**Punti di forza:**
- Coerenza end-to-end (idea → PRD → spec → codice).
- Community attiva e benchmark divulgativi.
- Integrazione Claude Code nativa.

**Contro:**
- **Token-heavy confermato:** ogni step consuma 80k–100k token per analisi (issue ufficiale #1235 "Excessive Token Usage" aperta, non risolto in v6.0).
- Versione 6 (sharding) **rivendica −74% a −82%** di riduzione token, ma confermato solo nei claim ufficiali (no benchmark indipendente).
- Scope totale (brainstorm → PRD → design → code) ≠ solo requisiti; rischio over-engineering per task semplici.

**Decisione per Sertor:** NON usare BMAD direttamente (costo, scope ampio); prendere spunti su elicitazione ma rimanere **lightweight**.

---

### 2. Amazon/AWS Kiro — Requirements in EARS, Design-First/Requirements-First

**Maturità:** produzione (parte dei tool ufficiali AWS, ~2.3k★ su GitHub)

**Scope:** focus sulla fase **Requirements distinta da Design**. Notazione **EARS** (Easy Approach to Requirements Syntax, Alistair Mavin, Rolls-Royce 2009). Genera `requirements.md`, `design.md`, `tasks.md`.

**Varianti:**
- **Requirements-First:** cattura requisiti EARS, poi design su richiesta.
- **Design-First:** parte da requirement alto-livello, genera design (meno utilizzato).

**Punti di forza:**
- EARS è metodologia consolidata (IEEE RE09 recognition).
- Separazione netta requisiti ↔ design (allineato col nostro disaccoppiamento).
- Notazione formale, requisiti testabili e tracciabili.

**Contro:**
- **Compatibilità fuori dal suo IDE non dimostrata** dalle fonti pubbliche (Kiro è pensato per il suo ecosistema AWS).
- Manuale offline (no integrazione web/API).
- Community niche (meno divulgazione di BMAD).

**Decisione per Sertor:** Kiro è una **fonte di ispirazione** per EARS e disaccoppiamento; NON usare direttamente (binding IDE), ma copia il pattern Requirements-First.

---

### 3. PRD Creator (Builder Methods) — skill Claude Code, intervista strutturata → PRD

**Maturità:** open-source, stabile (free skill, ~800★, mantenimento attivo)

**Scope:** fase **PRD sola** (intervista 8 step → PRD bloccato). Genera markdown portabile.

**Punti di forza:**
- Lightweight (no boilerplate, PRD entro 2–3 turni).
- Skill Claude Code nativa (riusabile nel workspace).
- Output markdown (importabile dovunque).
- Free & open-source.

**Contro:**
- Solo PRD; no requisiti formali (manca atomicità/testabilità EARS).
- Intervista generica (non domain-aware, no customizzazione metodologia).

**Decisione per Sertor:** PRD Creator è un **candidato** per generare visione iniziale; combineremo con EARS downstream (PR Creator genera PRD narrative, skill `/requirements` estrae requisiti EARS dalla narrazione).

---

### 4. OpenSpec (Fission-AI) — CLI npx, /opsx:propose → proposal + specs + design + tasks

**Maturità:** recente (~250★ GitHub, v2.1.0 del 2026). **Nessun MCP/API key richiesto** (pure CLI).

**Scope:** `npx openspec` con `/opsx:propose` → generazione end-to-end (proposal, specs, design, tasks) in un passaggio.

**Punti di forza:**
- **Tool-agnostico:** supporta ~31 tool inclusi Claude Code, Cursor, Codex, Kiro, VS Code, codeium, etc. (orchestrazione multi-tool).
- No auth key richiesta (locale-first per la proposta).
- Output multi-formato (specs + design + tasks in Markdown).

**Contro:**
- Ancora in evoluzione (pochi starburst, no grande case study pubblico).
- Orchestrazione multi-tool = complessità (non integrato con Sertor).
- No EARS nativo.

**Decisione per Sertor:** **interessante come aggregatore**, ma NON centrale; se mai useremo CLI aggregatori, OpenSpec è una candidata, ma il focus resta su skill native.

---

### 5. speckit-agents (sbhavani) — ponte sperimentale per il gap (PM-Agent → /speckit.specify)

**Maturità:** sperimentale (~9★ GitHub, MIT license)

**Scope:** **ponte GIÀ costruito** per il gap SpecKit: PM-Agent legge PRD.md → estrae top feature → `/speckit-specify` automatico.

**Punti di forza:**
- Riconosce il gap ufficialmente.
- Proof-of-concept riusabile (ispirazione per il nostro orchestratore).

**Contro:**
- Nessun uso in produzione noto (è un esperimento).
- Non divulgato (pochissimi starburst).
- Dipende da SpecKit (se SpecKit cambia schema, rompe).

**Decisione per Sertor:** Studiare il codice di speckit-agents (ispirazione); il nostro `/requirements` + ponte verso SpecKit sarà **standalone e testato** (non sperimentale).

---

## EARS — Metodologia consolidata (background teorico)

**Fonte primaria:** Alistair Mavin, "EARS — Easy Approach to Requirements Syntax" (Rolls-Royce, IEEE RE09). **IEEE-recognized** (anno 2009, >800 citazioni accademiche).

### 5 pattern core + Complex

1. **Ubiquitous (U):** `The [system] shall [action].` — sempre vera.
   - Esempio: "Il sistema deve gestire autenticazione OAuth2."

2. **State-driven (S):** `While [condition], the [system] shall [action].` — valida in stato specifico.
   - Esempio: "Mentre l'utente è autenticato, il sistema deve caricare token refresh."

3. **Event-driven (E):** `When [trigger], the [system] shall [action].` — reazione a evento.
   - Esempio: "Quando riceve una richiesta GET `/docs`, il sistema deve servire OpenAPI JSON."

4. **Optional (O):** `The [system] shall [action], if [condition].` — requisito condizionale/feature.
   - Esempio: "Il sistema deve supportare CORS, se origin è whitelisted."

5. **Unwanted behaviour (W):** `If [undesired-event], the [system] shall [recovery].` — gestione errori/edge case.
   - Esempio: "Se la connessione Azure cade, il sistema deve fallback a Ollama locale."

6. **Complex:** combinazioni di pattern (rari).

### Proprietà di un requisito EARS ben-formato

- **Atomico:** un solo comportamento per requisito.
- **Unambiguo:** termini definiti (glossario collegato).
- **Formale:** segue uno dei 5 pattern.
- **Testabile:** criterio accettazione misurabile.
- **Tracciabile:** ID REQ-NNN, link a test/code.

### Valore per lo scope Sertor

EARS **toglie ambiguità, termini non definiti, trigger mancanti, logica incompleta** → requisiti che vanno diritti in `/speckit-specify` senza riscrittura. Foundation del nostro skill `/requirements`.

---

## Feedback community & punti aperti

### Feedback confermato (non vendor claim)

1. **BMAD davvero pesante (segnale contrarian principale):** issue #1235 aperta a maggio 2025, richiede **sharding v6 per risolvere** l'overflow token. Community references: "80–100k per step è insostenibile"; v6 claims −74%, ma zero third-party benchmark.

2. **"Requisiti migliori o solo boilerplate?"** — **DOMANDA APERTA**, nessun benchmark verificato. I vendor (BMAD, Kiro, OpenSpec) reclamano qualità, ma gli study indipendenti sono assenti. **Opportunità:** il workspace valuterà il nostro tool con eval set concreto (EARS coverage, non fattualità, ma structure).

3. **Kiro fuori dal suo IDE = non dimostrato:** nessuna documentazione di uso di Kiro CLI senza AWS IDE. Code examples tutti IDE-bound.

4. **Il gap Spec-Kit è riconosciuto da utenti, non dai maintainer:** issue #1527 è chiara richiesta community; lo scopo di GitHub è innovazione interna, non copertura di ogni gap.

5. **Aggregatori in ritardo su repo primari:** marktechpost, dev.to, altri blog aggregatori reclamano "2026 tools landscape", ma i link puntano a articoli 2025 (lag di 6+ mesi). Fonti primarie (GitHub issue, doc ufficiali) sono più fresche.

---

## La nostra decisione: costruire uno strumento PROPRIO e standalone

### Principi

1. **Lightweight:** skill + agente (`requirements-analyst`), no framework pesante.
2. **EARS-native:** requisiti atomici, formali, testabili — non narrativa.
3. **Standalone:** agnostico rispetto a SpecKit (il nostro SpecKit legge output `.md`, NON c'è accoppiamento di nome).
4. **Dogfooding MCP:** usa sertor-rag per contestualizzare requisiti (se progetto Sertor stesso, accesso a codebase).
5. **Output portabile:** cartella `requirements/<short-name>/requirements.md` (copiabile su qualunque progetto).

### Artefatti attuali

Vedi [[requirements-engineering]] e [[ears-methodology]].

---

## Note storiche & crediti

- EARS: Alistair Mavin (Rolls-Royce, 2009). Evoluzione di Natural Language Processing per requirement, focus su disambiguazione.
- BMAD-METHOD: società privata, v6.8.0 community best-effort (no insider access).
- Spec-Kit: GitHub (maintainers design-first, scope spec-focused per design).
- PRD Creator: Builder Methods (open-source community, stabile).
- Kiro: Amazon AWS (produzione, scopo interno AWS Quicksight/etc., export pubblico di use case).
- OpenSpec: Fission-AI (incubatore AI, 2026 refresh).

---

## Referenze ulteriori

- [Exploring Generative AI for Software Design Documents — Martin Fowler](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) — survey 2025–2026 di tool gen-AI per design docs (menziona BMAD, Spec-Kit, alcuni custom solutions).
- [EARS Methodology — Official](https://alistairmavin.com/ears/) — documentation ufficiale Alistair Mavin.
- [GitHub Spec-Kit issues](https://github.com/github/spec-kit/issues/) — source of truth per community feedback.
