---
title: FEAT-018 — Portabilità OS degli hook e onestà sui surface Copilot inerti
type: experiment
tags: [feature, portabilità, hook, principio-xii, principio-x, debito-tecnico]
created: 2026-06-30
updated: 2026-06-30
sources: ["specs/078-portabilita-os-hook/", "requirements/debito-tecnico/portabilita-os-hook/requirements.md"]
---

# E10-FEAT-018 — Portabilità OS degli hook + Onestà Principio XII

**Feature:** Portabilità cross-OS degli hook distribuiti e dichiarazione esplicita dei surface inerti su Copilot.

**Stato:** ✅ Implementata (2026-06-30, branch `078-portabilita-os-hook`).

**Driver costituzionale:** [[principle-xii|Principio XII «Fail Loud, Fix the Cause»]] + [[principle-x|Principio X host-agnostico]].

## Problema e causa-radice

Tutti gli hook distribuiti sono **PowerShell** (`.ps1`). Su Claude, gli `settings.json` li cablano con `"shell": "powershell"` (NON `pwsh`). Su mac/Linux, l'eseguibile `powershell` **non esiste** (disponibile solo `pwsh` da PowerShell Core). Risultato: **gli hook non vengono mai eseguiti** e falliscono in silenzio (exit 0 dal client, nessun segnale).

Su Copilot CLI la stessa inerzia affligge due surface:
- **`memory-capture` SessionEnd:** non registra trascrizioni (adattatore Copilot non distribuito finché FEAT-009 memorie completamento fase-2) → hook esecuzione spenta, silenziosamente.
- **SessionStart:** Copilot CLI mostra il prompt come `type:"prompt"` interattivo; il client **riduce o non estrae il context** via il meccanismo di SessionStart (confermato da audit ISSUE-08, 2026-06-26). Non rotto come memory-capture, ma degradato.

Causa-radice del primo: il nome della shell negli `settings.json` Claude non è portabile. Limitazione tecnica: cambiare `powershell`→`pwsh` su Claude rompe Windows PowerShell 5.1.

## Decisione di scope (dall'utente)

**Guardia `pwsh` + gap dichiarato (NO gemello bash).**

- Hook rimangono **PowerShell-only** (convenzione «solo PowerShell» del repo).
- Rilevamento OS + availability di `pwsh` in **`sertor-install-kit/host_env.py`** (modulo puro, stdlib-only, mockabile offline).
- **`install_rag` e `install_wiki`** emettono una **nota azionabile** nel report d'install (`InstallReport.notes`), visibile all'utente, che nomina:
  - Il prerequisito mancante (`pwsh` assente).
  - L'azione: installare PowerShell Core + URL ufficiale.
  - Limite tecnico dichiarato: il wiring Claude portabile è un follow-up (non in ambito).
- Gating: **short-circuit se Windows** (nessun falso allarme su Windows PowerShell 5.1).

## Onestà sui surface inerti (audit corretto)

Audit iniziale confondeva l'inerzia:

1. **SessionStart Copilot CLI:** **NON inerte.** Il `prompt` funziona (hook nativo Copilot, tipo `"command"` lanciato in SessionStart); è **meno silenzioso** che su Claude (la direttiva di context-load è visibile all'utente come prompt). Questa è UX/gradazione, non rottura. *Cross-ref: FEAT-008 osservabilità per la visibilità UserExperience.*

2. **`memory-capture` SessionEnd su Copilot:** **Inerte per causa buona** — l'adattatore `CopilotCliTranscriptAdapter` non è distribuito finché **FEAT-009 memorie** non entra nella fase di completamento 2 (manopola `SERTOR_MEMORY_ADAPTER=copilot-cli` nei template `.env` installer). Quando FEAT-009 arriverà, il gap si risolverà per costruzione. Nota d'install: segnala il gap, zero dissimulazione.

**Onestà (Principio XII):** ogni inerzia è **segnalata esplicitamente nel report d'install** via `notes`; l'utente non scopre a sorpresa che nulla è accaduto.

## Implementazione (SpecKit completo)

### Modulo nuovo: `sertor-install-kit/host_env.py`

Puro (stdlib-only, `os`/`platform`/`shutil`):
- `is_windows(): bool` — True su Windows, False altrove.
- `pwsh_available(): bool` — True se `pwsh` esiste in PATH o `pwsh.exe` trovabile.
- `pwsh_unavailability_note(): str` — messaggio azionabile (URL + step installation).
- `PWSH_INSTALL_URL: str` — link ufficiale PowerShell Core.
- `maybe_note_pwsh(notes: list, assistant: AssistantId, is_rag: bool)` — helper che appende nota se `¬is_windows() AND ¬pwsh_available()`.

Testato offline (mock `os.system`, `shutil.which`).

### Wiring nei plan-builder

**`install_rag.py`** e **`install_wiki.py`** invocano `maybe_note_pwsh(report.notes, assistant, is_rag=True/False)` nel percorso di deposito artefatti. La nota entra in `InstallReport.notes` (lista di stringhe), primo uso reale del meccanismo.

Schema `install.report/1` rimane **byte-identico** (additivo: lista `notes` era già opzionale; default `[]` → nessuna nota per ambienti Windows).

### Guardie anti-regressione

1. **Tabella di verità guardia:** verifica che `pwsh_available()` ritorni `True` su Windows, `False` su non-Windows senza PowerShell Core (mock).
2. **Form e substring:** assert che la nota contiene «PowerShell Core» + URL + «prerequisito».
3. **Non-regressione Claude:** report di install su host Claude non deve contenere note `pwsh` (gating short-circuit ok).

## Esiti

- **SpecKit completo** (`specify`→`plan`→`tasks`→`implement` sul branch).
- **Constitution Check:** PASS 12/12 + missione senza deroghe.
- **Suite:** sertor **451** · kit **139** · root **1131 passed** (3 skip packaging, noti), ruff clean.
- **Codice:** zero touch a `sertor-core` (Principio XI).
- **Artefatti:** `requirements/debito-tecnico/portabilita-os-hook/requirements.md` (15 FR / 7 NFR / 5 CS).

## Follow-up dichiarato (NON in ambito)

- **Prova LIVE su ospite macOS/Linux:** visibilità della nota d'install quando `pwsh` assente (giudizio LLM, prova empirica necessaria).
- **Fix del wiring Claude portabile (candidato):** cambiare `"shell": "powershell"`→`"shell": "pwsh"` su Claude (rompe Windows PowerShell 5.1 oggi; richiede RESEARCH e DECISIONE di deprecazione). Promosso a feature futura (priorità Could).

## Crosslink

- **[[constitution]]** — Principio XII (Fail Loud, Fix the Cause) e Principio X (host-agnostico).
- **[[deterministic-vs-judgment]]** — Guardia è deterministica (offline, stdlib-only); nota d'install è giudizio (leggibilità).
- **[[sertor-install-kit]]** — Toolkit generico, riuso di `InstallReport.notes`.
- **[[sertor-installer]]** — Consumatore del wiring, deposita le note.
- **[[feat-019-fail-loud-hook-agent]]** — Gemella: fail-loud breadcrumb negli hook + fallback agent STOP; entrambe servono Principio XII.
- **[[feat-009-distribuzione-memoria-via-installer]]** — Debito memorie; la completezza della distribuzione chiude il gap `memory-capture` Copilot inerti.

