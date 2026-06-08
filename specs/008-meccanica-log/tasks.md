# Tasks: Meccanica del log del wiki (FEAT-008)

Ordinati per dipendenze. `[P]` = parallelizzabile. Test offline F.I.R.S.T. (`tmp_path`, no rete).

## Fase 1 — Fondazione (config + contratti)
- **T001** `profile.py`: aggiungi `log_dir`/`log_index_file` + property `rotation_enabled`, `log_dir_path`,
  `partition_path(date)`, `log_index_path`; parsing in `load_profile` (default vuoti = back-compat).
- **T002** `contracts.py`: aggiungi `AppendLogResult` (`wiki.append_log/1`) e `MigrateResult`
  (`wiki.migrate/1`) con `to_dict`/`to_json`. [P con T001 a livello di file diverso? no: stesso pacchetto, ma file diverso → P]

## Fase 2 — US1 (append curato + rotazione) [P1]
- **T010** `registry.py`: estendi `append_log(profile, op, title, *, on_date=None, body=None) -> AppendLogResult`:
  target per data, creazione partizione con seed header, idempotenza sull'heading, body non riformattato.
- **T011** `registry.py`: `update_log_index(profile)` (rigenera l'indice delle partizioni, idempotente);
  invocato da `append_log` su nuova partizione.
- **T012** `__main__.py`: op `append-log` (`--op`, `--title`, `--date`, corpo da stdin/`--body-file`),
  `_human`/`_run`, emette `wiki.append_log/1`.
- **T013** test `tests/unit/test_wiki_tools_log_rotation.py`: append crea il file del giorno; seconda voce in
  coda; ri-append idempotente; corpo byte-identico (SC-001/002/004).

## Fase 3 — US2 (scan/hook intatto) [P1]
- **T020** `scan.py`: `_latest_log_mtime(profile)` (partizione più recente in rotazione; `log_path` in
  file-unico); usa in `scan`.
- **T021** test parità: stesso dataset → conteggio pendente identico rotazione vs file-unico; nessuna
  modifica al contratto (SC-003).

## Fase 4 — US3 (migrate) [P2]
- **T030** `registry.py`: `migrate_log(profile) -> MigrateResult` (segmenta per heading datato, raggruppa per
  data, scrive partizioni con seed, idempotente, non distruttivo; aggiorna indice).
- **T031** `__main__.py`: op `migrate` → `wiki.migrate/1`.
- **T032** test: split per N date, ordine preservato, più voci stessa data → stessa partizione, riesecuzione
  no-op (SC-005).

## Fase 5 — US4 (indice partizioni) [P3]
- **T040** verifica/estendi `update_log_index` per coprire l'elenco ordinato dei giorni; test idempotenza.

## Fase 6 — Integrazione & qualità
- **T050** `wiki.config.toml`: `log_dir = "log"` (attiva la rotazione su Sertor).
- **T051** `_OPS` in `__main__.py` aggiornato; help coerente.
- **T052** `uv run pytest -m "not cloud"` verde; `uv run ruff check .` pulito.
- **T053** (fuori dal codice) migrazione reale dello storico `wiki/log.md` + rimozione via git: passo manuale
  post-merge.
