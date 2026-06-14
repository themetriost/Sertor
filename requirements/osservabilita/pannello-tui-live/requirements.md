# Requisiti — Pannello TUI: vista live

<!-- Deriva da: FEAT-003 (epica `requirements/osservabilita/epic.md`) -->

## 1. Contesto e problema (perché)

Sertor emette già eventi strutturati ricchi a ogni operazione tramite `log_event` in
`src/sertor_core/observability/logging.py` (riga 38). Questi eventi portano informazioni operative
essenziali — quanti documenti sono stati indicizzati, quanti token sono stati consumati, quante
hit/miss ha fatto la cache, se uno score è rimasto sotto soglia — ma sfuggono all'occhio umano:
vanno su stderr e si perdono a fine comando.

L'utente (owner, operatore di un progetto ospite) non ha attualmente nessun modo di rispondere a
domande elementari *durante* un'operazione: "l'indicizzazione è ancora in corso? quanti chunk ha
già processato? la cache sta funzionando?". Deve aspettare il ritorno del processo e leggere i log
a posteriori, se li ha conservati.

**FEAT-003 introduce la quarta superficie del core**: un pannello a terminale (TUI) che mostra lo
stato corrente del sistema e si aggiorna *mentre le operazioni sono in corso*, senza che l'utente
debba interrogare log, aprire altri tool o ricordare i numeri a memoria.

Come il [[server MCP]] (`src/sertor_mcp/server.py`) è un thin consumer del core per gli agenti
LLM, il pannello TUI è un thin consumer per l'operatore umano al terminale: legge le factory
pubbliche `build_*` del core, non reimplementa logica (Principio I). L'aggregazione dei dati
esposti appartiene a FEAT-002 (servizio di aggregazione/report); la persistenza degli eventi a
FEAT-001 (strato di osservabilità persistente). Questo pannello li *consuma*, non li produce.

> Il *come* (framework TUI, meccanismo di aggiornamento live, struttura del layout) è materia della
> **fase di design** a valle. Qui solo *cosa* e *perché*.

---

## 2. Obiettivi e criteri di successo

- **OB-1 — Stato corrente visibile in un colpo d'occhio:** l'utente apre il pannello e vede
  immediatamente: l'esito dell'ultimo index (quando, quanti documenti/chunk, dimensione embedding),
  il consumo corrente (token per provider), lo stato della cache (hit-rate attuale) e gli ultimi
  eventi/log tracciati.
  *SC-1:* un operatore che non ha mai visto il progetto apre il pannello e risponde correttamente
  a "quanti documenti sono stati indicizzati l'ultima volta?" e "quanti token ho consumato oggi?"
  senza aprire altri file o lanciare altri comandi.

- **OB-2 — Aggiornamento live durante le operazioni:** mentre un `index` o un `search` è in
  corso, il pannello mostra il progresso (nuovi eventi/log, contatori che avanzano) senza che
  l'utente debba fare nulla.
  *SC-2:* con un index in corso, un osservatore esterno che guarda il pannello vede lo stato
  cambiare almeno una volta prima che l'operazione sia completata.

- **OB-3 — Non intrusivo:** il pannello non altera, non rallenta e non perturba le operazioni
  che osserva.
  *SC-3:* il tempo medio di un index/search con il pannello aperto è statisticamente identico
  (dentro la varianza normale) a quello con il pannello chiuso.

- **OB-4 — Thin consumer architetturale:** il pannello non reimplementa logica di aggregazione
  né di retrieval; usa le factory e i dati già prodotti dal core (FEAT-001/002).
  *SC-4:* nessuna funzione di aggregazione o di retrieval è definita fuori da `src/sertor_core/`.

- **OB-5 — Testabilità senza terminale interattivo:** la logica di stato che alimenta il pannello
  è testabile in unit test senza un vero terminale (il rendering è separabile).
  *SC-5:* la suite CI (senza cloud, senza rete, senza TTY) contiene almeno N test sulla logica di
  stato del pannello che passano senza un framework TUI installato.

