# Epica — Osservabilità e pannello di controllo

> Livello: **epica**. Rende Sertor **trasparente sul proprio funzionamento** — log, costo, salute del
> corpus, efficacia della cache — con i numeri **persistiti** (oggi si perdono) e un **pannello da
> terminale (TUI)** che li mostra live e ne fa report. Si decompone in
> `requirements/osservabilita/<feature>/requirements.md` (EARS).
>
> Relazione con le altre epiche: il **core** (`sertor-core`) acquisisce uno strato di osservabilità
> persistente; il **pannello** è una nuova **superficie sottile** accanto a libreria/CLI/MCP (come per
> l'epica `sertor-cli`). Questa epica **matura** l'idea di backlog «logging come strategia runtime» e
> **assorbe** i Could **REQ-H9** (tracing/OTel) e **REQ-H10** (metriche aggregate) dell'hardening
> (`../sertor-core/hardening-produzione/`).

## 1. Visione e problema (perché)

Sertor **già** emette log strutturati ricchi a ogni operazione (via `log_event` in
`src/sertor_core/observability/logging.py`): `index`, `embeddings` (con token, feat. 019),
`embeddings_cache` (hits/misses/total, feat. 019), `embeddings_error`, `embeddings_retry`,
`low_confidence` (feat. 018), eventi di ricerca/rerank, `config_no_env_found`. Ma questi log sono
**effimeri**: vanno su stderr e **si perdono a fine comando**. Conseguenza: non si può rispondere a
domande banali ma essenziali — *quanto sto spendendo? quanto mi fa risparmiare la cache nel tempo?
quanto è fresco il corpus? quante query restano senza risposta?* — senza ricostruirle a mano.

Il valore dell'epica è duplice e ricalca due strati:

1. **Memoria dell'osservabilità (nel core):** dare agli eventi un **luogo dove restano** e un modo per
   **interrogarli** (aggregazioni/report). È il prerequisito di qualunque report storico.
2. **Un pannello da terminale (la superficie):** una **TUI** che mostra lo stato **live** e produce
   **report** (hit/miss della cache nel tempo, costo, salute del corpus), senza reimplementare logica
   (è un *thin consumer* del core, come il server MCP).

> Il *come* (stack, schema dello store, struttura del codice) è materia della **fase di design** a
> valle. Qui solo *cosa* e *perché*.

## 2. Ambito

### In ambito
- **Persistenza degli eventi** di osservabilità che il core già emette, in un archivio **locale**
  interrogabile, **senza** rompere i consumatori attuali del logging (additivo).
- **Aggregazione/report** su quegli eventi: hit/miss della cache, costo (token e stima €), conteggi
  del corpus, latenze, tassi di errore/astensione.
- **Pannello TUI** (terminale): vista **live** (stato corrente, ultimi eventi) + **report** sfogliabili.
- **Export OpenTelemetry** (opzionale) verso backend esterni (Langfuse/Phoenix/Grafana), per chi li usa
  già — *senza* incorporarli (nessun vincolo di licenza su Sertor).
- **Configurabilità** dell'osservabilità (attiva/disattiva, dove persiste) via la config centralizzata.
- **Portabilità**: il pannello e lo strato di osservabilità funzionano su **qualunque progetto ospite**
  (non solo su Sertor), coerenti col Principio X.

### Fuori ambito
- **Web GUI** (dashboard servita nel browser): rinviata a una fase successiva (Could/fase 2).
- **Metriche di qualità/eval della pertinenza** (rilevanza del contesto, groundedness à la TruLens/Ragas):
  collegate al Principio V e a un ground-truth; epica/feature separata.
- **Roll-up cross-progetto** (metriche di flotta, confronto fra più Sertor): è il
  [[second-brain-cross-progetto]] (Meta-Sertor), fuori da questa epica.
- **Alerting/notifiche** e SLO/allarmi automatici.
- Definizione del *come* (stack TUI, schema dello store, formato OTel): fase di **design**.
- Scelta della **licenza** di Sertor (decisione di governance tracciata a parte): non è un requisito di
  questa epica, ma l'export OTel è progettato per **non** vincolarla.

## 3. Criteri di successo
<!-- misurabili e tech-agnostici -->
- **CS-1 (persistenza):** con l'osservabilità attiva, dopo **N** operazioni (index/ricerche) gli eventi
  corrispondenti sono **recuperabili** da un archivio interrogabile (verificabile: il numero di eventi
  persistiti ≥ numero di operazioni svolte).
- **CS-2 (report cache):** è possibile produrre un report **hit/miss della cache nel tempo** e il
  relativo **risparmio cumulativo** (token, e opzionalmente €) **senza strumenti esterni**.
- **CS-3 (report costo):** è possibile vedere il **consumo cumulativo** (token per provider) e una
  stima di costo, aggregati per intervallo (es. per giorno / per re-index).
- **CS-4 (pannello live):** il pannello TUI mostra lo **stato corrente** (ultimo index, #doc/#chunk,
  stato cache, ultimi eventi) e si **aggiorna** mentre un'operazione è in corso.
- **CS-5 (nessuna regressione):** con l'osservabilità **disattivata** (default conservativo) il
  comportamento e le prestazioni sono **identici a oggi**; attiva, l'overhead sul percorso caldo
  (index/query) è **trascurabile e misurato**.
- **CS-6 (host-agnostico):** il pannello e lo strato di osservabilità operano su **≥2** progetti ospite
  diversi (Sertor stesso + un secondo repo) **senza modifiche al corpo** del codice (solo config).
- **CS-7 (export opzionale):** quando l'export OTel è configurato, gli eventi sono visibili in un
  backend esterno standard; quando **non** lo è, nulla cambia e nessuna dipendenza esterna è richiesta.

## 4. Stakeholder e attori
- **Owner/maintainer (tu):** osserva costo, cache, salute del corpus; usa il pannello per diagnosi.
- **Operatore/dev di un progetto ospite:** vuole capire quanto costa indicizzare e quanto rende la cache.
- **Team/SRE (futuro):** collega Sertor al proprio stack di osservabilità (OTel → Langfuse/Grafana).
- **Agente LLM:** indirettamente — un'osservabilità migliore rende il sistema più diagnosticabile, ma
  l'agente non è il consumatore primario del pannello.
- **Il core di Sertor:** sorgente degli eventi (`log_event`); l'osservabilità ne è un consumatore.

## 5. Vincoli, assunzioni e dipendenze
- **Additività (non-breaking):** lo strato di osservabilità si innesta sul `log_event` esistente
  **senza** cambiare la firma né rompere i consumatori odierni (Principio I/IV).
- **Thin consumer:** il pannello **non** reimplementa logica — legge il core dalle factory `build_*`
  (Principio I); le aggregazioni vivono nel core, non nella TUI.
- **Local-first & host-agnostico:** funziona interamente in locale e su qualunque ospite; ciò che varia
  per ospite sta in **config**, non nel corpo (Principi II/X).
- **Dipendenze isolate:** il framework TUI (es. tipo Textual) è un **extra opzionale** (`[tui]`) e
  l'export OTel un extra opzionale (`[otel]`); il **core resta senza nuove dipendenze obbligatorie**
  (Principio III), coerente con gli extra `graph`/`rerank` già esistenti.
- **Store locale gitignored:** l'archivio degli eventi è un artefatto rigenerabile → git-ignored
  (sezione Sicurezza della costituzione), simmetrico alla cache della feat. 019 (SQLite locale).
- **Nessun segreto persistito:** la redazione segreti già presente nel logging si applica anche allo
  store (Principio IX / REQ-032).
- **Default conservativo:** l'osservabilità persistente è **opt-in** (o comunque a impatto nullo da
  spenta), per non cambiare il comportamento odierno.
