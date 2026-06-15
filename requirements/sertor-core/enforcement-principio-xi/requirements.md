# Requisiti — Enforcement del Principio XI (consumo via vehicles)

<!-- Capacità cross-cutting su due epiche: sertor-core (Gruppo A) e sertor-cli (Gruppi B/C/D).
     Realizza/rinforza il Principio XI della costituzione v1.2.0 a tre livelli di forza
     (difesa in profondità) + neutralizzazione del plan-template del bundle. -->

## 1. Contesto e problema (perché)

Il **Principio XI** (costituzione v1.2.0) impone che i consumatori a runtime usino Sertor **solo via
vehicles** (CLI `sertor-rag`/`sertor-wiki-tools`, server MCP), non importando `sertor_core`
direttamente. Oggi è solo una **regola** (governance), non è **realizzata**: l'unico cablaggio dei
concern trasversali (`enable_observability`) vive nei consumatori CLI/MCP
(`cli/__main__.py`, `sertor_mcp/server.py`), **non** nelle factory `build_*` di `composition.py`. Gap
**reale e verificato**: un re-index via `build_indexer().index()` diretto **non** viene tracciato in
telemetria (salta `enable_observability`); confermato dallo store osservabilità (ultimo evento `index`
fermo a una run vecchia, i re-index via libreria di oggi assenti).

Servono **tre livelli complementari** (difesa in profondità) + una correzione del bundle:
- **A (per costruzione, `sertor-core`):** rendere ogni percorso d'ingresso **sicuro/tracciato** alla
  radice → la violazione del Principio XI diventa innocua.
- **B (istruzione, `sertor-cli`):** l'ospite riceve un'istruzione d'uso → la violazione è scoraggiata.
- **C (vincolo hard, `sertor-cli`):** un hook rileva/avvisa l'uso diretto sull'ospite → la violazione
  è osservata/bloccata.
- **D (coerenza bundle, `sertor-cli`):** il plan-template spedito agli ospiti **non** deve portare i
  gate costituzionali di Sertor (incl. XI, Sertor-specifico) ma derivarli dalla costituzione dell'ospite.

## 2. Obiettivi e criteri di successo

- **CS-1 (A):** una operazione di indicizzazione/retrieval eseguita via **qualunque** percorso
  d'ingresso supportato (CLI, MCP, factory `build_*`) con osservabilità abilitata produce l'evento
  persistito; **0** percorsi supportati bypassano i concern trasversali.
