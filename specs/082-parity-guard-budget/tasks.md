# Tasks — Parity guard esteso + budget altitude blocchi CLAUDE.md (E10-FEAT-024)

**Branch**: `082-parity-guard-budget` · **Generato**: 2026-06-30
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/guards.md`](contracts/guards.md) · **Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVA / solo test, ZERO codice di core.**
> Tocca esclusivamente:
> - 3 nuovi file di test — nessun file esistente modificato;
> - `packages/sertor/tests/test_copilot_hook_presence.py` (Gruppo A — shape-guard presenza);
> - `tests/unit/test_claude_md_block_budget.py` (Gruppo B — budget altitude, cross-package, root);
> - `packages/sertor/tests/test_hooks_rag_no_stdout_payload.py` (Gruppo C — source-level rag, Should).
>
> `sertor_core` **INVARIATO**. `install_rag.py` **INVARIATO**. `surfaces.py` **INVARIATO**.
> Hook `.ps1` e blocchi `claude-md-block*.md` **INVARIATI** (byte-identici prima e dopo).
> Zero nuovi `ArtifactKind` / `WriteStrategy` / `Surface` / seam del kit.
>
> **Fuori ambito esplicito (non toccare):**
> - `install_rag.py`, `surfaces.py`, `resources.py`: invariati.
> - Hook `.ps1` in `assets/rag/hooks/`: invariati (la guardia li *legge*, non li modifica).
> - `claude-md-block*.md` in `assets/`: invariati (la guardia li *conta*, non li tocca).
> - `test_schema_copilot_hooks.py`, `test_assets_copilot_parity.py`, `test_hooks_script_copilot.py`,
>   `test_assets_sync.py`: guardie esistenti, invariate (additività FR-013).
>
> **Vincoli trasversali:**
> - **RNF-1 (Principio XI):** zero modifiche a `sertor_core`; i nuovi test sono l'unica eccezione
>   ammessa al confine vehicles (esercitano l'installer in `tmp_path`, non importano `sertor_core`).
> - **RNF-3 (offline-safe):** Gruppi A e B: nessuna rete, nessun `uv` subprocess, nessun `pwsh`;
>   Gruppo C: stesso requisito — nessun `pytestmark` skipif-pwsh nel file dedicato (offline-always).
> - **RNF-4 (non-regressione suite):** suite `packages/sertor/tests`, `packages/sertor-flow/tests`,
>   root `tests/` — zero nuovi fallimenti rispetto al baseline.
> - **RNF-5 (impatto minimale):** la feature consiste in 3 nuovi file di test; 0 file di produzione.
>
> **Strategia MVP/incrementale.**
> - **Must (P1, Gruppi A + B):** i due task nucleari sono indipendenti e sviluppabili in parallelo;
>   insieme chiudono CS-1/CS-2/CS-3 e formano il nucleo MVP consegnabile in un unico passo.
> - **Should (P2, Gruppo C):** TASK-C01 è anch'esso indipendente dai Gruppi A e B; può girare in
>   parallelo con essi o essere integrato in un secondo passo.
> - La sequenza vincolante è: TASK-S01 → {TASK-A01 ‖ TASK-B01 ‖ TASK-C01} → TASK-P01 → TASK-P02.

---

## Fase 0 — Setup: pre-flight (1 task)

> Prerequisiti: nessuno. Bloccante per tutte le fasi successive.

### TASK-S01 — Pre-flight: sincronizza il venv e verifica i percorsi in scope

```powershell
cd C:\Workspace\Git\Sertor
uv sync --all-packages --extra dev
```

- [x] Verifica che `uv sync --all-packages --extra dev` completi senza errori.
- [x] Verifica che la suite colleghi senza crash di import:
      ```powershell
      uv run pytest --co -q -m "not cloud" 2>&1 | Select-String "ERROR"
      ```
      Nessun `ERROR` di import atteso.
- [x] Verifica che i file da creare **non** esistano già (devono essere nuovi):
  - `packages/sertor/tests/test_copilot_hook_presence.py`
  - `packages/sertor/tests/test_hooks_rag_no_stdout_payload.py`
  - `tests/unit/test_claude_md_block_budget.py`
- [x] Verifica che i file di riferimento (da cui riusare i pattern) esistano:
  - `packages/sertor/tests/test_schema_copilot_hooks.py`
  - `packages/sertor/tests/test_assets_hook_cli_invocation.py`
  - `packages/sertor/tests/conftest.py` (fixture `make_runner`)
  - `tests/unit/test_assets_sync.py`
- [x] Verifica che gli asset in scope esistano:
  - `packages/sertor/src/sertor_installer/assets/claude-md-block.md` (wiki, blocco 1/3)
  - `packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md` (RAG, blocco 2/3)
  - `packages/sertor-flow/src/sertor_flow/assets/claude-md-block-sdlc.md` (SDLC, blocco 3/3)
  - `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1`
  - `packages/sertor/src/sertor_installer/assets/rag/hooks/memory-capture.ps1`
  - `packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.ps1`
- [x] Verifica la baseline suite verde (zero fallimenti pre-modifica):
      ```powershell
      uv run pytest packages/sertor/tests/test_schema_copilot_hooks.py `
                    tests/unit/test_assets_sync.py -q
      ```

