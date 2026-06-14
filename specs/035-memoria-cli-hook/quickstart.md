# Quickstart — Memoria da CLI + cattura automatica (035)

Giro minimo «archivia → ritrova», più la cattura automatica a fine sessione. Tutto **gated** su
`SERTOR_MEMORY` (default off, privacy-by-default).

## 0. Abilitare la memoria (opt-in)

```bash
export SERTOR_MEMORY=true          # default false: senza questo, i comandi danno errore azionabile
```
Con la memoria spenta:
```bash
sertor-rag memory archive
# error: memory is disabled; set SERTOR_MEMORY=true to enable archiving (key: SERTOR_MEMORY)   (exit 1)
```

## 1. Archiviare le sessioni del progetto

```bash
sertor-rag memory archive
# archived=3 skipped=0 errors=0

sertor-rag memory archive            # rilancio immediato: idempotente
# archived=0 skipped=3 errors=0

sertor-rag memory archive --json
# {"archived": 0, "skipped": 3, "errors": 0}
```

## 2. Ritrovare una conversazione

```bash
sertor-rag memory search "hybrid search"
# [1] score=0.91  role=assistant  session=<key>  turn=14  @=2026-06-13T18:02:11Z
#     …combina BM25 e dense con [hybrid search] e RRF…

# Con finestra temporale e limite:
sertor-rag memory search "retrieval" --since 2026-06-10 --until 2026-06-14 -k 5

# JSON consumabile a macchina:
sertor-rag memory search "retrieval" --json
# [{"session_key":"…","captured_at":1718...,"role":"user","turn_index":7,"snippet":"…","score":0.83}]
```
Finestra impossibile:
```bash
sertor-rag memory search "x" --since 2026-06-14 --until 2026-06-10
# error: invalid time window: since (...) is after until (...) — swap the bounds ...   (exit 1)
```

## 3. Cattura automatica a fine sessione (Claude Code)

Cablata nel dogfood di Sertor: a ogni fine sessione l'hook `.claude/hooks/memory-capture.ps1`
(voce in `.claude/settings.json` → `SessionEnd`) invoca `sertor-rag memory archive`,
**non-bloccante** e **non-fatale**.

- A `SERTOR_MEMORY` spento → l'hook non fa nulla e non stampa nulla (no-op silenzioso).
- Se l'archiviazione fallisce → la sessione si chiude comunque (errore assorbito).

Verifica manuale dell'hook:
```powershell
# memoria spenta → nessun output, exit 0
$env:SERTOR_MEMORY=$null; .\.claude\hooks\memory-capture.ps1; $LASTEXITCODE   # 0, niente output
# memoria accesa → invoca archive, exit 0 comunque
$env:SERTOR_MEMORY='true'; .\.claude\hooks\memory-capture.ps1; $LASTEXITCODE  # 0
```

## 4. Test (sviluppo)

```bash
uv run pytest tests/unit/test_cli_memory.py        # comandi con core mockato (stile test_cli_search)
```
I comandi si testano come gli altri `_cmd_*`: monkeypatch di `build_memory_archiver`/
`build_episodic_search` con fake che ritornano `ArchiveRunReport`/`EpisodicResults`, e con `None`
per il caso «memoria spenta → ConfigError». La logica di gate/no-op dell'hook PowerShell si verifica
con i due comandi manuali sopra (§3).
