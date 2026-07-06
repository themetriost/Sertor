# Implementation Plan: asset-install — gli asset del dogfood dall'installer (0 special-case)

**Branch**: `089-asset-install` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/089-asset-install/spec.md` · Requisiti
`requirements/fedelta-dogfood/asset-install/requirements.md` (E15-FEAT-001 scope B, assorbe FEAT-003/004).

## Summary

Chiudere la **metà asset** della fedeltà dogfood: gli asset host-facing del dogfood devono avere come
**fonte** l'esecuzione dei veri `sertor install rag` / `sertor install wiki` / `sertor-flow install`
**sul dogfood**, non il `sync` interim né `materialize-speckit.ps1`. Il dry-run del 2026-07-04 ha
dimostrato che l'esito è **per lo più idempotente** (asset già byte-fedeli via sync → `skipped`;
`.env`/costituzione/`.mcp.json`/`wiki.config` preservati); il residuo di process-fidelity è **piccolo e
mappato**: (a) 3 blocchi marker in `CLAUDE.md` da riconciliare con la prosa hand-written (ibrido
per-blocco); (b) churn CRLF che rende il diff illeggibile; (c) `wiki/log.md` legacy spurio.

**Approccio tecnico.** La feature è **90% una procedura operativa** deterministica, reversibile e
documentata (eseguire i 3 installer sul branch, ispezionare il diff, riconciliare, committare) + **poche
modifiche chirurgiche host-agnostiche**:
1. **`.gitattributes` LF** (FR-005, contenuto di E15-FEAT-010) — nel dogfood, nel bundle `assets/` e nel
   **template installer** (host-facing: ogni ospite Windows ne beneficia); rinormalizzazione a LF così le
   guardie byte confrontano LF↔LF.
2. **Riconciliazione `CLAUDE.md`** ibrida per-blocco (FR-003/004) — *dogfood-only*, tocca solo lo stato del
   dogfood, non un asset distribuito.
3. **`wiki/log.md` legacy** (FR-008) — scartato nel dogfood; il template allineato alla rotazione è slice
   coordinata di E15-FEAT-006 (vedi *Structure Decision*).
4. **Doc/rituale + guardie** (FR-006) — sync/script retrocessi a *guardia/dev-tool* (non fonte); guardie
   byte rese EOL-consistenti e tenute verdi; doc utente aggiornata per `.gitattributes`.

`sertor-core` resta **invariato** (Principio XI); nessun asset distribuito diventa Sertor-specifico
(Principio X). Operazione su branch con **diff ispezionabile prima del commit** (Principio XII, FR-009).

## Technical Context

**Language/Version**: Python ≥ 3.11 (installer `sertor`/`sertor-flow`/`sertor-install-kit`); PowerShell 7+
per la procedura operativa; Git (config `.gitattributes` / `renormalize`).

**Primary Dependencies**: `sertor-installer`, `sertor-flow`, `sertor-install-kit` (già nel workspace);
`uvx` (per `specify init` durante `sertor-flow install`) — **richiede rete** (NFR-3). Nessuna nuova dip.

**Storage**: filesystem del repo — asset in `.claude/`, `.specify/`, `CLAUDE.md`, `settings.json`,
`.sertor/` (runtime, parzialmente gitignorato); bundle canonici in `assets/` dei tre package.

**Testing**: `uv run pytest -m "not cloud"` (suite completa, gate pre-merge E15-FEAT-008) + `ruff check .`;
guardie byte `tests/unit/test_assets_sync.py`, `tests/unit/test_assets_rag_dogfood_sync.py`,
`packages/sertor-flow/tests/unit/test_assets_sync.py`; nuovo test negativo EOL/guard.

**Target Platform**: repo di sviluppo Sertor su Windows (dogfood = host Claude). La modifica host-facing
(`.gitattributes` nel template) beneficia **ogni** ospite (Windows in primis; no-op su Unix, già LF).

**Project Type**: governance/process feature su un monorepo multi-package (single project, no web/mobile).

**Performance Goals**: N/A (operazione one-shot + procedura ripetibile a ogni bump; non un percorso caldo).

**Constraints**: **non-distruttivo/idempotente** (VI); reversibile su branch (XII); `sertor-core` byte-
invariato; nessun asset distribuito Sertor-specifico (X); offline **non** supportato (NFR-3).

**Scale/Scope**: 3 installer, ~un centinaio di asset host-facing byte-copiati, 3 blocchi marker in
`CLAUDE.md`, 3 guardie byte. Residuo reale mappato dal dry-run: ~174 righe in `CLAUDE.md` + wiring
`settings.json` + `.sertor/sertor-cli-reference.md`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Costituzione v1.4.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. `sertor-core` **invariato**; le modifiche
  vivono in `sertor-installer`/`sertor-flow`/`sertor-install-kit` (i vehicles) e nei bundle `assets/`.
  Nessun SDK nuovo, nessun import del core a runtime.
- [x] **II — Boundary & local-first:** N/A. Nessun provider/backend/vector store toccato.
- [x] **III — YAGNI & unità piccole:** PASS. Si **riusa** il meccanismo esistente (marker-block idempotente
  `write_marker_block`, preservazione FEAT-005, guardie byte); l'unica aggiunta è un `.gitattributes`
  (una riga) + una slice template `wiki/log/`. Nessuna astrazione nuova.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. Procedura fail-loud: install report + `git diff`
  ispezionati; nessuno stato parziale silenzioso; ogni clobber nuovo emerge sul branch prima del commit.
- [x] **V — Testabilità & misure:** PASS. Guardie byte restano verdi (rese EOL-consistenti) + test negativo
  che fallisce su drift indotto; idempotenza **verificata** con due esecuzioni (NFR-1), non assunta.
- [x] **VI — Idempotenza & non-distruttività:** PASS. È il cuore della feature: install idempotente,
  preservazione degli artefatti curati, install≠run, nessuna sovrascrittura silenziosa.
- [x] **VII — Leggibilità:** PASS. `.gitattributes` documentato per intenzione; procedura in prosa chiara.
- [x] **VIII — Configurabilità centralizzata:** N/A (nessun default di core). Il line-ending è policy di
  repo (`.gitattributes`), non un default hardcoded in un componente.
- [x] **IX — Osservabilità:** PASS. L'esito di ogni install è **ispezionabile** (InstallReport + diff git,
  NFR-2), coerente con fail-loud; nessun segreto nei report.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS. Il `.gitattributes` nel template è **generico**
  (`* text=auto eol=lf`, beneficia ogni host); i blocchi marker restano EN/host-agnostici. La
  riconciliazione ibrida di `CLAUDE.md` tocca **solo lo stato del dogfood** (bilingue per costruzione:
  blocchi-client EN + governance-dogfood IT), non un asset distribuito. Il dogfooding non deroga X.
- [x] **XI — Consumo via vehicles:** PASS. La feature **rafforza** XI: gli asset arrivano dai veri
  installer (i vehicles), non da uno script che li deposita a mano. Post-merge re-index via
  `sertor-rag index .`; nessun import di `sertor_core`.
- [x] **XII — Fail Loud, Fix the Cause:** PASS. Si **ritira una scorciatoia silenziosa** (sync come fonte)
  in favore del processo reale e ispezionabile; il churn CRLF **nascondeva** i diff reali → si rimuove la
  causa (policy EOL), non si sopprime; le guardie falliscono forte sul drift.
- [x] **Allineamento alla missione:** PASS (infra/governance a servizio della missione). La process-fidelity
  rende il dogfood un **client Sertor fedele** → il percorso d'install (fusione code+doc installabile
  ovunque) è **davvero esercitato** prima di raggiungere gli ospiti: bug come la duplicazione marker-block
  emergono qui, non sull'ospite. Non tocca direttamente il retrieval, ma serve la portabilità/installabilità
  che è la missione. Nessuna deriva su concern periferici.

**Esito: 12/12 + missione PASS.** Nessuna violazione → nessun *Complexity Tracking* da compilare.

## Project Structure

### Documentation (this feature)

```text
specs/089-asset-install/
├── plan.md              # questo file
├── research.md          # Phase 0: decisioni (DD-1/DD-2, DA-2/3/6), risoluzione FEAT-009/010/006
├── data-model.md        # Phase 1: tassonomia asset · artefatti curati · guardie · esiti install
├── quickstart.md        # Phase 1: RUNBOOK operativo (i 3 installer sul dogfood, reversibile)
├── contracts/
│   └── verification.md   # Phase 1: contratto di verifica (guardia byte EOL-consistente + test idempotenza)
├── checklists/
│   └── requirements.md   # (già presente)
└── tasks.md             # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)

