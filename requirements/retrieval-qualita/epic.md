# Epica — Qualità del retrieval (misurare e migliorare la pertinenza)

> Livello: **epica** — **estensione dell'epica primaria** [`../sertor-core/epic.md`](../sertor-core/epic.md).
> Non aggiunge una *nuova modalità* di RAG (quelle sono nel core: vettoriale/ibrido/grafo/agentico): ne
> alza la **qualità misurata**. Risponde al rischio **R-1 del core** («qualità retrieval insufficiente,
> senza metriche regredisce») e raccoglie le tecniche di retrieval avanzato finora orfane (i Could
> dell'hardening). Si decompone in `requirements/retrieval-qualita/<feature>/requirements.md` (EARS).

## 1. Visione e problema (perché)

Oggi Sertor restituisce risultati, ma «funziona» non è «misurato» (Principio V). Due xfail storici di
pertinenza sono stati chiusi **strict** sul mini-corpus, ma manca un **ground-truth reale** (set
query→file atteso) che renda la qualità un numero ripetibile e confrontabile tra provider/motori.
Inoltre `search_code` resta **debole sulle query architetturali** (intento ampio, non un simbolo).
Infine esistono **tecniche note** per alzare la pertinenza (query transformation/HyDE, filtro metadata,
contextual retrieval) che vivono come Could nell'hardening senza una casa durevole.

Il valore dell'epica: trasformare la pertinenza da impressione a **metrica** e darle le **leve** per
migliorarla, senza toccare le modalità di retrieval del core (le consuma, non le ridefinisce).

> Il *come* (stack di valutazione, struttura del codice) è materia della **fase di design**. Qui solo
> *cosa* e *perché*.

## 2. Ambito

### In ambito
- **Misura della pertinenza** su un **ground-truth reale**: set di query con file/risposta attesi,
  metriche `hit-rate@k`/`MRR@k`, chiusura definitiva degli xfail con dati veri.
- **Eval comparativa** tra motori (baseline/ibrido) e provider (locale/Azure), incluso il provider
  forte (marker `cloud`).
- **Miglioramento mirato di `search_code`** sulle query architetturali (intento, non simbolo).
- **Calibrazione delle soglie** di pertinenza (`SERTOR_MIN_SCORE` e affini) su dati, non a naso.
- **Tecniche di retrieval avanzato** come leve opzionali e misurate: query transformation (multi-query/
  HyDE), filtro per metadata esteso, contextual retrieval (à la Anthropic).

### Fuori ambito
- Le **modalità** di retrieval in sé (vettoriale/ibrido/grafo/agentico): epica `sertor-core`.
- **Nuovi backend di store / scala** (PGVector/Mongo, multi-collezione): epica
  [`../backend-store-scala/epic.md`](../backend-store-scala/epic.md).
- **Nuove fonti di ingestione** (formati, schema SQL): epiche `ingestione-estesa` / `conoscenza-schema-sql`.
- Telemetria/trend di qualità nel tempo (`low_confidence`/score nel tempo): è FEAT-009 dell'epica
  `osservabilita` (questa **produce** il segnale, quella lo storicizza).
- Definizione del *come* (stack eval, struttura): fase di **design**.

## 3. Criteri di successo
- **CS-1 (ground-truth):** esiste un set di valutazione versionato (query→atteso) su ≥1 corpus reale e
  un comando ripetibile che ne calcola `hit-rate@k`/`MRR` in modo deterministico.
- **CS-2 (confronto):** la stessa metrica è calcolabile su ≥2 configurazioni (es. baseline vs ibrido, o
  locale vs Azure) e i risultati sono confrontabili.
- **CS-3 (search_code):** su un set di query architetturali note, la pertinenza misurata **migliora** in
  modo dimostrabile rispetto alla baseline odierna (numero, non impressione).
- **CS-4 (soglie):** le soglie di confidenza derivano da una misura sul ground-truth, non da valori
  arbitrari; spegnendole il comportamento torna quello odierno.
- **CS-5 (leve opzionali):** ogni tecnica avanzata (HyDE/filtro/contextual) è un **opt-in** che, da
  spento, lascia il comportamento e il costo identici a oggi (Principio I/III).

## 4. Stakeholder e attori
- **Owner/maintainer (tu):** vuole sapere *quanto* è buono il retrieval e se un cambiamento lo migliora.
- **Agente LLM:** beneficiario diretto — contesto più pertinente e segnale di confidenza più affidabile.
- **Il core di Sertor:** fornisce motori e segnali (`low_confidence`, score); questa epica li misura.
- **Epica `osservabilita`:** consuma a valle il segnale di qualità per i trend.

## 5. Vincoli, assunzioni e dipendenze
- **Additività:** le leve avanzate sono extra/opt-in; il contratto delle porte resta invariato (Principio I).
- **Misurabilità prima di tutto:** nessuna tecnica si dichiara «migliore» senza un numero sul ground-truth.
- **Local-first:** la valutazione gira in locale (mock/Chroma); il confronto col provider forte è un
  esercizio `cloud` opzionale, mai obbligatorio in CI.
- **Dipendenza da FEAT-018** (soglia `SERTOR_MIN_SCORE`, già su master): questa epica la **calibra**.
- **Riferimento:** hardening produzione `../sertor-core/hardening-produzione/` (REQ-H7/H8/H11 confluiscono qui).

## 6. Rischi
- **R-1 — Ground-truth costoso/soggettivo:** costruire il set query→atteso richiede giudizio; mitigare
  con un set piccolo ma onesto, ancorato a casi reali (dogfood).
- **R-2 — Overfitting al set:** ottimizzare sul ground-truth può non generalizzare; tenere il set
  rappresentativo e separare i casi.
- **R-3 — Costo/latenza delle tecniche avanzate:** HyDE/multi-query moltiplicano le chiamate; misurare
  il trade-off qualità↔costo, non attivarle per default.
- **R-4 — Provider drift:** l'eval `cloud` dipende da modelli che cambiano; trattarlo come misura, non
  come gate di CI.

## 7. Requisiti trasversali (EARS)
- **REQ-E1 (Ubiquitous):** *The system shall expose a repeatable, deterministic way to measure retrieval
  relevance against a versioned ground-truth set.*
- **REQ-E2 (Optional):** *Where an advanced retrieval technique (query transformation, extended metadata
  filtering, contextual retrieval) is enabled, the system shall apply it as an opt-in, leaving default
  behaviour and cost unchanged when disabled.*
- **REQ-E3 (Unwanted):** *If no ground-truth set is configured, then the evaluation command shall fail
  with an actionable message rather than report a meaningless score.*
- **REQ-E4 (Optional):** *Where a cloud provider is configured, the system shall allow a comparative
  evaluation marked as cloud, without requiring it for the local test suite.*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Ground-truth & valutazione della pertinenza** — ciclo di vita di una suite di valutazione *del progetto ospite*: genesi (interattiva), artefatto-dato versionato (query→atteso), esecuzione ripetibile (`hit-rate@k`/`MRR` via vehicle), **non-regressione** (riferimento + gate); chiusura xfail con dati reali. *(Riformulata 2026-06-20: host-side, non solo dogfood.)* | Trasforma «funziona» in «misurato e presidiato» (Principio V) | **Must** | **decomposta** → [`ground-truth-valutazione/`](ground-truth-valutazione/requirements.md) |
| FEAT-002 | **Eval comparativa live su provider reale** (REQ-051, marker `cloud`) — confronto motori/provider col modello forte | Misura la qualità reale oltre il mock | **Could** *(abbassata 2026-06-20: dipende dall'attivazione del RAG su cloud)* | da decomporre — **bloccata finché il RAG cloud non è attivo** |
| FEAT-003 | **Qualità del retrieval fuso code+doc (`search_combined`) su query NL/architetturali** — alzare la pertinenza NL **per-superficie** (doc + code) con la **fusione** come test d'integrazione; metrica di **fusion coverage**; categoria dedicata ai casi **requisito→implementazione** | Il **differenziatore** della mission: codice (*cosa*) + documenti (*perché*) fusi per l'agente | **Should** | 🔄 **infrastruttura di misura CONSEGNATA (2026-06-21, merge `42aceaf`)** → [`qualita-search-code-nl/`](qualita-search-code-nl/requirements.md): campo `intent`, **fusion coverage**, baseline per-superficie, `eval run --fused`, evento `fused_eval` (Constitution 12/12, core 938 verdi). **Resta la fase empirica** (set NL reale + baseline dogfood + valutazione leve, Should) + debito P2 (skill `eval-suite-author` estesa) |
| FEAT-004 | **Calibrazione delle soglie di pertinenza** — derivare `SERTOR_MIN_SCORE` e affini dal ground-truth | Confidenza/astensione affidabili, non arbitrarie | **Should** | da decomporre |
| FEAT-005 | **Query transformation (multi-query / HyDE)** — riformulazione/espansione della query (opt-in) [ex REQ-H7] | Recupero migliore su query vaghe | **Could** | da decomporre — da `hardening-produzione` |
| FEAT-006 | **Filtro per metadata esteso** — restrizione del retrieval per attributi (path/linguaggio/doc_type…) [ex REQ-H8] | Precisione su corpora grandi/eterogenei | **Could** | da decomporre — da `hardening-produzione` |
| FEAT-007 | **Contextual retrieval (Anthropic)** — arricchimento del chunk con contesto di documento prima dell'embedding (opt-in) [ex REQ-H11] | Meno chunk «ciechi», più pertinenza | **Could** | da decomporre — da `hardening-produzione` |
| FEAT-008 | **Generazione assistita della suite (agente-from-corpus, da approvare)** — l'**agente** dell'utente (via skill, non un servizio LLM terzo) propone candidati query→atteso dai contenuti indicizzati; l'utente cura/approva. Riusa il pattern di `derive-entity-types`. *(Promossa da FEAT-001, Gruppo C; vedi `ground-truth-valutazione/` §5C.)* | Abbassa l'attrito di creare il ground-truth (R-1) | **Should** | requisiti in [`ground-truth-valutazione/`](ground-truth-valutazione/requirements.md) (Gruppo C) |
| FEAT-009 | **Feedback esplicito di pertinenza (human-in-the-loop)** — l'utente giudica i risultati di ricerca (pertinente/no) e il giudizio raffina gli `expected` della suite. *(Promossa da FEAT-001, Gruppo F; vedi `ground-truth-valutazione/` §5F.)* | Suite viva che migliora con l'uso | **Should** | requisiti in [`ground-truth-valutazione/`](ground-truth-valutazione/requirements.md) (Gruppo F) |
| FEAT-010 | **Pavimento assoluto di qualità** — soglia minima assoluta opzionale (es. `SERTOR_EVAL_MIN_MRR`/hit) come gate aggiuntivo oltre la baseline relativa della non-regressione. *(Rinviata dal plan di FEAT-001, feature 065: la baseline-file copre il caso «non peggiorare»; il pavimento assoluto è un di-più.)* | Pavimento di sicurezza indipendente dalla baseline | **Could** | da decomporre |
| FEAT-011 | **Valutazione della navigazione del grafo (set-based)** — misura la **correttezza delle query relazionali** del code-graph (`who_calls`, dipendenze/callees, `find_symbol`, `related_docs`): la risposta è un **insieme di simboli/nomi** (qualname), non un file in cima a un ranking. Oracolo a **insiemi** (precision/recall/F1 o match esatto), eseguito via la porta `CodeGraph` (vehicle, Principio XI), **senza** rank né @k. Possibile genesi a *snapshot* dal grafo corrente (approvato una volta → sentinella di regressione). *(Promossa 2026-06-20: l'harness `evaluate` hit@k su path NON può esprimere una navigazione relazionale; emerso provando live `eval-feedback` su una query "chi chiama / da cosa dipende".)* | Rende misurabile la potenza relazionale del grafo, oggi non valutata | **Should** | **decomposta** → [`valutazione-navigazione-grafo/`](valutazione-navigazione-grafo/requirements.md) |

> **Nota sull'MVP:** la prima release utile è **FEAT-001** (il ground-truth e la misura): senza un numero
> ripetibile, le altre feature non hanno un metro per dirsi migliorie. FEAT-002/003/004 (Should) seguono;
> le tecniche avanzate (Could) si attivano e si giustificano **solo se** misurate meglio della baseline.

## 9. Domande aperte
- **DA-Q-a — Forma del ground-truth:** ✅ **RISOLTA (utente, 2026-06-20):** è un **artefatto-dato del
  progetto ospite**, versionato e **fornito dall'ospite** (non un fixture Python), creato a mano *oppure*
  delegando la generazione a un LLM (proposta da approvare). Il set Sertor diventa l'**esempio dogfood** in
  questa forma. Il formato esatto (TOML/JSON) resta dettaglio di design (vedi `ground-truth-valutazione/`
  §10 DA-a). Capacità host-side, non solo dogfood.
- **DA-Q-b — Confine con l'osservabilità:** confermato che il **trend** nel tempo è di `osservabilita`
  (FEAT-009); qui si produce la misura puntuale e il ground-truth, non la storicizzazione.
