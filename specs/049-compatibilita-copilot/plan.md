# Implementation Plan: Hardening compatibilità GitHub Copilot dell'installer

**Branch**: `049-compatibilita-copilot` | **Date**: 2026-06-17 | **Spec**: `specs/049-compatibilita-copilot/spec.md`

**Input**: Feature specification from `specs/049-compatibilita-copilot/spec.md` (FEAT-011, epica `sertor-cli`)

---

## Summary

Correzione di FEAT-007 (PR #64) e FEAT-009 (PR #65) dopo un audit di dogfooding (Copilot CLI 1.0.63) che ha
dimostrato che la "parità funzionale piena" Copilot dichiarata è **falsa** su più superfici: l'installer
deposita artefatti in **formato Claude** non conformi allo schema Copilot (hook JSON senza `version:1` →
scartati in silenzio; output `.ps1` `systemMessage` Claude-only; SessionStart con stringhe nude; comandi
solo-prompt-file non invocabili su CLI; `mode:` invece di `agent:`; `model:` Claude nei custom-agent).

**Approccio**: tradurre ogni superficie nel **formato/contratto nativo** del tool target (principio guida:
NIENTE hack di compatibilità), riusando il **CONTENUTO** (corpo istruzionale + corpo logico degli script,
fonte unica byte-for-byte) e traducendo nativamente il **CONTENITORE/contratto**. Tutto vive nei pacchetti
installer (`sertor-install-kit` stdlib-only · `sertor` · `sertor-flow`), passa per il seam
`AssistantProfile`/`Surface`, ed è coperto da una suite di **validità-schema offline** (gruppo G) che
avrebbe preso i bug dell'audit. `sertor-core` invariato; `sertor-flow` resta senza dipendenza da
`sertor-core`/`sertor`.

I due nodi di design sono risolti in `research.md`:
1. **SessionStart VS Code**: wiring per-famiglia (CLI `type:"prompt"`; VS Code `type:"command"` →
   `{additionalContext}`), con **[ASSUNTO-VSC]** dichiarato (non verificato sul campo) + fallback nativo.
2. **Seam**: **estensione mirata** (4 interventi additivi), NON revisione profonda (YAGNI).

---

## Technical Context

**Language/Version**: Python ≥ 3.11 (kit/sertor/sertor-flow); script hook PowerShell (`.ps1`)

**Primary Dependencies**: `sertor-install-kit` **stdlib-only** (`json`, parsing frontmatter già esistente);
`sertor` e `sertor-flow` consumano il kit. Nessuna nuova dipendenza. `sertor-core` NON toccato.

**Storage**: N/A (artefatti su filesystem dell'ospite: `.github/**`, `.claude/**`, `.vscode/mcp.json`,
`.mcp.json`).

**Testing**: `pytest` offline (NFR-5): stdlib `json` per gli hook, parsing frontmatter per prompt/agent,
invocazione degli script con core mockato/`FakeCommandRunner` (pattern `test_install_*_copilot*.py`).
Nessun client Copilot reale.

**Target Platform**: ospite (qualsiasi progetto) con assistente Claude Code · GitHub Copilot VS Code agent
mode · GitHub Copilot CLI 1.0.x. Copilot coding agent cloud fuori scope (A-1).

**Project Type**: pacchetti installer in `uv workspace` (3 dei 4 membri: `sertor-install-kit`, `sertor`,
`sertor-flow`).

**Performance Goals**: N/A (operazioni install-time, deterministiche, locali).

**Constraints**: install ≠ run · non-distruttività · idempotenza · non-regressione `claude` (gate duro) ·
suite di schema OFFLINE · `sertor-flow` senza dipendenza da `sertor-core`/`sertor` · principio guida
(nativo, no dual-field/hack).

**Scale/Scope**: 43 FR (gruppi A–I), 8 user story (7×P1 + 1×P2), 11 SC. 2 pacchetti consumer
(`sertor`/`sertor-flow`) + 1 toolkit (`sertor-install-kit`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
Gate derivati da `.specify/memory/constitution.md` v1.2.0.

### Pre-design (prima di Phase 0) — **PASS 11/11**

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la feature NON tocca `sertor-core` (NFR-3);
  vive nei pacchetti installer. Il kit resta stdlib-only e non importa SDK/CLI di provider. **PASS.**
- [x] **II — Boundary & local-first:** nessuna dipendenza esterna nuova; tutto offline/locale. Gli unici
  "esterni" sono i tool host (`pwsh`/`uv`/`claude`) già dietro `CommandRunner`. **PASS.**
- [x] **III — YAGNI & unità piccole:** scelta esplicita di **estendere** il seam con parametri additivi
  invece di riprogettarlo (research §2); nessuna nuova `ArtifactKind`; il merge resta unico (dedup
  schema-aware). DRY: corpo script/contenuto = fonte unica. **PASS.**
- [x] **IV — Errori espliciti:** `AssistantId.from_str` già solleva `ConfigError`; gli script falliscono
  esplicitamente o (preToolUse) escono fail-open per evitare una negazione **silenziosa** di tool call —
  coerente con "niente stato corrotto". Nessun `None` silenzioso introdotto. **PASS.**
- [x] **V — Testabilità & misure:** suite di validità-schema F.I.R.S.T. e offline (gruppo G); reintroduzione
  difetti → fail (SC-007). Non c'è retrieval da misurare (feature d'installazione). **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** merge additivo dedup-by-command preservato; install≠run
  (nessuna indicizzazione); re-run stabile (FR-040/NFR-1). **PASS.**
- [x] **VII — Leggibilità:** rese hook/frontmatter come funzioni pure nominate (`render_copilot_hooks`,
  `render_prompt_file`, `render_custom_agent`); naming di dominio (Surface/AssistantProfile). **PASS.**
- [x] **VIII — Configurabilità centralizzata:** le differenze per-assistente passano TUTTE per il seam
  (`AssistantProfile`), unica sede delle convenzioni; nessun path hardcoded nuovo nei plan-builder. **PASS.**
- [x] **IX — Osservabilità:** l'installer emette già `InstallReport`/`log_event`; la dichiarazione dei gap
  nell'output d'installazione (FR-028) rafforza l'osservabilità onesta. **PASS.**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** è il cuore della feature — ogni superficie resa nel formato
  nativo del target via seam; nessuna assunzione d'ospite nel corpo; il dogfood (audit) non giustifica
  scorciatoie. **PASS.**
- [x] **XI — Consumo via vehicles:** la feature è tutta install-time; gli script hook consumano Sertor SOLO
  via la CLI (`sertor-wiki-tools scan`), MAI importando `sertor_core` (cfr. `wiki-pending-check.ps1`). I
  test esercitano le funzioni del kit direttamente (eccezione ammessa). **PASS.**

**Esito pre-design: PASS 11/11, nessuna deroga.**

### Post-design (dopo Phase 1) — **PASS 11/11**

Il design (research + data-model + contracts) non introduce violazioni:
- I/II preservati: `sertor-core` intatto, kit stdlib-only, nessuna nuova dipendenza/SDK.
- III confermato: estensione mirata (no revisione profonda, no nuove `ArtifactKind`, merge unico
  schema-aware); ogni intervento è additivo su funzioni esistenti.
- IV/VI: fail-open esplicito su preToolUse (no deny silenzioso), idempotenza/non-distruttività invariate.
- VIII/X: il seam resta l'unico punto delle convenzioni per-assistente (FR-043); `claude` default invariato.
- XI: nessun consumo runtime di `sertor_core` introdotto.
- FR-042/SC-011: il renderer condiviso vive nel kit → `sertor-flow` riusa senza dipendere da
  `sertor-core`/`sertor` (invariante verificata dai guard di simmetria esistenti).

**Esito post-design: PASS 11/11, nessuna deroga.** Complexity Tracking vuoto.

---

## Project Structure

### Documentation (this feature)

```text
specs/049-compatibilita-copilot/
├── plan.md                 # questo file
├── research.md             # Phase 0: risoluzione nodi #1/#2 + [ASSUNTO-VSC]
├── data-model.md           # Phase 1: estensioni del seam + contratti d'artefatto
├── contracts/
│   ├── copilot-hook-schema.md        # schema hook JSON Copilot (version:1, piatto, timeoutSec)
│   ├── hook-output-contract.md       # output script per evento/assistente (no dual-field)
│   ├── copilot-frontmatter.md        # prompt-file agent: / custom-agent no model: / veicolo COMMAND
│   └── surface-mapping-and-gaps.md   # claim di parità + dichiarazione gap (FR-027/028)
├── quickstart.md           # verifica offline degli asset Copilot
├── checklists/requirements.md        # (preesistente) checklist di qualità della spec
└── tasks.md                # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)

```text
packages/sertor-install-kit/src/sertor_install_kit/
├── assistant.py            # ESTENDERE: AssistantProfile copilot-cli → veicolo COMMAND custom-agent
├── surfaces.py             # MODIFICARE: render_prompt_file (agent:), render_custom_agent (no model);
│                           #             AGGIUNGERE render_copilot_hooks(events) + modello HookEntrySpec
└── settings_merge.py       # GENERALIZZARE: dedup schema-aware (forma piatta Copilot + annidata Claude)

packages/sertor/src/sertor_installer/
├── install_wiki.py         # piano comandi per-target (CLI custom-agent); wiring hook generato nativo;
│                           # SessionStart per-famiglia; dichiarazione gap nell'output
├── install_rag.py          # wiring rag-usage nativo Copilot; preToolUse fail-open garantito
├── assets/claude/hooks/wiki-pending-check.ps1   # + -Assistant; output nativo per evento
├── assets/claude/hooks/<wiki-session-start>.ps1 # NUOVO: estratto dall'inline + -Assistant
├── assets/.../sertor-rag-usage-check.ps1        # garantire exit 0 sempre su copilot
└── assets/copilot/hooks/*.json                  # RIMOSSI/SOSTITUITI dal wiring generato (no più formato Claude)

packages/sertor-flow/src/sertor_flow/
└── install_governance.py   # piano requirements per-target (CLI custom-agent); riusa renderer del kit

packages/{sertor,sertor-flow}/tests/   # gruppo G: suite di validità-schema offline (FR-021..026)
```

**Structure Decision**: nessuna nuova directory né pacchetto. Le modifiche si concentrano nel **seam
condiviso del kit** (fonte unica delle differenze per-assistente, FR-043/NFR-2) e nei due consumer. Gli
asset statici Copilot in formato Claude (`assets/copilot/hooks/*.json`) sono sostituiti dal wiring
**generato** nativo (research §2d). La suite di schema-validità è aggiunta nei test di `sertor` e
`sertor-flow`.

---

## Note di rischio per `/speckit-tasks`

- **R-1 (non-regressione Claude)**: ogni parametro nuovo ha default `claude`; gate duro = suite Claude
  esistente verde (SC-010). Eseguire la suite Claude PRIMA e DOPO ogni intervento sugli script condivisi.
- **R-2 (fail-closed preToolUse)**: garantire exit 0 incondizionato su `copilot`; test dedicato con stdin
  malformato (NFR-3).
- **R-3 (dedup merge schema-aware)**: la generalizzazione di `_inner_commands` deve restare retrocompatibile
  col formato Claude annidato (test su entrambe le forme).
- **[ASSUNTO-VSC]**: SessionStart VS Code resta **gap dichiarato** finché non confermato runtime; non
  promettere parità piena (FR-027/028). Fallback nativo pronto se smentito.
- **FR-020 (MCP CLI)**: nessuna modifica alla surface; solo documentazione dell'evidenza (PR #66) +
  caveat doc ufficiale. Correggere solo se una verifica empirica futura la smentisce.

---

## Complexity Tracking

> Nessuna violazione costituzionale da giustificare. Tabella vuota.
