# Requisiti — Pannello TUI: report sfogliabili

<!-- Deriva da: FEAT-004 (epica `requirements/osservabilita/epic.md`) -->

## 1. Contesto e problema (perché)

Il pannello TUI è la **superficie** che rende visibili i dati di osservabilità direttamente dal
terminale. FEAT-003 copre la **vista live** (stato corrente in tempo reale); questa feature (FEAT-004)
aggiunge le **viste di report** — navigabili da tastiera — che rispondono alle domande storiche
essenziali: *quanto mi fa risparmiare la cache nel tempo? quanto sto spendendo? il corpus è sano?
quando è stato indicizzato l'ultima volta?*

Il **servizio di aggregazione/report (FEAT-002)** è la fonte degli aggregati: calcola hit/miss,
consumo di token, conteggi corpus, freschezza, e li espone come oggetti interrogabili. FEAT-004 li
**rende** nella TUI, senza ricalcolarli. È un **thin consumer** (vedi `wiki/concepts/thin-consumer.md`)
nel senso più stretto: tutta la logica di aggregazione vive nel core (FEAT-002), il pannello traduce
i risultati in una vista testuale navigabile.

Senza questa feature il valore della persistenza (FEAT-001) e dell'aggregazione (FEAT-002) resterebbe
accessibile solo via API programmatica o strumenti esterni; con essa diventa consultabile in pochi
tasti nel terminale, senza uscire dal workflow di sviluppo.

> Il *come* (framework TUI, schema delle viste, layout, formato tabelle/sparkline) è materia della
> **fase di design** a valle. Qui solo *cosa* e *perché*.

## 2. Obiettivi e criteri di successo

- **OB-1 — Report cache accessibile da terminale:** l'utente può vedere, dentro la TUI, la serie
  storica di hit/miss della cache di embedding e il risparmio cumulativo in token.
  *SC-1:* il report cache è raggiungibile da tastiera in ≤ 3 tasti dalla schermata principale della
  TUI e mostra dati reali dallo store dell'osservabilità.
- **OB-2 — Report costo/consumo accessibile da terminale:** l'utente può vedere il consumo cumulativo
  di token per provider, aggregato per intervallo, e — dove FEAT-007 è presente — la stima in €.
  *SC-2:* il report costo mostra i token (sempre) e la stima € (solo se FEAT-007 è attiva); la
  degradazione onesta (token senza €) è visibile e non causa errori né crash.
- **OB-3 — Report salute corpus accessibile da terminale:** l'utente può vedere il numero di documenti
  e chunk indicizzati, con breakdown disponibile.
  *SC-3:* il report salute mostra #doc/#chunk aggiornati all'ultimo indice.
- **OB-4 — Report freschezza accessibile da terminale:** l'utente può vedere da quanto tempo non si
  re-indicizza il corpus.
  *SC-4:* il report freschezza mostra l'istante dell'ultimo indice e l'età in unità leggibili.
- **OB-5 — Navigazione e selezione temporale:** l'utente può sfogliare le viste di report e
  filtrare per intervallo temporale senza uscire dalla TUI.
  *SC-5:* le viste di report sono selezionabili da tastiera e ammettono almeno due intervalli
  temporali preimpostati (es. ultima ora / ultime 24 ore / ultima settimana).
- **OB-6 — Testabilità offline:** tutta la logica delle viste è verificabile in CI senza rete né
  terminale interattivo.
  *SC-6:* i test delle viste passano con dati aggregati sintetici, senza una TUI interattiva attiva.

## 3. Stakeholder e attori

- **Owner/operatore del progetto ospite:** consulta i report per diagnosticare costi, efficacia della
  cache e stato del corpus senza strumenti esterni.
- **Developer in locale:** interroga la TUI durante una sessione di sviluppo RAG.
- **FEAT-002 (servizio di aggregazione/report):** sorgente dei dati che il pannello rende; FEAT-004 ne
  è il consumatore a valle. FEAT-002 deve essere disponibile perché FEAT-004 abbia dati da mostrare.
- **FEAT-003 (vista live):** stessa app TUI, stessa navigazione di base; FEAT-004 aggiunge le viste
  di report alla medesima applicazione.
- **FEAT-007 (stima costi in €):** sorgente opzionale della colonna €; quando presente, viene esposta
  nel report costo; quando assente, il report mostra solo token (degradazione onesta).
