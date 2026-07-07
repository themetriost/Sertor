# Tasks — enforcement deterministico della freschezza RAG (hook) (E10-FEAT-011)

**Branch**: `076-enforcement-freschezza-rag` · **Generato**: 2026-06-24
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/rag-health-state.md`](contracts/rag-health-state.md) ·
[`contracts/freshness-hook-wiring.md`](contracts/freshness-hook-wiring.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO (harness + distribuzione), nessun codice di core.**
> La feature è 100% asset hook + installer + governance. Vive in:
> - 2 script PowerShell host-facing (`rag-freshness.ps1`, `rag-freshness-start.ps1`);
> - 4 asset settings JSON bundlati (SessionEnd + SessionStart, per-assistente Claude);
> - estensione di `install_rag.py` (costanti + plan-builder + lifecycle + dispatch);
> - una riga additiva in `packages/sertor-install-kit/.../gitignore_append.py`;
> - annotazione di `CLAUDE.md` (reclassificazione step 5/8);
> - copia dogfood in `.claude/hooks/`;
> - test offline + guardia di sync bundlato↔dogfood.
>
> `sertor-core` è **INVARIATO** (Principio XI: l'hook *consuma* i vehicle `sertor-rag index`/`doctor`,
> mai importa la libreria). I comportamenti a indice fresco sono **identici** a oggi (FR-003/NFR-1).
>
> **Rischi noti da coprire (calibra l'ordine):**
> - **R-1 (CRITICO):** il formato nativo Copilot per l'hook SessionEnd/SessionStart deve essere
>   **generato** via `render_copilot_hooks([HookEntrySpec(...)])` (mai asset JSON in formato Claude
>   — lezione FEAT-011/049). Va fatto **prima** dei test di parità.
> - **R-2:** l'hook `rag-freshness.ps1` deve uscire 0 in **qualsiasi** scenario (incluso errore di
>   `sertor-rag index`/`doctor`) — `try/catch` globale come `memory-capture.ps1` (FR-017).
> - **R-3:** la guardia di sync bundlato↔dogfood è **nuova** (non coperta da `test_assets_sync.py`
>   che segue solo il subtree `claude/` — research D-0e). Va aggiunta espressamente.
> - **R-4:** `RUNTIME_IGNORES` nel kit **non copre** oggi `.sertor/.rag-health.json` (research D-1
>   finding). Va esteso prima o in parallelo agli script hook.
>
> **Strategia MVP/incrementale.**
> - **Setup** (TASK-S01..S02): asset settings JSON bundlati + sync `uv run python -m sertor_installer.sync`.
>   Prerequisiti zero. Bloccanti per il wiring installer.
> - **Fondazionale A — Script SessionEnd** (TASK-F01): `rag-freshness.ps1` (re-index + doctor +
>   persistenza stato). Indipendente da F02 [P]; bloccante per il wiring SessionEnd.
> - **Fondazionale B — Script SessionStart Claude** (TASK-F02): `rag-freshness-start.ps1`
>   (ripesca + induce). Indipendente da F01 [P]; bloccante per il wiring SessionStart.
> - **Fondazionale C — Kit RUNTIME_IGNORES** (TASK-F03): estensione additiva della costante nel kit.
>   Indipendente [P]; bloccante per il test di copertura kit.
> - **Fondazionale D — Dogfood `.claude/`** (TASK-F04): copia degli script in `.claude/hooks/` +
>   voci `.claude/settings.json`. Dipende da F01+F02 [P rispetto a F03].
> - **Storia US1..US6 — Installer** (TASK-US1-01..US6-01): wiring in `install_rag.py` (costanti,
>   plan-builder, dispatch Copilot, lifecycle, upgrade). Dipende da F01+F02+S01. Sequenziale
>   internamente (dipendenze a cascata); il dispatch Copilot può partire in parallelo con le costanti.
> - **Storia US7 — Governance** (TASK-US7-01): annotazione `CLAUDE.md` step 5/8. Indipendente [P].
> - **Storia US8..US9 — Test** (TASK-US8-01..US9-01): test offline (deposito, parità, lifecycle,
>   guardia sync, promozione Out-of-Scope). Dipende da US1-01..US6-01.
> - **Polish/cross-cutting** (TASK-P01..P03): suite verde, lint, additività, sync finale.
>
> L'ordine di priorità segue: script hook (US1/US2/US4/US6, P1 Must) → installer (US8, P1 Must) →
> dogfood e governance (US7, P1 Must) → test/guardia (US8/US9) → Out-of-Scope (US5) → polish.

---

## Fase 0 — Setup: asset JSON bundlati (2 task)

> Prerequisiti: nessuno. Crea i file di settings JSON statici per le voci SessionEnd/SessionStart
> Claude nel bundle `sertor`. Bloccanti per il wiring installer (TASK-US1-01). Parallelizzabili [P].

### TASK-S01 [P] — Crea `assets/rag/settings.rag-freshness.json` (voce SessionEnd Claude)

**File**: `packages/sertor/src/sertor_installer/assets/rag/settings.rag-freshness.json` (NUOVO)
→ dipende da: nessuno

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/settings.rag-freshness.json`
      con il payload di merge della voce `SessionEnd` per Claude nel **formato annidato nativo**
      (contratto `contracts/freshness-hook-wiring.md` §1):
      ```json
      { "hooks": { "SessionEnd": [ { "hooks": [ {
        "type": "command", "shell": "powershell", "timeout": 15,
        "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/rag-freshness.ps1')"
      } ] } ] } }
      ```
- [x] Verifica che il formato sia **annidato** (forma `{hooks:{SessionEnd:[{hooks:[...]}]}}`) — lo
      stesso usato da `settings.rag-usage.json` e `settings.memory-capture.json` (gemello).
- [x] Verifica che il campo `timeout` (non `timeoutSec`) sia usato per Claude (il `timeoutSec` è
      il formato Copilot — W1 del contratto).
- [x] Verifica che il `command` costruisca il path in modo **host-agnostico**: `$env:CLAUDE_PROJECT_DIR`
      → fallback `'.'` (pattern `memory-capture.ps1` — research D-0a).

### TASK-S02 [P] — Crea `assets/rag/settings.rag-freshness-start.json` (voce SessionStart Claude)

