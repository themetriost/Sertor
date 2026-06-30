# Tasks — Portabilità OS hook (guardia `pwsh` + gap dichiarato) + onestà surface inerti (E10-FEAT-018)

**Branch**: `078-portabilita-os-hook` · **Generato**: 2026-06-30
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/install-notes.md`](contracts/install-notes.md) ·
[`contracts/pwsh-guard.md`](contracts/pwsh-guard.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO, host-facing, ZERO codice di core.**
> La feature tocca esclusivamente:
> - 1 modulo Python nuovo nel kit (`host_env.py`, stdlib puro): rilevamento OS + disponibilità `pwsh`;
> - 2 funzioni installer esistenti (`execute_rag_plan` in `install_rag.py`,
>   `execute_plan` in `install_wiki.py`): aggiunta emissione note dopo `_kit_execute_plan`;
> - 3 file di documentazione utente (`docs/install.md`, `docs/install-copilot.md`,
>   `packages/sertor/docs/install.md`): prerequisito `pwsh` + operatività-per-target;
> - 3 nuovi file di test guard (`test_host_env.py`, `test_install_pwsh_guard.py`,
>   `test_install_rag_copilot_memory_note.py`) + estensione `test_non_regression_claude.py`.
>
> `sertor-core` è **INVARIATO**. Schema `install.report/1` **invariato** (additivo: `notes` vuoto
> → JSON byte-identico). Nessun nuovo `ArtifactKind`/`Surface`/`WriteStrategy`/seam del kit.
> Nessuna nuova dipendenza (solo `os`/`shutil` stdlib). Nessun asset `.ps1`/JSON toccato →
> `test_assets_sync.py` verde **per costruzione** (FR-015, nessun byte di asset cambia).
>
> **Vincoli da coprire (calibra l'ordine):**
> - **INV-5 (no falso positivo su Windows):** `maybe_note_pwsh` chiama `is_windows()` prima di
>   tutto — garantisce che il gating su Windows sia il primo short-circuit; i test lo verificano
>   con OS mocking esplicito (`monkeypatch.setattr(host_env, "is_windows", lambda: True)`).
> - **INV-7 (determinismo CI):** la CI gira su Windows → tutti i test del ramo non-Windows usano
>   `monkeypatch.setattr(host_env, ...)` per simulare l'OS; mai dipendenza dall'OS reale.
> - **D-3 (nessuna riscrittura del wiring):** la guardia rileva e segnala, **non** modifica
>   `"shell": "powershell"` né `pwsh -File`; verificare che nessun wiring esistente sia toccato.
> - **A-004 (seam esistente):** `InstallReport.note()` e `notes: list[str]` sono già in
>   `sertor-install-kit/report.py:74,44`; la feature **usa** l'infrastruttura, non la modifica.
>
> **Strategia MVP/incrementale.**
> - **Fondazionale** (TASK-F01): `host_env.py` puro. Prerequisito bloccante per Fase 1 e Fase 4.
>   Può essere scritto e testato in isolamento completo. [P] con tutto il resto tranne US1.
> - **US1-4** (TASK-US1-01/02): wiring guardia pwsh nei due installer. Dipendono da F01.
>   Parallelizzabili tra loro [P]; bloccanti per US5 (stesso file) e per i guard test.
> - **US5** (TASK-US5-01): nota Copilot in `install_rag.py`. Dipende da US1-01 (stesso file,
>   stessa funzione, aggiunta successiva). Sequenziale rispetto a US1-01.
> - **US6** (TASK-US6-01..03): doc utente, indipendenti dal codice; tutti [P] tra loro e con US1-4/US5.
> - **US7** (TASK-US7-01..03): guard tests. Dipendono dai task di implementazione; tutti [P] tra loro.
> - **Polish** (TASK-P01/P02): suite verde totale, CS-check trasversale.
>
> L'ordine di priorità: fondazionale (F01) → guardia pwsh P1 Must (US1-4) → nota Copilot P1 Must
> (US5) → doc P1 Must (US6, in parallelo con US1-4) → guard tests P1 Must (US7) → polish.

---

## Fase 0 — Fondazionale: modulo `host_env.py` (1 task)

> Prerequisiti: nessuno. Puro stdlib, completamente mockabile. Parallelizzabile con US6 [P].
> Bloccante per Fase 1 (US1-4) e Fase 4 (US7-01).

### TASK-F01 [P] — Crea `sertor_install_kit/host_env.py` (modulo puro di rilevamento OS)

**File**: `packages/sertor-install-kit/src/sertor_install_kit/host_env.py` (NUOVO)
→ dipende da: nessuno

**Mappa FR**: FR-001/002/003/004/005/006 · US1/US2/US3/US4 · data-model §1 · contracts/pwsh-guard.md

- [ ] Crea il file `packages/sertor-install-kit/src/sertor_install_kit/host_env.py`.
      Docstring modulo: "Host OS environment helpers for install-time guard checks (E10-FEAT-018).
      All functions are pure stdlib, deterministic, mockable — zero imports of sertor_core or LLMs."
- [ ] Definisci la costante:
      ```python
      PWSH_INSTALL_URL = (
          "https://learn.microsoft.com/powershell/scripting/install/installing-powershell"
      )
      ```
- [ ] Implementa `is_windows() -> bool`:
      ```python
      import os
      def is_windows() -> bool:
          """True on Windows (os.name == 'nt'), False on macOS/Linux."""
          return os.name == "nt"
      ```
      (INV-5: gate primario; mockabile con `monkeypatch.setattr(host_env, "is_windows", ...)`.)
- [ ] Implementa `pwsh_available() -> bool`:
      ```python
      import shutil
      def pwsh_available() -> bool:
          """True if 'pwsh' (PowerShell Core) is found in PATH. Binary: no version check (NFR-4)."""
          return shutil.which("pwsh") is not None
      ```
      (INV-4: check binario, nessun hardcoding di distro; mockabile.)
- [ ] Implementa `pwsh_unavailability_note(hook_surfaces: Sequence[str]) -> str` (builder **puro**):
      - Firma: `from collections.abc import Sequence` (stdlib);
      - Corpo: costruisce una stringa che (A1) menziona `pwsh` e PowerShell Core; (A2) include
        `PWSH_INSTALL_URL`; (A3) elenca le `hook_surfaces` affette (almeno un path `.ps1`);
        (A4) contiene la frase esplicita che quei surface sono «installed but non-operational».
      - Esempio di forma (non vincolante alla virgola):
        `"pwsh (PowerShell Core) was not found on this non-Windows host: the deposited hooks
        (<surfaces>) are installed but non-operational until you install it — <URL>"`.
      - Nessun side-effect; non chiama `is_windows` né `pwsh_available`.
