# Research — Contratto di retrieval verso l'agente

**Feature**: `118-contratto-retrieval-agente` · **Data**: 2026-07-24

Tutte le decisioni sono prese in autonomia su autorizzazione esplicita («procedi fino a implement,
fermati solo su dubbi genuini»). Nessun `NEEDS CLARIFICATION` resta aperto.

---

## R1 — Dove vive l'harness di misura

**Decisione:** nuova directory **`eval_ab/`** alla radice del repo, **fuori** da `src/` e da `tests/`.
Non è un membro del workspace `uv`, non ha `pyproject.toml`, non viene installata.

**Motivazione:** non è codice di prodotto (non viaggia con `sertor-core`) e non è un test
deterministico (richiede un agente esterno, costa denaro, non è riproducibile a costo zero né
offline). Metterla in `tests/` la farebbe entrare in `uv run pytest` e romperebbe il gate pre-merge;
metterla in `src/` la spedirebbe agli ospiti. RNF-7 della spec lo richiede esplicitamente.

**Alternative scartate:** `tests/manual/` (finirebbe comunque sotto la radice di raccolta pytest, e
un marker `@pytest.mark.ab` sarebbe una convenzione fragile) · un package separato in `packages/`
(implicherebbe distribuzione, che qui non serve).

---

## R2 — Come l'harness esercita l'agente

**Decisione:** invocazione **headless** dell'assistente già presente sulla macchina
(`claude -p <prompt>`), con modello fissato per l'intera campagna di misura e **prompt template
identico** per tutti gli arm. La risposta dell'agente è testo; il verdetto su di essa è calcolato in
modo **deterministico**.

**Motivazione:** l'agente è **oggetto di misura**, non componente del sistema — il confine D↔N resta
intatto perché nessuna di queste chiamate vive nel percorso di retrieval. Il prompt identico fra gli
arm è ciò che rende la differenza attribuibile alla sola variante (FR-004).

**Alternative scartate:** chiamata diretta a un'API di modello (introdurrebbe una dipendenza e una
chiave in un componente che non è prodotto) · agente giudice per la qualità (rinviato: il criterio
deterministico è gratis e la spec lo assume, il giudice si aggiunge solo se non discrimina).

---

## R3 — Come l'harness ottiene il payload reale

**Decisione:** l'harness cattura il payload eseguendo il **vehicle** (`sertor-rag search --json` per
i flussi di somiglianza; il tool MCP quando serve la forma esatta consegnata all'agente), **non**
importando `sertor_core`.

**Motivazione:** Principio XI. È anche la sola via che garantisce FR-002 («la stessa forma che
l'agente riceve nell'uso normale»): un payload ricostruito a mano divergerebbe dal reale proprio
sugli aspetti che stiamo misurando.

**Conseguenza:** le varianti si ottengono **trasformando** il payload catturato con funzioni pure
(`strip_scores`, `strip_graph`), non rigenerandolo. Così i due arm differiscono per costruzione solo
nell'aspetto in esame.

---

## R4 — Forma del ramo strutturale: nuove entità di dominio

**Decisione:** nuovo modulo `src/sertor_core/domain/agent_context.py` con dataclass **frozen**, tuple
al posto di liste (stile del dominio esistente): `EntryPoint`, `RelationBlock`, `SymbolContext`,
`GraphBranch`, `AgentContext`.

**Motivazione:** `ContextBundle` esiste già ma è la risposta a *un* simbolo e **non porta né stato né
totali**; estenderlo con quei campi lo caricherebbe di responsabilità che i suoi consumatori attuali
non hanno. Le nuove entità **compongono** `SymbolHit` e `ContextBundle` invece di duplicarli.

**Alternative scartate:** dizionari nudi (perderebbero il controllo delle invarianti) · estensione di
`ContextBundle` con status e totali (cambierebbe il contratto di un tool già in uso).

---

## R5 — Lo stato complessivo è una property derivata, non un campo

**Decisione:** su `GraphBranch`, `status` è una **property calcolata**:
`unavailable` se `unavailable_reason` è valorizzato · `not_attempted` se `entry_points` è vuoto ·
`partial` se almeno un blocco non è `ok` · altrimenti `ok`.

**Motivazione:** FR-028 («non impostabile indipendentemente») e FR-029 (`not_attempted` ⟺
`entry_points` vuoto) diventano veri **per costruzione** anziché per disciplina. Un campo impostabile
può divergere dai suoi sotto-stati; una property no. È la stessa ragione per cui §3.3 della design
note vieta lo stato unico.

---

## R6 — Mappatura tipizzata delle indisponibilità (tre cause, non due)