- **Dipendenza dalle feat. 018/019:** gli eventi `low_confidence`, `embeddings`, `embeddings_cache`
  (già su master) sono la materia prima dei report; questa epica li **consuma**, non li ridefinisce.

## 6. Rischi
- **R-1 — Overhead sul percorso caldo:** persistere eventi durante index/query può rallentare; va
  misurato e reso trascurabile (scrittura asincrona/bufferizzata, mai bloccante).
- **R-2 — Crescita/retention dello store:** senza politica di rotazione l'archivio cresce indefinito
  (come per la cache); serve una strategia di retention.
- **R-3 — Privacy:** alcuni eventi potrebbero contenere il **testo delle query** (potenzialmente
  sensibile); va deciso se persisterlo e con quale opt-in (vedi Domande aperte).
- **R-4 — Stima costi fragile:** i **prezzi** dei provider cambiano; una stima € hardcoded invecchia.
- **R-5 — Scope creep verso una piattaforma di osservabilità:** il rischio di reimplementare
  Langfuse/Grafana. Mitigazione: pannello **essenziale** + export OTel per i casi avanzati.
- **R-6 — Manutenzione TUI:** una TUI ricca è codice d'interfaccia da mantenere; tenerla sottile e
  guidata dai dati del core.

## 7. Requisiti trasversali (EARS)
<!-- solo i pochi requisiti davvero trasversali a tutta l'epica -->
- **REQ-E1 (Optional):** *Where observability persistence is enabled, the system shall persist the
  structured events it already emits to a locally queryable store, without altering existing logging
  behaviour or breaking current log consumers.*