- **OB-6 — Host-agnostico:** il pannello funziona su qualunque progetto ospite che usi Sertor,
  senza modifiche al corpo del codice.
  *SC-6:* il pannello avviato su due ospiti diversi (es. Sertor stesso + un secondo repo) mostra
  i dati del rispettivo progetto con la sola differenza di configurazione.

---

## 3. Stakeholder e attori

- **Owner/operatore al terminale:** l'utente primario — vuole vedere cosa sta facendo Sertor,
  ora, senza aprire log o script.
- **Dev che integra Sertor in un progetto ospite:** vuole il pannello funzionante sul proprio
  progetto senza modificare il core.
- **FEAT-001 (strato di osservabilità persistente):** fornitore dei dati storici che il pannello
  può mostrare; il pannello è un consumatore a valle.
- **FEAT-002 (aggregazione/report):** fornitore delle aggregazioni (hit/miss, costo, conteggi)
  che il pannello espone in forma live; il pannello le legge, non le calcola.
- **Il core di Sertor** (`src/sertor_core/`): sorgente degli eventi, esposto via factory
  pubbliche `build_*`; il pannello è un thin consumer di queste factory.
- **CI/pipeline:** deve poter verificare la logica di stato del pannello senza TTY.

---

## 4. Ambito

### In ambito

- Un **pannello a terminale (TUI)** che mostra in modo live:
  - i dati dell'**ultimo index** (data/ora, numero di documenti indicizzati, numero di chunk,
    dimensione embedding);
  - il **consumo corrente** (token per provider);
  - lo **stato della cache** (hit-rate attuale, hits/misses totali);
  - gli **ultimi eventi/log** tracciati (stream scorrevole degli `operation` più recenti).
- **Aggiornamento in tempo reale**: il pannello si aggiorna mentre un'operazione è in corso
  (senza richiedere azione utente).
- L'**attivazione** e la **configurazione** del pannello via config centralizzata (sede, parametri
  di refresh).
- L'**isolamento** del framework TUI come extra opzionale `[tui]` (il core senza questa extra
  non acquisisce nuove dipendenze obbligatorie).
- La **separazione** tra logica di stato (testabile in unit test puri) e rendering (che richiede
  il framework TUI).
- Il rispetto del **vincolo di privacy**: mostra solo metriche persistite, mai contenuto grezzo
  (testo di query, trascrizioni) — coerente con REQ-E8 dell'epica.

### Fuori ambito

- **Logica di aggregazione**: calcolo di hit/miss, somme token, trend — delegato a **FEAT-002**.
- **Persistenza degli eventi**: scrivere lo store — delegato a **FEAT-001**.
- **Report sfogliabili** (viste storiche, tabelle hit/miss nel tempo, grafici costo) — delegati a
  **FEAT-004** (pannello TUI: report sfogliabili).
- **Web mode** (dashboard nel browser) — **FEAT-008**, Could, fuori da questa epica.
- **Export OpenTelemetry** — **FEAT-005**.
- **Stima costi in €** — **FEAT-007** (il pannello può mostrare il token count; la conversione €
  è competenza di FEAT-007).
- **Alerting/soglie/notifiche**: il pannello è read-only e non emette allarmi.
- La scelta del **framework TUI** (es. Textual, urwid, rich-live): decisione di design a valle.
- Il **meccanismo** con cui il pannello riceve gli aggiornamenti live: decisione di design a valle
  (vedi DA-O-c).

---

## 5. Requisiti funzionali (EARS)

### 5.1 Avvio e configurazione

- **REQ-001 (Optional):** *Where the TUI extra is installed, the system shall provide a command to
  start the live panel without arguments, reading its configuration from the centralised settings
  (no hardcoded paths or host-specific values).*

- **REQ-002 (Unwanted):** *If the TUI extra is not installed, then attempting to start the panel
  shall produce a clear, actionable message indicating which optional dependency is missing; the
  core shall remain unaffected.*

- **REQ-003 (Ubiquitous):** *The panel shall obtain all observability data through the core's
  public factories (`build_*`) and shall not read internal state, private modules or raw store
  files directly.*

### 5.2 Contenuto della vista live

- **REQ-004 (State-driven):** *While the panel is open, it shall display the data of the most
  recent index operation: its timestamp, the number of documents indexed, the number of chunks
  produced, and the embedding dimension used.*