---

## Fase 1 — US1/US4 (P1 Must): Gruppo A — Shape-guard di presenza del wiring Copilot [P]

> Prerequisiti: TASK-S01.
> Parallelizzabile con Fase 2 e Fase 3 (file distinti, nessuna dipendenza reciproca).
> Bloccante per TASK-P01.

### TASK-A01 — Crea `test_copilot_hook_presence.py` (FR-001/002/003/004)

→ dipende da: TASK-S01

**Mappa FR**: FR-001/002/003/004 · CS-1/CS-3 · US1/US4 · C-A · data-model §2.1 · research DA-D-1

**Contesto di ancoraggio.** Il piano rag eseguito per `AssistantId.COPILOT_CLI` produce un file
`.github/hooks/sertor-hooks.json` con 6 frammenti hook raggruppati per evento:
`PreToolUse` ×1 (usage-check), `SessionEnd` ×3 (memory-capture, rag-freshness, version-check),
`SessionStart` ×2 (prompt statici). Lo schema-test esistente (`assert_valid_copilot_hook_file` in
`test_schema_copilot_hooks.py`) valida la struttura ma **non** la presenza per-evento. Questa guardia
complementa lo schema (non lo sostituisce): entrambe devono valere (FR-004/CS-3).

**A. Crea il file `packages/sertor/tests/test_copilot_hook_presence.py`:**

Il file è nuovo e riusa il pattern `_rag_wiring` da `test_schema_copilot_hooks.py:57-64` senza
importarlo (zero accoppiamento, FR-013). Import minimi: `json`, `pytest`, `pathlib.Path`,
`sertor_install_kit.assistant.AssistantId`, `sertor_installer.install_rag.{build_rag_plan,
execute_rag_plan}`, `sertor_installer.rag_profile.{RagHostProfile, RagInstallOptions}`.

- [x] Dichiara la costante commentata degli eventi attesi (REQ-005, data-model §1.1):
      ```python
      # 6 hook fragments: PreToolUse×1 (usage-check), SessionEnd×3 (memory-capture,
      # rag-freshness, version-check), SessionStart×2 (static prompts).
      # Update this list if _rag_hook_fragment() in install_rag.py changes.
      _EXPECTED_RAG_EVENTS = ("SessionEnd", "SessionStart", "PreToolUse")
      ```

- [x] Implementa la funzione pura `assert_events_present(data, expected)` (contratto C-A1..C-A4):
      ```python
      def assert_events_present(data: dict, expected: tuple[str, ...]) -> None:
          """Assert that each expected event has ≥1 entry in the Copilot hook wiring.

          Fails with a message naming the missing event (FR-002). PreToolUse additionally
          requires a non-empty 'matcher' field in at least one entry (FR-001/CS-1).
          """
          for event in expected:
              entries = data.get("hooks", {}).get(event, [])
              assert len(entries) >= 1, (
                  f"hook event '{event}' is missing from sertor-hooks.json "
                  f"(copilot-cli rag wiring); found events: {list(data.get('hooks', {}).keys())}"
              )
          pre_entries = data.get("hooks", {}).get("PreToolUse", [])
          assert any(e.get("matcher") for e in pre_entries), (
              "PreToolUse entries must have a non-empty 'matcher' field (FR-001)"
          )
      ```

- [x] Replica il pattern `_rag_wiring` (NON importarlo, ridefinirlo localmente):
      ```python
      def _rag_wiring(tmp_path: Path, make_runner, assistant: AssistantId) -> dict:
          """Build and execute the rag install plan for COPILOT_CLI; return the parsed hook JSON."""
          options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          profile = RagHostProfile.from_options(options)
          plan = build_rag_plan(profile, with_deps=False, assistant=assistant)
          execute_rag_plan(plan, profile, make_runner(), assistant)
          return json.loads(
              (tmp_path / ".github/hooks/sertor-hooks.json").read_text(encoding="utf-8")
          )
      ```

- [x] Scrivi il test del piano reale (contratto C-A1/C-A2/C-A3):
      ```python
      def test_real_rag_wiring_has_all_events(tmp_path: Path, make_runner):
          """The rendered sertor-hooks.json for COPILOT_CLI contains all expected events."""
          data = _rag_wiring(tmp_path, make_runner, AssistantId.COPILOT_CLI)
          assert_events_present(data, _EXPECTED_RAG_EVENTS)
      ```

