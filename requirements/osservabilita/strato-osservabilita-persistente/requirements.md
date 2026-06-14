# Requisiti — Strato di osservabilità persistente nel core

<!-- Deriva da: FEAT-001 (epica `requirements/osservabilita/epic.md`) -->

## 1. Contesto e problema (perché)

Sertor **già** emette eventi strutturati a ogni operazione, tramite `log_event(level, operation,
**fields)` in `src/sertor_core/observability/logging.py`: l'evento va sullo **stdlib logging** con
`extra={"operation": ..., **safe}` e i campi-segreto sono **redatti** (`redact()`, match per-parola
dalla feat. 019). Gli eventi reali oggi: `index` (collection/provider/documents/chunks/embedding_dim/
elapsed_ms), `embeddings` (provider/texts/tokens), `embeddings_cache` (hits/misses/total),
`embeddings_error`, `embeddings_retry`, `low_confidence`, `retrieve` (collection/status/doc_type —
**non** contiene il testo della query), `config_no_env_found`.

Il problema: questi eventi sono **effimeri** (vanno su stderr e si perdono a fine comando). Senza un
**luogo dove restano** non esistono report storici (hit/miss della cache nel tempo, costo cumulativo,
salute del corpus). Questa feature è il **fondamento** dell'epica: dà agli eventi un **archivio locale
interrogabile**. FEAT-002 (aggregazione/report) interroga questo store; FEAT-003/004 (pannello TUI) lo
leggono. Matura l'idea di backlog «logging come strategia runtime».

> Il *come* (schema dello store, meccanismo di intercettazione, stack) è materia della **fase di
> design**. Qui solo *cosa* e *perché*.

## 2. Obiettivi e criteri di successo
- **OB-1 — Persistenza completa:** ogni evento emesso da `log_event` (operation + campi + istante)
  finisce in un archivio locale, senza perdite. *SC-1:* con la persistenza attiva, dopo **N**
  operazioni il numero di eventi recuperabili dall'archivio è **≥ N** (uno per ogni `log_event`).
- **OB-2 — Interrogabilità:** l'archivio è interrogabile per `operation` e per intervallo temporale
  (abilita FEAT-002). *SC-2:* è possibile recuperare i soli eventi di un dato `operation` in un dato
  intervallo.
- **OB-3 — Nessuna regressione:** con la persistenza **disattivata** (default) il comportamento e le
  prestazioni sono **identici a oggi**. *SC-3:* persistenza spenta → nessun archivio creato, output di
  logging invariato (stderr + redazione), suite verde senza modifiche ai consumatori.
- **OB-4 — Non intrusiva:** persistere non rompe né rallenta l'operazione osservata. *SC-4:* un guasto
  della persistenza (store non scrivibile/corrotto) **non** fa fallire l'operazione; l'overhead a
  persistenza attiva è misurato e trascurabile.
- **OB-5 — Privacy-by-default:** di default l'archivio contiene **solo metriche**, mai testo grezzo.
  *SC-5:* nessun campo di contenuto (es. testo di query) compare nell'archivio senza un opt-in esplicito
  (non oggetto di questa feature); i campi-segreto restano redatti anche nello store.

## 3. Stakeholder e attori
- **Il core di Sertor:** sorgente degli eventi (`log_event`); resta invariato nel comportamento.
- **FEAT-002 (aggregazione/report):** consumatore primario dell'archivio.
- **FEAT-003/004 (pannello TUI):** consumatori a valle (via FEAT-002 o diretti, lettura sola).
- **Owner/operatore:** abilita la persistenza e ne sceglie la sede via configurazione.
- **Adapter di persistenza:** l'implementazione concreta dell'archivio (scelta in composition root).

## 4. Ambito

### In ambito
- Una **porta di osservabilità** (astrazione) + un **adapter di persistenza** locale che cattura gli
  eventi che il core già emette, rendendoli interrogabili.
- L'**attivazione** e la **sede** dell'archivio governate dalla configurazione centralizzata.
- Il **vincolo di default** privacy-by-default (solo metriche) e il riuso della redazione esistente.
- La **resilienza** della persistenza (degrado non-fatale) e la **non-intrusività** (non bloccante).

