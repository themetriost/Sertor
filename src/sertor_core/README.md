# sertor-core

Nucleo di retrieval condiviso di Sertor (FEAT-001): la **fondazione production-grade** su cui
poggiano i motori RAG e le skill wiki. Legge un repository qualunque, ne fa chunking di codice e
documentazione, produce embeddings via provider intercambiabili, persiste/interroga i chunk via
un'astrazione di vector store, ed espone una **facade di retrieval importabile come libreria**.

## Architettura (Clean Architecture)

Le dipendenze puntano verso l'interno: il `domain` (entità + porte + errori) non importa alcun SDK
esterno; gli `adapters` implementano le porte; il `composition root` cabla tutto dalla
configurazione.

```
domain/        entità (Document, Chunk, RetrievalResult), porte (EmbeddingProvider, VectorStore), errori
services/      ingestion · chunking (code/markdown/fallback) · indexing · retrieval (facade)
adapters/      embeddings/{ollama,azure} · vectorstores/{chroma,azure_search}
config/        Settings (config centralizzata)
observability/ logging strutturato
composition.py build_facade() / build_indexer() / build_embedder() / build_store()
```

## Installazione

```bash
uv pip install sertor-core              # base: Chroma (locale) + Ollama (locale)
uv pip install "sertor-core[azure]"     # extra cloud: Azure OpenAI + Azure AI Search
```

Il chunking usa `tree-sitter-language-pack` (wheel precompilati, nessuna toolchain C).

## Configurazione

Tutte le scelte passano da `Settings`, lette da env + file `.env` (non versionato). Vedi
`.env.example` alla radice. Modalità `RAG_BACKEND=local` → nessuna chiamata di rete cloud.

## Uso come libreria

```python
from sertor_core import build_indexer, build_facade

# Indicizzare un repository qualunque
report = build_indexer().index("/path/al/repo")
print(report.documents, report.chunks)

# Interrogare (codice / doc / combinata)
facade = build_facade()
for hit in facade.search_code("validazione input", k=5):
    print(hit.path, hit.chunk_id, round(hit.score, 3))
```

Ogni risultato espone `text`, `path`, `chunk_id`, `doc_type`, `score`. Indice vuoto → lista vuota
+ warning (nessuna eccezione).

## Motore baseline (modalità RAG vettoriale)

La prima modalità RAG (FEAT-002): un motore sottile sopra il nucleo che indicizza una codebase e la
interroga per similarità vettoriale.

```python
from sertor_core import build_baseline_engine, evaluate, IndexNotFoundError

engine = build_baseline_engine()           # cablato da Settings; engine.name == "baseline"
engine.index("/path/al/repo")              # rebuild-from-scratch idempotente
hits = engine.query("come si valida un input", k=5)   # top-k per similarità

# Indice non costruito → errore esplicito (non lista vuota):
try:
    build_baseline_engine().query("x")
except IndexNotFoundError as e:
    print("Costruisci prima l'indice:", e)

# Valutazione della pertinenza (hit-rate@k, MRR@10) su un ground-truth:
report = evaluate(engine, [("avvio del server", ["web/server.js"])])
print(report.hit_rate, report.mrr)
```

Differenze rispetto alla facade del nucleo: il motore **ricostruisce l'indice da zero** a ogni
`index()` (nessun chunk obsoleto) e su indice mancante **solleva `IndexNotFoundError`** invece di
restituire una lista vuota. Usa **solo** retrieval vettoriale (nessun ibrido/grafo/agentico).

## Skill LLM Wiki (creare / indicizzare)

La skill (FEAT-003) gestisce un wiki di progetto e lo rende interrogabile dal RAG.

```python
from sertor_core.wiki.structure import create_wiki
from sertor_core.wiki.operations import record, ingest
from sertor_core.wiki.indexing import index_wiki
from sertor_core.wiki.conventions import Brief, SourceBrief

create_wiki("repo/wiki")                                   # struttura standard, non-distruttiva
record("repo/wiki", Brief("Scelta DB", "synthesis", "Scelto Postgres perché ..."))
ingest("repo/wiki", SourceBrief("Paper", "Riassunto...", reference="https://...",
                                related=["concepts/hybrid-search"]))
index_wiki("repo/wiki")                                    # full rebuild nel corpus RAG (riusa il nucleo)
```

