---
title: FEAT-008 — Cattura transcript su GitHub Copilot CLI (implementazione SpecKit)
type: experiment
tags: [feat-008, memoria, copilot-cli, transcript-capture, adapter, multi-assistente]
created: 2026-06-22
updated: 2026-06-22 (implementazione SpecKit completa, Constitution 12/12)
sources: ["requirements/memoria-conversazioni/cattura-copilot-cli/requirements.md", "specs/073-cattura-copilot-cli/**", "src/sertor_core/adapters/capture/copilot_cli.py", "src/sertor_core/config/settings.py", "src/sertor_core/composition.py", "tests/unit/adapters/test_copilot_capture.py"]
---

# FEAT-008 — Cattura transcript su GitHub Copilot CLI

**Epica:** [[memoria-conversazioni]] (Must priority, multi-assistente).
**Branch:** `073-cattura-copilot-cli`.
**Timeline:** ricognizione 2026-06-22; speckit→implementazione 2026-06-22; Constitution Check 12/12 PASS.

## Problema

L'MVP memoria (FEAT-001/002/035/004) rende la cattura e la ricerca episodica operative **solo su Claude Code**. L'adapter di cattura `TranscriptCaptureAdapter` (8ª porta) ha una sola implementazione concreta: `ClaudeCodeCaptureAdapter`. FEAT-009 ha già distribuito l'hook `SessionEnd` su GitHub Copilot CLI (nei `.github/` asset dell'installer), ma **rimane inerte** — non c'è un adapter che legga i transcript Copilot. Per la memoria conversazioni sia **veramente host-agnostica** e consegnabile a ospiti multi-assistente (es. progetto che usa sia Claude che Copilot), serve un **secondo adapter** dietro la stessa porta.

## Soluzione

Aggiungere un **adapter di cattura per GitHub Copilot CLI** (`CopilotCliCaptureAdapter`) che legge i transcript da `~/.copilot/session-state/` (il percorso di default dove Copilot CLI salva localmente le sessioni). Nessuna nuova porta, nessuna entità di dominio — **puro riuso** della porta `TranscriptCaptureAdapter` esistente e delle entità di cattura (`SessionRef`, `TranscriptTurn`, `TranscriptContent`). Il tier a valle (archivio, full-text FEAT-002, semantica FEAT-004, distillazione FEAT-003) rimane **invariato e host-agnostico**.

### Design (forche risolte empiricamente in dogfooding)

**(DA-CM-1) Sorgente:** transcript vivono in **`~/.copilot/session-state/<session-uuid>/events.jsonl`** (verifiato su doc GitHub ufficiale + filesystem locale, Copilot CLI 1.0.63). È l'**unica fonte** — niente session.db, niente workspace.yaml; l'associazione progetto viene dai metadati nel `session.start` event.

**(DA-CM-2) Turni e contenuto:** come Claude Code, solo turni `user.message` e `assistant.message`. Testo da `data.content` (NON `transformedContent`, ignorare i `toolRequests`). Reuso **totale** del parser JSONL da `claude-code.py` — formato identico.

**(DA-CM-3) Associazione progetto (asimmetrica, anti-misattribuzione):** il `session.start` contiene `cwd` (working directory) e `gitRoot` (antenato git). Una sessione appartiene al **progetto se:**
- `cwd` **è dentro-o-uguale** al progetto (path normalization POSIX, case-sensitive), **OPPURE**
- `gitRoot` **è antenato-o-uguale** del progetto (`Path(git_root).resolve()` è antenato).

Logica asimmetrica: se non soddisfa nessuno, **nessuna associazione** (sessione ignorata, non errore). Evita misattribuzioni quando si ha Copilot aperto in una cartella e il progetto è un sottodirectory; il rischio è accumulare transcript randomici — la guardia `_paths_match` lo previene.

**(DA-CM-4) Nome adapter e config:** `kind="copilot-cli"` in Settings; nuovi campi `copilot_session_dir` (env `SERTOR_MEMORY_COPILOT_SESSION_DIR`, default `~/.copilot/session-state`) e `memory_adapter` (enum → `"claude-code" | "copilot-cli"`; default `"claude-code"` per compatibilità backward). File nuovo `src/sertor_core/adapters/capture/copilot_cli.py`.

**(DA-CM-5) Privacy e cloud-sync:** Sertor legge **il locale** (`~/.copilot/session-state/`), NON accede al cloud-sync di Copilot (per documentazione Copilot, le sessioni sincronizzano su GitHub via `/chronicle`, ma Sertor non ha motivo di accedervi — privacy-by-design, niente cloud).

**(DA-CM-6) Legacy:** cartelle `~/.copilot/history-session-state/` (formato vecchio) ignorate; il parsing fallisce nel silenzio (file corrotti → `best-effort`, REQ-021 non-fatale).

