# Contratti — LLM Wiki end-to-end (FEAT-010)

Contratti di libreria (core), di confine (services), CLI e MCP. Riusano FEAT-001/002/003.

## Dominio — generazione (momento a)

### `generate(root, llm, *, sources, git=None, scope="since_watermark", facade=None, max_pages=None) -> GenerationReport`
| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | nessun git/watermark | genera su **tutte** le pagine dalle fonti | `mode=baseline` | FR-018/103 |
| 2 | git + watermark | `changed_paths` → EntityPageMap → **solo** pagine collegate | `mode=incremental` | FR-018/037 |
| 3 | changeset irrilevante | no-op rapido | report vuoto | FR-037 |
| 4 | `manual_edited/` come fonte | **compila** pagine derivate; **non** modifica i file sorgente | non-distruttivo | D-1/FR-016 |
| 5 | re-index incrementale assente | fallback segnalato | `fallbacks=[stale-index]` | R10/FR-014 |
| 6 | input invariato | esito strutturale identico (id=path) | idempotenza | FR-113 |

## Dominio — ingest (import in ingested_sources)

### `ingest_sources(root, items, *, dry_run=False) -> IngestReport`
- Importa documentazione esterna in `ingested_sources/`; **import ≠ compile** (no pagine-riassunto).
  Invocabile alla creazione, on-demand, su update. Binari non leggibili **esclusi**. (FR-030/031/022)

## Dominio — manutenzione

### `lint(root) -> LintReport`  (LLM-free)
Link rotti · orfani · copertura/cross-ref mancanti. (FR-035)

### `freshness(root, llm, facade, git=None, *, scope, authority) -> FreshnessReport`
Pagina **obsoleta** vs codice/test (comportamento) o vs decisione (perché); incrementale sul changeset o
full. (FR-017/036/037/038)

## Dominio — retrieval (momento b)

### `index_wiki_generated(root, settings) -> IndexReport`
Indicizza **solo** il wiki generato in una collezione **separata** (non gli input). Query congiunta col
codice via facade esistente; refresh **indipendente**. (FR-010/011/023/024)

## Confine — gate al commit (services)

### `run_commit_gate(root, llm, facade, git, *, threshold, authority, override=False, override_reason=None) -> GateOutcome`
| # | Comportamento | Esito | Req |
|---|---------------|-------|-----|
| 1 | incrementale → lint + freschezza sul changeset | report | FR-037 |
| 2 | problemi ≥ soglia | **blocca**, avvisa, **propone ≥1 soluzione** (incl. "ignora e committa") | FR-041 |
| 3 | `override=True` | procede, **registra** l'override | FR-042 |
| 4 | sotto soglia | `warning` (non blocca) | FR-110 |

Il blocco/exit vive qui (confine), non nel dominio. Trigger contract portabile; config-manager = binding.

## Confine — setup

### `init_wiki(root, *, install_binding=True, initial_ingest=None) -> SetupReport`
Crea struttura (`create_wiki`) + **installa il binding del trigger** + ingest iniziale opzionale. (FR-040)

## CLI (`sertor wiki ...`)
```
sertor wiki init <root> [--ingest <path>]      # setup: struttura + binding + ingest iniziale
sertor wiki generate <root> [--scope ...]      # generazione (on-demand)
sertor wiki ingest <root> <path|url> ...       # import in ingested_sources/
sertor wiki lint <root>                        # lint strutturale
sertor wiki gate <root> [--threshold ...] [--override --reason ...]   # gate (exit≠0 se blocked)
sertor wiki index <root>                       # indicizza il wiki generato (collezione separata)
sertor search "<q>"                            # query (RAG, wiki+codice) — comando esistente
```

## MCP (tool)
`wiki_generate` · `wiki_ingest` · `wiki_lint` · `wiki_gate` · (query via i tool `search_*` esistenti).
Stesse capacità on-demand della CLL, per uso cross-client. (FR-032)

## Invarianti
- **Principio I**: git dietro `GitPort`; gate fuori dal dominio.
- **Principio VI**: `manual_edited/` mai modificato; idempotenza; gate revisionabile.
- **Principio IV**: fallback (async, stale-index) e conflitti (human-in-the-loop) **espliciti**.
- **No-code**: tutte le funzioni operano anche senza fonte `code`.

## Test
Wiki sandbox + **LLM scriptato** + **FakeGit**: baseline/incrementale/no-op; manual_edited mai toccato;
input non indicizzati; lint (link/orfani); freschezza (obsoleto vs codice/decisione); gate
(blocked/warning/override); ingest import≠compile; idempotenza; percorso senza codice.
