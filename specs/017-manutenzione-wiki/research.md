# Research — Manutenzione wiki deterministica (feature 017)

**Data**: 2026-06-13 · **Branch**: `017-manutenzione-wiki`

Decisioni di design ancorate al codice reale di `wiki_tools` (`lint.py`, `collect.py`,
`frontmatter.py`, `contracts.py`, `__main__.py`).

---

## D1 — Riscrittura dei wikilink "form-preserving"

`lint._link_targets(rel)` dà le 3 forme con cui un wikilink può riferirsi a una pagina:
`{posix, no_ext, stem}` (es. `concepts/a.md`, `concepts/a`, `a`). `move` costruisce la mappa
**old→new** accoppiando le forme di `src` e `dest` per categoria
(`src_posix→dest_posix`, `src_no_ext→dest_no_ext`, `src_stem→dest_stem`) e per ogni wikilink
`[[T(|alias)(#anchor)]]` nel corpo, se `T ∈ mappa`, riscrive `T→mappa[T]` **preservando** alias e
anchor. Riusa la stessa nozione di target di `lint` (RNF-006: `move`+`lint` coerenti).

Conseguenza utile: uno spostamento **senza rename** (stesso stem) lascia invariati i link che usano
lo stem `[[a]]` (mappa stem→stem identità) e riscrive solo quelli che usano il path
(`[[concepts/a]]`→`[[experiments/a]]`). Un **rename** (stem diverso) riscrive anche gli `[[a]]`.

**Regex:** `move` usa una propria sub-regex coerente con `_WIKILINK` di `frontmatter.py`
(`\[\[([^\[\]|#]+)(?:[#|][^\[\]]*)?\]\]`) per sostituire **solo** la parte target.

## D2 — Link relativi Markdown

Oltre ai wikilink, `move` riscrive i link Markdown relativi `](path)` che risolvono alla pagina
spostata: per ogni pagina P, se `normalize(P.parent / path) == src`, sostituisce `path` con
`posixpath.relpath(dest, P.parent)`. URL (`http(s)://`, `mailto:`) e ancore (`#...`) restano
invariati. Copre REQ-010 per intero (wikilink **e** link relativi).

## D3 — File processati da `move`

`move` riscrive nelle **pagine** (`collect.iter_pages`, ordine deterministico) **e** nel **file
indice** (`profile.index_path`, escluso da `iter_pages` ma può linkare la pagina). **Non** tocca le
**partizioni di log** (storico append-only, FEAT-008): i link nei record datati sono testimonianza
storica, non si riscrivono. Documentato come scelta esplicita.

## D4 — Forma CLI

- `sertor-wiki-tools move <src> <dest> [--dry-run]`: due **positional** — si riusa il positional
  `subcommand` esistente come `src` e si aggiunge un secondo positional opzionale `dest`
  (`nargs="?"`). `move` valida che entrambi siano presenti (Principio IV).
- `sertor-wiki-tools reconcile [--json]`: nessun positional extra.
- `src`/`dest` sono relativi alla **radice del wiki** (`profile.root_path`), coerenti con il modello
  host-agnostico (i path vengono dalla config, non sono cablati).

## D5 — Idempotenza e recovery di `move` (REQ-013 ↔ REQ-014)

Riconciliazione dei due requisiti (collisione vs recovery):

| Stato `src` | Stato `dest` | Esito |
|---|---|---|
| esiste | **non** esiste | spostamento normale: riscrive i link, poi sposta il file |
| esiste | **esiste** | **collisione reale** → errore esplicito, nessuna modifica (REQ-013) |
| **non** esiste | esiste | **stato post-move/parziale** → recovery: completa solo le riscritture di link residue, nessun move (REQ-014); idempotente |
| non esiste | non esiste | errore: sorgente non trovata (REQ-014 edge) |

Ordine atomico: **rewrite-then-move**. La riscrittura è idempotente (sostituzione esatta old→new:
rieseguirla su link già riscritti è no-op). Così un'interruzione a metà si recupera rieseguendo lo
stesso comando.

## D6 — Successore di una pagina superata (REQ-022) — *risolve l'assunzione aperta della spec*

`reconcile` legge il successore dal **campo frontmatter `superseded_by`** (path/slug della pagina
che sostituisce), se presente; assente → campo successore vuoto (non un errore). **Decisione:**
fonte deterministica = solo frontmatter `superseded_by`. Il parsing di un "banner" di supersession
nel corpo è **scartato** (euristica fragile, non deterministica) — chi marca `status: superseded`
aggiunge `superseded_by` se vuole dichiarare il successore. Coerente con il modello frontmatter
esistente; zero ambiguità.

## D7 — `reason` e contratto di `reconcile`

`reason` è una stringa deterministica (`"status: superseded"`). Il contratto `wiki.reconcile/1`
elenca per candidata: `path`, `status`, `updated`, `superseded_by`, `reason`; più `clean: bool`
(true se lista vuota) a livello di risultato. Read-only assoluto (REQ-023/027).

## D8 — `collect` + `status` (REQ-021)

`collect._page_meta` aggiunge la chiave `"status": str(fields.get("status", ""))` al dict per pagina.
Additivo e forward-compatible: i consumatori che non lo conoscono ignorano il campo; `CollectResult`
(schema `wiki.collect/1`) non cambia struttura (lo `status` vive dentro `pages[i]`). Nessun bump di
versione.

## D9 — Trigger periodico (gruppo D, Could)

Nessuno scheduler in `wiki_tools` (host-agnostico, Principio X). Solo **documentazione** in
`docs/` / quickstart: come invocare `reconcile --json` da cron / Task Scheduler / hook CI e
indirizzarne l'output. Nessun codice.
