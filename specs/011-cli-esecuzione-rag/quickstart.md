# Quickstart — `sertor-rag`

**Feature**: `011-cli-esecuzione-rag` | **Data**: 2026-06-11

Guida rapida alla CLI di esecuzione RAG. Presuppone `sertor-core` installato (anche editable) e una
configurazione valida (env/`.env`, vedi `CLAUDE.md` § Setup).

---

## Installazione (sviluppo)

```powershell
uv sync --extra dev
# il console-script `sertor-rag` è disponibile nell'env (accanto a `sertor-wiki-tools`)
uv run sertor-rag --help
```

Equivalente senza console-script:

```powershell
uv run python -m sertor_core.cli --help
```

`install ≠ run`: installare o importare la CLI non avvia alcuna indicizzazione (FR-023).

---

## 1. Indicizzare un repository (US1)

```powershell
# Locale (Ollama + Chroma), corpus di default
uv run sertor-rag index .

# Su un altro repository, in un corpus dedicato
uv run sertor-rag index C:\Workspace\Git\AltroRepo --corpus altro

# Report come JSON (per script/agente)
uv run sertor-rag index . --json
```

Output umano:
```
collection=default__nomic_embed_text documents=128 chunks=1430 embedding_dim=768 elapsed_ms=5210.3
```

Errori tipici:
- `<path>` non esiste / non è una directory → errore leggibile, exit 1, nessun indice (FR-006).
- Backend `azure` senza credenziali → blocco prima di contattare servizi, con i nomi delle env
  mancanti (FR-015):
  ```
  errore: configurazione backend incompleta: mancano AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_EMBED_DEPLOYMENT
  ```

---

## 2. Interrogare l'indice (US2)

```powershell
# Top-k di default (Settings.default_k), modalità both
uv run sertor-rag search "come si costruisce l'indicizzatore?"

# 10 risultati, solo codice
uv run sertor-rag search "build_indexer" -k 10 --type code

# Output JSON per consumo da agente (anteprime troncate)
uv run sertor-rag search "facade di retrieval" --json

# Testo completo del chunk on-demand
uv run sertor-rag search "facade di retrieval" --full
```

Output umano (anteprime troncate):
```
[1] score=0.834  doc=code  path=src/sertor_core/composition.py  chunk=src/sertor_core/composition.py#3
    def build_indexer(settings: Settings | None = None): … (troncato)
```

Errori tipici:
- Indice non costruito → errore esplicito (mai risultato vuoto silenzioso), per **qualunque**
  `--type` (FR-012):
  ```
  errore: indice inesistente: esegui prima 'sertor-rag index <path>'
  ```
- Query vuota → errore d'uso leggibile, exit non-zero.

---

## 3. Osservabilità (US3)

```powershell
# Eventi INFO strutturati del core sulla console
uv run sertor-rag index . -v

# Log come record JSON (uno per evento), per ingestione esterna
uv run sertor-rag search "query" --log-json

# Configurazione di logging esterna (dictConfig YAML o JSON): aggancia file/syslog/Splunk
uv run sertor-rag index . --log-config logging.yaml
```

Esempio `logging.json` (dictConfig, stdlib-only):
```json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {"json": {"format": "%(message)s"}},
  "handlers": {
    "file": {"class": "logging.FileHandler", "filename": "sertor.log", "formatter": "json"}
  },
  "loggers": {"sertor_core": {"handlers": ["file"], "level": "INFO"}}
}
```

I campi emessi per operazione sono documentati in `contracts/log-events.md`. I segreti non compaiono
mai nei log (redazione automatica, FR-022).

---

## 4. Dogfooding del repo Sertor (SC-008)

```powershell
# Indicizza Sertor stesso nel corpus `sertor` (coerente col server MCP)
$env:SERTOR_CORPUS = "sertor"
uv run sertor-rag index .
uv run sertor-rag search "composition root"
```

I risultati devono essere coerenti con quelli della facade / server MCP a parità di configurazione.

---

## 5. Test (NFR-02 / SC-007)

L'intera superficie CLI è verificabile con provider/store **mock**, senza rete:

```powershell
uv run pytest tests/unit -k cli
uv run pytest -m "not cloud"
```

I mock structural-typing vivono in `tests/fixtures/mocks.py`.
