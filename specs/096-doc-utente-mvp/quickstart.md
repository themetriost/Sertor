# Quickstart — verifica di accettazione (096-doc-utente-mvp)

Come **verificare** che la feature è consegnata. Non c'è codice/test automatico: la verifica è la lettura
degli artefatti contro i criteri di successo (SC-001..006) + un controllo link.

## 1. Percorso unico → primo valore (SC-001, US1)

- Aprire **solo** `docs/getting-started.md` e seguirlo dall'alto in basso.
- Verificare che copra, **in ordine**: prerequisiti → install RAG → index → prima query, come un unico
  viaggio lineare, **senza** far scegliere l'assistente in cima.
- Verificare che ogni comando sia uno di quelli reali (Decisione 4 di `research.md`) e che il dettaglio
  divergente per-assistente sia **delegato** a `install-claude.md`/`install-copilot.md` (non ricopiato).

## 2. Esempio concreto code+doc (SC-003, US1/US2)

- In fondo al getting-started **e** nel README, verificare la presenza di **un esempio concreto** di
  `search_combined` che restituisce **codice + documentazione insieme** (la tupla `(docs, code)`),
  illustrativo/generico (query sul repo dell'utente), non legato al corpus di Sertor.

## 3. README valore-first (SC-002, US2)

- Aprire `README.md`: verificare che **apra** col differenziatore **fusione code+doc** (*il codice dice
  cosa fa, la documentazione dice perché*), **prima** di ogni elenco di feature/status.
- Verificare che sia comprensibile a un non-addetto in pochi minuti, **senza gergo** non spiegato.
- Verificare che punti a `docs/getting-started.md` come **ingresso unico**.
- Verificare che i **fatti** di capacità/status non siano regrediti (preservati, riordinati) rispetto al
  README precedente.

## 4. Convergenza & separazione (SC-005/SC-006, US3)

- Verificare che `install-claude.md`, `install-copilot.md`, `retrieval.md` rimandino al getting-started
  (convergenza), e che il getting-started rimandi a `install.md` (reference) e `retrieval.md` (concetti).
- Verificare **zero** blocchi di contenuto duplicati verbatim tra `getting-started.md` e i per-assistente.
- Verificare **zero** rimandi che espongano `wiki/` o `specs/` come doc utente.

## 5. Controllo link (SC-004)

- Verificare (manuale/scriptato) che **ogni** link relativo `[…](….md)` in `README.md` e in `docs/*.md`
  risolva a un file esistente (0 link interni rotti). Vedi DA-4/Decisione 1: nessun linter automatico per
  `docs/` — il controllo è parte dell'implement.

## Esito atteso

Tutti i SC verdi → feature pronta per PR. Nessun `sertor-core`/CLI/installer toccato (D↔N): la suite
pytest + ruff non è impattata, ma il **gate pre-merge** (suite completa `not cloud` + `ruff check .`)
resta verde per costruzione (nessuna modifica a codice).