**File**: `packages/sertor/src/sertor_installer/assets/rag/settings.rag-freshness-start.json` (NUOVO)
→ dipende da: nessuno

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/settings.rag-freshness-start.json`
      con il payload di merge della voce `SessionStart` per Claude (contratto §1):
      ```json
      { "hooks": { "SessionStart": [ { "hooks": [ {
        "type": "command", "shell": "powershell", "timeout": 10,
        "statusMessage": "Verifico la freschezza del RAG",
        "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/rag-freshness-start.ps1') -Assistant claude"
      } ] } ] } }
      ```
- [x] Verifica che `statusMessage` sia presente (feedback user-visible all'avvio, coerente con il
      pattern Claude per gli hook informativi).
- [x] Verifica il timeout 10 (s) — inferiore a quello SessionEnd (15 s) perché il SessionStart è
      solo lettura del file di stato, non re-index (NFR-2).
- [x] Verifica che il `command` passi `-Assistant claude` esplicitamente allo script (lo script usa
      il parametro per adattare il messaggio emesso — data-model §2b).

---

## Fase 1 — Fondazionale: script hook, kit e dogfood (4 task)

> Prerequisiti: nessuno per F01/F02/F03 (parallelizzabili tra loro [P]). F04 dipende da F01+F02.
> Bloccanti per la fase installer (TASK-US1-01..US6-01).

### TASK-F01 [P] — Crea `assets/rag/hooks/rag-freshness.ps1` (SessionEnd: re-index + doctor + persistenza)

**File**: `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1` (NUOVO)
→ dipende da: nessuno

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1`
      seguendo la **disciplina di `memory-capture.ps1`** (research D-0a): wrapper `SessionEnd` thin,
      `try/catch` globale, exit 0 **sempre** (FR-017, R-2), payload JSON tollerante da stdin,
      root da `$env:CLAUDE_PROJECT_DIR` → `hook.cwd` → `'.'`.