**Decisione:**

| Eccezione osservata | `unavailable_reason` |
|---|---|
| `GraphNotFoundError` | `graph_not_built` |
| `ConfigError` con `key == "graph"` | `navigation_library_missing` |
| `ConfigError` senza quella chiave | `graph_artifact_unusable` |

**Motivazione:** verificato su `adapters/graph/networkx_graph.py:97-130`. L'adapter converte
l'`ImportError` dell'extra mancante in `ConfigError(key="graph")`, **ma solleva lo stesso tipo** per
artefatto corrotto (JSON illeggibile) e formato non riconosciuto. Catturare `ConfigError` nudo
conflaterebbe «manca una dipendenza» con «l'indice è rotto» — due cause con rimedi opposti, e
precisamente il collasso che FR-026 vieta.

**Nota di fragilità (dichiarata):** il discriminante è un attributo dell'eccezione, non un tipo. Se
un domani l'adapter smettesse di valorizzare `key`, la distinzione degraderebbe silenziosamente. Il
piano include un **test che pinna il discriminante**, così la regressione fallisce invece di degradare.

---

## R7 — Totali per il troncamento

**Decisione:** estendere `ContextBundle` con un campo **additivo e con default vuoto**
`totals: tuple[tuple[str, int], ...] = ()`, popolato dall'adapter **prima** di applicare i limiti.

**Motivazione:** oggi `get_context` applica i limiti configurati e **butta via** i conteggi: il totale
non è recuperabile a valle. Serve contarlo alla sorgente. Il default vuoto mantiene il contratto
retrocompatibile per i consumatori esistenti (Principio VI, additività).

**Alternative scartate:** una seconda chiamata di conteggio (raddoppierebbe il lavoro sul grafo) ·
dedurre il totale dalla saturazione del limite (indistinguibile fra «esattamente al limite» e
«tagliato»).

---

## R8 — Enumerazione dei simboli sulla porta

**Decisione:** aggiungere `list_symbols() -> list[str]` alla porta `CodeGraph` e implementarla
nell'adapter leggendo i `qualname` già presenti nell'artefatto.

**Motivazione:** la via d'ingresso per confronto lessicale ha bisogno dell'elenco dei nomi noti.
`networkx_graph.py:68` mostra che i `qualname` sono già serializzati: nessun ricalcolo, nessuna
struttura nuova. Estendere la porta è l'unico modo di ottenerlo senza violare l'inversione delle
dipendenze.

**Conseguenza:** i mock della porta nei test vanno estesi; essendo `Protocol` con structural typing,
è additivo.

---

## R9 — Vie d'ingresso deterministiche come funzioni pure

**Decisione:** nuovo modulo `src/sertor_core/services/graph_entry.py`, funzioni pure senza dipendenze:

- `extract_identifiers(query)` — token con maiuscole interne, underscore o notazione puntata;
- `match_symbol_table(query, qualnames, min_overlap=2)` — spezza i `qualname` in sotto-parti
  (CamelCase / underscore / punto, minuscolo), spezza la domanda in parole, candida un simbolo quando
  la sovrapposizione raggiunge la soglia **oppure** il nome intero compare nella domanda;
- `resolve_entry_points(...)` — ordina (identificatori prima, poi tabella), deduplica, taglia al tetto.

**Motivazione:** funzioni pure ⇒ test F.I.R.S.T. senza I/O, e determinismo (RNF-2) verificabile. Zero
dipendenze nuove: nessuna libreria di fuzzy matching, solo sovrapposizione di sotto-token.

**Ordine deliberato:** un identificatore *scritto* nella domanda è un segnale più forte di una
sovrapposizione lessicale; a parità di tetto, vince il più affidabile.

---

## R10 — Corroborazione fra flussi

**Decisione:** funzione pura `mark_corroboration(docs, code, graph)` che confronta **solo il path**
fra le definizioni del grafo e gli item dei flussi di somiglianza, e valorizza in **entrambe** le
direzioni: sull'item di somiglianza i `qualname` che lo corroborano, sul risultato strutturale i
`chunk_id` corrispondenti.

**Motivazione:** i `chunk_id` non portano un intervallo di righe confrontabile con la riga di una
definizione; il confronto su path è la v1 onesta. Bilaterale perché un segnale unidirezionale
costringerebbe l'agente a dedurre l'altra metà confrontando i path da sé — lavoro che il contratto
può risparmiargli.

**Limite dichiarato:** il match su path è **grossolano** — un file con molte definizioni corrobora
qualunque chunk dello stesso file. Accettato per la v1 e registrato; il raffinamento per intervallo di
righe è un'estensione successiva, non un debito nascosto.