### Fuori ambito
- **Aggregazione/report** sugli eventi → **FEAT-002**.
- **Pannello TUI** (live e report) → **FEAT-003/004**.
- **Export OpenTelemetry** → **FEAT-005**; **stima € / metriche aggregate** → FEAT-007/006.
- **Persistenza del testo grezzo** (query/conversazioni): è un **opt-in** di una feature successiva;
  qui il default *metriche-only* è il **vincolo**, non si implementa l'opt-in.
- Lo **schema** dell'archivio e il **meccanismo** di intercettazione (handler vs emissione esplicita):
  **design** a valle (vedi §10, DA-O-f).

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Optional):** *Where observability persistence is enabled, the system shall write every
  event emitted via `log_event` to a local store, preserving the operation name, its fields and a
  timestamp.*
- **REQ-002 (Optional):** *Where observability persistence is enabled, the store shall be queryable by
  operation and by time range (enabling downstream aggregation).*
- **REQ-003 (Optional):** *Where observability persistence is enabled, the system shall capture all
  emitted event kinds, not a subset (no event type is silently dropped).*
- **REQ-004 (Unwanted):** *If observability persistence is not enabled, then the system shall create no
  store and shall behave exactly as today (stderr logging and redaction unchanged).*
- **REQ-005 (Ubiquitous):** *The system shall keep today's logging behaviour additive: the `log_event`
  contract is not changed in a breaking way and existing log consumers are unaffected.*
- **REQ-006 (State-driven):** *While an observed operation (index/search) is running, persisting its
  events shall not block it nor slow it measurably.*
- **REQ-007 (Unwanted):** *If persisting an event fails (store unwritable, corrupt or locked), then the
  observed operation shall continue unaffected and the failure shall be reported as a non-fatal
  warning (never an error of the observed operation).*
- **REQ-008 (Unwanted, privacy-by-default):** *If raw-text persistence is not explicitly enabled, then
  the store shall contain only metric/metadata fields and never raw content (e.g. query text).*
- **REQ-009 (Ubiquitous):** *The system shall apply the existing secret redaction to anything written
  to the store (no secret is persisted).*
- **REQ-010 (Ubiquitous):** *The observability persistence shall be provided behind a port whose
  concrete adapter is selected by the composition root from configuration, with lazy import, so the
  core requires no new mandatory dependency.*
- **REQ-011 (Optional):** *Where observability persistence is enabled, its activation and store
  location shall be governed by the centralised configuration (no hardcoded defaults in components),
  and a retention knob shall be foreseen (detail deferred — see Domande aperte).*
- **REQ-012 (Ubiquitous):** *The store location shall derive from configuration (host-agnostic) and the
  store shall be a regenerable, git-ignored artifact.*
- **REQ-013 (Event-driven):** *When events are appended across multiple runs or after a restart, the
  system shall not corrupt the archive (append is safe and non-destructive to prior events).*

## 6. Requisiti non funzionali
- **RNF-001 — Testabilità senza rete:** ogni requisito verificabile **offline** (store locale + eventi
  simulati), coerente con la CI senza cloud (Principio V).
- **RNF-002 — Overhead trascurabile e misurato:** a persistenza attiva, l'impatto sul percorso caldo
  (index/query) è misurato e trascurabile (scrittura non bloccante, RNF coerente con REQ-006).
- **RNF-003 — Retro-compatibilità:** persistenza spenta = comportamento odierno bit-per-bit (RNF
  coerente con REQ-004); default **conservativo**.
- **RNF-004 — Degrado non-fatale:** gli errori di persistenza non si propagano all'operazione osservata
  (coerente con la cache della feat. 019); il guasto è osservabile (warning).
- **RNF-005 — Dipendenze isolate (Principio III):** se l'adapter richiede una libreria, è un **extra**
  opzionale; il core resta senza nuove dipendenze obbligatorie (come gli extra `graph`/`rerank`).
- **RNF-006 — Osservabilità del proprio funzionamento (Principio IX):** l'attivazione/disattivazione e
  gli eventuali guasti dell'archivio sono essi stessi loggati (senza ricorsione patologica).

## 7. Vincoli, assunzioni e dipendenze
- **Additività:** lo strato si innesta sul `log_event` esistente **senza** romperne la firma né i
  consumatori (Principio I/IV).
- **Composition root:** l'adapter concreto si sceglie **solo** in `composition.py` da `Settings`
  (Principio I/VIII); import lazy (Principio III).