- **REQ-E2 (Ubiquitous):** *The control panel shall consume the core through its public factories and
  shall not reimplement retrieval, indexing or aggregation logic (thin consumer).*
- **REQ-E3 (Unwanted):** *If observability persistence is disabled, then the system shall behave
  exactly as today, with no measurable overhead and no store created.*
- **REQ-E4 (Optional):** *Where an OpenTelemetry exporter is configured, the system shall emit its
  observability events to the external backend in addition to (not instead of) the local store.*
- **REQ-E5 (Unwanted):** *If an event field is a secret, then the system shall not persist it in the
  store (the existing redaction applies to persistence too).*
- **REQ-E6 (Ubiquitous):** *The panel and the observability layer shall operate on any host project
  without changes to their body — only configuration (Principio X).*
- **REQ-E7 (State-driven):** *While an operation (index/search) is running, persisting its events shall
  not block or measurably slow the operation (non-blocking observability).*
- **REQ-E8 (Unwanted, privacy-by-default):** *If raw-text persistence is not explicitly enabled, then
  the system shall persist only metrics (no query text, no transcripts) — content is never stored by
  default.* (Decisione DA-O-d, 2026-06-14.)
- **REQ-E9 (Optional, layered opt-in):** *Where raw-text persistence is enabled, the system shall
  persist the content with secret-pattern scrubbing applied and a configurable retention; and where
  semantic (embedding-based) search over that content is enabled, embedding that content shall be a
  further, separate opt-in (the local full-text path keeps content on-machine).*

## 8. Backlog di feature

