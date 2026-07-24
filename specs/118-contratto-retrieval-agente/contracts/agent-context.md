# Contratto — payload della ricerca combinata con flusso strutturale

**Schema**: `agent.context/1` · **Superficie**: tool MCP `search_combined` · **Feature**: 118

## Forma

### A interruttore spento (default)

Invariata rispetto a oggi — **byte per byte** (SC-007):

```json
{
  "docs": [ { "path": "...", "source": "doc",  "chunk": "...#3", "score": 0.0321, "preview": "..." } ],
  "code": [ { "path": "...", "source": "code", "chunk": "...#0", "score": 0.0318, "preview": "..." } ]
}
```

### A interruttore acceso

Si aggiunge **una sola chiave**, `graph`. Le due esistenti non cambiano forma, salvo il campo
opzionale `corroborated_by` sugli item che il grafo conferma.

```json
{
  "docs": [ { "path": "...", "source": "doc", "chunk": "...#3", "score": 0.0321, "preview": "..." } ],
  "code": [
    {
      "path": "src/sertor_core/adapters/embeddings/cache.py",
      "source": "code",
      "chunk": "src/sertor_core/adapters/embeddings/cache.py#2",
      "score": 0.0318,
      "preview": "...",
      "corroborated_by": ["CachingEmbedder"]
    }
  ],
  "graph": {
    "status": "partial",
    "entry_points": [
      { "symbol": "CachingEmbedder", "source": "symbol_table_match" }
    ],
    "symbols": [
      {
        "qualname": "CachingEmbedder",
        "definitions": {
          "status": "ok",
          "shown": 1,
          "total": 1,
          "items": [
            {
              "path": "src/sertor_core/adapters/embeddings/cache.py",
              "line": 98,
              "kind": "class",
              "qualname": "CachingEmbedder",
              "ref": "src/sertor_core/adapters/embeddings/cache.py#CachingEmbedder",
              "corroborated_by": ["src/sertor_core/adapters/embeddings/cache.py#2"]
            }
          ]
        },
        "callers":  { "status": "ok",          "shown": 8, "total": 47, "items": [ ... ] },
        "callees":  { "status": "empty",       "shown": 0, "total": 0,  "items": [] },
        "docs":     { "status": "unavailable", "shown": 0, "total": 0,  "items": [],
                      "reason": "graph_artifact_unusable" }
      }
    ]
  }
}
```

## Regole vincolanti

### 1. Additività

A `combined_graph_enabled = false` la risposta **non contiene** la chiave `graph`, e nessun item porta
`corroborated_by`. Un consumatore scritto prima di questa feature non vede alcuna differenza.

### 2. `status` è derivato, mai dichiarato

Il produttore **non** imposta `status`: lo calcola dai blocchi sottostanti. Un consumatore che legge
`partial` sa che deve guardare i livelli inferiori; `ok` gli garantisce che non c'è nulla di parziale
sotto.

**Invariante osservabile:** `status == "not_attempted"` ⟺ `entry_points` è vuoto.

### 3. Il vuoto non è mai ambiguo

| Cosa vede il consumatore | Cosa può concludere |
|---|---|
| `status: "not_attempted"` | *«non è stato guardato»* — nessuna conclusione sull'esistenza |
| blocco con `status: "empty"` | *«guardato, non c'è»* — **conclusione di assenza legittima** |
| blocco con `status: "unavailable"` + `reason` | *«non si è potuto guardare»* — nessuna conclusione |

Un blocco `unavailable` **DEVE** portare `reason`. Le tre cause globali sono:

| `reason` | Significato | Rimedio per l'utente |
|---|---|---|
| `graph_not_built` | l'artefatto non esiste | indicizzare il corpus |
| `navigation_library_missing` | la capacità di navigazione non è installata | installare l'extra `graph` |
| `graph_artifact_unusable` | artefatto illeggibile o di formato ignoto | re-indicizzare |

Le tre cause hanno **rimedi diversi**: conflatarle renderebbe il messaggio inutile.

### 4. Il troncamento è dichiarato solo dove può mentire

`shown` e `total` compaiono **nei blocchi del grafo**, che sono insiemi esaustivi per costruzione:
mostrarne una parte senza dirlo farebbe passare un sottoinsieme per il tutto.

**Non** compaiono nei flussi `docs`/`code`: lì il taglio top-k è **costitutivo** — su un corpus intero
ogni documento ha una similarità, «totale» non ha senso insiemistico, e la classifica non pretende
esaustività (FR-031).

### 4-bis. `source` ha due soli valori possibili

`extracted_from_query` (l'identificatore era scritto nella domanda) · `symbol_table_match`
(sovrapposizione lessicale con i nomi noti al grafo). Sono le **sole due vie prodotte** da questa
feature: la via per espansione dai risultati semantici è rinviata, e quella per simboli dichiarati dal
chiamante richiederebbe un parametro sul tool che qui non si espone.

Il consumatore può quindi trattare `extracted_from_query` come l'ingresso **più affidabile** dei due, e
scontare di conseguenza i risultati che arrivano dall'altro.

### 5. La corroborazione è bilaterale

Quando una posizione compare in entrambi i mondi:

- l'item del flusso di somiglianza porta `corroborated_by: [qualname, ...]`
- il risultato strutturale porta `corroborated_by: [chunk_id, ...]`

**Nessun dedup fra flussi** (FR-033): la convergenza di due metodi indipendenti è un segnale, e
rimuoverne una metà lo nasconderebbe.

*Limite v1 dichiarato:* il confronto avviene **sul solo path**. Un file con molte definizioni
corrobora qualunque chunk dello stesso file — grossolano, e registrato come tale.

### 6. Il punteggio e il suo ambito

Il campo `score` **resta** nei flussi di somiglianza, ma il suo ambito di validità è dichiarato nella
**descrizione del tool**, non nel payload (sarebbe una costante ripetuta a ogni chiamata):

> Confrontabile **solo entro la propria lista**. Mai fra flussi, mai fra ricerche, mai come misura
> assoluta di qualità.

E il testo **cambia con la configurazione**: sotto motore a fusione per rango dichiara che il
punteggio aggiunge poco rispetto all'ordine; sotto motore vettoriale che è una similarità. Dichiara
inoltre che il valore su cui si decide l'astensione e quello mostrato sono **grandezze diverse**.

*Il destino definitivo del campo lo decide la misura (FR-017), non questo contratto.*

## Osservabilità

Ogni ricerca con interruttore acceso emette un evento con: numero di punti d'ingresso risolti, la loro
provenienza, lo `status` risultante e, se `unavailable`, la causa. Una risoluzione a vuoto è
**osservabile** — è il caso normale, ma il suo tasso è ciò che dice se la selezione degli ingressi
funziona.