- **REQ-005 (State-driven):** *While the panel is open, it shall display the current token
  consumption per provider (as reported by the observability layer).*

- **REQ-006 (State-driven):** *While the panel is open, it shall display the current cache
  state: hit count, miss count, and hit-rate (ratio), as exposed by the aggregation layer
  (FEAT-002).*

- **REQ-007 (State-driven):** *While the panel is open, it shall display a scrollable stream of
  the most recent structured events (operation name, key fields, timestamp) as they are recorded
  by the observability layer.*

- **REQ-008 (Unwanted, privacy-by-default):** *If raw-text persistence is not explicitly enabled,
  then the panel shall display only metric and metadata fields and shall never render raw content
  (e.g. query text, document excerpts) — consistent with REQ-E8 of the epic.*

### 5.3 Aggiornamento live

- **REQ-009 (Event-driven):** *When a new observability event is recorded during an in-progress
  operation (index or search), the panel shall reflect the updated state without requiring any
  user action.*

- **REQ-010 (State-driven):** *While an operation is running, the panel shall provide a visible
  indication that an operation is in progress (e.g. a status indicator or running counter).*

- **REQ-011 (Optional):** *Where a refresh-rate knob is configured, the panel shall honour it;
  where it is not configured, the panel shall use a sensible default that does not measurably
  affect the observed operation.*

  [DA CHIARIRE — DA-O-c: il requisito REQ-009 è intenzionalmente neutro sul meccanismo di
  aggiornamento. Non specifica se il pannello riceve eventi in push (tail/streaming del flusso di
  log), li recupera in pull (polling dello store di FEAT-001), o usa una combinazione dei due
  (flusso live + stato storico dallo store). Questa decisione appartiene al design: impatta la
  latenza percepita, il grado di accoppiamento tra il pannello e FEAT-001, e il comportamento
  quando la persistenza è disabilitata (vedi REQ-015). Il requisito specifica il *cosa* — l'utente
  vede lo stato aggiornarsi — non il *come*.]

### 5.4 Non-intrusività e robustezza

- **REQ-012 (Ubiquitous):** *The panel shall be read-only: it shall not trigger, modify or cancel
  any operation in the core.*

- **REQ-013 (State-driven):** *While the panel is reading observability data, it shall not block
  or measurably slow any ongoing core operation (index or search).*

- **REQ-014 (Unwanted):** *If the observability data source becomes temporarily unavailable (store
  locked, aggregation service unreachable), then the panel shall display the last known state with
  a visible staleness indicator and shall not crash or propagate errors to the core.*

- **REQ-015 (Optional):** *Where observability persistence (FEAT-001) is disabled, the panel
  shall operate on whatever live event stream is available and shall communicate clearly when
  historical data is absent.*

  [DA CHIARIRE — DA-O-c: questo requisito lascia aperta la domanda se il pannello possa funzionare
  *esclusivamente* sul flusso effimero (senza FEAT-001 attivo) o richieda necessariamente lo store.
  Se il meccanismo di aggiornamento live è *solo polling dello store*, il pannello senza FEAT-001
  non ha dati. Se è *tail/streaming*, può funzionare anche senza persistenza. La scelta è di
  design; il requisito specifica che il pannello deve *comunicare chiaramente* lo stato, qualunque
  sia il meccanismo.]

### 5.5 Thin consumer e isolamento

- **REQ-016 (Ubiquitous):** *The panel shall not define or reimplement any aggregation, retrieval
  or indexing logic; all computed values (hit-rate, token totals, chunk counts) shall be provided
  by FEAT-002 or by the core's existing services.*

- **REQ-017 (Ubiquitous):** *The TUI framework dependency shall be isolated as an optional extra
  `[tui]`; installing `sertor-core` without this extra shall not pull in any TUI library and shall
  not affect the core's import graph.*

- **REQ-018 (Ubiquitous):** *The panel's state model (the data objects describing what to display)
  shall be importable and testable without the TUI framework installed (the rendering layer is a
  separate concern).*

### 5.6 Host-agnosticità

