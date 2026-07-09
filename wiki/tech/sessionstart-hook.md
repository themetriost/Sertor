---
title: SessionStart hook
type: tech
tags: [hook, claude-code, wiki, contesto, da-w1]
created: 2026-05-31
updated: 2026-07-09 (A-09: hook riscritto in Python portabile, non più comando PowerShell inline)
sources: [".claude/settings.json", ".claude/hooks/wiki-session-start.py"]
---

# SessionStart hook

Il **SessionStart hook** fa aprire la sessione con lo **stato del progetto** nel contesto. Dal 2026-07-09
(A-09) è uno **script Python portabile** — `wiki-session-start.py`, invocato via
`uv run --no-project python` (nessuna dipendenza da PowerShell/`pwsh`, funziona su ogni OS) — cablato in
`.claude/settings.json` (`statusMessage` = "Carico lo stato del wiki", timeout 15s). È la prova empirica del ruolo *"contesto
iniettato"* del wiki ([[wiki-role-da-w1]]): l'**host** (Claude Code) spinge la mappa del wiki davanti al
modello in modalità *push*, prima di qualunque query e senza passare dal RAG.

## Cosa fa (hook sottile: innesca, non trasporta)

Si esegue all'**avvio** della sessione e — come si osserva dai `system-reminder` — anche su **resume** e
**compact**. **Non trasporta più il contenuto**: emette una **direttiva breve** (~630 byte) che istruisce il
flusso principale a caricare il contesto *di propria iniziativa* con il tool `Read` —
`wiki/syntheses/roadmap.md`, `wiki/index.md`, l'ultimo file di `wiki/log/` — e poi a **mostrare all'utente
l'executive summary** della roadmap (il blocco tra i marker `<!-- EXEC:START -->` / `<!-- EXEC:END -->`).
L'unica computazione che fa è risolvere la radice da `CLAUDE_PROJECT_DIR` (con fallback alla cwd, via
`_hooklib`) e calcolare il **nome** della partizione di log più recente (vedi sotto), da nominare nella
direttiva. Il wiring esatto vive in `.claude/settings.json` (non trascritto qui: una copia nel wiki
divergerebbe al primo ritocco).

La catena è: **l'hook *innesca*, il `Read` *trasporta*, il rituale tiene il *contenuto* vero**.

## Perché l'hook non stampa più il contenuto (il cap dei 10.000 caratteri)

L'output di un hook è **limitato a ~10.000 caratteri**: oltre quella soglia l'harness lo **salva su file** e
nel contesto inietta solo un **preview (~2 KB)**. La versione precedente stampava `index.md` *intero* (~12 KB)
più roadmap e coda log (~17 KB totali): sforava il cap a ogni avvio, così nel contesto arrivava solo mezza
roadmap e né indice né log. La causa **non** era il contesto della sessione (1M token, ampio) ma il **canale-
hook**. Il fix sposta il trasporto sul tool `Read`, il cui output entra **intero** nel contesto senza alcun
cap; l'hook resta ben sotto i 10 K perché porta solo istruzioni. *(Ridisegnato il 2026-06-09.)*

## Compatibilità con la rotazione del log

Il log del wiki è **partizionato per giorno** in `wiki/log/<data>.md` (rotazione FEAT-008): non esiste più
un `wiki/log.md` unico. L'hook seleziona quindi la **partizione più recente** di `wiki/log/` (elenca i
`*.md`, esclude `index.md`, ordina per nome — che per il formato `YYYY-MM-DD` è anche ordine cronologico —
e prende l'ultimo) e ne **mette il path nella direttiva**, perché sia il `Read` del flusso principale a
caricarne il contenuto; con fallback al vecchio `wiki/log.md` se la cartella non c'è.

## Perché è rilevante per DA-W1

Conferma la decisione [[wiki-role-da-w1]]: il **ruolo 1 (contesto iniettato)** è competenza dell'**host**,
non del core di Sertor. L'MVP di Sertor si limita a esporre un wiki ben strutturato (`index.md` + log
interlinkati con wikilink); è l'host a iniettarlo così com'è. I ruoli 2 e 3 (query precisa via RAG,
ingestion) sono quelli che competono al core.

## Vedi anche
- [[wiki-role-da-w1]] — il wiki come corpus + superficie e la ripartizione dei ruoli host/core.
- [[step-ritual]] — il rituale di step, di cui questo hook è il promemoria d'avvio.
- [[meccanica-log-feat008]] — la rotazione del log che ha reso obsoleto `wiki/log.md`.
