# Implementation Plan — auto-update version check (avviso d'aggiornamento al SessionStart)

**Branch**: `feat013-version-check-backlog` · **Spec**: [`spec.md`](./spec.md) · **Data**: 2026-06-25
**Epica**: sertor-cli (E2) · **Feature**: FEAT-013 · **Status**: Plan (design completo)

## Summary
Aggiungere un **avviso non invasivo a inizio sessione** quando la versione installata di Sertor è più
vecchia dell'ultima pubblicata su `master`. È il **gemello concettuale di E10-FEAT-011** (hook di
freschezza): stesso pattern host-facing (hook distribuiti dall'installer, parità Claude / Copilot CLI)
e stesso confine **D↔N** — un harness deterministico **segnala**, l'utente **agisce** (mai
auto-upgrade). Due tempi: **(SessionEnd)** uno script `version-check.ps1` fa una **GET HTTP semplice**
del `/VERSION` remoto (cachata ~1/giorno), lo confronta con uno **stamp installato** scritto
dall'installer (`.sertor/.sertor-version`) e persiste l'esito in `.sertor/.version-check.json`;
**(SessionStart)** uno script (Claude) / prompt statico (Copilot) **legge lo stato e avvisa** se
indietro, **zero rete**. La feature è **additiva e host-facing**: **nessun codice di `sertor-core`**
(Principio XI — l'hook usa HTTP+file, mai importa la libreria, mai invoca un LLM), e wiring di
distribuzione via `sertor install rag` / `sertor-flow install` con lifecycle install/upgrade/uninstall.

## Technical Context
- **Linguaggio/runtime**: PowerShell (script hook host-agnostici, stdlib `pwsh` — `Invoke-WebRequest`)
  + Python 3.11+ (installer `sertor`/`sertor-flow`/`sertor-install-kit`, stdlib-only nel kit).
- **Dipendenze consumate**: nessun vehicle CLI e nessun LLM (a differenza della freschezza); solo una
  **GET HTTP** del `/VERSION` pubblico + lettura/confronto di file locali.
- **Meccanismo riusato**: pattern hook installer di `rag-freshness`/`memory-capture`
  (`install_rag.py`); seam di parità `AssistantProfile`/`HookEntrySpec`/`render_copilot_hooks` (kit);
  guardia di sync dogfood `test_rag_freshness_dogfood_sync` (estesa).
- **Storage**: stato JSON `.sertor/.version-check.json` (schema `version.check/1`) + stamp installato
  `.sertor/.sertor-version` (+ `.sertor/.sertor-flow-version` per la governance), tutti gitignored.
- **Fonte versione**: `/VERSION` a radice (fonte unica dei 4 `pyproject`); remoto raw su `master`
  derivato da `DIST_URL`, override env `SERTOR_VERSION_CHECK_URL`.
- **Confine D↔N**: lo script è meccanico (GET, confronto, persistenza, avviso); **nessun LLM**
  (NFR-5). Decisione e azione (aggiornare) restano all'utente (FR-005/CS-4).
- **NEEDS CLARIFICATION**: **nessuno** — le 4 decisioni di scope sono fisse nella spec; le 5 forche di
  *come* (DA-1..DA-5) sono risolte in [`research.md`](./research.md) (D-1..D-4, D-6).

## Constitution Check — **PASS 12/12 + Missione PASS** (pre e post-design, nessuna deroga)

> Costituzione v1.4.0 (12 principi I–XII + gate «Allineamento alla missione»).

| # | Principio | Esito | Motivazione |
|---|---|---|---|
| I | La libreria è il prodotto | PASS | nessun codice di core; lo script è un consumatore esterno (HTTP+file) |
| II | Dettagli sostituibili / no lock-in | PASS | script PowerShell + JSON locale; nessuna dipendenza nuova; URL parametrizzato via env |
| III | YAGNI / no over-engineering | PASS | nessun nuovo `ArtifactKind`/`Surface`/seam; riuso dei modelli installer; piggyback scartato per semplicità |
| IV | Errori avvolti al boundary | PASS | hook non-fatale (`try/catch`→exit 0); offline/parse-fail → skip silenzioso, mai stato corrotto |
| V | Misurabilità | PASS | stato persistito ispezionabile (verdict/installed/latest/checked_at); CS-1..6 verificabili offline |
| VI | Idempotenza / non-distruttività | PASS | install merge-dedup additivo; `up-to-date` scritto canonico (no oscillazione); stamp riscritto a upgrade |
| VII | Funzioni piccole / basso nesting | PASS | script thin: GET → confronto puro → scrittura; nessuna logica oltre l'orchestrazione |
| VIII | Config centralizzata | PASS | `RUNTIME_IGNORES` (unica fonte) esteso; URL override via env, nessun default hardcodato sparso |
| IX | Osservabilità | PASS | eventuale evento metrics-only (NFR-6); lo stato persistito è il segnale diagnostico |
| X | Capacità host-agnostiche | PASS | script senza assunzioni hardcoded; distribuito a Claude+Copilot con parità (RNF-3) |
| XI | Consumo via vehicles | PASS | **cardine**: nessun `import sertor_core`, nessun LLM; solo HTTP pubblico + file (FR-014/RNF-5) |
| XII | Fail loud, fix the cause | PASS | l'avviso **rende visibile** uno stato silenzioso (host stantio); offline = skip *segnalato come inconcludente*, non finto «sei indietro» |

### Gate «Allineamento alla missione» — **PASS**
La missione è la qualità del contesto reso all'agente; un ospite **silenziosamente stantio** ne è una
minaccia *indiretta* ma reale — retrieval, wiki e governance girano su una Sertor vecchia e i
fix/miglioramenti non arrivano. Rendere **visibile** la disponibilità di un aggiornamento serve
l'**adozione e la portabilità** (Principio X: un ospite qualsiasi sa da solo quando è indietro). È il
gemello della freschezza del corpus (E10-FEAT-011): quella tiene fresco il *corpus*, questa tiene
fresco il *pacchetto*. Periferica al differenziatore (fusione code+doc) ma ne è un abilitatore. Non
deriva su concern periferici (il check è meccanico, non chiama LLM, non importa il core).

### Complexity Tracking
**Nessuna deviazione tracciata.** La feature è additiva, riusa i seam esistenti, non tocca il core,
non introduce dipendenze. Le uniche modifiche al kit (3 righe in `RUNTIME_IGNORES`) sono additive e
non-breaking.

## Decisioni di design (forche risolte — research D-1..D-6)
- **DA-1 + DA-4 → RISOLTE** (D-1): check «vivo» (GET+confronto+persist) in uno **script SessionEnd**
  `version-check.ps1` (Claude + Copilot); SessionStart = **solo lettura+avviso** (script Claude /
  prompt statico Copilot — quest'ultimo non può fare rete). Asset/voci **separati** dall'hook di
  freschezza (gemello indipendente); piggyback sul SessionEnd di freschezza **valutato e scartato**
  (scope/lifecycle/cadenze diversi; le GET sono di cose diverse, nessuna duplicazione reale).
- **DA-2 → RISOLTA** (D-2): `/VERSION` «ultimo» = raw su `master`
  (`raw.githubusercontent.com/themetriost/Sertor/master/VERSION`, derivato da `DIST_URL`),
  **parametrizzabile** via env `SERTOR_VERSION_CHECK_URL` (fork/branch). GET con timeout breve.
- **DA-3 → RISOLTA** (D-3): versione «installata» = **stamp install-time** `.sertor/.sertor-version`
  (scritto dall'installer dal proprio `/VERSION`), confronto **puro testuale** stamp↔remoto, **nessun
  Python/`sertor_core`** nel path caldo dell'hook. `sertor-flow` scrive `.sertor/.sertor-flow-version`.
- **DA-5 → RISOLTA** (D-4): confronto **semantico per segmenti numerici** + fallback lessicale;
  verdetto `behind`/`up-to-date`/`ahead`/`unknown`; **installato ≥ remoto ⇒ nessun avviso** (copre il
  dev-locale). Contratti: [`contracts/version-check-state.md`](./contracts/version-check-state.md),
  [`contracts/version-check-hook-wiring.md`](./contracts/version-check-hook-wiring.md).

## Phase 0 — Research
→ [`research.md`](./research.md): D-0 ancoraggio (hook pattern, wiring installer, render Copilot,
`/VERSION`, `RUNTIME_IGNORES`, guardia sync); D-1..D-4/D-6 forche risolte; D-5 cadenza/cache; D-7
promozione Out-of-Scope; D-8 confini/non-regressione.

## Phase 1 — Design & contracts
- [`data-model.md`](./data-model.md): stato del check (§1), stamp installato (§2), script hook (§3),
  wiring per-assistente (§4), artefatti installer (§5), lifecycle (§6), invarianti.
- [`contracts/`](./contracts/): `version-check-state.md` (schema `version.check/1` + stamp),
  `version-check-hook-wiring.md` (voci native Claude/Copilot, SessionEnd + SessionStart).
- [`quickstart.md`](./quickstart.md): verifiche manuali (GET cachata, behind→avviso, ahead/up-to-date
  → silenzio, offline→skip, loop chiusa dopo upgrade, distribuzione/parità, lifecycle, guardia sync,
  D↔N/privacy).

## Implementazione prevista (mappa file — riferimento per `tasks`)
**Asset bundlati** (`packages/sertor/src/sertor_installer/assets/`):
- `rag/hooks/version-check.ps1` (NUOVO — SessionEnd: GET cachata + confronto stamp↔remoto + persist,
  gemello di `rag-freshness.ps1`; exit 0 sempre; nessun LLM/`sertor_core`).
- `rag/hooks/version-check-start.ps1` (NUOVO — SessionStart Claude: legge lo stato, avvisa se behind).
- `rag/settings.version-check.json` (NUOVO — voce SessionEnd Claude) +
  `rag/settings.version-check-start.json` (NUOVO — voce SessionStart Claude). *(Copilot: generati via
  sentinel, nessun asset statico.)*

**Installer** (`packages/sertor/src/sertor_installer/install_rag.py`):
- costanti `_VERSION_CHECK_*`/`_VERSION_CHECK_START_*` + 2 sentinel Copilot;
  `_copilot_version_check_end_specs()` / `_copilot_version_check_start_specs()` (prompt statico).
- `build_rag_plan`: +2 FILE script (start solo Claude) +2 SETTINGS_MERGE (SessionEnd/SessionStart,
  per-assistente) **+1 FILE generato** per lo stamp `.sertor/.sertor-version` (scritto a install/
  upgrade-time dal `/VERSION` del pacchetto via `importlib.metadata`, NON nel path caldo dell'hook).
- `_rag_hook_fragment`: dispatch dei 2 nuovi sentinel (art-aware, riuso `render_copilot_hooks`).
- `sertor_owned_paths`: +owned_files (i 2 script, start solo Claude; lo stamp); shared_edit settings
  già coperto.
- uninstall/upgrade: già art-aware (FILE→remove/update; SETTINGS_MERGE→remove_settings_entries con
  `delete_if_empty`) — nessuna logica nuova; **upgrade riscrive lo stamp** (chiude la loop, FR-013).

**Installer governance** (`packages/sertor-flow/...`): analogo per la copertura per-dimensione US6 —
scrive `.sertor/.sertor-flow-version` + distribuisce il version-check (gemello di `sertor install`).
*(Could FR-012: se rinviato, il version-check del solo `sertor` resta funzionale; tracciato nel backlog
E2.)*

**Kit** (`packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py`):
- `RUNTIME_IGNORES += (".sertor/.version-check.json", ".sertor/.sertor-version",
  ".sertor/.sertor-flow-version")` (additivo).

**Dogfood** (`.claude/`): copia di `version-check.ps1`/`version-check-start.ps1` in `.claude/hooks/`
+ voci in `.claude/settings.json` (propagate dall'asset, verificate dalla guardia sync estesa).

**Governance** (`CLAUDE.md`): annotare (sezione *Setup ed esecuzione* / `docs/install.md §10.1`) che
l'avviso d'aggiornamento è ora automatico via hook; cross-ref a E10-FEAT-011. *(Non rimuove la via
manuale: resta la rete fino a distribuzione completa.)*

**Test** (offline, no rete):
- `packages/sertor/tests/test_install_rag_version_check.py` (NUOVO): deposito Claude/Copilot, formato
  nativo, voce SessionEnd + SessionStart, owned_paths coverage, stamp scritto/aggiornato, uninstall/
  upgrade granulare, isolamento da rag-freshness/memory-capture.
- estensione di `test_rag_freshness_dogfood_sync` (o guardia sorella) per i 2 nuovi script.
- copertura `RUNTIME_IGNORES` (kit) per le 3 nuove righe.
- *(la GET HTTP e il confronto vivono nello script `.ps1`: la logica è verificabile offline via fixture
  di stato/stamp; la GET reale è esercitata in quickstart manuale — coerente con gli altri hook.)*

## Promozione Out-of-Scope (regola «si promuovono, non restano appesi» — research D-7)
- **Rilevazione commit-SHA** → scartata per decisione (low-noise sul bump di `/VERSION`); se mai
  servisse, **nuova FEAT** dell'epica `sertor-cli` (non sepolta).
- **Pulizia artefatti obsoleti** → **E10-FEAT-015** (già esistente): cross-ref.
- **Freschezza del corpus** → **E10-FEAT-011** (gemello, già consegnato): cross-ref.
- **PyPI** → **FEAT-006** (Won't): cross-ref.
- **Granularità per-dimensione (FR-012) e re-check forzato (FR-008)** → Could di **questa** feature
  (REQ-011/018); se rinviati restano Could tracciati nel backlog E2 (`requirements/sertor-cli/epic.md`),
  non in `specs/`.

## Out of scope (questa feature)
- L'**applicazione** dell'aggiornamento: la fa `sertor upgrade` / `uvx --refresh` (FEAT-008); l'avviso
  li **raccomanda**, non li reimplementa, mai auto-upgrade (FR-005).
- Qualunque GET diversa dal `/VERSION` pubblico; nessun contenuto/segreto in rete (FR-015).
- Modifiche a `sertor-core` / comandi CLI nuovi (la feature è 100% asset + installer).

## Nota di processo
`.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** nel repo →
parametri ricavati per **convenzione dal branch** (forma dal gemello `076-enforcement-freschezza-rag`);
**nessun hook SpecKit eseguito**. **MCP `sertor-rag` interrogato** in apertura (`search_code` sul
wiring installer freschezza — **nessun errore tool**); il resto ancorato con `Read`/`Grep` su file a
posizione nota (`install_rag.py`, `rag-freshness*.ps1`, `gitignore_append.py`, `rag_profile.py`,
`/VERSION`, `test_install_rag_freshness.py`). Git **non** eseguito (delegato al
`configuration-manager`).
