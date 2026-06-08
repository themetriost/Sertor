# Implementation Plan: Meccanica del log del wiki (FEAT-008)

**Branch**: `spec/008-meccanica-log` · **Spec**: [spec.md](spec.md) · **Requisiti**:
`requirements/sertor-core/meccanica-log/requirements.md`

## Sintesi tecnica

Estensione del nucleo deterministico `src/sertor_core/wiki_tools/` (FEAT-003-D) per: (1) **rotazione** del
log a un file per giorno; (2) **write-back `append_log` curato** esposto in CLI; (3) **`migrate`** una-tantum
per splittare lo storico; (4) **indice** delle partizioni. Nessuna nuova dipendenza (stdlib only), offline,
host-agnostico via `wiki.config.toml`.

## Constitution Check

| Principio | Esito | Nota |
|---|---|---|
| I — Dipendenze verso l'interno | ✅ | resta in `wiki_tools`; dipende solo da `profile`/`contracts`/`errors`/`observability`; nessun SDK |
| II — Boundary & local-first | ✅ | offline, stdlib, nessuna rete |
| III — YAGNI | ✅ | nessun job di rotazione (implicita per data); nessuna nuova astrazione oltre 2 funzioni + 2 contratti |
| IV — Errori espliciti | ✅ | heading non valido / config assente → `ConfigError`; nessuno stato parziale |
| V — Testabilità | ✅ | funzioni pure su `tmp_path`; test offline F.I.R.S.T.; parità `scan` testabile |
| VI — Idempotenza & non-distruttività | ✅ | append idempotente sull'heading; `migrate` skippa partizioni esistenti, non cancella `log.md` |
| VII — Leggibilità | ✅ | naming di dominio (`partition`, `append_log`, `migrate_log`) |
| VIII — Config centralizzata | ✅ | `log_dir`/`log_index_file` da `wiki.config.toml`; nessun default d'ospite hard-coded |
| IX — Osservabilità | ✅ | `log_event` per ogni operazione (partizione, created, migrated) |
| X — Host-agnostico (NON-NEG.) | ✅ | tutta la specificità in config; `doc_only_host` continua a valere; modalità file-unico = back-compat |

**Complexity Tracking:** vuoto (nessuna violazione).

## Design

### Configurazione (`profile.py`, `wiki.config.toml`)
- Nuovi campi `WikiProfile`: `log_dir: str = ""` (vuoto → **modalità file-unico**, back-compat; valorizzato →
  **rotazione**), `log_index_file: str = "index.md"`.
- Nuove property: `rotation_enabled` (`log_dir != ""`), `log_dir_path` (`root_path/log_dir`),
  `partition_path(d: date)` (`log_dir_path/f"{d.isoformat()}.md"`), `log_index_path`
  (`log_dir_path/log_index_file`).
- `wiki.config.toml` (profilo Sertor): aggiungere `log_dir = "log"`.

### Write-back curato (`registry.py`)
- `append_log(profile, op, title, *, on_date=None, body=None) -> AppendLogResult`.
  - heading = `profile.log_format.format(date, op, title)`; entry = heading se `body` è `None`, altrimenti
    `heading + "\n\n" + body.rstrip() + "\n"` (il corpo curato **non viene riformattato**).
  - target = `partition_path(date)` se `rotation_enabled` else `log_path`.
  - **creazione** del file-giorno se assente (seed header) — solo in rotazione; in file-unico si conserva il
    comportamento attuale (registro deve esistere).
  - **idempotenza**: identità = la riga di heading (DA-5); se già presente nel target → no-op.
  - se è stata creata una nuova partizione → aggiorna l'indice delle partizioni.
- `update_log_index(profile) -> bool`: rigenera `log_index_path` elencando le partizioni `YYYY-MM-DD.md`
  ordinate (idempotente).

### Coupling `scan` (`scan.py`)
- `_latest_log_mtime(profile)`: in rotazione → max `mtime` tra i file-partizione (esclude l'indice); in
  file-unico → `log_path` mtime (comportamento attuale). Resto di `scan` invariato; contratto `wiki.scan/1`
  e output dell'hook **immutati** (FR-008, SC-003).

### Migrazione (`registry.py`)
- `migrate_log(profile) -> MigrateResult`: legge `log_path`; segmenta per heading `^## \[YYYY-MM-DD\]`;
  raggruppa per data (preambolo prima della 1ª voce ignorato); scrive ogni gruppo in `partition_path(date)`
  con seed header; **idempotente** (data già presente → skip); **non distruttivo** (non cancella `log.md`).
  Aggiorna l'indice. Heading malformati → ignorati con warning (non bloccano).

### CLI (`__main__.py`)
- `append-log`: `--op <op> --title <title> [--date YYYY-MM-DD]`; **corpo curato da stdin** (o `--body-file`).
  Emette `wiki.append_log/1`.
- `migrate`: nessun argomento extra; emette `wiki.migrate/1`.

## Artefatti
- [data-model.md](data-model.md) — entità e contratti.
- [contracts/wiki-log-contracts.md](contracts/wiki-log-contracts.md) — `wiki.append_log/1`, `wiki.migrate/1`.
- [quickstart.md](quickstart.md) — uso da CLI.
- [tasks.md](tasks.md) — task ordinati per dipendenze.

## Rischi e mitigazioni (design)
- **Parità `scan`**: test dedicato che confronta il conteggio rotazione vs file-unico sugli stessi dati.
- **Idempotenza voci multi-riga**: identità sull'heading; test su ri-append.
- **Migrate non distruttivo**: `log.md` resta; la sua rimozione dal repo è un passo manuale/git separato.
