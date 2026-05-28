---
description: Consolida nel wiki locale il lavoro della sessione (log + pagine + index)
argument-hint: "[ambito opzionale, es. 'esperimento 01' o 'ingest raw/papers/x.pdf']"
---

Aggiorna il **wiki locale** in `wiki/` seguendo lo schema della sezione
"Wiki & documentazione" di `CLAUDE.md`. Ambito richiesto: $ARGUMENTS
(se vuoto, considera tutto il lavoro rilevante svolto in questa sessione).

Procedi così:

1. Leggi `wiki/index.md` e la coda di `wiki/log.md` per capire lo stato attuale.
2. Determina l'operazione: **record** (lavoro/decisione nostra), **ingest** (nuova fonte
   in `raw/`), **query** (esplorazione da archiviare) o **lint** (verifica di coerenza).
3. Crea o aggiorna le pagine rilevanti in `concepts/`, `tech/`, `experiments/`, `sources/`
   o `syntheses/`, con frontmatter YAML completo e backlink `[[...]]` corretti.
4. Aggiorna i cross-reference e `wiki/index.md` (link + summary di una riga).
5. Appendi a `wiki/log.md` una voce `## [YYYY-MM-DD] <operazione> | <titolo>`
   (usa la data odierna).
6. Se trovi contraddizioni o pagine orfane, segnalale esplicitamente.

Mantieni le pagine concise e interlinkate. Non modificare mai i file in `raw/`.
Al termine, riassumi in 2-3 righe cosa hai aggiornato.
