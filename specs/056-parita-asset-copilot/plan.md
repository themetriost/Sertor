# Implementation Plan: Parità funzionale completa su Copilot CLI + governance dual-target

**Branch**: `056-parita-asset-copilot` · **Spec**: `specs/056-parita-asset-copilot/spec.md` ·
**Requirements**: `requirements/debito-tecnico/host-agnosticita-asset-residui/requirements.md`
(decomposizione di FEAT-001, epica `debito-tecnico`).

## Summary

Su un host Copilot CLI la capacità wiki è non funzionante: il **payload multi-file** della skill
`wiki-author` non viene depositato e i **body** distribuiti citano path `.claude/` e comandi `/wiki`
inesistenti. La feature ottiene la **parità funzionale completa** su Copilot CLI per **tutti** gli asset
distribuibili (wiki + governance `requirements` + rag) **neutralizzando i body alla sorgente**
(host-agnostici, byte-identici Claude↔Copilot, riferimento al payload **per nome**) e **depositando il
payload** su Copilot in un container dedicato non-agente `.github/sertor/wiki-author/`, riusando
l'infrastruttura esistente (`iter_asset_dir` + byte-copy) senza nuovi `Surface`/`ArtifactKind`. Una
**guardia di parità offline** con **closure dei riferimenti** rende la regressione impossibile, e tre
sedi di **governance dual-target** impediscono che il difetto rientri. Ramo Claude invariato (gate).

## Technical Context

- **Pacchetti toccati**: `sertor` (installer wiki/rag + asset), `sertor-flow` (installer governance +
  asset), `sertor-install-kit` (solo se serve un punto di aggancio condiviso per il deposito payload).
  **`sertor-core` INVARIATO** (porte/adapter/composition/`sertor-rag`).
- **Punti di codice noti**: `packages/sertor/src/sertor_installer/install_wiki.py`
  (`_build_copilot_wiki_plan`, `sertor_owned_paths`, `_render_for_target`, `iter_asset_dir`);
  `packages/sertor-install-kit/src/sertor_install_kit/{assistant.py,surfaces.py}` (seam, render —
  **non si aggiungono Surface/ArtifactKind**); `packages/sertor-flow/.../install_governance.py`.
- **Asset sorgente**: `packages/sertor/.../assets/claude/{skills/wiki-author/**,agents/wiki-curator.md,
  commands/wiki.md,claude-md-block.md}`; `packages/sertor-flow/.../assets/claude/**`.
- **Test**: nuovo `packages/sertor/tests/test_assets_copilot_parity.py`; guardia byte-identica esistente
  (`test_assets_copilot_guard.py`) **resta verde**; coverage `plan ⊆ owned` esistente protegge i path.
- **Verifica empirica**: host reale **Spike** (Copilot CLI 1.0.63).
- **Tooling**: `uv` (un solo `.venv`); offline (NFR-05, niente cloud nei test).

## Constitution Check (pre-design) — **PASS 11/11, nessuna deroga**

- **I (core = libreria):** `sertor-core` non viene toccato; la feature vive negli installer/asset. ✅
- **II (boundary, local-first):** nessun nuovo fetch; la guardia è offline; byte-copy locale. ✅
- **III (YAGNI, unità piccole):** riuso di `iter_asset_dir` + dispatch byte-copy esistente; **niente
  nuovi `Surface`/`ArtifactKind`**; loop di deposito ~8 righe. ✅ (è il cuore della scelta D3)
- **IV (errori espliciti, niente null silenzioso):** la **closure dei riferimenti** trasforma un agente
  rotto-silenzioso (playbook mancante) in un **fallimento esplicito** del test. ✅ (la feature *serve*
  direttamente questo principio)
- **V (testabilità da misure):** guardia offline + SC misurabili (0 `.claude/`, 0 dangling, prima azione
  riesce su Spike). ✅
- **VI (idempotenza, determinismo, non-distruttività):** byte-copy deterministico; install idempotente;
  uninstall rimuove il container in blocco (owned_dir). ✅
- **VII (leggibilità, lascia il codice più pulito):** body neutralizzati + governance documentata. ✅
- **VIII (config centralizzata):** nessuna nuova manopola; nulla di hardcodato fuori posto. ✅
- **IX (osservabilità):** percorso d'installazione, `install.report` invariato; nessun nuovo evento
  richiesto. ✅
