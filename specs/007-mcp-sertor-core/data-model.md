# Data Model — Server MCP di produzione (`sertor_mcp`)

**Phase 1**. Il server non possiede uno storage proprio: modella solo l'**input di configurazione**,
l'**input dei tool** e la **forma del risultato** restituito al client. Le entità di dominio del
retrieval (Document, Chunk, RetrievalResult) appartengono a `sertor_core`.

## Entità di configurazione (input, da `sertor_core.config.Settings`)

| Campo | Origine | Ruolo nel server | Default |
|-------|---------|------------------|---------|
| `corpus` | env `SERTOR_CORPUS` | namespace logico dell'indice da interrogare | `default` nel core; **`sertor`** via binding del repo |
| `backend` | env `RAG_BACKEND` | `local` (Chroma+Ollama) · `azure` (Azure AI Search+Azure OpenAI) | `local` |
| (provider/parametri) | `Settings` | risolti dal core (embedder, store, `default_k`, collection) | — |

> Il server **non** introduce default propri di dominio: legge `Settings`, costruisce la facade,
> usa ciò che il core decide (Principio VIII/X).

## Input dei tool

Tutti e tre i tool condividono la stessa firma logica:

| Parametro | Tipo | Obbligatorio | Significato |
|-----------|------|--------------|-------------|
| `query` | string | sì | testo della ricerca in linguaggio naturale |
| `k` | integer | no | numero massimo di risultati; se omesso, default del motore (`Settings.default_k`) |

## Forma del risultato (output, per ogni hit)

Lista di oggetti con **campi stabili e identici** tra i tre tool (derivati da `RetrievalResult`):

| Campo | Tipo | Derivazione | Note |
|-------|------|-------------|------|
| `path` | string | `RetrievalResult.path` | path del documento (id stabile = path relativo) |
| `source` | string | `RetrievalResult.doc_type.value` | `"code"` o `"doc"` |
| `chunk` | string | `RetrievalResult.chunk_id` | identificatore del chunk (`path#indice`) |
| `score` | number | `RetrievalResult.score` (arrotondato) | pertinenza |
| `preview` | string | `RetrievalResult.text` normalizzato | troncato a soglia (`_PREVIEW`) con marcatore se eccede |

**Invarianti**:
- Il set di chiavi è identico per `search_code`, `search_docs`, `search_combined` (FR-010/REQ-042).
- `source ∈ {"code","doc"}`; per `search_code` tutti `"code"`, per `search_docs` tutti `"doc"`,
  per `search_combined` misti (FR-003).
- `preview` non supera la soglia + marcatore (FR-011/RNF-007).
- Lista **vuota** ammessa e significativa (indice assente / nessun hit) — non è un errore (FR-012).

## Stato interno del server

| Elemento | Tipo | Ciclo di vita |
|----------|------|----------------|
| facade del core | `RetrievalFacade` | costruita una volta (memoizzata), riusata tra le chiamate (R3) |
| istanza `FastMCP` | server MCP | una per processo; espone i tool e le istruzioni |
| soglia anteprima `_PREVIEW` | costante | parametro di presentazione del server |

Nessuno stato persistente, nessuna mutazione: il server è **sola lettura** (FR-004/Principio VI).
