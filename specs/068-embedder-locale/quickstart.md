# Quickstart — Embedder locale (FEAT-011)

**Rigenerato (2026-06-21):** `RAG_BACKEND` rimosso; provider via `SERTOR_EMBED_PROVIDER` (default `glove`).
Tutti gli accessi sono **via vehicle** (`sertor-rag`), mai importando `sertor_core` (Principio XI).

## 1. Zero-config (default GloVe) — US1

Su una macchina senza Ollama e senza credenziali cloud, senza alcuna manopola:
```powershell
sertor-rag index .      # prima volta: scarica glove.6B.zip (~822 MB, avviso) → cache utente
sertor-rag search "come funziona la cache degli embeddings"
```
Atteso: indicizzazione e ricerca riescono; risultati non vuoti per query NL. Default = `glove:300`.

## 2. Airgapped / offline (pavimento lessicale) — US2

Nessuna rete, nessun download:
```powershell
$env:SERTOR_EMBED_PROVIDER = "hash"
sertor-rag index .
sertor-rag search "build_indexer"
```
Atteso: funziona senza scaricare nulla; avviso «ricerca NL limitata»; identificatori OOV contribuiscono
segnale. Stessi input → stessi vettori anche su altra macchina/altro Python.

## 3. Airgapped con GloVe da percorso esplicito — US3

Si fornisce il file 300d a mano (nessun download tentato):
```powershell
$env:SERTOR_EMBED_PROVIDER = "glove"
$env:SERTOR_GLOVE_PATH = "D:\data\glove.6B.300d.txt"
sertor-rag index .
```

## 4. Upgrade a Ollama / Azure — US1.4

```powershell
$env:SERTOR_EMBED_PROVIDER = "ollama"   # oppure "azure" (richiede credenziali Azure OpenAI)
sertor-rag index .
```
Atteso: upgrade senza toccare codice; comportamento e costo di Ollama/Azure identici a oggi.

## 5. Fail-loud (GloVe assente, no path, no rete) — US4

```powershell
$env:SERTOR_EMBED_PROVIDER = "glove"   # cache vuota, niente SERTOR_GLOVE_PATH, niente rete
sertor-rag index .
```
Atteso: **errore azionabile** (`GloveUnavailableError`) che nomina `SERTOR_GLOVE_PATH` **e**
`SERTOR_EMBED_PROVIDER=hash`. Nessun degrado silenzioso. Un valore di manopola non valido →
`ConfigError` che nomina la manopola e i valori ammessi.

## 6. Migrazione da `RAG_BACKEND`

Chi usava `RAG_BACKEND=azure` (incl. il dogfood `.sertor/.env`):
```powershell
# PRIMA (non più onorato → warning all'avvio):  RAG_BACKEND=azure
# DOPO:
$env:SERTOR_EMBED_PROVIDER = "azure"   # se vuoi gli embeddings Azure
# lo store si sceglie a parte:
$env:SERTOR_STORE_BACKEND = "azure"    # oppure "local" (default)
```
Se `RAG_BACKEND` resta nell'ambiente, Sertor emette un warning che non è più onorato e nomina le manopole
sostitutive (non cambia comportamento di nascosto). La `.sertor/.env` va aggiornata a mano (il codice non la
tocca).

## 7. Eval/CI offline (abilita FEAT-003)

```powershell
$env:SERTOR_EMBED_PROVIDER = "hash"    # deterministico, zero-rete
sertor-rag eval run                    # gate di non-regressione senza cloud
```
