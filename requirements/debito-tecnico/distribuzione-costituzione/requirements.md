# Requisiti — Distribuzione corretta della costituzione neutra + rifinitura principi

> Epica: **`debito-tecnico`** · decomposizione di **FEAT-009**. Pacchetto: **`sertor-flow`** (installer
> governance). Branch: `058-distribuzione-costituzione`. `sertor-core` **non coinvolto** (NFR-03).

## 1. Contesto e problema

`sertor-flow install` (governance/SDLC) deve depositare sull'ospite una **costituzione-starter neutra**
(`constitution-starter.md` → `.specify/memory/constitution.md`, FEAT-005). **Verifica empirica
2026-06-19** (host Spike + install pulito in dir temp): l'ospite riceve invece il **template placeholder
di spec-kit** (`# [PROJECT_NAME] Constitution`, `[PRINCIPLE_1_NAME]`, `<!-- Example: … -->`), **non** il
nostro starter.

**Causa (confermata nel codice).** Dopo il pivot vendoring→launch-installer (FEAT-045),
`execute_governance_plan` esegue **Step 0 = `specify init --ai <assistant>`** (spec-kit upstream) che
scaffolda `.specify/**` **incluso un `constitution.md` placeholder**. Poi il piano applica il nostro
artefatto CONFIG della costituzione con strategia **`CREATE_IF_ABSENT`** (`_apply_config`,
`install_governance.py`): il file esiste già (creato da `specify init`) → **SKIP**. Quindi lo starter
neutro **non viene mai depositato**. Lo stesso vale in **upgrade** (la costituzione è preservata, FR-040).

Conseguenza: la promessa «distribuiamo una costituzione sensata» è **falsa**; ogni ospite governance
ottiene il template vuoto da compilare a mano.

## 2. Decisioni di design (approvate)

- **D1 — replace-if-placeholder (Q-confermata 2026-06-19):** dopo `specify init`, se
  `.specify/memory/constitution.md` è **il placeholder di spec-kit**, il sistema lo **sovrascrive** con
  lo starter neutro; se è una **costituzione reale** (già personalizzata dall'ospite), la **preserva**
  (non-distruttività, Principio VI). Scartate: «sovrascrivi sempre» (distruttiva) e «lascia com'è» (bug).
- **D2 — rilevamento placeholder deterministico:** il placeholder si riconosce da **sentinelle** del
  template spec-kit assenti in qualunque costituzione reale (es. `[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]`,
  o il pattern di placeholder `[MAIUSCOLE_CON_UNDERSCORE]`). Deterministico, offline, zero LLM.
- **D3 — rifinitura dei principi neutri:** lo starter aggiunge i **kernel generici** oggi mancanti,
  estratti dalla costituzione di Sertor de-RAGizzata: (a) **«Consume through stable interfaces, not
  internals»** (generalizzazione del Principio XI); (b) **«Replaceable details / no vendor lock-in»**
  (kernel del Principio II, oggi solo implicito in I); (c) allineamento del principio di leggibilità alla
  **chiosa SESE/nesting** (v1.1.1). I principi Sertor-specifici (X host-agnostico, veicoli `sertor-rag`)
  restano **esclusi** dallo starter.

## 3. Requisiti funzionali (EARS)

### Distribuzione corretta (D1/D2)
- **REQ-001 (Event):** QUANDO l'install governance, dopo `specify init`, trova
  `.specify/memory/constitution.md` riconosciuto come **placeholder di spec-kit**, il sistema DEVE
  **sovrascriverlo** con lo starter neutro.
- **REQ-002 (Unwanted):** SE `.specify/memory/constitution.md` è una costituzione **reale** (non
  placeholder), ALLORA il sistema DEVE **preservarla** invariata (nessuna sovrascrittura).
- **REQ-003 (Ubiquitous):** Il rilevamento del placeholder DEVE essere **deterministico** (sentinelle del
  template spec-kit), offline, senza LLM né rete.
- **REQ-004 (Event):** QUANDO l'install è eseguito su un ospite **senza** alcun `.specify/` (caso in cui
  `specify init` non produce la costituzione, o fallisce il layout), il sistema DEVE comunque depositare
  lo starter neutro (create-if-absent classico) — nessuna regressione del comportamento di deposito.
- **REQ-005 (Ubiquitous):** L'**upgrade** governance DEVE applicare la stessa semantica
  replace-if-placeholder (un placeholder residuo viene portato allo starter; una costituzione reale è
  preservata, FR-040 invariato per le costituzioni reali).

