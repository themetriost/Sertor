# Operazione `structure` — bootstrap della struttura (idempotente)

> **Modulo operazione.** Esecutore: **curator/CLI** (puro meccanico, nessun giudizio).
> Per il **substrato condiviso** (tassonomia §3) vedi il playbook `wiki-playbook.md`. Qui solo la procedura.

Su un ospite nuovo (o per riparare cartelle/file speciali mancanti): `sertor-wiki-tools structure
init`. Crea le cartelle della tassonomia + index + log con seed minimo; **non sovrascrive** ciò che esiste
(contratto `wiki.structure/1`: `created` / `skipped_existing`). Nessun giudizio: puro meccanico.

Appendi una voce di log `structure` **solo se** ha creato qualcosa (`created` non vuoto); se è tutto
`skipped_existing`, **niente voce** (idempotente + regola anti-banale dell'indice §6).