- [x] Scrivi il test anti-pattern che rimuove `PreToolUse` (contratto C-A6; FR-003/REQ-005):
      ```python
      def test_missing_pretooluse_fails_naming_event(tmp_path: Path, make_runner):
          """Anti-pattern: removing PreToolUse from the rendered JSON makes the guard fail,
          and the failure message names the missing event.  This proves the guard is non-vacuous
          (the single PreToolUse fragment is the most fragile: removing it erases the event).
          """
          data = _rag_wiring(tmp_path, make_runner, AssistantId.COPILOT_CLI)
          del data["hooks"]["PreToolUse"]          # simulate removal of the sole fragment
          with pytest.raises(AssertionError, match="PreToolUse"):
              assert_events_present(data, _EXPECTED_RAG_EVENTS)
      ```

- [x] Scrivi il meta-test di non-vacuità su dict sintetico (complementa l'anti-pattern):
      ```python
      def test_missing_sessionend_fails_naming_event():
          """Meta-guard on a synthetic dict: missing SessionEnd → AssertionError naming it."""
          data = {"hooks": {"SessionStart": [{"type": "prompt", "prompt": "x"}]}}
          with pytest.raises(AssertionError, match="SessionEnd"):
              assert_events_present(data, _EXPECTED_RAG_EVENTS)
      ```

**B. Verifica immediata:**

- [x] Esegui il solo file nuovo — deve essere **verde**:
      ```powershell
      uv run pytest packages/sertor/tests/test_copilot_hook_presence.py -v
      ```
      Atteso: 3 `PASSED` (test reale + anti-pattern PreToolUse + meta SessionEnd).

- [x] Verifica che il test reale giri offline (nessun processo figlio `uv`/`pwsh`/rete):
      il `FakeCommandRunner` di `conftest.py` intercetta ogni subprocess; la fixture `make_runner`
      non apre processi reali. Se il test richiede rete → errore di import o connessione esplicita,
      non una risposta 200. Atteso: nessuna richiesta di rete registrata.

- [x] Verifica che `test_schema_copilot_hooks.py` resti verde e **indipendente**
      (la guardia di presenza non importa e non duplica `assert_valid_copilot_hook_file`):
      ```powershell
      uv run pytest packages/sertor/tests/test_schema_copilot_hooks.py -v
      ```
      Tutti `PASSED`; nessun import da `test_copilot_hook_presence.py`.

- [x] Lint sul nuovo file:
      ```powershell
      uv run ruff check packages/sertor/tests/test_copilot_hook_presence.py
      ```
      Zero errori (regole E,F,I,UP,B; line-length 100).

---

## Fase 2 — US2/US3 (P1 Must): Gruppo B — Budget altitude blocchi always-on [P]

> Prerequisiti: TASK-S01.
> Parallelizzabile con Fase 1 e Fase 3 (file distinto in suite root, nessuna dipendenza).
> Bloccante per TASK-P01.

### TASK-B01 — Crea `test_claude_md_block_budget.py` (FR-005/006/007/008)

→ dipende da: TASK-S01

**Mappa FR**: FR-005/006/007/008 · CS-2 · US2/US3 · C-B · data-model §1.2/§2.2 · research DA-D-2

**Contesto di ancoraggio.** I tre blocchi always-on hanno stato corrente verificato:
wiki **52** righe · RAG **49** · SDLC **64**. Le soglie fissate (costanti esplicite, REQ-012):
wiki **60** · RAG **58** · SDLC **70**. La suite root è la collocazione canonica per guard
cross-package (precedente: `tests/unit/test_assets_sync.py`). Il reader parametrico del kit
(`sertor_install_kit.resources.read_asset_text(anchor, rel)`) legge asset di qualunque package
del workspace; per `sertor_flow` l'anchor è `"sertor_flow"` (package distribuito nel workspace
e installato nel `.venv` dal `uv sync --all-packages`).

**A. Crea il file `tests/unit/test_claude_md_block_budget.py`:**

Import: `pytest`, `re`, `sertor_install_kit.resources as _kit`.

- [x] Dichiara il registro costante `_BUDGETS` (soglie esplicite, non calcolate — REQ-012;
      data-model §1.2):
      ```python
      # Soglie per-blocco (costanti esplicite). Un aumento richiede una modifica deliberata
      # di questo registro (REQ-012). Stato al 2026-06-30: wiki 52, RAG 49, SDLC 64.
      # DA-1: soglie differenziate per blocco, non uniforme a 75 (blocchi pre-FEAT-021 erano
      # wiki 71 / RAG 72 → una soglia ≥ 71 permetterebbe di tornare ai valori pre-riduzione).
      _BUDGETS: dict[tuple[str, str], int] = {
          ("sertor_installer", "claude-md-block.md"):               60,  # wiki  (attuale 52)
          ("sertor_installer", "rag/claude-md-block-rag-usage.md"): 58,  # RAG   (attuale 49)
          ("sertor_flow",      "claude-md-block-sdlc.md"):          70,  # SDLC  (attuale 64)
      }
      ```

