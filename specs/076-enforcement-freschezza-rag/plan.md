# Implementation Plan — enforcement deterministico della freschezza RAG (hook)

**Branch**: `076-enforcement-freschezza-rag` · **Spec**: [`spec.md`](./spec.md) · **Data**: 2026-06-24
**Epica**: debito-tecnico (E10) · **Feature**: FEAT-011 · **Status**: Plan (design completo)

## Summary
Spostare i due passi meccanici del *rituale di step* (re-index = punto 5, smoke = punto 8) dalla
discrezione dell'agente a un **harness deterministico**: un **hook a fine sessione**
(`rag-freshness.ps1`, `SessionEnd`) che re-indicizza via vehicle e verifica la salute via `doctor`,
persistendo l'esito su `.sertor/.rag-health.json`; un **segnale a inizio sessione** (`SessionStart`)
che ripesca l'esito e, se degradato, **induce** la correzione prima del lavoro dell'agente. La
feature è **additiva e host-facing**: **nessun codice di `sertor-core`** (Principio XI — l'hook
*consuma* `sertor-rag index`/`doctor`, mai importa la libreria), e wiring di distribuzione via
`sertor install rag` con parità Claude / Copilot CLI e lifecycle install/upgrade/uninstall.

## Technical Context
- **Linguaggio/runtime**: PowerShell (script hook host-agnostici, stdlib) + Python 3.11+ (installer
  `sertor`/`sertor-install-kit`, stdlib-only nel kit).
- **Dipendenze consumate (su `master`)**: `sertor-rag index .` (incrementale: manifest FEAT-009 +
  cache embeddings FEAT-019), `sertor-rag doctor [--json]` (E12-FEAT-001, 4 aree, exit-code gate).
- **Meccanismo riusato**: pattern hook installer di `memory-capture`/`sertor-rag-usage-check`
  (`install_rag.py`); seam di parità `AssistantProfile`/`HookEntrySpec`/`render_copilot_hooks` (kit).
- **Storage**: file di stato JSON `.sertor/.rag-health.json` (schema `rag.health/1`), gitignored.
- **Confine D↔N**: l'hook è meccanico (re-index, doctor, persistenza, induzione); **nessun LLM**
  (NFR-5). Il giudizio/esecuzione della correzione resta all'agente.
- **NEEDS CLARIFICATION**: **nessuno** — le 4 decisioni di scope (DA-1..4) sono fisse nella spec; le
  2 forche di *come* (DA-D-r1/r2) sono risolte in [`research.md`](./research.md) (D-1/D-2).

## Constitution Check — **PASS 12/12 + Missione PASS** (pre e post-design, nessuna deroga)

> Costituzione v1.4.0 (12 principi I–XII + gate «Allineamento alla missione»).

| # | Principio | Esito | Motivazione |
|---|---|---|---|
| I | La libreria è il prodotto | PASS | nessun codice di core; l'hook è un consumatore esterno via CLI |
| II | Dettagli sostituibili / no lock-in | PASS | hook PowerShell + JSON locale; nessuna dipendenza nuova; vehicle astratti |
| III | YAGNI / no over-engineering | PASS | nessun nuovo `ArtifactKind`/`Surface`/seam; riuso dei modelli installer esistenti |
| IV | Errori avvolti al boundary | PASS | hook non-fatale (`try/catch`→exit 0); gli errori dei vehicle restano nei vehicle |
| V | Misurabilità | PASS | verdetto strutturato `doctor` + stato persistito ispezionabile; CS-1..5 misurabili |
| VI | Idempotenza / non-distruttività | PASS | install merge-dedup additivo; stato `healthy` riscritto (no oscillazione, NFR-6) |
| VII | Funzioni piccole / basso nesting | PASS | script thin (orchestrazione), nessuna logica di change-detection (FR-002) |
| VIII | Config centralizzata | PASS | `RUNTIME_IGNORES` (unica fonte) esteso; nessun default hardcodato sparso |
| IX | Osservabilità | PASS | il re-index via vehicle CLI cabla `enable_observability` (Principio XI realizzato) |
| X | Capacità host-agnostiche | PASS | hook senza assunzioni hardcoded; distribuito a Claude+Copilot con parità (NFR-4) |
| XI | Consumo via vehicles | PASS | **cardine**: solo `sertor-rag` CLI, mai `import sertor_core` (FR-004/NFR-5) |
| XII | Fail loud, fix the cause | PASS | fail-loud a due tempi (stato persistito + messaggio + induzione); buco `where` dichiarato e promosso, non sepolto |

