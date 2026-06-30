# Implementation Plan — Pulizia stile delle skill distribuite (E10-FEAT-022)

**Branch**: `080-pulizia-stile-skill` | **Date**: 2026-06-30 | **Spec**: `specs/080-pulizia-stile-skill/spec.md`

**Input**: `specs/080-pulizia-stile-skill/spec.md` · `requirements/debito-tecnico/pulizia-stile-skill/requirements.md`

## Summary
Igiene host-facing degli asset **skill** distribuiti da `sertor install rag` e `sertor-flow install`:
(1) ALL-CAPS enfatico → bold/imperativo + *why*; (2) condensazione delle sezioni «What NOT to do»
ridondanti; (3) Table of Contents nel `wiki-playbook.md` (281 righe); (4) rimozione del wikilink
orfano `[[assistant-targeting]]`; (5) callout «How to invoke» delle eval-skill → pointer al
riferimento unico `sertor-cli-reference.md` (FEAT-021). **ADDITIVA, solo forma/leggibilità, ZERO
`sertor_core`** (Principio XI). Una **guardia anti-regressione** (ALL-CAPS=0 · no `[[` orfani ·
pointer in 1 fonte · pin semantico) blocca il re-accumulo. Body host-agnostici byte-identici
Claude↔Copilot preservati; parità + sync dogfood verdi.

## Technical Context
- **Linguaggio/stack:** documentazione `.md` + test pytest (stdlib `re`); nessun runtime nuovo.
- **File toccati (5 asset + 3 guardie):**
  - `packages/sertor/.../assets/rag/skills/guided-setup/SKILL.md` (A1)
  - `packages/sertor/.../assets/rag/skills/eval-suite-author/SKILL.md` (A2)
  - `packages/sertor/.../assets/rag/skills/eval-feedback/SKILL.md` (A3)
  - `packages/sertor/.../assets/claude/skills/wiki-author/wiki-playbook.md` (A4)
  - `packages/sertor-flow/.../assets/claude/skills/requirements/SKILL.md` (A5)
  - `packages/sertor/tests/test_assets_skill_style.py` (NUOVO, G1)
  - `packages/sertor-flow/tests/unit/test_assets_skill_style.py` (NUOVO, G2)
  - `packages/sertor/tests/test_assets_cli_invocation.py` (estensione G3)
  - dogfood: `.claude/skills/wiki-author/wiki-playbook.md`, `.claude/skills/requirements/SKILL.md`
    (rigenerati via sync).
- **Decisioni di design:** `research.md` (DA-D-1..5) + `contracts/` (style-rules, stable-substrings,
  guard-contract) + `data-model.md` (allowlist, anchor ToC, pointer).
- **Vincoli:** zero core (XI); host-agnostico (X); nessun cambiamento semantico (RNF-3); parità
  Copilot + sync dogfood + FEAT-021 «1 fonte» verdi.
- **Ignoti (`NEEDS CLARIFICATION`):** nessuno. Tutte le forche di scope sono fissate dalla spec
  (DA-1/2/3) e le forche di *come* sono risolte qui (DA-D-1..5).

## Constitution Check
*GATE: passare prima di Phase 0; rivalutare dopo Phase 1.* Gate v1.4.0.

**PRE-design (PASS 12/12 + missione):**
- [x] **I** — zero core, nessun import SDK; libreria invariata.
- [x] **II** — nessun boundary/local-first toccato.
- [x] **III** — YAGNI: riusa le guardie esistenti; nessuna astrazione nuova; una sola guardia
  additiva minimale per package.
- [x] **IV** — nessun error handling toccato.
- [x] **V** — aggiunge guardie deterministiche (ALL-CAPS=0, no `[[`, pin); misurabile.
- [x] **VI** — edit idempotenti; install≠run invariato; sync deterministico.
- [x] **VII** — *la feature È leggibilità come comunicazione* (serve direttamente il principio).
- [x] **VIII** — nessuna config.
- [x] **IX** — nessuna osservabilità toccata.
- [x] **X** — body restano host-agnostici; la rimozione del wikilink orfano *aumenta*
  l'host-agnosticità (niente riferimento al wiki interno di Sertor sull'ospite).
- [x] **XI** — solo asset `.md` + test installer; **nessun** `sertor_core`, nessun vehicle/porta/engine.
- [x] **XII** — la guardia fallisce loud sulla reintroduzione; il fork IT dei dogfood eval (F-6) è
  **segnalato e promosso**, non sepolto.
- [x] **Missione** — contesto agente più pulito e veritiero (meno rumore ALL-CAPS, niente link al
  nulla) = qualità del contesto reso all'agente, la stella polare. Non deriva su concern periferici.

**Complexity Tracking:** vuoto (nessuna deroga).

**POST-design (Phase 1):** invariato — **PASS 12/12 + missione**. Le scelte di *come* (allowlist,
forma ToC con anchor GitHub, rimozione frase wikilink, pointer closure-safe, condensazione che
preserva i pin) non introducono codice di core, dipendenze, deroghe o assunzioni d'ospite. La nuova
guardia è additiva e per-package (no read cross-package). **Nessun nuovo** `ArtifactKind`/`Surface`/
`WriteStrategy`/seam del kit.

## Project Structure
```
specs/080-pulizia-stile-skill/
├── spec.md
├── plan.md            # questo file
├── research.md        # Phase 0 (DA-D-1..5 + findings)
├── data-model.md      # Phase 1 (asset, allowlist, anchor ToC, pointer, guardie)
├── quickstart.md      # Phase 1 (sequenza operativa + verifiche)
├── contracts/
│   ├── style-rules.md         # R1..R5 (ALL-CAPS, ToC, wikilink, pointer, condensazione)
│   ├── stable-substrings.md   # pin semantici per file (no perdita load-bearing)
│   └── guard-contract.md      # G1..G4 (guardia nuova + estensione + esistenti)
└── checklists/
    └── requirements.md
```
Sorgente: i 5 asset `.md` + 2 guardie nuove + 1 estensione (vedi Technical Context). `sertor-core`
**INVARIATO**. Installer (`build_rag_plan`, lifecycle) **invariato**: i file skill continuano a essere
depositati/rimossi come prima (FR-015).

## Phasing (per `/speckit-tasks`)
1. **Must (P1):** ToC `wiki-playbook.md` (FR-007); rimozione wikilink orfano (FR-008/009); guardie e
   sync verdi (FR-011/012/013/014/015). 2. **Should (P2):** ALL-CAPS A1–A5 (FR-001/002/003);
   condensazione sezioni (FR-004/005/006); sync dogfood (FR-013). 3. **Could (P3):** pointer eval-skill
   (FR-010). La guardia copre tutti gli invarianti a fine lavoro.

## Note di processo
`setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** → parametri ricavati per
convenzione dal branch (forma da `079`); **nessun hook SpecKit eseguito**. MCP `sertor-rag`
interrogato in apertura (orientamento su guardie/asset) **senza errori tool**; per i conteggi esatti
di riga e l'inventario ALL-CAPS si è usato `Read`/`Grep`/script (fatti puntuali a posizione nota).
Git **non eseguito** (delega al `configuration-manager` — brief nel report).