- **CS-2 (A, Principio I preservato):** `sertor_core` resta importabile e l'intera suite test passa
  invocando libreria/funzioni direttamente (l'eccezione test è intatta).
- **CS-3 (B):** dopo `sertor install rag` l'ospite ha un'istruzione d'uso machine-readable per
  l'agente (blocco a marker in `CLAUDE.md`) che indica i vehicles e vieta l'import diretto.
- **CS-4 (C):** sull'ospite, un uso diretto di `sertor_core` fuori dai vehicles/test **viene rilevato**
  e segnalato (almeno warning) in ≥1 scenario verificabile, senza bloccare il flusso quando in modalità
  warn.
- **CS-5 (D):** un ospite che installa la governance riceve un plan-template i cui gate **derivano dalla
  sua costituzione** (placeholder generico), **0** gate Sertor-specifici (incl. XI) nel template
  dell'ospite; il dogfood di Sertor mantiene il proprio template gated.
- **CS-6 (non-regressione):** tutte le suite esistenti (root, kit, sertor, sertor-flow) restano verdi.

## 3. Stakeholder e attori

- **Agente LLM dell'ospite** — consumatore primario (deve usare i vehicles).
- **Sviluppatore di Sertor / dogfood** — beneficiario di A (telemetria completa anche da libreria).
- **Ospite (repo target)** — riceve B/C/D via installer.
- **Costituzione (Principio XI, v1.2.0)** — fonte normativa che questi requisiti realizzano.

## 4. Ambito

### In ambito
- **A:** cablaggio dei concern trasversali (osservabilità, config, wrapping errori al boundary) **dentro
  il composition root / le `build_*`**; restringimento della superficie pubblica (`__init__`) verso le
  factory; preservando import e testabilità (Principio I).
- **B:** blocco `CLAUDE.md` a marker (es. `SERTOR:RAG-USAGE`) depositato da `sertor install rag`.
- **C:** hook host-specifico (depositato dall'installer) che rileva l'uso diretto della libreria.
- **D:** il bundle `sertor-flow` spedisce il plan-template **generico** (gate derivati dalla costituzione
  dell'ospite), non quello gated del dogfood.

### Fuori ambito
- Modifica del Principio XI in costituzione (già fatto, v1.2.0).
- Rendere `sertor_core` non importabile (vietato dal Principio I).
- Enforcement hard "blocco" come default (vedi DA-C: default = warn).
- Distribuzione/installer su assistenti non-Claude (Principio X, epica multi-assistente).

## 5. Requisiti funzionali (EARS)

### Gruppo A — Per costruzione (epica `sertor-core`)
- **REQ-A1 (Ubiquitous):** *The composition root shall wire the cross-cutting concerns (observability
  activation, centralized configuration, boundary error-wrapping) so that any supported entry path —
  CLI, MCP, or a `build_*` factory — gets them applied uniformly.*
- **REQ-A2 (Event-driven):** *When an indexing or retrieval operation runs through a `build_*` factory
  with observability enabled in configuration, the system shall persist the corresponding event*
  (chiude il gap: il re-index via libreria diventa tracciato).
- **REQ-A3 (Ubiquitous, Principio I):** *The system shall keep `sertor_core` importable and testable in
  isolation; unit/integration tests may invoke library and functions directly.*
- **REQ-A4 (Ubiquitous):** *The public package surface (`__init__`) shall expose the safe factory
  entry points as the natural way in, not the low-level internals.*
- **REQ-A5 (Unwanted):** *If observability is disabled in configuration, then the system shall remain a
  no-op on that path (zero overhead, no store), preserving current default-off behaviour.*

### Gruppo B — Istruzione lato ospite (epica `sertor-cli`)
- **REQ-B1 (Event-driven):** *When `sertor install rag` runs, the system shall deposit a
  marker-delimited usage block in the host `CLAUDE.md` instructing the agent to use the RAG capability
  via the `sertor-rag` CLI or the MCP tools and not to import `sertor_core` in its own scripts.*
- **REQ-B2 (Ubiquitous):** *The usage block shall use its own markers (distinct from the wiki and SDLC
  ritual blocks) and be idempotent and non-destructive (re-run does not duplicate; the rest of
  `CLAUDE.md` is preserved).*
- **REQ-B3 (Ubiquitous):** *The usage block shall be host-facing English and contain no Sertor-internal
  constitutional clauses (it is a usage instruction, not a host governance gate).*

### Gruppo C — Vincolo hard lato ospite (epica `sertor-cli`)
- **REQ-C1 (Event-driven):** *When the host agent uses `sertor_core` directly outside the vehicles
  (and outside tests), the installed hook shall detect it and surface a signal.*
- **REQ-C2 (Optional/severity):** *Where the hook severity is `warn` (default), the system shall emit a
  non-blocking warning; where it is `block`, the system shall prevent the action.* (default: DA-C)
- **REQ-C3 (Ubiquitous, Principio X):** *The hook shall be host/assistant-specific (a trigger adapter
  deposited by the installer), not embedded in the core; its absence shall not break Sertor usage.*
- **REQ-C4 (Unwanted):** *If the hook cannot evaluate (parse error, unknown context), then it shall fail
  open (no false block), non-fatally.*

### Gruppo D — Plan-template neutro nel bundle (epica `sertor-cli`)
- **REQ-D1 (Ubiquitous):** *The `sertor-flow` bundle shall ship a generic `plan-template.md` whose
  Constitution Check gates are derived from the host's own constitution (the neutral starter), not the
  Sertor-specific gated template.*
- **REQ-D2 (Ubiquitous):** *Sertor's own dogfood plan-template (with the 11 Sertor gates) shall remain
  unchanged; only the bundled/host-facing copy is neutralized.*
- **REQ-D3 (Ubiquitous):** *The bundle's plan-template shall be sourced from the upstream spec-kit
  (generic) — same provenance logic already applied to the scaffolding scripts (F3) — and excluded from
  the dogfood-sourced asset sync that would re-introduce the gated version.*

## 6. Requisiti non funzionali
- **NFR-1 (Principio I):** A non deve introdurre dipendenze del core verso CLI/MCP; il wiring resta nel
  composition root.
- **NFR-2 (default-off):** osservabilità resta opt-in (`SERTOR_OBSERVABILITY`); A non la accende da sola.
- **NFR-3 (non-distruttività/idempotenza):** B/C/D rispettano la disciplina installer (skip/merge a
  marker, re-run a zero modifiche).
- **NFR-4 (host-agnostico, Principio X):** B/C/D non incorporano assunzioni sul dominio ospite; gli
  asset host-facing sono in inglese.
- **NFR-5 (non-regressione):** suite root/kit/sertor/sertor-flow verdi; ruff pulito.

## 7. Vincoli, assunzioni e dipendenze
- Principio XI già in costituzione v1.2.0; questi requisiti lo **realizzano**, non lo ridefiniscono.
- Dipendenza A→(B/C utili ma indipendenti): A è la causa-radice; B/C/D non dipendono da A per
  l'implementazione.
- Riferimenti reali: `src/sertor_core/composition.py` (`build_*`, `enable_observability`),
  `cli/__main__.py`, `sertor_mcp/server.py`, `packages/sertor/src/sertor_installer/install_rag.py`,
  `packages/sertor-flow/src/sertor_flow/sync.py` + assets, `ExternalRepos/spec-kit/templates/plan-template.md`.

## 8. Rischi
- **R-1 (A):** spostare il wiring nel composition root tocca un punto centrale → rischio regressione su
  CLI/MCP (che oggi chiamano `enable_observability` esplicitamente). Mitigazione: idempotenza
  dell'attach + gate non-regressione.
- **R-2 (A):** restringere `__init__` può rompere consumatori/test che importano internals.
  Mitigazione: mappare gli import attuali prima di restringere.
- **R-3 (C):** un hook che blocca rischia falsi positivi (es. i test). Mitigazione: default warn,
  fail-open, esclusione esplicita dei percorsi test.
- **R-4 (D):** il guard anti-drift del bundle (`test_assets_sync.py`) confronta col dogfood; cambiando
  la fonte del plan-template va aggiornato anche il guard (escludere/riposizionare).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-A1, A2, A3, A5 (root fix + Principio I); REQ-B1, B2 (istruzione); REQ-D1, D2, D3
  (coerenza bundle); NFR-1/2/3/5.
- **Should:** REQ-A4 (restringere superficie); REQ-C1, C3, C4 (hook warn host-specifico); REQ-B3.
- **Could:** REQ-C2 modalità `block`.
- **Won't (ora):** enforcement su assistenti non-Claude; blocco hard di default.

## 10. Domande aperte
- **DA-A — Superficie pubblica (REQ-A4):** restringere `__init__` ora (rischio rotture import) o solo
  documentare le factory come ingresso e rinviare il restringimento? [DA CHIARIRE]
- **DA-C — Severità hook (REQ-C2):** default `warn` (non-bloccante) confermato? `block` resta Could?
  [proposto: default warn]
- **DA-mapping — Strutturazione SpecKit:** A come feature `sertor-core`; B+C+D come una o più feature
  `sertor-cli`? [proposto: A = 1 feature core; B+C = 1 feature installer "host enforcement"; D = fix
  piccolo, feature a sé o accorpato]