### Gate «Allineamento alla missione» — **PASS**
La freschezza del RAG è **al cuore** della stella polare (qualità del contesto reso all'agente *nel
tempo*). Un indice stantio è esattamente «l'agente ragiona su contesto non reale» — il fallimento che
RAG+wiki+lint esistono per prevenire. Spostare i passi di freschezza in un harness deterministico
**realizza** la prevenzione invece di affidarla alla memoria dell'agente. Rafforza la fusione
code+doc (tiene fresco l'unico corpus). Complementa, senza sovrapporsi, la drift-detection FEAT-012
(quella *osserva*, questa *previene a monte*). Non deriva su concern periferici.

### Complexity Tracking
**Nessuna deviazione tracciata.** La feature è additiva, riusa i seam esistenti, non tocca il core,
non introduce dipendenze. L'unica modifica al kit (`+ ".sertor/.rag-health.json"` in
`RUNTIME_IGNORES`) è additiva e non-breaking.

## Decisioni di design (forche residue risolte — research D-1/D-2)
- **DA-D-r1 (file di stato) → RISOLTA**: `.sertor/.rag-health.json` (sotto la radice runtime
  `.sertor/`, igiene radice feature 016), formato **JSON** schema `rag.health/1`
  (`verdict`/`timestamp`/`reason` minimi + `areas`/`exit_code` additivi). A `healthy` il file è
  **riscritto** (non cancellato) → no-op all'avvio, no loop (INV-1/NFR-6). **Azione necessaria**:
  estendere `RUNTIME_IGNORES` (kit) con `.sertor/.rag-health.json` (oggi non coperto). Contratto:
  [`contracts/rag-health-state.md`](./contracts/rag-health-state.md).
- **DA-D-r2 (aggancio SessionStart) → RISOLTA**: **voce/script dedicato** `rag-freshness-start.ps1`
  (Claude) + voce `SessionStart` propria, **NON** riuso di `wiki-session-start.ps1` (isolamento
  FR-016 + lifecycle granulare per-capacità `rag`). Su **Copilot CLI** il SessionStart è un **prompt
  nativo statico** (nessuno script; A-005) che istruisce l'agente a leggere lo stato e indurre.
  Contratto: [`contracts/freshness-hook-wiring.md`](./contracts/freshness-hook-wiring.md).

## Phase 0 — Research
→ [`research.md`](./research.md): D-0 ancoraggio (hook pattern, wiring installer, render Copilot,
vehicle, guardia sync); D-1/D-2 forche risolte; D-3 coesistenza/guardia; D-4 reclassificazione
CLAUDE.md; D-5 promozione Out-of-Scope; D-6 confini/non-regressione.

## Phase 1 — Design & contracts
- [`data-model.md`](./data-model.md): file di stato (§1), script hook (§2), wiring per-assistente
  (§3), artefatti installer (§4), lifecycle (§5), invarianti.
- [`contracts/`](./contracts/): `rag-health-state.md` (schema `rag.health/1`),
  `freshness-hook-wiring.md` (voci native Claude/Copilot).
- [`quickstart.md`](./quickstart.md): 9 verifiche manuali (re-index zero-cost, fail-loud,
  induzione, clear, non-fatale, distribuzione/parità, lifecycle, guardia sync, D↔N).

