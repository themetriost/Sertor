# Requisiti — Contratto di retrieval verso l'agente (fan-out del grafo, misurato)

<!-- Deriva da: FEAT-012 (epica `retrieval-qualita`) -->

## 1. Contesto e problema (perché)

Il sistema espone all'agente due famiglie di interrogazione **strutturalmente diverse**: il
**retrieval per similarità** (una *classifica* di frammenti con punteggio) e la **navigazione
strutturale** sul code-graph (un *insieme* di riferimenti esatti, senza punteggio). Sono ortogonali —
rispondono a domande di natura diversa.

Oggi le due famiglie si raggiungono con **tool separati**, e la scelta di quale usare è interamente
dell'agente. `search_combined` restituisce sì due flussi, ma **entrambi provengono dallo stesso
motore di similarità**, distinti solo da un filtro sui metadata (`services/retrieval.py:215-216`): il
grafo non vi entra affatto, pur essendo **costruito a ogni indicizzazione** e **caricato a ogni avvio**
del server.

Il problema ha due facce, ed è la seconda quella che blocca:

**(a) L'agente deve indovinare lo strumento.** L'evidenza registrata mostra che sulle domande
strutturali («dov'è definito X») la ricerca per similarità è genuinamente scarsa (hit@1 ≈ 0.18) mentre
il grafo è esatto (hit@1 ≈ 0.64, hit@10 = 1.00). Il sistema composito funziona **solo se l'agente
sceglie bene** — e non misuriamo se lo fa.

**(b) Non sappiamo misurare il contratto.** L'analisi di design ([[llm-facing-retrieval-contract]], 4
giri di revisione esterna) ha prodotto **quattro affermazioni empiriche non verificate** su come
presentare i risultati a un LLM. Nessuna è misurabile con gli strumenti attuali: la macchina di
valutazione esistente misura il **retrieval** (hit@k, MRR sui risultati recuperati), mentre queste
affermazioni riguardano il **comportamento dell'agente** che quei risultati li legge. Fra le due cose
non c'è ponte.

