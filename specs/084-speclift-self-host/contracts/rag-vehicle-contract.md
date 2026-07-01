# Contratto — Vehicle RAG (SpecLift → Sertor)

**Feature**: speclift FEAT-001 (self-host) · **Branch**: `084-speclift-self-host`

L'**unica** interfaccia esterna tra SpecLift e Sertor a runtime. Non è un import: è una **invocazione di
subprocess della CLI** (Principio XI). Questo contratto è già soddisfatto dalla CLI Sertor odierna
(verificato) — la feature lo **configura**, non lo modifica.

## Comando invocato

```text
uv run sertor-rag search <query> --type code --json -k 5
```

- **Chi lo invoca**: `speclift.adapters.rag_sertor.SertorRagLocator._search` (`rag_sertor.py:85-99`),
  con `cwd = <repo Sertor>` (default `.`), `_SEARCH_K = 5` (`rag_sertor.py:26`).
- **Vehicle** (self-host Sertor): `("uv", "run", "sertor-rag")` — costante `SERTOR_RAG_VEHICLE`
  patchata (`config.py:27`, divergenza tracciata in `VENDORING.md`). Nel repo Sertor il RAG vive a
  **root** (entry point `sertor-rag` di `sertor-core`, `pyproject.toml:22`), non in `.sertor/`.
- **Nessun altro sottocomando** è usato. `find_symbol`/`who_calls`/`search_docs`/`get_context` (MCP)
  **NON** sono invocati (onestà doc↔codice, Gruppo H).

## Ingresso

| Argomento | Valore | Note |
|-----------|--------|------|
| `query` | un identificatore candidato o (fallback) la 1ª riga dello snippet se è un singolo identificatore | `rag_sertor.py:42-83`, dedup, cap `MAX_QUERIES_PER_SYMBOL=4` |
| `--type` | `code` | l'array piatto è preservato; `--type both` (feature 070) NON usato |
| `--json` | flag | output machine-readable |
| `-k` | `5` | `_SEARCH_K` |

## Uscita attesa (dalla CLI Sertor)

Un **array JSON piatto**; ogni elemento è un dict con **almeno** `path` (opzionale `chunk_id`):

```json
[
  {"path": "src/sertor_core/composition.py", "doc_type": "code",
   "chunk_id": "src/sertor_core/composition.py#12", "score": 0.31, "preview": "…"}
]
```

Ancoraggio Sertor: `src/sertor_core/cli/__main__.py:124-131` (parser `search`),
`cli/output.py:95-109` (resa `--json --type code` = array piatto). SpecLift legge **solo** `path`
(obbligatorio) e `chunk_id` (opzionale, → `Symbol.provenance`/`TestRef.provenance`);
la **riga** del simbolo **non** è fornita dalla CLI → l'àncora usa le righe dell'hunk (`line=0`,
`rag_sertor.py:55`).

## Fallimento (fail-loud, Principio XII)

| Condizione | Effetto SpecLift | Ancora |
|------------|------------------|--------|
| Vehicle exit≠0 (es. `sertor-rag` assente, `IndexNotFoundError`) | `RagUnavailableError` → **exit 3** | `rag_sertor.py:89-90,120-124` |
| Output non-JSON | `RagUnavailableError` («indice mancante o errore?») | `rag_sertor.py:91-96` |
| JSON non-lista | `RagUnavailableError` («atteso un array JSON») | `rag_sertor.py:97-99` |

- **Must (FR-007):** exit 3 + messaggio esplicito su stderr, mai risultati vuoti/fabbricati.
  Comportamento **upstream invariato**.
- **Should (FR-008):** il messaggio raccomanda `sertor-rag index .` dalla root (divergenza D-3 nel
  messaggio vendorato). Rimedio concreto, non un generico «RAG non raggiungibile».
- Gli stadi che **non** toccano il RAG (`ingest`/`parse_diff`/`filter_sources`) restano operativi
  senza indice (RNF-4).

## Invarianti del contratto

1. **Vehicle-only** (Principio XI): mai `import sertor_core`. Puro subprocess con vehicle fisso, niente
   shell (`rag_sertor.py:113`).
2. **Stabilità**: la superficie usata (`search --type code --json`) è stretta e stabile; non impattata
   dai breaking change delle superfici fuse (feature 070).
3. **Determinismo** (RNF-6): la marcia `bundle`/`assemble` è deterministica; il RAG *propone*, il
   filesystem *dispone* (moat, `anchor_fs.py:26-62`).