Tutte le operazioni sono **idempotenti per struttura** (re-run su input invariato → file identici).
La **distillazione** (`wiki.distill.distill`) richiede un LLM (`build_llm()`); senza, solleva
`LLMNotConfiguredError`. Le pagine wiki entrano nel RAG come corpus documentale **paritario** e si
recuperano con `build_facade().search_docs(...)`.

## Manutenzione del wiki (lint / indice / documentazione)

La manutenzione (FEAT-007) tiene il wiki sano e allineato. È **LLM-free e non distruttiva**, pensata
per girare di frequente come gate (es. a fine feature).

```python
from sertor_core.wiki.maintenance import lint, regenerate_index
from sertor_core.wiki.distill import distill_artifact

# Lint: report di igiene (link rotti, orfani, fuori-indice, contraddizioni marcate) + coperture.
report = lint("repo/wiki", expected=["syntheses/architettura.md"])   # sola lettura
print(report.render())
import sys; sys.exit(0 if report.ok else 1)          # gate pass/fail non interattivo

regenerate_index("repo/wiki")        # rigenera solo il blocco <!-- sertor:catalog --> (idempotente)
lint("repo/wiki", fix=True)          # lint + unico fix sicuro (= rigenera indice); mai auto-fix dei link

# Distilla un artifact (spec/plan/requisito) in documentazione ufficiale, con backlink alla fonte:
distill_artifact("repo/wiki", source="specs/001-nucleo-retrieval/spec.md",
                 kind="synthesis", title="Architettura del nucleo", llm=build_llm())
```

`lint` non scrive nulla (salvo `fix=True`); `regenerate_index` tocca **solo** la regione tra i
marcatori del catalogo; `distill_artifact` **crea-se-assente** e non sovrascrive una pagina curata a
mano. Vedi `specs/005-wiki-manutenzione/` per spec, piano, contratti e quickstart.

## CLI `sertor` (esecuzione da riga di comando)

Il pacchetto `sertor-cli` espone un comando `sertor` (console-script) che esegue le capacità del core
su un repository, come **layer sottile** sopra il composition root (non duplica il core).

```bash
sertor index .                          # indicizza il repo (rebuild idempotente, non distruttivo)
sertor index /repo --corpus production  # collezione namespaced dedicata
sertor search "valido un input" -k 5    # ricerca (default dal core); --type code|doc|both
sertor search "x" --json                # output JSON (per agenti); --full per il testo completo
sertor wiki index wiki/                 # indicizza un wiki nel corpus

# osservabilità: log visibili e appender esterni (Splunk/syslog) senza toccare il codice
sertor index . -v                       # INFO a console
sertor index . --log-json               # record JSON
sertor index . --log-config logging.yaml  # dictConfig (YAML/JSON)
```

Principi: install ≠ run (nessuna operazione automatica all'import), errori espliciti + exit code,
provider/parametri letti dalla configurazione del core. Schema dei campi di log:
[`observability/README.md`](observability/README.md).

## Test con mock (senza cloud né rete)

Il core è esercitabile con adapter mock delle porte:

```python
from sertor_core.services.retrieval import RetrievalFacade

facade = RetrievalFacade(embedder=FakeEmbedder(dim=8), store=InMemoryStore(),
                         collection="test", default_k=5)
```

## Linguaggi del chunking code-aware

Sintattici al primo rilascio: Python, JavaScript/TypeScript, Java, C#, Go, C/C++, PHP, Ruby.
PowerShell e i dialetti SQL (T-SQL/PL-SQL) usano il **fallback dimensionale** finché i node-type
non sono validati (estensione incrementale). Qualunque altro linguaggio ricade sul fallback senza
errore.

Vedi `specs/001-nucleo-retrieval/` per spec, piano, contratti e quickstart completi.
