# Sertor

> Un framework per dare a **qualsiasi progetto** una conoscenza di sé **viva, interrogabile e auto-manutenuta** — indicizzazione, RAG e LLM Wiki, senza lock-in.

## 🌅 Vision

Ogni progetto software — che sia codice, documentazione, o entrambi — dovrebbe poter
**conoscere e interrogare sé stesso**. La conoscenza di una codebase e dei suoi documenti smette
di essere sparsa, volatile e ricostruita da zero a ogni sessione, e diventa un **asset vivo,
persistente e auto-manutenuto**. E questo deve essere possibile **ovunque e senza lock-in**:
portabile da un progetto all'altro, eseguibile in locale, neutrale rispetto al provider di LLM e
di storage.

## 🎯 Mission

Sertor è un **framework installabile** che dota **qualsiasi progetto** — *code+doc*, *solo-doc* o
*solo-code* — di tre capacità componibili:

1. **Indicizzazione repo-agnostica** dei contenuti (codice e documenti);
2. **Retrieval RAG** con più motori, da locale ad Azure;
3. un **LLM Wiki** cumulativo che cresce con il lavoro.

Ogni capacità è **disaccoppiata dal dominio dell'ospite**: Sertor si aggancia a un progetto solo
come *consumatore* — oggi a sé stesso, in modo strumentale, via **dogfooding**. È consegnato come
**libreria importabile** (è quello il prodotto) — riproducibile e adatta a contesti di ogni scala,
**enterprise inclusa** — mentre CLI e MCP ne sono veicoli sottili.

## I tre profili di progetto

Sertor non assume nulla sulla forma dell'ospite. Si installa e si adatta a:

| Profilo | Esempio | Cosa indicizza |
|---------|---------|----------------|
| **code + doc** | un repository applicativo con i suoi `docs/` | sorgenti *e* documentazione |
| **solo doc** | un knowledge base, un wiki, una raccolta di PDF/MD | solo documenti |
| **solo code** | una libreria senza documentazione narrativa | solo sorgenti |

## Le tre capacità

- **Indicizzazione** — ingestione repo-agnostica, chunking *code-aware* (multi-linguaggio) e
  *markdown-aware*, embeddings multi-provider, vector store astratto.
- **RAG** — recupero su quei contenuti; più motori (baseline vettoriale oggi; ibrido+reranking,
  a grafo e agentico come incrementi).
- **LLM Wiki** — una base di conoscenza del progetto che si scrive e si mantiene durante il lavoro
  (pattern "LLM Wiki"), interrogabile a sua volta via RAG.

## Disaccoppiamento (perché conta)

Le funzionalità e le skill di Sertor **non devono conoscere il business dell'ospite**. Il fatto che
in questo repository siano applicate a Sertor stesso è **strumentale** (dogfooding), non un permesso
a incorporare assunzioni specifiche del progetto. Questo principio è vincolante: vedi la
[costituzione](.specify/memory/constitution.md).

## Architettura in breve

- **La libreria è il prodotto.** Il nucleo vive in [`src/sertor_core/`](src/sertor_core/) in
  **Clean Architecture** (le dipendenze puntano verso l'interno; il `domain` non importa SDK).
- **Local-first ↔ Azure**, intercambiabili via configurazione (`RAG_BACKEND=local|azure`), senza
  toccare il codice. Provider LLM/embeddings e vector store sono dietro *porte* astratte.
- **CLI e MCP** sono consumatori sottili della libreria.

## Stato

In **costruzione attiva**. Disponibile oggi su `master`:

- ✅ **`sertor-core`** — libreria di retrieval prod-ready (ingestione, chunking, embeddings, facade).
- ✅ **Motore RAG baseline** (vettoriale) con valutazione (hit\@k, MRR).

In sviluppo: LLM Wiki end-to-end, motori avanzati (ibrido/grafo/agentico), refresh incrementale
dell'indice, veicoli CLI e MCP.

## Sviluppo

Si usa [`uv`](https://github.com/astral-sh/uv):

```bash
uv sync --extra dev          # ambiente con dipendenze di sviluppo
uv run pytest -m "not cloud" # suite senza servizi cloud
uv run ruff check .          # lint
```

Vedi [`CLAUDE.md`](CLAUDE.md) per la guida operativa completa.
