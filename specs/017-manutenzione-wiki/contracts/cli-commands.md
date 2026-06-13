# Contract — CLI (feature 017)

**Data**: 2026-06-13 · **Branch**: `017-manutenzione-wiki`

Delta della CLI `sertor-wiki-tools` (`src/sertor_core/wiki_tools/__main__.py`).

## 1. `move` — spostamento con riscrittura dei link

```
sertor-wiki-tools move <src> <dest> [--dry-run] [--json]
                       [--config ...] [--root ...]
```
- `<src>`, `<dest>`: path relativi alla **radice del wiki** (`.md`).
- `--dry-run`: calcola e riporta il piano senza modificare alcun file.
- Esito JSON: contratto `wiki.move/1` (`source`, `destination`, `rewritten[]`, `moved`, `dry_run`).
- Esito umano: `moved=<bool> dry_run=<bool> rewritten=<n_file> occurrences=<tot>`.
- Errori (exit 1, con `--json` → `wiki.error/1`):
  - sorgente non trovata;
  - destinazione già esistente **con sorgente presente** (collisione, REQ-013);
  - path fuori dalla radice del wiki o non `.md`.
- Recovery (REQ-014): sorgente assente + destinazione presente → completa solo le riscritture
  residue dei link (nessun move), esito `moved=false`, senza errore.

## 2. `reconcile` — detection delle obsolescenze (sola lettura)

```
sertor-wiki-tools reconcile [--json] [--config ...] [--root ...]
```
- Elenca le pagine con frontmatter `status: superseded`.
- Esito JSON: contratto `wiki.reconcile/1` (`candidates[]` con `path`/`status`/`updated`/
  `superseded_by`/`reason`, `clean`).
- Esito umano: `candidates=<n> clean=<bool>`.
- **Mai** modifica/cancella file (REQ-023/027). Nessuna pagina superata → `candidates=[] clean=true`,
  exit 0.

## 3. `collect` — campo `status` (additivo)

Invariato come comando; il contratto `wiki.collect/1` ora include `status` nei metadati per pagina
(stringa, vuota se assente). Forward-compatible, nessun bump di versione.

## 4. Convenzioni invariate

Auto-discovery del `--config` (feature 016), exit code `0`/`1`(`SertorError`)/`2`(argparse), I/O
UTF-8, `--json` per il contratto versionato. `move`/`reconcile` ereditano queste convenzioni.
