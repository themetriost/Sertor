# Quickstart — Contratto di retrieval verso l'agente

**Feature**: `118-contratto-retrieval-agente` · **Data**: 2026-07-24

Tutti i comandi in **PowerShell**, dalla radice del repo.

---

## 1. Verificare l'additività (a interruttore spento)

Il default è **spento**: la risposta deve essere identica a quella di prima della feature.

```powershell
uv run --project .sertor sertor-rag search "come funziona la cache degli embeddings" --json
```

Atteso: due flussi (`docs`, `code`), **nessuna chiave `graph`**, nessun `corroborated_by`.

---

## 2. Accendere il flusso strutturale

```powershell
$env:SERTOR_COMBINED_GRAPH = "true"
uv run --project .sertor sertor-rag search "chi chiama build_indexer" --json
```

Atteso: tre flussi. Il ramo `graph` con `entry_points` che dichiara
`{"symbol": "build_indexer", "source": "extracted_from_query"}` — l'identificatore era scritto nella
domanda.

### Le tre indisponibilità, distinte

```powershell
# (a) grafo mai costruito
$env:SERTOR_GRAPH = "false"; uv run --project .sertor sertor-rag index .    # indicizza senza costruire il grafo
uv run --project .sertor sertor-rag search "chi chiama build_indexer" --json
#   → graph.status = "unavailable", reason = "graph_not_built"

# (b) libreria di navigazione assente  (in un ambiente senza l'extra `graph`)
#   → reason = "navigation_library_missing"

# (c) artefatto illeggibile
#   (corrompere una copia dell'artefatto in un index_dir di prova)
#   → reason = "graph_artifact_unusable"
```

Le tre cause hanno **rimedi diversi** — indicizzare, installare l'extra, re-indicizzare — ed è per
questo che il contratto le tiene separate.

### Il caso a costo zero

```powershell
uv run --project .sertor sertor-rag search "perche' abbiamo scelto questo approccio" --json
```

Atteso: `graph.status = "not_attempted"`, `entry_points` vuoto. Nessun accesso al grafo: una domanda
concettuale che non nomina né implica alcun simbolo **non paga nulla**.

---

## 3. Verificare la descrizione derivata dalla configurazione

```powershell
$env:SERTOR_ENGINE = "hybrid"
# la descrizione dei tool di ricerca dichiara che il punteggio e' un valore di fusione per rango
# e aggiunge poco rispetto all'ordine

$env:SERTOR_ENGINE = "baseline"
# la stessa descrizione dichiara che il punteggio e' una similarita', confrontabile solo entro la
# propria lista
```

In entrambe le configurazioni è dichiarata l'**asimmetria**: il valore su cui si decide l'astensione e
quello mostrato sono grandezze diverse.

---

## 4. Le invarianti della valutazione

```powershell
uv run pytest tests/unit/test_eval_routing_invariants.py -v
```

Due proprietà oggi vere ma finora non protette:

1. **instradamento esclusivo** — una domanda strutturale interroga *solo* il grafo, una non
   strutturale *solo* la ricerca per somiglianza;
2. **indipendenza dal segnaposto** — cambiando il valore fittizio assegnato ai risultati di grafo,
   l'esito della valutazione resta identico campo per campo.

Il secondo è quello che conta: se un domani una metrica leggesse quel punteggio, la valutazione
misurerebbe una politica di fusione **che in produzione non esiste**. Il test lo rende impossibile in
silenzio.

---

## 5. Le misure A/B (fuori dalla suite)

> ⚠️ Richiede un agente e **costa denaro**. Non gira in `uv run pytest`, per costruzione.

### 5.1 Registrare la regola PRIMA

```powershell
notepad eval_ab/README.md
```

**Vincolo non negoziabile** (FR-005/FR-006): la regola di decisione va scritta **prima** di eseguire.
Deciderla dopo aver visto i numeri è esattamente il ragionamento che il requisito vieta — e un
risultato ottenuto senza regola registrata **non è utilizzabile** per decidere.

### 5.2 Catturare i payload

```powershell
uv run python eval_ab/capture.py
```

Cattura via **vehicle** (CLI/MCP), non importando la libreria: è l'unico modo per avere la forma reale
che l'agente riceve.

### 5.3 Le misure

```powershell
# 6b — sotto motore ibrido: il punteggio serve o e' peso morto?
$env:SERTOR_ENGINE = "hybrid";   uv run python eval_ab/drive.py --measure score --variant strip_scores

# 6a — sotto motore vettoriale: stessa domanda, motore diverso
$env:SERTOR_ENGINE = "baseline"; uv run python eval_ab/drive.py --measure score --variant strip_scores

# gate del fan-out — beneficio e non-regressione insieme
uv run python eval_ab/drive.py --measure fanout --variant strip_graph
```

Ogni caso è eseguito **3 volte** per arm. Se la variazione fra ripetizioni supera l'effetto misurato,
l'esito è **non conclusivo** — e va dichiarato tale, non riportato come risultato.

### 5.4 Applicare il gate

| Esito sulle domande **non** strutturali | Conseguenza |
|---|---|
| calo > 5 punti percentuali | la capacità **non si consegna** |
| calo ≤ 5 punti ma misurabile | si consegna **spenta**, attivabile su richiesta |
| nessun calo misurabile (+ beneficio confermato) | può essere **attiva di default** |

Le due soglie sono deliberatamente diverse: «la capacità è utile» e «è abbastanza sicura da accenderla
per tutti» sono due domande distinte, e un'unica soglia costringerebbe a sbagliarne una.

---

## 6. Riportare gli esiti dove sono nati

Chiuse le misure, gli esiti tornano nella design note che le ha generate:
`wiki/concepts/llm-facing-retrieval-contract.md` §8, dove le righe **«non misurato»** diventano
verdetti e il frontmatter esce da `in-review`.

È il ciclo che chiude la feature: un documento di design produce affermazioni confutabili, la feature
costruisce lo strumento per confutarle, e gli esiti tornano a correggere il documento.