- **FEAT-001 (strato di osservabilità persistente):** lo store che alimenta FEAT-002 e quindi FEAT-004;
  se la persistenza è spenta, i report sono vuoti o non disponibili.

## 4. Ambito

### In ambito

- **Vista report cache:** serie storica hit/miss degli embedding, risparmio cumulativo in token,
  filtrabile per intervallo temporale.
- **Vista report costo/consumo:** token consumati per provider per intervallo, con stima € se FEAT-007
  è attiva.
- **Vista report salute corpus:** #doc, #chunk, breakdown disponibile, riferiti all'ultimo indice.
- **Vista report freschezza:** istante dell'ultimo re-indice e anzianità del corpus.
- **Navigazione da tastiera** fra le viste di report e selezione dell'intervallo temporale.
- **Degradazione onesta** quando una sorgente è assente (FEAT-007 non attiva, FEAT-001 disabilitata,
  FEAT-002 non disponibile): messaggio esplicito, non crash né dato silenziosamente omesso.
- **Integrazione nell'app TUI di FEAT-003:** stessa applicazione, stessa navigazione di base; le viste
  di report sono una sezione aggiuntiva, non una app separata.
- **Testabilità isolata** della logica delle viste (separazione logica-vista da rendering TUI).

### Fuori ambito

- **Calcolo degli aggregati:** compete a FEAT-002; FEAT-004 non reimplementa logica di aggregazione.
- **Vista live (stato corrente, ultimi eventi):** è FEAT-003.
- **Export di un report** (CSV, Markdown, ecc.): Could; non è nel perimetro MVP di questa feature.
- **Web dashboard** (browser): è FEAT-008 dell'epica.
- **Metriche del code-graph o del wiki:** è FEAT-010 dell'epica.
- **Trend di qualità del retrieval (low_confidence, distribution score):** è FEAT-009 dell'epica.
- **Metriche aggregate esposte via API** (p95/p99 latenza, throughput): è FEAT-006.
- **Export OpenTelemetry:** è FEAT-005.
- **Configurazione dei prezzi per la stima €:** compete a FEAT-007.
- **UX dettagliata** (layout, sparkline vs tabelle, palette colori): materia di design a valle.

## 5. Requisiti funzionali (EARS)

### Vista report cache

- **REQ-001 (Optional):** *Where observability persistence (FEAT-001) and the aggregation service
  (FEAT-002) are available, the TUI panel shall present a cache report view showing, for the selected
  time range, the total number of embedding cache hits, misses and the cumulative token saving
  attributable to cache hits.*

- **REQ-002 (Optional):** *Where the cache report view is active, the panel shall allow the user to
  select a time range from a set of presets (covering at least: last hour, last 24 hours, last 7 days)
  using keyboard input, and shall refresh the displayed data accordingly.*

- **REQ-003 (Unwanted):** *If no cache events are recorded in the selected time range, then the panel
  shall display an explicit "no data for this period" message and shall not display zeroes as if data
  were present.*

### Vista report costo/consumo

- **REQ-004 (Optional):** *Where observability persistence (FEAT-001) and the aggregation service
  (FEAT-002) are available, the TUI panel shall present a cost/consumption report view showing the
  cumulative token count per provider for the selected time range.*

- **REQ-005 (Optional):** *Where cost estimation (FEAT-007) is active, the cost report view shall
  additionally display the estimated monetary cost (€) alongside the token count.*

- **REQ-006 (Unwanted):** *If cost estimation (FEAT-007) is not active, then the cost report view
  shall display an explicit notice that the monetary estimate is unavailable, and shall show only
  the token count without omitting it silently or raising an error.*

### Vista report salute corpus