> Due strati: **A. Osservabilità nel core** (la memoria + i report) · **B. Il pannello** (la superficie).

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Strato di osservabilità persistente nel core** — porta di osservabilità + adapter di persistenza (archivio locale) che cattura gli eventi già emessi da `log_event`; additivo e non-breaking. Matura il backlog «logging come strategia runtime» | La **memoria** senza cui non esistono report storici | **Must** | [decomposta](strato-osservabilita-persistente/requirements.md) **(2026-06-14)** |
| FEAT-002 | **Servizio di aggregazione/report** — interroga lo store per produrre report: hit/miss della cache nel tempo, costo (token), conteggi del corpus, latenze, tassi di errore/astensione | Trasforma gli eventi grezzi in **risposte** alle domande chiave | **Must** | [decomposta](aggregazione-report/requirements.md) **(2026-06-14)** |
| FEAT-003 | **Pannello TUI — vista live** — superficie a terminale che mostra lo stato corrente (ultimo index, #doc/#chunk, consumo, stato cache, ultimi eventi/log tracciati) e si aggiorna durante le operazioni | La superficie richiesta: *vedere* cosa fa Sertor, ora | **Must** | [decomposta](pannello-tui-live/requirements.md) **(2026-06-14)** |
| FEAT-004 | **Pannello TUI — report sfogliabili** — viste di report dentro la TUI: hit/miss nel tempo, costo/consumo, salute del corpus, freschezza | I **report** richiesti (missing vs hit & co.) senza strumenti esterni | **Must** | [decomposta](pannello-tui-report/requirements.md) **(2026-06-14)** |
| FEAT-005 | **Export OpenTelemetry** (GenAI semantic conventions) — emette gli eventi anche verso un backend OTel esterno; extra opzionale `[otel]`. **Assorbe REQ-H9** dell'hardening | Ponte verso lo stack enterprise (Langfuse/Phoenix/Grafana) senza vincoli di licenza | **Should** | da decomporre |
| FEAT-006 | **Metriche aggregate esposte** (es. latenza p95/p99, cache-hit rate, throughput). **Assorbe REQ-H10** dell'hardening | Numeri di salute pronti per dashboard/monitoraggio | **Should** | da decomporre |
| FEAT-007 | **Stima costi in €** — converte i token in una stima di spesa per provider (tabella prezzi in config aggiornabile) | Rende il costo **leggibile** in valuta, non solo in token | **Should** *(alzata da Could, DA-O-g, 2026-06-14)* | da decomporre |
| FEAT-008 | **Web mode** — dashboard servita in locale nel browser, sopra lo stesso strato di osservabilità | Grafici ricchi per chi li preferisce al terminale | **Could** | da decomporre |
| FEAT-009 | **Trend di qualità del retrieval** — andamento di `low_confidence` (astensioni), query a vuoto, distribuzione degli score | Primo passo verso la qualità (non solo costo), senza un eval completo | **Could** | da decomporre |
| FEAT-010 | **Metriche del code-graph e del wiki** — #nodi/#archi e copertura per linguaggio; #pagine, orfani/link rotti, stato *pending vs clean* (dal lint) | Estende l'osservabilità alle due capacità ortogonali | **Could** | da decomporre |

> **Nota sull'MVP (Must):** la prima release utile è **FEAT-001 → FEAT-004**: persistere gli eventi,
> aggregarli, e una TUI che mostra live **e** fa il report hit/miss + costo. La **stima € (FEAT-007,
> Should)** è attesa **accanto al report costo** (DA-O-g): i token grezzi da soli sono poco leggibili.
> Export OTel e metriche aggregate (Should) seguono; web, qualità e graph/wiki (Could) dopo.

> **Confine con l'hardening:** REQ-H9 (tracing distribuito) e REQ-H10 (metriche aggregate), oggi Could
> in `../sertor-core/hardening-produzione/`, sono **ricollocati** qui come FEAT-005 e FEAT-006 — non si
> duplicano: in fase di decomposizione si aggiornerà il banner del requirement di hardening.

## 9. Domande aperte
<!-- ogni punto irrisolto resta [DA CHIARIRE: domanda] -->
- **DA-O-a — Stima prezzi €:** [DA CHIARIRE: la tabella prezzi per provider va *hardcoded* (semplice
  ma invecchia), messa in **config aggiornabile** dall'utente, o versionata come dato del repo? — i
  prezzi cambiano spesso. Default proposto: config aggiornabile con valori di default versionati.]
- **DA-O-b — Retention/rotazione dello store:** [DA CHIARIRE: quanto storico conservare e con quale
  limite (per tempo? per dimensione? rotazione come il log?). Default proposto: rotazione configurabile,
  conservativa.]
- **DA-O-c — Cosa rende il TUI "live":** [DA CHIARIRE: la vista live legge **tailando** il flusso di
  log, fa **polling** dello store, o entrambi? Impatta latenza percepita e accoppiamento.]
- **DA-O-d — Privacy del testo delle query:** ✅ **RISOLTA (2026-06-14, utente):** **privacy-by-default a
  strati** (vedi REQ-E8/E9). Default = **solo metriche**; persistere il testo (query e, nell'epica
  gemella, trascrizioni) = **opt-in** esplicito; la ricerca **semantica** (che embedda → manda al
  provider) = **opt-in ulteriore** (di default full-text locale). + scrub dei segreti nel testo +
  retention configurabile. Principio condiviso con l'epica **memoria conversazioni**.
- **DA-O-e — Confine col fleet/second-brain:** confermato **fuori scope** il roll-up cross-progetto
  (→ [[second-brain-cross-progetto]]); lo store resta **per-progetto**. [DA CHIARIRE solo se in futuro
  si vorrà un formato compatibile con un'aggregazione di flotta.]
- **DA-O-f — Innesto sul `log_event` esistente:** [DA CHIARIRE in design: come la porta di osservabilità
  intercetta gli eventi (handler sul logging stdlib? emissione esplicita verso la porta?) restando
  additiva e non-breaking. È materia di design, ma la scelta vincola FEAT-001.]
- **DA-O-g — Priorità della stima €:** ✅ **RISOLTA (2026-06-14, utente):** la **stima € sale a Should**
  ed è attesa **accanto al report costo** dell'MVP (FEAT-007, vedi §8). I prezzi vivono in **config
  aggiornabile** (DA-O-a, default proposto confermato).

## 10. Riferimenti (prior art, non requisiti)
- **Osservabilità LLM/RAG:** Langfuse (core MIT, cost/token tracking incl. embeddings), Arize Phoenix
  (Elastic License 2.0, debug del retrieval), TruLens/Ragas (qualità RAG — fuori scope qui).
- **Costo/token:** Tokdash, OpenObserve.
- **UX TUI:** Toolong (log viewer), dolphie (single-pane real-time), harlequin (SQL TUI su SQLite),
  k9s/lazygit (navigazione da tastiera).
- **Standard:** OpenTelemetry GenAI semantic conventions (base di FEAT-005).
- **Backlog correlati:** «logging come strategia runtime» (roadmap) → maturato qui; REQ-H9/H10
  dell'hardening → ricollocati in FEAT-005/006; licenza di Sertor → decisione di governance a parte
  (l'export OTel non la vincola).
