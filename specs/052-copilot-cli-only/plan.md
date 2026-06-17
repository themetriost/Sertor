# Implementation Plan: consolidamento della distribuzione Copilot su un solo target (CLI-only)

**Branch**: `052-copilot-cli-only` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/052-copilot-cli-only/spec.md` (FEAT-012, epica `sertor-cli`)

## Summary

Consolidamento della distribuzione Copilot su un **solo target esposto, `copilot-cli`** (la CLI),
eliminando alla radice il footgun di due target paralleli e non-equivalenti dietro lo stesso flag
`--assistant`. Refactor **sottrattivo** confinato ai tre pacchetti installer: si **rimuove totalmente**
il target VS Code (`AssistantId.COPILOT`) dal seam condiviso (Q1=a), si **unifica il naming** a
`claude|copilot-cli` su `sertor` e `sertor-flow` (Q4=a, breaking diretto), si rende la skill
`requirements` un **custom-agent** invocabile da CLI (già abilitato dal seam FEAT-011, basta esporre il
target), si mappa `copilot-cli → --ai copilot` per spec-kit in un **unico punto documentato**
(`_SPECKIT_AI_FLAG`) e si allinea la **verifica del layout** idempotente. `sertor-core` **invariato**
(NFR-03). Anti-drift preservato (sorgente canonica Claude + renderer del kit). Non-regressione Claude =
gate duro. Nodi di *come* risolti in [research.md](./research.md); contratto in
[contracts/assistant-cli.md](./contracts/assistant-cli.md).

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: stdlib-only nel kit (`sertor-install-kit`); `sertor` dipende da `sertor-core`
+ kit; `sertor-flow` dipende **solo** dal kit (NO `sertor-core`, VIN-04/FR-045). Lancio upstream via
`uvx` + spec-kit pinned `0.8.18`.

**Storage**: N/A (l'installer deposita artefatti su filesystem dell'ospite; nessun DB).

**Testing**: pytest offline (`FakeCommandRunner`/`FakeSpecifyRunner`), `ruff`. CI senza cloud
(`-m "not cloud"`).

**Target Platform**: cross-platform (Windows/POSIX); script hook `.ps1` riusati byte-for-byte.

**Project Type**: librerie/CLI installer (3 pacchetti del `uv` workspace) + documentazione utente.

**Performance Goals**: N/A (operazione d'installazione, non hot-path).

**Constraints**: `install ≠ run`; non-distruttività; idempotenza; anti-drift (sorgente canonica unica);
breaking change esplicita su `copilot` (exit di errore nominante); `sertor-core` intoccato.

**Scale/Scope**: refactor mirato — 1 enum value rimosso, 1 ramo profilo eliminato, branching consumatori
semplificato in 3 file `sertor` + 2 file `sertor-flow`, 1 mappa nuova, ~8 file di test riallineati, 3 doc.

## Constitution Check

*GATE: passato PRIMA della Phase 0 e RI-VALUTATO dopo la Phase 1. Costituzione v1.2.0.*

### Pre-design (prima della Phase 0)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il refactor non tocca il core; il kit resta
  stdlib-only senza dipendenze dal nucleo (VIN-04). `sertor-flow` non importa `sertor-core`. **PASS**
- [x] **II — Boundary & local-first:** nessuna dipendenza esterna nuova; lancio spec-kit dietro
  `CommandRunner` (boundary già esistente). **PASS**
- [x] **III — YAGNI & unità piccole:** rimozione di codice (meno rami), una sola mappa nuova
  (`_SPECKIT_AI_FLAG`); nessuna astrazione aggiunta. **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** `copilot` legacy → `ConfigError`/argparse nominante,
  exit di errore (FR-001, NFR-02); nessun fallback silenzioso. **PASS**
- [x] **V — Testabilità & misure:** test F.I.R.S.T. offline; tabella di copertura (research §Nodo 4)
  garantisce nessuna superficie scoperta (SC-008). Retrieval/qualità non pertinenti (no core). **PASS**
- [x] **VI — Idempotenza & non-distruttività:** `_EXPECTED_LAYOUT` allineato preserva l'idempotenza
  (SC-007); installer non-distruttivo invariato; `install ≠ run`. **PASS**
- [x] **VII — Leggibilità:** nomi di dominio del seam (`AssistantProfile`, `CommandVehicle`); commenti
  d'intenzione sul mapping; rimozione di rami riduce il nesting. **PASS**
- [x] **VIII — Configurabilità centralizzata:** il target assistente resta config (flag), non presunto
  nel corpo; mapping upstream centralizzato in un punto. **PASS**
- [x] **IX — Osservabilità:** gli eventi `log_event` esistenti (`speckit_launch`, lifecycle) restano;
  nessun segreto nei log. **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** `AssistantProfile.for_assistant` resta l'unico punto che
  conosce le convenzioni per-assistente (VIN-05); i plan-builder non guadagnano assunzioni d'ospite. La
  rimozione di un target non introduce path fissi. **PASS**
- [x] **XI — Consumo via vehicles:** il `--check`/probe non è in ambito; il refactor riguarda solo
  l'installer (deposita artefatti). Nessun consumo runtime del core introdotto. **PASS**

**Esito pre-design: PASS 11/11, nessuna deroga.**

### Post-design (dopo la Phase 1)

Ri-valutato sugli artefatti generati (research/data-model/contracts/quickstart). Il design **conferma**
ogni gate:

- I/III/VII migliorano (meno codice, meno rami: rimozione enum value + ramo profilo + branching
  consumatori; una sola mappa aggiunta).
- IV confermato dal contratto C1.1 (errore nominante) e dalla derivazione dell'errore dal `from_str`
  esistente (nessuna logica fragile nuova).
- VI confermato da C3.4/§5 data-model (chiave `_EXPECTED_LAYOUT["copilot-cli"]` con marker spec-kit
  Copilot → idempotenza preservata).
- X confermato: il seam resta l'unico locus delle convenzioni; nodo 3 dimostra che il comportamento
  corretto **emerge dal profilo** senza ramificare nei plan-builder.
- NFR-03/SC-010 (core invariato) rispettato by design (C5.1).

**Esito post-design: PASS 11/11, nessuna deroga.** *Complexity Tracking* vuoto.

## Project Structure

### Documentation (this feature)

```text
specs/052-copilot-cli-only/
├── plan.md              # questo file
├── research.md          # Phase 0 — 5 nodi di "come" risolti
├── data-model.md        # Phase 1 — entità del seam (ristrette)
├── quickstart.md        # Phase 1 — verifiche offline US1..US7
├── contracts/
│   └── assistant-cli.md # Phase 1 — contratto CLI + mapping upstream
├── checklists/          # (preesistente)
└── tasks.md             # Phase 2 — /speckit-tasks (NON creato qui)
```

### Source Code (file impattati — refactor, no nuova struttura)

```text
packages/sertor-install-kit/src/sertor_install_kit/
├── assistant.py         # RIMUOVI enum COPILOT (riga 25) + ramo for_assistant COPILOT (156-176)
└── surfaces.py          # invariato (render_prompt_file resta primitiva; non più richiamato dai plan)