Ne segue l'ordine di questo requisito: **prima lo strumento di misura, poi la capacità che quello
strumento deve validare.** Costruire il fan-out senza poterlo misurare significherebbe consegnarlo
sulla fiducia — e il costo che introduce (diluizione del contesto dell'agente su *ogni* query) è
esattamente il tipo di danno che non si vede senza misura.

## 2. Obiettivi e criteri di successo

**Obiettivi.**

1. Rendere **misurabile** l'effetto della forma di un risultato di retrieval sulla qualità della
   risposta dell'agente.
2. Decidere **su evidenza** se e sotto quali condizioni il punteggio appartenga al payload.
3. Portare il segnale strutturale all'agente **senza che debba chiederlo**, se e solo se la misura
   mostra che aiuta e non danneggia.
4. Blindare con test le invarianti oggi vere ma non protette.

**Criteri di successo (misurabili, tech-agnostici).**

| # | Criterio | Soglia |
|---|---|---|
| SC-001 | Le invarianti della valutazione strutturale sono asserite da test che falliscono se violate | 2 invarianti coperte |
| SC-002 | Ogni misura è eseguita con la regola di decisione **registrata prima** dell'esecuzione | 100% delle misure |
| SC-003 | La decisione sull'esposizione del punteggio è presa su misura, non per opinione, e differenziata per motore | 2 motori decisi |
| SC-004 | Sulle domande **strutturali**, la risposta dell'agente con il flusso di grafo cita le fonti attese più spesso che senza | miglioramento misurato, direzione positiva |
| SC-005 | Sulle domande **non strutturali**, la risposta non peggiora quando il flusso di grafo arriva non richiesto | nessun peggioramento sistematico |
| SC-006 | Le tre cause di indisponibilità del grafo sono distinguibili nel risultato | 3 cause distinte |
| SC-007 | A capacità disattivata, la risposta è identica a quella odierna | identità verificata |
| SC-008 | Il costo aggiuntivo del flusso di grafo su una query che non lo richiede è dichiarato e misurato | misurato |

## 3. Stakeholder e attori

- **Agente LLM consumatore** — attore primario: riceve il risultato e ne trae conclusioni. È lui che
  può essere ingannato da un contratto che tace.
- **Utente finale** dell'agente — subisce le affermazioni false che un contratto ambiguo produce.
- **Manutentore del progetto ospite** — configura, e deve poter disattivare senza perdere il
  comportamento precedente.
- **Consumatore deterministico** (valutazione, diagnostica) — legge gli stessi risultati per misurare,
  con esigenze diverse da quelle dell'agente.

## 4. Ambito

### In ambito

- Blindatura con test delle invarianti della valutazione strutturale già vere.
- Dichiarazione, nella descrizione dei tool di ricerca, dell'ambito di validità del punteggio,
  **coerente con il motore effettivamente configurato**.
- Un **harness di valutazione agent-facing**: misura l'effetto di una variante di payload sulla
  qualità della risposta di un agente.
- Le misure che decidono l'esposizione del punteggio, per ciascun motore.
- Un **terzo flusso strutturale** in `search_combined`, dietro interruttore, con assenza tipizzata,
  troncamento dichiarato, provenienza degli ingressi e marcatura della corroborazione.
- Le vie d'ingresso **deterministiche** al grafo a partire da una query in linguaggio naturale.
- Il **gate duplice** (beneficio + non-regressione) come condizione di consegna.

### Fuori ambito

- Qualunque **router automatico** che scelga il metodo al posto dell'agente: la scelta resta al
  consumatore, la capacità qui fa fan-out e consegna i segnali separati.
- **Fusione** dei due segnali in una classifica unica (errore di categoria: richiederebbe una scala
  comune inesistente).
- Chiamate a un LLM **dentro** il percorso di retrieval: l'harness usa un agente, il retrieval no.
- Resa testuale alternativa (blocchi etichettati in ordine prescritto) e sua misura → **rinviata**,
  dipende dall'esito delle misure di base.
- Via d'ingresso **semantica** al grafo (embedding dei nomi qualificati) → rinviata: reintrodurrebbe
  la dipendenza dalla similarità che le vie deterministiche evitano.
- Propagazione del segnale di confidenza per-flusso fino al payload → **debito tracciato** (§10), non
  consegnato qui.
- Storicizzazione nel tempo delle metriche di qualità (è dell'epica osservabilità).

## 5. Requisiti funzionali (EARS)

### Gruppo A — Invarianti della valutazione strutturale (blindatura)

- **REQ-001 (Ubiquitous):** *The evaluation router shall route a structural case exclusively to the
  code-graph, without invoking the similarity engine.*
- **REQ-002 (Ubiquitous):** *The evaluation router shall route a non-structural case exclusively to
  the similarity engine, without invoking the code-graph.*
- **REQ-003 (Event-driven):** *When the placeholder value assigned to graph results changes, the
  evaluation report shall remain identical in every field.*
- **REQ-004 (Unwanted):** *If a metric ever derives from that placeholder, then the invariant test
  shall fail.*

### Gruppo B — Dichiarazione dell'ambito del punteggio

- **REQ-005 (Ubiquitous):** *The description of each search tool shall state the comparability scope
  of any score it exposes: within its own list only, never across flows, never across queries, never
  as an absolute measure of quality.*
- **REQ-006 (State-driven):** *While the configured retrieval engine produces rank-fusion values, the
  tool description shall state that the score carries little information beyond the list order.*
- **REQ-007 (Ubiquitous):** *The tool description shall reflect the engine that is actually
  configured for the running instance.*
- **REQ-008 (Unwanted):** *If the description cannot be reconciled with the active configuration,
  then the system shall surface the discrepancy rather than present a description that does not
  hold.*

### Gruppo C — Harness di valutazione agent-facing

- **REQ-009 (Ubiquitous):** *The system shall allow measuring the effect of a payload variant on the
  quality of an agent's answer to a question.*
- **REQ-010 (Ubiquitous):** *The harness shall submit to the agent the payload in the same form the
  agent receives in normal operation.*
- **REQ-011 (Ubiquitous):** *The harness shall record, for each case and each variant, whether the
  answer cites the expected sources and whether it cites sources absent from the supplied material.*
- **REQ-012 (Ubiquitous):** *The harness shall keep the two variants identical in every respect
  except the one under test.*
- **REQ-013 (Ubiquitous):** *The decision rule of a measurement shall be recorded before the
  measurement is executed.*
- **REQ-014 (Unwanted):** *If the decision rule was not recorded beforehand, then the result shall
  not be treated as evidence for a contract decision.*
- **REQ-015 (Ubiquitous):** *The harness shall record per case the size of the supplied material and
  the latency of the call, so that benefit and cost are measured together.*
- **REQ-016 (Ubiquitous):** *The harness shall run repetitions of each case so that variation between
  runs is distinguishable from the effect under test.*

### Gruppo D — Esito sull'esposizione del punteggio

- **REQ-017 (Optional feature):** *Where the measurement shows no difference in answer quality under
  a given engine, the system shall not expose the score under that engine.*
- **REQ-018 (Optional feature):** *Where the score is withheld from the agent, a deterministic
  consumer shall still be able to obtain it by explicit opt-in.*
- **REQ-019 (Unwanted):** *If the agent is observed comparing scores across flows despite the
  declared scope, then the system shall withhold the score rather than rescale it.*

### Gruppo E — Il flusso strutturale

- **REQ-020 (Optional feature):** *Where the structural fan-out is enabled, the combined search shall
  return a third labelled flow carrying the code-graph result, alongside the two existing flows.*
- **REQ-021 (State-driven):** *While the structural fan-out is disabled, the combined search shall
  return exactly what it returns today.*
- **REQ-022 (Ubiquitous):** *The structural flow shall group its results by symbol and, within each
  symbol, by type of relation.*
- **REQ-023 (Ubiquitous):** *The structural flow shall declare, for each entry point used, how that
  entry point was derived.*
- **REQ-024 (Ubiquitous):** *The system shall derive entry points from the query by deterministic
  means, without invoking a language model.*
- **REQ-025 (Ubiquitous):** *The system shall bound the number of entry points it resolves for a
  single query.*
- **REQ-026 (Unwanted):** *If no entry point can be derived from the query, then the structural flow
  shall report that it was not attempted, and shall cost nothing further.*

### Gruppo F — Assenza tipizzata e troncamento

- **REQ-027 (Ubiquitous):** *The structural flow shall distinguish three outcomes: not attempted,
  attempted and empty, and not attemptable.*
- **REQ-028 (Ubiquitous):** *The system shall distinguish at least three separate causes of "not
  attemptable": the graph was never built, the navigation capability is unavailable, and the graph
  artifact is unusable.*
- **REQ-029 (Unwanted):** *If the graph cannot be consulted for any reason, then the flow shall not
  present an empty result, because an empty result asserts absence.*
- **REQ-030 (Ubiquitous):** *The outcome reported for the flow as a whole shall be derived from the
  per-relation outcomes, and shall not be settable independently of them.*
- **REQ-031 (Ubiquitous):** *The flow shall report "not attempted" if and only if it used no entry
  point.*
- **REQ-032 (Optional feature):** *Where a set of relations is truncated by a limit, the flow shall
  declare how many are shown and how many exist.*
- **REQ-033 (Ubiquitous):** *The similarity flows shall not declare a total, because their cut is
  constitutive and asserts no exhaustiveness.*

### Gruppo G — Corroborazione fra flussi

- **REQ-034 (Optional feature):** *Where the same location is present both in a similarity flow and
  in the structural flow, each shall carry a reference to the other.*
- **REQ-035 (Ubiquitous):** *The system shall not remove a result from one flow because it appears in
  another, because the convergence of two independent methods is itself a signal.*

### Gruppo H — Il gate di consegna

- **REQ-036 (Ubiquitous):** *The structural fan-out shall be measured both for benefit on structural
  questions and for non-regression on non-structural questions.*
- **REQ-037 (Unwanted):** *If the non-regression half of the gate fails, then the fan-out shall not
  be enabled by default.*
- **REQ-038 (Unwanted):** *If the benefit half of the gate fails, then the fan-out shall not be
  delivered.*

## 6. Requisiti non funzionali

- **RNF-1 — Nessun LLM nel percorso di retrieval.** La risoluzione degli ingressi e la costruzione
  del flusso sono deterministiche. L'agente è **oggetto di misura** nell'harness, mai componente del
  retrieval.
- **RNF-2 — Determinismo e ripetibilità.** A parità di query e di indice, gli ingressi risolti e il
  flusso prodotto sono identici.
- **RNF-3 — Additività.** A interruttore spento, comportamento e forma della risposta invariati
  (SC-007). L'interruttore è spento di default fino al superamento del gate.
- **RNF-4 — Costo dichiarato.** L'aumento di materiale consegnato per query è misurato e riportato,
  non stimato.
- **RNF-5 — Onestà nella degradazione.** Ogni indisponibilità è **riportata**, mai silenziata: una
  degradazione che tace produce affermazioni false a valle (Principio *Fail Loud*).
- **RNF-6 — Accesso via vehicle.** Ogni esecuzione di misura passa dalle superfici supportate, mai
  importando la libreria direttamente (Principio XI).
- **RNF-7 — L'harness non è codice di prodotto.** Vive separato dalla libreria e dai test
  deterministici: richiede un agente e non è riproducibile a costo zero.
- **RNF-8 — Riproducibilità dell'evidenza.** Ogni esecuzione conserva materiale, risposte e verdetti
  in forma ispezionabile, così che una decisione di contratto sia riesaminabile a posteriori.

## 7. Vincoli, assunzioni e dipendenze

**Vincoli ancorati al codice esistente** (verificati in sessione, 2026-07-24):

| Fatto | Dove | Conseguenza sul requisito |
|---|---|---|
| L'instradamento strutturale è totale e il punteggio dei risultati di grafo è un segnaposto | `services/eval/runner.py:76-84` | REQ-001..004 blindano un'invariante **già vera**, non la introducono |
| Il motore di default produce valori di **fusione per rango**, non similarità | `engines/hybrid.py:180` | REQ-006: la dichiarazione deve differire per motore |
| La soglia di confidenza agisce sul **pool denso prima della fusione** | `engines/hybrid.py:129-132` | Il numero che decide l'astensione e quello eventualmente esposto sono **su scale diverse** → §10 |
| Tre cause distinte di indisponibilità, due delle quali condividono lo stesso tipo di errore | `adapters/graph/networkx_graph.py:114-130` | REQ-028: non basta distinguere il tipo, serve il discriminante |
| I nomi qualificati sono presenti nell'artefatto del grafo | `adapters/graph/networkx_graph.py:68` | La via d'ingresso per confronto lessicale è realizzabile |
| I metadata dei risultati trasportano il nome qualificato… | `adapters/vectorstores/chroma.py:251` | …ma **solo** per i risultati provenienti dal pool denso |
| …**non** per i risultati provenienti dal solo ramo lessicale | `engines/hybrid.py:200-203` | La via d'ingresso per espansione ha **copertura parziale** → assunzione A-3 |

**Assunzioni.**

- **A-1** — L'agente usato dall'harness è un attore stabile abbastanza da rendere confrontabili due
  varianti nella stessa sessione di misura. Le misure sono **relative** (variante A vs B), mai
  assolute, proprio per contenere questa variabilità.
- **A-2** — Il grafo è già costruito e caricato: il costo marginale di interrogarlo è un accesso in
  memoria, non un ricalcolo. Da verificare nella misura, non assunto (SC-008).
- **A-3** — La via d'ingresso per espansione dai risultati semantici ha copertura parziale per il
  vincolo sopra. Se la copertura risulta troppo bassa, la via è **rinviata** anziché corretta in
  questa feature.

**Dipendenze.**

- La suite di valutazione esistente fornisce le domande e le fonti attese: senza di essa non c'è
  ground-truth per l'harness (dipendenza da FEAT-001 dell'epica, consegnata).
- La classificazione delle domande per tipo (strutturale / non strutturale) esiste già ed è la base
  della partizione beneficio ↔ non-regressione.
- La copertura dichiarata del grafo per linguaggio e tipo di arco è la fonte per distinguere «arco
  non estratto per questo linguaggio» da «nessun risultato».

## 8. Rischi

| # | Rischio | Mitigazione |
|---|---|---|
| R-1 | **La misura non discrimina** (il giudizio sulla qualità della risposta è rumoroso) | Misure relative, ripetizioni, criteri binari verificabili in modo deterministico (cita le fonti attese? cita fonti inesistenti?) accanto al giudizio soggettivo |
| R-2 | **Il fan-out diluisce il contesto** e peggiora le risposte non strutturali | È metà del gate (REQ-036/037): il rischio è la cosa che si misura, non un imprevisto |
| R-3 | **Gli ingressi sbagliati** producono materiale irrilevante che *sembra* preciso | Provenienza dichiarata (REQ-023) + tetto (REQ-025) + costo auto-correlato alla rilevanza (REQ-026) |
| R-4 | **Il buco lessicale**: query in lingua diversa dagli identificatori → nessun ingresso deterministico | Riconosciuto: il caso ricade su «non tentato», che è onesto e a costo nullo. La via semantica che lo chiuderebbe è fuori ambito |
| R-5 | **Deriva del giudice**: il criterio di qualità cambia fra due esecuzioni | Regola di decisione registrata prima (REQ-013/014); materiale e verdetti conservati (RNF-8) |
| R-6 | **Costo economico** delle misure (ogni caso richiede chiamate a un agente) | Insiemi contenuti; l'harness è opt-in e non gira nella suite ordinaria (RNF-7) |
| R-7 | **Si consegna la forma senza l'esito**: lo schema viene implementato e il gate no | Il gate è un requisito funzionale (REQ-036..038), non una raccomandazione |

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivo |
|---|---|---|
| **Must** | REQ-001..004 (invarianti) · REQ-009..016 (harness) · REQ-036..038 (gate) | L'harness è il prerequisito di ogni decisione; le invarianti proteggono ciò che è già vero; il gate è ciò che rende la consegna legittima |
| **Must** | REQ-020..033 (flusso strutturale, assenza tipizzata) | È la capacità; l'assenza tipizzata ne è parte inscindibile — senza, il flusso produce affermazioni false |
| **Should** | REQ-005..008 (dichiarazione dell'ambito) · REQ-017..019 (esito sul punteggio) | Alto valore e basso costo, ma indipendenti dalla capacità principale |
| **Should** | REQ-034..035 (corroborazione) | Migliora il segnale; il flusso è utile anche senza |
| **Could** | Resa testuale alternativa e sua misura · via d'ingresso semantica · testo per le definizioni | Dipendono dall'esito delle misure di base |
| **Won't (qui)** | Router automatico · fusione in classifica unica · propagazione del segnale di confidenza | I primi due sono esclusi per design, il terzo è debito tracciato |

## 10. Domande aperte

- **[DA CHIARIRE]** Il numero su cui si decide l'astensione (calcolato prima della fusione) e quello
  eventualmente esposto nel payload (prodotto dalla fusione) sono **su scale diverse**, e oggi nulla
  lo dichiara. Va risolto in questa feature dichiarandolo, o rinviato alla feature che propaga il
  segnale di confidenza fino al payload?
- **[DA CHIARIRE]** Soglia di somiglianza della via d'ingresso per confronto lessicale: da fissare
  per misura (falsi agganci sull'insieme non strutturale) o da esporre come manopola all'ospite?
- **[DA CHIARIRE]** Se la copertura della via d'ingresso per espansione risulta troppo parziale
  (assunzione A-3), si corregge la costruzione dei risultati solo-lessicali — allargando l'ambito — o
  si rinvia la via?
- **[DA CHIARIRE]** L'harness misura la qualità della risposta con un giudizio automatico, con un
  giudizio umano, o con entrambi? Il criterio deterministico (cita le fonti attese?) è disponibile
  gratis; quello sulla qualità no.
- **[DA CHIARIRE]** L'esito delle misure va riportato nella design note che le ha generate
  ([[llm-facing-retrieval-contract]], §8) come parte della definizione di fatto? *(Proposta: sì — le
  righe «non misurato» diventano verdetti, e il documento passa da `in-review` a uno stato risolto.)*
