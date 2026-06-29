# Tasks — Fail-loud breadcrumb negli hook + fallback «asset mancante → STOP» negli agent (E10-FEAT-019)

**Branch**: `077-fail-loud-hook-agent` · **Generato**: 2026-06-29
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/last-hook-error-state.md`](contracts/last-hook-error-state.md) ·
[`contracts/anti-regression-guard.md`](contracts/anti-regression-guard.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO, host-facing, ZERO codice di core.**
> La feature tocca esclusivamente:
> - 4 script PowerShell hook canonici (`assets/rag/hooks/` e `assets/claude/hooks/`): aggiunta
>   della funzione inline `Write-HookBreadcrumb` + punti di scrittura breadcrumb;
> - 3 body markdown agent canonici (`concierge.md`, `wiki-curator.md`, `requirements-analyst.md`):
>   aggiunta della regola «asset mancante → STOP e segnala»;
> - 1 riga in `gitignore_append.py` (kit): `RUNTIME_IGNORES += ".sertor/.last-hook-error"`;
> - copie dogfood `.claude/hooks/` e `.claude/agents/wiki-curator.md` ri-sincronizzate;
> - 3 nuovi file di guardia test (`test_assets_hook_breadcrumb.py`, `test_assets_agent_fallback.py`,
>   `test_assets_rag_dogfood_sync.py`).
>
> `sertor-core` è **INVARIATO**. Gli hook non importano `sertor_core` e non chiamano un LLM
> (Principio XI). I comportamenti a hook sano (nessun fallimento) sono **identici** a oggi.
>
> **Rischi noti da coprire (calibra l'ordine):**
> - **R-1 (cruciale PowerShell):** un comando nativo (`uv run …`) con exit non-zero **non** solleva
>   un'eccezione terminante in PowerShell: il `catch` esterno cattura solo il mancato avvio del
>   processo. Per rendere fail-loud anche «il vehicle è girato ma è fallito» occorre controllare
>   `$LASTEXITCODE` dopo ogni invocazione, **oltre** al `catch`. Tutti e 4 gli hook lo richiedono.
> - **R-2 (no-op gated by construction):** in `memory-capture.ps1` il gate `if (-not $enabled) { exit 0 }`
>   precede la risoluzione di `$root` e qualunque invocazione → il breadcrumb è fisicamente
>   irraggiungibile da quel path. Non serve logica aggiuntiva; la guardia A verifica la struttura.
> - **R-3 (no `$_` nel reason):** i `reason` string devono essere **hook-local e fissi** (es.
>   `"sertor-rag memory archive exited $LASTEXITCODE"`), mai interpolazione di `$_.Exception.Message`
>   o output esterno grezzo → REQ-008/A-003 (scrub alla fonte garantito dai vehicle).
> - **R-4 (buco sync rag dogfood):** `sertor_installer.sync` copre solo `assets/claude/**`; i 3 hook
>   rag dogfood (`.claude/hooks/memory-capture`, `rag-freshness`, `version-check`) non hanno guardia
>   → Guardia C nuova (scoperta D-5). La copia va fatta **manualmente** dopo aver editato il canonico.
>
> **Strategia MVP/incrementale.**
> - **Setup** (TASK-S01): kit RUNTIME_IGNORES (1 riga additiva). Prerequisito per Guardia D e per la
>   coerenza lifecycle. Bloccante per nessun hook, eseguibile in qualsiasi momento [P].
> - **Fondazionale** (TASK-F01..F04): i 4 hook canonici ricevono `Write-HookBreadcrumb` inline + punti
>   breadcrumb. Tutti parallelizzabili [P]; bloccanti per Guardia A + sync dogfood.
> - **Storia US6/US7** (TASK-US6-01..03): i 3 body agent ricevono il fallback host-agnostico. Tutti
>   parallelizzabili [P]; bloccanti per Guardia B + parità esistente.
> - **Storia US8/US9** (TASK-US8-01..03, US9-01): le 4 guardie anti-regressione (A/B/C/D).
>   US8-01/02/03 [P]; US9-01 dipende da S01.
> - **Polish/cross-cutting** (TASK-P01..P03): sync dogfood, suite verde totale, CS-check trasversale.
>
> L'ordine di priorità segue: fondazionale hook P1 Must (US1/US2/US5) → agent fallback P1 Must
> (US6/US7) → guardie P1 Must (US8) → RUNTIME_IGNORES + sync P2 Should (US9) → polish.

---

## Fase 0 — Setup: kit RUNTIME_IGNORES (1 task)

> Prerequisiti: nessuno. Additiva, 1 riga. Parallelizzabile con tutto il resto [P].
> Bloccante per Guardia D (TASK-US9-01) e per la coerenza lifecycle dell'installer.

### TASK-S01 [P] — Aggiungi `.sertor/.last-hook-error` a `RUNTIME_IGNORES` (kit)

**File**: `packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-016 · US9-AC2

- [ ] Apri `packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py`.
      Individua la tupla `RUNTIME_IGNORES` (oggi contiene 7 voci: `.venv/`, `.index*`, `.env`,
      `.rag-health.json`, `.version-check.json`, `.sertor-version`, `.sertor-flow-version`).
- [ ] Aggiungi come **ultima voce** della tupla:
      ```python
      ".sertor/.last-hook-error",  # E10-FEAT-019: breadcrumb ultimo errore hook (runtime, mai versionato)
      ```
      Gemello diretto di `.rag-health.json` (stessa collocazione `.sertor/`, stesso trattamento).
- [ ] Verifica che il test esistente
      `packages/sertor-install-kit/tests/unit/test_gitignore_append.py`
      resti verde: il test asserisce che ogni voce di `RUNTIME_IGNORES` compaia nel `.gitignore`
      generato; la nuova voce la soddisfa automaticamente (test di non-regressione).
- [ ] Verifica che `remove_gitignore_lines` rimuova anche la nuova voce su uninstall: la funzione
      itera su `RUNTIME_IGNORES` — comportamento ereditato, nessuna modifica aggiuntiva necessaria.
- [ ] Verifica che l'aggiunta sia l'**unica** modifica al kit: nessun nuovo `ArtifactKind`,
      `WriteStrategy` o seam (additività pura — data-model §5).

---

## Fase 1 — Fondazionale: `Write-HookBreadcrumb` nei 4 hook canonici (4 task)

> Prerequisiti: nessuno. I 4 hook sono indipendenti tra loro [P].
> Bloccanti per Guardia A (TASK-US8-01) e per il sync dogfood (TASK-P01).
>
> **Convenzione comune a tutti e 4 gli hook (da seguire esattamente):**
> 1. Aggiungi la funzione inline `Write-HookBreadcrumb -Root <string> -Hook <string> -Reason <string>`
>    dopo il blocco `<# … #>` di documentazione iniziale; il corpo è byte-identico nei 4 hook:
>    - crea `.sertor/` se assente (`New-Item -ItemType Directory -Force`, pattern `rag-freshness.ps1`);
>    - scrive `.sertor/.last-hook-error` (JSON `hook.error/1`: `schema`, `hook`, `ts` UTC
>      `yyyy-MM-ddTHH:mm:ssZ`, `reason`) con `Set-Content` (sovrascrittura, semantica «ultimo errore»);
>    - emette nota stderr: `"[sertor] hook '$Hook' degraded: $Reason (see .sertor/.last-hook-error)"`;
>    - **tutto** dentro `try{…}catch{}` interno → mai solleva, mai fatale (REQ-005/INV-3).
> 2. Aggiungi l'accumulatore `$reason = $null` prima del blocco operativo principale.
> 3. Imposta `$reason` **solo** sui rami degradati, con **stringhe hook-local fisse** (mai `$_.Exception.Message`
>    né output grezzo del vehicle — R-3/REQ-008). Dove il fallimento deriva dall'exit code del vehicle,
>    interpola solo `$LASTEXITCODE` numerico: es. `"sertor-rag … exited $LASTEXITCODE"`.
> 4. Prima del `exit 0` finale: `if ($reason) { Write-HookBreadcrumb -Root $root -Hook '<nome>' -Reason $reason }`.
> 5. Verifica che ogni `catch { }` silenzioso **fuori** dalla funzione `Write-HookBreadcrumb` stessa
>    sia convertito in un ramo che imposta `$reason` (il solo catch silenzioso sanzionato è quello
>    interno alla funzione — sink best-effort REQ-005).
> 6. Verifica che `exit 0` sia l'ultima istruzione in **tutti** i path (FR-007/NFR-5).
> 7. Verifica che l'hook non importi `sertor_core` e non chiami un LLM (Principio XI).

### TASK-F01 [P] — `memory-capture.ps1`: 1 punto breadcrumb (invocazione delegata)

**File**: `packages/sertor/src/sertor_installer/assets/rag/hooks/memory-capture.ps1` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-001/002/003/004/005/007/008/009 · US1/US2/US3/US5

- [ ] Aggiungi la funzione `Write-HookBreadcrumb` inline (convenzione comune sopra) subito dopo il
      blocco `<# … #>` di documentazione. Verifica che `$root` sia già risolto prima del blocco `try`
      principale (riga ~50-56 originale) e sia quindi accessibile in ogni `catch`.
- [ ] Aggiungi `$reason = $null` prima del blocco `try` principale.
- [ ] **No-op gated (REQ-004/FR-004) — by construction:** il gate `if (-not $enabled) { exit 0 }`
      (riga ~41 originale) precede la risoluzione di `$root` e qualunque invocazione → il path no-op
      **non raggiunge mai** `Write-HookBreadcrumb`. Nessuna modifica al gate. Verificalo leggendo
      la struttura: il gate deve rimanere **prima** di qualsiasi riferimento a `$root` o `$reason`.
- [ ] **Punto breadcrumb — invocazione primaria/globale** (riga ~68-71 originale):
      dopo `uv run --project … sertor-rag memory archive` E dopo il fallback globale `sertor-rag`:
      ```powershell
      if ($LASTEXITCODE -ne 0) { $reason = "sertor-rag memory archive exited $LASTEXITCODE" }
      ```
      (controlla `$LASTEXITCODE` per rendere fail-loud anche il vehicle avviato con errore — R-1).
- [ ] **Punto breadcrumb — catch esterno** (riga ~79-90 originale, `catch {}`):
      nel `catch` che gestisce `uv` assente o fallback venv:
      - se il venv `sertor-rag` non esiste: `$reason = "uv and venv sertor-rag both unavailable"`
      - se il venv esiste ma esce con codice non-zero: `$reason = "venv sertor-rag exited $LASTEXITCODE"`
      - sostituisce il `catch {}` silenzioso (R-1: controlla `$LASTEXITCODE` anche nel venv).
- [ ] **Scrittura breadcrumb** — prima del `exit 0` finale:
      ```powershell
      if ($reason) { Write-HookBreadcrumb -Root $root -Hook 'memory-capture' -Reason $reason }
      exit 0
      ```
- [ ] Verifica che nessun `reason` contenga `$_.Exception.Message` o output grezzo del vehicle
      (R-3/REQ-008): solo stringhe fisse o interpolazione di `$LASTEXITCODE` numerico.
- [ ] Spot check visivo: percorso sano (archive OK, `$LASTEXITCODE = 0`) → `$reason` resta `$null` →
      nessun breadcrumb scritto → funzionamento identico a oggi.

### TASK-F02 [P] — `rag-freshness.ps1`: 3 punti breadcrumb (path catastrofici muti)

**File**: `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-001/002/003/005/007/008/009 · US1/US2/US5

> **Nota di scope (DA-1):** i path che confluiscono nel verdetto `doctor` → `.rag-health.json`
> (rig ~99-159 originali) sono **già** una traccia ispezionabile e **non** ricevono breadcrumb
> (nessun doppio segnale). Il breadcrumb copre SOLO i 3 path che **bypassano** la scrittura del
> verdetto (path muti). Leggendo il file, identifica le 3 aree seguenti e non toccare le altre.

- [ ] Aggiungi `Write-HookBreadcrumb` inline (convenzione comune) dopo il blocco `<# … #>` iniziale.
      Verifica che `$root` (risolto nel foreground ~riga 195-197) sia accessibile nei `catch` del
      foreground; nel worker, `$root` è passato come parametro (`-Root` da argparse o param block).
- [ ] Aggiungi `$reason = $null` nel foreground, prima del blocco `try/Start-Process`.
- [ ] **Punto breadcrumb 1 — spawn foreground fallito** (riga ~209-212, `catch` su `Start-Process pwsh`):
      il worker non parte → nessun `doctor`, nessun verdetto, nessun re-index → silenzio → sostituisci
      `catch { … exit 0 }` con:
      ```powershell
      catch {
          $reason = "failed to spawn freshness worker"
          Write-HookBreadcrumb -Root $root -Hook 'rag-freshness' -Reason $reason
          exit 0
      }
      ```
      (stringa fissa, no `$_` — R-3).
- [ ] **Punto breadcrumb 2 — re-index fallito nel worker** (riga ~164-168, dopo la scrittura del
      verdetto — anche `healthy`): dopo `uv run --project … sertor-rag index .` nel worker:
      ```powershell
      if ($LASTEXITCODE -ne 0) { $reason = "re-index failed after health write" }
      ```
      e, nel `catch` del re-index:
      ```powershell
      catch { $reason = "re-index failed after health write" }
      ```
      Prima di uscire dal worker: `if ($reason) { Write-HookBreadcrumb -Root $root -Hook 'rag-freshness' -Reason $reason }`.
- [ ] **Punto breadcrumb 3 — outer catch catastrofico del worker** (riga ~172-175, `catch { exit 0 }`
      esterno che non ha scritto lo stato): sostituisci con:
      ```powershell
      catch {
          Write-HookBreadcrumb -Root $root -Hook 'rag-freshness' -Reason "freshness worker crashed"
          exit 0
      }
      ```
      (stringa fissa — R-3; no `$_`).
- [ ] Verifica che i path `doctor` → `.rag-health.json` (riga ~99-159) **non** siano toccati:
      la degradazione rilevata da `doctor` è già tracciata nel file di salute RAG.
- [ ] Spot check: path sano (spawn OK, index OK, doctor OK) → `$reason` mai impostato → nessun
      breadcrumb scritto → comportamento identico a oggi.

### TASK-F03 [P] — `wiki-pending-check.ps1`: 1 punto breadcrumb (scan fallita)

**File**: `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-001/002/003/005/007/008/009 · US1/US2/US5

- [ ] Aggiungi `Write-HookBreadcrumb` inline (convenzione comune) dopo il blocco `<# … #>` iniziale.
      Verifica che `$root` sia risolto (~riga 39-44 originale) prima di qualunque `try/catch`.
- [ ] Aggiungi `$reason = $null` prima del blocco `try` principale.
- [ ] **No-op legittimi (NON breadcrumb):** assenza di `wiki.config.toml` (~riga 50) e
      `pending <= 0` / schema invalido (~riga 75): questi sono esiti **definiti** (niente da fare),
      non fallimenti → NON impostare `$reason` su questi rami.
- [ ] **Punto breadcrumb — catch sulla scan** (~riga 70-73, oggi `Pop-Location; exit 0  # silent`):
      `sertor-wiki-tools scan` non risolvibile o in errore → sostituisci con:
      ```powershell
      catch {
          $reason = "sertor-wiki-tools scan unavailable or failed"
          Pop-Location
          # il breadcrumb viene scritto prima di exit 0 in fondo allo script
      }
      ```
      (stringa hook-local fissa, **no** `$_` — R-3/REQ-008).
- [ ] **Scrittura breadcrumb** prima di `exit 0` finale:
      ```powershell
      if ($reason) { Write-HookBreadcrumb -Root $root -Hook 'wiki-pending-check' -Reason $reason }
      exit 0
      ```
- [ ] Verifica che `Pop-Location` sia ancora eseguito prima della scrittura del breadcrumb (gestione
      stack directory invariata).
- [ ] Spot check: assenza `wiki.config.toml` → `$reason` resta `$null` → nessun breadcrumb →
      comportamento identico a oggi.

### TASK-F04 [P] — `version-check.ps1`: 1 punto breadcrumb (catch catastrofico + REQ-006)

**File**: `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.ps1` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-001/002/003/005/006/007/008/009 · US1/US2/US4/US5

- [ ] Aggiungi `Write-HookBreadcrumb` inline (convenzione comune) dopo il blocco `<# … #>` iniziale.
      Verifica che `$root` sia risolto (~riga 85-87 originale) prima del blocco `try` principale.
- [ ] Aggiungi `$reason = $null` prima del blocco `try` principale.
- [ ] **No-op legittimo (NON breadcrumb):** GET HTTP fallito → `$latest = ''` → verdetto `unknown`
      (~riga 139-141): questo è un esito **definito** (offline/rete non raggiungibile), NON un
      problema nascosto → NON impostare `$reason` su questo ramo.
- [ ] **Punto breadcrumb — outer catch catastrofico** (~riga 166-168, oggi `catch { } # Catastrophic
      internal error: silent`): questo catch copre sia errori interni catastrofici sia la **lettura
      cieca** dello stato runtime proprio (`.version-check.json` / stamp corrotto che nasconde un
      problema — REQ-006/FR-006) → sostituisci con:
      ```powershell
      catch {
          Write-HookBreadcrumb -Root $root -Hook 'version-check' -Reason "version-check internal error"
          exit 0
      }
      ```
      (stringa fissa, no `$_` — R-3/REQ-008; copre REQ-006 by-construction).
- [ ] Verifica che il percorso `unknown` (rete offline) **non** raggiunga il catch catastrofico:
      il `$latest = ''` / verdetto `unknown` deve essere gestito **prima** dell'outer catch.
- [ ] Spot check: versione letta OK, confronto OK → `$reason` mai impostato → nessun breadcrumb →
      comportamento identico a oggi.

---

## Fase 2 — Storia US6/US7: fallback «asset mancante → STOP» nei 3 body agent (3 task)

> Prerequisiti: nessuno. I 3 body sono indipendenti tra loro [P].
> Bloccanti per Guardia B (TASK-US8-02) e per la parità Copilot esistente (TASK-P02).
>
> **Convenzione comune a tutti e 3 i body (da seguire esattamente):**
> - La regola di fallback va inserita **prima** della prima istruzione che legge l'asset di cui
>   l'agent è guscio (prima della riga che dice «leggi la skill X» / «leggi il playbook»).
> - Il testo usa i **token stabili EN** (Guardia B): `STOP` (maiuscolo), nome dell'asset,
>   frase `cannot be resolved or read`.
> - Il testo è **host-agnostico**: nessun path `.claude/`, nessun slash-command, nessun nome-modello
>   o prodotto Claude-only (REQ-013/FR-013 — verificato dalla parità esistente `test_assets_copilot_parity.py`).
> - Il testo è **byte-identico** tra la distribuzione Claude e Copilot (il file è uno solo).
> - Forma consigliata (adattata all'asset):
>   ```
>   **IMPORTANT — missing asset guard:** Before reading the skill/playbook, verify it can be
>   resolved and read. If `<asset-name>` cannot be resolved or read, **STOP immediately** and
>   inform the user: report which asset is missing and that the operation cannot proceed until
>   the asset is available. Do not attempt to proceed without it.
>   ```

### TASK-US6-01 [P] — `concierge.md`: fallback «guided-setup mancante → STOP»

**File**: `packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-010/013 · US6-AC1/US7-AC1/AC2

- [ ] Individua nel body la prima istruzione che legge / fa riferimento alla skill `guided-setup`.
- [ ] Inserisci **prima** di quella istruzione la regola di fallback (convenzione comune sopra),
      con i token stabili: `STOP` + `guided-setup` + `cannot be resolved or read`.
- [ ] Verifica che il testo non contenga:
      - path `.claude/` → FAIL Guardia B / parità
      - slash-command (es. `/wiki`, `/specify`) → FAIL parità
      - nomi-modello/prodotto Claude-only (es. «Opus», «Haiku», «Claude Code») → FAIL parità
- [ ] Verifica visiva: la frase è inequivocabile — un LLM che legge il body capisce che deve
      fermarsi e segnalare, non procedere (US6-AC1, CS-3).
- [ ] Spot check parità: il testo aggiunto è identico a come apparirebbe per Copilot (nessun
      contenitore Claude-specifico nel body dell'agent).

### TASK-US6-02 [P] — `wiki-curator.md`: fallback «wiki-playbook/ops mancante → STOP»

**File**: `packages/sertor/src/sertor_installer/assets/claude/agents/wiki-curator.md` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-011/013 · US6-AC2/US7-AC1/AC2

- [ ] Individua nel body la prima istruzione che legge / fa riferimento a `wiki-playbook.md`
      o ai moduli `ops/`.
- [ ] Inserisci **prima** di quella istruzione la regola di fallback (convenzione comune), con
      i token stabili: `STOP` + `wiki-playbook` + `cannot be resolved or read`.
- [ ] Verifica che il testo sia host-agnostico (niente `.claude/`, slash-command, nomi Claude)
      e inequivocabile (US6-AC2, CS-3).
- [ ] Verifica che la regola copra **sia** `wiki-playbook.md` **sia** i moduli `ops/` richiesti:
      se uno qualunque degli asset citati nel body non è risolvibile, la regola si applica.

### TASK-US6-03 [P] — `requirements-analyst.md`: fallback «skill requirements mancante → STOP»

**File**: `packages/sertor-flow/src/sertor_flow/assets/claude/agents/requirements-analyst.md` (MODIFICA)
→ dipende da: nessuno

**Mappa FR**: FR-012/013 · US6-AC3/US7-AC1/AC2

> Nota: il body di questo agent è in italiano con notazione EARS in inglese. La frase di fallback
> usa i token EN stabili per uniformità della Guardia B, restando host-agnostica e comprensibile.

- [ ] Individua nel body la prima istruzione che legge / fa riferimento alla skill `requirements`.
- [ ] Inserisci **prima** di quella istruzione la regola di fallback (convenzione comune), con
      i token stabili: `STOP` + `requirements` + `cannot be resolved or read`.
- [ ] Verifica che la regola sia **uniforme** (DA-2): «STOP e segnala», senza alcun path di
      auto-recupero differenziato (A-005 — decisione utente, FR-012).
- [ ] Verifica host-agnosticità e inequivocabilità (US6-AC3, CS-3).
- [ ] Nota: il dogfood `.claude/agents/requirements-analyst.md` andrà sincronizzato in TASK-P01
      (copia manuale dalla sorgente sertor-flow, perché non coperto da `sertor_installer.sync`).

---

## Fase 3 — Storie US8/US9: guardie anti-regressione (4 task)

> TASK-US8-01 [P], TASK-US8-02 [P] e TASK-US8-03 [P] sono parallelizzabili tra loro.
> TASK-US9-01 [P] dipende solo da TASK-S01 ed è parallelizzabile con US8-*.
> Tutti i test scritti in questa fase dipendono dai canonici editati (Fase 1 e Fase 2)
> ma possono essere **scritti** prima del sync dogfood (TASK-P01); diventeranno verdi dopo P01.

### TASK-US8-01 [P] — Guardia A: lint breadcrumb sui 4 hook in scope

**File**: `packages/sertor/tests/test_assets_hook_breadcrumb.py` (NUOVO)
→ dipende da: TASK-F01, TASK-F02, TASK-F03, TASK-F04

**Mappa FR**: FR-015 · US8-AC1/AC3 · CS-6

> Modello: `packages/sertor/tests/test_assets_hook_cli_invocation.py` (usa `iter_asset_dir`,
> strip `<# … #>` + righe `#`, meta-test positivi/negativi).

- [ ] Crea `packages/sertor/tests/test_assets_hook_breadcrumb.py`.
- [ ] Implementa `_ps1_code_lines(body)`: rimuove blocchi `<# … #>` e righe `#`
      (pattern `_code_lines` da `test_assets_hook_cli_invocation.py`).
- [ ] Implementa `_hook_bodies_in_scope()`: ritorna i body canonici (solo codice) dei **4 hook in scope**:
      - `packages/sertor/src/sertor_installer/assets/rag/hooks/memory-capture.ps1`
      - `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1`
      - `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.ps1`
      - `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1`
      Usa `iter_asset_dir("rag/hooks")` e `iter_asset_dir("claude/hooks")`, filtrando i `.ps1`
      in scope per nome. Anti-vacuità: asserisci che siano esattamente 4.
- [ ] **Test A1 — presenza + uso di `Write-HookBreadcrumb`:**
      ```python
      def test_write_hook_breadcrumb_defined_and_invoked_in_scope_hooks():
          for name, body in _hook_bodies_in_scope():
              code = "\n".join(_ps1_code_lines(body))
              assert "function Write-HookBreadcrumb" in code, f"{name}: funzione non definita"
              assert "Write-HookBreadcrumb" in code.replace("function Write-HookBreadcrumb", ""), \
                  f"{name}: funzione definita ma mai invocata"
      ```
- [ ] **Test A2 — no silent-swallow (nessun `catch` silenzioso fuori da `Write-HookBreadcrumb`):**
      Regex per `catch` con corpo vuoto / solo `exit 0` / solo `Pop-Location`
      (es. `catch\s*\{\s*(exit\s+0\s*|Pop-Location\s*)?\}`). Per ogni hook, asserisci che
      tali pattern esistano **solo** dentro il corpo della funzione `Write-HookBreadcrumb`
      (il sink best-effort sanzionato — REQ-005/INV-3):
      ```python
      def test_no_silent_catch_outside_write_hook_breadcrumb():
          for name, body in _hook_bodies_in_scope():
              # estrai il corpo di Write-HookBreadcrumb per escluderlo
              # asserisci 0 occorrenze di silent-catch fuori da quella funzione
      ```
- [ ] **Meta-test positivo** (anti-vacuità A2): un body sintetico con `catch { exit 0 }` fuori da
      `Write-HookBreadcrumb` viene flaggato dal rilevatore → `assert offenders != []`.
- [ ] **Meta-test negativo** (anti-vacuità A2): un body sintetico con `catch { Write-HookBreadcrumb … }`
      (forma robusta) NON viene flaggato → `assert offenders == []`.
- [ ] **Meta-test scoperta** (anti-vacuità A1): un body sintetico privo di `Write-HookBreadcrumb`
      viene segnalato come mancante → A1 fallisce.
- [ ] Tutti i test `not cloud`, nessun `uv run`, offline.

### TASK-US8-02 [P] — Guardia B: assert fallback sui 3 body agent

**File**: `packages/sertor/tests/test_assets_agent_fallback.py` (NUOVO)
→ dipende da: TASK-US6-01, TASK-US6-02, TASK-US6-03

**Mappa FR**: FR-015 · US8-AC2/AC3 · CS-6

- [ ] Crea `packages/sertor/tests/test_assets_agent_fallback.py`.
- [ ] Implementa la helper `_agent_bodies()` che legge i 3 body canonici da path assoluti:
      - `packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md`
      - `packages/sertor/src/sertor_installer/assets/claude/agents/wiki-curator.md`
      - `packages/sertor-flow/src/sertor_flow/assets/claude/agents/requirements-analyst.md`
      Ritorna lista di `(nome_agent, path, testo)`. Anti-vacuità: asserisci che siano esattamente 3.
      (Usa `pathlib.Path(__file__).parents[N]` per risolvere il root del repo in modo robusto.)
- [ ] Definisci i **token attesi per agent** (stabili, da `data-model.md §3`):
      ```python
      _EXPECTED_TOKENS = {
          "concierge":             ("STOP", "guided-setup",  "cannot be resolved or read"),
          "wiki-curator":          ("STOP", "wiki-playbook", "cannot be resolved or read"),
          "requirements-analyst":  ("STOP", "requirements",  "cannot be resolved or read"),
      }
      ```
- [ ] **Test B — presenza token stabili nei 3 body:**
      ```python
      def test_agent_fallback_tokens_present():
          for name, path, text in _agent_bodies():
              tokens = _EXPECTED_TOKENS[name]
              for token in tokens:
                  assert token in text, f"{name} ({path}): token '{token}' mancante nel fallback"
      ```
- [ ] **Meta-test** (anti-vacuità): un body sintetico privo di `STOP` → l'assert fallisce. Verifica
      che rimuovere la frase di fallback da un body lo faccia fallire nel test (US8-AC2).
- [ ] Tutti `not cloud`, nessun `uv run`, offline.

### TASK-US8-03 [P] — Guardia C: sync rag dogfood (scoperta D-5)

**File**: `tests/unit/test_assets_rag_dogfood_sync.py` (NUOVO)
→ dipende da: TASK-F01, TASK-F02, TASK-F04 (canonici modificati); TASK-P01 (sync eseguito)

**Mappa FR**: FR-014 · US9-AC1 · CS-5

> Chiude il buco D-5: `sertor_installer.sync` copre solo `assets/claude/**`; i 3 hook rag
> (`memory-capture`, `rag-freshness`, `version-check`) non hanno guardia di sync. `wiki-pending-check`
> (assets/claude) è coperto dalla root sync esistente; questo test copre i soli hook rag.

- [ ] Crea `tests/unit/test_assets_rag_dogfood_sync.py`.
- [ ] Implementa la fixture `repo_root` (se non già disponibile in `conftest.py` root):
      ```python
      import pathlib
      REPO_ROOT = pathlib.Path(__file__).parents[2]  # tests/unit/ → root
      ```
- [ ] **Test C — byte-identità dogfood↔canonico per i 3 hook rag:**
      ```python
      import pytest

      _RAG_HOOKS_IN_SCOPE = ("memory-capture.ps1", "rag-freshness.ps1", "version-check.ps1")

      @pytest.mark.parametrize("name", _RAG_HOOKS_IN_SCOPE)
      def test_rag_hook_dogfood_sync(name):
          bundled = REPO_ROOT / "packages/sertor/src/sertor_installer/assets/rag/hooks" / name
          dogfood = REPO_ROOT / ".claude/hooks" / name
          assert bundled.read_bytes() == dogfood.read_bytes(), (
              f"Drift: '{name}' bundlato ≠ dogfood .claude/hooks/{name}. "
              "Eseguire la copia manuale (quickstart §6)."
          )
      ```
- [ ] Verifica che il test **fallisca** introducendo un drift di 1 carattere in uno dei file
      (meta-test di sanità — US9-AC1; verifica offline, non committare il drift).
- [ ] Verifica che `tests/unit/test_assets_sync.py` (guardia `assets/claude/**` esistente) **non**
      copra già gli hook rag (il subtree `claude/` in `sync.py` è distinto da `rag/hooks/`) →
      nessuna duplicazione, guardia C è additiva.
- [ ] Tutti `not cloud`, nessun `uv run`, offline; dipende da `pathlib` stdlib.

### TASK-US9-01 [P] — Guardia D: assert `.sertor/.last-hook-error` in `RUNTIME_IGNORES`

**File**: `packages/sertor-install-kit/tests/unit/test_gitignore_append.py` (MODIFICA)
→ dipende da: TASK-S01

**Mappa FR**: FR-016 · US9-AC2

> Gemella dell'assert per `.sertor/.rag-health.json` e `.sertor/.version-check.json`
> già presenti nel test del kit.

- [ ] Apri `packages/sertor-install-kit/tests/unit/test_gitignore_append.py`.
- [ ] Individua la sezione/assert che verifica la presenza delle voci in `RUNTIME_IGNORES` nel
      `.gitignore` generato.
- [ ] Aggiungi (o verifica che sia già coperto dall'assert generale) l'asserzione esplicita:
      ```python
      assert ".sertor/.last-hook-error" in RUNTIME_IGNORES, \
          "E10-FEAT-019: .last-hook-error deve essere in RUNTIME_IGNORES"
      ```
      Se il test esistente già itera su `RUNTIME_IGNORES` e verifica ogni voce → la nuova voce
      è coperta automaticamente da TASK-S01; in tal caso aggiungere solo un commento descrittivo.
- [ ] Esegui il test isolato: `uv run pytest packages/sertor-install-kit/tests/ -m "not cloud" -q`
      → verde dopo TASK-S01.
- [ ] Verifica che l'uninstall test esistente (se presente) resti verde: `remove_gitignore_lines`
      deve rimuovere la nuova voce (comportamento ereditato dall'iterazione su `RUNTIME_IGNORES`).

---

## Fase 4 — Polish e cross-cutting (3 task)

> Prerequisiti: tutte le Fasi 0–3 complete. TASK-P01 e TASK-P02 [P] sono parallelizzabili
> nell'avvio (P01 blocca P02 per la Guardia C); TASK-P03 dipende da entrambi.

### TASK-P01 — Sync dogfood: canonici → `.claude/` (copia + verify)

→ dipende da: TASK-F01, TASK-F02, TASK-F03, TASK-F04, TASK-US6-01, TASK-US6-02, TASK-US6-03

- [ ] **Sync automatico (`assets/claude/**`) via `sertor_installer.sync`:**
      ```powershell
      uv run python -m sertor_installer.sync
      ```
      Questo propaga `assets/claude/hooks/wiki-pending-check.ps1` → `.claude/hooks/wiki-pending-check.ps1`
      e `assets/claude/agents/wiki-curator.md` → `.claude/agents/wiki-curator.md`.
      Verifica che il comando esca 0 e segnali i file aggiornati.
- [ ] **Copia manuale dei 3 hook rag** (non coperti da sync automatico — R-4/scoperta D-5):
      ```powershell
      Copy-Item packages/sertor/src/sertor_installer/assets/rag/hooks/memory-capture.ps1 `
                .claude/hooks/memory-capture.ps1
      Copy-Item packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1 `
                .claude/hooks/rag-freshness.ps1
      Copy-Item packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.ps1 `
                .claude/hooks/version-check.ps1
      ```
- [ ] **Copia manuale di `requirements-analyst.md`** (sertor-flow, non coperto da `sertor_installer.sync`):
      ```powershell
      Copy-Item packages/sertor-flow/src/sertor_flow/assets/claude/agents/requirements-analyst.md `
                .claude/agents/requirements-analyst.md
      ```
      (Se `.claude/agents/requirements-analyst.md` non esiste come dogfood, crearlo.)
- [ ] **Verifica byte-identità** post-sync:
      - `diff .claude/hooks/memory-capture.ps1 packages/sertor/src/sertor_installer/assets/rag/hooks/memory-capture.ps1`
      - `diff .claude/hooks/rag-freshness.ps1 packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1`
      - `diff .claude/hooks/version-check.ps1 packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.ps1`
      - `diff .claude/hooks/wiki-pending-check.ps1 packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1`
      - `diff .claude/agents/wiki-curator.md packages/sertor/src/sertor_installer/assets/claude/agents/wiki-curator.md`
      Tutti devono essere privi di diff.
- [ ] Verifica che la root `tests/unit/test_assets_sync.py` (guardia `assets/claude/**` esistente)
      resti verde dopo il sync (non-regressione).

### TASK-P02 [P] — Suite verde totale + lint ruff

→ dipende da: TASK-P01 (per Guardia C), tutte le Fasi 0–3

- [ ] **Guardie nuove:**
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_hook_breadcrumb.py `
                    packages/sertor/tests/test_assets_agent_fallback.py `
                    tests/unit/test_assets_rag_dogfood_sync.py -v
      ```
      Tutti devono essere verdi (A1/A2 + meta-test + B + meta-test + C + D).
- [ ] **Parità Copilot (riuso — nessun codice nuovo):**
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_parity.py -v
      ```
      Le frasi di fallback host-agnostiche nei 3 body (TASK-US6-01..03) non devono contenere
      `.claude/`, slash-command né nomi Claude → il test rende i piani e li verifica.
- [ ] **Sync esistente (non-regressione):**
      ```powershell
      uv run pytest tests/unit/test_assets_sync.py -v
      ```
      La guardia `claude/` existente deve restare verde dopo il sync (TASK-P01).
- [ ] **Guardie hook esistenti (non-regressione):**
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_hook_cli_invocation.py -v
      ```
      I 4 hook modificati devono continuare a passare: `uv run --project` usato, nessun bare `uv run`.
- [ ] **Kit (non-regressione):**
      ```powershell
      uv run pytest packages/sertor-install-kit/tests/ -m "not cloud" -v
      ```
      Inclusi `test_gitignore_append.py` (Guardia D) → verde.
- [ ] **Lint ruff (nessun Python modificato, ma verifica):**
      ```powershell
      uv run ruff check packages/sertor/tests/test_assets_hook_breadcrumb.py `
                       packages/sertor/tests/test_assets_agent_fallback.py `
                       tests/unit/test_assets_rag_dogfood_sync.py
      ```
      Zero errori (regole E,F,I,UP,B; line-length 100).

### TASK-P03 — Verifica CS-1..6 e additività trasversale

→ dipende da: TASK-P01, TASK-P02

- [ ] **CS-1 (rottura silenziosa lascia traccia):** i 4 hook in scope (F01-F04) hanno `Write-HookBreadcrumb`
      definita e invocata sui path degradati; Guardia A verde conferma. Spot check manuale quickstart §1. ✓
- [ ] **CS-2 (non-fatalità preservata):** ogni hook esce 0 in tutti i path; `Write-HookBreadcrumb`
      ha `try{…}catch{}` interno (mai fatale); Guardia A2 verifica assenza silent-catch non sanzionati. ✓
- [ ] **CS-3 (agent si fermano sull'asset mancante):** i 3 body (US6-01..03) hanno la regola
      uniforme STOP; Guardia B verde conferma. Nota: il comportamento runtime vero è verificabile solo
      con test live su ospite reale — la spec lo dichiara (US6 nota D↔N). ✓
- [ ] **CS-4 (nessun segreto nella traccia):** tutti i `reason` string sono hook-local fissi o usano
      solo `$LASTEXITCODE` numerico; nessun `$_.Exception.Message`; verifica testuale nei body. ✓
- [ ] **CS-5 (parità host-agnostica preservata):** fallback testo host-agnostico (US7); parità Copilot
      verde (TASK-P02); Guardia C sync rag dogfood verde; sync esistente verde. ✓
- [ ] **CS-6 (guardia anti-regressione):** Guardia A (lint hook), B (fallback agent), C (sync rag
      dogfood), D (RUNTIME_IGNORES) tutte verdi. ✓
- [ ] **Additività core — invarianza `sertor_core`:** verifica che nessun file in `src/sertor_core/`
      sia stato modificato. Gli hook non importano `sertor_core` e non chiamano un LLM (Principio XI). ✓
- [ ] **Additività installer:** le modifiche al kit sono limitate a 1 riga in `gitignore_append.py`
      (TASK-S01). Nessun nuovo `ArtifactKind`/`WriteStrategy`/`Surface`/seam (data-model §5). ✓
- [ ] **No-op gated (US3) — verifica manuale quickstart §2:**
      `$env:SERTOR_MEMORY = $null; .\.claude\hooks\memory-capture.ps1; Test-Path .sertor\.last-hook-error`
      → `False` (nessun breadcrumb). ✓ (documentato come verifica manuale, non automatizzata offline)
- [ ] Segnala come **follow-up non-bloccante**: prova LIVE su ospite Claude e Copilot reale
      (quickstart §1..§7) — il done offline è raggiunto con i task precedenti.

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01 [P]  (RUNTIME_IGNORES += .last-hook-error)       ─────────────────────────────┐
                                                                                         │
TASK-F01 [P]  (memory-capture.ps1 breadcrumb)             ─────────────────────────┐   │
TASK-F02 [P]  (rag-freshness.ps1 breadcrumb ×3)           ──────────────────────┐  │   │
TASK-F03 [P]  (wiki-pending-check.ps1 breadcrumb)         ───────────────────┐  │  │   │
TASK-F04 [P]  (version-check.ps1 breadcrumb + REQ-006)    ────────────────┐  │  │  │   │
                                                                           │  │  │  │   │
TASK-US6-01 [P] (concierge.md fallback)                   ──────────┐     │  │  │  │   │
TASK-US6-02 [P] (wiki-curator.md fallback)                ───────┐  │     │  │  │  │   │
TASK-US6-03 [P] (requirements-analyst.md fallback)        ────┐  │  │     │  │  │  │   │
                                                             │  │  │     │  │  │  │   │
TASK-US8-01 [P] (Guardia A lint breadcrumb)  ← F01-F04   ──┘  │  │     │  │  │  │   │
TASK-US8-02 [P] (Guardia B assert fallback)  ← US6-01..03 ────┘  │     │  │  │  │   │
TASK-US8-03 [P] (Guardia C sync rag dogfood) ← P01        ───────┘     │  │  │  │   │
TASK-US9-01 [P] (Guardia D RUNTIME_IGNORES)  ← S01                     │  │  │  │   │
                                                                         │  │  │  │   │
TASK-P01    (Sync dogfood)    ← F01, F02, F03, F04,      ───────────────┘  │  │  │   │
                                US6-01, US6-02, US6-03                      │  │  │   │
        │                                                                   │  │  │   │
TASK-P02 [P] (Suite verde + lint) ← P01 + US8-01..03 + US9-01 ────────────┘  │  │   │
        │                                                                       │  │   │
TASK-P03     (CS-1..6 trasversali) ← P02                      ─────────────────┘  │   │
                                                                                    │   │
             (verifica additività sertor_core INVARIATO)       ─────────────────────┘   │
             (verifica additività kit: solo 1 riga RUNTIME_IGNORES) ────────────────────┘
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (rottura silenziosa lascia traccia) | I 4 hook in scope hanno `Write-HookBreadcrumb` definita e invocata sui path degradati; Guardia A1 verde. Spot check manuale: provocando un fallimento, il file `.sertor/.last-hook-error` viene prodotto con campi `hook`/`ts`/`reason`. | TASK-F01..F04, TASK-US8-01 | TESTUALE + MANUALE |
| **US2** (traccia sopravvive, non-fatale) | Ogni hook esce 0 in tutti i path (incluso breadcrumb write failure); `Write-HookBreadcrumb` ha `try{}catch{}` interno; Guardia A2: nessun silent-catch non sanzionato fuori dalla funzione. | TASK-F01..F04, TASK-US8-01 | TESTUALE |
| **US3** (no-op gated → nessuna traccia) | In `memory-capture.ps1`: il gate `if (-not $enabled) { exit 0 }` precede `$root` e `$reason` (struttura verificabile testualmente). Verifica manuale (quickstart §2): `SERTOR_MEMORY` off → `Test-Path .sertor\.last-hook-error` → `False`. | TASK-F01 | TESTUALE + MANUALE |
| **US4** (lettura cieca stato runtime → breadcrumb) | In `version-check.ps1`: l'outer catch catastrofico copre anche la lettura cieca di `.version-check.json` (REQ-006 by-construction); verifica testuale che il catch produca `$reason = "version-check internal error"`. | TASK-F04 | TESTUALE |
| **US5** (nessun segreto nella traccia) | Tutti i `reason` in F01-F04 sono stringhe hook-local fisse o interpolano solo `$LASTEXITCODE` numerico; nessun `$_.Exception.Message` ni output grezzo esterno; verifica testuale. | TASK-F01..F04 | TESTUALE |
| **US6** (agent si fermano sull'asset mancante) | Guardia B verde: i 3 body contengono `STOP` + asset name + `cannot be resolved or read`. Il comportamento LLM runtime è verificabile solo con test live (nota D↔N, US6). | TASK-US6-01..03, TASK-US8-02 | TESTUALE |
| **US7** (fallback host-agnostico, byte-identico) | `test_assets_copilot_parity.py` verde dopo US6-01..03: nessun `.claude/`, slash-command né nome Claude nei 3 body. | TASK-US6-01..03, TASK-P02 | MECCANICO |
| **US8** (guardia anti-regressione) | Guardia A (lint breadcrumb) + Guardia B (assert fallback) + Guardia C (sync rag dogfood) tutte verdi dopo P01. Meta-test: un silent-catch reintrodotto o un fallback rimosso fa fallire la guardia corrispondente. | TASK-US8-01..03 | MECCANICO |
| **US9** (dogfood in sync, lifecycle additivo) | Guardia D: `.sertor/.last-hook-error in RUNTIME_IGNORES` (kit test verde). Guardia C: 3 hook rag dogfood byte-identici al canonico dopo P01. Sync esistente (`test_assets_sync.py`) verde. | TASK-S01, TASK-US8-03, TASK-US9-01, TASK-P01 | MECCANICO |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 — nessun prerequisito (massima parallelizzazione):**
- TASK-S01 [P] (RUNTIME_IGNORES kit — testo/codice puro, indipendente)
- TASK-F01 [P] (memory-capture.ps1 breadcrumb)
- TASK-F02 [P] (rag-freshness.ps1 breadcrumb × 3)
- TASK-F03 [P] (wiki-pending-check.ps1 breadcrumb)
- TASK-F04 [P] (version-check.ps1 breadcrumb + REQ-006)
- TASK-US6-01 [P] (concierge.md fallback)
- TASK-US6-02 [P] (wiki-curator.md fallback)
- TASK-US6-03 [P] (requirements-analyst.md fallback)

**Sprint 2 — dopo Fase 1 + Fase 2 (scrivere le guardie in parallelo):**
- TASK-US8-01 [P] (Guardia A ← F01..F04)
- TASK-US8-02 [P] (Guardia B ← US6-01..03)
- TASK-US8-03 [P] (Guardia C ← da scrivere ora, passerà dopo P01)
- TASK-US9-01 [P] (Guardia D ← S01)

**Sprint 3 — sync dogfood (sblocca Guardia C):**
- TASK-P01 (Sync dogfood — sequenziale, dipende da F01..04 + US6-01..03)

**Sprint finale — suite verde + CS-check:**
- TASK-P02 [P] (suite verde totale ← P01 + tutti i test)
- TASK-P03 (CS-1..6 + additività ← P02)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E10-FEAT-019 — fail-loud breadcrumb hook + fallback agent

Fase SpecKit "tasks" completata per specs/077-fail-loud-hook-agent.
15 task in 5 fasi:
  Fase 0 Setup (1 task):
    TASK-S01 [P]  kit RUNTIME_IGNORES += ".sertor/.last-hook-error" (1 riga additiva)
  Fase 1 Fondazionale (4 task, tutti [P]):
    TASK-F01  memory-capture.ps1 — 1 punto breadcrumb (invocazione delegata)
    TASK-F02  rag-freshness.ps1  — 3 punti (spawn/re-index/worker-crash, soli path muti)
    TASK-F03  wiki-pending-check.ps1 — 1 punto (scan fallita)
    TASK-F04  version-check.ps1 — 1 punto (catch catastrofico + REQ-006 lettura cieca)
  Fase 2 Storia US6/US7 (3 task, tutti [P]):
    TASK-US6-01  concierge.md — fallback guided-setup
    TASK-US6-02  wiki-curator.md — fallback wiki-playbook
    TASK-US6-03  requirements-analyst.md (sertor-flow) — fallback requirements
  Fase 3 Storia US8/US9 guardie (4 task):
    TASK-US8-01 [P]  Guardia A — lint breadcrumb (presenza+no-silent-catch) + meta-test
    TASK-US8-02 [P]  Guardia B — assert fallback 3 agent + meta-test
    TASK-US8-03 [P]  Guardia C — sync rag dogfood byte-identità (buco D-5)
    TASK-US9-01 [P]  Guardia D — RUNTIME_IGNORES assert (gemello version-check)
  Fase 4 Polish/cross-cutting (3 task):
    TASK-P01  sync dogfood (sync.py automatico + copia manuale 3 hook rag)
    TASK-P02 [P]  suite verde totale + lint ruff
    TASK-P03  CS-1..6 trasversali + additività

Natura: ADDITIVO, host-facing. ZERO codice runtime di core. sertor_core INVARIATO.
Artefatti toccati: 4 hook .ps1 + 3 body agent .md + 1 riga kit + 3 nuovi file test.
Rischi coperti:
  R-1 (PowerShell $LASTEXITCODE): controllare il codice di uscita del vehicle oltre al catch
      (documenta nei 4 hook F01-F04).
  R-2 (no-op gated by construction): gate memory-capture precede root/reason — verificato testualmente.
  R-3 (no $_ nel reason): solo stringhe fisse o $LASTEXITCODE numerico — verifica testuale in P03.
  R-4 (buco sync rag dogfood): Guardia C nuova + copia manuale in P01 (scoperta D-5).
Copertura: FR-001..017, RNF-1..6, CS-1..6, US1..9.
Test natura: TESTUALE (US1-statico/US2/US3/US4/US5) + MECCANICO (US6-guardia/US7/US8/US9) +
             MANUALE post-merge (US1-live/US3-live).
Parità Copilot: riuso test_assets_copilot_parity.py esistente (nessun codice nuovo).
Sync dogfood claude/: sertor_installer.sync (wiki-pending-check + wiki-curator) +
                      copia manuale (memory-capture, rag-freshness, version-check, requirements-analyst).
Nessun hook SpecKit eseguito (script assenti); nessuna operazione git.
Template tasks da 076 (setup-plan.ps1/SKILL.md assenti nel repo).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/077-fail-loud-hook-agent/tasks.md` (questo file, nuovo)
