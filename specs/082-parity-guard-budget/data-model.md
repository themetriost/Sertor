# Data Model — E10-FEAT-024 (parity guard + budget altitude)

**Branch**: `082-parity-guard-budget` · **Fase**: Phase 1 (design)

> Feature **solo-test, zero runtime**. Non introduce entità di dominio (`sertor_core` invariato): le
> «entità» qui sono **costanti di test** e le **guardie** (funzioni pure di test) che le consumano.
> Nessuna porta/adapter/engine/servizio/comando coinvolto.

---

## 1. Costanti di soglia e registri (test-data)

### 1.1 `_EXPECTED_RAG_EVENTS` — eventi attesi del wiring Copilot rag (Gruppo A)
| Campo | Valore | Note |
|---|---|---|
| Tipo | `tuple[str, ...]` | costante esplicita nel sorgente del test |
| Valore | `("SessionEnd", "SessionStart", "PreToolUse")` | gli eventi prodotti dai 6 frammenti |
| Commento solidale | lista dei **6 frammenti** (`_copilot_*_specs`) | pattern `_RAG_HOOKS` — visibilità al cambio |
| Granularità | **per-evento**, non per-frammento | limite dichiarato R-1 (`SessionEnd` ×3) |

### 1.2 `_BUDGETS` — registro soglie per-blocco (Gruppo B)
| Chiave `(anchor, rel_path)` | Soglia | Attuale | Headroom |
|---|---|---|---|
| `("sertor_installer", "claude-md-block.md")` | **60** | 52 | 8 |
| `("sertor_installer", "rag/claude-md-block-rag-usage.md")` | **58** | 49 | 9 |
| `("sertor_flow", "claude-md-block-sdlc.md")` | **70** | 64 | 6 |

- Soglie **costanti esplicite** (REQ-012): un aumento è una modifica di codice deliberata e visibile.
- `anchor` seleziona il pacchetto via `sertor_install_kit.read_asset_text(anchor, rel)`.
- Conteggio = `len(text.splitlines())` (esclude newline finale; consistente, ±1-safe).
- **Invariante di coverage:** l'insieme dei `claude-md-block*.md` scoperti (walk dei due pacchetti) ⊆
  chiavi di `_BUDGETS`. Un file scoperto non registrato → fallimento (REQ-011).

### 1.3 `_DECISION_PAYLOAD` — pattern vietato (Gruppo C, Should)
| Campo | Valore | Note |
|---|---|---|
| Tipo | `re.Pattern` | regex compilata |
| Valore | `r"""["']?decision["']?\s*[:=]"""` | chiave `decision` JSON/hashtable |
| Ambito | 3 script rag SessionEnd | `rag-freshness.ps1`, `memory-capture.ps1`, `version-check.ps1` |
| Esclusioni | commenti `<# … #>` e `#` strippati prima della scansione | FR-010 |
| **NON** vieta | `reason` / `-Reason` (param breadcrumb) | evita false-positive FEAT-019 |

---

## 2. Le guardie (funzioni di test pure)

### 2.1 Shape-guard di presenza (nuova — Gruppo A)
- **File:** `packages/sertor/tests/test_copilot_hook_presence.py`
- **Nucleo puro:** `assert_events_present(data: dict, expected: tuple[str, ...]) -> None`
  - per ogni `event` in `expected`: `assert len(data["hooks"].get(event, [])) >= 1`, messaggio nomina
    l'evento mancante;
  - `PreToolUse`: in più, almeno una entry con `matcher` non vuoto.
- **Test del piano reale:** `_rag_wiring(tmp_path, make_runner, COPILOT_CLI)` → `assert_events_present(...)`.
- **Complementarità (FR-004):** indipendente da `assert_valid_copilot_hook_file` (non lo importa né lo
  richiama); schema e presenza devono valere entrambi.
- **Anti-pattern (FR-003):** dal `dict` reso reale rimuove `hooks["PreToolUse"]` → attesa `AssertionError`
  con `"PreToolUse"` nel messaggio; + meta su `dict` sintetico privo di `SessionEnd`.

### 2.2 Budget-test (nuovo — Gruppo B)
- **File:** `tests/unit/test_claude_md_block_budget.py` (suite root, cross-package)
- `_discover_blocks() -> set[(anchor, rel_path)]`: walk dei `Traversable` radice dei due pacchetti,
  filtra basename `claude-md-block*.md`.
- `test_blocks_within_budget`: per ogni `(anchor, rel)` registrato, conteggio ≤ soglia (FR-005/007).
- `test_budget_coverage_exhaustive`: `_discover_blocks() ⊆ _BUDGETS.keys()` (FR-006/REQ-011).
- `test_budget_guard_not_vacuous`: body sintetico 80 righe vs soglia 60 → fallimento (FR-008).

### 2.3 Source-level guard rag (nuova, Should — Gruppo C)
- **File:** `packages/sertor/tests/test_hooks_rag_no_stdout_payload.py` (offline, **nessun** `pytestmark` pwsh)
- `_code_lines(body)`: strip `<# … #>` + righe `#` (riuso pattern cli-invocation/breadcrumb).
- `test_rag_sessionend_scripts_emit_no_decision_payload`: per i 3 script, nessuna code-line matcha
  `_DECISION_PAYLOAD` (FR-009).
- `test_rag_payload_guard_not_vacuous`: snippet artificiale con `decision` → flaggato (FR-011).
- `test_rag_payload_guard_ignores_comment`: commento con `decision`/`reason` → strippato, non flaggato (FR-010).

---

## 3. Guardie esistenti — invariate (additività)
| File | Stato dopo la feature |
|---|---|
| `packages/sertor/tests/test_schema_copilot_hooks.py` | **invariato**, resta verde (schema) |
| `packages/sertor/tests/test_assets_copilot_parity.py` | **invariato** (body `.md`, `.ps1`/`.json` out) |
| `packages/sertor/tests/test_hooks_script_copilot.py` | **invariato** (pwsh-dipendente) |
| `tests/unit/test_assets_sync.py` | **invariato** |
| `install_rag.py` / `surfaces.py` / hook `.ps1` / blocchi `.md` | **invariati** (byte-identici) |
