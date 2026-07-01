# SpecLift (MVP)

Genera **requisiti EARS ancorati** a partire da un **changeset git**. Dato un commit, un range o il
diff *staged*, SpecLift produce un documento di requisiti dove ogni requisito è **multi-quota**
(capacità utente · comportamento · implementazione) e **ancorato** a `file:righe` + simbolo + (se
trovato) il test che lo copre — e **ogni àncora è verificata deterministicamente**.

È il ponte `diff → requisito`, primitivo condiviso del *gate del pre-merge*.

## Architettura — "sandwich deterministico"

Sette stadi, di cui **uno solo** è giudizio LLM; gli altri sei sono deterministici e testabili.

```
ingest → parse_diff → locate_evidence → bundle → [lift] → verify → render
  (git)     (puro)        (RAG)         (puro)   (LLM)    (moat)   (JSON+MD)
```

- **RAG localizza, il filesystem verifica.** Sertor RAG (via *vehicle*, mai `import sertor_core`)
  propone simboli/test candidati; la verifica delle àncore è una funzione deterministica sul
  filesystem (file esiste, righe nei limiti, simbolo presente, test che referenzia il simbolo). Niente
  esecuzione di codice. Questo è il **moat**: l'LLM non inventa mai àncore.
- **Domain puro / ports & adapters.** Il dominio (`src/speclift/domain/`) non importa SDK né I/O; gli
  adapter (`git`, RAG, EARS-author, filesystem) stanno dietro *port* e sono wirati nel composition root
  (`pipeline.py`).

## Uso

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"
speclift HEAD                       # report JSON + Markdown dal commit HEAD
speclift --staged --format md       # diff staged, sola vista Markdown su stdout
speclift --range main..HEAD --out ./report
pytest                              # suite deterministica (core con fake dei port)
```

**Exit code** (vedi `specs/001-speclift-mvp/contracts/cli.md`): `0` ok · `2` ref git invalido ·
`3` RAG non disponibile/indice mancante · `4` capacità `requirements` non disponibile · `5`
bundle/contratto invalido. Nessun output parziale silenzioso su errore (fail-loud).

## Stato: stesura EARS *stubbed* — dipendenza esterna (BLOCKED-EXT)

La formulazione EARS vera è **delegata** alla capacità `requirements` di Sertor in modalità
*bundle-driven non interattiva*. **Quella modalità non esiste ancora** in sertor-flow (richiesta
depositata nell'inbox Sertor). Finché non è disponibile, l'adapter
`src/speclift/adapters/ears_requirements.py` è uno **stub** che:

- emette, per ogni elemento di evidenza, requisiti *placeholder* marcati `[EARS DEMANDATO A SERTOR]`,
  con l'**àncora presa dal bundle** (così verify/render girano end-to-end), e
- **segnala** la dipendenza mancante in `open_questions` (Constitution XI: degrada *e* segnala, non
  nasconde).

Tutto il resto della pipeline (ingest → parse → locate → bundle → verify → render → CLI) è **reale ed
esercitabile end-to-end**. Quando Sertor fornirà la modalità, si sostituisce **solo** l'adapter dietro
il port `EarsAuthor` — zero modifiche al core.

## Riferimenti

- Spec/Plan/Tasks: `specs/001-speclift-mvp/`
- Requisiti EARS canonici: `requirements/speclift/`
- Contratti (schemi + port): `specs/001-speclift-mvp/contracts/`
