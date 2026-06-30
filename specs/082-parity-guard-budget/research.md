# Research — Parity guard esteso (.ps1/.json) + budget altitude blocchi CLAUDE.md (E10-FEAT-024)

**Branch**: `082-parity-guard-budget` · **Fase**: Phase 0 (design) · **Data**: 2026-06-30

Risolve le tre forche di *come* (DA-D-1/2/3) lasciate aperte dalla spec. Le **decisioni di scope**
(soglie 60/58/70 differenziate; Gruppo C in ambito come Should) sono **già fissate** e non si
riaprono. Tutto ciò che segue è ancorato a codice reale, verificato via MCP `sertor-rag` e `Read`.

> **Nota MCP.** Il server `sertor-rag` è stato interrogato in apertura (`search_code` sul wiring hook
> Copilot e sui test di parità). **Nessun errore tool.** L'ancoraggio puntuale (numeri di riga, conteggi
> righe) è stato poi confermato con `Read`/walk del filesystem — i fatti puntuali a posizione nota sono
> l'eccezione legittima alla regola MCP-first.

---

## Stato di partenza verificato (dato, non da progettare)

| Fatto | Valore verificato | Fonte |
|---|---|---|
| Blocco wiki | **52** righe (`splitlines()`) | `assets/claude-md-block.md` |
| Blocco RAG | **49** righe | `assets/rag/claude-md-block-rag-usage.md` |
| Blocco SDLC | **64** righe | `sertor-flow .../assets/claude-md-block-sdlc.md` |
| Frammenti wiring Copilot rag | **6** funzioni-frammento, dispatch `_rag_hook_fragment()` | `install_rag.py:695-715` |
| Eventi prodotti dai 6 frammenti | `PreToolUse` ×1 · `SessionEnd` ×3 · `SessionStart` ×2 | `install_rag.py` + tabella requirements §1.2 |
| Render nativo | `render_copilot_hooks(events) -> {"version":1,"hooks":{<Event>:[...]}}` | `surfaces.py:162-190` |
| Schema-guard esistente | `assert_valid_copilot_hook_file` valida lo *schema*, **non** la *presenza* per-evento | `test_schema_copilot_hooks.py:25-43` |
| Esecuzione piano offline | `_rag_wiring(tmp_path, make_runner, COPILOT_CLI)` → legge `sertor-hooks.json` | `test_schema_copilot_hooks.py:57-64` |
| 3 script rag SessionEnd | `rag-freshness.ps1`, `memory-capture.ps1`, `version-check.ps1` | `assets/rag/hooks/` |
| Discovery asset | `iter_asset_dir(rel)` walk ricorsivo; `asset_path(rel)` → `Traversable`; kit parametrico su anchor | `resources.py` |

**Trabocchetto identificato (false-positive `reason`).** I tre script rag SessionEnd usano la funzione
`Write-HookBreadcrumb -Reason '…'` (breadcrumb fail-loud, FEAT-019). Quindi il **token nudo `reason`
è legittimamente presente nel codice** di quegli script. Una guardia Gruppo C che vietasse `\breason\b`
sarebbe **vacuamente rossa** sull'attuale. → Il segnale discriminante da vietare è la **chiave
`decision`** di un payload Copilot (JSON/hashtable), non `reason`. (Vedi DA-D-3.)

---

## DA-D-1 — Collocazione della shape-guard di presenza (Gruppo A)

### Decisione
**File dedicato nuovo** `packages/sertor/tests/test_copilot_hook_presence.py`. La guardia è una
**funzione pura** `assert_events_present(data, expected_events)` che opera sul `dict` già parsato; il
test del piano reale riusa `_rag_wiring` (pattern `tmp_path` di `test_schema_copilot_hooks.py`).

### Razionale
- **Schema ≠ presenza (FR-004/REQ-007).** Tenere la presenza in un file separato rende esplicito che
  *complementa* lo schema senza duplicarlo: le due guardie restano indipendenti (US4). Estendere
  `test_schema_copilot_hooks.py` confonderebbe le due responsabilità nello stesso modulo.
- **Riuso del pattern, non del codice.** Il test del piano reale replica `_rag_wiring` (3 righe:
  `build_rag_plan` → `execute_rag_plan` con `make_runner()` → `json.loads` del file). `make_runner` è
  una fixture di pacchetto già disponibile (usata da `test_schema_copilot_hooks.py`); è offline (no
  rete, no `uv`, no `pwsh`). Non importo nulla dallo schema-test → zero accoppiamento (FR-013).