## Implementazione

**Nuovo adapter:** `src/sertor_core/adapters/capture/copilot_cli.py` espone:
- `CopilotCliTranscriptAdapter(session_dir)` — implementa la porta `TranscriptCaptureAdapter`.
- Metodo `get_transcript(session_key: str) → TranscriptRef | None` — legge `events.jsonl`, esegue `_paths_match` per associazione, ritorna sessione se match, `None` altrimenti.
- Parsing **identico** a Claude Code fino alla granularità turno (formato JSONL copilot → stessi campi di claude-code).

**Estensioni architetturali:**

1. **Settings:** `config/settings.py`
   - Nuovo campo `copilot_session_dir: str | None = None` (env `SERTOR_MEMORY_COPILOT_SESSION_DIR`; default `None` → nessuna ricerca).
   - Campo `memory_adapter_kind: str = "claude-code"` (env `SERTOR_MEMORY_ADAPTER`; scelte `"claude-code" | "copilot-cli"`).

2. **Composition:** `composition.py`
   - Dispatch lazy `_VALID_MEMORY_ADAPTERS = ("claude-code", "copilot-cli")`.
   - Funzione `build_capture_adapter(settings) → TranscriptCaptureAdapter | None`:
     ```
     if not memory_enabled: return None
     match settings.memory_adapter_kind:
       case "claude-code": return ClaudeCodeCaptureAdapter(...)
       case "copilot-cli": return CopilotCliCaptureAdapter(settings.copilot_session_dir or default)
     ```

3. **Validazione:** `settings.validate_backend()` esteso — se `memory_adapter_kind` non in `_VALID_MEMORY_ADAPTERS`, `ConfigError` fail-loud che nomina le opzioni.

**Test:** 32 test in `tests/unit/adapters/test_copilot_capture.py`:
- Fixture: JSON sample `session.start`/`user.message`/`assistant.message` da doc GitHub.
- Parsing: identico a claude-code, nessuna divergenza formato.
- Associazione progetto (`_paths_match`): 8 casi (cwd dentro, cwd uguale, cwd fuori ma gitRoot antenato, entrambi vuoti/assenti, ecc.).
- Best-effort: file corrotto → skip + warning.

## Risultati

- **1039 test non-cloud passed:** +32 nuovi in `test_copilot_capture.py` + 8 estensioni settings/composition test.
- **ruff clean:** src + test.
- **Constitution Check:** 12/12 PASS (pre e post-design).
- **sertor-core invariato:** fuori dai 4 punti citati (adapter nuovo, settings, composition, test).

## Gap e debito dichiarato

**Debito di completamento (corollario installabile):** i cablaggio di `SERTOR_MEMORY_ADAPTER=copilot-cli` e `SERTOR_MEMORY_COPILOT_SESSION_DIR` **non sono ancora nei template `.env` dell'installer** (riguarda host Copilot CLI). Follow-up di **FEAT-009** (distribuzione memoria via installer) — quando l'installer sarà aggiornato con i template di Copilot CLI, anche questi due campi entreranno. Finché non arriva, un ospite Copilot che fa `sertor install rag` riceve l'hook `memory-capture.ps1` ma rimane configurato col default `claude-code` (adattatore inerte su Copilot).

**Principio XII (onestà):** la capacità di **cattura Copilot** è implementata e testata, ma non è pienamente "installabile" finché il cablaggio dell'installer non arriva. La memoria conversazioni rimane **incompleta per Copilot** come consumatore. Questo è un rischio R-1 dell'epica che si mitiga quando FEAT-009 phase-2 (Copilot installer) arriva.

## Lezioni codificate

1. **Adattatori host-specifici su porta host-agnostica:** la porta `TranscriptCaptureAdapter` rimane astratta; ogni assistente ha il suo adapter. Riuso del modello dati (`SessionRef`, `TranscriptTurn`), parsing locale, nessun nuovo stato globale.
2. **Determinismo offline:** parsificazione JSONL local-only, zero API cloud, zero sincronizzazione; la privacy è scontata dalla sorgente.
3. **Associazione asimmetrica:** anti-misattribuzione via guardia `_paths_match` (entrambe le condizioni verificate, nessun fallback implicito).

## Pagine collegate

- [[memoria-conversazioni]] — anchor concettuale (adapter aggiunto alla sezione cattura).
- [[transcript-capture-adapter-e-storage]] — porta 8ª + adapter concreti (sezione aggiornata con `CopilotCliCaptureAdapter`).
- [[copilot-cli-session-storage]] — fonte ricognizione storage GitHub (source page).
- [[assistant-targeting]] — multi-assistente, strategie di parità.
- [[sertor-con-copilot]] — posizionamento del supporto Copilot.