- **REQ-007 (Optional):** *Where observability persistence (FEAT-001) and the aggregation service
  (FEAT-002) are available, the TUI panel shall present a corpus-health report view showing the
  document count (#doc), chunk count (#chunk) and any available breakdown from the last indexing
  run.*

- **REQ-008 (Unwanted):** *If no indexing event is recorded in the store, then the corpus-health
  view shall display an explicit "never indexed" or "no data" message instead of showing zeroes.*

### Vista report freschezza

- **REQ-009 (Optional):** *Where observability persistence (FEAT-001) and the aggregation service
  (FEAT-002) are available, the TUI panel shall present a freshness report view showing the timestamp
  of the last indexing run and the elapsed time since then expressed in human-readable units (e.g.
  "3 days ago").*

- **REQ-010 (Unwanted):** *If no indexing event has been recorded, then the freshness view shall
  display an explicit "corpus never indexed" message and shall not display a misleading elapsed time.*

### Navigazione e struttura

- **REQ-011 (Ubiquitous):** *The report views shall be reachable from the TUI panel's main navigation
  using keyboard input only, without requiring a pointing device.*

- **REQ-012 (Ubiquitous):** *The report views (cache, cost, corpus health, freshness) shall be
  navigable as distinct, selectable sections within the same TUI application used by FEAT-003 (live
  view), sharing its navigation conventions.*

- **REQ-013 (Event-driven):** *When the user selects a different time range preset, the panel shall
  request updated report data from the aggregation service (FEAT-002) and refresh the displayed
  content without restarting the application.*

### Degradazione onesta e disponibilità

- **REQ-014 (Unwanted):** *If observability persistence (FEAT-001) is disabled or FEAT-002 is
  unavailable, then the report views shall display an explicit message stating that reports are
  unavailable (persistence is off or aggregation service not reachable), and shall not crash nor
  display stale or empty data without explanation.*

- **REQ-015 (Unwanted):** *If the aggregation service (FEAT-002) returns a partial result (some
  report kinds available, others not), then the panel shall render the available views normally and
  display a per-view notice for those that are unavailable, rather than failing the entire panel.*

### Thin consumer e privacy

- **REQ-016 (Ubiquitous):** *The report views shall consume data exclusively from the aggregation
  service (FEAT-002) public interface and shall not perform any aggregation or computation on raw
  events directly (thin consumer — REQ-E2 of the epic).*

- **REQ-017 (Ubiquitous):** *The panel shall display only pre-aggregated metrics as supplied by
  FEAT-002 and shall never display raw query text, transcripts or content fields (privacy — REQ-E8
  of the epic).*

## 6. Requisiti non funzionali

- **RNF-001 — Testabilità senza rete e senza terminale interattivo:** la logica delle viste (formattazione
  dei dati aggregati ricevuti da FEAT-002, selezione dell'intervallo, messaggeria di degradazione) deve
  essere verificabile con dati sintetici e senza istanziare un terminale interattivo. Il rendering TUI
  è separabile dalla logica di vista (coerente con Principio V e con la CI senza cloud).
- **RNF-002 — Coerenza con FEAT-003 (stessa app TUI):** le viste di report si integrano nella medesima
  applicazione TUI di FEAT-003 senza romperne la navigazione; la UX (scorciatoie, tasti, stile) è
  coerente con le convenzioni già stabilite da FEAT-003.
- **RNF-003 — Extra opzionale `[tui]` (Principio III):** il framework TUI è una dipendenza opzionale;
  il core resta senza nuove dipendenze obbligatorie. Installare `sertor[tui]` non deve impattare chi
  usa solo il core o il server MCP.
- **RNF-004 — Host-agnostico (Principio X):** il pannello funziona su qualunque progetto ospite senza
  modifiche al suo corpo; la configurazione (sede dello store, provider attivi, FEAT-007 on/off) è
  tutta in `Settings`.
- **RNF-005 — Read-only:** il pannello di report non scrive nello store di osservabilità né altera lo
  stato del sistema; è una superficie di sola lettura.
- **RNF-006 — Risposta percepita:** la navigazione tra le viste di report deve rispondere ai tasti in
  tempo percepibilmente immediato; il caricamento dei dati aggregati da FEAT-002 (potenzialmente
  una query sullo store) non deve bloccare il rendering dell'interfaccia.

## 7. Vincoli, assunzioni e dipendenze

- **Thin consumer (REQ-E2 dell'epica):** FEAT-004 non reimplementa aggregazione né accede direttamente
  allo store di osservabilità grezzo; consuma esclusivamente l'interfaccia pubblica di FEAT-002
  (Principio I). La separazione garantisce che la logica di aggregazione sia testabile indipendentemente
  dalla TUI e che la TUI non si accoppi allo schema dello store.
- **Dipendenza necessaria da FEAT-002:** senza il servizio di aggregazione/report (FEAT-002), le viste
  di report non hanno dati. FEAT-004 non è utile in produzione senza FEAT-002. La degradazione onesta
  (REQ-014) copre il caso di assenza temporanea o di sviluppo parallelo.
- **Dipendenza necessaria da FEAT-001:** FEAT-002 dipende a sua volta dallo store di FEAT-001; se la
  persistenza è disattivata, i report sono vuoti. FEAT-004 eredita questa dipendenza transitivamente.
- **Dipendenza opzionale da FEAT-007:** la colonna € nel report costo appare solo se FEAT-007 è
  installata e configurata (REQ-005/006). La stima € è una capacità Should, non Must: il report costo
  deve essere utile anche senza di essa (token leggibili da soli).
- **Integrazione con FEAT-003:** le viste di report sono aggiunte alla stessa app TUI di FEAT-003;
  la navigazione base (tasti, stile) è definita da FEAT-003 e FEAT-004 la estende senza ridefinirla.
  [DA CHIARIRE: DA-F4-a — se FEAT-003 non è ancora implementata quando si lavora su FEAT-004, come
  si gestisce la dipendenza di integrazione? Sviluppo in parallelo con una shell TUI condivisa?]
- **Privacy-by-default (REQ-E8 dell'epica):** il pannello mostra solo metriche aggregate, mai contenuto
  grezzo. Questo è un vincolo architetturale, non una scelta di UX: anche se FEAT-002 esponesse campi
  di contenuto (opt-in separato, FEAT-001 REQ-008), il pannello non li renderebbe senza un requisito
  esplicito aggiuntivo.
- **Config centralizzata (Principio VIII):** tutte le manopole (FEAT-007 on/off, store location,
  intervalli di default) derivano da `Settings`; nessun default hardcoded nel pannello.
- **Assunzione sulla disponibilità di FEAT-002:** si assume che FEAT-002 esponga un'interfaccia
  (porta/protocollo) consultabile in modo sincrono o asincrono dalla TUI; il dettaglio del contratto
  è materia di design. I requisiti qui sono agnostici sul protocollo di comunicazione.

## 8. Rischi

- **R-1 — Dipendenza bloccante da FEAT-002:** se FEAT-002 non è disponibile alla data di sviluppo di
  FEAT-004, le viste non hanno dati reali. Mitigazione: il requisito REQ-014 (degradazione onesta) e
  la separazione logica-vista/rendering permettono di sviluppare e testare FEAT-004 con dati sintetici
  anche prima che FEAT-002 sia completa.
- **R-2 — Scope creep verso viste ricche:** il rischio di aggiungere sparkline, grafici ASCII, trend
  di qualità — trasformando il pannello in una dashboard completa. Mitigazione: FEAT-004 copre le
  quattro viste essenziali (cache, costo, corpus, freschezza); trend di qualità è FEAT-009; web è
  FEAT-008.
- **R-3 — Accoppiamento allo schema di FEAT-002:** se il pannello accede allo store grezzo invece
  dell'interfaccia di FEAT-002, ogni cambiamento di schema rompe le viste. Mitigazione: REQ-016
  (thin consumer obbligatorio).
- **R-4 — Frammentazione TUI:** se FEAT-003 e FEAT-004 non condividono la stessa app TUI, l'utente ha
  due comandi separati con UX divergenti. Mitigazione: REQ-012 vincola l'integrazione nella stessa
  applicazione.
- **R-5 — Stima € obsoleta nel report:** i prezzi di FEAT-007 possono essere stantii se la config
  non è aggiornata; il pannello li rende così come li riceve da FEAT-002 (che li riceve da FEAT-007).
  Il rischio di obsolescenza appartiene a FEAT-007 (DA-O-a dell'epica); FEAT-004 non ne è responsabile.
- **R-6 — Latenza di caricamento report:** una query su uno store di eventi cresciuto può essere lenta
  e bloccare il rendering. Mitigazione: RNF-006 (risposta non bloccante); la query è responsabilità
  di FEAT-002, ma FEAT-004 deve gestire la latenza lato UI (es. indicatore di caricamento).

## 9. Prioritizzazione (MoSCoW)

| Item | REQ | MoSCoW | Perché |
|---|---|---|---|
| Vista report cache (hit/miss + token saving) | REQ-001/002/003 | **Must** | È il report esplicitamente richiesto ("missing vs hit") |
| Vista report costo/consumo (token) | REQ-004/006 | **Must** | Risponde alla domanda "quanto sto spendendo" (in token) |
| Vista report salute corpus (#doc/#chunk) | REQ-007/008 | **Must** | Salute di base del corpus, necessaria per diagnosi |
| Vista report freschezza (data ultimo indice) | REQ-009/010 | **Must** | Risponde a "quanto è fresco il corpus" |
| Navigazione da tastiera e struttura integrata | REQ-011/012/013 | **Must** | Senza navigazione le viste non sono accessibili |
| Degradazione onesta (persistenza off / FEAT-002 assente) | REQ-014/015 | **Must** | Non crashare, non ingannare; coerente con Principio IV |
| Thin consumer (no aggregazione nella TUI) | REQ-016 | **Must** | Vincolo architetturale REQ-E2 epica |
| Privacy: solo metriche aggregate nella TUI | REQ-017 | **Must** | Vincolo privacy REQ-E8 epica |
| Stima € nel report costo (dove FEAT-007 presente) | REQ-005 | **Should** | Richiede FEAT-007 (Should); attesa nell'MVP accanto ai token (DA-O-g) |
| Testabilità separata logica-vista/rendering | RNF-001 | **Must** | CI offline obbligatoria; parte del vincolo di progettazione |
| Extra opzionale `[tui]` | RNF-003 | **Must** | Principio III; il core non deve acquisire nuove dipendenze obbligatorie |
| Export report (CSV/Markdown) | — | **Could** | [DA CHIARIRE: DA-F4-b] utile ma non nell'MVP; dipende dall'interfaccia di FEAT-002 |

## 10. Domande aperte

- **DA-F4-a — Integrazione con FEAT-003 in parallelo:** [DA CHIARIRE: se FEAT-003 e FEAT-004 vengono
  sviluppate in parallelo, deve esistere una shell TUI condivisa (scaffolding) su cui entrambe
  costruiscono? Chi ne è responsabile e come si evita il conflitto di integrazione?]

- **DA-F4-b — Export di un report (CSV/Markdown):** [DA CHIARIRE: l'export di una vista di report
  (es. tabella cache hit/miss → CSV) è nel perimetro MVP o è un Could rinviabile? E, se sì, FEAT-004
  lo delega a FEAT-002 (che genera il dato) o gestisce il rendering/serializzazione in proprio?]

- **DA-F4-c — Intervalli temporali configurabili vs fissi:** [DA CHIARIRE: i preset di intervallo
  (ultima ora / 24h / 7gg) sono fissi nell'MVP o l'utente deve poter configurarne i valori?
  E si prevede un intervallo libero (da-data / a-data) via input testuale nella TUI?]

- **DA-F4-d — Ordine di priorità delle viste nell'MVP:** [DA CHIARIRE: se il tempo di sviluppo
  costringe a un sotto-insieme delle quattro viste Must, qual è l'ordine? Proposta: cache (hit/miss)
  → costo (token) → freschezza → salute corpus. Confermare o riordinare.]

- **DA-F4-e — Contratto con FEAT-002:** [DA CHIARIRE in design/FEAT-002: quale interfaccia espone
  il servizio di aggregazione affinché la TUI la consumi? I requisiti qui sono neutri sul protocollo,
  ma la progettazione di FEAT-004 dipende dalla forma dell'interfaccia (porta Protocol, dataclass,
  funzioni pure?). Va chiarito nella decomposizione di FEAT-002.]

- **DA-F4-f — Indicatore di caricamento report:** [DA CHIARIRE: quando FEAT-002 impiega tempo a
  rispondere (store grande), la TUI deve mostrare uno spinner/indicatore? O si assume che FEAT-002
  risponda sempre in modo da sembrare istantaneo? Impatta RNF-006.]

- **DA-O-a (ereditata dall'epica) — Stima prezzi € (FEAT-007):** [DA CHIARIRE: la tabella prezzi
  per provider è hardcoded, in config aggiornabile, o versionata? Impatta il report costo che FEAT-004
  rende. Default proposto: config aggiornabile con valori di default versionati.]
