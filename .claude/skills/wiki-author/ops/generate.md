# Operazione `generate` — genera il wiki dal repo (da-zero) o aggiornalo dalle modifiche (da-diff)

> **Modulo operazione.** Esecutore: **solo flusso principale (Opus)** — il piano-pagine e il contenuto
> sono giudizio. Per il **substrato condiviso** (confine D↔N §2, tassonomia §3, convenzioni §4, voce di
> log §6) vedi il playbook `wiki-playbook.md`; per **se/cosa merita una pagina**
> [`../wiki-craft.md`](../wiki-craft.md) (test link/nome §1, archetipi e lente di prodotto §2, pagine di
> struttura §3), per **come si scrive** [`../page-craft.md`](../page-craft.md). Qui solo la procedura.
>
> *Storia:* nata come `generate-from-diff` (N8, completa come procedura il 2026-06-09, D-19/D-20);
> generalizzata il 2026-06-10 con l'ingresso **da-zero** (N3, FR-008). Le voci di log storiche
> `generate-from-diff` restano valide (il log è append-only).

La generazione è **una capacità, due ingressi** (FR-008: contenuto in linguaggio naturale a concetti
linkati, *aggiornabile incrementalmente*). **Selettore:** se l'ospite **non ha** `wiki.config.toml`, o la
root del wiki non esiste/è vuota → **da-zero** (bootstrap); altrimenti → **da-diff** (il default di
`/wiki generate`).

## Ingresso A — da-zero (bootstrap su un repo privo di wiki)

Tutte le chiamate CLI usano `--config <config dell'ospite>`: i path si risolvono relativi alla cartella
del file di config, quindi l'operazione funziona anche su un ospite diverso dalla cwd. **Ogni scrittura
(pagine, log, indice) avviene nel wiki dell'ospite** — mai in quello di chi esegue.

0. **Config dell'ospite (giudizio — prerequisito).** Se manca `wiki.config.toml` alla radice dell'ospite,
   **autoralo minimale** guardando il repo, senza presumere: `language` (la lingua della doc dell'ospite —
   il wiki si scrive in quella; chiedi se ambiguo), `root`/`index_file`/`log_file`/`log_dir`,
   `[[taxonomy]]` (le 5 aree del profilo standard come base, adattate alla natura dell'ospite),
   `source_dirs` (FR-009 — doc, codice, test, specs **se esistono**: verificalo), `exclude` (VCS, build,
   dipendenze, media), `[rag] enabled=false` se l'ospite non ha infrastruttura RAG, `[roles]` solo se
   l'host ha gli agenti. *Questo passo è il segnaposto-giudizio di `sertor wiki init` (D-16): quando la
   CLI d'install nascerà, la parte meccanica diventerà sua.*
1. **Struttura (D).** `sertor-wiki-tools structure init --config <config> --json` — idempotente: crea
   cartelle della tassonomia + index + log, non sovrascrive nulla.
2. **Ricognizione delle fonti (D+N).** `collect --json` per l'inventario (al bootstrap è vuoto; alla
   seconda run è l'anti-duplicato). Ordine di lettura delle fonti-input: **README** → **doc dedicata** →
   **specs/requirements** se esistono → **struttura del codice** (albero, entry point, contratti
   pubblici — input *opzionale*: su un ospite solo-documentale si salta, FR-029/D-9) → **test** (il
   comportamento). Serve la **mappa**, non il mirror: niente lettura esaustiva file-per-file.
3. **Piano-pagine bounded (N — il passo distintivo).** Enumera i candidati col test del link/nome
   (wiki-craft §1) e la lente di prodotto (§2 se l'ospite è codice); applica l'**anti-frammentazione**
   (poche pagine vive). **Proponi il piano prima di scrivere** — elenco `pagina → area → scopo in una
   riga` — e sottoponilo all'utente se il flusso è interattivo. **Prima ondata: 6–12 pagine** (sotto manca
   il cuore del dominio, sopra è frammentazione: il wiki è cumulativo, il resto arriva con le run
   successive). Includi le pagine di struttura necessarie (la home coincide con l'`index_file`;
   un'overview solo se il dominio la richiede — wiki-craft §3).
4. **Scrittura (N).** Pagine conformi a page-craft: definizione in apertura, il *perché*, le relazioni coi
   vicini, claim ancorati alle fonti — **linka la fonte, non ricopiarla** (né doc né codice in snippet).
   Tessi la rete `[[wikilink]]`; riga d'indice per pagina (`upsert-index`, o curata a mano se l'indice
   dell'ospite è curato — giudizio).
5. **Log (D).** **UNA** voce di log `generate` via `append-log --config <config>` — nel **wiki
   dell'ospite** — con lead «bootstrap da-zero» e l'essenziale (n. pagine, fonti lette). La prima voce fa
   anche da àncora temporale per i futuri run da-diff/`scan`. Questo ingresso **non richiede git**.
6. **Verifica (D).** `lint --json` + `validate --json` sull'ospite: zero broken link, zero orfani,
   frontmatter completo. **Idempotenza:** una seconda invocazione su un wiki già accurato non riscrive
   nulla — `structure init` risponde tutto `skipped_existing`, il `collect` mostra le pagine esistenti, e
   senza delta non c'è seconda ondata né nuova voce di log (regola anti-banale, playbook §6).

## Ingresso B — da-diff (aggiorna dalle modifiche recenti)

Evita di rileggere l'intero repo: aggiorna solo ciò che è cambiato. Trigger = comando manuale `/wiki`
(D-19); ambito = changeset dell'ultimo commit. Lint/freschezza qui sono **non bloccanti** (gate eliminato,
D-20).

1. Ancora il punto di partenza con `uv run sertor-wiki-tools scan --json` (file pendenti via mtime) e/o
   **delega al ruolo VCS** (`[roles].vcs`) un brief di sola lettura «`git log` + `git diff` dal punto X».
   X = data dell'ultima voce di log (o l'ultimo commit che tocca il wiki). *(Le operazioni git si
   delegano; se l'ospite non ha un ruolo VCS configurato, chiedi all'utente come ottenere il diff.)*
2. Col diff ricevuto, aggiorna **solo** le pagine impattate (giudizio).
3. Aggiorna l'indice e appendi una voce di log `generate` che cita il range di commit.
