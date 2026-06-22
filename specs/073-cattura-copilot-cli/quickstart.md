# Quickstart — Cattura memoria su GitHub Copilot CLI (FEAT-008)

**Branch**: `073-cattura-copilot-cli` · **Data**: 2026-06-22

Rende la memoria di Sertor operativa quando il progetto è guidato da **GitHub Copilot CLI**: cattura le
conversazioni Copilot nell'archivio locale, alla pari di Claude. Tutto on-machine. PowerShell (Windows).

> **Versione verificata:** GitHub Copilot CLI **1.0.63** (ricognizione 2026-06-22). Il formato
> `events.jsonl` è un dettaglio **interno** di Copilot (non un contratto pubblico): un loro
> aggiornamento può richiedere un adeguamento dell'adapter; il parsing è best-effort e degrada con
> warning, mai con un crash (NFR-001/006).

## 1. Abilitare (privacy-by-default: tutto off finché non lo accendi)

```powershell
# Strato 1: cattura della memoria (FEAT-001) — opt-in, default off
$env:SERTOR_MEMORY = "true"
# Strato 2: seleziona l'assistente da catturare → Copilot CLI
$env:SERTOR_MEMORY_ADAPTER = "copilot-cli"
```

- Con `SERTOR_MEMORY=false` (default) **nessun** file Copilot è letto, nessun adapter è costruito
  (RNF-3).
- Senza `SERTOR_MEMORY_ADAPTER` l'adapter resta `claude-code` (default invariato — gli ospiti Claude
  non cambiano comportamento).
- Un valore di adapter non riconosciuto → errore azionabile (exit 1) che nomina i valori ammessi
  (`claude-code`, `copilot-cli`).

## 2. (Opzionale) Override del percorso sorgente

```powershell
# Default: ~/.copilot/session-state. Override per ambienti non standard o per i test (Should).
$env:SERTOR_MEMORY_COPILOT_SESSION_DIR = "D:\percorso\custom\session-state"
```

Mirror esatto dell'override di Claude (`SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`).

## 3. Catturare

```powershell
# Cattura tutte le sessioni Copilot del progetto corrente (idempotente: ri-eseguire non duplica).
uv run sertor-rag memory archive
```

- L'adapter scopre le sessioni sotto `~/.copilot/session-state/<uuid>/`, associa ciascuna al progetto
  leggendo cwd/gitRoot dal suo `session.start`, e cattura **solo** quelle del progetto corrente. Le
  sessioni di altri progetti, o senza progetto determinabile, sono **escluse** (mai misattribuite).
- I turni catturati contengono **solo** il dialogo user/assistant; tool, diff, eventi di sistema/hook/
  permessi non diventano turni.
- Il contenuto passa per lo **scrub dei segreti** esistente prima di essere archiviato.
- **Su un ospite Copilot** la cattura scatta da sola a fine sessione tramite l'hook `SessionEnd` già
  depositato dall'installer (FEAT-009): con la memoria attiva e l'adapter Copilot, l'hook smette di
  essere inerte.

## 4. Recuperare (alla pari di Claude — nessun comando nuovo)

```powershell
# Full-text (FEAT-002)
uv run sertor-rag memory search "min-score"

# Semantica, se opt-in (FEAT-004)
$env:SERTOR_MEMORY_SEMANTIC = "true"
uv run sertor-rag memory search "scelte sul backend" --semantic

# Elenco/dettaglio per la distillazione (FEAT-003)
uv run sertor-rag memory list
uv run sertor-rag memory show <session-key>
```

Le conversazioni Copilot sono trattate **uniformemente** a quelle catturate da Claude: archivio,
ricerca e distillazione non distinguono la provenienza.

## 5. Sorgente assente / Copilot non installato

```powershell
# Copilot non installato o nessuna sessione → risultato vuoto + warning, MAI un errore.
uv run sertor-rag memory archive
# → 0 sessioni archiviate, warning "memory_capture_source_absent"
```

## 6. Privacy & cloud-sync (importante)

- **Local-first:** Sertor legge **solo** i file locali di Copilot (`~/.copilot/session-state/**`);
  **non** contatta il cloud session-sync di GitHub e **non** richiede rete.
- **Cloud-sync di Copilot (a monte, fuori dal controllo di Sertor):** GitHub Copilot CLI **può
  sincronizzare di default le sessioni sul cloud GitHub**. È un comportamento **di Copilot**,
  indipendente dall'archivio locale di Sertor: Sertor non vi interagisce e non lo modifica. Questa nota
  è l'unica forma di trasparenza prevista — **nessun avviso a runtime** (REQ-015).

## Verifica (test offline, RNF-4/5/7)

```powershell
# Adapter con una directory di sessione Copilot di fixture (events.jsonl + session.start),
# senza Copilot CLI installato né rete.
uv run pytest tests/unit/test_copilot_capture.py
uv run pytest -m "not cloud"
uv run ruff check .
```

> **Nota installer (debito tracciato, DA-CM-7):** il valore `SERTOR_MEMORY_ADAPTER=copilot-cli` (e
> l'override `SERTOR_MEMORY_COPILOT_SESSION_DIR`) va cablato nel template `.env`/asset di
> `sertor install` su host Copilot — **FEAT-009** (owner di `sertor install`). Finché non arriva, la
> capacità è usabile via libreria/CLI ma non «completa = installabile su un ospite Copilot».