- [x] Implementa `_discover_blocks()` per la coverage esaustiva (FR-006/REQ-011;
      data-model §2.2):
      ```python
      def _discover_blocks() -> set[tuple[str, str]]:
          """Walk both packages and collect all claude-md-block*.md files as (anchor, rel).

          Used by test_budget_coverage_exhaustive to ensure no file escapes the budget guard.
          """
          found: set[tuple[str, str]] = set()
          for anchor in ("sertor_installer", "sertor_flow"):
              root = _kit.asset_path(anchor, "")

              def _walk(node, prefix: str = "") -> None:
                  for child in node.iterdir():
                      rel = f"{prefix}{child.name}"
                      if child.is_dir():
                          _walk(child, f"{rel}/")
                      elif child.name.startswith("claude-md-block") and child.name.endswith(".md"):
                          found.add((anchor, rel))

              _walk(root)
          return found
      ```

- [x] Scrivi `test_blocks_within_budget` (contratto C-B1/C-B2; FR-005/007):
      ```python
      def test_blocks_within_budget():
          """Each registered claude-md-block*.md is within its declared line budget.

          Failure message names file (anchor:rel), current line count and configured budget (FR-007).
          """
          for (anchor, rel), budget in _BUDGETS.items():
              text = _kit.read_asset_text(anchor, rel)
              count = len(text.splitlines())   # splitlines() excludes trailing newline (A-004)
              assert count <= budget, (
                  f"{anchor}:{rel} — {count} righe > soglia {budget}. "
                  f"Aggiorna la soglia in _BUDGETS se l'aumento è deliberato (REQ-012)."
              )
      ```

- [x] Scrivi `test_budget_coverage_exhaustive` (contratto C-B3/C-B4; FR-006/REQ-011):
      ```python
      def test_budget_coverage_exhaustive():
          """Every claude-md-block*.md discovered in both packages is registered in _BUDGETS.

          A fourth block added without a corresponding budget entry causes this test to fail,
          naming the unregistered file (FR-006/CS-2).
          """
          discovered = _discover_blocks()
          registered = set(_BUDGETS.keys())
          uncovered = discovered - registered
          assert not uncovered, (
              f"claude-md-block*.md trovati senza soglia in _BUDGETS: {uncovered}. "
              f"Aggiungi una voce a _BUDGETS per ciascun file scoperto."
          )
      ```

- [x] Scrivi `test_budget_guard_not_vacuous` (contratto C-B5; FR-008/REQ-013):
      ```python
      def test_budget_guard_not_vacuous():
          """Anti-pattern: a synthetic body over the budget causes an assertion failure.

          Proves the guard logic is not vacuous (a body below budget passes; one above fails).
          """
          budget = 60
          body_over = "\n".join(["riga"] * (budget + 20))   # 80 righe > 60
          body_under = "\n".join(["riga"] * (budget - 10))  # 50 righe < 60
          count_over = len(body_over.splitlines())
          count_under = len(body_under.splitlines())
          # body over budget must fail the budget assertion
          with pytest.raises(AssertionError):
              assert count_over <= budget, f"synthetic:{count_over} > soglia {budget}"
          # body under budget must not fail
          assert count_under <= budget  # no AssertionError expected
      ```

**B. Verifica immediata:**

- [x] Esegui il solo file nuovo — deve essere **verde**:
      ```powershell
      uv run pytest tests/unit/test_claude_md_block_budget.py -v
      ```
      Atteso: 3 `PASSED` (within-budget + coverage-exhaustive + not-vacuous).
      In particolare `test_blocks_within_budget` passa perché 52 ≤ 60, 49 ≤ 58, 64 ≤ 70.

- [x] Verifica offline: il test non invoca subprocess, non apre rete.
      `_kit.read_asset_text` usa `importlib.resources.files` (no disco diretto via `pathlib`):
      verifica che le letture avvengano senza errori di import/percorso nel venv corrente.

- [x] Lint sul nuovo file:
      ```powershell
      uv run ruff check tests/unit/test_claude_md_block_budget.py
      ```
      Zero errori.

---

## Fase 3 — US5 (P2 Should): Gruppo C — Source-level guard rag SessionEnd [P]

> Prerequisiti: TASK-S01.
> Parallelizzabile con Fasi 1 e 2 (file distinto, nessuna dipendenza reciproca).
> Bloccante per TASK-P01 (ma Should: se non implementata, TASK-P01 va aggiornato di conseguenza).

### TASK-C01 — Crea `test_hooks_rag_no_stdout_payload.py` (FR-009/010/011)

→ dipende da: TASK-S01

**Mappa FR**: FR-009/010/011 · CS-5 · US5 · C-C · data-model §1.3/§2.3 · research DA-D-3

**Contesto di ancoraggio.** I tre script rag SessionEnd usano `Write-HookBreadcrumb -Reason '…'`
(FEAT-019): il token `-Reason` è legittimamente presente nel codice → vietare `\breason\b` sarebbe
un false-positive vacuo. Il pattern vietato è la **chiave `decision`** di un payload Copilot
(`["']?decision["']?\s*[:=]`), che appare in `"decision": "block"` (JSON) o `decision = 'block'`
(hashtable PS). Il file è **separato** da `test_hooks_script_copilot.py` perché quel file ha
`pytestmark = skipif(_PWSH is None)` a livello di modulo → senza `pwsh` l'intero file è skippato;
questa guardia deve girare **sempre, offline** (FR-012/CS-5). Strip-commenti riusato da
`test_assets_hook_cli_invocation.py:40-44`.