- **REQ-019 (Ubiquitous):** *The panel shall derive its data source location and all configurable
  parameters from the centralised Settings, with no hardcoded host-specific paths or values
  (Principio X).*

- **REQ-020 (Ubiquitous):** *The panel shall work on any host project that has Sertor installed,
  without modifications to the panel's code — only configuration changes are permitted between
  hosts.*

---

## 6. Requisiti non funzionali

- **RNF-001 — Testabilità senza TTY:** la logica di stato del pannello (costruzione degli oggetti
  di vista, aggiornamento dei contatori, gestione degli eventi in arrivo) deve essere verificabile
  in unit test che girano in CI senza un terminale interattivo e senza il framework TUI installato
  (Principio V). Il rendering è l'unica parte non testabile in unit test puri.

- **RNF-002 — Non-intrusività misurabile:** il pannello aperto non deve introdurre overhead
  misurabile sulle operazioni di core (index/search). In assenza di dati a valle, il criterio
  conservativo è: nessuna operazione di I/O sincrona sul percorso caldo delle operazioni osservate.

- **RNF-003 — Avvio rapido:** il pannello deve diventare operativo entro un tempo percepito come
  immediato dall'utente umano (criterio qualitativo, da quantificare in design; riferimento
  comparativo: l'avvio del server MCP è ~1 s).

- **RNF-004 — Degrado non-fatale:** un errore nel pannello (rendering crash, evento malformato,
  sorgente dati assente) non si propaga al core e non termina le operazioni in corso (coerente con
  RNF-004 di FEAT-001 e con la cache della feat. 019).

- **RNF-005 — Dipendenze isolate (Principio III):** il core non acquisisce dipendenze
  obbligatorie dalla TUI; l'extra `[tui]` segue il pattern degli extra `[graph]` e `[rerank]`
  già esistenti (import lazy nel composition root).

- **RNF-006 — Compatibilità CI senza cloud:** il pannello deve essere verificabile in CI locale
  (senza rete, senza cloud, senza Azure) — marker `not cloud` (Principio V).

