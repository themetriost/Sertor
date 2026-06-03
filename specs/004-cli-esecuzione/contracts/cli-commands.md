# Contratto — Comandi della CLI `sertor`

Interfaccia a riga di comando (il "contratto" esposto all'utente/agente). La CLI è un layer sottile
sul core: ogni comando fa parse → composition root → output. Exit code 0 = successo, non-zero = errore.

## `sertor index <path> [--corpus <nome>]`

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | path valido + provider configurato | `build_indexer(settings).index(path, rebuild=True)` | report (chunks, dim) su stdout; exit 0 | REQ-010 |
| 2 | `--corpus <nome>` | indicizza nella collezione namespaced del corpus | corpora isolati | REQ-014 |
| 3 | path inesistente/illeggibile | nessuna indicizzazione | errore leggibile su stderr; exit ≠0 | REQ-011 |
| 4 | provider/store non disponibile | abort | errore leggibile; nessun indice parziale; exit ≠0 | REQ-012 |
| 5 | nessun provider configurato | operazione bloccata | errore esplicito (CS-5); exit ≠0 | REQ-041 |
| 6 | sempre | non modifica i file del repo | non distruttivo | REQ-013 |

## `sertor search <query> [-k N] [--type code|doc|both] [--json] [--full] [--corpus <nome>]`

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | indice popolato | embed query → top-k dal core | risultati (path, tipo, chunk_id, score, anteprima); exit 0 | REQ-020 |
| 2 | `-k`/`--type` omessi | default dal core (`default_k`, `both`) | — | REQ-021 |
| 3 | `--json` | array JSON strutturato; senza → testo | — | REQ-023 |
| 4 | `--full` | anteprima sostituita dal testo completo; default troncata | economia token | REQ-020/023 |
| 5 | indice inesistente | errore esplicito "costruisci prima l'indice" | exit ≠0, no vuoto silenzioso | REQ-022 |
| 6 | provider non disponibile | errore | exit ≠0 | REQ-010(core)/041 |

## `sertor wiki index <wiki-path> [--corpus <nome>]`

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | wiki + provider | `index_wiki(wiki_path, settings)` (full rebuild) | n. documenti su stdout; exit 0 | REQ-030 |
| 2 | radice vuota/senza .md | warning, indice immutato | exit 0 (warning) | REQ-031 |
| 3 | store non disponibile | abort, indice non corrotto | errore; exit ≠0 | REQ-043(core) |

## Opzioni globali di osservabilità

| Opzione | Comportamento | Req |
|---------|---------------|-----|
| `-v/--verbose` | abilita i log INFO strutturati del core (default WARNING) | REQ-050 |
| `--log-json` | log come record JSON | REQ-051 |
| `--log-config <file>` | `dictConfig` (YAML/JSON): collega handler/appender esterni (file/syslog/Splunk) | REQ-052 |

## Invarianti trasversali

- **install ≠ run**: importare/installare la CLI non avvia alcuna operazione (REQ-060); ogni azione
  richiede un comando esplicito.
- **repo-agnostico**: opera su qualunque path senza assunzioni hardcoded (REQ-061).
- **sottile sul core**: nessuna logica RAG nella CLI (Principio I, NFR-01).
- **segreti**: mai nei log né su file versionati (REQ-042/055).
- **errori di dominio** → messaggio leggibile + exit ≠0 (REQ-003); traceback solo in `--verbose`.

## Test (contract tests)

Invocare `cli.main([...])` con `build_*` del core monkeypatchati a mock (FakeEmbedder/InMemoryStore/
FakeLLM): verificare output, exit code e log per ciascuna riga delle tabelle sopra. Nessun cloud/rete.
