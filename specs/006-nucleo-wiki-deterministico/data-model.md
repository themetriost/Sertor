# Data Model — FEAT-003-D

Entità del nucleo deterministico. Tutte sono **dataclass pure** (serializzabili), senza dipendenze esterne. Le
specificità dell'ospite vivono **solo** in `WikiProfile`.

## WikiProfile *(la config dell'ospite — unica fonte di specificità)*

Caricata da `wiki.config.toml` (override del path via `--config`/`--root`). Default = profilo Sertor (file esterno).

| Campo | Tipo | Note / validazione |
|---|---|---|
| `profile` | str ∈ {`code+doc`,`doc-only`,`code-only`} | profilo dell'ospite |
| `language` | str (es. `it`,`en`) | seleziona le `strings` |
| `root` | str (path rel.) | radice del wiki (REQ-006) — **obbligatorio** |
| `index_file` | str | default `index.md` |
| `log_file` | str | default `log.md` |
| `taxonomy` | list[TaxonomyEntry] | ≥1 voce; nomi/dir unici |
| `source_dirs` | list[str] | cartelle scansionate dallo `scan` (FR-009); può essere vuota (`doc-only` senza codice) |
| `exclude` | list[str] (glob) | pattern di esclusione per lo `scan` |
| `frontmatter_required` | list[str] | campi obbligatori (default da consolidato: `title,type,tags,created,updated`) |
| `frontmatter_optional` | list[str] | es. `sources` |
| `wikilink_style` | str | default `[[name]]` |
| `log_format` | str (template) | default `## [{date}] {op} | {title}` |
| `roles` | dict[str,str] | es. `{curator: wiki-keeper, vcs: configuration-manager}` (consumato dalle skill, non dal nucleo) |
| `rag` | dict | `{enabled: bool, corpus: str}` — abilita US5; se `enabled=false`, l'indicizzazione è un no-op pulito |
| `strings` | dict[str,str] | messaggi localizzati (es. `pending`) |

**Validazione (`profile.py`)**: `root`, `taxonomy` (≥1), `language` presenti → altrimenti `ConfigError` esplicito
(Principio IV). Una cartella di tassonomia dichiarata ma assente sul disco → **warning + skip**, non errore.

## TaxonomyEntry

| Campo | Tipo | Note |
|---|---|---|
| `name` | str | identificatore logico (es. `concepts`) |
| `dir` | str | cartella relativa sotto `root` (es. `concepts`) |
| `type` | str | valore del campo `type` nel frontmatter delle pagine di quell'area |

## WikiPage *(derivata, non persistita)*

Rappresentazione in memoria di una pagina del wiki durante collect/lint.

| Campo | Tipo | Note |
|---|---|---|
| `rel_path` | str (POSIX) | **identità stabile** (REQ-051) |
| `area` | str | nome dell'area di tassonomia (dalla cartella) |
| `type` | str | dal frontmatter |
| `title` | str | dal frontmatter |
| `tags` | list[str] | dal frontmatter |
| `frontmatter_present` | bool | blocco `---...---` presente e parsabile |
| `missing_fields` | list[str] | campi richiesti assenti |
| `wikilinks` | list[str] | bersagli `[[..]]` uscenti |

## Contratti di risultato *(serializzati in JSON — vedi `contracts/`)*

Ogni operazione restituisce una dataclass con un campo `schema` versionato.

- **ScanResult** (`wiki.scan/1`): `pending:int`, `anchor:str|null` (iso), `dirs_scanned:list[str]`, `message:str`.
- **LintResult** (`wiki.lint/1`): `broken_links:list[{page,target}]`, `orphans:list[str]`,
  `missing_frontmatter:list[{page,missing:list[str]}]`.
- **CollectResult** (`wiki.collect/1`): `root:str`, `index:str`, `log:str`, `pages:list[WikiPage-meta]` (senza corpo).
- **StructureResult** (`wiki.structure/1`): `created:list[str]`, `skipped_existing:list[str]`.
- **IndexResult** (`wiki.index/1`, US5): `collection:str`, `documents:int`, `regenerated:bool`.

## Relazioni / invarianti

- `WikiProfile` è l'**unico** input di specificità: ogni path/nome/lingua deriva da qui (Principio X).
- `rel_path` è l'identità trasversale: collect, lint e registry usano lo stesso id (REQ-050/051 → idempotenza).
- Nessuna entità contiene il **contenuto integrale** delle pagine nei contratti JSON (solo metadati + riferimenti).
