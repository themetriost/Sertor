# Contratto — `sertor-wiki-tools upsert-index`

**Schema del risultato**: `wiki.upsert_index/1`

## Invocazione

```bash
# sommario come argomento
sertor-wiki-tools upsert-index --page concepts/retrieval-core.md --summary "Il nucleo importabile…" [--config wiki.config.toml] [--root <dir>] [--json]

# sommario da stdin (UTF-8; per testi lunghi o con caratteri speciali)
echo "Il nucleo importabile…" | sertor-wiki-tools upsert-index --page concepts/retrieval-core.md [--json]
```

| Argomento | Obbligatorio | Semantica |
|---|---|---|
| `--page` | sì | identità della riga: path relativo POSIX della pagina nel wiki |
| `--summary` | no | testo del sommario; se assente è letto da stdin (UTF-8) |
| `--config` / `--root` / `--json` | no | come per le altre operazioni della CLI |

## Esiti

**Successo** (exit 0). Output umano: `written=<bool> action=<insert|update|noop> page=<page>`.
Con `--json`:

```json
{"written": true, "action": "insert", "page": "concepts/retrieval-core.md", "schema": "wiki.upsert_index/1"}
```

| Caso | `written` | `action` |
|---|---|---|
| Riga assente → inserita | `true` | `insert` |
| Riga presente, sommario diverso → aggiornata in place | `true` | `update` |
| Riga presente, stesso sommario → nessuna scrittura | `false` | `noop` |

**Errore** (exit 1, messaggio su stderr; con `--json` anche `wiki.error/1` su stdout):

| Caso | Errore |
|---|---|
| `--page` mancante | `ConfigError` («upsert-index richiede --page») |
| Sommario assente (né `--summary` né stdin) | `ConfigError` |
| Sommario vuoto/solo whitespace (post-trim) | `ConfigError` (FR-018) |
| Sommario con newline interni | `ConfigError` — nessuna normalizzazione silenziosa (FR-018, clarify #3) |
| File di indice inesistente | `ConfigError` («inizializzare la struttura», FR-015) |

## Invarianti

- La CLI scrive **esattamente** il testo fornito (post-trim): mai generato/inferito/riscritto (FR-014).
- Idempotenza: stessa `(page, summary)` → `noop`, zero scritture (FR-012).
- La riga ha forma `- [[page]] — summary` (formato esistente di `upsert_index`).
- stdin/stdout/stderr riconfigurati UTF-8 (meccanica esistente di `__main__.py`, FR-017).

## Test di contratto (da tasks)

1. Insert su indice senza riga → riga presente, esito `insert`.
2. Update con sommario diverso → riga sostituita in place, esito `update`.
3. Re-invocazione identica → `noop`, file invariato (byte-identico).
4. Indice mancante → exit 1, messaggio azionabile.
5. Sommario vuoto → exit 1; multilinea → exit 1; nessuna scrittura in entrambi.
6. Sommario non-ASCII via stdin → scritto fedelmente (no mojibake).
7. `--json` → contratto `wiki.upsert_index/1` ben formato.
