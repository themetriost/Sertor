# Research — FEAT-003-D (nucleo wiki deterministico host-agnostico)

Fase 0. Tutte le `NEEDS CLARIFICATION` risolte. Le decisioni riusano pattern già nel repo e nel riferimento
Transcriptio (`C:\Workspace\Git\ExternalRepos`/`Transcriptio` — script `collect.cjs`/`wiki-to-wiki-linker.cjs`).

## D1 — Formato della config dell'ospite: **TOML**
- **Decisione**: `wiki.config.toml` letto con `tomllib` (stdlib ≥ 3.11).
- **Rationale**: zero nuove dipendenze (coerente con Principio III e con l'isolamento extra `azure` del progetto);
  nativo; supporta array-of-tables (`[[taxonomy]]`) e stringhe multilinea (`[strings]`). Solo il nucleo Python lo
  parsa; hook/skill non devono parsare nulla (chiamano la CLI).
- **Alternative**: YAML (più diffuso ma richiede `pyyaml`, dipendenza nuova) — **scartato** per YAGNI/dipendenze.

## D2 — Parsing del frontmatter: **regex su stdlib**
- **Decisione**: estrarre il blocco frontmatter (`^---\n...\n---`) e i campi con `re`, senza librerie YAML.
- **Rationale**: il frontmatter del wiki è semplice (coppie `chiave: valore`, liste tag, wikilink); il pattern
  Transcriptio (`parseFrontmatter` in `collect.cjs:32-42`) dimostra che basta. Niente dipendenze.
- **Alternative**: `pyyaml` — scartato (dipendenza non giustificata).

## D3 — Segnale dello `scan` (lavoro pendente): **mtime, non git**
- **Decisione**: confronto del `mtime` dei file delle cartelle-sorgente (con esclusioni) vs il `mtime`/timestamp
  dell'ultima voce del registro. (Fissato in Clarifications.)
- **Rationale**: host-agnostico (funziona su ospiti non-git); coerente con l'attuale `wiki-pending-check.ps1`. Il
  refresh *git-driven* (watermark, consolidato FR-018/019) è competenza della metà LLM/agentica (FEAT-003-N).
- **Alternative**: watermark git — scartato qui (introdurrebbe una dipendenza da git nel nucleo deterministico).

## D4 — Contratto di output: **JSON versionato per operazione**
- **Decisione**: ogni operazione emette un JSON con un campo `schema` versionato (`wiki.scan/1`, `wiki.lint/1`,
  `wiki.collect/1`, `wiki.structure/1`), contenente metadati e riferimenti (mai il contenuto integrale delle pagine).
- **Rationale**: pattern Transcriptio (output JSON leggero consumato dall'LLM); separa il *meccanico* (Python) dal
  *giudizio* (LLM) come da confine di delega; versionare lo schema rende i consumatori robusti all'evoluzione.
- **Alternative**: output testuale ad-hoc — scartato (fragile da parsare per i consumatori).

## D5 — Orchestrazione indicizzazione: **riuso del facade/indexer esistente, collezioni separate**
- **Decisione**: `indexing.py` riusa `build_indexer()`/facade di `sertor_core` e indicizza il wiki in una collezione
  separata dalle sorgenti, via `collection_name((corpus, provider))` già esistente; rigenerazione indipendente.
- **Rationale**: DRY (Principio III) e Boundary (Principio II) — non si reimplementa il retrieval; l'embedding è una
  chiamata all'adapter esistente, non un giudizio LLM. Import **lazy** così le altre operazioni restano senza dipendenze.
- **Alternative**: un indexer dedicato al wiki — scartato (duplicazione).

## D6 — Superficie d'uso: **CLI come modulo + console-script**
- **Decisione**: `python -m sertor_core.wiki_tools <op> --config <path> [--root <override>] --json`; console-script
  `sertor-wiki-tools` in `pyproject.toml`. `__main__.py` è un entry-point **sottile** (parse args → chiama le funzioni
  pure → stampa JSON).
- **Rationale**: invocabile da hook PowerShell e skill senza accoppiare il nucleo alla CLI (Principio I); `--root`
  override segue il pattern Transcriptio (`--root` in `wiki-to-wiki-linker.cjs:20-36`).
- **Alternative**: solo API Python — scartato (gli hook/skell devono invocarlo da shell).

## D7 — Idempotenza & identità: **id = path relativo POSIX; merge set-based**
- **Decisione**: l'identità stabile di una pagina è il suo path relativo (`as_posix()`); le scritture di registro/index
  sono idempotenti via confronto set-based (non riaggiungere ciò che è già presente).
- **Rationale**: REQ-050/051 del consolidato; àncora in `prototype/shared/loaders.py` (id = rel path); pattern
  idempotente Transcriptio (`rewriteRelated`/`Set(existing)`).
- **Alternative**: hash del contenuto come id — scartato (instabile a modifiche minori; REQ-051 impone il path relativo).

## D8 — Prova di host-agnosticità (Principio X): **fixture ospite finto `doc-only`**
- **Decisione**: una fixture `tests/fixtures/doc_only_host/` con `wiki.config.toml` diverso (radice `knowledge/`,
  source-dirs `["docs"]`, lingua `en`, tassonomia diversa); i test eseguono **lo stesso** nucleo su Sertor e su questa
  fixture (SC-001) verificando che cambi solo per config.
- **Rationale**: rende il Principio X **verificabile** automaticamente, non un'affermazione.

## Note trasversali
- **Zero LLM/offline** (SC-005): nessun import di adapter LLM nel nucleo; le operazioni base non toccano la rete; US5
  (indicizzazione) usa embeddings locali via adapter esistente (marker `not cloud`).
- **Osservabilità** (Principio IX): `observability.logging` per ogni operazione (operazione, profilo, conteggi, esiti).
