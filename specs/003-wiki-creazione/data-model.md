# Phase 1 — Data Model: Skill LLM Wiki

Entità di FEAT-003. Riusa le primitive del nucleo per l'indicizzazione; aggiunge le strutture proprie
della skill (brief, frontmatter, esito operazione) e una porta/eccezione LLM.

---

## Brief (input strutturato di record/distill — DA-W2)

| Campo | Tipo | Note |
|-------|------|------|
| `title` | `str` | titolo della pagina (origina il nome kebab-case) |
| `kind` | `enum {concept, tech, experiment, source, synthesis}` | area tematica → sottocartella |
| `body` | `str` | corpo Markdown della pagina (già condensato dall'agente) |
| `tags` | `list[str]` | tag per il frontmatter |
| `sources` | `list[str]` | riferimenti per il frontmatter |

`kind` → directory: concept→`concepts/`, tech→`tech/`, experiment→`experiments/`,
source→`sources/`, synthesis→`syntheses/`.

---

## SourceBrief (input di ingest — REQ-020..023)

| Campo | Tipo | Note |
|-------|------|------|
| `title` | `str` | titolo della fonte |
| `summary` | `str` | riassunto della fonte (corpo della pagina `sources/`) |
| `reference` | `str` | riferimento originale (URL/citazione) → frontmatter `sources` |
| `related` | `list[str]` | pagine tematiche esistenti a cui propagare il riferimento (REQ-021) |
| `contradicts` | `list[tuple[str, str]]` | (pagina, nota) contraddizioni da marcare (REQ-023) |

---

## Frontmatter (convenzione obbligatoria — REQ-003)

| Campo | Tipo | Note |
|-------|------|------|
| `title` | `str` | — |
| `type` | `str` | = `kind` |
| `tags` | `list[str]` | — |
| `created` | `str (YYYY-MM-DD)` | impostato alla creazione; **preservato** sulle pagine esistenti |
| `updated` | `str (YYYY-MM-DD)` | aggiornato solo a contenuto modificato (idempotenza, R3) |
| `sources` | `list[str]` | — |

Convenzioni: nome file **kebab-case** nella sottocartella corretta (REQ-005); cross-riferimenti via
**wikilink** `[[nome-pagina]]` (REQ-004).

---

## LogEntry (voce append-only — REQ-012)

Riga in `log.md`: `## [YYYY-MM-DD] <operazione> | <titolo>` con operazione ∈
{setup, record, ingest, query, lint}. La distillazione registra come `record` (REQ-032). Le voci
precedenti non vengono mai modificate (append-only).

---

## WikiOpResult (esito di un'operazione — REQ-013, osservabilità)

| Campo | Tipo | Note |
|-------|------|------|
| `operation` | `str` | create/record/ingest/distill/index |
| `page_path` | `str \| None` | pagina creata/aggiornata (relativa alla radice wiki) |
| `changed` | `bool` | False se no-op (idempotenza: input invariato) |
| `log_appended` | `bool` | True se è stata aggiunta una voce a `log.md` |

---

## Indicizzazione: riuso entità del nucleo (Gruppo E)

`index_wiki` restituisce un `IndexReport` del nucleo (collection, documents, chunks, embedding_dim).
I chunk del wiki sono `Chunk`/`RetrievalResult` del nucleo con `doc_type=doc`, `chunker=markdown`,
`id = path relativo` (REQ-051). Nessuna nuova entità.

---

## Porta `LLMProvider` (nuovo boundary — solo distill) [additivo al nucleo]

```python
class LLMProvider(Protocol):
    name: str
    def generate(self, prompt: str, system: str | None = None) -> str: ...
```

| Aspetto | Valore |
|---------|--------|
| Adapter | Ollama (chat `/api/chat`), Azure (`/chat/completions`) |
| Uso | esclusivamente dalla distillazione (REQ-030/031) |

---

## Eccezione `LLMNotConfiguredError` (REQ-031) [additivo al nucleo]

| Aspetto | Valore |
|---------|--------|
| Base | `SertorError` |
| Quando | `distill()` invocata senza un `LLMProvider` configurato |
| Messaggio | azionabile ("configura un provider LLM per la distillazione") |

---

## Relazioni

```text
create_wiki(root) ─> struttura cartelle + index.md/log.md (se assenti)        [REQ-001/002]
record(root, Brief) ─> pagina tematica (dedup) + index + 1 voce log           [REQ-010..013]
ingest(root, SourceBrief) ─> sources/ + propaga ref + marca contraddizioni    [REQ-020..023]
distill(root, Brief, LLMProvider) ─> pagina distillata + log (richiede LLM)    [REQ-030..033]
index_wiki(wiki_root, settings) ─> [nucleo] IndexingService(rebuild=True) ─> IndexReport  [REQ-040..045]

ogni operazione ─> WikiOpResult (+ log strutturato)                            [REQ-013/RNF-004]
idempotenza: scrivi solo se cambia; id chunk = path relativo                   [REQ-050/051]
```