- [x] Implementa la **logica di orchestrazione** (NON change-detection — FR-002):
      1. `uv run sertor-rag index .` **incondizionato** (skip-quando-nulla-cambia delegato al core,
         FR-001/002/003; Principio XI — mai importare `sertor_core`).
      2. `uv run sertor-rag doctor --json` → cattura stdout e exit code (FR-005).
      3. Deriva `verdict`: `degraded` se exit code ≠ 0 **oppure** almeno un'area in `fail`/`warn`
         nel JSON; `healthy` altrimenti (FR-006).
      4. Scrive `.sertor/.rag-health.json` nel path dell'host (FR-008/010/011):
         - `degraded`: `verdict`, `timestamp` ISO-8601 UTC, `reason` (area/causa), `areas`,
           `exit_code` (schema `rag.health/1`, contratto `contracts/rag-health-state.md`); emette
           messaggio prominente su stdout/stderr (FR-009).
         - `healthy`: riscrive il file con `verdict: "healthy"` e campi minimali (INV-1, FR-010 —
           **non cancella** il file, così il segnale d'avvio legge `healthy` e fa no-op).
- [x] Verifica che **nessun LLM sia invocato** (Principio D↔N, NFR-5): l'hook chiama solo
      `sertor-rag` via `uv run`, mai `openai`/`anthropic`/modelli.
- [x] Verifica che lo script sia **host-agnostico** (NFR-4): nessun path hardcodato a `Sertor`;
      funziona su un ospite qualsiasi con la capacità `rag` installata.
- [x] Verifica che nessun segreto finisca nel file di stato (NFR-3/INV-2): `reason` proviene da
      `doctor --json` (già scrubbed dai vehicle), mai dal contenuto di `.sertor/.env`.
- [x] Verifica `exit 0` **anche se `sertor-rag index`/`doctor` falliscono** (R-2/FR-017):
      il `try/catch` assorbe ogni eccezione PowerShell; il file di stato NON viene scritto in caso
      di errore interno catastrofico (silenzio onesto > dati corrotti).

### TASK-F02 [P] — Crea `assets/rag/hooks/rag-freshness-start.ps1` (SessionStart Claude: ripesca + induce)

**File**: `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness-start.ps1` (NUOVO)
→ dipende da: nessuno

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness-start.ps1`
      con parametro `-Assistant` (valore atteso: `claude`; estendibile al futuro senza breaking change).
- [x] Implementa la **logica di lettura e induzione** (research D-2 — D↔N):
      1. Legge `.sertor/.rag-health.json` nel path dell'host (`$env:CLAUDE_PROJECT_DIR` → `'.'`).
      2. Se il file **non esiste** o `verdict == "healthy"` → **no-op** (exit 0, nessun output):
         NFR-6 idempotenza; nessun inducement perpetuo (FR-015, INV-1).
      3. Se `verdict == "degraded"` → emette su **stdout** la direttiva d'induzione (il messaggio
         che Claude riceve come contesto SessionStart — FR-013): include `reason` e l'istruzione
         «esegui `sertor-rag index .` e/o riconnetti il server MCP prima di procedere col lavoro»
         (FR-013, US3-AC1).
- [x] Verifica il **confine D↔N** (FR-014): lo script **NON** lancia `sertor-rag index` da sé
      (sarebbe giudizio + costo bloccante all'avvio) — emette solo la direttiva, l'agente decide
      ed esegue. Nessun LLM invocato (NFR-5).
- [x] Verifica che exit sia **sempre 0** (FR-017): il `try/catch` assorbe file mancante, JSON
      malformato, qualsiasi errore di lettura.
- [x] Verifica che lo script sia **host-agnostico** (NFR-4): nessun path hardcodato a `Sertor`.

### TASK-F03 [P] — Estendi `RUNTIME_IGNORES` nel kit con `.sertor/.rag-health.json`

**File**: `packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py` (MODIFICA)
→ dipende da: nessuno

- [x] Aggiungi `".sertor/.rag-health.json"` alla tupla `RUNTIME_IGNORES` (riga 14):
      ```python
      RUNTIME_IGNORES = (
          ".sertor/.venv/",
          ".sertor/.index*",
          ".sertor/.env",
          ".sertor/.rag-health.json",    # E10-FEAT-011: file di stato salute RAG
      )
      ```
      (additivo, non-breaking — research D-1 / data-model §1 INV-3; unica fonte di verità per il
      `.gitignore` dell'ospite).
- [x] Verifica che il test esistente `packages/sertor-install-kit/tests/unit/test_gitignore_append.py`
      (riga `:19` circa: `assert all(entry in text for entry in RUNTIME_IGNORES)`) sia ancora verde
      dopo l'aggiunta (la nuova voce appare nel `.gitignore` generato).
- [x] Verifica che `append_gitignore` (con default `RUNTIME_IGNORES`) scriva la nuova riga nel
      `.gitignore` host quando chiamato dall'installer.
- [x] Verifica che `remove_gitignore_lines` rimuova anche la nuova voce su uninstall (la funzione
      itera su `RUNTIME_IGNORES` — comportamento ereditato, nessuna modifica aggiuntiva richiesta).

### TASK-F04 — Aggiorna dogfood `.claude/`: copia script + voci settings

**File**: `.claude/hooks/rag-freshness.ps1` (NUOVO), `.claude/hooks/rag-freshness-start.ps1` (NUOVO),
         `.claude/settings.json` (MODIFICA)
→ dipende da: TASK-F01, TASK-F02 (script sorgente devono esistere)

- [x] Copia `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1` →
      `.claude/hooks/rag-freshness.ps1` (**byte-identico** — la guardia di sync TASK-US9-01 la
      verifica; FR-024).
- [x] Copia `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness-start.ps1` →
      `.claude/hooks/rag-freshness-start.ps1` (**byte-identico**; FR-024).
- [x] Aggiungi la voce `SessionEnd` per `rag-freshness` in `.claude/settings.json` via **merge
      dedup** (lo stesso payload di `assets/rag/settings.rag-freshness.json`): la nuova voce va
      accanto a quella di `memory-capture` e `sertor-rag-usage-check` **senza toccarle** (FR-016/018,
      research D-3).
- [x] Aggiungi la voce `SessionStart` per `rag-freshness-start` in `.claude/settings.json` (payload
      di `assets/rag/settings.rag-freshness-start.json`): va accanto alla voce `wiki-session-start`
      esistente, **senza toccarla** (FR-016).
- [x] Verifica che `.claude/settings.json` contenga **entrambe** le nuove voci dopo il merge e che
      le voci pre-esistenti (`wiki`, `memory-capture`, `sertor-rag-usage-check`) siano **intatte**.
- [x] Verifica che `.sertor/.rag-health.json` sia presente in `.gitignore` (propagato da TASK-F03 +
      `append_gitignore` — oppure aggiunto manualmente se il `.gitignore` dogfood non è gestito
      dall'installer su questo host).

---

## Fase 2 — Storia US1-US6: wiring installer `install_rag.py` (5 task)

> Prerequisiti: TASK-F01, TASK-F02 (script sorgente bundlati), TASK-S01, TASK-S02 (settings JSON).
> I task di questa fase hanno dipendenze interne: W1 e W2 [P] tra loro; W3 dipende da W1+W2;
> W4 dipende da W3; W5 dipende da W4.

### TASK-US1-01 [P] — W1: costanti e sentinel Copilot per l'hook SessionEnd freschezza

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-S01, TASK-F01

**Mappa FR**: FR-001/002/004/016/017/020/021/022 · US1/US2/US4/US6/US8

- [x] Aggiungi le costanti per l'hook `SessionEnd` rag-freshness, **dopo** il blocco
      `_COPILOT_MEMORY_WIRING_SENTINEL` (research D-0b, data-model §3):
      ```python
      # RAG freshness hook – SessionEnd (E10-FEAT-011)
      _FRESHNESS_HOOK_ASSET   = "rag/hooks/rag-freshness.ps1"
      _FRESHNESS_HOOK_TARGET  = ".claude/hooks/rag-freshness.ps1"
      _FRESHNESS_HOOK_TARGET_COPILOT = ".github/hooks/rag-freshness.ps1"
      _FRESHNESS_SETTINGS     = "rag/settings.rag-freshness.json"
      _COPILOT_FRESHNESS_END_WIRING_SENTINEL = "(generated: copilot freshness-end hooks)"
      ```
- [x] Aggiungi la factory `_copilot_freshness_end_specs() -> list[HookEntrySpec]` (gemella di
      `_copilot_memory_hook_specs`) che genera la voce SessionEnd **nativa Copilot** (formato piatto
      `version:1`/`timeoutSec` — contratto §2, R-1):
      ```python
      def _copilot_freshness_end_specs() -> list[HookEntrySpec]:
          return [HookEntrySpec(
              "SessionEnd", "command",
              f"{_PWSH} {_FRESHNESS_HOOK_TARGET_COPILOT}", 15,
          )]
      ```
- [x] Verifica che `HookEntrySpec` sia già importato (riga `:60` circa di `install_rag.py`) —
      nessun import aggiuntivo richiesto.
- [x] Verifica (su carta) che `render_copilot_hooks([HookEntrySpec("SessionEnd","command",…,15)])` →
      formato `{"version":1,"hooks":{"SessionEnd":[{"type":"command","command":"…","timeoutSec":15}]}}`
      (piatto, mai `shell`/`statusMessage`/`timeout` — W1 del contratto, R-1).

### TASK-US2-01 [P] — W2: costanti e sentinel Copilot per il segnale SessionStart freschezza

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-S02, TASK-F02

**Mappa FR**: FR-012/013/014/016/020/021/022 · US3/US8

- [x] Aggiungi le costanti per il segnale `SessionStart` rag-freshness, **dopo** le costanti W1:
      ```python
      # RAG freshness signal – SessionStart (E10-FEAT-011)
      _FRESHNESS_START_ASSET  = "rag/hooks/rag-freshness-start.ps1"
      _FRESHNESS_START_TARGET = ".claude/hooks/rag-freshness-start.ps1"
      _FRESHNESS_START_SETTINGS = "rag/settings.rag-freshness-start.json"
      _COPILOT_FRESHNESS_START_WIRING_SENTINEL = "(generated: copilot freshness-start hooks)"
      ```
- [x] Aggiungi la factory `_copilot_freshness_start_specs() -> list[HookEntrySpec]` che genera la
      voce SessionStart **nativa Copilot** come **prompt statico** (nessuno script — A-005, research
      D-2, contratto §2, W5):
      ```python
      def _copilot_freshness_start_specs() -> list[HookEntrySpec]:
          return [HookEntrySpec(
              "SessionStart", "prompt",
              "All'avvio: leggi .sertor/.rag-health.json. "
              "Se verdict=degraded, rendi evidente il degrado (reason) e induci la correzione "
              "— esegui `sertor-rag index .` e/o riconnetti il server MCP — "
              "PRIMA di procedere col lavoro. Se healthy/assente, procedi.",
              10,
          )]
      ```
- [x] Verifica che la factory **non depositi** uno script `rag-freshness-start.ps1` su Copilot
      (W5 del contratto: SessionStart Copilot = prompt statico). Lo script `.ps1` è un artefatto
      **solo Claude** (data-model §4 nota artefatto (b)).
- [x] Verifica (su carta) che `render_copilot_hooks([HookEntrySpec("SessionStart","prompt",…,10)])` →
      `{"version":1,"hooks":{"SessionStart":[{"type":"prompt","prompt":"…","timeoutSec":10}]}}`.

### TASK-US3-01 — W3: estendi `build_rag_plan` con i 4 nuovi artefatti

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-US1-01, TASK-US2-01

**Mappa FR**: FR-020/021/022 · US8-AC1

- [x] Individua la sezione di `build_rag_plan` che emette gli artefatti hook esistenti (blocco
      `memory-capture` FILE + SETTINGS_MERGE, circa righe `:317-340`).
- [x] Aggiungi **in coda** al blocco hook i 4 nuovi artefatti rag-freshness (data-model §4):
      ```python
      # RAG freshness hook – SessionEnd (E10-FEAT-011)
      plan.append(Artifact(
          ArtifactKind.FILE,
          _FRESHNESS_HOOK_ASSET,
          _FRESHNESS_HOOK_TARGET if not is_copilot else _FRESHNESS_HOOK_TARGET_COPILOT,
          WriteStrategy.CREATE_IF_ABSENT,
      ))
      plan.append(Artifact(
          ArtifactKind.SETTINGS_MERGE,
          _FRESHNESS_SETTINGS if not is_copilot else _COPILOT_FRESHNESS_END_WIRING_SENTINEL,
          _SETTINGS_TARGET if not is_copilot else _COPILOT_HOOK_WIRING,
          WriteStrategy.MERGE_DEDUP,
      ))
      # RAG freshness signal – SessionStart (E10-FEAT-011)
      if not is_copilot:
          plan.append(Artifact(
              ArtifactKind.FILE,
              _FRESHNESS_START_ASSET,
              _FRESHNESS_START_TARGET,
              WriteStrategy.CREATE_IF_ABSENT,
          ))
      plan.append(Artifact(
          ArtifactKind.SETTINGS_MERGE,
          _FRESHNESS_START_SETTINGS if not is_copilot else _COPILOT_FRESHNESS_START_WIRING_SENTINEL,
          _SETTINGS_TARGET if not is_copilot else _COPILOT_HOOK_WIRING,
          WriteStrategy.MERGE_DEDUP,
      ))
      ```
- [x] Verifica che lo script `rag-freshness-start.ps1` sia emesso **solo per Claude** (`not is_copilot`),
      in coerenza con W5 del contratto e data-model §4 nota artefatto (b).
- [x] Verifica che i target siano coerenti con i path di `sertor_owned_paths` (da aggiornare in
      TASK-US4-01) — `plan ⊆ owned` (test di copertura esistente).
- [x] Verifica additività: gli artefatti pre-esistenti (`memory-capture`, `rag-usage`, skill, agente)
      **non** sono rimossi o spostati; i nuovi vengono aggiunti in coda (non-regressione SC-010).

### TASK-US4-01 — W4: estendi `_rag_hook_fragment` con i 2 nuovi sentinel Copilot

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-US3-01

**Mappa FR**: FR-021 · US8-AC2

- [x] Individua la funzione `_rag_hook_fragment` (circa riga `:424`) che fa dispatch sui sentinel
      Copilot generati. Oggi gestisce `_COPILOT_RAG_WIRING_SENTINEL` e
      `_COPILOT_MEMORY_WIRING_SENTINEL`.
- [x] Estendi il dispatch con i 2 nuovi sentinel (art-aware, riuso `render_copilot_hooks`):
      ```python
      elif art.source == _COPILOT_FRESHNESS_END_WIRING_SENTINEL:
          return render_copilot_hooks(_copilot_freshness_end_specs())
      elif art.source == _COPILOT_FRESHNESS_START_WIRING_SENTINEL:
          return render_copilot_hooks(_copilot_freshness_start_specs())
      ```
- [x] Verifica che `render_copilot_hooks` sia già importato in `install_rag.py` (riga `:60`):
      `from sertor_installer.surfaces import HookEntrySpec, render_copilot_hooks, render_custom_agent`.
      Nessun import aggiuntivo richiesto.
- [x] Verifica (su carta) che il risultante JSON Copilot per `SessionEnd` sia nel formato piatto
      nativo (R-1/W1): `{"version":1,"hooks":{"SessionEnd":[{"type":"command","command":"…",
      "timeoutSec":15}]}}` — mai il formato Claude annidato.
- [x] Verifica (su carta) che il risultante JSON Copilot per `SessionStart` sia un prompt statico
      (W5): `{"version":1,"hooks":{"SessionStart":[{"type":"prompt","prompt":"…","timeoutSec":10}]}}`.

### TASK-US5-01 — W5: estendi `sertor_owned_paths` + lifecycle uninstall/upgrade

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-US4-01

**Mappa FR**: FR-022/023 · US9-AC1

- [x] Individua `sertor_owned_paths` (circa riga `:510`). Oggi gestisce `owned_files` per
      `memory-capture.ps1` (Claude: `_MEMORY_HOOK_TARGET`, Copilot: `_MEMORY_HOOK_TARGET_COPILOT`)
      e per `sertor-rag-usage-check.ps1`.
- [x] Aggiungi ai **`owned_files`** i nuovi path (da rimuovere su uninstall / da aggiornare su
      upgrade — FR-023):
      - Claude: `_FRESHNESS_HOOK_TARGET` + `_FRESHNESS_START_TARGET`.
      - Copilot: `_FRESHNESS_HOOK_TARGET_COPILOT` (solo SessionEnd script — il SessionStart Copilot
        è un prompt generato, nessun file `.ps1` depositato — W5 del contratto).
- [x] Verifica che i `shared_edits` coprano le voci `SessionEnd`/`SessionStart` rag-freshness nello
      stesso settings file degli altri hook (`_SETTINGS_TARGET` per Claude,
      `_COPILOT_HOOK_WIRING` per Copilot): le voci atterrano nel file già dichiarato come
      `SharedEdit` — già coperte dallo `SharedEdit(settings_target, SETTINGS, …)` esistente.
- [x] Verifica che l'**uninstall** sia già art-aware (FILE→`remove_path`; SETTINGS_MERGE→
      `remove_settings_entries` con `delete_if_empty` per `sertor-hooks.json` Copilot):
      il dispatch esistente `_apply_rag_lifecycle` gestisce i nuovi artefatti senza logica aggiuntiva.
      Conferma guardando circa riga `:554-607`.
- [x] Verifica che l'**upgrade** aggiorna i nuovi script FILE via `update_file_if_changed`
      (già gestito dal dispatch art-aware) e aggiorna le voci SETTINGS_MERGE.
- [x] Verifica che il test di copertura `plan ⊆ owned` resti verde: ogni nuovo `target_rel`
      degli artefatti aggiunti in TASK-US3-01 compare negli `owned_files` o `shared_edits`.

---

## Fase 3 — Storia US7: reclassificazione governance `CLAUDE.md` (1 task)

> Prerequisito: nessuno (indipendente [P] — modifica di testo puro, non dipende dall'implementazione).
> Può essere eseguito in qualsiasi momento.

### TASK-US7-01 [P] — Annota gli step 5 e 8 del rituale nel `CLAUDE.md` come «enforced via hook»

**File**: `CLAUDE.md` (MODIFICA — radice repo)
→ dipende da: nessuno

**Mappa FR**: FR-019 · US7-AC1/AC2/AC3

- [x] Individua lo **step 5** del *Rituale di step* nel `CLAUDE.md` (sezione «Re-index del corpus
      toccato» — circa riga `:360` a partire dal confine di sessione). Aggiungi all'inizio del
      paragrafo l'annotazione:
      ```
      > **ENFORCED VIA HOOK (E10-FEAT-011):** il re-index a fine sessione è ora un hook
      > deterministico (`rag-freshness.ps1`, `SessionEnd`). Confine D↔N: l'hook re-indicizza e
      > verifica (meccanico); l'agente esegue la correzione indotta all'avvio se lo stato è degradato
      > (giudizio). Il testo seguente descrive ancora la rete agente (valida finché il buco
      > filtro-metadata `where` non è chiuso da E12 e finché l'hook non è su tutti gli ospiti).
      ```
- [x] Individua lo **step 8** del rituale (sezione «Smoke test del RAG di dogfooding» — circa
      riga `:400`). Aggiungi analoga annotazione:
      ```
      > **ENFORCED VIA HOOK (E10-FEAT-011):** la verifica di salute (`sertor-rag doctor`) è ora
      > parte dell'hook `rag-freshness.ps1` (`SessionEnd`). Il buco del filtro metadata `where`
      > (guasto storico 2026-06-19) non è coperto dall'hook (promosso a E12-FEAT-011 usabilità)
      > → il rituale punto 8 dell'agente resta la rete per quel buco specifico.
      ```
- [x] Verifica che le annotazioni documentino la **sfumatura D↔N** (FR-019, research D-4):
      l'hook re-indicizza e verifica (meccanico), l'agente esegue la correzione indotta (giudizio).
- [x] Verifica che i due passi **non vengano rimossi** dal `CLAUDE.md` (research D-4: si
      riclassificano, non si eliminano — restano la rete per il buco `where` e per ospiti non ancora
      aggiornati).
- [x] Verifica che `CLAUDE.md` sia ancora well-formed dopo la modifica (nessun heading rotto,
      nessun markdown malformato).

---

## Fase 4 — Storie US8/US9: test offline e guardia di sync (4 task)

> Prerequisiti: TASK-US5-01 (wiring completo), TASK-F01/F02 (script sorgente).
> TASK-US8-01 [P] e TASK-US8-02 [P] sono parallelizzabili; TASK-US8-03 dipende da entrambi;
> TASK-US9-01 [P] è indipendente dagli altri tre (file sorgente, non plan-builder).

### TASK-US8-01 [P] — Test deposito Claude: script + voci + lifecycle (US8, P1 Must)

**File**: `packages/sertor/tests/test_install_rag_freshness.py` (NUOVO)
→ dipende da: TASK-US5-01

**Mappa FR**: FR-016/020/022/023 · US8-AC1/US9-AC1 · CS-4

- [x] Crea il file `packages/sertor/tests/test_install_rag_freshness.py` (gemello di
      `test_install_rag_memory.py` — stessa struttura con `FakeCommandRunner`).
- [x] `test_freshness_hook_deposited_claude`: via plan-builder offline (`build_rag_plan` con
      `assistant=CLAUDE`), verifica che `.claude/hooks/rag-freshness.ps1` sia un target FILE del
      piano (FR-020/US8-AC1).
- [x] `test_freshness_start_deposited_claude`: verifica che `.claude/hooks/rag-freshness-start.ps1`
      sia un target FILE del piano Claude (FR-020/US8-AC1; solo Claude, non Copilot — W5).
- [x] `test_freshness_session_end_settings_claude`: verifica che `.claude/settings.json` sia un
      target SETTINGS_MERGE del piano Claude con la voce `SessionEnd` rag-freshness (FR-020/US8-AC1).
- [x] `test_freshness_session_start_settings_claude`: verifica che `.claude/settings.json` sia un
      target SETTINGS_MERGE del piano Claude con la voce `SessionStart` rag-freshness (FR-020/US8-AC1).
- [x] `test_freshness_isolated_from_memory_capture`: verifica che il piano contenga ENTRAMBE le
      voci hook `memory-capture` E `rag-freshness` su `SessionEnd` come **artefatti distinti**
      (FR-016 — non fusi in uno script unico).
- [x] Test lifecycle — uninstall: dopo `build_rag_plan(op=UNINSTALL, assistant=CLAUDE)`, i path
      `_FRESHNESS_HOOK_TARGET` e `_FRESHNESS_START_TARGET` compaiono negli `owned_files` di
      `sertor_owned_paths` (verifica che siano rimossi su uninstall — FR-023/US9-AC1).
- [x] Test lifecycle — upgrade: lo script `rag-freshness.ps1` è aggiornato su upgrade
      (`update_file_if_changed` nel dispatch lifecycle — FR-023).
- [x] Tutti `not cloud`, offline (nessun `uv`/ospite reale — NFR-1).

### TASK-US8-02 [P] — Test deposito Copilot: formato nativo + parità (US8, P1 Must)

**File**: `packages/sertor/tests/test_install_rag_freshness.py` (MODIFICA — continua dal task precedente)
→ dipende da: TASK-US5-01

**Mappa FR**: FR-021 · US8-AC2 · CS-4

- [x] `test_freshness_hook_deposited_copilot`: via `build_rag_plan(assistant=COPILOT_CLI)`, verifica
      che `.github/hooks/rag-freshness.ps1` sia un target FILE del piano (FR-021/US8-AC2).
- [x] `test_freshness_start_NOT_deposited_copilot`: verifica che `.github/hooks/rag-freshness-start.ps1`
      **NON** sia un target del piano Copilot (W5 — il SessionStart Copilot è un prompt statico,
      mai uno script depositato; US8-AC2).
- [x] `test_freshness_end_wiring_copilot_native_format`: il contenuto del SETTINGS_MERGE per
      `SessionEnd` Copilot (da `render_copilot_hooks`) ha formato piatto nativo:
      `{"version":1,"hooks":{"SessionEnd":[{"type":"command","command":"…","timeoutSec":15}]}}` —
      mai `shell`/`statusMessage`/`timeout` (R-1/W1 contratto).
- [x] `test_freshness_start_wiring_copilot_native_format`: il contenuto SETTINGS_MERGE per
      `SessionStart` Copilot ha `{"type":"prompt","prompt":"…","timeoutSec":10}` (W5/R-1).
- [x] `test_freshness_no_claude_format_on_copilot`: verifica che nessun artefatto Copilot contenga
      i campi Claude (`shell`, `statusMessage`, `timeout` senza `Sec`) nel suo contenuto serializzato
      (parità — lezione FEAT-011/049, FR-021).
- [x] Tutti `not cloud`, offline.

### TASK-US8-03 — Guardia di sync bundlato↔dogfood (US9, P2 Should) (R-3)

**File**: `tests/unit/test_assets_sync.py` (MODIFICA — o nuova sezione) ·
         oppure `packages/sertor/tests/test_install_rag_freshness.py` (aggiunta)
→ dipende da: TASK-F01, TASK-F02, TASK-F04

**Mappa FR**: FR-024 · US9-AC2/AC3 · CS-4

- [x] Aggiungi `test_rag_freshness_dogfood_sync` che confronta **byte-per-byte**:
      - `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1` vs
        `.claude/hooks/rag-freshness.ps1` → identici (R-3/FR-024).
      - `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness-start.ps1` vs
        `.claude/hooks/rag-freshness-start.ps1` → identici (R-3/FR-024).
- [x] Modellare il test su `test_assets_sync.py:31-41` (forma della guardia esistente):
      ```python
      def test_rag_freshness_dogfood_sync(repo_root):
          for name in ("rag-freshness.ps1", "rag-freshness-start.ps1"):
              bundled = repo_root / "packages/sertor/src/sertor_installer/assets/rag/hooks" / name
              dogfood = repo_root / ".claude/hooks" / name
              assert bundled.read_bytes() == dogfood.read_bytes(), \
                  f"Drift: {name} bundlato ≠ dogfood .claude/hooks/{name}"
      ```
- [x] Verifica che il test **fallisca** se si introduce un drift manuale in uno dei due file
      (controllo di sanity della guardia — US9-AC3).
- [x] Verifica che `test_assets_sync.py` (guardia `claude/` esistente) **non** copra già gli hook
      rag (research D-0e: il subtree `claude/` non include `assets/rag/hooks/`) — nessuna
      duplicazione.

### TASK-US9-01 [P] — Promozione Out-of-Scope a backlog E12 (US5, P2 Should)

**File**: `requirements/usabilita/epic.md` (MODIFICA)
→ dipende da: nessuno (può partire in qualsiasi fase)

**Mappa FR**: FR-007 · US5-AC2 · spec §Tracciamento dello scope

- [x] Apri `requirements/usabilita/epic.md` e individua la sezione §8 del backlog (o la fine della
      lista FEAT esistente — la spec indica FEAT-001..FEAT-010 già presenti).
- [x] Aggiungi la **nuova voce FEAT-011** dell'epica usabilità (E12):
      ```
      | FEAT-011 | Estensione `doctor` con check-query metadata-filtered (`where`) | Should | da decomporre |
      ```
      Descrizione: estende `sertor-rag doctor` con un *check-query* che esercita il path del filtro
      metadata (`search_code`/`search_docs` con `where`) — il buco storico del 2026-06-19 non coperto
      dall'hook di freschezza; buco dichiarato in E10-FEAT-011 spec §Fuori ambito.
- [x] Verifica che la voce sia marcata `Should` (non `Must`) e `da decomporre` (non è in progress —
      è una promozione, non una feature attiva).
- [x] Verifica che **nessun'altra voce** venga rimossa o spostata (additivo — non toccare
      FEAT-001..010 dell'epica usabilità).
- [x] Verifica che `requirements/usabilita/epic.md` sia still-parseable (nessuna tabella rotta).

---

## Fase 5 — Polish e cross-cutting (3 task)

> Prerequisiti: tutte le Fasi 0–4. TASK-P01 [P] e TASK-P02 [P] sono parallelizzabili;
> TASK-P03 dipende da entrambi.

### TASK-P01 [P] — Suite verdi + lint ruff pulito

→ dipende da: tutti i task delle Fasi 0–4

- [x] Esegui `uv run pytest packages/sertor/tests/ -m "not cloud" -v` → verde (tutti i nuovi e
      modificati test: `test_install_rag_freshness.py`, aggiornamenti `test_assets_sync.py`).
- [x] Verifica **non-regressione**: i test pre-esistenti di `test_install_rag.py`,
      `test_install_rag_memory.py`, `test_install_rag_usage.py`, `test_install_rag_copilot_cli.py`
      restano verdi (i nuovi artefatti sono **additivi** — nessun piano pre-esistente cambia).
- [x] Esegui `uv run pytest packages/sertor-install-kit/tests/ -m "not cloud" -v` → verde
      (il kit ha solo TASK-F03 modificato: `gitignore_append.py`, test `test_gitignore_append.py`).
- [x] Esegui `uv run pytest tests/unit/ -m "not cloud" -v` → verde (guardia sync rag-freshness
      + guardia `test_assets_sync.py` pre-esistente).
- [x] Esegui `uv run ruff check packages/sertor/` → zero errori (regole E,F,I,UP,B; line-length 100).
- [x] Esegui `uv run ruff check packages/sertor-install-kit/` → zero errori.

### TASK-P02 [P] — Verifica additività: core, kit e comandi runtime invariati

→ dipende da: tutti i task delle Fasi 0–4

- [x] Verifica che **nessuno** dei seguenti file sia stato modificato (Principio XI / D-6):
      - `src/sertor_core/` — INVARIATO (porte/adapter/composition/engine/services/CLI).
      - `packages/sertor-install-kit/src/sertor_install_kit/` salvo `gitignore_append.py`
        (unica modifica al kit: riga `RUNTIME_IGNORES` — additiva, non-breaking, D-6).
      - `packages/sertor/src/sertor_installer/install_wiki.py` — INVARIATO.
      - `packages/sertor/src/sertor_installer/install_governance.py` — INVARIATO.
- [x] Esegui il sync dell'asset bundlato (meccanismo `sertor_installer.sync`) dopo aver creato i
      nuovi file in `assets/rag/hooks/`:
      ```powershell
      uv run python -m sertor_installer.sync
      ```
      Verifica che il comando non sovrascriva `.claude/hooks/rag-freshness*.ps1` con contenuto
      diverso da quello appena copiato in TASK-F04 (se il sync copre il subtree `rag/hooks/`,
      allinearli preventivamente; research D-0e: il sync attuale è su `claude/` — verificare
      l'effettiva copertura del subtree rag).
- [x] Spot check comandi runtime invariati:
      - `sertor install rag --assistant claude` produce gli stessi artefatti pre-esistenti **più** i
        4 nuovi rag-freshness (additivo — nessun artefatto pre-esistente rimosso).
      - `sertor-rag doctor`, `sertor-rag index`, `sertor configure` invariati (non toccati).
      - `sertor install rag --assistant copilot-cli` deposita lo script SessionEnd Copilot ma **non**
        lo script SessionStart (solo prompt statico — W5).
- [x] Verifica che la suite root `tests/unit/test_assets_sync.py` sia verde (guardia sync `claude/`
      pre-esistente non regredita).

### TASK-P03 — Verifica CS-1..5 e criteri di accettazione trasversali

→ dipende da: TASK-P01, TASK-P02

- [x] **CS-1 (freschezza enforced senza azione manuale):** TASK-F01 implementa il re-index
      incondizionato; TASK-US1-01..US3-01 lo verificano nel plan-builder. Confermato. ✓
- [x] **CS-2 (degrado evidente e indotto tra sessioni):** TASK-F01 persiste lo stato; TASK-F02
      legge e induce; TASK-US8-01 verifica le voci SessionEnd/SessionStart nel piano. Confermato. ✓
- [x] **CS-3 (non-fatale sempre):** TASK-F01/F02 hanno `try/catch` → exit 0 (R-2); TASK-US8-01
      verifica isolamento da `memory-capture`. Confermato. ✓
- [x] **CS-4 (installabile con parità e isolamento):** TASK-US8-01/02 verificano deposito Claude e
      Copilot; TASK-US8-02 verifica formato nativo Copilot (R-1); TASK-US8-03 verifica sync
      bundlato↔dogfood (R-3). Confermato. ✓
- [x] **CS-5 (zero costo a corpus invariato):** delegato all'incrementale del core (FEAT-009 su
      `master`, A-001) — l'hook non implementa change-detection propria (FR-002). Non testabile
      offline (richiederebbe un re-index reale); documentato come verifica manuale (quickstart §1). ✓
- [x] Verifica che il contratto `contracts/rag-health-state.md` (C1..C6) sia rispettato
      dall'implementazione in TASK-F01 (schema `rag.health/1`, campi obbligatori, nessun segreto,
      riscrittura a `healthy`).
- [x] Verifica che il contratto `contracts/freshness-hook-wiring.md` (W1..W5) sia rispettato:
      W1 parità formato → TASK-US8-02; W2 non-bloccante → TASK-F01/F02; W3 isolamento → TASK-US8-01;
      W4 D↔N → TASK-F02; W5 Copilot SessionStart prompt → TASK-US2-01/US8-02.
- [x] Segnala come **follow-up non-bloccante**: prova LIVE su ospite Claude e Copilot reale
      (quickstart §6) — il done offline è raggiunto con i task precedenti; la verifica su host reale
      è post-merge.

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01 [P]  (settings.rag-freshness.json)       ─────────────────────────────┐
TASK-S02 [P]  (settings.rag-freshness-start.json) ──────────────────────────┐  │
TASK-F01 [P]  (rag-freshness.ps1)                 ──────────────────────┐   │  │
TASK-F02 [P]  (rag-freshness-start.ps1)           ───────────────────┐  │   │  │
TASK-F03 [P]  (RUNTIME_IGNORES += rag-health.json)                   │  │   │  │
                                                                      │  │   │  │
TASK-F04      (dogfood .claude/) ← F01 + F02      ──────────────┐    │  │   │  │
                                                                 │    │  │   │  │
TASK-US7-01 [P] (CLAUDE.md step 5/8)              ─── [P]       │    │  │   │  │
                                                                 │    │  │   │  │
TASK-US1-01 [P] (W1: costanti SessionEnd Copilot)  ← S01, F01  │    │  │   │  │
TASK-US2-01 [P] (W2: costanti SessionStart Copilot) ← S02, F02 │    │  │   │  │
        │                                                        │    │  │   │  │
TASK-US3-01     (W3: build_rag_plan +4 artefatti)  ← US1+US2  ─┘    │  │   │  │
        │                                                             │  │   │  │
TASK-US4-01     (W4: dispatch _rag_hook_fragment)  ← US3             │  │   │  │
        │                                                             │  │   │  │
TASK-US5-01     (W5: owned_paths + lifecycle)      ← US4             │  │   │  │
        │                                                             │  │   │  │
        ├──────────────────────────────────────────────────────────   │  │   │  │
        │                                                             │  │   │  │
TASK-US8-01 [P] (test Claude: deposito+lifecycle)  ← US5, F01+F02   │  │   │  │
TASK-US8-02 [P] (test Copilot: formato nativo)     ← US5            │  │   │  │
TASK-US8-03     (guardia sync bundlato↔dogfood)    ← F01+F02+F04   ─┘  │   │  │
TASK-US9-01 [P] (promozione Out-of-Scope E12)      ← nessuno           │   │  │
        │                                                                │   │  │
TASK-P01 [P]    (suite verde + lint)               ← tutti            ──┘   │  │
TASK-P02 [P]    (additività + sync)                ← tutti            ──────┘  │
        │                                                                        │
TASK-P03        (CS-1..5 trasversali)              ← P01+P02         ──────────┘
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (re-index enforced senza azione manuale) | Il piano Claude contiene l'artefatto FILE `rag-freshness.ps1` e la voce SETTINGS_MERGE `SessionEnd`; lo script invoca `sertor-rag index .` incondizionatamente e delega lo skip al core (nessuna logica change-detection propria — FR-002). | TASK-F01, TASK-US8-01 | MECCANICO |
| **US2** (zero costo a corpus invariato) | Lo script non implementa change-detection propria (verifica testuale: assenza di logica diff/hash nell'hook); il comportamento di skip è documentato come delegato all'incrementale del core. Verifica offline: assenza del blocco change-detection; verifica live: quickstart §1. | TASK-F01 | TESTUALE+MANUALE |
| **US3** (stato degradato evidente all'avvio) | Con file di stato `verdict=degraded`, `rag-freshness-start.ps1` emette su stdout la direttiva d'induzione; con `healthy`/assente, nessun output (no-op). Script Claude [P] + prompt statico Copilot nel piano Copilot. | TASK-F02, TASK-US8-01, TASK-US8-02 | MECCANICO |
| **US4** (stato persiste oltre il confine di sessione) | L'hook SessionEnd scrive `.sertor/.rag-health.json` con schema `rag.health/1` (C1..C6): `verdict`/`timestamp`/`reason` obbligatori su `degraded`; a `healthy` riscrive (non cancella — INV-1/FR-010). | TASK-F01, TASK-US8-01 | MECCANICO |
| **US5** (smoke limitato a `doctor`, buco dichiarato) | L'hook non contiene alcuna query `where` su `search_code`/`search_docs` (verifica testuale: assenza di pattern `where`/`search_code`/`search_docs` negli script); il buco è promosso a E12 backlog (TASK-US9-01). | TASK-F01, TASK-F02, TASK-US9-01 | TESTUALE |
| **US6** (hook separato, non-fatale, isolato) | Il piano contiene voci `memory-capture` E `rag-freshness` come artefatti **distinti** (non fusi); entrambi gli script hanno `try/catch` → exit 0; isolamento: il fallimento di uno non blocca l'altro (artefatti indipendenti, processi separati). | TASK-F01, TASK-F02, TASK-US8-01 | MECCANICO |
| **US7** (governance riclassifica step 5/8) | `CLAUDE.md` step 5 e 8 contengono l'annotazione «ENFORCED VIA HOOK (E10-FEAT-011)» con nota D↔N; i passi non sono rimossi. | TASK-US7-01 | TESTUALE |
| **US8** (ospite riceve l'hook via installer, con parità) | `sertor install rag` Claude: deposita script SessionEnd + SessionStart + entrambe le voci settings. `sertor install rag` Copilot: deposita script SessionEnd + voce SETTINGS_MERGE SessionEnd formato nativo `version:1` + voce SessionStart prompt statico; **non** deposita `rag-freshness-start.ps1`. Guardia di sync: bundlato == dogfood byte-per-byte. | TASK-US8-01, TASK-US8-02, TASK-US8-03 | MECCANICO |
| **US9** (lifecycle granulare + asset in sync) | Uninstall: `rag-freshness.ps1`/`rag-freshness-start.ps1` rimossi dagli `owned_files`; upgrade: script aggiornato. Guardia sync bundlato↔dogfood verde. Promozione Out-of-Scope E12 nel backlog. | TASK-US5-01, TASK-US8-01, TASK-US8-03, TASK-US9-01 | MECCANICO |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 — nessun prerequisito (massima parallelizzazione):**
- TASK-S01 [P] (settings SessionEnd JSON)
- TASK-S02 [P] (settings SessionStart JSON)
- TASK-F01 [P] (script `rag-freshness.ps1`)
- TASK-F02 [P] (script `rag-freshness-start.ps1`)
- TASK-F03 [P] (kit `RUNTIME_IGNORES`)
- TASK-US7-01 [P] (CLAUDE.md reclassificazione — testo puro, indipendente)
- TASK-US9-01 [P] (backlog E12 promozione Out-of-Scope — testo puro, indipendente)

**Sprint 2 — dopo F01+F02 (in parallelo):**
- TASK-F04 (dogfood `.claude/` — dipende da F01+F02)
- TASK-US1-01 [P] (W1 costanti SessionEnd — dipende da S01+F01)
- TASK-US2-01 [P] (W2 costanti SessionStart — dipende da S02+F02)

**Sprint 3 — dopo US1+US2 (sequenziale a cascata):**
- TASK-US3-01 (W3 build_rag_plan — dipende da US1+US2)
- TASK-US4-01 (W4 dispatch Copilot — dipende da US3)
- TASK-US5-01 (W5 lifecycle — dipende da US4)

**Sprint 4 — dopo US5 (test in parallelo):**
- TASK-US8-01 [P] (test Claude)
- TASK-US8-02 [P] (test Copilot parità)
- TASK-US8-03 (guardia sync — dipende da F01+F02+F04)

**Sprint finale — Polish (in parallelo poi convergenza):**
- TASK-P01 [P] (suite verde + lint)
- TASK-P02 [P] (additività + sync)
- TASK-P03 (CS-1..5 — dopo P01+P02)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E10-FEAT-011 — enforcement freschezza RAG (hook)

Fase SpecKit "tasks" completata per specs/076-enforcement-freschezza-rag.
22 task in 6 fasi:
  Fase 0 Setup                    : 2 task  [P] (TASK-S01 settings SessionEnd · S02 settings SessionStart)
  Fase 1 Fondazionale             : 4 task  (TASK-F01 [P] script SessionEnd · F02 [P] script SessionStart ·
                                             F03 [P] kit RUNTIME_IGNORES · F04 dogfood .claude/)
  Fase 2 Storia US1..US6 Installer: 5 task  (TASK-US1-01 [P] · US2-01 [P] · US3-01 · US4-01 · US5-01
                                             — W1..W5 in install_rag.py)
  Fase 3 Storia US7 Governance    : 1 task  [P] (TASK-US7-01 — CLAUDE.md step 5/8 enforced via hook)
  Fase 4 Storie US8/US9 Test      : 4 task  (TASK-US8-01 [P] Claude · US8-02 [P] Copilot ·
                                             US8-03 guardia sync · US9-01 [P] backlog E12)
  Fase 5 Polish/cross-cutting     : 3 task  (TASK-P01 [P] suite+lint · P02 [P] additività ·
                                             P03 CS-1..5 trasversali)

Natura: ADDITIVO (harness hook + distribuzione). Nessun codice runtime del core.
sertor-core INVARIATO (Principio XI). Unica modifica al kit: +1 riga RUNTIME_IGNORES (additiva).
Rischi coperti:
  R-1 (CRITICO): formato Copilot generato via render_copilot_hooks — mai asset JSON in formato Claude
      (TASK-US1-01/US2-01/US8-02 — lezione FEAT-011/049).
  R-2: try/catch globale → exit 0 sempre in entrambi gli script (TASK-F01/F02, FR-017).
  R-3: guardia di sync bundlato↔dogfood nuova (TASK-US8-03 — non coperta da test_assets_sync.py).
  R-4: RUNTIME_IGNORES esteso prima del wiring (TASK-F03, research D-1 finding).
Copertura: FR-001..024, RNF-1..6, CS-1..5, US1..9.
Test natura: MECCANICO (US1/US3/US4/US6/US8/US9) + TESTUALE (US2/US5/US7).
Promozione Out-of-Scope: TASK-US9-01 → nuova FEAT-011 backlog usabilità E12 (smoke where).
Parità dual-target: TASK-US8-02 (formato nativo Copilot) + TASK-US8-03 (sync).
Default `memory-capture`/`rag-usage`/eval-skill invariati (additivo).
Sincronizzazione asset bundlati: TASK-P02 ricorda uv run python -m sertor_installer.sync.

Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.
Template tasks da 075-guided-setup (setup-plan.ps1/SKILL.md assenti).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/076-enforcement-freschezza-rag/tasks.md` (questo file, nuovo)
