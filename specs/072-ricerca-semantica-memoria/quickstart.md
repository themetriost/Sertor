# Quickstart — Ricerca semantica della memoria (FEAT-004)

**Branch**: `072-ricerca-semantica-memoria` · **Data**: 2026-06-22

Percorso opt-in a strati per ritrovare conversazioni passate **per significato** (non per parola).
Tutto on-machine col provider locale di default (FEAT-011). PowerShell (Windows).

## 1. Abilitare (due strati di opt-in)

```powershell
# Strato 1: cattura (FEAT-001) — già richiesto per avere un archivio
$env:SERTOR_MEMORY = "true"
# Strato 2: semantica (questa feature) — opt-in ULTERIORE e distinto, default off
$env:SERTOR_MEMORY_SEMANTIC = "true"
# Provider di embeddings: locale di default (glove) → contenuto on-machine, zero rete
#   (per restare offline NON impostare un provider cloud)
$env:SERTOR_EMBED_PROVIDER = "glove"
```

Accendere solo `SERTOR_MEMORY` **non** accende mai l'embedding (REQ-003). Accendere solo
`SERTOR_MEMORY_SEMANTIC` senza la cattura → semantica inattiva, dipendenza segnalata (REQ-002).

## 2. Indicizzare

```powershell
# Auto a fine sessione: `memory archive` (o hook SessionEnd) embedda anche le sessioni appena
# archiviate, quando la semantica è opt-in — nessun passo manuale per la freschezza.
uv run sertor-rag memory archive

# Backfill delle sessioni catturate PRIMA dell'opt-in (incrementale: solo le non ancora indicizzate).
uv run sertor-rag memory index-semantic
```

Una seconda esecuzione senza nuove sessioni → `embedded=0` (incrementalità O(nuovo), REQ-030/NFR-009).

## 3. Cercare per significato

```powershell
# Full-text (default invariato, FEAT-002): match per parola esatta
uv run sertor-rag memory search "min-score"

# Semantica: match per concetto (parole diverse, significato affine)
uv run sertor-rag memory search "astensione quando il punteggio è basso" --semantic

# Con finestra temporale (parità con la full-text)
uv run sertor-rag memory search "scelte sul backend" --semantic --since 1717000000

# JSON per consumo programmatico
uv run sertor-rag memory search "..." --semantic --json
```

Ogni risultato porta: `session_key`, `turn_index`, `captured_at`, `role`, `snippet`, `score`
(REQ-010), ordinato per similarità, tagliato a `SERTOR_MEMORY_SEMANTIC_LIMIT` (default 20).

## 4. Nessun fallback silenzioso

```powershell
$env:SERTOR_MEMORY_SEMANTIC = "false"
uv run sertor-rag memory search "..." --semantic
# → errore azionabile (exit 1): «semantic search not enabled — set SERTOR_MEMORY_SEMANTIC=true …»
#   MAI risultati full-text mascherati da semantici (REQ-015).
```

## 5. Privacy & rebuild

- **On-machine col locale**: con `glove`/`hash` index + query sono offline (zero rete). Con un
  provider **cloud** l'auto-index manda contenuto (già scrubbed) fuori macchina a ogni chiusura di
  sessione: implicazione **esplicita** (warning + questa nota), default locale la evita (REQ-019/020).
- **Cambio provider/dimensione** → la collezione cambia nome (namespacing per provider) → si ripopola
  incrementalmente al prossimo `memory archive`/`index-semantic`. È l'unico caso che ri-embedda lo
  storico, ed è esplicito (REQ-032).
- L'indice semantico è **derivato**: cancellarlo non tocca `memory.sqlite`; ricostruirlo dall'archivio
  produce un indice equivalente (REQ-029).

## Verifica (test offline, RNF-5/7)

```powershell
uv run pytest tests/unit/test_memory_semantic.py   # componente con embedder/store mock, no rete
uv run pytest -m "not cloud"
uv run ruff check .
```

> **Nota installer (debito tracciato, DA-SS-6):** le manopole `SERTOR_MEMORY_SEMANTIC*` e l'aggancio
> hook vanno cablati nel template `.env`/asset di `sertor install` — **FEAT-009** (owner). Finché non
> arriva, la feature è usabile via libreria/CLI ma non «completa = installabile».