## Implementazione prevista (mappa file — riferimento per `tasks`)
**Asset bundlati** (`packages/sertor/src/sertor_installer/assets/`):
- `rag/hooks/rag-freshness.ps1` (NUOVO — SessionEnd: index+doctor+persist, gemello memory-capture).
- `rag/hooks/rag-freshness-start.ps1` (NUOVO — SessionStart Claude: ripesca+induce).
- `rag/settings.rag-freshness.json` (NUOVO — voce SessionEnd Claude) + `rag/settings.rag-freshness-start.json`
  (NUOVO — voce SessionStart Claude). *(Copilot: generati via sentinel, nessun asset statico.)*

**Installer** (`packages/sertor/src/sertor_installer/install_rag.py`):
- costanti `_FRESHNESS_HOOK_*`/`_FRESHNESS_START_*` + 2 sentinel Copilot; `_copilot_freshness_*_specs()`.
- `build_rag_plan`: +2 FILE (start solo Claude) +2 SETTINGS_MERGE (SessionEnd/SessionStart, per-assistente).
- `_rag_hook_fragment`: dispatch dei 2 nuovi sentinel (art-aware, riuso `render_copilot_hooks`).
- `sertor_owned_paths`: +owned_files (i 2 script, start solo Claude); shared_edit settings già coperto.
- uninstall/upgrade: già art-aware (FILE→remove/update; SETTINGS_MERGE→remove_settings_entries con
  `delete_if_empty` per `sertor-hooks.json`) — nessuna logica nuova.

**Kit** (`packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py`):
- `RUNTIME_IGNORES += (".sertor/.rag-health.json",)` (additivo).

**Dogfood** (`.claude/`): copia di `rag-freshness.ps1`/`rag-freshness-start.ps1` in `.claude/hooks/`
+ voci in `.claude/settings.json` (propagate dall'asset, verificate dalla guardia FR-024).

**Governance** (`CLAUDE.md`): annotare gli step 5 e 8 del rituale «enforced via hook (E10-FEAT-011)»
con la nota D↔N (FR-019, research D-4). Riallineare `.claude/` se serve.

**Test** (offline, no cloud):
- `packages/sertor/tests/test_install_rag_freshness.py` (NUOVO): deposito Claude/Copilot, formato
  nativo, voce SessionEnd + SessionStart, owned_paths coverage, uninstall/upgrade granulare,
  isolamento da memory-capture.
- guardia di sync bundlato↔dogfood mirata agli hook rag (FR-024, research D-3).
- copertura `RUNTIME_IGNORES` (kit) per la nuova riga.

## Promozione Out-of-Scope (regola «si promuovono, non restano appesi» — research D-5)
- **Smoke col filtro metadata `where`** → **nuova FEAT-011 nel backlog epica usabilità (E12)**,
  `requirements/usabilita/epic.md` §8 (owner di `doctor`, Should): estensione di `doctor` con un
  *check-query* metadata-filtered. **DA ESEGUIRE al plan/decomposizione** (aggiunta riga al backlog).
- **Staleness forte cross-processo del server MCP** → debito **osservabilita**/server MCP (già
  tracciato, finding 2026-06-23): cross-ref, nessuna riga nuova.
- **Drift-detection** → epica **osservabilita FEAT-012** (già esistente): cross-ref, nessuna riga nuova.

## Out of scope (questa feature)
- Modifiche al motore di re-index o a `doctor` (li consuma, non li estende).
- Query reale col filtro `where` dentro l'hook (buco dichiarato → E12).
- Client MCP standalone dall'hook a `SessionEnd` (mitigato dal reconnect indotto al SessionStart).

## Nota di processo
`.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** nel repo →
parametri ricavati per **convenzione dal branch** (forma da `075-guided-setup`); **nessun hook
SpecKit eseguito**. **MCP `sertor-rag` interrogato** in apertura (`search_code` sul wiring installer
hook — nessun errore tool); il resto ancorato con `Read`/`Grep` su file a posizione nota. Git **non**
eseguito (delegato al `configuration-manager`).