- [ ] Implementa `maybe_note_pwsh(report: InstallReport, hook_surfaces: Sequence[str]) -> None`:
      - Import: `from sertor_install_kit.report import InstallReport` (dipendenza interna kit, ok).
      - Corpo: gating triplo `(not is_windows()) and (not pwsh_available()) and hook_surfaces`:
        se vero → `report.note(pwsh_unavailability_note(hook_surfaces))`; altrimenti **no-op**.
      - La funzione **mai solleva** (INV-1): il `report.note()` è già idempotente e non-fatale.
      - È l'unico entry-point chiamato dai consumatori (`execute_rag_plan`, `execute_plan` wiki).
- [ ] Esporta le funzioni e la costante in `__init__.py` del kit (se la convenzione del kit
      esporta tutto dal top-level); oppure lascia come modulo esplicito `host_env` — verifica la
      convenzione guardando `packages/sertor-install-kit/src/sertor_install_kit/__init__.py`.
- [ ] Verifica che il file non importi nulla di `sertor_core` (RNF-2/Principio XI): solo
      `os`, `shutil`, `collections.abc.Sequence` e `sertor_install_kit.report.InstallReport`.
- [ ] Verifica che `maybe_note_pwsh` invochi `is_windows()` e `pwsh_available()` come **globali
      del modulo** (non parametri) → i test patchano `host_env.is_windows`/`host_env.pwsh_available`
      direttamente (R-6/INV-7 — CI Windows simula il ramo non-Windows).

---

## Fase 1 — Storie US1/US2/US3/US4 — guardia `pwsh` nell'installer (2 task)

> Prerequisiti: TASK-F01. I 2 task sono indipendenti tra loro [P].
> Bloccanti per TASK-US5-01 (stesso file `install_rag.py`) e per i guard test US7-02/03.
>
> **Convenzione comune a entrambi i task:**
> 1. Il seam è **dopo** la chiamata a `_kit_execute_plan` che ritorna il `report`.
> 2. Derivare `hook_surfaces` dal piano già costruito (dichiarativo, non hardcoded):
>    ```python
>    hook_surfaces = [a.target_rel for a in plan if a.target_rel.endswith(".ps1")]
>    ```
> 3. Chiamare `maybe_note_pwsh(report, hook_surfaces)` subito dopo la derivazione.
> 4. Aggiungere l'import: `from sertor_install_kit import host_env` (o il percorso equivalente).
> 5. **Non** modificare il wiring Claude `"shell": "powershell"` né Copilot `pwsh -File`
>    (INV-3/D-3 — la guardia rileva e segnala, non riscrive il wiring).
> 6. La CLI (`_cmd_install_rag`/`_cmd_install_wiki`) resta **thin** — nessuna modifica.

### TASK-US1-01 [P] — Wiring guardia `pwsh` in `install_rag.py::execute_rag_plan`

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-F01

**Mappa FR**: FR-001/002/003/004/005/006 · CS-1/CS-2/CS-3 · US1/US2/US3/US4

- [ ] Apri `packages/sertor/src/sertor_installer/install_rag.py`.
      Individua la funzione `execute_rag_plan` (riga ~735). Verifica che la struttura corrente sia:
      ```python
      def execute_rag_plan(plan, profile, runner, assistant=...) -> InstallReport:
          apply = make_rag_apply(profile, runner, assistant)
          report = _kit_execute_plan(plan, apply, target=..., capability="rag", assistant=...)
          return report
      ```
- [ ] Aggiungi l'import (se non già presente): `from sertor_install_kit import host_env`
      (oppure `from sertor_install_kit.host_env import maybe_note_pwsh` — verifica la convenzione
      del progetto guardando gli import esistenti in `install_rag.py`).
- [ ] Dopo `report = _kit_execute_plan(...)` e **prima** di `return report`, inserisci:
      ```python
      hook_surfaces = [a.target_rel for a in plan if a.target_rel.endswith(".ps1")]
      host_env.maybe_note_pwsh(report, hook_surfaces)
      ```
      (Il piano è già costruito e passato a `execute_rag_plan`; la derivazione è dichiarativa.)
- [ ] Aggiorna il commento stale che descrive lo stato della nota `memory-capture` (piano §Phase 1,
      punto 2): la riga a `:146-148` che dice `«INERT until adapter exists»` va corretta —
      l'adapter Copilot esiste (E5-FEAT-008, 2026-06-22) ma l'installer non distribuisce il valore
      (`SERTOR_MEMORY_ADAPTER=copilot-cli`), che è FEAT-009 memorie. Aggiorna il commento di conseguenza.
- [ ] Verifica che `maybe_note_pwsh` sia chiamata **dopo** `_kit_execute_plan` e **prima** di
      `return report` (seam corretto — research §Ancoraggio).
- [ ] Spot check manuale: su Windows CI, `is_windows()` reale ritorna `True` → `maybe_note_pwsh` è
      no-op → `report.notes` non accumula la nota pwsh → comportamento invariato (US3/CS-3).
- [ ] Verifica che nessun import di `sertor_core` sia aggiunto (RNF-2/Principio XI).

### TASK-US1-02 [P] — Wiring guardia `pwsh` in `install_wiki.py::execute_plan`

**File**: `packages/sertor/src/sertor_installer/install_wiki.py` (MODIFICA)
→ dipende da: TASK-F01

**Mappa FR**: FR-001/002/003/004/005/006 · CS-1/CS-2/CS-3 · US1/US2/US3/US4

- [ ] Apri `packages/sertor/src/sertor_installer/install_wiki.py`.
      Individua la funzione `execute_plan` (riga ~380). Verifica la struttura corrente:
      ```python
      def execute_plan(plan, profile, assistant=...) -> InstallReport:
          root = profile.target_root
          apply = make_wiki_apply(profile, assistant)
          report = _kit_execute_plan(plan, apply, target=str(root), capability="wiki", ...)
          return report
      ```
- [ ] Aggiungi l'import (se non già presente): `from sertor_install_kit import host_env`
      (o la forma equivalente usata in `install_rag.py` — uniforma lo stile).
- [ ] Dopo `report = _kit_execute_plan(...)` e **prima** di `return report`, inserisci:
      ```python
      hook_surfaces = [a.target_rel for a in plan if a.target_rel.endswith(".ps1")]
      host_env.maybe_note_pwsh(report, hook_surfaces)
      ```
