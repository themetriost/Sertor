---
title: SessionStart hook
type: tech
tags: [hook, claude-code, wiki, contesto, da-w1]
created: 2026-05-31
updated: 2026-06-09
sources: [".claude/settings.json"]
---

# SessionStart hook

Il **SessionStart hook** inietta lo **stato del wiki** nel contesto della sessione al suo avvio. È un
comando PowerShell **inline** (non uno script separato) dichiarato in `.claude/settings.json`
(`statusMessage` = "Carico lo stato del wiki", timeout 15s). È la prova empirica del ruolo *"contesto
iniettato"* del wiki ([[wiki-role-da-w1]]): l'**host** (Claude Code) spinge la mappa del wiki davanti al
modello in modalità *push*, prima di qualunque query e senza passare dal RAG.

## Cosa fa

Si esegue all'**avvio** della sessione e — come si osserva dai `system-reminder` — anche su **resume** e
**compact**. In sola lettura: legge i file del wiki e ne stampa il contenuto su STDOUT, che l'harness
**inietta nel contesto** come primo blocco prima del turno dell'utente. Non scrive nulla. Nel dettaglio:
forza l'output in UTF-8 (accenti delle pagine italiane), risolve la radice da `$env:CLAUDE_PROJECT_DIR`,
stampa l'intero `wiki/index.md` (la mappa del wiki) e infine un promemoria a delegare gli aggiornamenti al
`wiki-curator`. Il comando esatto vive in `.claude/settings.json` (non trascritto qui: una copia nel wiki
divergerebbe al primo ritocco).

Il payload è **piccolo e curato** per scelta: l'indice (la struttura navigabile) e — quando disponibile —
la coda del log recente, **non** chunk casuali né l'intero wiki (troppo rumoroso per il contesto iniziale).

## Compatibilità con la rotazione del log

Il log del wiki è **partizionato per giorno** in `wiki/log/<data>.md` (rotazione FEAT-008): non esiste più
un `wiki/log.md` unico. L'hook seleziona quindi la **partizione più recente** di `wiki/log/` (elenca i
`*.md`, esclude `index.md`, ordina per nome — che per il formato `YYYY-MM-DD` è anche ordine cronologico —
e prende l'ultimo) e ne stampa la coda; con fallback al vecchio `wiki/log.md` se la cartella non c'è.
*(Allineato il 2026-06-09: prima leggeva `wiki/log.md` fisso, ormai inesistente → la coda del log non
veniva più iniettata.)*

## Perché è rilevante per DA-W1

Conferma la decisione [[wiki-role-da-w1]]: il **ruolo 1 (contesto iniettato)** è competenza dell'**host**,
non del core di Sertor. L'MVP di Sertor si limita a esporre un wiki ben strutturato (`index.md` + log
interlinkati con wikilink); è l'host a iniettarlo così com'è. I ruoli 2 e 3 (query precisa via RAG,
ingestion) sono quelli che competono al core.

## Vedi anche
- [[wiki-role-da-w1]] — il wiki come corpus + superficie e la ripartizione dei ruoli host/core.
- [[step-ritual]] — il rituale di step, di cui questo hook è il promemoria d'avvio.
- [[meccanica-log-feat008]] — la rotazione del log che ha reso obsoleto `wiki/log.md`.