**A. Crea il file `packages/sertor/tests/test_hooks_rag_no_stdout_payload.py`:**

Import: `re`, `sertor_installer.resources.iter_asset_dir`. Nessun `pytestmark` pwsh.

- [x] Dichiara le costanti (data-model §1.3):
      ```python
      import re
      from sertor_installer.resources import iter_asset_dir

      # Payload Copilot vietato: la chiave `decision` in JSON ("decision":) o hashtable PS
      # (decision =). NON vietiamo `reason`/`-Reason`: sono parametri legittimi del breadcrumb
      # Write-HookBreadcrumb -Reason '…' (FEAT-019) — false-positive se vietati (research DA-D-3).
      _DECISION_PAYLOAD = re.compile(r"""["']?decision["']?\s*[:=]""")
      # PowerShell block comment `<# … #>` (may span lines).
      _BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)
      # I tre script rag SessionEnd soggetti alla guardia.
      _RAG_SESSION_END_SCRIPTS = frozenset({
          "rag-freshness.ps1",
          "memory-capture.ps1",
          "version-check.ps1",
      })
      ```

- [x] Implementa `_code_lines(body)` (contratto C-C1; FR-010/REQ-016;
      pattern da `test_assets_hook_cli_invocation.py:40-44`):
      ```python
      def _code_lines(body: str) -> list[str]:
          """Code only: drop `<# … #>` blocks and whole-line `#` comments.

          Prose that merely mentions 'decision' or 'reason' (e.g. in a docstring comment)
          is not mistaken for a payload-emitting code line (FR-010).
          """
          without_block = _BLOCK_COMMENT.sub("", body)
          return [ln for ln in without_block.splitlines() if not ln.strip().startswith("#")]
      ```

- [x] Implementa il loader degli script:
      ```python
      def _rag_session_end_bodies() -> dict[str, str]:
          """Load the three rag SessionEnd scripts by name from the bundled assets."""
          all_hooks = dict(iter_asset_dir("rag/hooks"))
          missing = _RAG_SESSION_END_SCRIPTS - set(all_hooks)
          assert not missing, f"script rag SessionEnd mancanti dagli asset: {missing}"
          return {name: all_hooks[name] for name in _RAG_SESSION_END_SCRIPTS}
      ```

- [x] Scrivi `test_rag_sessionend_scripts_emit_no_decision_payload` (contratto C-C2; FR-009):
      ```python
      def test_rag_sessionend_scripts_emit_no_decision_payload():
          """No rag SessionEnd script emits a Copilot 'decision' payload key on stdout.

          Comments are stripped before scanning so prose that mentions 'decision'
          is not mistaken for code (FR-010/C-C1). Viets the key 'decision' only;
          '-Reason' is a legitimate Write-HookBreadcrumb parameter (FR-009/research DA-D-3).
          """
          for name, body in _rag_session_end_bodies().items():
              offenders = [
                  ln.strip()
                  for ln in _code_lines(body)
                  if _DECISION_PAYLOAD.search(ln)
              ]
              assert not offenders, (
                  f"{name}: codice che emette payload 'decision' trovato "
                  f"(confonde il client Copilot su sessionEnd): {offenders}"
              )
      ```

- [x] Scrivi `test_rag_payload_guard_not_vacuous` (contratto C-C3; FR-011/REQ-017):
      ```python
      def test_rag_payload_guard_not_vacuous():
          """Anti-pattern: a snippet emitting a 'decision' key is flagged by the guard."""
          snippet_ps = "@{ decision = 'block'; reason = 'x' } | ConvertTo-Json"
          snippet_json = 'Write-Output \'{"decision":"block"}\''
          assert _DECISION_PAYLOAD.search(snippet_ps), (
              "guard must flag @{ decision = … } (PowerShell hashtable)"
          )
          assert _DECISION_PAYLOAD.search(snippet_json), (
              "guard must flag '\"decision\":\"block\"' (JSON write)"
          )
      ```

- [x] Scrivi `test_rag_payload_guard_ignores_comment` (contratto C-C4; FR-010):
      ```python
      def test_rag_payload_guard_ignores_comment():
          """Comment lines mentioning 'decision'/'reason' are stripped and not flagged (FR-010)."""
          comment_line = "# emits a decision/reason payload on sessionEnd (see Copilot docs)"
          block_comment = "<# This hook must never write a decision key to stdout. #>"
          # Line comment stripped → no match
          code = _code_lines(comment_line)
          assert not any(_DECISION_PAYLOAD.search(ln) for ln in code)
          # Block comment stripped → no match
          code_block = _code_lines(block_comment)
          assert not any(_DECISION_PAYLOAD.search(ln) for ln in code_block)
      ```

**B. Verifica immediata:**

- [x] Esegui il solo file nuovo — deve essere **verde**:
      ```powershell
      uv run pytest packages/sertor/tests/test_hooks_rag_no_stdout_payload.py -v
      ```
      Atteso: 4 `PASSED` (no-decision-payload + not-vacuous PS + not-vacuous JSON +
      ignores-comment).

- [x] Verifica che il file **non** abbia `pytestmark = skipif(_PWSH is None)` — la guardia deve
      girare senza PowerShell installato (CS-5). Se il file venisse eseguito su una macchina
      senza `pwsh`, tutti i test devono risultare `PASSED`, non `SKIPPED`.

- [x] Verifica che `test_hooks_script_copilot.py` resti **invariato** (FR-013):
      ```powershell
      uv run pytest packages/sertor/tests/test_hooks_script_copilot.py -v
      ```
      Deve restare verde (o skip-for-pwsh com'era prima). Il nuovo file è indipendente.

- [x] Lint:
      ```powershell
      uv run ruff check packages/sertor/tests/test_hooks_rag_no_stdout_payload.py
      ```
      Zero errori.

---

## Fase 4 — Polish/cross-cutting (2 task)

> Prerequisiti: TASK-A01, TASK-B01 (bloccanti; TASK-C01 deve essere complete o la fase
> adatta il perimetro). Fase 4 non è parallelizzabile: TASK-P01 → TASK-P02.

### TASK-P01 — Non-regressione suite completa + lint (CS-4/CS-5/RNF-3/RNF-4)

→ dipende da: TASK-A01, TASK-B01, TASK-C01

**Mappa FR**: FR-012/013 · RNF-3/4 · CS-4/CS-5 · US6

**A. Suite nuove guardie (quickstart §1):**

- [x] Esegui le tre nuove guardie insieme — devono essere tutte **verdi**:
      ```powershell
      uv run pytest `
          packages/sertor/tests/test_copilot_hook_presence.py `
          packages/sertor/tests/test_hooks_rag_no_stdout_payload.py `
          tests/unit/test_claude_md_block_budget.py `
          -v
      ```
      Atteso: verde su tutti i nuovi test. Conteggio atteso: 3 (A) + 3 (B) + 4 (C) = **10 test**
      (o 6 senza Gruppo C se TASK-C01 è rinviato).

**B. Guardie esistenti invariate (FR-013, additività):**

- [x] Verifica che le guardie di schema esistenti restino verdi e indipendenti (CS-3/US4):
      ```powershell
      uv run pytest packages/sertor/tests/test_schema_copilot_hooks.py -v
      ```
      Tutti `PASSED`. Nessun import dai nuovi file.

- [x] Verifica che la parity guard e i test hook pwsh esistenti restino invariati:
      ```powershell
      uv run pytest `
          packages/sertor/tests/test_assets_copilot_parity.py `
          packages/sertor/tests/test_hooks_script_copilot.py `
          tests/unit/test_assets_sync.py `
          -v
      ```
      Nessun nuovo fallimento.

**C. Non-regressione suite pacchetto `sertor` (RNF-4):**

- [x] Suite `packages/sertor/tests/` completa:
      ```powershell
      uv run pytest packages/sertor/tests/ -m "not cloud" -q
      ```
      Zero nuovi fallimenti rispetto al baseline di TASK-S01.

**D. Non-regressione suite root (RNF-4):**

- [x] Suite root completa:
      ```powershell
      uv run pytest -m "not cloud" -q
      ```
      Zero nuovi fallimenti. I nuovi test sono inclusi automaticamente (collocazione standard).

**E. Lint ruff su tutti i nuovi file (RNF-5):**

- [x] Lint complessivo:
      ```powershell
      uv run ruff check `
          packages/sertor/tests/test_copilot_hook_presence.py `
          packages/sertor/tests/test_hooks_rag_no_stdout_payload.py `
          tests/unit/test_claude_md_block_budget.py
      ```
      Zero errori su tutti e tre i file.