La feature tocca **stato del dogfood** + **tre punti host-agnostici** nei package installer; `src/`
(`sertor-core`) resta invariato.

```text
# Modifiche host-agnostiche (distribuite / template) — beneficiano ogni ospite
.gitattributes                                      # NUOVO — policy EOL del repo dogfood (LF)
packages/sertor/src/sertor_installer/assets/
  └── wiki/                                          # slice: .gitattributes nel template + rotazione log/
packages/sertor-flow/src/sertor_flow/assets/         # (se il bundle governance tocca line-ending)
packages/*/…/assets/**                               # rinormalizzati a LF (guardia byte LF↔LF)

# Stato del dogfood — riconciliazione (NON distribuito)
CLAUDE.md                                            # riconciliazione ibrida per-blocco + prosa preservata
.claude/**, .specify/**, settings.json               # esito dei veri installer (idempotente)
.sertor/sertor-cli-reference.md                      # residuo non-byte prodotto dall'install (FR-007)
wiki/log.md                                          # SCARTATO (legacy) — la conoscenza resta in wiki/log/

# Guardie & doc
tests/unit/test_assets_sync.py                        # resa EOL-consistente, tenuta verde
tests/unit/test_assets_rag_dogfood_sync.py            # idem
packages/sertor-flow/tests/unit/test_assets_sync.py   # idem
tests/unit/test_asset_install_eol.py                  # NUOVO — test negativo EOL/guard (SC-2/SC-4)
docs/install.md, docs/install-claude.md, README.md    # doc utente: nota .gitattributes/EOL (FEAT-010)
scripts/dev/materialize-speckit.ps1                   # retrocesso a dev-tool (commento/doc), non fonte
```

**Structure Decision.** Single project / monorepo multi-package. La feature è una **procedura operativa**
(quickstart = runbook) più tre modifiche di codice **minime e host-agnostiche**. **Confine di scope
fissato al plan** (chiude l'assunzione della spec §Assumptions):
- **E15-FEAT-010 (`.gitattributes` nel template) = IN AMBITO** in questa feature — è il prerequisito diretto
  di FR-005 (no-churn), è piccolo e host-agnostico, e la regola «feature completa = installabile su ospite»
  impone di cablarlo nel template + doc utente nello stesso step.
- **E15-FEAT-006 (template `wiki/log/` rotazione) = SLICE MINIMA in ambito, resto rinviato.** Qui: (a)
  scartare il `wiki/log.md` spurio nel dogfood; (b) far sì che il template/installer produca la struttura
  di rotazione **o** dichiari il `wiki/log/` del dogfood come forma-client (decisione in research). La
  riscrittura completa della meccanica di rotazione lato template resta **E15-FEAT-006** proper (promossa,
  non sepolta).

## Complexity Tracking

> Nessuna violazione costituzionale → sezione vuota.
