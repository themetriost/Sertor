# Quickstart — Cattura & archiviazione locale dei transcript (031)

**Feature**: `031-cattura-archiviazione`. Capacità di **core** (libreria): nessuna UI nuova in questa
feature (la ricerca è FEAT-002, fuori ambito). Privacy-by-default: **spenta** salvo opt-in.

## Abilitare la cattura

```bash
# .sertor/.env (o variabili d'ambiente)
SERTOR_MEMORY=true                       # opt-in esplicito (default: false → nessuna scrittura)
SERTOR_MEMORY_ADAPTER=claude-code        # adapter sorgente (default: claude-code)
# opzionali:
SERTOR_MEMORY_RETENTION_DAYS=            # gancio: nessuna scadenza se vuoto (enforcement = FEAT-006)
SERTOR_MEMORY_SCRUB_PATTERNS=GH_PAT_[A-Za-z0-9]+,glpat-[A-Za-z0-9]+   # regex extra (CSV)
```

A `SERTOR_MEMORY=false` (default) **nessun** adapter o store è istanziato, **nessun** file è aperto.

## Uso come libreria (dal composition root)

```python
from sertor_core.composition import build_memory_archiver
from sertor_core.config.settings import Settings

settings = Settings.load()
archiver = build_memory_archiver(settings)   # None se SERTOR_MEMORY=false
if archiver is not None:
    report = archiver.archive_all()
    print(f"archiviate={report.archived} saltate={report.skipped} errori={report.errors}")
```

Ri-eseguire `archive_all()` è **idempotente**: le sessioni già presenti risultano `skipped`, nessun
duplicato, i record esistenti restano invariati.

## Dove finisce l'archivio

`<index_dir>/memory.sqlite` (es. `.sertor/.index/memory.sqlite`), **gitignored** (coperto da
`**/.index/` in `.gitignore`), namespaced per progetto. Mai sotto controllo di versione, mai remoto.

## Verifiche rapide (mappate ai Success Criteria)

| Verifica | Come | SC |
|---|---|---|
| N sessioni → N record, 0 duplicati | mock adapter con N sessioni, `archive_all()`, contare `get` | SC-001 |
| Idempotenza | rieseguire → `skipped=N`, archivio invariato | SC-002, SC-006 |
| Off = 0 scritture | `SERTOR_MEMORY=false`, nessun file `memory.sqlite` creato | SC-003 |
| Segreti ripuliti | turno con `sk-...`/bearer/`PASSWORD=...` → 0 occorrenze in chiaro | SC-004 |
| Host-agnostico | 2 mock adapter diversi → stesso comportamento | SC-005 |
| Degradazione non-fatale | store corrotto → warning, esecuzione prosegue | SC-007 |

## Test offline

```bash
uv run pytest tests/unit/test_memory_archive.py tests/unit/test_scrub.py \
              tests/unit/test_claude_code_capture.py -q
```

Tutti i test girano **senza rete e senza Claude Code reale**: adapter mock + `tmp_path` per lo store,
file JSONL sintetici per il parser difensivo (Principio V).

## Adapter Claude Code (prima implementazione)

Legge `~/.claude/projects/<encoded-project-path>/<session-id>.jsonl` (encoding: i separatori del path
assoluto del progetto → `-`, es. `C:\Workspace\Git\Sertor` → `C--Workspace-Git-Sertor`). Estrae i turni
`user`/`assistant` (block `text`/`thinking`), best-effort: righe non parsabili saltate con warning, mai
fatale. Sola lettura. La conoscenza host-specifica vive **solo** in questo adapter (Principio X).
