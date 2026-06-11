# Contratto CLI — `sertor-rag`

**Feature**: `011-cli-esecuzione-rag` | **Fase**: Phase 1 (Contracts) | **Data**: 2026-06-11

Console-script del pacchetto `sertor-core`. Entry-point: `sertor_core.cli.__main__:main`.
Equivalente modulo: `python -m sertor_core.cli`. Pattern di riferimento:
`sertor_core/wiki_tools/__main__.py`.

---

## Sinossi

```
sertor-rag [--help]
sertor-rag index <path>  [--corpus NAME] [--json] [-v|--verbose] [--log-json] [--log-config FILE]
sertor-rag search <query> [-k N] [--type code|doc|both] [--full] [--json]
                          [--corpus NAME] [-v|--verbose] [--log-json] [--log-config FILE]
```

- `<path>`: radice del repository da indicizzare (obbligatorio per `index`).
- `<query>`: testo della query (obbligatorio per `search`, non vuoto).
- Le opzioni di logging (`-v`, `--log-json`, `--log-config`) sono disponibili su entrambi i
  sottocomandi.

---

## Exit code (FR-004)

| Code | Significato |
|------|-------------|
| `0` | Operazione completata con successo |
| `1` | Errore di dominio del core (`SertorError`: config incompleta, path non valido, provider/store irraggiungibile, indice assente, ...) |
| `2` | Errore d'uso (argparse: sottocomando ignoto, argomento obbligatorio mancante, `--type` non valido) — FR-003 |

Errori di dominio: messaggio leggibile su **stderr** (`errore: <messaggio>`), nessuno stack trace
salvo verbosità elevata (NFR-04). Con `--json`, l'errore è anche un oggetto JSON su stdout
(`{"error": "<TipoEccezione>", "message": "..."}`), coerente con `wiki_tools`.

---

## Comando `index <path>` (US1 / FR-005..009)

Costruisce l'indice vettoriale del repository (full rebuild via core, idempotente) e riporta i
conteggi. Non distruttivo sui file sorgente (scrive solo nello store).

### Opzioni
| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `--corpus NAME` | namespace del corpus; prevale su `SERTOR_CORPUS` (FR-009) | da `Settings` |
| `--json` | report come oggetto JSON | output umano |

### Output umano (esempio)
```
collection=sertor__azure_text_embedding_3_large documents=128 chunks=1430 embedding_dim=3072 elapsed_ms=8421.5
```

### Output `--json`
```json
{
  "collection": "sertor__azure_text_embedding_3_large",
  "documents": 128,
  "chunks": 1430,
  "embedding_dim": 3072,
  "elapsed_ms": 8421.5
}
```

### Comportamenti d'errore
| Condizione | Esito | Requisito |
|------------|-------|-----------|
| `<path>` inesistente / non directory / file | `errore: ...` stderr, exit 1, nessun indice | FR-006 |
| backend config incompleta (es. azure senza endpoint) | blocco **prima** di contattare servizi, errore che nomina le env mancanti, exit 1 | FR-015 |
| provider/store irraggiungibile a metà | abort, errore leggibile, indice preesistente intatto (no parziale) | FR-007 |
| repository vuoto/minuscolo | successo, report a conteggi bassi/zero | edge case |

---

## Comando `search <query>` (US2 / FR-010..013)

Interroga l'indice e restituisce i top-k risultati con metadati citabili.

### Opzioni
| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `-k N` | numero di risultati | `Settings.default_k` (FR-011) |
| `--type code\|doc\|both` | filtro per tipo documento | `both` (FR-011) |
| `--full` | testo completo del chunk invece dell'anteprima troncata | off (FR-010/013) |
| `--json` | risultati come array JSON | output umano (FR-013) |
| `--corpus NAME` | namespace del corpus; prevale sul config | da `Settings` |

### Output umano (esempio, anteprima troncata)
```
[1] score=0.834  doc=code  path=src/sertor_core/composition.py  chunk=src/sertor_core/composition.py#3
    def build_indexer(settings: Settings | None = None): … (troncato)
[2] score=0.791  doc=doc   path=wiki/concepts/hybrid-search.md  chunk=wiki/concepts/hybrid-search.md#0
    L'hybrid search combina retrieval lessicale (BM25) e denso … (troncato)
```

### Output `--json` (anteprima troncata; con `--full` il campo diventa `text` integrale)
```json
[
  {
    "path": "src/sertor_core/composition.py",
    "doc_type": "code",
    "chunk_id": "src/sertor_core/composition.py#3",
    "score": 0.834,
    "preview": "def build_indexer(settings: Settings | None = None): …"
  }
]
```

### Comportamenti d'errore
| Condizione | Esito | Requisito |
|------------|-------|-----------|
| indice inesistente | `errore: indice inesistente: esegui prima 'sertor-rag index <path>'`, exit 1 (per **qualunque** `--type`) | FR-012 / D6 |
| `query` vuota o solo spazi | errore d'uso leggibile, exit non-zero | edge case |
| `--type` non valido | errore d'uso argparse, exit 2 | FR-003 |
| backend config incompleta | blocco prima di contattare servizi, exit 1 | FR-015 |
| provider irraggiungibile (es. Ollama spento) | errore runtime leggibile, exit 1 | FR-007 |

Invarianti:
- Ogni hit include almeno `path`, `doc_type`, `chunk_id`, `score`, anteprima troncata (FR-010).
- Output umano e `--json` informativamente equivalenti (SC-002).
- Nessun risultato vuoto silenzioso su indice assente (FR-012).

---

## Help (FR-002)

`sertor-rag --help`, `sertor-rag index --help`, `sertor-rag search --help` descrivono argomenti e
opzioni. Generati da argparse (description + help per arg).

---

## Install ≠ run (FR-023 / SC-003)

L'import del package `sertor_core.cli` o l'installazione del console-script **non** avvia alcuna
operazione: nessun side-effect a import-time; ogni operazione richiede l'invocazione esplicita di
un sottocomando. Verificabile con un test che importa il modulo e asserisce assenza di chiamate al
core.

---

## Repo-agnosticità (FR-024 / SC-005)

Nessuna assunzione hardcoded su struttura, linguaggio o dimensione del repository target: `<path>`
è arbitrario; le esclusioni/parametri vengono da `Settings`. Le stesse operazioni completano su ≥2
repository diversi senza modifiche al codice.