- **X (host-agnostico):** è **l'embodiment** del principio — i body diventano host-agnostici e il payload
  è depositato dove ciascun host lo cerca. ✅ (FEAT-001 dell'epica = host-agnosticità asset residui)
- **XI (consumo via vehicles):** install-time, non runtime-library; non introduce accesso diretto al
  core. ✅

## Project Structure (file impattati)

```
requirements/debito-tecnico/host-agnosticita-asset-residui/requirements.md   [fatto]
specs/056-parita-asset-copilot/{spec.md,plan.md,tasks.md,checklists/}        [questa fase]
packages/sertor/src/sertor_installer/
  install_wiki.py                  → deposito payload Copilot + sertor_owned_paths
  assets/claude/skills/wiki-author/{SKILL.md,wiki-playbook.md,ops/*.md,*-craft.md}  → neutralizzare
  assets/claude/agents/wiki-curator.md, commands/wiki.md, claude-md-block.md         → neutralizzare/DoD
  tests/test_assets_copilot_parity.py   [NUOVO]
packages/sertor-flow/src/sertor_flow/
  install_governance.py            → audit/neutralizzare (requirements/agenti)
  assets/claude/**                 → neutralizzare body
wiki/tech/assistant-targeting.md   → sezione "parità by construction"
.claude/**, CLAUDE.md              → ri-sync dogfood (coerenza asset↔dogfood)
```

## Phase 0 — Research & Decisioni (chiuse)

| ID | Decisione | Esito |
|---|---|---|
| D1 | Body dual-valido | **Neutralizzare la sorgente** (byte-identico); NON tradurre per-target |
| D2 | Sede payload Copilot | **`.github/sertor/wiki-author/`** (non-agente, fuori da `.github/agents/`) |
| D3 | Meccanismo deposito | **Riuso `iter_asset_dir` + byte-copy**; no nuovi Surface/ArtifactKind |
| D4 | Guardia | Offline: no `.claude/` · no slash · no "Claude Code" · **closure riferimenti** (Copilot+Claude) |
| D5 | Governance | Playbook + `assistant-targeting.md` + DoD nel rituale |
| D6 | Scope | **Full sweep**: wiki + governance + rag |
| — | Tensione D1×D2 | **Riferimento-per-nome**: il body cita il payload per nome file (host-agnostico), non per path assoluto → byte-identico e risolvibile su entrambi |

**Unknown risolti:** verifica Copilot reale = Spike (non xfail); host già installati = `upgrade`;
`derive-entity-types` = fuori (backlog separato).

## Phase 1 — Design

**Data model:** **nessuna entità nuova**. Concetti: *payload di supporto* (file della skill letti a
runtime), *container del payload* (per-host), *body host-agnostico*, *riferimento-per-nome*, *closure*.

**Contratti:** l'unico "contratto" nuovo è la **guardia di parità** (test, non API runtime):
- *Input:* i piani d'installazione Copilot (wiki+governance+rag) resi in memoria/tmp + (per closure) il
  piano Claude.
- *Invarianti verificati:* (a) `.claude/` ∉ file resi Copilot; (b) nessun slash-command come invocazione;
  (c) "Claude Code" ∉ body resi; (d) **closure**: ∀ riferimento-a-file in un body reso ⇒ il file è un
  target del piano (relativi risolti rispetto al container del referente).
- *Output:* PASS/FAIL con nome del riferimento dangling in caso di fallimento.

**Quickstart (verifica end-to-end):** install wiki Claude (dir temp) → payload in `.claude/skills/...`;
install wiki Copilot su Spike → payload in `.github/sertor/wiki-author/**` + 0 `.claude/` nei resi;
seguire closure manuale; invocare l'agente wiki su Copilot CLI 1.0.63 → la prima azione (Read playbook)
riesce + nessun agente-fantasma da `.github/sertor/`; install Claude non-regressione; uninstall rimuove i
container in blocco.

## Fasi di implementazione (mappate alle user story)

1. **US1/US2 (P1) — wiki funzionante + zero refs Claude:** neutralizzare gli asset wiki (SKILL/agent/
   command/playbook/ops/craft) con riferimento-per-nome; aggiungere al `_build_copilot_wiki_plan` il loop
   `iter_asset_dir` → `.github/sertor/wiki-author/**`; aggiornare `sertor_owned_paths` (Copilot).
2. **US3 (P2) — full sweep:** audit + neutralizzare governance (`requirements`/agenti) e rag.
3. **US4 (P2) — guardia:** `test_assets_copilot_parity.py` (4 controlli + closure su Copilot e Claude).
4. **US5 (P3) — governance:** sezione playbook + `assistant-targeting.md` + DoD nel `claude-md-block.md`.
5. **Ri-sync dogfood + verifica:** ri-sync `.claude/**`; suite verde (parità + byte-identica + coverage);
   verifica empirica su Spike (Claude + Copilot).

## Constitution Check (post-design) — **PASS 11/11, nessuna deroga**

Il design non introduce nuovi `Surface`/`ArtifactKind`, non tocca `sertor-core`, non aggiunge fetch né
config, e rafforza i Principi IV (errori espliciti via closure) e X (host-agnosticità). Nessun elemento
di complessità da tracciare.

## Complexity Tracking

Nessuna deviazione costituzionale. Rischio residuo (non costituzionale) = R4 (container `.github/sertor/`
da validare su host reale), gestito empiricamente nella fase di verifica con fallback dichiarato.
