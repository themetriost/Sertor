---
description: Consolida nel wiki locale il lavoro della sessione (record/ingest/query/lint/generate-from-diff/rag-sync)
argument-hint: "[operazione e/o ambito, es. 'lint', 'ingest https://...', 'rag-sync', 'esperimento 01']"
---

Mantieni il **wiki locale** in `wiki/`. Ambito/operazione richiesti: $ARGUMENTS
(se vuoto, considera il lavoro rilevante svolto in questa sessione → operazione `record`).

**Fonte di verità unica:** leggi `.claude/skills/genera-wiki/playbook.md` e **seguilo**. Definisce
tassonomia, convenzioni e le 6 operazioni. Non reinventare le regole qui.

Procedi così:

1. Leggi il **playbook**, poi `wiki/index.md` e la coda di `wiki/log.md` per lo stato attuale.
2. **Determina l'operazione** da `$ARGUMENTS` o dal lavoro di sessione, tra:
   `record` · `ingest` · `query` · `lint` · `generate-from-diff` · `rag-sync`.
3. **Esegui la procedura corrispondente** del playbook (input → passi → output), rispettandone i vincoli
   — in particolare: `generate-from-diff` delega `git log/diff` al `configuration-manager`; `rag-sync`
   gira solo nel flusso principale (lancia l'indexer di `sertor_core`).
4. Aggiorna i cross-reference e `wiki/index.md`, e appendi a `wiki/log.md` la voce
   `## [YYYY-MM-DD] <operazione> | <titolo>` (data odierna).
5. Segnala esplicitamente contraddizioni o pagine orfane.

Mantieni le pagine concise e interlinkate. Non toccare `prototype/` né le fonti originali.
Al termine, riassumi in 2-3 righe cosa hai aggiornato.