- **RNF-007 — Privacy-by-default strutturale:** il modello di stato del pannello deve rendere
  impossibile, per costruzione, il rendering di campi di contenuto grezzo in assenza di opt-in
  esplicito — non solo una guardia a runtime (Principio IX, REQ-E8 dell'epica).

---

## 7. Vincoli, assunzioni e dipendenze

- **Thin consumer (Principio I):** il pannello entra nel core esclusivamente dalle factory
  pubbliche `build_*` (come il server MCP in `src/sertor_mcp/server.py`); non legge adapter
  concreti, non accede a store interni, non importa da `adapters/` o `services/` direttamente.

- **Dipendenza da FEAT-001:** il pannello assume che un archivio di eventi sia disponibile (o
  almeno un flusso live, vedi DA-O-c). Se FEAT-001 è disabilitato, il pannello deve funzionare
  in modalità degradata (REQ-015) e comunicarlo.

- **Dipendenza da FEAT-002:** le aggregazioni esposte nel pannello (hit-rate, totali token,
  conteggi) sono prodotte dal servizio di aggregazione di FEAT-002; il pannello non le ricalcola.

- **Ordine di realizzazione:** FEAT-001 (store) e FEAT-002 (aggregazione) devono essere
  disponibili prima che il pannello possa mostrare dati storici aggregati. La vista sul flusso
  live effimero potrebbe essere realizzabile in anticipo (vedi DA-O-c).

- **Composition root (Principio I/VIII):** se il pannello richiede un adapter specifico (es. un
  reader dello store), la sua selezione avviene solo in `composition.py` da `Settings`; nessun
  import concreto fuori dal composition root.

- **Extra opzionale `[tui]` (Principio III):** import lazy nel composition root, identico agli
  extra `graph` e `rerank`. Un progetto ospite che non usa il pannello non trascina il framework
  TUI.

- **Store git-ignored (Sicurezza):** il pannello non crea né modifica artefatti persistenti; la
  sua configurazione non deve includere percorsi hardcoded.

- **Aggiornamenti degli eventi reali:** gli eventi oggi emessi da `log_event` sono:
  `index` (collection, provider, documents, chunks, embedding_dim, elapsed_ms),
  `embeddings` (provider, texts, tokens), `embeddings_cache` (hits, misses, total),
  `embeddings_error`, `embeddings_retry`, `low_confidence`, `retrieve` (collection, status,
  doc_type — senza testo della query), `config_no_env_found`. Il pannello deve mostrare
  almeno i campi di `index` ed `embeddings_cache`; per gli altri, la scelta dei campi visualizzati
  è di design.

- **Privacy condivisa:** la policy metriche-only (REQ-E8/E9 dell'epica, decisione 2026-06-14) è
  un vincolo architetturale condiviso con l'epica `memoria-conversazioni`; il pannello la eredita
  senza deroga.

---

## 8. Rischi

- **R-1 — Accoppiamento al meccanismo live (DA-O-c):** la scelta del meccanismo di aggiornamento
  (push vs poll vs ibrido) determina il grado di dipendenza del pannello da FEAT-001. Se il
  meccanismo è solo polling, il pannello non funziona senza lo store; se è streaming, può
  funzionare parzialmente in modalità effimera. La domanda è aperta e la risposta vincola i
  requisiti REQ-009 e REQ-015 in fase di design.

- **R-2 — Scope creep verso FEAT-004 (report):** il pannello live potrebbe espandersi verso
  grafici storici o tabelle di tendenza, che appartengono a FEAT-004. La linea di confine da
  mantenere: la vista live mostra lo *stato corrente*; i report mostrano il *trend storico*.

- **R-3 — Framework TUI costoso da mantenere:** una TUI ricca aggiunge superficie di manutenzione
  (layout, widget, eventi tastiera, compatibilità terminale). Mitigazione: il pannello resta
  minimo (stato corrente + stream eventi), guidato dai dati del core; i test di logica di stato
  sono indipendenti dal framework (RNF-001).

- **R-4 — Compatibilità terminale:** framework TUI diversi hanno compatibilità variabile con
  Windows Terminal, SSH, tmux, CI. La scelta del framework (design a valle) deve considerare
  questa variabilità.

- **R-5 — Overhead percepito:** anche un polling leggero, se su percorso caldo, può rallentare.
  La separazione fisica tra percorso di lettura del pannello e percorso di esecuzione delle
  operazioni è un vincolo architetturale (REQ-013/RNF-002).

- **R-6 — Stale display:** se la sorgente dati si interrompe silenziosamente, il pannello mostra
  dati stantii senza che l'utente se ne accorga. REQ-014 richiede un indicatore di stale esplicito.

---

## 9. Prioritizzazione (MoSCoW)

| Item | REQ/RNF | MoSCoW | Perché |
|---|---|---|---|
| Avvio da config centralizzata, host-agnostico | REQ-001, REQ-019, REQ-020 | **Must** | Non funziona senza (Principio X) |
| Messaggio chiaro se extra `[tui]` assente | REQ-002 | **Must** | DX base; allineato a `[graph]`/`[rerank]` |
| Accesso solo via factory `build_*` | REQ-003, REQ-016 | **Must** | Thin consumer (Principio I) |
| Vista dati ultimo index (quando/#doc/#chunk/dim) | REQ-004 | **Must** | È la domanda più frequente dell'operatore |
| Vista consumo token per provider | REQ-005 | **Must** | CS-3 dell'epica (report costo) |
| Vista stato cache (hit/miss/hit-rate) | REQ-006 | **Must** | CS-2 dell'epica (report cache) |
| Stream ultimi eventi/log | REQ-007 | **Must** | OB-2; è il segnale "cosa sta facendo ora" |
| Privacy-by-default (solo metriche) | REQ-008, RNF-007 | **Must** | REQ-E8 epica, decisione 2026-06-14 |
| Aggiornamento live senza azione utente | REQ-009 | **Must** | CS-4 dell'epica (pannello live) |
| Indicatore visivo operazione in corso | REQ-010 | **Must** | Segnale essenziale per l'operatore |
| Extra `[tui]` isolato, import lazy | REQ-017, RNF-005 | **Must** | Principio III; no regressione core |
| Modello di stato testabile senza TTY | REQ-018, RNF-001 | **Must** | CI senza cloud (Principio V) |
| Non-intrusività (read-only, no overhead) | REQ-012, REQ-013, RNF-002 | **Must** | REQ-E7 epica |
| Degrado non-fatale se sorgente assente | REQ-014 | **Must** | Robustezza; allineato a policy cache |
| Modalità degradata se FEAT-001 disabilitato | REQ-015 | **Should** | Dipende da DA-O-c |
| Refresh-rate configurabile | REQ-011 | **Should** | Flessibilità; non critico per l'MVP |
| Avvio rapido (< soglia percettiva) | RNF-003 | **Should** | DX; non bloccante per la prima release |
| Compatibilità CI senza cloud | RNF-006 | **Must** | Nessuna eccezione (Principio V) |

---

## 10. Domande aperte

- **DA-O-c — Cosa rende la vista "live" (CENTRALE, blocca il design):**
  [DA CHIARIRE: il pannello riceve gli aggiornamenti tramite (i) tail/streaming del flusso di log
  in tempo reale (push), (ii) polling periodico dello store di FEAT-001 (pull), o (iii) entrambi
  (flusso live per la latenza percepita + storico dallo store per il contesto)? Questa scelta
  determina: la latenza percepita dell'aggiornamento, il grado di accoppiamento a FEAT-001, e se
  il pannello può funzionare *senza* FEAT-001 attivo (solo flusso effimero). I requisiti REQ-009
  e REQ-015 sono intenzionalmente neutri sul meccanismo: specificano il *cosa* (l'utente vede lo
  stato aggiornarsi; il pannello comunica l'assenza di dati storici) senza vincolare il *come*.
  Default proposto: la scelta migliore dipende dall'architettura di FEAT-001 — da risolvere in
  design congiunto FEAT-001+FEAT-003.]

- **DA-O-c-bis — Pannello live senza FEAT-001 attivo:**
  [DA CHIARIRE: se la persistenza (FEAT-001) è disabilitata, il pannello può mostrare almeno il
  flusso live effimero degli eventi correnti (senza storico), oppure richiede necessariamente lo
  store? La risposta dipende da DA-O-c: meccanismo streaming → sì (dati live senza store);
  meccanismo polling → no (senza store nulla da mostrare). Segnalato in REQ-015.]

- **DA-F-001 — Framework TUI (design):**
  [DA CHIARIRE in design: quale framework TUI usare? (es. Textual, rich-live, urwid, blessed, …).
  I fattori rilevanti: compatibilità Windows Terminal / SSH / tmux, licenza, superficie di API da
  mantenere, possibilità di testare il modello di stato senza il framework. I requisiti non lo
  vincolano. La scelta diventa un vincolo architetturale non appena si sceglie.]

- **DA-F-002 — Refresh rate di default:**
  [DA CHIARIRE: quale intervallo di aggiornamento usare come default se non configurato (REQ-011)?
  Troppo frequente → overhead; troppo rado → latenza percepita elevata. Default proposto: 1-2 s
  come punto di partenza (da misurare); la manopola `SERTOR_TUI_REFRESH_MS` (o simile) rende il
  valore configurabile. La definizione del nome della variabile è di design.]

- **DA-F-003 — Scope dei campi di evento mostrati:**
  [DA CHIARIRE: il pannello mostra tutti i campi di ogni evento nello stream (REQ-007), o solo
  un sottoinsieme scelto per leggibilità? Default proposto: mostrare operation + timestamp +
  i campi "chiave" per tipo (es. per `index`: documents/chunks; per `embeddings_cache`:
  hits/misses/total); il dettaglio completo su espansione/selezione. Questa è principalmente
  una scelta di UX/design, ma la lista di campi "chiave" per tipo di evento deve essere
  dichiarata nei requisiti di FEAT-004 o in un ADR a monte.]

- **DA-O-b (ereditata dall'epica) — Retention dello store:**
  [Appartiene primariamente a FEAT-001; il pannello non gestisce retention ma ne mostra il
  risultato. Se lo store è vuoto per rotazione, il pannello mostra uno stato "nessun dato storico"
  — non è un caso di errore.]
