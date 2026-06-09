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

## ⚠️ Gap noto: la coda del log non viene più iniettata

Il comando tenta di leggere `wiki/log.md` e, se esiste, ne stampa le ultime 20 righe. Ma con la rotazione
del log (FEAT-008) **`wiki/log.md` non esiste più**: i log sono partizionati per giorno in
`wiki/log/<data>.md`. La guardia `if (Test-Path $log)` è quindi sempre falsa → **la sezione "coda del log"
è un no-op silenzioso**: oggi l'hook inietta solo `index.md`. Per ripristinare l'iniezione del log il
comando andrebbe aggiornato a leggere la partizione più recente di `wiki/log/`. *(Disallineamento tra
l'hook e la rotazione del log; vale come bug, non come comportamento voluto.)*

## Perché è rilevante per DA-W1

Conferma la decisione [[wiki-role-da-w1]]: il **ruolo 1 (contesto iniettato)** è competenza dell'**host**,
non del core di Sertor. L'MVP di Sertor si limita a esporre un wiki ben strutturato (`index.md` + log
interlinkati con wikilink); è l'host a iniettarlo così com'è. I ruoli 2 e 3 (query precisa via RAG,
ingestion) sono quelli che competono al core.

## Vedi anche
- [[wiki-role-da-w1]] — il wiki come corpus + superficie e la ripartizione dei ruoli host/core.
- [[step-ritual]] — il rituale di step, di cui questo hook è il promemoria d'avvio.
- [[meccanica-log-feat008]] — la rotazione del log che ha reso obsoleto `wiki/log.md`.