- **Sede gitignored:** l'archivio è un artefatto rigenerabile sotto una sede derivata da config (es.
  accanto all'indice, come la cache `embed_cache.sqlite` della feat. 019); git-ignored (Sicurezza).
- **Privacy condivisa:** il default *metriche-only* attua REQ-E8/E9 dell'epica (decisione 2026-06-14),
  principio condiviso con l'epica `memoria-conversazioni`.
- **Stato attuale favorevole:** oggi **nessun** evento porta testo di query/contenuto (verificato:
  `retrieve` logga solo collection/status/doc_type) → il default metriche-only è realizzabile **senza**
  filtrare nulla di esistente; serve una **classificazione** quando in futuro si introdurranno campi di
  contenuto (vedi DA-001).
- **Dipendenza a valle:** FEAT-002/003/004 presuppongono questo store; questa feature **non** dipende da
  loro.

## 8. Rischi
- **R-1 — Overhead sul percorso caldo:** scrittura sincrona durante index/query → mitigazione:
  non-bloccante/bufferizzata (REQ-006/RNF-002).
- **R-2 — Crescita dell'archivio:** senza retention cresce indefinito → manopola prevista (REQ-011),
  dettaglio in DA-O-b.
- **R-3 — Intercettazione fragile:** un meccanismo di cattura accoppiato male ai call-site potrebbe
  perdere eventi o rompere consumatori → requisiti neutri sul *come* (DA-O-f), vincolo di additività.
- **R-4 — Falso senso di "solo metriche":** se in futuro un evento porta contenuto senza
  classificazione, il default privacy verrebbe violato → DA-001 (classificazione dei campi).
- **R-5 — Ricorsione del logging:** loggare i guasti della persistenza tramite lo stesso canale →
  evitare loop (RNF-006).

## 9. Prioritizzazione (MoSCoW)
| Item | REQ | MoSCoW | Perché |
|---|---|---|---|
| Persistenza locale degli eventi | REQ-001/003 | **Must** | È la capacità stessa della feature |
| Interrogabilità per operation/tempo | REQ-002 | **Must** | Senza, FEAT-002 non esiste |
| Default off = nessuna regressione | REQ-004/RNF-003 | **Must** | Retro-compatibilità (epica REQ-E3) |
| Additività / non-breaking | REQ-005 | **Must** | Non rompere i consumatori (Principio I) |
| Non bloccante + degrado non-fatale | REQ-006/007 | **Must** | Non intrusiva (epica REQ-E7) |
| Privacy-by-default (solo metriche) + redazione | REQ-008/009 | **Must** | Principio privacy deciso (REQ-E8) |
| Porta + adapter da config, lazy | REQ-010/011/012 | **Must** | Architettura (Principi I/III/VIII/X) |
| Append sicuro tra run | REQ-013 | **Should** | Robustezza; il rebuild from-scratch è un'alternativa accettabile |
| Manopola di retention (solo il gancio) | REQ-011 | **Should** | Il dettaglio è DA-O-b |

## 10. Domande aperte
- **DA-O-f — Meccanismo di intercettazione (design, vincola questa feature):** [DA CHIARIRE in design/
  SpecKit: la cattura avviene via (i) un `logging.Handler` stdlib che instrada i record verso la porta
  (trasparente, zero modifiche ai call-site) o (ii) un'emissione esplicita verso la porta dentro
  `log_event`? Entrambe devono restare additive/non-breaking. I requisiti qui sono **neutri** sul
  meccanismo.]
- **DA-001 — Classificazione campo-metrica vs campo-contenuto:** [DA CHIARIRE: serve una policy che
  marchi quali campi sono "contenuto" (oggi: nessuno) per garantire REQ-008 quando si introdurranno
  campi di testo. Default proposto: allow-list di campi-metrica + tutto il resto trattato come
  contenuto (escluso di default).]
- **DA-O-b — Retention/rotazione (ereditata dall'epica):** [DA CHIARIRE: limite per tempo o dimensione,
  rotazione come il log? Qui si prevede solo la **manopola** (REQ-011); il valore/strategia è da fissare.]
- **DA-002 — Schema/formato dell'archivio:** [design: l'archivio è un DB locale (es. SQLite, simmetrico
  alla cache 019), un file di eventi, o altro? Materia di design; i requisiti restano agnostici.]
- *(DA-O-c "cosa rende live il TUI" appartiene a FEAT-003, non a questa feature.)*
