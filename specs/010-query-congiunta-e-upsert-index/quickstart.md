# Quickstart — Query congiunta multi-collezione & `upsert-index`

## A — Interrogare codice + wiki in una sola ricerca

```bash
# 1. Dichiarare i corpora extra nella configurazione (.env dell'ospite)
SERTOR_CORPUS=sertor              # corpus primario (codice), già configurato
SERTOR_EXTRA_CORPORA=wiki         # corpus aggiuntivi per la ricerca combinata (CSV)

# 2. Assicurarsi che entrambe le collezioni esistano nello stesso index dir
#    (il corpus wiki si costruisce con il nucleo wiki: rag-sync)
uv run sertor-wiki-tools index --config wiki.config.toml
```

```python
# 3. Consumare: nessun cambiamento rispetto a oggi (thin-consumer)
from sertor_core import build_facade

facade = build_facade()
hits = facade.search_combined("perché le collezioni sono namespaced per provider?")
for h in hits:
    print(f"{h.score:.3f}  {h.doc_type}  {h.path}#{h.chunk_id}")
# → risultati fusi da codice E wiki, ordinati per pertinenza, al più k totali
```

Comportamenti notevoli:
- `SERTOR_EXTRA_CORPORA` assente/vuoto → comportamento identico a prima (una collezione).
- Corpus extra mai indicizzato → warning + risultati dalle altre collezioni (degradazione morbida).
- Corpus extra indicizzato con un **altro provider** di embeddings → `ProviderMismatchError`
  esplicita: reindicizzare il corpus col provider corrente (o cambiare provider).
- `search_code` / `search_docs` NON cambiano: il fan-out è solo della ricerca combinata.

## B — Scrivere la riga d'indice del wiki dalla CLI

```bash
# sommario inline
uv run sertor-wiki-tools upsert-index --page concepts/retrieval-core.md \
    --summary "Il nucleo di retrieval importabile: architettura Clean, porte e composition root." --json
# → {"written": true, "action": "insert", "page": "concepts/retrieval-core.md", "schema": "wiki.upsert_index/1"}

# sommario da stdin (testi lunghi / caratteri speciali; UTF-8)
echo "Sintesi aggiornata della pagina." | uv run sertor-wiki-tools upsert-index --page tech/wiki-tools.md

# idempotenza: ripetere la stessa invocazione non scrive nulla
# → written=false action=noop page=tech/wiki-tools.md
```

Regole: il sommario è **autorato dall'LLM** (la CLI non lo genera né lo riscrive); vuoto o
multilinea → errore esplicito, exit 1, nessuna scrittura; indice mancante → inizializzare prima la
struttura (`sertor-wiki-tools structure init`).

## Verifica rapida (sviluppo)

```bash
uv run pytest tests/unit -q          # unit (mock, no rete)
uv run pytest -m "not cloud" -q      # suite completa senza cloud
uv run ruff check .                  # lint
```
