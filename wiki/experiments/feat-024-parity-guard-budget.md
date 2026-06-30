---
title: E10-FEAT-024 — Parity guard esteso e budget altitude CLAUDE.md
type: experiment
tags: [debito-tecnico, guardie, CI, asserzioni, FEAT-024]
created: 2026-06-30
updated: 2026-06-30
sources: ["specs/082-parity-guard-budget/", "requirements/debito-tecnico/parity-guard-budget/requirements.md"]
---

# E10-FEAT-024 — Parity guard esteso (`.ps1`/`.json`) + budget blocchi CLAUDE.md

**Status:** ✅ Implementata (2026-06-30, branch `082-parity-guard-budget`)

Implementazione **ADDITIVA solo-test** di E10-FEAT-024 (epica debito-tecnico, Could-P2): estensione del
parity guard per catturare drift di wiring Copilot silenzioso su asset non-testati (script/JSON) e
freno automatico alla crescita dei blocchi always-on in `CLAUDE.md` via budget per-blocco in CI.

## Problema

Due lacune nel **sistema di prevenzione drift asset Copilot/ospite**:

1. **Il parity guard esclude `.ps1` e `.json`**: verifica che i body asset siano host-agnostici (zero
   path `.claude/`, zero slash-command, zero nomi-prodotto), **ma salta** gli script PowerShell e file
   JSON (hook, MCP config, settings). Risultato: il **wiring Copilot** (hook JSON nativo, il PlainAgent
   di FEAT-019) potrebbe derivare in silenzio e il test non lo catturerebbe.

2. **Nessun freno alla ricrescita dei blocchi always-on**: dopo FEAT-021 (riduzione a −20%), i blocchi
   CLAUDE.md restano **senza limite superiore**. Una nuova feature che aggiunge una sezione → cresce di
   nuovo verso il carico previous. Niente guardia in CI che dica «qui è il soffitto».

Consequenza: fattori di rischio della host-agnosticità non visibili fino al dogfooding.

## Soluzione — 3 guardie offline

### 1. `test_copilot_hook_presence` — Shape del wiring hook Copilot

Rende il piano `build_rag_plan(copilot-cli)` offline e asserisce sulla **struttura** dei file JSON
generati, non sulla resa:

- `sertor-hooks.json` esistente e contenente gli eventi attesi: `PreToolUse` (×1) · `SessionEnd` (×3) ·
  `SessionStart` (×2).
- Contratto JSON nativo Copilot verificato (`version:1`, entry piatta, nessun `shell`/`timeout`
  senza `timeoutSec`, niente dual-field per assistente).
- **Anti-vacuità:** se un evento è rimosso dal bundle → test rosso, nomina l'evento.

### 2. `test_claude_md_block_budget` — Limite righe per blocco sempre-on

Suite **ROOT** (cross-package) che crea il piano per tutti i target e verifica che ogni blocco a marker
**NON SUPERI** una soglia personalizzata:

- **Budget per-blocco (differenziato):** `wiki=60` · `rag=58` · `sdlc=70` righe.
  - Scelta di soglia: post-FEAT-021 i reali sono 52/49/64; il budget è **stretto ma realistica** (−8/9
    righe rispetto a pre-FEAT-021 = 71/72), lascia margine ~8 righe per crescita futura senza blocco.
  - Differenziamento: blocchi diversi hanno semantica diversa (wiki=strumenti+passi+invocazione · rag=config+vehicle ·
    sdlc=giurisdizione); uno stesso tetto uniformerebbe e bloccherebbe i guadagni FEAT-021.
- **Coverage esaustiva:** ogni blocco (wiki/rag/sdlc) è presente nel piano → se uno è eliminato o rinominato,
  l'asserzione non lo trova → rosso.
- **Test con `--dry-run`:** non scrive su disco, veloce, idempotente.

### 3. `test_hooks_rag_no_stdout_payload` — Script `.ps1` non emettono payload su stdout

Guardia che il comportamento osservabile del wiring `.ps1` è conforme al contratto Copilot (nessun
`decision` payload stdout che l'agente-falso consumerebbe):

- Riguarda solo `rag-freshness.ps1` SessionEnd (FEAT-019): asserisce che **non emetta** `decision`
  su stdout (sì a `reason`/`-Reason` e prosa di commenti, vietato il JSON/codice computazionale che
  il payload di hook `agentStop:block` manderebbe).
- **Falsi positivi evitati:** verifica con regex mirata (non `[{}]` → falso positivo on braces in
  comments; non `decision"?:` → parola intera).

## Esiti

**SpecKit completo:** `requirements/debito-tecnico/parity-guard-budget/requirements.md` (17 FR EARS) →
`specs/082-parity-guard-budget/spec.md` → `specs/082-parity-guard-budget/plan.md` → tasks → implementation
(branch `082-parity-guard-budget`).

- **Constitution PASS 12/12 + missione:** Principio X (host-agnosticità asset resa verificabile) · Principio XII
  (fail loud in CI) · Principio III (DRY guardia una-volta-sola nel test).
- **Test:** root **1134 passed** (sertor 480 · sertor-flow 140 · kit 139); 3 skip packaging (non-ermetico);
  ruff pulito.
- **Codice:** ZERO modifiche `sertor-core` / runtime. SOLO test. Zero nuova `ArtifactKind` / Surface /
  WriteStrategy / dipendenza / env.
- **File toccati:** `tests/unit/test_copilot_hook_presence.py` (NEW) · `tests/unit/test_claude_md_block_budget.py`
  (NEW) · `tests/unit/test_hooks_rag_no_stdout_payload.py` (NEW).

## Backlink

- [[constitution]] — Principi X/XII/III applicati (host-agnosticità resa verificabile, freno CI).
- [[deterministic-vs-judgment]] — Guardie meccaniche deterministiche, niente LLM.
- [[sertor-installer]] — Asset distribuzione, guardia che copre.
- [[feat-021-altitude-claude-md]] — Precedente riduzione; questa guardia frena ricrescita.
- [[feat-022-pulizia-stile-skill]] — Contemporaneo; guardia stile complementare.
- [[feat-019-fail-loud-hook-agent]] — Hook wiring che la guardia `test_copilot_hook_presence` verifica.
- [[feat-018-portabilita-os-hook]] — Portabilità OS; questa guardia copre il wiring Copilot.

## Prossimo passo

Merge branch `082` su `master` (nessuna iterazione attesa, no-core, test-only). La guardia di budget è un
freno permanente che si acuisce con la contezza della soglia reale (numero di feature, frequenza aggiunte).

---

## Note di implementazione (se utile)

**Stratificazione guardie:**
- **A (strutturale):** formato JSON/lunghezza linea (CLI `lint` del wiki-tools).
- **B (semantico):** content (host-agnosticità path/slash/nomi — FEAT-056, test offline).
- **C (organizzativo, nuovo):** comportamento-osservabile (non emette payload) + dimensione
  (budget righe).

Le tre agiscono a livelli diversi: prevenire la forma difettosa, prevenire il contenuto coperto e prevenire la
ricrescita incontrollata.
