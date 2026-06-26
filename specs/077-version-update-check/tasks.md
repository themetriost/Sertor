# Tasks — auto-update version check (avviso d'aggiornamento) (E2-FEAT-013)

**Branch**: `feat013-version-check-backlog` · **Generato**: 2026-06-25
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/version-check-state.md`](contracts/version-check-state.md) ·
[`contracts/version-check-hook-wiring.md`](contracts/version-check-hook-wiring.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO (harness + distribuzione), nessun codice di core.**
> La feature è 100% asset hook + installer + governance. Vive in:
> - 2 script PowerShell host-facing (`version-check.ps1`, `version-check-start.ps1`);
> - 4 asset settings JSON bundlati (SessionEnd + SessionStart, per-assistente Claude);
> - estensione di `install_rag.py` (costanti + plan-builder + stamp + lifecycle + dispatch);
> - 3 righe additive in `packages/sertor-install-kit/.../gitignore_append.py`;
> - copia dogfood in `.claude/hooks/`;
> - test offline + estensione guardia di sync bundlato↔dogfood.
>
> `sertor-core` è **INVARIATO** (Principio XI: lo script fa HTTP+file, mai importa la libreria
> né invoca un vehicle CLI). I comportamenti pre-feature sono **identici** a oggi (RNF-5).
>
> **Rischi noti da coprire (calibra l'ordine):**
> - **R-1 (CRITICO):** il formato nativo Copilot per l'hook SessionEnd/SessionStart deve essere
>   **generato** via `render_copilot_hooks([HookEntrySpec(...)])` (mai asset JSON in formato Claude
>   — lezione FEAT-011/049). Va fatto **prima** dei test di parità.
> - **R-2:** `version-check.ps1` deve uscire 0 in **qualsiasi** scenario (incluso GET fallita,
>   parse fallito, stamp assente) — `try/catch` globale gemello di `rag-freshness.ps1` (FR-009).
> - **R-3:** `version-check-start.ps1` NON deve essere depositato su Copilot (W5 del contratto:
>   Copilot SessionStart = prompt statico, niente script). Va verificato nei test di parità.
> - **R-4:** lo stamp `.sertor/.sertor-version` è scritto **dall'installer** (`importlib.metadata`
>   in-process), **mai** dall'hook a runtime (D-3); la logica va nel plan-builder, non nello script.
> - **R-5:** la guardia di sync bundlato↔dogfood si **estende** alla lista esistente in
>   `test_rag_freshness_dogfood_sync` (DRY, D-0f) — non una guardia gemella separata.
>
> **Strategia MVP/incrementale.**
> - **Setup** (TASK-S01..S02): asset settings JSON bundlati + sync via `sertor_installer.sync`.
>   Prerequisiti zero. Bloccanti per il wiring installer.
> - **Fondazionale A — Script SessionEnd** (TASK-F01): `version-check.ps1` (GET cachata +
>   confronto + persistenza). Indipendente [P]; bloccante per il wiring SessionEnd.
> - **Fondazionale B — Script SessionStart Claude** (TASK-F02): `version-check-start.ps1`
>   (legge stato + avvisa se behind). Indipendente [P]; bloccante per il wiring SessionStart.
> - **Fondazionale C — Kit RUNTIME_IGNORES** (TASK-F03): +3 righe additive nel kit.
>   Indipendente [P]; bloccante per il test di copertura kit.
> - **Fondazionale D — Dogfood `.claude/`** (TASK-F04): copia degli script + voci
>   `.claude/settings.json`. Dipende da F01+F02.
> - **Storia US1..US5/US8 — Installer** (TASK-US1-01..US5-01): wiring in `install_rag.py`
>   (costanti, plan-builder incluso stamp, dispatch Copilot, lifecycle). Dipende da F01+F02+S01.
>   Sequenziale internamente; W1 e W2 parallelizzabili.
> - **Storia US7 — Loop chiusura/governance** (TASK-US7-01): verifica stamp a upgrade. Dipende
>   da TASK-US3-01.
> - **Storia US6/US8/US9 — Test** (TASK-US6-01..US9-01): test offline (deposito, parità,
>   lifecycle, guardia sync, RUNTIME_IGNORES). Dipende da US5-01.
> - **Polish/cross-cutting** (TASK-P01..P03): suite verde, lint, additività, sync finale.
>
> L'ordine di priorità segue: script hook (Must P1) → installer + stamp → dogfood → test/guardia
> → polish. La granularità per-dimensione (`sertor-flow`, FR-012 Could) e il re-check forzato
> (FR-008/US9 Could) sono inclusi come parte dell'implementazione degli asset (nessun task
> separato) e testati come Must se implementati.

---

## Fase 0 — Setup: asset JSON bundlati (2 task)

> Prerequisiti: nessuno. Crea i file di settings JSON statici per le voci SessionEnd/SessionStart
> Claude nel bundle `sertor`. Bloccanti per il wiring installer (TASK-US1-01). Parallelizzabili [P].

### TASK-S01 [P] — Crea `assets/rag/settings.version-check.json` (voce SessionEnd Claude)

**File**: `packages/sertor/src/sertor_installer/assets/rag/settings.version-check.json` (NUOVO)
→ dipende da: nessuno

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/settings.version-check.json`
      con il payload di merge della voce `SessionEnd` per Claude nel **formato annidato nativo**
      (contratto `contracts/version-check-hook-wiring.md` §1):
      ```json
      { "hooks": { "SessionEnd": [ { "hooks": [ {
        "type": "command", "shell": "powershell", "timeout": 15,
        "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/version-check.ps1')"
      } ] } ] } }
      ```
- [x] Verifica che il formato sia **annidato** (forma `{"hooks":{"SessionEnd":[{"hooks":[...]}]}}`) —
      gemello di `settings.rag-freshness.json` (stessa struttura).
- [x] Verifica che il campo sia `"timeout"` (non `"timeoutSec"`) — `"timeoutSec"` è il formato Copilot
      (W1 del contratto di wiring).
- [x] Verifica che il `command` costruisca il path **host-agnostico**: `$env:CLAUDE_PROJECT_DIR` →
      fallback `'.'` (pattern `memory-capture.ps1` — research D-0a).

### TASK-S02 [P] — Crea `assets/rag/settings.version-check-start.json` (voce SessionStart Claude)

