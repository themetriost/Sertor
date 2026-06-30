# Contract — `parity-guard-budget/1` (E10-FEAT-024)

Le tre guardie offline introdotte dalla feature, il loro contratto osservabile e le soglie. Non c'è
un'interfaccia di runtime (feature solo-test): il «contratto» è ciò che la CI garantisce.

---

## C-A — Shape-guard di presenza del wiring Copilot rag

**File:** `packages/sertor/tests/test_copilot_hook_presence.py` · **Offline** (no rete/`uv`/`pwsh`).

**Input:** `sertor-hooks.json` reso dal piano rag per `AssistantId.COPILOT_CLI`, ottenuto eseguendo
`build_rag_plan` + `execute_rag_plan` in `tmp_path` (pattern `_rag_wiring`).

**Garanzie:**
| ID | Garanzia |
|---|---|
| C-A1 | `hooks["SessionEnd"]` ha ≥1 entry |
| C-A2 | `hooks["SessionStart"]` ha ≥1 entry |
| C-A3 | `hooks["PreToolUse"]` ha ≥1 entry con `matcher` non vuoto |
| C-A4 | Se un evento atteso è assente → `AssertionError` che **nomina** l'evento |
| C-A5 | Indipendente da `assert_valid_copilot_hook_file` (complementa, non sostituisce) |
| C-A6 | Anti-pattern: rimosso `hooks["PreToolUse"]`, la guardia fallisce nominando `PreToolUse` |

**Costante:** `_EXPECTED_RAG_EVENTS = ("SessionEnd", "SessionStart", "PreToolUse")` (commento solidale =
6 frammenti). **Limite dichiarato:** granularità per-evento; cattura la rimozione dell'ultimo frammento
di un evento (es. il solo `PreToolUse`).

---

## C-B — Budget altitude dei blocchi `claude-md-block*.md`

**File:** `tests/unit/test_claude_md_block_budget.py` (root, cross-package) · **Offline**.

**Soglie (costanti esplicite, REQ-012):**
| Blocco | `(anchor, rel_path)` | Soglia | Attuale |
|---|---|---|---|
| wiki | `("sertor_installer", "claude-md-block.md")` | **60** | 52 |
| RAG | `("sertor_installer", "rag/claude-md-block-rag-usage.md")` | **58** | 49 |
| SDLC | `("sertor_flow", "claude-md-block-sdlc.md")` | **70** | 64 |

**Conteggio:** `len(read_asset_text(anchor, rel).splitlines())`.

**Garanzie:**
| ID | Garanzia |
|---|---|
| C-B1 | Per ogni blocco registrato, conteggio ≤ soglia, altrimenti fallisce |
| C-B2 | Messaggio di fallimento nomina file (`anchor:rel`), conteggio corrente, soglia |
| C-B3 | Coverage esaustiva: ogni `claude-md-block*.md` scoperto nei due pacchetti ⊆ chiavi `_BUDGETS` |
| C-B4 | Un 4° blocco non registrato → fallisce nominandolo |
| C-B5 | Anti-pattern: body sintetico sopra-soglia → assertion fallita |

---

## C-C — Source-level guard rag SessionEnd (Should)

**File:** `packages/sertor/tests/test_hooks_rag_no_stdout_payload.py` · **Offline** (nessun `pytestmark`
pwsh).

**Ambito:** `rag-freshness.ps1`, `memory-capture.ps1`, `version-check.ps1` (asset `rag/hooks/`).

**Pattern vietato:** `_DECISION_PAYLOAD = re.compile(r"""["']?decision["']?\s*[:=]""")` — la chiave
`decision` di un payload Copilot (JSON o hashtable). **Non** vieta `reason`/`-Reason` (legittimo nel
breadcrumb FEAT-019).

**Garanzie:**
| ID | Garanzia |
|---|---|
| C-C1 | Strip `<# … #>` + righe `#` prima della scansione (prosa non scambiata per codice) |
| C-C2 | Nessuna code-line dei 3 script matcha `_DECISION_PAYLOAD` |
| C-C3 | Anti-pattern: snippet `@{ decision = 'block'; reason = 'x' } | ConvertTo-Json` → flaggato |
| C-C4 | Commento che menziona `decision`/`reason` → strippato, non flaggato |

---

## Invarianti trasversali
- **Offline-safe (CS-5):** nessun assert critico richiede rete, `uv` subprocess o `pwsh`.
- **Additività (CS-4):** guardie esistenti (`test_schema_copilot_hooks.py`,
  `test_assets_copilot_parity.py`, `test_hooks_script_copilot.py`, `test_assets_sync.py`) invariate e verdi.
- **Zero runtime (RNF-1/5):** `sertor_core` e il codice di produzione (`install_rag.py`, `surfaces.py`,
  hook `.ps1`, blocchi `.md`) byte-identici prima e dopo.
