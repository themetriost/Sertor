# Quickstart — Meccanica del log del wiki

Prerequisito: `wiki.config.toml` con `log_dir` valorizzato (es. `log_dir = "log"`) per attivare la rotazione.

## Appendere una voce curata (corpo da stdin)
```bash
printf 'Lead della voce.\n- **Cosa:** ...\n- **Verifica:** lint A 0/0/0/0.' \
  | uv run sertor-wiki-tools append-log --op record --title "Titolo dello step" --json
# → {"written": true, "partition": "log/2026-06-08.md", "created": true, "schema": "wiki.append_log/1"}
```
La voce finisce in `wiki/log/2026-06-08.md` (data odierna), creando il file se assente. Il corpo curato è
quello prodotto secondo `log-craft`; il deterministico costruisce l'heading e fa il piazzamento.

## Migrare lo storico (una-tantum)
```bash
uv run sertor-wiki-tools migrate --json
# → {"migrated_entries": N, "created": [...], "skipped": [...], "schema": "wiki.migrate/1"}
```
Splitta `wiki/log.md` in partizioni giornaliere (non distruttivo, idempotente). `wiki/log.md` resta in
posto: rimuovilo via git quando hai verificato.

## Rilevazione lavoro pendente (invariata)
```bash
uv run sertor-wiki-tools scan --json   # anchor = partizione più recente; l'hook non cambia
```