packages/sertor/src/sertor_installer/
├── __main__.py          # help --assistant: rimuovi "(VS Code) | copilot-cli" → "claude | copilot-cli" (84-101,196-198)
├── install_rag.py       # is_copilot → is COPILOT_CLI; rimuovi is_vscode/servers (249-253,459-460); nota [ASSUNTO-VSC] (368-374)
└── install_wiki.py      # _build_copilot_wiki_plan: rimuovi ramo SessionStart VS Code + script (108-159,254-258); nota gap (398-399); owned (429-430)

packages/sertor-flow/src/sertor_flow/
├── __main__.py          # choices ["claude","copilot"] → ["claude","copilot-cli"] (46-49,59-62)
├── speckit_launch.py    # + _SPECKIT_AI_FLAG; build_specify_command usa mapping (90); _EXPECTED_LAYOUT chiave copilot→copilot-cli (55-64)
└── install_governance.py # nota [ASSUNTO-VSC] su assistant=="copilot" (295-302): rimuovi/aggiorna

packages/sertor/tests/, packages/sertor-flow/tests/, packages/sertor-install-kit/tests/
└── (riallineamento per la tabella di copertura research §Nodo 4)

docs/install-copilot.md, docs/install.md, packages/sertor/docs/install.md
└── un solo percorso copilot-cli + nota di migrazione (research §Nodo 5)
```

**Structure Decision**: nessuna nuova struttura. Il refactor agisce sul seam `AssistantProfile`
(`sertor-install-kit`) e si propaga ai due consumatori (`sertor`, `sertor-flow`) per costruzione del
tipo condiviso (VIN-02/A-3). Le directory esistenti sono quelle dei tre pacchetti del `uv` workspace.

## Decisioni sui 5 nodi di *come* (sintesi; dettaglio in research.md)

1. **Rimozione `COPILOT`**: totale a 3 cerchi — enum value, ramo `for_assistant`, semplificazione
   `is_copilot → is COPILOT_CLI` nei consumatori. L'errore nominante su `copilot` cade dal `from_str`
   esistente (no logica nuova). `CommandVehicle.PROMPT_FILE`/`render_prompt_file` **restano** (non
   VS-Code-specifici; Claude usa il default), ma nessun plan li richiama più.
2. **Mapping upstream**: `_SPECKIT_AI_FLAG = {"claude":"claude","copilot-cli":"copilot"}` in
   `speckit_launch.py`, usato in `build_specify_command`; `_EXPECTED_LAYOUT` rinominato `copilot →
   copilot-cli` con i marker spec-kit Copilot invariati (idempotenza).
3. **Skill `requirements` su CLI**: nessun ramo nuovo — il profilo `copilot-cli` (FEAT-011,
   `command_vehicle=CUSTOM_AGENT`) già risolve COMMAND→`.github/agents/*.agent.md`. Azione concreta: solo
   esporre `copilot-cli` in `sertor-flow` (nodo Naming) + copertura test.
4. **Test**: tabella superficie→test (research §Nodo 4) — rimozione sottrattiva dei rami VS Code +
   completamento dei casi unici su `copilot-cli`; nessuna superficie scoperta (SC-008). Tutto offline.
5. **Nota di migrazione**: inline in `docs/install-copilot.md` (un solo percorso `copilot-cli`),
   richiamata da `docs/install.md` + copia `packages/sertor/docs/install.md`.

## Out of Scope (confine locale; promozioni)

Coerente con spec §Assumptions. Tutte le voci rinviate sono **capacità future già censite** (nessuna
nuova promozione richiesta da questo plan):

- **Supporto VS Code come target** (riapertura `copilot`): nuova feature separata se mai emergesse un
  caso d'uso reale (A-1). Non un rollback.
- **Rilevamento/migrazione automatica** per ospiti VS Code esistenti: escluso (Q3=a); solo nota
  documentale.
- **`sertor-rag check` / probe live** (`--check` di FEAT-003/051): follow-up già tracciato (backlog
  `sertor-core`, gemella self-test MCP). Fuori ambito qui.
- **Nuovi assistenti** oltre `claude`/`copilot-cli`, cloud-agent/Codex: già Won't in FEAT-007.

Nessuna voce resta sepolta solo in `specs/052-…/`: tutte mappano su capacità future già nel
backlog/roadmap o sono confini di scope dichiarati.