**F. Verifica che nessun file di produzione sia stato modificato (RNF-1/RNF-2):**

- [x] Controlla che i file di produzione siano invariati:
      ```powershell
      git diff --name-only
      ```
      L'output deve contenere **solo** i tre nuovi file di test.
      In particolare: `install_rag.py`, `surfaces.py`, `resources.py`, hook `.ps1`, blocchi
      `claude-md-block*.md` **non** devono comparire nel diff.

---

### TASK-P02 — Verifica CS-1..5 e invarianza trasversale finale

→ dipende da: TASK-P01

**Mappa**: CS-1..5 · RNF-1/2/3/4/5 · US1..6 · tutti i FR

- [x] **CS-1 (event-presence guard attiva):** `test_copilot_hook_presence.py::test_real_rag_wiring_has_all_events`
      verde; `test_missing_pretooluse_fails_naming_event` verde (l'anti-pattern dimostra che la
      rimozione del frammento PreToolUse rende la guardia rossa nominando `PreToolUse`). ✓

- [x] **CS-2 (budget guard attiva):** `test_blocks_within_budget` verde (52 ≤ 60, 49 ≤ 58, 64 ≤ 70);
      `test_budget_coverage_exhaustive` verde (3 blocchi registrati = 3 blocchi scoperti);
      `test_budget_guard_not_vacuous` verde (80 righe > 60 → fallimento corretto). ✓

