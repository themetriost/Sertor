# Data model — Pagine ASP.NET nel corpus (140)

Nessuna entità di **dominio** nuova: `Document`, `Chunk`, `ChunkMetadata`, `GraphNode`, `GraphEdge` restano
invariati. La feature aggiunge un **valore di servizio** (la proiezione) e due **valori di linguaggio**.

## Valori di linguaggio (`Document.language`, `ChunkMetadata.language`)

| Valore | Estensioni | Note |
|---|---|---|
| `webforms` | `.aspx`, `.ascx`, `.master`, `.asmx`, `.ashx` | handler/web service riconosciuti dalla direttiva (research D-3) |
| `razor` | `.cshtml`, `.razor` | |

`Document.doc_type` = `CODE` per entrambi. Le costanti vivono nel modulo della proiezione e sono importate da
ingestione e grafo (research D-8).

## `PageProjection` (servizio, immutabile)

Risultato puro e deterministico di `project_page(text, language)`.

| Campo | Tipo | Significato |
|---|---|---|
| `chunk_view` | `str` | C# dei blocchi (script avvolti nella sentinella, codice, blocchi Razor); tutto il resto spazi |
| `graph_view` | `str` | `chunk_view` + espressioni brevi come istruzioni `expr;` |
| `markup_view` | `str` | testo originale con i blocchi di codice sbiancati; espressioni e direttive restano |
| `server_language` | `str` | linguaggio dichiarato (`"C#"` di default) |
| `has_code` | `bool` | almeno un blocco di codice trovato |

**Invariante (verificata da test):** le tre viste hanno **lo stesso numero di `\n`** del testo originale.

**Regole di validazione**
- `server_language` diverso da C# (case-insensitive: `C#`, `cs`, `csharp`) → pagina degradata, motivo
  `server_language`.
- `chunk_view` con errori di parsing → pagina degradata, motivo `parse_error`.
- `has_code = False` → nessun chunk sintattico, solo chunk del markup, **nessun evento** (FR-013).

## Chunk di una pagina

| Origine | `chunker` | `language` | `qualname` / `symbol` / `node_type` | Righe |
|---|---|---|---|---|
| simbolo nel codice della pagina | `SYNTACTIC` | `webforms`/`razor` | `Stem.Metodo` fuori classe; regola C# in una classe dichiarata | del file originale |
| istruzioni globali (`<% %>`, `@{ }`) | `SYNTACTIC` | idem | `node_type = module`, senza simbolo | del file originale |
| markup | `SIZE_FALLBACK` | idem | — | del file originale |
| pagina degradata | `SIZE_FALLBACK` | idem | — | del file originale |

La classe sentinella `__page__` non produce chunk e non compare nel testo dei chunk.

## Grafo

| Elemento | Regola |
|---|---|
| nodo `module` | uno per pagina (come ogni documento di codice) |
| nodi simbolo | dai metadati dei chunk sintattici (meccanismo esistente) + dalla visita della `graph_view` |
| arco `contains` | gerarchia dei qualname (meccanismo esistente): `Default.Page_Load` → genitore assente → modulo |
| arco `calls` | dalla `graph_view`; chiamante = simbolo racchiudente, altrimenti il **modulo della pagina** (research D-7) |
| `COVERAGE` | `webforms` e `razor` derivate da `c_sharp` |

## Evento `aspnet_page_degraded`

| Campo | Valore |
|---|---|
| livello | `WARNING` |
| `path` | id del documento |
| `reason` | `server_language` \| `parse_error` |
| `detail` | linguaggio dichiarato, oppure riga (1-based) del primo nodo d'errore |
