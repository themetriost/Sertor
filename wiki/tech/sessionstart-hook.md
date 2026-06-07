---
title: SessionStart hook ('Carico lo stato del wiki')
type: tech
tags: [hook, claude-code, wiki, contesto, da-w1]
created: 2026-05-31
updated: 2026-05-31
sources: [.claude/settings.json]
---

# Cos'è e dove

**Hook `SessionStart`** di Claude Code, definito in `.claude/settings.json`.

È un **COMANDO POWERSHELL INLINE** (non uno script a parte) che si esegue **all'avvio di ogni
sessione**. Parametri:
- Shell: `powershell`
- Timeout: `15` secondi
- Status message: `"Carico lo stato del wiki"`

# Quando si attiva

All'**AVVIO** di una sessione e — come si osserva dai `system-reminder` in conversation — anche su:
- **RESUME** (ripresa dopo pausa)
- **COMPACT** (compattazione del contesto)

Quindi ricarica lo stato del wiki **ogni volta che la sessione (ri)parte o viene compattata**.

# Cosa fa, passo per passo

1. **Forza UTF-8**:
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```
   Assicura che l'output sia decodificato correttamente. Essenziale per gli accenti delle pagine
   italiane (non si corrompono).

2. **Calcola la radice del progetto**:
   ```powershell
   $d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }
   ```
   La radice è fornita dall'harness di Claude Code (fallback alla cartella corrente se non set).

3. **Calcola i path del wiki**:
   ```powershell
   $idx = Join-Path $d "wiki/index.md"
   $log = Join-Path $d "wiki/log.md"
   ```

4. **Se `index.md` esiste**: stampa il contenuto intero:
   ```powershell
   if (Test-Path $idx) {
       Write-Host "=== WIKI INDEX ===" -ForegroundColor Cyan
       Get-Content -Raw $idx
   }
   ```

5. **Se `log.md` esiste**: stampa le ULTIME **20 RIGHE**:
   ```powershell
   if (Test-Path $log) {
       Write-Host "=== WIKI LOG (coda) ===" -ForegroundColor Cyan
       Get-Content -Tail 20 $log
   }
   ```

6. **Stampa un promemoria**:
   ```powershell
   Write-Host "`nPromemoria: aggiornamenti del wiki vanno delegati all'agente wiki-curator." -ForegroundColor Yellow
   ```

# Effetto ed effetti collaterali

Lo **STDOUT dell'hook viene INIETTATO nel contesto della sessione** all'avvio (è ciò che compare
in alto nella conversazione prima del primo turno dell'utente).

**È SOLA LETTURA**: legge `index.md` e `log.md` e stampa, non scrive nulla.

**Payload piccolo e curato**:
- Indice (la MAPPA/struttura del wiki)
- Coda del log (attività recente, ultime 20 righe)
- **NON** chunk casuali del wiki
- **NON** l'intero wiki (troppo rumoroso)

# Perché è rilevante per DA-W1 (ruolo 1)

È la **prova empirica** del *"contesto iniettato"* come ruolo del wiki.

Il wiki prepara il **terreno** prima di qualunque query. Usa la **SUPERFICIE STRUTTURATA**
del wiki (l'indice = mappa navigabile) in modalità **PUSH**, e a farlo è l'**HOST** (Claude Code),
non il RAG/MCP.

Conferma la decisione [[wiki-role-da-w1]]:

- **Ruolo 1 (contesto iniettato)** = competenza dell'HOST, non della core di Sertor nel MVP.
- **MVP Sertor** = espone wiki ben strutturato (`wiki/index.md`, `wiki/log.md` interlinkati);
  l'host li inietta così come sono.
- **Superficie strutturata** = il wiki è speciale perché ha indice, log, wikilink; l'host
  la sfrutta direttamente senza intermediazione RAG.

Nel MVP, il ruolo 1 è **già funzionante** (se qualcuno lanciava Claude Code su questo workspace,
vedrebbe l'indice e il log a inizio sessione). Questo allinea il presente con la decisione
di DA-W1: ruoli 2 e 3 (query precisa, ingestion) sono prioritari; ruolo 1 poggia su
infrastructura dell'host, non su feature Sertor.
