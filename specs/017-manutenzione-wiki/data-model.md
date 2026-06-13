# Data Model — Manutenzione wiki (feature 017)

**Data**: 2026-06-13 · **Branch**: `017-manutenzione-wiki`

Solo le **delta** rispetto a `wiki_tools` esistente.

## 1. Nuovi contratti (in `contracts.py`)

### `MoveResult` — `wiki.move/1`
```
source: str            # rel path POSIX (radice wiki) della pagina spostata
destination: str       # rel path POSIX di destinazione
rewritten: list[dict]  # [{ "page": rel_path, "occurrences": int }, ...] file con link riscritti
moved: bool            # True se il file è stato spostato (False in --dry-run o in recovery senza move)
dry_run: bool
schema: str = "wiki.move/1"
```

### `ReconcileResult` — `wiki.reconcile/1`
```
candidates: list[dict] # [{ "path", "status", "updated", "superseded_by", "reason" }, ...]
clean: bool            # True se candidates == []
schema: str = "wiki.reconcile/1"
```

Entrambi: dataclass `frozen`, `to_dict`/`to_json` come gli altri contratti; forward-compatible
(consumatore che conosce solo `schema` deserializza senza errori).

## 2. Estensione `wiki.collect/1` (additiva, no bump)

`collect._page_meta` aggiunge al dict per pagina:
```
"status": str   # valore del frontmatter `status` (vuoto se assente)
```
`CollectResult` invariato (lo `status` vive in `pages[i]`). Forward-compatible.

## 3. Nuovi moduli / funzioni

- `src/sertor_core/wiki_tools/move.py` — `move(profile, src, dest, dry_run=False) -> MoveResult`
  (riscrittura form-preserving D1 + link relativi D2; recovery D5; errori espliciti).
- `src/sertor_core/wiki_tools/reconcile.py` — `reconcile(profile) -> ReconcileResult`
  (read-only, filtra `status: superseded`, legge `superseded_by`).
- `collect.py` — `_page_meta` esteso con `status` (D8).
- `contracts.py` — `MoveResult`, `ReconcileResult`.
- `__main__.py` — `move`/`reconcile` in `_OPS`, parsing (2° positional `dest`, `--dry-run`),
  dispatch in `_run`, righe in `_human`.

## 4. Errori di dominio (Principio IV)

`move` solleva `ConfigError` (riusato) con messaggio esplicito su: sorgente non trovata; destinazione
già esistente con sorgente ancora presente (collisione, REQ-013); src/dest fuori dalla radice del
wiki o non `.md`. Nessuno stato parziale silenzioso; con `--json` → `wiki.error/1` (come il resto del
CLI).

## 5. Regole di risoluzione (riassunto da research)

- Wikilink: mappa old→new per forma (`_link_targets`), preserva `|alias`/`#anchor`.
- Link relativi: `posixpath.relpath(dest, page.parent)` quando `page.parent/path == src`.
- File processati: pagine (`iter_pages`) + indice; **non** le partizioni di log.
- `move` recovery: vedi tabella research D5.
