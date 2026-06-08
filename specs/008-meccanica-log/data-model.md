# Data Model: Meccanica del log del wiki

## Estensioni a `WikiProfile` (config)

| Campo | Tipo | Default | Significato |
|---|---|---|---|
| `log_dir` | `str` | `""` | directory delle partizioni (relativa a `root`). Vuoto → modalità file-unico (back-compat) |
| `log_index_file` | `str` | `"index.md"` | nome dell'indice delle partizioni, dentro `log_dir` |

**Property derivate:** `rotation_enabled` (`bool`), `log_dir_path` (`Path`), `partition_path(d: date) -> Path`
(`log_dir_path / f"{d.isoformat()}.md"`), `log_index_path` (`Path`).

## Entità

- **Partizione di log giornaliera** — file `YYYY-MM-DD.md` sotto `log_dir`; header seed minimo; contiene tutte
  le voci di quella data. Identità = la data.
- **Voce di log** — `## [YYYY-MM-DD] <op> | <titolo>` (heading, costruito dal deterministico via `log_format`)
  + corpo curato opzionale (lead/bullet/esito, fornito dall'LLM, non riformattato). Identità per idempotenza =
  l'heading.
- **Indice delle partizioni** — `log_dir/index.md`: elenco ordinato dei giorni presenti, rigenerabile.

## Contratti (output)

- **`AppendLogResult`** → `wiki.append_log/1`: `{ written: bool, partition: str|null, created: bool, schema }`.
  - `written`: ha scritto (False se idempotente no-op). `partition`: path relativo del file toccato.
  - `created`: True se la partizione è stata creata in questa chiamata.
- **`MigrateResult`** → `wiki.migrate/1`: `{ migrated_entries: int, created: list[str], skipped: list[str],
  schema }`.
  - `created`/`skipped`: nomi-file delle partizioni create / saltate (già presenti).

`ScanResult` (`wiki.scan/1`) **invariato**.