---

## R11 — Descrizione dei tool derivata dalla configurazione

**Decisione:** helper puro `score_contract(settings) -> str` che produce il testo del contratto di
comparabilità in funzione di `settings.engine`; `Settings.load()` viene invocato **prima** di
istanziare il server, e le descrizioni dei tool di ricerca vengono composte da testo base + contratto.

**Motivazione:** FR-011 impone che la descrizione rifletta la configurazione **attiva**. Oggi
`instructions` e i docstring sono statici: dichiarerebbero un contratto che l'istanza non rispetta.
Il testo differisce per motore (somiglianza vs fusione per rango) e include l'asimmetria fra la scala
su cui si decide l'astensione e quella eventualmente esposta (FR-013).

**Nota:** il destino del campo `score` nel payload **non** si decide qui — lo decide la misura (FR-017).
Questa fase rende il contratto *dichiarato*, non lo cambia.

---

## R12 — Manopole e default

**Decisione:** tre nuove voci in `Settings`, tutte con default **conservativi**:

| Manopola | Default | Significato |
|---|---|---|
| `combined_graph_enabled` (`SERTOR_COMBINED_GRAPH`) | `False` | l'interruttore del fan-out (FR-019) |
| `combined_graph_max_symbols` (`SERTOR_COMBINED_GRAPH_MAX_SYMBOLS`) | `3` | tetto dei punti d'ingresso (FR-023) |
| `combined_match_min_overlap` (`SERTOR_COMBINED_MATCH_MIN_OVERLAP`) | `2` | soglia del confronto lessicale (FR-023a) |

**Motivazione:** Principio VIII — i default vivono **solo** in `Settings`, mai nei componenti.
L'interruttore nasce spento perché il gate non è ancora stato superato (FR-019), il che rende la
consegna additiva per costruzione (SC-007).

---

## R13 — Serializzazione v1

**Decisione:** JSON annidato, chiavi nell'ordine `docs`, `code`, `graph`. **Non** la resa a blocchi
etichettati nell'ordine prescritto dalla design note §3.2.

**Motivazione:** i tool di questo server restituiscono dizionari, e i dizionari Python preservano
l'ordine di inserzione nella serializzazione. Imporre l'ordine di §3.2 richiederebbe una **resa
testuale**, che è precisamente l'oggetto delle affermazioni non misurate 7 e 8 della design note:
sceglierla adesso significherebbe decidere per gusto ciò che va deciso per misura.

**Marcata provvisoria.** La resa alternativa e il suo A/B sono fuori ambito di questa feature e
tracciati come estensione.

---

## R14 — Blindatura delle invarianti della valutazione

**Decisione:** promuovere il letterale `1.0` di `RoutedEvalEngine.query` a costante nominata
`_GRAPH_SCORE_SENTINEL`, e aggiungere due test:

1. **Instradamento esclusivo** — un motore fittizio che fallisce il test se invocato su un caso
   strutturale, e un grafo fittizio che fallisce se invocato su un caso non strutturale.
2. **Indipendenza dal segnaposto** — eseguire la valutazione due volte con il segnaposto sostituito da
   due valori diversi e asserire report **identici campo per campo**.

**Motivazione:** entrambe le proprietà sono **già vere** (verificato su `services/eval/runner.py:76-84`),
ma niente le protegge. Il secondo test è quello che conta davvero: se un domani una metrica leggesse
lo score, il segnaposto smetterebbe di essere cosmetico e la valutazione misurerebbe una politica di
fusione inesistente in produzione — un difetto silenzioso, del tipo peggiore.

**Vincolo di scrittura del test:** `RoutedEvalEngine` passa l'**intera query** a `find_symbol`, quindi
i casi di prova devono usare query che *sono* nomi di simbolo, com'è nella suite reale.

---

## R15 — La via d'ingresso per espansione semantica resta fuori

**Decisione:** **rinviata**, non implementata in questa feature.

**Motivazione:** i risultati che provengono dal solo ramo lessicale sono costruiti **senza metadata**
(`engines/hybrid.py:200-203`), quindi non trasportano il `qualname`: l'espansione avrebbe copertura
parziale e non dichiarabile a priori. Sanare quella costruzione è una modifica al motore ibrido con
un proprio rischio di regressione, e merita un requisito proprio anziché entrare di straforo in questa
feature.

**Conseguenza sul gate:** il fan-out viene misurato con le sole vie deterministiche. Se il beneficio
risulta scarso, resta aperta la possibilità che sia la copertura degli ingressi il fattore limitante —
e questa è un'ipotesi da verificare, non una scusa da invocare a posteriori.
