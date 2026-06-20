# Quickstart — Ground-truth & valutazione della pertinenza (FEAT-001)

> Comandi in **PowerShell** (Windows). Presuppone il progetto **già indicizzato** (RAG) — la
> valutazione misura un indice esistente, non lo costruisce.

## 0. Prerequisito: indicizza il progetto
```powershell
uv run sertor-rag index .
```

## 1. Crea la suite (a mano)
Crea `eval/suite.toml` a root del progetto (dato **versionato**), oppure aggiungi casi via CLI:
```powershell
uv run sertor-rag eval add-case --query "EmbeddingProvider" `
    --expected "src/sertor_core/domain/ports.py" --kind symbol
```
Se un path atteso non è nell'indice, il comando avvisa e chiede `--confirm` prima di scriverlo (REQ-012):
```powershell
uv run sertor-rag eval add-case --query "vecchia funzione" `
    --expected "src/old/removed.py" --confirm
```
Forma del file (vedi `contracts/artifacts-toml.md`):
```toml
[[case]]
query = "EmbeddingProvider"
expected = ["src/sertor_core/domain/ports.py"]
kind = "symbol"
```

## 2. Esegui la valutazione
```powershell
uv run sertor-rag eval run
# hit@1=…  hit@5=…  mrr=…  + dettaglio per-query hit/miss
uv run sertor-rag eval run --json    # stessa informazione in JSON
```
Due esecuzioni a parità di indice+suite danno **metriche identiche** (determinismo, REQ-035).

## 3. Registra la baseline e attiva il gate di non-regressione
```powershell
uv run sertor-rag eval run --record-baseline   # scrive eval/baseline.toml (versionato)
```
Da ora, un run sotto baseline oltre tolleranza **esce con stato non-zero** (gate):
```powershell
uv run sertor-rag eval run
# … non-regression: REGRESSED → exit 1   (oppure PASS → exit 0)
echo $LASTEXITCODE
```
Tolleranza configurabile (default `0.0`):
```powershell
$env:SERTOR_EVAL_TOLERANCE = "0.02"   # ammette fluttuazioni fino a 0.02
```
Aggiorna la baseline **solo** quando accetti esplicitamente un nuovo livello:
```powershell
uv run sertor-rag eval run --record-baseline
```

## 4. Confronta due configurazioni locali (REQ-034)
```powershell
uv run sertor-rag eval run --compare baseline,hybrid
# tabella affiancata: hit@k e mrr per ciascuna config, in locale (no cloud)
```

## 5. (P2) Genesi assistita dall'agente — skill
La skill `derive-eval-suite` (FEAT-008) fa **proporre** all'agente candidati `query → atteso` letti dal
corpus via i tool RAG/MCP; tu approvi; solo gli approvati sono persistiti via `eval add-case`. Il run
deterministico (passi 2–4) **non dipende mai** dalla skill né da un LLM.

## Esito atteso
- metriche `hit-rate@k`/`MRR` ripetibili (umano + JSON) con dettaglio per-query (SC-001);
- suite e baseline **dentro il progetto** (`eval/`), versionate, senza copiare file da Sertor (SC-002);
- gate di non-regressione funzionante (SC-004);
- su un host pulito dopo `sertor install`, i passi 1–4 funzionano dal percorso di installazione (SC-008);
- a comando non invocato, indice/ricerca/costo identici a oggi (SC-009).
