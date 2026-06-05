# Contract — Schemi JSON versionati

Ogni operazione emette un oggetto JSON con un campo `schema` versionato (`<nome>/<versione>`). I contratti contengono
**metadati e riferimenti**, mai il contenuto integrale delle pagine. I consumatori (hook, skill, metà LLM FEAT-003-N)
devono tollerare campi aggiuntivi futuri (forward-compatible) e verificare `schema`.

## `wiki.scan/1`
```json
{
  "schema": "wiki.scan/1",
  "pending": 3,
  "anchor": "2026-06-05T10:00:00",
  "dirs_scanned": ["src", "specs", "requirements", ".claude"],
  "message": "Lavoro non ancora registrato nel wiki: 3 file più recenti dell'ultima voce di log."
}
```
- `pending` ≥ 0 · `anchor` = ISO 8601 o `null` se il registro non esiste/è vuoto · `message` = da `strings` nella lingua del profilo.

## `wiki.structure/1`
```json
{ "schema": "wiki.structure/1", "created": ["concepts", "tech", "index.md", "log.md"], "skipped_existing": ["log.md"] }
```
- `created` = elementi creati · `skipped_existing` = preesistenti lasciati intatti (non-distruttività, SC-006).

## `wiki.lint/1`  *(usato da `lint` e `validate`)*
```json
{
  "schema": "wiki.lint/1",
  "broken_links": [ { "page": "tech/x.md", "target": "y" } ],
  "orphans": [ "sources/z.md" ],
  "missing_frontmatter": [ { "page": "concepts/a.md", "missing": ["updated"] } ],
  "naming_violations": [ { "page": "Tech/BadName.md", "reason": "not-kebab-case" } ]
}
```
- Liste vuote = wiki pulito. `naming_violations` popolato solo da `validate`/`lint` completo.

## `wiki.collect/1`
```json
{
  "schema": "wiki.collect/1",
  "root": "wiki", "index": "index.md", "log": "log.md",
  "pages": [
    { "rel_path": "concepts/rag.md", "area": "concepts", "type": "concept",
      "title": "RAG", "tags": ["rag"], "frontmatter_present": true, "wikilinks": ["chunking"] }
  ]
}
```
- `pages[].rel_path` = identità stabile (POSIX). Niente corpo delle pagine.

## `wiki.index/1`  *(US5)*
```json
{ "schema": "wiki.index/1", "collection": "wiki__azure-large", "documents": 42, "regenerated": true }
```
- Se `rag.enabled=false` → `{ "schema": "wiki.index/1", "collection": null, "documents": 0, "regenerated": false }` (no-op pulito).

## Errori
Su condizione d'errore esplicita il processo esce con codice `1` e scrive su **stderr** un messaggio azionabile; con
`--json` può inoltre emettere `{ "schema": "wiki.error/1", "error": "ConfigError", "message": "..." }`. Niente stato
parziale (Principio IV).