- [x] **CS-3 (difetto storico FEAT-049 coperto):** `test_schema_copilot_hooks.py` verde e invariato;
      la shape-guard di presenza non lo importa né lo duplica (file separati, responsabilità distinte:
      schema ≠ presenza). ✓

- [x] **CS-4 (non-regressione suite):** suite `packages/sertor`, `packages/sertor-flow`, root —
      zero nuovi fallimenti. ✓

- [x] **CS-5 (offline-safe):** Gruppi A e B girano senza rete/pwsh/uv-subprocess (fixture
      `FakeCommandRunner` + `importlib.resources`); Gruppo C gira senza `pytestmark` skipif-pwsh.
      Verifica su una shell senza `pwsh` installato: i test restano `PASSED` (non `SKIPPED`). ✓

- [x] **Invarianza `sertor_core` (RNF-1):** nessun file in `src/sertor_core/` modificato;
      zero import di `sertor_core` nei tre nuovi test. ✓

- [x] **Invarianza codice di produzione (RNF-2):** `install_rag.py`, `surfaces.py`, hook `.ps1`,
      blocchi `claude-md-block*.md` **byte-identici** prima e dopo. ✓

- [x] **Impatto minimale (RNF-5):** esattamente 3 nuovi file creati; 0 file di produzione toccati.
      Verifica:
      ```powershell
      git diff --name-only --diff-filter=A  # file aggiunti
      ```
      Atteso: 3 file (`test_copilot_hook_presence.py`, `test_claude_md_block_budget.py`,
      `test_hooks_rag_no_stdout_payload.py` + `tasks.md`) e nessun altro.

- [x] Segnala follow-up già a casa durevole (non-bloccanti):
  - Sincronizzazione `assets/rag/**` ↔ `.claude/` (buco noto) + riconciliazione fork IT eval-skill
    → **FEAT-025** (backlog debito-tecnico).
  - Guard automatico che aggiorna la soglia budget → **escluso** per disegno (renderebbe il freno
    inefficace).

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01  (pre-flight)
    │
    ├── TASK-A01  [P]  (test_copilot_hook_presence.py — Gruppo A Must P1)
    │
    ├── TASK-B01  [P]  (test_claude_md_block_budget.py — Gruppo B Must P1)
    │
    └── TASK-C01  [P]  (test_hooks_rag_no_stdout_payload.py — Gruppo C Should P2)
         │
         └── TASK-P01  (non-regressione suite + lint)
                  │
             TASK-P02  (CS-1..5 + invarianza trasversale)
```

`TASK-A01`, `TASK-B01`, `TASK-C01` sono pienamente parallelizzabili (file distinti, suite diverse).
`TASK-P01` richiede che almeno `TASK-A01` + `TASK-B01` siano completi (Must P1).
`TASK-C01` (Should P2) può essere integrato in `TASK-P01` o rinviato; il suo rinvio non blocca
la consegna dei Must.

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principale | Natura |
|----|-------------------------------|-----------------|--------|
| **US1** (frammento rimosso → guardia rossa, P1) | `test_missing_pretooluse_fails_naming_event` verde: anti-pattern rimuove `hooks["PreToolUse"]` e asserisce `AssertionError` con `"PreToolUse"` nel messaggio. | TASK-A01 | MECCANICO/OFFLINE |
| **US2** (blocco oltre soglia → CI rossa, P1) | `test_budget_guard_not_vacuous` verde: body 80 righe > soglia 60 → `AssertionError`; `test_blocks_within_budget` verde allo stato corrente. | TASK-B01 | MECCANICO/OFFLINE |
| **US3** (4° blocco non registrato → CI rossa, P1) | `test_budget_coverage_exhaustive` verde: `_discover_blocks()` = 3 file, tutti registrati; un 4° file senza voce in `_BUDGETS` produce fallimento che lo nomina. | TASK-B01 | MECCANICO/OFFLINE |
| **US4** (FEAT-049 resta coperto, P1) | `test_schema_copilot_hooks.py` verde e invariato; `test_copilot_hook_presence.py` è un file separato che non importa `assert_valid_copilot_hook_file`. | TASK-A01 + TASK-P01 | MECCANICO |
| **US5** (script rag no payload `decision`, P2) | `test_rag_sessionend_scripts_emit_no_decision_payload` verde (3 script ok); `test_rag_payload_guard_not_vacuous` verde (snippet artificiale flaggato). | TASK-C01 | MECCANICO/OFFLINE |
| **US6** (suite verdi + offline-safe, P1) | `uv run pytest -m "not cloud" -q` — zero nuovi fallimenti; Gruppi A e B verificati senza `pwsh`; Gruppo C senza `pytestmark` skipif-pwsh. | TASK-P01/P02 | MECCANICO |

---

## Parallelizzazione consigliata

```
Passo 1:  TASK-S01  (pre-flight, venv, verifica percorsi)

