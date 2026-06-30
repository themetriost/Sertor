# Implementation Plan — Ridurre l'altitude dei blocchi CLAUDE.md + fonte unica «How to invoke» (E10-FEAT-021)

**Branch**: `079-altitude-claude-md` · **Data**: 2026-06-30 · **Spec**: `specs/079-altitude-claude-md/spec.md`
**Requirements**: `requirements/debito-tecnico/altitude-claude-md/requirements.md`

> **Nota di processo.** `.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **ASSENTI** nel repo → parametri ricavati per convenzione dal branch (forma da `076`/`078`); nessun
> hook SpecKit eseguito. MCP `sertor-rag` interrogato in apertura (`search_code` sul wiring installer
> SDLC, **nessun errore tool**); ancoraggio puntuale via `Read`/`Grep` su posizioni note.

## Summary
Sertor inietta **tre blocchi always-on** (~208 righe) nel file di istruzione di ogni ospite: wiki-ritual
(71), SDLC-ritual (65), RAG-usage (72). I blocchi mescolano **direttive comportamentali standing** (che
giustificano l'always-on) con **dettaglio operativo lookup-on-demand** (sintassi di invocazione,
troubleshooting) che spreca budget di contesto a ogni sessione. La sezione «How to invoke Sertor's
commands» + Windows note è **triplicata** (RAG block, `guided-setup`, `wiki-playbook`).

La feature **riduce ogni blocco a direttiva standing + pointer** ed **estrae «How to invoke» in una
fonte unica** host-agnostica citata per nome. È **igiene di asset host-facing, ADDITIVA, ZERO
`sertor_core`** (Principio XI): tocca solo asset `.md`, un `Artifact` FILE nel plan-builder RAG
(`install_rag.py`, installer non-core), le copie dogfood `.claude/` e le guardie di test.

**Decisioni di *come* (research):**
- **DA-D-r1 → Opzione A:** nuovo asset `rag/sertor-cli-reference.md`, depositato da `sertor install rag`
  in `.sertor/sertor-cli-reference.md` (target host-agnostico). RAG block + `guided-setup` lo citano per
  nome (closure RAG). Il `wiki-playbook` (REQ-009 Should) **non** lo cita per filename (sarebbe pointer
  morto su install solo-wiki): rimuove la sottosezione duplicata, tiene la forma minima §2 + frase
  condizionale senza token di file. La sezione completa + Windows note vive in **un** asset → CS-2.
- **DA-D-r2:** criterio qualitativo «standing inline, lookup a pointer» (NO soglia numerica → FEAT-024);
  contenuto minimo per blocco fissato in `contracts/reduced-blocks.md` (C1/C2/C3).
- **DA-D-r3:** confermato per lettura — il blocco SDLC NON contiene «How to invoke» → **invariato**.
- **DA-D-r4:** guardia di non-reintroduzione = **assert testuale** (heading/Windows-note/`uvx --from`
  assenti dai blocchi) + **closure** del reference; rework dei test di presenza-guida.

## Technical Context
- **Linguaggio/Runtime:** Python ≥ 3.11; asset Markdown distribuiti via `sertor_installer` /
  `sertor_flow` (pacchetti installer, stdlib-only).
- **Modifiche di codice:** SOLO `packages/sertor/src/sertor_installer/install_rag.py` (1 `Artifact`
  FILE nel `build_rag_plan` + entry owned se necessaria). **Nessun** `sertor_core`, nessun nuovo
  `ArtifactKind`/`WriteStrategy`/`Surface`/seam del kit.
- **Asset toccati:** `assets/claude-md-block.md` (wiki), `assets/rag/claude-md-block-rag-usage.md`
  (RAG), `assets/rag/sertor-cli-reference.md` (NUOVO), `assets/rag/skills/guided-setup/SKILL.md`,
  `assets/claude/skills/wiki-author/wiki-playbook.md`; copia dogfood `.claude/skills/wiki-author/wiki-playbook.md`.
- **SDLC block (`sertor-flow`):** contenuto **invariato** (no lookup da estrarre).
- **Guardie:** `test_assets_copilot_parity.py` (esteso: closure reference), `test_assets_cli_invocation.py`
  (rework presence + non-reintroduzione), `tests/unit/test_assets_sync.py` (invariata, re-sync playbook),
  assert gemello non-reintroduzione SDLC in `sertor-flow`.
- **Testing:** offline (no rete, no `uv` nelle guardie); `uv run pytest -m "not cloud"`, `ruff`.
- **Performance/scale:** N/A (igiene asset; meno righe always-on = più budget di contesto).
- **NEEDS CLARIFICATION:** nessuno (DA-1/DA-2 risolte in spec; DA-D-r1..r4 risolte in research).

## Constitution Check — PRE-design (Phase 0 gate)

| Principio | Esito | Motivo |
|---|---|---|
| I — Core a dipendenze interne | **PASS** | nessun tocco al core; solo asset host-facing + installer. |
| II — Provider/backend dietro boundary; local-first | **N/A** | nessun provider/backend. |
| III — Semplicità (YAGNI), unità piccole, DRY | **PASS** | DRY *rafforzato* (elimina la triplicazione); nessun nuovo astrazione/seam. |
| IV — Errori espliciti, niente null | **N/A** | nessun percorso d'errore di runtime. |
| V — Testabilità/misure | **PASS** | guardie offline (parità, closure, non-reintroduzione, sync); CS-1 misurabile. |
| VI — Idempotenza/determinismo/non-distruttività | **PASS** | blocchi a marker idempotenti; reference owned-file (create/update/remove); install≠run. |
| VII — Leggibilità | **PASS** | blocchi più scansionabili (segnale standing non diluito). |
| VIII — Config centralizzata | **N/A** | nessuna manopola. |
| IX — Osservabilità | **N/A** | nessuna operazione di runtime nuova. |
| X — Host-agnostico | **PASS** | body byte-identici Claude↔Copilot; reference host-agnostico; parità+closure a guardia. |
| XI — Consumo via vehicles | **PASS** | ZERO import/modifica `sertor_core`; l'unica modifica di codice è nell'installer host-facing. |
| XII — Fail Loud, Fix the Cause | **PASS** | la regola «errore MCP = segnale» resta tra le direttive standing del RAG block ridotto; guardie fail-loud sulla reintroduzione. |
| **Allineamento alla missione** | **PASS** | il budget di contesto è risorsa finita: ~42 righe always-on di lookup in meno = più budget per il **contesto fuso code+doc** reso all'agente, e una **fonte unica** che il plan/upgrade tiene senza deriva. Protegge la stella polare (qualità/realtà del contesto). |

**Gate PRE: PASS 12/12 (+ missione).** Nessuna deroga; Complexity Tracking vuoto.

## Project Structure (artefatti)
```
specs/079-altitude-claude-md/
├─ spec.md                  (input)
├─ plan.md                  (questo file)
├─ research.md              (DA-D-r1..r4 risolte)
├─ data-model.md            (entità/relazioni di asset)
├─ contracts/
│  ├─ reduced-blocks.md     (substringhe stabili C1..C6)
│  └─ guard.md              (contratto guardie G1..G7)
├─ quickstart.md            (verifica offline e2e)
└─ checklists/              (preesistente)
```

## Phase 0 — Research (completata)
Vedi `research.md`. Tutti gli ignoti di *come* risolti; ancoraggio reale verificato (asset, righe,
wiring, guardie); residui promossi (R-eval→FEAT-022; budget→FEAT-024; stub copilot→FEAT-023).

## Phase 1 — Design (completata)
- **`data-model.md`** — E1 blocchi ridotti, E2 reference (NUOVO, FILE→`.sertor/`), E3 pointer, E4 copie
  inline da centralizzare, E5 guardie, E6 dogfood; relazioni di closure per-capacità; vincoli VR-1..4.
- **`contracts/reduced-blocks.md`** — substringhe stabili di presenza/assenza per RAG/wiki/SDLC + il
  reference + `guided-setup`/`wiki-playbook` (C1..C6).
- **`contracts/guard.md`** — G1 non-reintroduzione, G2 fonte unica, G3 pointer, G4 closure reference,
  G5 rework presence, G6 parità, G7 sync; mappa contratto→requisito→criterio.
- **`quickstart.md`** — verifica offline e2e (altitude, fonte unica, pointer, guardie, sync,
  non-regressione, closure).
- **Aggiornamento `CLAUDE.md`** — riferimento al piano `079` in testa, `078` storicizzato (marker
  `<!-- SPECKIT START/END -->` non presenti in questo repo: si aggiorna il blocco-plan testuale come
  per le feature precedenti).

### Sequenza di implementazione (per `tasks`)
1. Creare `assets/rag/sertor-cli-reference.md` (contenuto C4, host-agnostico).
2. Aggiungere l'`Artifact` FILE al `build_rag_plan` (`install_rag.py`), target `.sertor/sertor-cli-reference.md`;
   verificare copertura owned (owned_dir `.sertor`) + upgrade/uninstall (coverage test plan⊆owned).
3. Ridurre il RAG block (C1) + pointer; ridurre il wiki block (C2) + pointer playbook.
4. Rimuovere la sezione inline da `guided-setup` (C5) + pointer; ridurre il `wiki-playbook` (C6,
   closure-safe).
5. `python -m sertor_installer.sync` → re-sync `.claude/skills/wiki-author/wiki-playbook.md`.
6. Estendere/rework guardie: closure reference (G4), non-reintroduzione (G1), fonte unica (G2), pointer
   (G3), rework presence (G5); assert gemello SDLC in `sertor-flow`.
7. `pytest -m "not cloud"` (root + 3 pacchetti) + `ruff` verdi.

## Constitution Check — POST-design (Phase 1 gate)
Rivalutato dopo il design. Nessuna entità/seam nuovo introdotto; il design conferma:
- **Principio XI:** l'unica modifica di codice è in `install_rag.py` (installer host-facing), che
  consuma i meccanismi esistenti del kit; **nessun** import/uso di `sertor_core`. **PASS.**
- **Principio X:** reference + blocchi ridotti host-agnostici, parità+closure a guardia (G4/G6).
  **PASS.**
- **Principio III (DRY):** la fonte unica `sertor-cli-reference.md` elimina la triplicazione → DRY
  *rafforzato*; nessun nuovo `ArtifactKind`/`WriteStrategy`/`Surface`. **PASS.**
- **Missione:** ridotto il rumore always-on, protetto il budget per il contesto fuso e tolta la deriva
  tra copie. **PASS.**

**Gate POST: PASS 12/12 (+ missione)**, identico al PRE. Nessuna deroga; **Complexity Tracking vuoto**.

## Complexity Tracking
*(vuoto — nessuna deviazione dai principi.)*

## Ignoti residui (NEEDS CLARIFICATION)
Nessuno. Le forche di *cosa* (DA-1/DA-2) sono risolte in spec; quelle di *come* (DA-D-r1..r4) in
research. I rinvii reali sono già a casa durevole (FEAT-022/023/024).