**File**: `packages/sertor/src/sertor_installer/assets/rag/settings.version-check-start.json` (NUOVO)
→ dipende da: nessuno

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/settings.version-check-start.json`
      con il payload di merge della voce `SessionStart` per Claude (contratto §1):
      ```json
      { "hooks": { "SessionStart": [ { "hooks": [ {
        "type": "command", "shell": "powershell", "timeout": 10,
        "statusMessage": "Verifico la disponibilità di aggiornamenti Sertor",
        "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/version-check-start.ps1') -Assistant claude"
      } ] } ] } }
      ```
- [x] Verifica che `statusMessage` sia presente (feedback user-visible, coerente col pattern Claude
      — gemello di `settings.rag-freshness-start.json`).
- [x] Verifica il timeout `10` (s) — inferiore a quello SessionEnd (15 s) perché il SessionStart è
      solo lettura del file di stato, zero rete (RNF-1/W6 del contratto).
- [x] Verifica che il `command` passi `-Assistant claude` allo script (usato per adattare il messaggio
      emesso — data-model §3b).

---

## Fase 1 — Fondazionale: script hook, kit e dogfood (4 task)

> Prerequisiti: nessuno per F01/F02/F03 (parallelizzabili tra loro [P]). F04 dipende da F01+F02.
> Bloccanti per la fase installer (TASK-US1-01..US5-01).

### TASK-F01 [P] — Crea `assets/rag/hooks/version-check.ps1` (SessionEnd: GET cachata + confronto + persistenza)

**File**: `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.ps1` (NUOVO)
→ dipende da: nessuno

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.ps1`
      seguendo la **disciplina di `rag-freshness.ps1`** (research D-0a): wrapper `SessionEnd` thin,
      `try/catch` globale, exit 0 **sempre** (R-2/FR-009/RNF-2), payload JSON tollerante da stdin,
      root da `$env:CLAUDE_PROJECT_DIR` → `hook.cwd` → `'.'`.
- [x] Implementa la **logica di orchestrazione** (data-model §3a, research D-5):
      1. Legge `.sertor/.version-check.json`; se `checked_at` entro ~24h e
         `$env:SERTOR_VERSION_CHECK_FORCE` non impostata → **riusa l'esito** (nessuna GET, FR-006)
         e riconferma il verdetto vs stamp corrente (gestisce un upgrade a metà giornata, R-5/FR-013).
      2. Altrimenti: **GET** `$env:SERTOR_VERSION_CHECK_URL` (default
         `https://raw.githubusercontent.com/themetriost/Sertor/master/VERSION`, research D-2),
         timeout ~5 s, `.Trim()` del contenuto → `$latest`.
      3. Legge lo stamp `.sertor/.sertor-version` → `$installed`; legge
         `.sertor/.sertor-flow-version` se presente → `$dimensions` (FR-011/012, Could).
      4. **Confronto semantico per segmenti numerici** + fallback lessicale (research D-4): split
         su `.`, confronta segmenti come interi; se un segmento è non-numerico → fallback stringa.
         Verdetto: `$installed < $latest` → `behind`; `==` → `up-to-date`; `>` → `ahead`;
         parse fallito → `unknown` (FR-010, INV-2, mai un falso `behind`).
      5. Scrive `.sertor/.version-check.json` con schema `version.check/1` (contratto
         `contracts/version-check-state.md`): campi `schema`, `verdict`, `installed`, `latest`,
         `checked_at` (ISO-8601 UTC) obbligatori; `dimensions` additivo (INV-1: scritto sempre,
         non cancellato, così `up-to-date`/`ahead`/`unknown` portano a no-op al SessionStart).
      6. **exit 0 sempre**; GET fallita/parse fallito → `verdict: "unknown"`, nessun errore.
- [x] Verifica che **nessun Python né `sertor_core`** sia invocato (R-4/FR-014/Principio XI):
      la versione «installata» viene dallo stamp, **non** da `importlib.metadata` a runtime.
- [x] Verifica che lo script sia **host-agnostico** (RNF-3): nessun path hardcodato a `Sertor`;
      URL del remoto sovrascrivibile via `$env:SERTOR_VERSION_CHECK_URL` (research D-2/Principio VIII).
- [x] Verifica che nessun segreto finisca nel file di stato (INV-3/FR-015): i campi `installed`/
      `latest` sono numeri di versione pubblici; nessun path di progetto né credenziali.
- [x] Verifica `exit 0` **anche se GET fallisce o `.sertor/.sertor-version` è assente** (R-2): il
      `try/catch` assorbe qualsiasi eccezione PowerShell; stamp assente → `verdict: "unknown"` (INV-6).
- [x] Verifica che l'implementazione della cache (~24h) rispecchi S2 del contratto: lo script
      **riusa** l'esito senza GET quando `checked_at` è fresco, e **riconfronta** il verdetto vs stamp
      attuale (così un upgrade a metà giornata non avvisa a vuoto — INV-4/R-5).

### TASK-F02 [P] — Crea `assets/rag/hooks/version-check-start.ps1` (SessionStart Claude: legge stato + avvisa)