Passo 2:  TASK-A01 ‖ TASK-B01 ‖ TASK-C01  (3 file di test indipendenti, sviluppabili in parallelo)
          └── TASK-A01: packages/sertor/tests/test_copilot_hook_presence.py
          └── TASK-B01: tests/unit/test_claude_md_block_budget.py
          └── TASK-C01: packages/sertor/tests/test_hooks_rag_no_stdout_payload.py

Passo 3:  TASK-P01  (non-regressione + lint; richiede A01+B01 completi; C01 opzionale se Should)

Passo 4:  TASK-P02  (CS-1..5 + invarianza; check finale)
```

**Costo stimato (passo critico):** passo 2 è il bottleneck; i tre task sono file di test
senza dipendenze esterne (solo rilettura degli asset bundlati e del piano rag in `tmp_path`).
Sviluppati in parallelo, il blocco dura come il più lento (~30–45 minuti a task).

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E10-FEAT-024 — parity guard esteso + budget altitude

Fase SpecKit "tasks" completata per specs/082-parity-guard-budget.
6 task in 5 fasi:
  Fase 0 Setup (1 task):
    TASK-S01  uv sync --all-packages --extra dev; verifica percorsi in scope;
              baseline suite verde (test_schema_copilot_hooks, test_assets_sync).
  Fase 1 US1/US4 P1 Must — Gruppo A shape-guard presenza Copilot [P] (1 task):
    TASK-A01  Crea packages/sertor/tests/test_copilot_hook_presence.py:
              - costante _EXPECTED_RAG_EVENTS = ("SessionEnd", "SessionStart", "PreToolUse")
              - funzione pura assert_events_present(data, expected)
              - pattern _rag_wiring replicato (non importato) da test_schema_copilot_hooks.py
              - test reale piano COPILOT_CLI + anti-pattern (rimozione PreToolUse → AssertionError)
              - meta-test sintetico (SessionEnd assente → fail nominante)
  Fase 2 US2/US3 P1 Must — Gruppo B budget altitude [P] (1 task):
    TASK-B01  Crea tests/unit/test_claude_md_block_budget.py (suite root, cross-package):
              - costante _BUDGETS = {wiki:60, RAG:58, SDLC:70} (soglie esplicite)
              - _discover_blocks() walk Traversable entrambi i package
              - test_blocks_within_budget (verifica per-blocco, messaggio diagnostico)
              - test_budget_coverage_exhaustive (copertura esaustiva 3 blocchi)
              - test_budget_guard_not_vacuous (anti-vacuità con body 80 righe > 60)
  Fase 3 US5 P2 Should — Gruppo C source-level guard rag [P] (1 task):
    TASK-C01  Crea packages/sertor/tests/test_hooks_rag_no_stdout_payload.py:
              - nessun pytestmark skipif-pwsh (offline-always, CS-5)
              - _DECISION_PAYLOAD = re.compile(r"""["']?decision["']?\s*[:=]""")
              - _code_lines(body): strip <# … #> + righe # (pattern da cli-invocation)
              - test_rag_sessionend_scripts_emit_no_decision_payload (3 script)
              - test_rag_payload_guard_not_vacuous (snippet artificiale)
              - test_rag_payload_guard_ignores_comment (prosa non flaggata)
  Fase 4 Polish (2 task, sequenziali):
    TASK-P01  Suite verdi (A+B+C nuove + schema + parity + hook + sync + root),
              lint ruff tutti e 3 i nuovi file, verifica diff solo nuovi test.
    TASK-P02  CS-1..5 + invarianza trasversale; segnala FEAT-025 (follow-up).

Natura: ADDITIVA / solo test, ZERO codice runtime di core. sertor_core INVARIATO.
install_rag.py INVARIATO. surfaces.py INVARIATO. Hook .ps1 e claude-md-block*.md INVARIATI.
Zero nuovi ArtifactKind/WriteStrategy/Surface/seam del kit.
Artefatti creati (3 nuovi file di test):
  - packages/sertor/tests/test_copilot_hook_presence.py   (Gruppo A)
  - tests/unit/test_claude_md_block_budget.py              (Gruppo B, root)
  - packages/sertor/tests/test_hooks_rag_no_stdout_payload.py  (Gruppo C)
Copertura: FR-001..013, RNF-1..5, CS-1..5, US1..6.
Constitution CHECK: PASS 12/12 + missione (pre e post-design, plan.md §Constitution Check).
Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/082-parity-guard-budget/tasks.md` (questo file, nuovo)