### Rifinitura dei principi (D3)
- **REQ-006 (Ubiquitous):** Lo starter neutro DEVE includere un principio **«Consume through stable
  interfaces, not internals»** (forma host-agnostica del Principio XI di Sertor).
- **REQ-007 (Ubiquitous):** Lo starter neutro DEVE includere un principio **«Replaceable details / no
  vendor lock-in»** (kernel del Principio II) — dipendenze esterne dietro boundary, scelta per config.
- **REQ-008 (Should):** Il principio di leggibilità dello starter DOVREBBE riflettere la chiosa
  **guard-clause/early-return vs SESE** (Principio VII v1.1.1).
- **REQ-009 (Ubiquitous):** I principi Sertor/RAG-specifici (host-agnosticità X, veicoli, motori RAG,
  hit@k/MRR) DEVONO restare **esclusi** dallo starter; la versione dello starter DEVE essere **bumpata**
  (semver) e la nota d'intestazione DEVE restare («personalizza con `speckit-constitution`»).

### Guardia / non-regressione
- **REQ-010 (Ubiquitous):** Una **guardia offline** DEVE attestare che, dato un `.specify/memory/
  constitution.md` placeholder (fixture), dopo l'install il file depositato è **lo starter neutro** (non
  il placeholder); e che una **costituzione reale** (fixture) è **preservata**.
- **REQ-011 (Ubiquitous):** Le suite esistenti (`sertor-flow`, `kit`, `sertor`) DEVONO restare **verdi**;
  `sertor-flow` DEVE restare **senza dipendenza** da `sertor-core`/`sertor` (NFR-03).

## 4. Requisiti non funzionali
- **NFR-01:** Solo `sertor-flow` (+ eventuale primitiva nel `sertor-install-kit` se condivisa); `sertor-core` INVARIATO.
- **NFR-02:** `install ≠ run`, non-distruttivo, idempotente; la sovrascrittura del placeholder è essa stessa idempotente.
- **NFR-03:** `sertor-flow` senza dipendenza da `sertor-core`/`sertor`.
- **NFR-04:** Offline (nessuna rete/credenziali); il fix non dipende dall'esito di `specify init`.

## 5. Criteri di successo
- **CS-1:** Dopo `sertor-flow install` su host pulito, `.specify/memory/constitution.md` **==** lo starter
  neutro (0 occorrenze di `[PROJECT_NAME]`/`[PRINCIPLE_1_NAME]`).
- **CS-2:** Una costituzione reale pre-esistente è **preservata byte-per-byte** dopo install/upgrade.
- **CS-3:** Lo starter contiene i due nuovi principi (interfacce stabili; replaceable details) e nessun
  principio Sertor/RAG-specifico.
- **CS-4:** Guardia offline verde; suite `sertor-flow`/`kit`/`sertor` verdi; `sertor-flow`↛`sertor-core` (guard).
- **CS-5 (empirico):** install pulito in dir temp → la costituzione depositata è lo starter neutro
  (riproduce il bug-fix end-to-end).

## 6. Ambito
**In ambito:** fix replace-if-placeholder (install + upgrade), rilevamento placeholder, rifinitura dei
principi neutri dello starter, guardia offline, bump versione starter.
**Fuori ambito:** modifiche a spec-kit upstream; la costituzione **di Sertor** (`.specify/memory/
constitution.md` di questo repo, scritta a mano, non toccata); altri asset governance; FEAT-008.

## 7. Rischi
- **R-1 (falsi positivi/negativi nel rilevamento):** una costituzione reale che contenga per caso `[…]`
  bracket. *Mitigazione:* sentinelle specifiche del template spec-kit (`[PROJECT_NAME]`,
  `[PRINCIPLE_1_NAME]`) + test-del-test; in dubbio, **preservare** (fail-safe verso la non-distruttività).
- **R-2 (dipendenza dal formato del template upstream):** se spec-kit cambia i placeholder, il
  rilevamento va aggiornato. *Mitigazione:* sentinelle multiple + guardia che fallisce se il template
  vendorato cambia forma.
- **R-3 (scope creep nella rifinitura principi):** tenere i due principi nuovi **brevi e generici**, in
  linea con lo stile dello starter esistente.

## 8. Domande aperte — risolte
- **Q-1** Semantica sovrascrittura → **replace-if-placeholder** (D1, confermata utente 2026-06-19).
- **Q-2** Rilevamento → **sentinelle del template spec-kit** (D2).
- **Q-3** Rifinitura principi → **sì**, due kernel generici + allineamento VII (D3).