### Forma della guardia + anti-vacuità (FR-001/002/003/005)
- Costante commentata `_EXPECTED_RAG_EVENTS = ("SessionEnd", "SessionStart", "PreToolUse")` con il
  commento della **lista dei 6 frammenti attesi** (pattern `_RAG_HOOKS` di
  `test_assets_hook_breadcrumb.py:33`) → se cambia il numero di frammenti, l'aggiornamento è visibile.
- `assert_events_present(data, expected)`: per ogni evento atteso asserisce `len(data["hooks"][event]) >= 1`;
  l'`AssertionError` **nomina** l'evento mancante. `PreToolUse` richiede in più `matcher` non vuoto.
- **Granularità per-evento — limite dichiarato (R-1).** `SessionEnd` ha 3 frammenti: rimuoverne *uno*
  lascia l'evento presente, quindi la shape-guard per-evento **non** lo cattura. Cattura invece la
  rimozione dell'**ultimo** frammento di un evento — segnatamente `PreToolUse`, che ha **un solo**
  frammento (`_copilot_rag_hook_specs`, l'`usage-check`): rimuoverlo fa sparire l'intero evento. Questo
  è esattamente lo scenario CS-1. Il limite è documentato nella docstring del test e nel commento della
  lista frammenti.
- **Anti-pattern (FR-003/REQ-005).** Test negativo che parte dal `dict` reso reale, **elimina la chiave
  `PreToolUse`** (modella la rimozione del solo frammento PreToolUse) e asserisce che
  `assert_events_present` solleva `AssertionError` il cui messaggio contiene `"PreToolUse"`. Un secondo
  meta-test verifica la non-vacuità su un `dict` sintetico privo di `SessionEnd`.

### Scartato
- *Estensione di `test_schema_copilot_hooks.py`*: mescolerebbe schema e presenza (contro FR-004).
- *Anti-pattern via rimozione di un frammento da una lista di 3 su `SessionEnd`*: non produrrebbe
  fallimento (l'evento resta presente) → sarebbe un test fuorviante. Si usa `PreToolUse` (1 frammento).

---

## DA-D-2 — Collocazione del budget-test (Gruppo B)

### Decisione
**Suite root** `tests/unit/test_claude_md_block_budget.py`. Soglie come **costanti esplicite**;
discovery esaustiva via **walk del `Traversable`** di entrambi i pacchetti.

### Razionale
- **È intrinsecamente cross-package.** I 3 blocchi vivono in `sertor` (×2) e `sertor-flow` (×1). La
  suite **root** è la casa naturale dei guard cross-package — precedente diretto:
  `tests/unit/test_assets_sync.py` importa `sertor_installer` dalla root. Entrambi i pacchetti sono
  membri del workspace `uv` (installati nel `.venv`), quindi importabili dalla root senza trucchi.
- L'alternativa (test nel pacchetto `sertor` con import lazy di `sertor_flow`, come
  `test_assets_copilot_parity.py:91-97`) è valida ma colloca un guard *cross-package* dentro *un*
  pacchetto: meno leggibile («perché il budget SDLC è nei test di `sertor`?»). La root è più onesta.

### Discovery esaustiva + soglie (FR-005/006/007/008)
- **Registro costante** (REQ-012, soglie non calcolate a runtime):
  ```
  _BUDGETS = {
      ("sertor_installer", "claude-md-block.md"):              60,  # wiki  (attuale 52)
      ("sertor_installer", "rag/claude-md-block-rag-usage.md"): 58,  # RAG   (attuale 49)
      ("sertor_flow",      "claude-md-block-sdlc.md"):          70,  # SDLC  (attuale 64)
  }
  ```
  Chiave = `(anchor, rel_path)`; valore = soglia (costante esplicita). L'anchor seleziona il pacchetto
  via `sertor_install_kit.read_asset_text(anchor, rel)` (entrambi i pacchetti passano per il reader
  parametrico del kit — `sertor_installer.read_asset_text` ne è il wrapper a anchor fisso).
- **Conteggio (REQ-009, A-004):** `len(read_asset_text(...).splitlines())` — esclude la newline finale,
  consistente; l'headroom 8/9/6 assorbe ogni differenza ±1.
- **Messaggio diagnostico (FR-007):** su sforamento nomina `f"{anchor}:{rel}"`, il conteggio corrente e
  la soglia configurata.
- **Coverage esaustiva (FR-006/REQ-010/011):** una funzione `_discover_blocks()` walk-a i `Traversable`
  radice di **entrambi** i pacchetti (`asset_path(anchor, "")` + walk ricorsivo, filtrando solo i file
  il cui basename combacia con `claude-md-block*.md`) e confronta l'insieme scoperto con le chiavi di
  `_BUDGETS`. Un file scoperto **non registrato** → fallimento che lo nomina. *(Si walk-a il `Traversable`
  e si legge solo i file che matchano il pattern, evitando di leggere asset binari/irrilevanti — più
  robusto di `iter_asset_dir("")` che leggerebbe il contenuto di tutto l'albero.)*
- **Anti-vacuità (FR-008/REQ-013):** test che applica la logica di soglia a un **body sintetico**
  sopra-soglia (es. 80 righe vs soglia 60) → assertion fallita; + meta che un body sotto-soglia passa.

### Scartato
- *Test nel pacchetto `sertor`*: valido ma meno leggibile per un guard cross-package (vedi sopra).
- *Soglia uniforme 75 della raccomandazione analista*: **scartata** (decisione fissata DA-1) — lascerebbe
  ricrescere i blocchi oltre i valori pre-FEAT-021 (wiki 71/RAG 72).

---

## DA-D-3 — Forma della source-level guard rag SessionEnd (Gruppo C, Should)

### Decisione
**File dedicato nuovo** `packages/sertor/tests/test_hooks_rag_no_stdout_payload.py`. Vieta la **chiave
`decision`** di un payload (JSON/hashtable) nel **codice** (commenti strippati) dei 3 script rag
SessionEnd; **non** `reason` (false-positive sul breadcrumb).

### Razionale
- **Perché NON estendere `test_hooks_script_copilot.py`** (dove vive già
  `test_no_dual_field_in_pending_check_source`): quel modulo ha un **`pytestmark = skipif(_PWSH is None)`
  a livello di modulo** → senza `pwsh` l'intero file è skippato. La guardia Gruppo C **deve girare
  offline, sempre** (FR-012/CS-5): metterla lì la renderebbe muta sulle macchine senza PowerShell. →
  File separato, nessun `pytestmark` pwsh.
- **Strip commenti (FR-010/REQ-016):** riuso del pattern di `test_assets_hook_cli_invocation.py:30-44`
  e `test_assets_hook_breadcrumb.py:28-41`: rimuovi i blocchi `<# … #>` (regex `DOTALL`) e le righe il
  cui `strip()` inizia con `#`. Convenzione del repo: ogni guard ridefinisce localmente il piccolo
  helper (non c'è un modulo condiviso) → resto **additivo**, zero modifiche ai file esistenti.
- **Pattern vietato preciso (FR-009/REQ-015):** la chiave `decision` di un payload Copilot, in forma
  JSON **o** hashtable PowerShell:
  ```
  _DECISION_PAYLOAD = re.compile(r"""["']?decision["']?\s*[:=]""")
  ```
  Cattura `"decision":`, `'decision' :`, `decision =` (hashtable `@{ decision = … }`). **Non** cattura
  il parametro `-Reason` del breadcrumb né un token `reason` isolato. Il `decision`-key è il **segnale
  discriminante** di una decisione hook Copilot: un payload `sessionEnd` che confonde il client ha
  *sempre* una chiave `decision`. Vietare solo questa evita il false-positive su `reason` e resta
  fedele all'intento (no payload Copilot-decision su stdout).
- **Anti-vacuità (FR-011/REQ-017):** snippet artificiale
  `@{ decision = 'block'; reason = 'x' } | ConvertTo-Json` (e/o `Write-Output '{"decision":"block"}'`)
  → la guardia lo flagga; + meta che un commento `# emits a decision/reason payload …` viene strippato
  e **non** flaggato (FR-010).

### Scartato
- *Vietare `\b(decision|reason)\b`*: rosso vacuo sull'attuale per via di `-Reason` del breadcrumb.
- *Estendere `test_hooks_script_copilot.py`*: il `skipif` pwsh di modulo viola l'offline-safe (CS-5).
- *Esecuzione `pwsh` reale dei rag hook*: fuori ambito (non offline-safe, duplicativo); resta il guard
  pwsh-dipendente esistente per i wiki hook.

---

## Estensioni / promozioni (tracciamento scope)

Le voci fuori ambito che sono **capacità future reali** sono già promosse a case durevoli **dalla spec**;
questo plan non introduce nuovi rinvii:
- Sincronizzazione `assets/rag/**` ↔ `.claude/` (buco noto) e riconciliazione fork IT eval-skill →
  **FEAT-025** (backlog epica debito-tecnico).
- Estensione invarianti di *contenuto* ai `.ps1`/`.json` (no `.claude/` nel codice script) → **Won't**
  dichiarato (beneficio marginale, gli script non sono body LLM-facing).

Nessun rinvio reale resta sepolto in `specs/082-…/`.