**File**: `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check-start.ps1` (NUOVO)
→ dipende da: nessuno

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check-start.ps1`
      con parametro `-Assistant` (valore atteso: `claude`; estendibile senza breaking change).
- [x] Implementa la **logica di lettura e avviso** (data-model §3b, research D-1 — D↔N):
      1. Legge `.sertor/.version-check.json` (root da `$env:CLAUDE_PROJECT_DIR` → `'.'`).
      2. File assente OR `verdict != "behind"` → **no-op** (exit 0, nessun output): INV-1,
         nessun avviso superfluo su `up-to-date`/`ahead`/`unknown` (FR-004/010).
      3. `verdict == "behind"` → emette su **stdout** l'avviso (FR-003): nomina `installed`,
         `latest`, e il comando d'aggiornamento (`sertor upgrade` / `uvx --refresh …`);
         se `dimensions` è presente, nomina quale/i dimensione/i è indietro (FR-012/US6-AC2).
- [x] Verifica il **confine D↔N** (W4/FR-014): lo script **NON** applica mai alcun aggiornamento
      (FR-005/CS-4) — emette solo l'avviso; l'utente decide ed esegue. Nessun LLM invocato.
- [x] Verifica exit **sempre 0** (FR-009/RNF-2): il `try/catch` assorbe file mancante, JSON
      malformato, qualsiasi errore di lettura — la sessione parte sempre normalmente.
- [x] Verifica host-agnosticità (RNF-3): nessun path hardcodato a `Sertor`; funziona su qualsiasi
      ospite con la capacità installata.

### TASK-F03 [P] — Estendi `RUNTIME_IGNORES` nel kit con le 3 nuove voci di stato

**File**: `packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py` (MODIFICA)
→ dipende da: nessuno

- [x] Aggiungi le 3 nuove voci alla tupla `RUNTIME_IGNORES` (dopo la riga `.sertor\.rag-health.json`,
      research D-0e / data-model §6 / contratto `version-check-state.md`):
      ```python
      ".sertor/.version-check.json",   # E2-FEAT-013: version-check state (regenerable, never versioned)
      ".sertor/.sertor-version",        # E2-FEAT-013: installed version stamp (written by installer)
      ".sertor/.sertor-flow-version",   # E2-FEAT-013: governance stamp (written by sertor-flow install)
      ```
      (additivo, non-breaking — unica fonte di verità per il `.gitignore` dell'ospite, Principio VIII).
- [x] Verifica che il test esistente
      `packages/sertor-install-kit/tests/unit/test_gitignore_append.py`
      (asserzione `all(entry in text for entry in RUNTIME_IGNORES)`) sia ancora verde dopo l'aggiunta
      — le 3 nuove voci appaiono nel `.gitignore` generato.
- [x] Verifica che `append_gitignore` (con default `RUNTIME_IGNORES`) scriva le nuove righe nel
      `.gitignore` host quando chiamato dall'installer.
- [x] Verifica che `remove_gitignore_lines` rimuova anche le 3 nuove voci su uninstall
      (la funzione itera su `RUNTIME_IGNORES` — comportamento ereditato, nessuna modifica aggiuntiva).

### TASK-F04 — Aggiorna dogfood `.claude/`: copia script + voci settings

**File**: `.claude/hooks/version-check.ps1` (NUOVO),
         `.claude/hooks/version-check-start.ps1` (NUOVO),
         `.claude/settings.json` (MODIFICA)
→ dipende da: TASK-F01, TASK-F02 (script sorgente devono esistere)

- [x] Copia `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.ps1` →
      `.claude/hooks/version-check.ps1` (**byte-identico** — la guardia estesa TASK-US8-03 la
      verifica; research D-0f/FR-016).
- [x] Copia `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check-start.ps1` →
      `.claude/hooks/version-check-start.ps1` (**byte-identico**; FR-016).
- [x] Aggiungi la voce `SessionEnd` per `version-check` in `.claude/settings.json` via **merge
      dedup** (stesso payload di `assets/rag/settings.version-check.json`): la nuova voce va
      accanto a quelle di `memory-capture`, `rag-freshness` e `sertor-rag-usage-check` **senza
      toccarle** (FR-016/W3 del contratto — isolamento).
- [x] Aggiungi la voce `SessionStart` per `version-check-start` in `.claude/settings.json` (payload
      di `assets/rag/settings.version-check-start.json`): accanto alla voce `rag-freshness-start`
      esistente, **senza toccarla** (FR-016).
- [x] Verifica che `.claude/settings.json` contenga **entrambe** le nuove voci dopo il merge e che
      le voci pre-esistenti (wiki, memory-capture, rag-freshness, rag-usage) siano **intatte**.
- [x] Verifica che `.sertor/.version-check.json`, `.sertor/.sertor-version` e
      `.sertor/.sertor-flow-version` siano presenti in `.gitignore` (propagati da TASK-F03 +
      `append_gitignore` sul dogfood, o aggiunti manualmente se il `.gitignore` non è gestito
      dall'installer su questo host).

---

## Fase 2 — Storie US1-US5/US8: wiring installer `install_rag.py` (5 task)

> Prerequisiti: TASK-F01, TASK-F02 (script sorgente bundlati), TASK-S01, TASK-S02 (settings JSON).
> W1 e W2 sono [P] tra loro; W3 dipende da W1+W2; W4 dipende da W3; W5 dipende da W4.

### TASK-US1-01 [P] — W1: costanti e sentinel Copilot per l'hook SessionEnd version-check

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-S01, TASK-F01

**Mappa FR**: FR-001/002/006/009/016/017 · US1/US2/US3/US4/US8

- [x] Aggiungi le costanti per l'hook `SessionEnd` version-check, **dopo** il blocco
      `_COPILOT_FRESHNESS_START_WIRING_SENTINEL` (research D-0b, data-model §5):
      ```python
      # Version-update check hook – SessionEnd (E2-FEAT-013)
      _VERSION_CHECK_HOOK_ASSET  = "rag/hooks/version-check.ps1"
      _VERSION_CHECK_HOOK_TARGET = ".claude/hooks/version-check.ps1"
      _VERSION_CHECK_HOOK_TARGET_COPILOT = ".github/hooks/version-check.ps1"
      _VERSION_CHECK_SETTINGS    = "rag/settings.version-check.json"
      _COPILOT_VERSION_CHECK_END_WIRING_SENTINEL = "(generated: copilot version-check-end hooks)"
      ```
- [x] Aggiungi la factory `_copilot_version_check_end_specs() -> list[HookEntrySpec]` (gemella di
      `_copilot_freshness_end_specs`) che genera la voce SessionEnd **nativa Copilot**
      (formato piatto `version:1`/`timeoutSec` — contratto §2/W1, R-1):
      ```python
      def _copilot_version_check_end_specs() -> list[HookEntrySpec]:
          return [HookEntrySpec(
              "SessionEnd", "command",
              f"{_PWSH} {_VERSION_CHECK_HOOK_TARGET_COPILOT}", 15,
          )]
      ```
- [x] Verifica che `HookEntrySpec` sia già importato in `install_rag.py` — nessun import aggiuntivo.
- [x] Verifica (su carta) che `render_copilot_hooks([HookEntrySpec("SessionEnd","command","…",15)])`
      produca formato piatto nativo: `{"version":1,"hooks":{"SessionEnd":[{"type":"command",
      "command":"…","timeoutSec":15}]}}` — mai `"shell"`/`"statusMessage"`/`"timeout"` senza `Sec`.

### TASK-US2-01 [P] — W2: costanti e sentinel Copilot per il segnale SessionStart version-check

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-S02, TASK-F02

**Mappa FR**: FR-003/016/017 · US1/US8

- [x] Aggiungi le costanti per il segnale `SessionStart` version-check, **dopo** le costanti W1:
      ```python
      # Version-update check signal – SessionStart (E2-FEAT-013)
      _VERSION_CHECK_START_ASSET   = "rag/hooks/version-check-start.ps1"
      _VERSION_CHECK_START_TARGET  = ".claude/hooks/version-check-start.ps1"
      _VERSION_CHECK_START_SETTINGS = "rag/settings.version-check-start.json"
      _COPILOT_VERSION_CHECK_START_WIRING_SENTINEL = "(generated: copilot version-check-start hooks)"
      ```
- [x] Aggiungi la factory `_copilot_version_check_start_specs() -> list[HookEntrySpec]` che genera
      la voce SessionStart **nativa Copilot** come **prompt statico** (W5/A-005, research D-1 — il
      SessionStart Copilot non può fare rete, il prompt istruisce l'agente a leggere lo stato):
      ```python
      def _copilot_version_check_start_specs() -> list[HookEntrySpec]:
          return [HookEntrySpec(
              "SessionStart", "prompt",
              "All'avvio: leggi .sertor/.version-check.json. "
              "Se verdict=behind, mostra l'avviso (versione installata, ultima versione, "
              "comando d'aggiornamento `sertor upgrade` / `uvx --refresh ...`); "
              "se sono presenti dimensions, nomina quali dimensioni sono indietro. "
              "Non applicare alcun aggiornamento da te. "
              "Se up-to-date/ahead/unknown/assente, procedi senza avviso.",
              10,
          )]
      ```
- [x] Verifica che la factory **non depositi** uno script `version-check-start.ps1` su Copilot
      (W5/R-3): il SessionStart Copilot è solo un prompt statico; lo script `.ps1` è un artefatto
      **solo Claude** (data-model §5 nota artefatto (a)).
- [x] Verifica (su carta) che `render_copilot_hooks([HookEntrySpec("SessionStart","prompt","…",10)])`
      produca `{"version":1,"hooks":{"SessionStart":[{"type":"prompt","prompt":"…","timeoutSec":10}]}}`.

### TASK-US3-01 — W3: estendi `build_rag_plan` con i 5 nuovi artefatti (script + stamp)

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-US1-01, TASK-US2-01

**Mappa FR**: FR-007/013/016/017/018 · US5/US7/US8-AC1

- [x] Individua la sezione di `build_rag_plan` che emette gli artefatti hook esistenti (blocco
      rag-freshness, circa riga `:404-440`).
- [x] Aggiungi **in coda** al blocco hook i 4 artefatti version-check (data-model §5):
      ```python
      # Version-update check hook – SessionEnd (E2-FEAT-013)
      version_check_target = (
          _VERSION_CHECK_HOOK_TARGET if not is_copilot
          else _VERSION_CHECK_HOOK_TARGET_COPILOT
      )
      plan.append(Artifact(
          ArtifactKind.FILE,
          _VERSION_CHECK_HOOK_ASSET,
          version_check_target,
          WriteStrategy.CREATE_IF_ABSENT,
      ))
      plan.append(Artifact(
          ArtifactKind.SETTINGS_MERGE,
          _VERSION_CHECK_SETTINGS if not is_copilot
              else _COPILOT_VERSION_CHECK_END_WIRING_SENTINEL,
          _SETTINGS_TARGET if not is_copilot else _COPILOT_HOOK_WIRING,
          WriteStrategy.MERGE_DEDUP,
      ))
      # Version-update check signal – SessionStart (E2-FEAT-013)
      if not is_copilot:
          plan.append(Artifact(
              ArtifactKind.FILE,
              _VERSION_CHECK_START_ASSET,
              _VERSION_CHECK_START_TARGET,
              WriteStrategy.CREATE_IF_ABSENT,
          ))
      plan.append(Artifact(
          ArtifactKind.SETTINGS_MERGE,
          _VERSION_CHECK_START_SETTINGS if not is_copilot
              else _COPILOT_VERSION_CHECK_START_WIRING_SENTINEL,
          _SETTINGS_TARGET if not is_copilot else _COPILOT_HOOK_WIRING,
          WriteStrategy.MERGE_DEDUP,
      ))
      ```
- [x] Aggiungi il **5° artefatto**: lo stamp `.sertor/.sertor-version` scritto a install-time
      (data-model §5 riga 5 / R-4 — l'installer scrive la versione in-process via
      `importlib.metadata.version("sertor")`, **mai** lo script a runtime). Valuta come `ArtifactKind`
      gestire una scrittura di file generato (contenuto derivato a apply-time): modella su un pattern
      simile esistente nel kit (es. `ENV_MERGE` o un `ArtifactKind.FILE` con source generata
      on-the-fly nel dispatcher `_apply_rag_install`). Il valore da scrivere è
      `importlib.metadata.version("sertor")` letto nell'apply del plan rag (chiamata in-process
      a install/upgrade-time, **non** runtime hook):
      ```python
      import importlib.metadata as _imeta
      # nel dispatcher:
      version_stamp = _imeta.version("sertor")
      (root / ".sertor" / ".sertor-version").write_text(version_stamp + "\n", encoding="utf-8")
      ```
      Se un `ArtifactKind` dedicato non è disponibile, è accettabile scrivere lo stamp
      **direttamente nel dispatcher** di install/upgrade (sopra il return del report, un blocco
      try/except non-fatale — coerente con il pattern di `DEPENDENCIES` che crea `.sertor/.venv`).
- [x] Verifica che lo script `version-check-start.ps1` sia emesso **solo per Claude** (`not is_copilot`),
      in coerenza con W5 del contratto e data-model §5 nota artefatto (a).
- [x] Verifica additività: gli artefatti pre-esistenti (rag-freshness, memory-capture, rag-usage,
      skill, agente) **non** sono rimossi o spostati; i nuovi vengono aggiunti in coda (SC-010).

### TASK-US4-01 — W4: estendi `_rag_hook_fragment` con i 2 nuovi sentinel Copilot

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-US3-01

**Mappa FR**: FR-016 · US8-AC2

- [x] Individua la funzione `_rag_hook_fragment` (circa riga `:524-539`). Oggi gestisce i sentinel
      `_COPILOT_FRESHNESS_END_WIRING_SENTINEL` e `_COPILOT_FRESHNESS_START_WIRING_SENTINEL`.
- [x] Estendi il dispatch con i 2 nuovi sentinel (art-aware, riuso `render_copilot_hooks`):
      ```python
      if art.source == _COPILOT_VERSION_CHECK_END_WIRING_SENTINEL:
          return render_copilot_hooks(_copilot_version_check_end_specs())
      if art.source == _COPILOT_VERSION_CHECK_START_WIRING_SENTINEL:
          return render_copilot_hooks(_copilot_version_check_start_specs())
      ```
- [x] Verifica che `render_copilot_hooks` sia già importato in `install_rag.py` (riga `:60` circa)
      — nessun import aggiuntivo.
- [x] Verifica (su carta) il JSON Copilot risultante per `SessionEnd`:
      `{"version":1,"hooks":{"SessionEnd":[{"type":"command","command":"pwsh -File …/version-check.ps1","timeoutSec":15}]}}` — mai formato Claude (R-1/W1).
- [x] Verifica (su carta) il JSON Copilot per `SessionStart` (prompt statico):
      `{"version":1,"hooks":{"SessionStart":[{"type":"prompt","prompt":"…","timeoutSec":10}]}}` — W5.

### TASK-US5-01 — W5: estendi `sertor_owned_paths` + lifecycle uninstall/upgrade

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-US4-01

**Mappa FR**: FR-013/017 · US7/US8-AC1/US9

- [x] Individua `sertor_owned_paths` (circa riga `:614`). Oggi `owned_files` include i target di
      rag-freshness (`_FRESHNESS_HOOK_TARGET`, `_FRESHNESS_START_TARGET`, Copilot) e memory-capture.
- [x] Aggiungi ai **`owned_files`** i nuovi path (FR-017 — da rimuovere su uninstall / aggiornare
      su upgrade):
      - Claude: `_VERSION_CHECK_HOOK_TARGET` + `_VERSION_CHECK_START_TARGET`.
      - Copilot: `_VERSION_CHECK_HOOK_TARGET_COPILOT` (solo SessionEnd script — W5: il SessionStart
        Copilot è un prompt generato, nessun file `.ps1` depositato).
      - Stamp: `".sertor/.sertor-version"` (e `.sertor/.sertor-flow-version` se scritto da questo
        plan-builder — da valutare in base a come TASK-US3-01 scrive lo stamp).
- [x] Verifica che i `shared_edits` coprano le voci `SessionEnd`/`SessionStart` version-check nello
      stesso settings file degli altri hook — già coperte dallo `SharedEdit` esistente per
      `_SETTINGS_TARGET` (Claude) e `_COPILOT_HOOK_WIRING` (Copilot): nessuna modifica aggiuntiva.
- [x] Verifica che l'**uninstall** sia già art-aware (FILE→`remove_path`; SETTINGS_MERGE→
      `remove_settings_entries` con `delete_if_empty` per `sertor-hooks.json`): il dispatch esistente
      gestisce i nuovi artefatti senza logica aggiuntiva (riuso, data-model §6).
- [x] Verifica che l'**upgrade** aggiorni i nuovi script FILE via `update_file_if_changed` e
      **riscriva lo stamp** (chiude la loop, INV-5/FR-013/US7): dopo l'upgrade, il prossimo
      SessionEnd confronta la nuova versione col remoto e il verdetto torna `up-to-date`.
- [x] Verifica che il test di copertura `plan ⊆ owned` resti verde: ogni `target_rel` degli
      artefatti aggiunti in TASK-US3-01 compare negli `owned_files` o `shared_edits` di
      `sertor_owned_paths`.

---

## Fase 3 — Storia US7: chiusura della loop a upgrade (1 task)

> Prerequisito: TASK-US3-01 (la logica di scrittura dello stamp è in `build_rag_plan` / dispatcher).
> Può essere eseguito in parallelo con US4-01 se la logica stamp è già in US3-01 [P].

### TASK-US7-01 [P] — Verifica e documenta la chiusura della loop a upgrade (stamp riscritto)

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (verifica) ·
         `specs/077-version-update-check/quickstart.md` (già presente come V6)
→ dipende da: TASK-US3-01

**Mappa FR**: FR-013 · US7-AC1/AC2/AC3 · INV-5

- [x] Verifica che nella logica di `upgrade` (dispatch `_apply_rag_lifecycle` o equivalente) lo
      stamp `.sertor/.sertor-version` venga **riscritto** con la nuova versione del pacchetto —
      gemello di come l'upgrade aggiorna i FILE tramite `update_file_if_changed` (data-model §6,
      lifecycle upgrade).
- [x] Verifica che la cache del version-check sia **invalidata** dopo l'upgrade: poiché lo script
      SessionEnd riconferma il verdetto vs stamp **ogni volta** (inclusa la finestra cache — INV-4),
      il prossimo SessionEnd post-upgrade legge il nuovo stamp e, se corrisponde al `latest`,
      scrive `up-to-date` → il SessionStart successivo non avvisa (US7-AC1/AC2).
- [x] Verifica che l'edge case «upgrade a metà giornata con cache ancora fresca e verdetto `behind`»
      sia gestito correttamente (R-5): la riconferma del verdetto vs stamp corrente — eseguita anche
      dentro la finestra cache — aggiorna il verdict a `up-to-date` senza una nuova GET (INV-4/D-5).
- [x] Verifica che lo stamp assente post-uninstall → `verdict: "unknown"` (skip silenzioso, INV-6);
      nessun avviso residuo dopo la rimozione della capacità (US7-AC3 implicito).

---

## Fase 4 — Storie US6/US8/US9: test offline e guardia di sync (4 task)

> Prerequisiti: TASK-US5-01 (wiring completo), TASK-F01/F02 (script sorgente).
> TASK-US6-01 [P] e TASK-US6-02 [P] sono parallelizzabili; TASK-US8-01 dipende da entrambi;
> TASK-US9-01 [P] è indipendente (file sorgente, non plan-builder).

### TASK-US6-01 [P] — Test deposito Claude: script + voci + stamp + lifecycle (P1 Must)

**File**: `packages/sertor/tests/test_install_rag_version_check.py` (NUOVO)
→ dipende da: TASK-US5-01

**Mappa FR**: FR-007/016/017/018 · US5/US7/US8-AC1 · CS-5

- [x] Crea il file `packages/sertor/tests/test_install_rag_version_check.py` (gemello di
      `test_install_rag_freshness.py` — stessa struttura con `FakeCommandRunner`/`_run`/`_profile`).
- [x] `test_version_check_hook_deposited_claude`: via `build_rag_plan(assistant=CLAUDE)`, verifica
      che `.claude/hooks/version-check.ps1` sia un target FILE del piano (FR-016/US8-AC1).
- [x] `test_version_check_start_deposited_claude`: verifica che `.claude/hooks/version-check-start.ps1`
      sia un target FILE del piano Claude (FR-016/US8-AC1; solo Claude, non Copilot — W5/R-3).
- [x] `test_version_check_session_end_settings_claude`: verifica che `.claude/settings.json` sia
      un target SETTINGS_MERGE del piano Claude con la voce `SessionEnd` version-check (FR-016).
- [x] `test_version_check_session_start_settings_claude`: verifica che `.claude/settings.json` sia
      un target SETTINGS_MERGE del piano Claude con la voce `SessionStart` version-check (FR-016).
- [x] `test_version_check_isolated_from_freshness`: verifica che il piano contenga ENTRAMBE le voci
      hook `rag-freshness` E `version-check` su `SessionEnd` come **artefatti distinti** (W3 del
      contratto — non fusi in uno script unico; FR-016).
- [x] Test lifecycle — uninstall: dopo `build_rag_plan(op=UNINSTALL, assistant=CLAUDE)`, i path
      `_VERSION_CHECK_HOOK_TARGET` e `_VERSION_CHECK_START_TARGET` compaiono negli `owned_files` di
      `sertor_owned_paths` (FR-017/US9).
- [x] Test lifecycle — upgrade: lo script `version-check.ps1` è presente nel piano come FILE da
      aggiornare su upgrade (`update_file_if_changed`); lo stamp è riscritto (FR-013/US7).
- [x] `test_version_stamp_written_at_install`: verifica che il piano o il dispatcher scriva
      `.sertor/.sertor-version` a install-time con un valore di versione (non vuoto) —
      **non** uno script lo scrive a runtime (R-4/D-3).
- [x] Tutti `not cloud`, offline (nessun `uv`/ospite reale — RNF-5).

### TASK-US6-02 [P] — Test deposito Copilot: formato nativo + parità (P1 Must)

**File**: `packages/sertor/tests/test_install_rag_version_check.py` (MODIFICA — continua)
→ dipende da: TASK-US5-01

**Mappa FR**: FR-016 · US8-AC2 · CS-5

- [x] `test_version_check_hook_deposited_copilot`: via `build_rag_plan(assistant=COPILOT_CLI)`,
      verifica che `.github/hooks/version-check.ps1` sia un target FILE del piano (FR-016/US8-AC2).
- [x] `test_version_check_start_NOT_deposited_copilot`: verifica che `.github/hooks/version-check-start.ps1`
      **NON** sia un target del piano Copilot (W5/R-3 — il SessionStart Copilot è un prompt statico,
      mai uno script depositato; US8-AC2).
- [x] `test_version_check_end_wiring_copilot_native_format`: il contenuto del SETTINGS_MERGE per
      `SessionEnd` Copilot (da `render_copilot_hooks`) ha formato piatto nativo:
      `{"version":1,"hooks":{"SessionEnd":[{"type":"command","command":"…","timeoutSec":15}]}}` —
      mai `"shell"`/`"statusMessage"`/`"timeout"` senza `Sec` (R-1/W1 contratto).
- [x] `test_version_check_start_wiring_copilot_native_format`: il contenuto SETTINGS_MERGE per
      `SessionStart` Copilot ha `{"type":"prompt","prompt":"…","timeoutSec":10}` (W5/R-1).
- [x] `test_version_check_no_claude_format_on_copilot`: verifica che nessun artefatto Copilot
      contenga i campi Claude (`"shell"`, `"statusMessage"`, `"timeout"` senza `Sec`) nel suo
      contenuto serializzato (parità — lezione FEAT-011/049, FR-016).
- [x] Tutti `not cloud`, offline.

### TASK-US8-01 — Estendi guardia di sync bundlato↔dogfood (R-5, P2 Should)

**File**: `packages/sertor/tests/test_install_rag_freshness.py` (MODIFICA — estende
         `test_rag_freshness_dogfood_sync`) ·
→ dipende da: TASK-F01, TASK-F02, TASK-F04

**Mappa FR**: FR-016 · US9 · CS-5

- [x] **Estendi** la lista in `test_rag_freshness_dogfood_sync` (file esistente `test_install_rag_freshness.py:323`)
      aggiungendo i 2 nuovi nomi script (DRY — non creare una guardia gemella separata, research D-0f):
      ```python
      for name in (
          "rag-freshness.ps1", "rag-freshness-start.ps1",
          "version-check.ps1", "version-check-start.ps1",   # E2-FEAT-013
      ):
      ```
- [x] Verifica che il test **fallisca** se si introduce un drift manuale in uno dei 2 nuovi file
      (controllo di sanity della guardia).
- [x] Verifica che `test_assets_sync.py` (guardia `claude/` esistente) **non** copra già gli hook
      rag (il subtree `claude/` non include `assets/rag/hooks/`) — nessuna duplicazione.
- [x] Verifica che la guardia copra anche i nuovi script prima di qualsiasi merge.

### TASK-US9-01 [P] — Test `RUNTIME_IGNORES` esteso (kit) + form degli script (P2 Should)

**File**: `packages/sertor/tests/test_install_rag_version_check.py` (aggiunta) ·
         `packages/sertor-install-kit/tests/unit/test_gitignore_append.py` (verifica)
→ dipende da: TASK-F03

**Mappa FR**: FR-018 · US5-AC3 · CS-5

- [x] `test_version_check_runtime_ignores`: verifica che `RUNTIME_IGNORES` del kit contenga le 3
      nuove voci (`.sertor/.version-check.json`, `.sertor/.sertor-version`,
      `.sertor/.sertor-flow-version`) — la tupla è la fonte unica per il `.gitignore` dell'ospite
      (FR-018/TASK-F03).
- [x] `test_version_check_scripts_no_sertor_core`: legge il contenuto dei 2 script bundlati
      e verifica assenza di pattern `sertor_core|import sertor|python` nel path caldo (R-4/FR-014) —
      gemello del quickstart V10 come verifica offline.
- [x] `test_version_check_script_has_try_catch_and_exit0`: verifica presenza di `try` e `catch`
      (o equivalente PowerShell) e `exit 0` nel corpo di `version-check.ps1` (R-2/RNF-2 — offline,
      analisi testuale del file).
- [x] Verifica che il test kit `test_gitignore_append.py` (già esistente) sia ancora verde con le
      3 nuove voci in `RUNTIME_IGNORES` (TASK-F03).

---

## Fase 5 — Polish e cross-cutting (3 task)

> Prerequisiti: tutte le Fasi 0–4. TASK-P01 [P] e TASK-P02 [P] sono parallelizzabili;
> TASK-P03 dipende da entrambi.

### TASK-P01 [P] — Suite verdi + lint ruff pulito

→ dipende da: tutti i task delle Fasi 0–4

- [x] Esegui `uv run pytest packages/sertor/tests/ -m "not cloud" -v` → verde (tutti i nuovi test:
      `test_install_rag_version_check.py`, aggiornamento `test_install_rag_freshness.py`).
- [x] Verifica **non-regressione**: i test pre-esistenti di `test_install_rag.py`,
      `test_install_rag_freshness.py`, `test_install_rag_memory.py`, `test_install_rag_usage.py`,
      `test_install_rag_copilot_cli.py` restano verdi (i nuovi artefatti sono additivi).
- [x] Esegui `uv run pytest packages/sertor-install-kit/tests/ -m "not cloud" -v` → verde
      (il kit ha solo TASK-F03 modificato: `gitignore_append.py` + `test_gitignore_append.py`).
- [x] Esegui `uv run pytest tests/unit/ -m "not cloud" -v` → verde (guardia sync estesa in
      `test_install_rag_freshness.py:test_rag_freshness_dogfood_sync`).
- [x] Esegui `uv run ruff check packages/sertor/` → zero errori (regole E,F,I,UP,B; line-length 100).
- [x] Esegui `uv run ruff check packages/sertor-install-kit/` → zero errori.

### TASK-P02 [P] — Verifica additività: core, kit e comandi runtime invariati

→ dipende da: tutti i task delle Fasi 0–4

- [x] Verifica che **nessuno** dei seguenti file sia stato modificato (Principio XI/RNF-5):
      - `src/sertor_core/` — INVARIATO (porte/adapter/composition/engine/services/CLI).
      - `packages/sertor-install-kit/src/sertor_install_kit/` salvo `gitignore_append.py`
        (unica modifica al kit: +3 righe `RUNTIME_IGNORES` — additiva, non-breaking, D-8).
      - `packages/sertor/src/sertor_installer/install_wiki.py` — INVARIATO.
      - `packages/sertor/src/sertor_installer/install_governance.py` — INVARIATO.
- [x] Esegui il sync dell'asset bundlato dopo aver creato i nuovi file in `assets/rag/hooks/`:
      ```powershell
      uv run python -m sertor_installer.sync
      ```
      Verifica che il comando non sovrascriva `.claude/hooks/version-check*.ps1` con contenuto
      diverso da quello copiato in TASK-F04 (research D-0f: il sync attuale copre il subtree `claude/`;
      verificare se include `assets/rag/hooks/` — se sì, allineare preventivamente).
- [x] Spot check comandi runtime invariati:
      - `sertor install rag --assistant claude` produce gli stessi artefatti pre-esistenti **più** i
        5 nuovi version-check (additivo — nessun artefatto pre-esistente rimosso).
      - `sertor-rag`, `sertor configure`, `sertor-rag doctor`, `sertor-rag index` invariati.
      - `sertor install rag --assistant copilot-cli` deposita script SessionEnd Copilot ma **non**
        lo script SessionStart (solo prompt statico — W5/R-3).
- [x] Verifica che la suite root `tests/unit/test_assets_sync.py` sia verde (guardia sync `claude/`
      pre-esistente non regredita).

### TASK-P03 — Verifica CS-1..6 e criteri di accettazione trasversali

→ dipende da: TASK-P01, TASK-P02

- [x] **CS-1 (avviso corretto):** TASK-F01/F02 implementano il check+avviso; TASK-US6-01 verifica
      le voci SessionEnd/SessionStart nel piano Claude. Il verdetto `behind` → avviso su stdout
      (`version-check-start.ps1`); non-`behind` → no-op (INV-1). Confermato. ✓
- [x] **CS-2 (economico & non bloccante):** TASK-F01 implementa la cache ~24h (INV-4); GET fallita
      → skip silenzioso (INV-2/FR-009); TASK-US9-01 verifica la struttura del try/catch. Confermato. ✓
- [x] **CS-3 (copertura 3 dimensioni):** TASK-F01 legge gli stamp `.sertor/.sertor-version` e
      `.sertor/.sertor-flow-version` (se presente) e popola `dimensions`; TASK-US3-01 scrive lo
      stamp a install-time; TASK-US7-01 verifica la riconferma a upgrade. Confermato. ✓
- [x] **CS-4 (solo avviso):** TASK-F02/F01 non applicano mai un aggiornamento (FR-005); assenza di
      `sertor upgrade` / `uvx --refresh` come **invocazione** (solo come stringa nell'avviso);
      TASK-US9-01 verifica assenza di pattern esecutivi. Confermato. ✓
- [x] **CS-5 (host-agnostico & installabile):** TASK-US6-01/02 verificano deposito Claude e Copilot;
      TASK-US6-02 verifica formato nativo Copilot (R-1/W1); TASK-US8-01 estende la guardia sync
      bundlato↔dogfood (R-5). Confermato. ✓
- [x] **CS-6 (D↔N & privacy):** TASK-US9-01 verifica assenza di `sertor_core`/`python` negli script;
      la GET è del solo `/VERSION` pubblico (FR-015); nessun segreto in `.version-check.json`
      (INV-3). Confermato. ✓
- [x] Verifica che il contratto `contracts/version-check-state.md` (S1..S5/T1..T4) sia rispettato
      dall'implementazione in TASK-F01/F02/US3-01 (schema `version.check/1`, campi obbligatori,
      cache, verdetto, privacy).
- [x] Verifica che il contratto `contracts/version-check-hook-wiring.md` (W1..W6) sia rispettato:
      W1 parità formato → TASK-US6-02; W2 non-bloccante → TASK-F01/F02; W3 isolamento →
      TASK-US6-01; W4 D↔N → TASK-F02; W5 Copilot SessionStart prompt → TASK-US2-01/US6-02;
      W6 zero rete al SessionStart → TASK-F02.
- [x] Segnala come **follow-up non-bloccante**: prova LIVE su ospite Claude e Copilot reale
      (quickstart V1..V10) e verifica `sertor-flow install` per la copertura della dimensione
      governance (FR-012/US6, Could) — il done offline è raggiunto con i task precedenti.

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01 [P]  (settings.version-check.json)           ─────────────────────────────┐
TASK-S02 [P]  (settings.version-check-start.json)     ──────────────────────────┐  │
TASK-F01 [P]  (version-check.ps1)                     ──────────────────────┐   │  │
TASK-F02 [P]  (version-check-start.ps1)               ───────────────────┐  │   │  │
TASK-F03 [P]  (RUNTIME_IGNORES += 3 voci)             ─ [P]              │  │   │  │
                                                                          │  │   │  │
TASK-F04      (dogfood .claude/) ← F01 + F02          ──────────────┐    │  │   │  │
                                                                     │    │  │   │  │
TASK-US1-01 [P] (W1: costanti SessionEnd Copilot)  ← S01, F01      │    │  │   │  │
TASK-US2-01 [P] (W2: costanti SessionStart Copilot) ← S02, F02     │    │  │   │  │
        │                                                            │    │  │   │  │
TASK-US3-01     (W3: build_rag_plan +5 artefatti)  ← US1+US2  ─────┘    │  │   │  │
        │                                                                 │  │   │  │
TASK-US4-01     (W4: dispatch _rag_hook_fragment)  ← US3                 │  │   │  │
        │                                                                 │  │   │  │
TASK-US5-01     (W5: owned_paths + lifecycle)      ← US4                 │  │   │  │
        │                                                                 │  │   │  │
TASK-US7-01 [P] (US7: loop chiusura stamp-upgrade) ← US3   ─── [P]      │  │   │  │
        │                                                                 │  │   │  │
TASK-US6-01 [P] (test Claude: deposito+lifecycle+stamp) ← US5, F01+F02  │  │   │  │
TASK-US6-02 [P] (test Copilot: formato nativo)     ← US5                │  │   │  │
TASK-US8-01     (estende guardia sync rag hooks)   ← F01+F02+F04   ─────┘  │   │  │
TASK-US9-01 [P] (RUNTIME_IGNORES + form script)   ← F03                    │   │  │
        │                                                                    │   │  │
TASK-P01 [P]    (suite verde + lint)               ← tutti            ──────┘   │  │
TASK-P02 [P]    (additività + sync)                ← tutti            ──────────┘  │
        │                                                                           │
TASK-P03        (CS-1..6 trasversali)              ← P01+P02          ─────────────┘
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (avviso a inizio sessione se indietro) | Con `.sertor/.version-check.json` contenente `verdict=behind`, `version-check-start.ps1` emette su stdout l'avviso (installato, ultimo, comando d'aggiornamento); con non-`behind`/assente, nessun output. Piano Claude contiene FILE + SETTINGS_MERGE per entrambe le voci. | TASK-F01, TASK-F02, TASK-US6-01 | MECCANICO |
| **US2** (ultima versione da `/VERSION` remoto) | Lo script contiene una GET all'URL configurabile (assenza di logica commit-SHA); confronto per segmenti numerici; `installed >= latest` ⇒ non avvisa. Verifica testuale: assenza del pattern SHA/git log; presenza di `Invoke-WebRequest`/`Invoke-RestMethod` e split su `.`. | TASK-F01, TASK-US9-01 | TESTUALE+MECCANICO |
| **US3** (al più ~1 chiamata di rete al giorno) | Con `checked_at` entro ~24h e `SERTOR_VERSION_CHECK_FORCE` non impostata, lo script non fa una nuova GET (riusa l'esito — INV-4). Verifica testuale: presenza della logica di lettura cache + condizione su `checked_at`; verifica live: quickstart V1. | TASK-F01 | TESTUALE+MANUALE |
| **US4** (offline/GET fallita → skip silenzioso) | Lo script ha `try/catch` globale → exit 0 anche con GET fallita; stamp assente → `verdict: "unknown"`; SessionStart con `unknown` → no-op (INV-2). Test offline: TASK-US9-01 verifica struttura try/catch; verifica live: quickstart V4. | TASK-F01, TASK-F02, TASK-US9-01 | TESTUALE+MANUALE |
| **US5** (stato persistito sotto `.sertor/`) | Dopo un check, esiste `.sertor/.version-check.json` con schema `version.check/1` (campi obbligatori S1..S5); la voce è in `RUNTIME_IGNORES` (mai versionata). Test: TASK-US9-01 verifica RUNTIME_IGNORES; TASK-US6-01 verifica il piano emette il file di stato (o che il dispatcher lo scrive). | TASK-F01, TASK-US3-01, TASK-F03, TASK-US9-01 | MECCANICO |
| **US6** (copertura 3 dimensioni) | Lo script legge `.sertor/.sertor-version` (e `.sertor/.sertor-flow-version` se presente); `dimensions` nel JSON di stato nomina la versione per dimensione; il piano scrive lo stamp a install-time. Test: TASK-US6-01 verifica scrittura stamp; verifica live dimensione governance: quickstart V7 con sertor-flow. | TASK-F01, TASK-US3-01, TASK-US6-01 | MECCANICO+MANUALE |
| **US7** (loop chiusa dopo upgrade) | `upgrade` riscrive lo stamp con la nuova versione (INV-5); il prossimo SessionEnd confronta nuovo stamp vs `latest` → `up-to-date`; SessionStart → no-op. Test: TASK-US7-01 verifica logica upgrade; verifica live: quickstart V6. | TASK-US5-01, TASK-US7-01 | MECCANICO+MANUALE |
| **US8** (parità Claude/Copilot via installer) | `sertor install rag` Claude: deposita SessionEnd+SessionStart script + entrambe le voci settings + stamp. `sertor install rag` Copilot: deposita SessionEnd script + voce SETTINGS_MERGE SessionEnd formato nativo `version:1` + voce SessionStart prompt statico; **non** deposita `version-check-start.ps1`. Guardia sync: bundlato == dogfood byte-per-byte. | TASK-US6-01, TASK-US6-02, TASK-US8-01 | MECCANICO |
| **US9** (re-check forzato, Could) | Con `$env:SERTOR_VERSION_CHECK_FORCE=1` (o `1`), lo script ignora la cache fresca ed esegue una nuova GET anche con `checked_at` recente. Verifica testuale: presenza del controllo `SERTOR_VERSION_CHECK_FORCE` nella logica cache; verifica live: quickstart V2 con env force. | TASK-F01 | TESTUALE+MANUALE |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 — nessun prerequisito (massima parallelizzazione):**
- TASK-S01 [P] (settings SessionEnd JSON)
- TASK-S02 [P] (settings SessionStart JSON)
- TASK-F01 [P] (script `version-check.ps1`)
- TASK-F02 [P] (script `version-check-start.ps1`)
- TASK-F03 [P] (kit `RUNTIME_IGNORES` +3 voci)

**Sprint 2 — dopo F01+F02 (in parallelo):**
- TASK-F04 (dogfood `.claude/` — dipende da F01+F02)
- TASK-US1-01 [P] (W1 costanti SessionEnd — dipende da S01+F01)
- TASK-US2-01 [P] (W2 costanti SessionStart — dipende da S02+F02)
- TASK-US9-01 [P] (RUNTIME_IGNORES + form script — dipende da F03, può partire qui)

**Sprint 3 — dopo US1+US2 (sequenziale a cascata):**
- TASK-US3-01 (W3 build_rag_plan +5 artefatti — dipende da US1+US2)
- TASK-US4-01 (W4 dispatch Copilot — dipende da US3)
- TASK-US5-01 (W5 lifecycle — dipende da US4)

**Sprint 4 — dopo US3 in parallelo con US4-US5:**
- TASK-US7-01 [P] (loop chiusura stamp-upgrade — dipende da US3, può partire con US4)

**Sprint 5 — dopo US5 (test in parallelo):**
- TASK-US6-01 [P] (test Claude: deposito+lifecycle+stamp)
- TASK-US6-02 [P] (test Copilot: formato nativo)
- TASK-US8-01 (guardia sync estesa — dipende da F01+F02+F04)

**Sprint finale — Polish (in parallelo poi convergenza):**
- TASK-P01 [P] (suite verde + lint)
- TASK-P02 [P] (additività + sync)
- TASK-P03 (CS-1..6 — dopo P01+P02)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E2-FEAT-013 — auto-update version check (avviso aggiornamento)

Fase SpecKit "tasks" completata per specs/077-version-update-check.
23 task in 6 fasi:
  Fase 0 Setup                       : 2 task  [P] (TASK-S01 settings SessionEnd · S02 settings SessionStart)
  Fase 1 Fondazionale                : 4 task  (TASK-F01 [P] script version-check.ps1 ·
                                                F02 [P] script version-check-start.ps1 ·
                                                F03 [P] kit RUNTIME_IGNORES +3 voci ·
                                                F04 dogfood .claude/)
  Fase 2 Storie US1..US5/US8 Instllr: 5 task  (TASK-US1-01 [P] · US2-01 [P] · US3-01 · US4-01 · US5-01
                                                — W1..W5 in install_rag.py + stamp a install-time)
  Fase 3 Storia US7 Loop chiusura    : 1 task  [P] (TASK-US7-01 — stamp riscritto a upgrade, no avviso a vuoto)
  Fase 4 Storie US6/US8/US9 Test     : 4 task  (TASK-US6-01 [P] Claude · US6-02 [P] Copilot ·
                                                 US8-01 guardia sync estesa · US9-01 [P] RUNTIME_IGNORES+form)
  Fase 5 Polish/cross-cutting        : 3 task  (TASK-P01 [P] suite+lint · P02 [P] additività ·
                                                 P03 CS-1..6 trasversali)

Natura: ADDITIVO (harness hook + distribuzione). Nessun codice runtime del core.
sertor-core INVARIATO (Principio XI). Unica modifica al kit: +3 righe RUNTIME_IGNORES (additiva).
Rischi coperti:
  R-1 (CRITICO): formato Copilot generato via render_copilot_hooks — mai asset JSON in formato Claude
      (TASK-US1-01/US2-01/US6-02 — lezione FEAT-011/049).
  R-2: try/catch globale → exit 0 sempre in version-check.ps1 (TASK-F01, FR-009/RNF-2).
  R-3: version-check-start.ps1 NON depositato su Copilot (W5 — solo prompt statico; TASK-US2-01/US6-02).
  R-4: stamp scritto dall'installer in-process (importlib.metadata), mai dall'hook a runtime
      (TASK-US3-01/US6-01 — D-3/Principio XI).
  R-5: guardia sync estende lista esistente in test_rag_freshness_dogfood_sync (DRY, TASK-US8-01).
Copertura: FR-001..018, RNF-1..6, CS-1..6, US1..9.
Test natura: MECCANICO (US1/US5/US6/US7/US8) + TESTUALE (US2/US3/US4/US9) + MANUALE-quickstart (V1..V10).
Out-of-Scope gestiti: granularità per-dimensione (FR-012/Could) e re-check forzato (FR-008/US9/Could)
  inclusi nell'asset come Could tracciati nel backlog E2 (non task separati in questa decomposizione).
Parità dual-target: TASK-US6-02 (formato nativo Copilot) + TASK-US8-01 (sync guardia).
Default rag-freshness/memory-capture/rag-usage/eval-skill invariati (additivo).
Sincronizzazione asset bundlati: TASK-P02 ricorda uv run python -m sertor_installer.sync.
Gemello di E10-FEAT-011 (rag-freshness): stessa disciplina hook, stesso pattern installer.

Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.
Template tasks da 076-enforcement-freschezza-rag (setup-plan.ps1/SKILL.md assenti).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/077-version-update-check/tasks.md` (questo file, nuovo)
