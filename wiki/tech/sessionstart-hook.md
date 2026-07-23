---
title: SessionStart hook
type: tech
tags: [hook, claude-code, wiki, contesto, da-w1]
created: 2026-05-31
updated: 2026-07-23
sources: [".claude/settings.json", ".claude/hooks/wiki-session-start.py", "wiki/wiki.config.toml"]
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
**compact**. **Non trasporta più il contenuto**: emette una **direttiva breve** che istruisce il flusso
principale a caricare il contesto *di propria iniziativa* con il tool `Read`, e poi a **mostrare all'utente
l'executive summary** della roadmap (il blocco tra i marker `<!-- EXEC:START -->` / `<!-- EXEC:END -->`).

**Config-driven & host-agnostico (E10-FEAT-029, dal 2026-07-22).** L'hook **non hardcoda più i path**: li
costruisce leggendo `wiki.config.toml` (via `_hooklib.wiki_config`) — `root`, `index_file`, `log_dir`, e
l'**opt-in `[ritual].exec_page`** (sul dogfood = `syntheses/roadmap.md`). La direttiva **degrada**: include
solo i file che **esistono** (un wiki appena creato non riceve l'ordine di leggere una roadmap inesistente),
e la voce roadmap+EXEC compare **solo se** l'ospite ha configurato `exec_page` (un ospite generico riceve
index + ultima partizione di log, senza roadmap). Prima l'hook citava i letterali `wiki/syntheses/roadmap.md`
/ `wiki/index.md` / `wiki/log/`, che rompevano su un ospite con `root`/tassonomia diversi — bug corretto da
FEAT-029 (gemella di FEAT-031/032). Risolve la radice da `CLAUDE_PROJECT_DIR` (fallback cwd, via `_hooklib`).
Il wiring esatto vive in `.claude/settings.json` (non trascritto qui: una copia nel wiki divergerebbe al
primo ritocco).

La catena è: **l'hook *innesca*, il `Read` *trasporta*, il rituale tiene il *contenuto* vero**.

## Perché l'hook non stampa più il contenuto (il cap dei 10.000 caratteri)

L'output di un hook è **limitato a ~10.000 caratteri**: oltre quella soglia l'harness lo **salva su file** e
nel contesto inietta solo un **preview (~2 KB)**. La versione precedente stampava `index.md` *intero* (~12 KB)
più roadmap e coda log (~17 KB totali): sforava il cap a ogni avvio, così nel contesto arrivava solo mezza
roadmap e né indice né log. La causa **non** era il contesto della sessione (1M token, ampio) ma il **canale-
hook**. Il fix sposta il trasporto sul tool `Read`, il cui output entra **intero** nel contesto senza alcun
cap; l'hook resta ben sotto i 10 K perché porta solo istruzioni. *(Ridisegnato il 2026-06-09.)*

## Compatibilità con la rotazione del log

Il log del wiki è **partizionato per giorno** in `<root>/<log_dir>/<data>.md` (rotazione FEAT-008): non
esiste più un `log.md` unico. L'hook prende `root` e `log_dir` **dalla config** e seleziona la **partizione
più recente** (elenca i `*.md`, esclude `index.md`, ordina per nome — che per il formato `YYYY-MM-DD` è
anche ordine cronologico — e prende l'ultimo), mettendone il path nella direttiva perché sia il `Read` del
flusso principale a caricarne il contenuto. Se `log_dir` non è configurato (log single-file), ripiega sul
`log_file` della config; se non esiste nessun log, la voce viene **omessa** (degradazione, FEAT-029).

## Perché è rilevante per DA-W1

Conferma la decisione [[wiki-role-da-w1]]: il **ruolo 1 (contesto iniettato)** è competenza dell'**host**,
non del core di Sertor. L'MVP di Sertor si limita a esporre un wiki ben strutturato (`index.md` + log
interlinkati con wikilink); è l'host a iniettarlo così com'è. I ruoli 2 e 3 (query precisa via RAG,
ingestion) sono quelli che competono al core.

## Vedi anche
- [[wiki-role-da-w1]] — il wiki come corpus + superficie e la ripartizione dei ruoli host/core.
- [[step-ritual]] — il rituale di step, di cui questo hook è il promemoria d'avvio.
- [[meccanica-log-feat008]] — la rotazione del log che ha reso obsoleto `wiki/log.md`.
