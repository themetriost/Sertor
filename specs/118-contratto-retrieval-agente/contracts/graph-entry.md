# Contratto — risoluzione dei punti d'ingresso al grafo

**Modulo**: `services/graph_entry.py` · **Natura**: funzioni **pure**, zero I/O, zero LLM · **Feature**: 118

Il grafo vuole un nome esatto; la domanda è prosa. Queste funzioni sono il ponte, e sono
**deterministiche**: a parità di input, stesso output (RNF-2).

---

## `extract_identifiers(query: str) -> list[str]`

Estrae dalla domanda i token che **hanno forma di identificatore**.

**Riconosce:** maiuscole interne (`CachingEmbedder`) · underscore (`build_indexer`) · notazione puntata
(`Settings.load`).

**Non riconosce:** parole tutte minuscole senza separatori — `cache`, `index` — che in prosa italiana o
inglese sono parole comuni e aggancerebbero qualunque cosa.

**Ordine:** di prima apparizione nella domanda. **Duplicati:** rimossi.

| Domanda | Esito |
|---|---|
| `come funziona CachingEmbedder?` | `["CachingEmbedder"]` |
| `chi chiama build_indexer e Settings.load?` | `["build_indexer", "Settings.load"]` |
| `come funziona la cache degli embedding?` | `[]` |

---

## `match_symbol_table(query, qualnames, min_overlap=2) -> list[str]`

Confronta il **vocabolario della domanda** con le **parti dei nomi qualificati** noti al grafo.

**Procedura:**
1. ogni `qualname` è spezzato in parti su CamelCase, underscore e punto, e ridotto a minuscolo
   (`CachingEmbedder` → `{caching, embedder}`);
2. la domanda è spezzata in parole, minuscole;
3. un simbolo è **candidato** se il suo nome intero compare nella domanda (match forte, sempre valido)
   **oppure** se almeno `min_overlap` parti **distinte** compaiono fra le parole della domanda.

**Ordine:** per numero di parti coincidenti (decrescente), poi alfabetico — deterministico anche a
parità di punteggio.

| Domanda | `qualnames` disponibili | Esito | Perché |
|---|---|---|---|
| `la classe che fa caching degli embedding` | `CachingEmbedder`, `EmbeddingCache`, `IndexingService` | `["CachingEmbedder", "EmbeddingCache"]` | 2 parti su 2 per entrambi |
| `come funziona l'indicizzazione` | `IndexingService` | `[]` | «indicizzazione» ≠ `indexing`: **lexical gap** |
| `parlami di CachingEmbedder` | `CachingEmbedder` | `["CachingEmbedder"]` | nome intero presente |
| `cosa fa la cache` | `CachingEmbedder`, `EmbeddingCache` | `[]` | una sola parte in comune, sotto soglia |

**Il limite è dichiarato, non nascosto.** La via copre la sovrapposizione fra il vocabolario della
domanda e le **parti** dell'identificatore, non «il concetto». Domande in italiano su identificatori
inglesi cadono nel *lexical gap* e producono `[]` — che è un esito **onesto** (`not_attempted`, costo
nullo), non un errore.

**Perché `min_overlap = 2`:** con 1 una domanda contenente «index» pescherebbe ogni simbolo con
«index» nel nome, pagando il costo di contesto dove il beneficio è nullo; con 3 si ricade di fatto sul
nome intero. Due è il primo valore che discrimina — ed è configurabile, da tarare sulla misura.

---

## `resolve_entry_points(query, qualnames, *, max_symbols=3, min_overlap=2) -> list[EntryPoint]`

Compone le vie e produce l'elenco finale.

**Ordine di precedenza** (dal più affidabile al meno):

1. `extract_identifiers` → `source="extracted_from_query"` — l'identificatore è *scritto* nella domanda
2. `match_symbol_table` → `source="symbol_table_match"` — sovrapposizione lessicale

> **Non c'è una via «simboli dichiarati dal chiamante».** Richiederebbe un parametro sul tool per
> nominarli, che questa feature non espone — e la spec la dichiara «la meno giustificata, la prima da
> tagliare». Prevederla nel tipo senza produrla mai sarebbe YAGNI, la stessa ragione per cui è
> rinviata la via per espansione semantica.

**Deduplica** per `symbol`, conservando la **prima** provenienza (cioè la più affidabile).
**Taglia** a `max_symbols`.

**Restituisce `[]`** quando nessuna via produce candidati → il chiamante riporta `not_attempted` e
**non tocca il grafo** (costo nullo).

### Perché quest'ordine

Un identificatore che l'utente ha *scritto* è un segnale più forte di una sovrapposizione lessicale
dedotta. A parità di tetto, i posti disponibili vanno agli ingressi di cui ci si può fidare di più — e
poiché `source` viaggia fino all'agente, questi può **scontare** i risultati che arrivano da un
ingresso debole invece di prenderli per buoni.

### Invarianti verificabili

- `len(result) <= max_symbols`
- nessun `symbol` ripetuto
- output identico a input identico (nessuna dipendenza da ordinamenti instabili)
- `result == []` ⟹ il grafo non viene interrogato
- ogni `EntryPoint` porta una `source` fra le tre previste (mai vuota, mai inferita a valle)
