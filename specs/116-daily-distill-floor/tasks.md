# Tasks: Daily distill floor (E10-FEAT-039)

**Feature**: 116-daily-distill-floor | **Branch**: `116-daily-distill-floor`
**Input**: [spec.md](spec.md) · [plan.md](plan.md) · [research.md](research.md) ·
`requirements/debito-tecnico/daily-distill-floor/requirements.md`

Ordine per dipendenza. `[P]` = parallelizzabile. Confine D↔N: il tool trova (deterministico), l'agente
giudica, l'hook esige.

> **STATO (2026-07-22).** ✅ **Implementato** con il DESIGN FINALE (vedi banner in spec.md): l'enforcement
> è un hook **`PreToolUse` che BLOCCA il merge** (non il nudge persistente della prima stesura), e il tool
> `distill-audit` è **advisory** (hint allegato al blocco), non il gate. Fatto: T001–T004 (tool + 13 test),
> T005–T006 (hook `distill-floor` merge-gate + 12 test), T007–T009 (wiring Claude PreToolUse + parità
> Copilot + sync), T011 (blocco `SERTOR:WIKI-RITUAL` + budget), T012 (playbook), T014 (gate verde: root
> 1241 · sertor 552 · kit 194 · flow 142, ruff clean), T015 (prova LIVE: `deny` su merge reale). Residuo:
> T016 (EXEC/epic + record/distill al merge). SessionStart heads-up: codice+test presenti, **non cablato**
> (superficie minima); attivabile in seguito.

## Phase A — Tool `distill-audit` (core, US1)

- **T001** `contracts.py`: aggiungi `DistillAuditResult` (`wiki.distill_audit/1`) — campi `debt:int`,
  `threshold:int`, `corpus_files:int`, `candidates:list[dict]` (`{name, frequency, points, signal}`),
  `schema`. Con `to_dict`/`to_json`. (REQ-004)
- **T002** Nuovo `distill_audit.py`: `distill_audit(profile, *, threshold=None) -> DistillAuditResult`.
  Enumera il corpus (tutti i `.md` sotto root, incl. log, escl. index); costruisci `page_aliases` dalle
  content page (`iter_pages` + `_link_aliases`, lowercase); segnale (i) wikilink penzolanti; segnale (ii)
  backtick-identifier via regex; fondi per nome normalizzato; filtra per soglia k (punti distinti ≥k);
  debito N; ordina per frequenza. `log_event`. (REQ-001/002/003/005/006, FR-001..006)
- **T003** `__main__.py`: aggiungi `"distill-audit"` a `_OPS`, dispatch in `_run` (leggi `--threshold`),
  summary in `_human` (`debt=N threshold=k candidates=… top: a,b,c`), arg `--threshold`. (REQ-004)
- **T004** `test_distill_audit.py` [P]: wikilink penzolante contato per punti; backtick-identifier;
  candidato con pagina esistente escluso; soglia k; debito N; determinismo + no-write (SC-001/002);
  stopword; corpus vuoto → N=0.

## Phase B — Hook `distill-floor` (US2)

- **T005** Nuovo asset `packages/sertor/src/sertor_installer/assets/claude/hooks/distill-floor.py`:
  `--mode {SessionStart,Stop,SessionEnd}` `--assistant`. Risolvi root+config (come `wiki-pending-check`);
  esegui `sertor-wiki-tools distill-audit --json` con cache once-per-day `.sertor/.distill-floor.json`;
  rileva voce `distill` del giorno nel log del giorno (regex); pavimento non soddisfatto ⟺ N>0 e nessuna
  voce distill oggi → messaggio (top candidati); auto-silenzio se soddisfatto o N=0; reso NATIVO per
  assistant/mode; exit 0 sempre; breadcrumb su errore CLI. (FR-007..011)
- **T006** Test hook [P] (`packages/sertor/tests/…`, offline, stile `test_portable_hooks_parity.py`):
  soddisfatto→silenzio; N>0 senza distill→messaggio; N=0→silenzio; parità Claude/Copilot per i 3 mode;
  exit 0; no-write sul contenuto wiki.

## Phase C — Distribuzione via installer (US4, REQ-013/014)

- **T007** Wiring Claude: registra `distill-floor.py` su `SessionStart`+`Stop`+`SessionEnd` negli asset
  `settings*.json` (ancorato `${CLAUDE_PROJECT_DIR}`, come gli altri hook).
- **T008** Wiring Copilot: `HookEntrySpec` per i 3 eventi (cwd="."), rendering nativo.
- **T009** Bundle sync: `uv run python -m sertor_installer.sync`; guardia `tests/unit/test_assets_sync.py`
  verde; parity guard hook.
- **T010** Guardie esito-install/upgrade dell'hook (identità per stem, come FEAT-032) se pertinente.

## Phase D — Contratto host-facing (US3, REQ-011/012)

- **T011** Blocco `SERTOR:WIKI-RITUAL` (`claude-md-block`): aggiungi la regola standing «≥1 distill/giornata
  attiva» + «il "no" costa» (un «distill: non necessario» va **loggato come voce `distill`** che nomina i
  candidati) + cenno al tool `distill-audit` e all'hook.
- **T012** Playbook wiki (`wiki-playbook.md`): documenta `distill-audit` tra le operazioni + il pavimento.
- **T013** Budget guard `claude-md-block` (righe) verde dopo l'aggiunta.

## Phase E — Validazione & dogfood

- **T014** Suite completa `uv run pytest -m "not cloud"` (root + packages) + `uv run ruff check .` verdi.
- **T015** Prova LIVE sul dogfood: `sertor-wiki-tools distill-audit` reale (debito N + candidati); hook
  eseguito a mano nei 3 mode.
- **T016** Aggiorna EXEC roadmap + epic (FEAT-039 → consegnata) + record/distill/lint del rituale al merge.

## Confine (ricorda)

Tool = deterministico/zero-LLM/read-only. Hook = non-bloccante/non-giudica. Il giudizio (distilla o «no»
motivato) resta nel flusso principale. Host-agnostico (config), fail-loud su scope indeterminabile.