- [ ] Verifica che su un piano wiki `AssistantId.CLAUDE` la lista `hook_surfaces` contenga
      almeno `.claude/hooks/wiki-pending-check.ps1` (il plan deposita quell'hook — data-model §2).
      Se nessun piano wiki deposita hook (edge: piano vuoto), `hook_surfaces == []` → `maybe_note_pwsh`
      è no-op per costruzione (guard clause in `maybe_note_pwsh`).
- [ ] Verifica che `test_claude_report_has_no_gap_note` in
      `packages/sertor/tests/test_install_wiki_copilot_cli.py:192` resti verde senza modifiche:
      su CI Windows `is_windows()` reale è `True` → la guardia è no-op → `report.notes == []`.
      Non modificare quel test (è la non-regressione naturale su CI Windows).
- [ ] Verifica che nessun import di `sertor_core` sia aggiunto (RNF-2/Principio XI).

---

## Fase 2 — Storia US5 — nota `memory-capture` su Copilot CLI (1 task)

> Prerequisiti: TASK-US1-01 (stesso file `install_rag.py`, stessa funzione `execute_rag_plan`).
> Bloccante per TASK-US7-03 (guard test nota Copilot).
>
> La nota è **sempre** emessa su `--assistant copilot-cli` (decisione D-2: anticipatoria,
> default-state visibility, indipendente da `SERTOR_MEMORY`). Vive in `install_rag.py`
> (rag-specifica, single consumer — YAGNI III). **Non** va nel kit.

### TASK-US5-01 — Nota `memory-capture` Copilot CLI in `install_rag.py::execute_rag_plan`

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-US1-01

**Mappa FR**: FR-007/008/009 · CS-4 · US5 · contracts/install-notes.md §Nota B

- [ ] Apri `packages/sertor/src/sertor_installer/install_rag.py`.
      Verifica che TASK-US1-01 sia già stato applicato (la guardia pwsh è nel seam).
- [ ] Definisci una costante a livello di modulo per il testo della nota `memory-capture`
      (stabile, substringhe B1/B2/B3/B4 dal contratto `contracts/install-notes.md §Nota B`):
      ```python
      _COPILOT_MEMORY_NOTE = (
          "memory-capture is wired but requires SERTOR_MEMORY=true and an explicit Copilot adapter "
          "value for SERTOR_MEMORY_ADAPTER to capture Copilot CLI sessions — with the default "
          "the hook fires but captures nothing useful. Out-of-the-box completion is planned "
          "(distribution of the adapter value in the .env template, tracked in the "
          "memory-conversations epic / FEAT-009)."
      )
      ```
      La costante deve contenere tutte e 4 le substringhe stabili: (B1) `"memory-capture"`,
      (B2) `"SERTOR_MEMORY"` e `"SERTOR_MEMORY_ADAPTER"`, (B3) la dichiarazione esplicita di
      «captures nothing useful», (B4) il riferimento alla capacità pianificata (FEAT-009).
- [ ] In `execute_rag_plan`, **dopo** `host_env.maybe_note_pwsh(report, hook_surfaces)` e
      **prima** di `return report`, aggiungi:
      ```python
      if assistant is AssistantId.COPILOT_CLI:
          report.note(_COPILOT_MEMORY_NOTE)
      ```
      (Verifica che `AssistantId` sia già importato nel file — è usato nella firma della funzione.)
- [ ] Verifica che la nota **non** sia emessa su `AssistantId.CLAUDE` (FR-009/CS-3):
      la condizione `if assistant is AssistantId.COPILOT_CLI` garantisce l'isolamento.
- [ ] Verifica che la nota **non** sia emessa su install wiki (questa modifica è solo in
      `install_rag.py` — `install_wiki.py` non ha la nota Copilot, corretto).
- [ ] Verifica che la nota sia emessa **sempre** su Copilot CLI rag, indipendente dal valore
      runtime di `SERTOR_MEMORY` (decisione D-2 — la costante non legge env a runtime).
- [ ] Spot check substringhe stabili nella costante `_COPILOT_MEMORY_NOTE`:
      - [ ] `"memory-capture"` presente (B1)
      - [ ] `"SERTOR_MEMORY"` presente (B2a)
      - [ ] `"SERTOR_MEMORY_ADAPTER"` presente (B2b)
      - [ ] `"captures nothing useful"` o equivalente esplicito presente (B3)
      - [ ] riferimento a FEAT-009 / capacità pianificata presente (B4)

---

## Fase 3 — Storia US6 — documentazione utente (3 task)

> Prerequisiti: nessuno (la doc è indipendente dal codice e parallelizzabile con le Fasi 0-2).
> I 3 task sono parallelizzabili tra loro [P].
> Bloccanti per TASK-P02 (CS-5).
>
> **Convenzione comune:** dichiarare onestamente il prerequisito, non inventare operatività
> piena. Il limite tecnico del wiring Claude `"shell": "powershell"` su non-Windows (D-3) va
> dichiarato nella sezione operatività-per-target; NON affermare che installare `pwsh` garantisce
> operatività completa su Claude/non-Windows (l'incertezza su `shell` semantics è reale).

### TASK-US6-01 [P] — `docs/install.md` — prerequisito `pwsh` + operatività-per-target

**File**: `docs/install.md` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-010/012 · CS-5 · US6-AC1/AC3

- [ ] Apri `docs/install.md`. Individua la sezione Prerequisiti (§5 o §6 del documento,
      dipende dalla struttura attuale — cerca la sezione che elenca i requisiti di sistema).
- [ ] Aggiungi **`pwsh` come prerequisito su macOS/Linux** per il funzionamento dei surface hook:
      - Voce da aggiungere ai prerequisiti: «`pwsh` (PowerShell Core) — richiesto su macOS/Linux
        per il funzionamento degli hook di lifecycle distribuiti da `sertor install`. Su Windows è
        già presente tramite PowerShell 5.1; su macOS/Linux va installato separatamente.»
      - URL: `https://learn.microsoft.com/powershell/scripting/install/installing-powershell`.
      - Elenco dei surface hook affetti (i `.ps1` distribuiti dall'installer: `rag-freshness.ps1`,
        `rag-freshness-start.ps1`, `version-check.ps1`, `version-check-start.ps1`,
        `memory-capture.ps1`, `sertor-rag-usage-check.ps1`, `wiki-pending-check.ps1`).
      - Frase esplicita: «Senza `pwsh`, questi surface sono installati ma non-operativi.»
        (substringa A4 del contratto).
- [ ] Aggiungi (o aggiorna) la sezione §10.1 (o sezione esistente sull'upgrade/setup) con un
      riferimento al prerequisito `pwsh` per gli host non-Windows.
- [ ] Aggiungi una **sezione (o tabella) «Operatività per target»** che dichiari, per ogni
      target supportato, quali surface sono pienamente operativi dopo `sertor install` e quali
      richiedono configurazione manuale aggiuntiva (FR-012):

      | Target | Surface pienamente operativi | Richiedono configurazione |
      |---|---|---|
      | Claude su Windows | MCP, blocco CLAUDE.md, hook `.ps1` (via `powershell`), skill, agent | — |
      | Copilot CLI su qualsiasi OS | MCP, blocco istruzioni, skill, agent | Hook: richiedono `pwsh` su macOS/Linux; `memory-capture`: richiede `SERTOR_MEMORY=true` + `SERTOR_MEMORY_ADAPTER=copilot-cli` |
      | Claude su macOS/Linux | MCP, blocco CLAUDE.md, skill, agent | Hook: richiedono `pwsh`; operatività hook Claude/non-Windows può dipendere dalla semantica `shell` del client (verifica in corso) |

      (Adatta la tabella alla struttura esistente del documento; mantieni tono onesto su Claude/non-Windows.)
- [ ] Verifica che il documento dichiari esplicitamente che senza `pwsh` i surface hook
      sono **installati ma non-operativi** (substringa A4 — verificabile in test manuale US6).

### TASK-US6-02 [P] — `docs/install-copilot.md` — prerequisito `pwsh` + adapter `memory-capture`

**File**: `docs/install-copilot.md` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-011 · CS-5 · US6-AC2

- [ ] Apri `docs/install-copilot.md`. Individua la sezione §1 o la sezione di prerequisiti
      del percorso Copilot CLI.
- [ ] Aggiungi la dichiarazione **`pwsh` richiesto per gli hook su macOS/Linux** (FR-011a):
      - Voce: «`pwsh` (PowerShell Core) è richiesto su macOS/Linux per il funzionamento degli
        hook di lifecycle distribuiti da `sertor install rag`/`wiki` su Copilot CLI. Su macOS/Linux
        senza `pwsh`, gli hook sono installati ma non vengono eseguiti.»
      - URL: `https://learn.microsoft.com/powershell/scripting/install/installing-powershell`.
- [ ] Aggiungi la dichiarazione **`memory-capture` richiede configurazione adapter** (FR-011b):
      - Sezione dedicata (o nota prominente): «`memory-capture` — configurazione richiesta per
        catturare sessioni Copilot CLI. L'hook viene distribuito e cablato, ma per catturare
        le sessioni Copilot CLI è necessario impostare esplicitamente:
        ```
        SERTOR_MEMORY=true
        SERTOR_MEMORY_ADAPTER=copilot-cli
        ```
        Con i valori di default, l'hook scatta ma non cattura nulla di utile. Il completamento
        out-of-the-box (distribuzione automatica di `copilot-cli` nel template `.env`) è
        pianificato nell'epica memoria-conversazioni.»
- [ ] Verifica che il documento dichiari entrambe le condizioni: (a) pwsh richiesto su mac/Linux
      + (b) configurazione adapter esplicita per `memory-capture` (US6-AC2).

### TASK-US6-03 [P] — `packages/sertor/docs/install.md` — tabella capability + note operatività

**File**: `packages/sertor/docs/install.md` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-012 · CS-5 · research D-2 (tabella capability)

- [ ] Apri `packages/sertor/docs/install.md`. Individua la tabella capability (quella che elenca
      le surface distribuite da `sertor install rag`/`wiki`).
- [ ] Aggiungi una **colonna «Operatività / Note»** alla tabella (o una sezione di note sotto),
      che annoti per ogni surface rilevante:
      - Hook (`.ps1`): «Richiedono `pwsh` su macOS/Linux. Su Windows: operativi via
        `powershell` (Claude) o `pwsh` (Copilot CLI).»
      - `memory-capture` (Copilot CLI): «Richiede `SERTOR_MEMORY=true` + esplicito
        `SERTOR_MEMORY_ADAPTER=copilot-cli` per catturare sessioni Copilot CLI.»
      - MCP, blocco istruzioni, skill, agent: «Operativi su tutti gli OS e target
        (non dipendono da `pwsh`).»
- [ ] Aggiungi (o aggiorna) una nota a piè di tabella con il link a `docs/install.md` §pwsh
      e `docs/install-copilot.md` per i dettagli di configurazione.
- [ ] Verifica che la tabella non affermi «parità piena» per target/OS in cui l'operatività
      è condizionale — usa frasi come «operativo con `pwsh`» o «richiede configurazione».

---

## Fase 4 — Storia US7 — guard tests (3 task)

> Prerequisiti: TASK-F01 (per US7-01); TASK-US1-01/02 (per US7-02); TASK-US5-01 (per US7-03).
> I 3 task sono parallelizzabili tra loro [P] (file distinti, nessuna dipendenza reciproca).
> I test possono essere **scritti** prima che le implementazioni siano complete; diventeranno
> verdi solo dopo le Fasi 0-2. Bloccanti per TASK-P01.
>
> **Convenzione comune a tutti i test:**
> - OS mocking via `monkeypatch.setattr(host_env, "is_windows", lambda: True/False)` e
>   `monkeypatch.setattr(host_env, "pwsh_available", lambda: True/False)`.
> - Import `import sertor_install_kit.host_env as host_env` in cima al file.
> - Nessun `uv run`, nessun cloud, nessun processo reale — offline puri (INV-7/R-6).
> - Marker: nessun `@pytest.mark.cloud`; solo test standard veloci.

### TASK-US7-01 [P] — `test_host_env.py`: test builder puri e gating (kit)

**File**: `packages/sertor-install-kit/tests/unit/test_host_env.py` (NUOVO)
→ dipende da: TASK-F01

**Mappa FR**: FR-001/004/006 · CS-6 · US7-AC1/AC3 · data-model §1 · contracts/pwsh-guard.md

- [ ] Crea `packages/sertor-install-kit/tests/unit/test_host_env.py`.
- [ ] Verifica che la directory `packages/sertor-install-kit/tests/unit/` esista (analoga a
      `packages/sertor/tests/unit/`); creala se assente.
- [ ] **Test T1 — `pwsh_unavailability_note` (builder puro, substringhe stabili):**
      ```python
      from sertor_install_kit import host_env

      def test_pwsh_unavailability_note_contains_required_substrings():
          surfaces = [".github/hooks/rag-freshness.ps1", ".github/hooks/memory-capture.ps1"]
          note = host_env.pwsh_unavailability_note(surfaces)
          assert "pwsh" in note                             # A1: menziona pwsh
          assert "learn.microsoft.com/powershell" in note  # A2: URL rimediazione
          assert ".ps1" in note                             # A3: surface affetti
          assert "non-operational" in note or "not-operational" in note  # A4: stato esplicito
      ```
- [ ] **Test T2 — `maybe_note_pwsh` tabella di verità (4 righe di contracts/pwsh-guard.md):**
      Usa un report mock (o `InstallReport` reale con `tmp_path`).
      ```python
      from sertor_install_kit.report import InstallReport

      def _make_report(tmp_path):
          return InstallReport(target=str(tmp_path), capability="rag")

      def test_maybe_note_pwsh_emits_on_non_windows_no_pwsh(monkeypatch, tmp_path):
          """Riga 1 della tabella: non-Windows, pwsh assente, hook depositati → Nota A."""
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
          report = _make_report(tmp_path)
          host_env.maybe_note_pwsh(report, [".github/hooks/rag-freshness.ps1"])
          assert len(report.notes) == 1
          assert "pwsh" in report.notes[0]

      def test_maybe_note_pwsh_no_note_if_pwsh_present(monkeypatch, tmp_path):
          """Riga 2: non-Windows, pwsh presente → nessuna nota."""
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: True)
          report = _make_report(tmp_path)
          host_env.maybe_note_pwsh(report, [".github/hooks/rag-freshness.ps1"])
          assert report.notes == []

      def test_maybe_note_pwsh_no_note_on_windows(monkeypatch, tmp_path):
          """Riga 3: Windows → nessuna nota (INV-5, no falso positivo)."""
          monkeypatch.setattr(host_env, "is_windows", lambda: True)
          # pwsh_available non viene chiamata su Windows — no patch necessaria
          report = _make_report(tmp_path)
          host_env.maybe_note_pwsh(report, [".claude/hooks/rag-freshness.ps1"])
          assert report.notes == []

      def test_maybe_note_pwsh_no_note_if_no_hooks(monkeypatch, tmp_path):
          """Riga 4 (edge): nessun hook nel piano → nessuna nota (no-op)."""
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
          report = _make_report(tmp_path)
          host_env.maybe_note_pwsh(report, [])  # nessun hook
          assert report.notes == []
      ```
- [ ] **Test T3 — `maybe_note_pwsh` non-fatale (INV-1):**
      ```python
      def test_maybe_note_pwsh_does_not_raise(monkeypatch, tmp_path):
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
          report = _make_report(tmp_path)
          host_env.maybe_note_pwsh(report, [".github/hooks/rag-freshness.ps1"])
          assert report.exit_code() == 0  # INV-1: non-fatale, exit_code invariato
      ```
- [ ] **Test T4 — idempotenza (`.note()` deduplica):**
      ```python
      def test_maybe_note_pwsh_idempotent(monkeypatch, tmp_path):
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
          report = _make_report(tmp_path)
          surfaces = [".github/hooks/rag-freshness.ps1"]
          host_env.maybe_note_pwsh(report, surfaces)
          host_env.maybe_note_pwsh(report, surfaces)  # seconda chiamata → no-op
          assert len(report.notes) == 1  # nessun duplicato
      ```
- [ ] Verifica che tutti i test siano offline (nessun subprocess, nessuna rete).

### TASK-US7-02 [P] — `test_install_pwsh_guard.py`: guardia nota pwsh su rag e wiki (+ NR Claude)

**File**: `packages/sertor/tests/test_install_pwsh_guard.py` (NUOVO)
→ dipende da: TASK-US1-01, TASK-US1-02

**Mappa FR**: FR-001/002/003/004/005/006 · CS-1/CS-2/CS-3/CS-6 · US1/US2/US3/US4/US7 ·
contracts/install-notes.md §Nota A · contracts/pwsh-guard.md

> Modello: `test_non_regression_claude.py` (struttura fixture, `build_rag_plan`/`execute_rag_plan`,
> `FakeCommandRunner` via `make_runner` conftest). Usa i conftest esistenti.

- [ ] Crea `packages/sertor/tests/test_install_pwsh_guard.py`.
      Import necessari:
      ```python
      import json
      import sertor_install_kit.host_env as host_env
      from pathlib import Path
      from sertor_install_kit.assistant import AssistantId
      from sertor_installer.config_gen import build_host_profile
      from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
      from sertor_installer.install_wiki import build_install_plan, execute_plan
      from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
      ```
- [ ] **Test G1 — nota A presente: non-Windows senza pwsh, install rag Claude (US1/CS-1):**
      ```python
      def test_rag_install_emits_pwsh_note_on_non_windows_no_pwsh(
              monkeypatch, tmp_path, make_runner):
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
          options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          profile = RagHostProfile.from_options(options)
          plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
          report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
          assert any("pwsh" in n for n in report.notes)                        # A1
          assert any("learn.microsoft.com/powershell" in n for n in report.notes)  # A2
          assert any(".ps1" in n for n in report.notes)                        # A3
          assert report.exit_code() == 0                                       # non-fatale (FR-005)
          # nota presente anche in JSON (FR-003)
          payload = json.loads(report.render_json())
          assert "notes" in payload
          assert any("pwsh" in n for n in payload["notes"])
      ```
- [ ] **Test G2 — nota A assente: non-Windows con pwsh (US2/CS-2), install rag:**
      ```python
      def test_rag_install_no_pwsh_note_when_pwsh_present(monkeypatch, tmp_path, make_runner):
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: True)
          options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          profile = RagHostProfile.from_options(options)
          plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
          report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
          assert not any("pwsh" in n and "non-operational" in n for n in report.notes)
      ```
- [ ] **Test G3 — nota A presente: non-Windows senza pwsh, install wiki Claude (US1/CS-1):**
      ```python
      def test_wiki_install_emits_pwsh_note_on_non_windows_no_pwsh(monkeypatch, tmp_path):
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
          profile = build_host_profile(tmp_path)
          plan = build_install_plan(AssistantId.CLAUDE)
          report = execute_plan(plan, profile, AssistantId.CLAUDE)
          assert any("pwsh" in n for n in report.notes)   # A1
          assert report.exit_code() == 0                   # non-fatale (FR-005)
      ```
- [ ] **Test G4 — non-regressione Claude+Windows (US3/CS-3), install rag (estende NR esistente):**
      ```python
      def test_rag_claude_windows_no_notes(monkeypatch, tmp_path, make_runner):
          """NR: report.notes == [] su Windows + Claude (INV-5)."""
          monkeypatch.setattr(host_env, "is_windows", lambda: True)
          options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          profile = RagHostProfile.from_options(options)
          plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
          report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
          # solo nota pwsh assente; nota Copilot non deve comparire su Claude
          assert not any("pwsh" in n and "non-operational" in n for n in report.notes)
      ```
      Nota: se TASK-US5-01 è già applicato, verifica anche `assert not any("memory-capture" in n
      for n in report.notes)` (FR-009 — nessuna nota Copilot su Claude).
- [ ] **Test G5 — non-regressione Claude+Windows (US3/CS-3), install wiki (preserva esistente):**
      ```python
      def test_wiki_claude_windows_no_notes(monkeypatch, tmp_path):
          """NR: test_claude_report_has_no_gap_note (test_install_wiki_copilot_cli.py:192)."""
          monkeypatch.setattr(host_env, "is_windows", lambda: True)
          profile = build_host_profile(tmp_path)
          plan = build_install_plan(AssistantId.CLAUDE)
          report = execute_plan(plan, profile, AssistantId.CLAUDE)
          assert report.notes == []   # invariata (CS-3)
      ```
      Verificare che il test esistente `test_claude_report_has_no_gap_note` (test_install_wiki_copilot_cli.py:192)
      resti ancora verde (non toccarlo — il nuovo test G5 è la versione con OS mocking esplicito,
      che è più robusta; entrambi devono passare).
- [ ] Aggiunge `assert report.notes == []` al test `test_claude_rag_artifacts_unchanged` in
      `packages/sertor/tests/test_non_regression_claude.py` (estensione della NR esistente):
      questo test gira su CI Windows reale → `is_windows()` è `True` → la guardia è no-op →
      `report.notes == []` naturalmente. Aggiungere l'assert rende la NR esplicita.
- [ ] Verifica che tutti i test siano offline (no subprocess, no cloud), deterministici (INV-7).

### TASK-US7-03 [P] — `test_install_rag_copilot_memory_note.py`: guardia nota Copilot (US5)

**File**: `packages/sertor/tests/test_install_rag_copilot_memory_note.py` (NUOVO)
→ dipende da: TASK-US5-01

**Mappa FR**: FR-007/008/009 · CS-4/CS-6 · US5/US7 · contracts/install-notes.md §Nota B

- [ ] Crea `packages/sertor/tests/test_install_rag_copilot_memory_note.py`.
      Import necessari (analoghi a TASK-US7-02):
      ```python
      import sertor_install_kit.host_env as host_env
      from pathlib import Path
      from sertor_install_kit.assistant import AssistantId
      from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
      from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
      ```
- [ ] **Test M1 — nota B presente su install rag Copilot CLI (US5/CS-4):**
      ```python
      def test_rag_copilot_cli_emits_memory_note(monkeypatch, tmp_path, make_runner):
          """Nota B presente sempre su Copilot CLI, indipendente da OS e SERTOR_MEMORY."""
          monkeypatch.setattr(host_env, "is_windows", lambda: True)  # OS irrilevante per B
          options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          profile = RagHostProfile.from_options(options)
          plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
          report = execute_rag_plan(plan, profile, make_runner(), AssistantId.COPILOT_CLI)
          # substringhe stabili (B1/B2/B3/B4)
          assert any("memory-capture" in n for n in report.notes)            # B1
          assert any("SERTOR_MEMORY_ADAPTER" in n for n in report.notes)     # B2
          assert any("SERTOR_MEMORY" in n for n in report.notes)             # B2
          # B3: "nothing useful" o equivalente esplicito
          assert any("nothing useful" in n or "not capture" in n for n in report.notes)
          # B4: riferimento alla capacità pianificata
          assert any("FEAT-009" in n or "planned" in n or "memory-conversations" in n
                     for n in report.notes)
      ```
- [ ] **Test M2 — nota B assente su install rag Claude+Windows (FR-009/CS-3):**
      ```python
      def test_rag_claude_no_memory_note(monkeypatch, tmp_path, make_runner):
          monkeypatch.setattr(host_env, "is_windows", lambda: True)
          options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          profile = RagHostProfile.from_options(options)
          plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
          report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
          assert not any("memory-capture" in n for n in report.notes)  # FR-009
      ```
- [ ] **Test M3 — nota B presente anche con non-Windows senza pwsh (indipendenza, D-2):**
      ```python
      def test_rag_copilot_cli_memory_note_independent_of_os(monkeypatch, tmp_path, make_runner):
          """La nota Copilot è emessa anche con pwsh assente (le due note coesistono)."""
          monkeypatch.setattr(host_env, "is_windows", lambda: False)
          monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
          options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          profile = RagHostProfile.from_options(options)
          plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
          report = execute_rag_plan(plan, profile, make_runner(), AssistantId.COPILOT_CLI)
          # entrambe le note presenti
          assert any("pwsh" in n for n in report.notes)             # Nota A
          assert any("memory-capture" in n for n in report.notes)   # Nota B
          assert report.exit_code() == 0                             # non-fatale
      ```
- [ ] Verifica che tutti i test siano offline, deterministici, nessun cloud.

---

## Fase 5 — Polish e cross-cutting (2 task)

> Prerequisiti: tutte le Fasi 0–4 complete. TASK-P01 [P] (non dipende da altri polish).
> TASK-P02 dipende da TASK-P01.

### TASK-P01 [P] — Suite verde totale + lint ruff

→ dipende da: tutte le Fasi 0-4

- [ ] **Guardie nuove (FR-013/014):**
      ```powershell
      uv run pytest packages/sertor-install-kit/tests/unit/test_host_env.py -v
      uv run pytest packages/sertor/tests/test_install_pwsh_guard.py -v
      uv run pytest packages/sertor/tests/test_install_rag_copilot_memory_note.py -v
      ```
      Tutti devono essere verdi (T1-T4, G1-G5, M1-M3 e tutte le estensioni NR).
- [ ] **Non-regressione Claude (FR-009/CS-3):**
      ```powershell
      uv run pytest packages/sertor/tests/test_non_regression_claude.py -v
      uv run pytest packages/sertor/tests/test_install_wiki_copilot_cli.py -v
      ```
      Il test `test_claude_report_has_no_gap_note` deve restare verde (NR su CI Windows).
- [ ] **Sync dogfood (FR-015/CS-6):** verifica che `test_assets_sync.py` resti verde
      per costruzione (la feature non tocca alcun asset `.ps1`/JSON sotto `assets/`):
      ```powershell
      uv run pytest tests/unit/test_assets_sync.py -v
      ```
- [ ] **Suite completa del kit (non-regressione kit):**
      ```powershell
      uv run pytest packages/sertor-install-kit/tests/ -m "not cloud" -v
      ```
- [ ] **Suite completa sertor (non-regressione installer):**
      ```powershell
      uv run pytest packages/sertor/tests/ -m "not cloud" -v
      ```
      Verifica che i test di parità Copilot (`test_assets_copilot_parity.py`,
      `test_surface_parity.py`) restino verdi (la feature non tocca asset body).
- [ ] **Lint ruff sui nuovi file Python:**
      ```powershell
      uv run ruff check `
          packages/sertor-install-kit/src/sertor_install_kit/host_env.py `
          packages/sertor-install-kit/tests/unit/test_host_env.py `
          packages/sertor/src/sertor_installer/install_rag.py `
          packages/sertor/src/sertor_installer/install_wiki.py `
          packages/sertor/tests/test_install_pwsh_guard.py `
          packages/sertor/tests/test_install_rag_copilot_memory_note.py
      ```
      Zero errori (regole E,F,I,UP,B; line-length 100).
- [ ] **Quickstart rapido (verifica manuale CS-1..CS-4):**
      ```powershell
      # CS-1: nota A su non-Windows senza pwsh (richiede monkeypatch — vedi quickstart §1)
      # CS-4: nota B su Copilot CLI (richiede monkeypatch — vedi quickstart §4)
      # CS-5: leggere docs/install.md e docs/install-copilot.md (verifica manuale)
      ```

### TASK-P02 — Verifica CS-1..6 e additività trasversale

→ dipende da: TASK-P01

- [ ] **CS-1 (gap `pwsh` dichiarato, non nascosto):** test G1 (rag, non-Windows, no pwsh → nota A)
      e test G3 (wiki, non-Windows, no pwsh → nota A) verdi; nota contiene substringhe A1/A2/A3/A4;
      exit_code == 0 (non-fatale). ✓
- [ ] **CS-2 (nessun falso allarme con `pwsh`):** test G2 (rag con pwsh) verde; nessuna nota A
      emessa. ✓
- [ ] **CS-3 (non-regressione Claude+Windows):** test G4/G5 (OS mocking Windows, Claude) e
      test `test_claude_report_has_no_gap_note` (NR esistente) verdi; `report.notes == []`
      sia per rag che per wiki. Nessun nuovo artefatto, nessun cambio di wiring. ✓
- [ ] **CS-4 (onestà `memory-capture` Copilot):** test M1 verde; nota B contiene B1/B2/B3/B4;
      test M2 verde (nota B assente su Claude). ✓
- [ ] **CS-5 (documentazione utente onesta):** verifica manuale `docs/install.md` (pwsh prerequisito
      + URL + elenco surface + «installati ma non-operativi» + tabella operatività-per-target) e
      `docs/install-copilot.md` (pwsh richiesto per hook + configurazione adapter `memory-capture`).
      `packages/sertor/docs/install.md`: colonna operatività/note aggiornata in tabella capability. ✓
- [ ] **CS-6 (guardie deterministiche):** test T1-T4 (host_env puro), G1-G5 (nota pwsh rag+wiki),
      M1-M3 (nota Copilot), `test_assets_sync.py` (sync invariato) tutti verdi; tutti usano OS
      mocking, nessuna dipendenza dall'OS reale di CI. ✓
- [ ] **Additività core — invarianza `sertor_core`:** verifica che nessun file in `src/sertor_core/`
      sia stato modificato. Nessun import di `sertor_core` in `host_env.py`, `install_rag.py` (nuovo
      import) né `install_wiki.py` (nuovo import). ✓
- [ ] **Additività installer — schema invariato:** verifica che `install.report/1` non sia stato
      modificato (schema ancora in `sertor-install-kit/report.py:24`); il campo `notes` era già
      presente; il JSON è byte-identico a prima della feature quando `notes == []`. ✓
- [ ] **Additività installer — nessun nuovo seam:** verifica che non siano stati introdotti nuovi
      `ArtifactKind`, `Surface`, `WriteStrategy`, porte o dipendenze esterne. Solo `host_env.py`
      (modulo interno stdlib) è nuovo; nessun extra PyPI aggiunto. ✓
- [ ] **Nessun asset toccato (FR-015):** verifica che i file in `assets/rag/hooks/`,
      `assets/claude/hooks/`, `assets/rag/agents/`, `assets/claude/agents/` siano inalterati.
      `test_assets_sync.py` verde per costruzione — conferma. ✓
- [ ] Segnala come **follow-up non-bloccante**: prova LIVE su ospite macOS/Linux senza `pwsh`
      (verifica che il messaggio sia visibile in output umano e JSON dopo `sertor install rag`).
      Il done offline è raggiunto con i task precedenti (quickstart §1-6 verificati offline
      con OS mocking).

---

## Grafo delle dipendenze (sintesi)

```
TASK-F01 [P]  (host_env.py NUOVO, puro stdlib)           ──────────────────────────┐
                                                                                    │
TASK-US1-01 [P]  (install_rag.py: pwsh guard)  ← F01    ────────────────────┐     │
TASK-US1-02 [P]  (install_wiki.py: pwsh guard) ← F01    ──────────────┐     │     │
                                                                        │     │     │
TASK-US5-01      (install_rag.py: nota Copilot) ← US1-01  ──────┐     │     │     │
                                                                  │     │     │     │
TASK-US6-01 [P]  (docs/install.md)              ← —      ───┐    │     │     │     │
TASK-US6-02 [P]  (docs/install-copilot.md)      ← —      ───┤    │     │     │     │
TASK-US6-03 [P]  (packages/sertor/docs/install.md) ← —   ───┘    │     │     │     │
                                                                   │     │     │     │
TASK-US7-01 [P]  (test_host_env.py)             ← F01   ────┐    │     │     │     │
TASK-US7-02 [P]  (test_install_pwsh_guard.py)   ← US1-01,02 ┤    │     │     │     │
TASK-US7-03 [P]  (test_rag_copilot_memory_note) ← US5-01 ───┤    │     │     │     │
                                                              │     │     │     │     │
TASK-P01 [P]  (suite verde + lint) ← US7-01..03, US6-01..03 ┘     │     │     │     │
        │                                                           │     │     │     │
TASK-P02      (CS-1..6 + additività) ← P01                ────────┘     │     │     │
                                                                          │     │     │
              (invarianza sertor_core)                      ──────────────┘     │     │
              (schema install.report/1 invariato)           ──────────────────────┘     │
              (nessun seam/ArtifactKind/Surface nuovo)      ────────────────────────────┘
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (non-Windows senza pwsh → nota A) | Test G1 (rag) e G3 (wiki): simulando non-Windows + pwsh assente, `report.notes` contiene nota con A1/A2/A3/A4; `exit_code() == 0`. | TASK-US1-01/02, TASK-US7-02 | MECCANICO (OS mock) |
| **US2** (non-Windows con pwsh → nessun allarme) | Test G2 (rag): simulando non-Windows + pwsh presente, nessuna nota A in `report.notes`. | TASK-US1-01, TASK-US7-02 | MECCANICO (OS mock) |
| **US3** (Windows + Claude → comportamento invariato) | Test G4/G5 e NR `test_claude_report_has_no_gap_note`: su Windows `report.notes == []` (né nota A né nota B). Nessun artefatto nuovo, wiring invariato. | TASK-US1-01/02, TASK-US7-02 | MECCANICO + NR |
| **US4** (install non bloccato da assenza pwsh) | Test G1/G3: exit_code == 0 anche con pwsh assente; tutti i surface non-hook installati (verificabile dal conteggio `created`/`skipped` nel report). Test T3 (INV-1 non-fatale in `host_env`). | TASK-F01, TASK-US1-01/02, TASK-US7-01/02 | MECCANICO |
| **US5** (Copilot CLI → nota B `memory-capture`) | Test M1: `report.notes` contiene nota con B1/B2/B3/B4 su Copilot CLI. Test M2: nota assente su Claude. Test M3: nota B coesiste con nota A. | TASK-US5-01, TASK-US7-03 | MECCANICO (OS mock) |
| **US6** (doc dichiara prerequisito e surface parziali) | Lettura manuale di `docs/install.md` (pwsh prerequisito + URL + «installati ma non-operativi» + tabella operatività-per-target) e `docs/install-copilot.md` (pwsh + adapter config). CS-5 in TASK-P02. | TASK-US6-01/02/03 | MANUALE |
| **US7** (guard tests deterministici in CI) | Suite T1-T4, G1-G5, M1-M3 verde in CI Windows (OS mocking); `test_assets_sync.py` verde (nessun asset toccato). | TASK-US7-01/02/03, TASK-P01 | MECCANICO |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 — nessun prerequisito (massima parallelizzazione):**
- TASK-F01 [P] (host_env.py — fondazionale, scrivi e testa in isolamento)
- TASK-US6-01 [P] (docs/install.md — doc indipendente dal codice)
- TASK-US6-02 [P] (docs/install-copilot.md)
- TASK-US6-03 [P] (packages/sertor/docs/install.md)

**Sprint 2 — dopo TASK-F01:**
- TASK-US1-01 [P] (install_rag.py: pwsh guard ← F01)
- TASK-US1-02 [P] (install_wiki.py: pwsh guard ← F01)
- TASK-US7-01 [P] (test_host_env.py ← F01)

**Sprint 3 — dopo US1-01 e US1-02:**
- TASK-US5-01 (install_rag.py: nota Copilot ← US1-01)
- TASK-US7-02 [P] (test_install_pwsh_guard.py ← US1-01, US1-02)

**Sprint 4 — dopo US5-01:**
- TASK-US7-03 [P] (test_rag_copilot_memory_note.py ← US5-01)

**Sprint finale — dopo tutte le fasi:**
- TASK-P01 [P] (suite verde totale + lint)
- TASK-P02 (CS-check + additività)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E10-FEAT-018 — portabilità OS hook + onestà surface inerti

Fase SpecKit "tasks" completata per specs/078-portabilita-os-hook.
12 task in 6 fasi:
  Fase 0 Fondazionale (1 task):
    TASK-F01 [P]  host_env.py NUOVO — modulo puro stdlib (is_windows, pwsh_available,
                  pwsh_unavailability_note, maybe_note_pwsh, PWSH_INSTALL_URL)
  Fase 1 US1/US2/US3/US4 — guardia pwsh (2 task, [P]):
    TASK-US1-01 [P]  install_rag.py::execute_rag_plan — derivazione hook_surfaces + maybe_note_pwsh
    TASK-US1-02 [P]  install_wiki.py::execute_plan    — derivazione hook_surfaces + maybe_note_pwsh
  Fase 2 US5 — nota memory-capture Copilot CLI (1 task):
    TASK-US5-01      install_rag.py — costante _COPILOT_MEMORY_NOTE + if COPILOT_CLI
  Fase 3 US6 — documentazione utente (3 task, [P]):
    TASK-US6-01 [P]  docs/install.md — prerequisito pwsh + tabella operatività-per-target
    TASK-US6-02 [P]  docs/install-copilot.md — pwsh + adapter memory-capture
    TASK-US6-03 [P]  packages/sertor/docs/install.md — colonna operatività in tabella capability
  Fase 4 US7 — guard tests (3 task, [P]):
    TASK-US7-01 [P]  test_host_env.py NUOVO (kit) — T1-T4 builder puri + gating + tabella verità
    TASK-US7-02 [P]  test_install_pwsh_guard.py NUOVO — G1-G5 nota pwsh rag+wiki + NR Claude
    TASK-US7-03 [P]  test_install_rag_copilot_memory_note.py NUOVO — M1-M3 nota Copilot
  Fase 5 Polish/cross-cutting (2 task):
    TASK-P01 [P]  suite verde totale + lint ruff (tutte le guardie + NR + sync)
    TASK-P02      CS-1..6 + additività trasversale

Natura: ADDITIVO, host-facing. ZERO codice runtime di core. sertor_core INVARIATO.
Schema install.report/1 INVARIATO (additivo: notes vuoto → JSON byte-identico).
Artefatti toccati:
  - 1 modulo Python NUOVO (host_env.py, kit, stdlib puro)
  - 2 funzioni esistenti modificate (execute_rag_plan, execute_plan wiki): seam dopo _kit_execute_plan
  - 3 file doc utente aggiornati (docs/install.md, docs/install-copilot.md, packages/sertor/docs/install.md)
  - 3 file test NUOVI + estensione test_non_regression_claude.py
  - 0 asset .ps1/JSON toccati → test_assets_sync.py verde per costruzione (FR-015)
Copertura: FR-001..012, RNF-1..7, CS-1..6, US1..7.
Test natura: MECCANICO con OS mocking (US1/US2/US3/US4/US5/US7) + MANUALE (US6 doc).
Vincoli copeRti:
  INV-5 (no falso positivo Windows): gating is_windows() primo short-circuit.
  INV-7 (determinismo CI Windows): monkeypatch.setattr(host_env, ...) in tutti i test non-Windows.
  D-3 (nessuna riscrittura wiring): shell:powershell e pwsh -File invariati.
  A-004 (seam esistente): InstallReport.note() riusato, non modificato.
Parità Copilot: nessun asset body toccato → test_assets_copilot_parity.py verde per costruzione.
Nessun hook SpecKit eseguito (script assenti); nessuna operazione git.
Template tasks da 077 (setup-plan.ps1/SKILL.md assenti nel repo).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/078-portabilita-os-hook/tasks.md` (questo file, nuovo)
