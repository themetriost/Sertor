# Research — Distribuzione governance su Copilot (FEAT-009)

Phase 0. Risolve le due leve di design e la non-regressione Claude. Ground: lettura di
`packages/sertor-flow/src/sertor_flow/install_governance.py` (plan-builder reale) + seam FEAT-007 su
master + grounding spec-kit (giugno 2026): supporta `--ai copilot` di prima classe (genera
`.github/prompts/` + `.github/agents/`); `.specify/` è agent-agnostic.

## Stato attuale (cosa cambia)

`build_governance_plan` oggi: (1) copia `assets/claude/**` → `.claude/**` — **mischia** gli speckit-*
**vendorati** e i **Sertor-authored** (`requirements-analyst`, `configuration-manager`, skill
`requirements`); (2) copia `assets/specify/**` → `.specify/**`; (3) costituzione; (4) init generati;
(5) NOTICE/LICENSE (attribuzione del vendoring spec-kit); (6) blocco SDLC. `GovernanceProfile` ha **già**
un campo `assistant` (oggi guida solo i file init generati).

## Leva 1 — Pivot vendoring → launch-installer

- **Decisione:** rimuovere dal bundle gli asset **SpecKit** (`claude/skills/speckit-*`,
  `claude/agents/speckit-*`, `specify/**`, NOTICE/LICENSE di spec-kit) e ottenerli **lanciando l'installer
  di spec-kit** per l'assistente target: `specify init` (via `uvx`/CLI) con `--ai <assistant>` e lo
  `--script <ps|sh>` da `profile.script`, **a versione pinnata**.
- **Come (design):** nuovo `speckit_launch.py` in `sertor-flow` che invoca il comando via il
  **`CommandRunner` del kit** (già mockabile, usato da `install rag`). Dopo il lancio, **verifica il
  layout prodotto** (presenza delle superfici attese per l'assistente); assente/fallito/layout inatteso →
  **fail-fast** con messaggio azionabile (FR-004, SC-007). Nessuno stato parziale.
- **Refactor del path Claude (FR-012):** il lancio sostituisce il vendoring **per entrambi** gli
  assistenti. Per Claude il risultato deve restare **funzionalmente equivalente** all'odierno (stessi
  comandi/agenti SpecKit + `.specify/`); è il gate di non-regressione (test).
- **Rationale:** spec-kit è multi-assistente di prima classe → vendorare 2-3 varianti è debito; lanciare
  l'installer segue automaticamente gli assistenti upstream ed elimina il doppio vendoring.
- **Impatto offline (Principio II, deroga tracciata):** reintroduce un fetch a install-time. Confinato:
  versione **pinnata**, dietro `CommandRunner`, **fail-fast**. Dichiarato nel report e in Complexity
  Tracking. La governance non è una capacità RAG (II mira ai provider).
- **Alternative scartate:** *(a)* continuare a vendorare (offline puro) → N varianti da mantenere; *(b)*
  vendorare solo Copilot accanto a Claude → doppio vendoring, stesso debito.

## Leva 2 — Superfici Sertor-authored (traduzione, come FEAT-007)

- **Decisione:** `requirements-analyst`, `configuration-manager` (agenti), skill `requirements`, blocco
  rituale **SDLC** → resi per Copilot **riusando il renderer di FEAT-007**, che viene **spostato nel
  `sertor-install-kit`** (`surfaces.py`) così `sertor` e `sertor-flow` condividono un'unica
  implementazione (anti-drift/DRY, REQ-017). `sertor` reimporta dal kit (non-regressione FEAT-007).
- **Targeting:** via `AssistantProfile` (FEAT-007): agenti → `.github/agents/*.agent.md`, skill →
  `.github/prompts/*.prompt.md`, blocco SDLC → `.github/copilot-instructions.md` (marker
  `SERTOR:SDLC-RITUAL`, idempotente). Claude invariato (`.claude/**`, `CLAUDE.md`).
- **Costituzione-starter:** assistant-agnostic, installata identica (FR-009).
- **Alternativa scartata:** replicare il renderer in `sertor-flow` → divergenza dal renderer di `sertor`.

## Non-regressione Claude (gate)

Dopo il refactor, `sertor-flow install` con target **Claude** deve produrre una governance
**funzionalmente equivalente** all'odierna: stessi comandi/agenti SpecKit (ora da `specify init --ai
claude`), stesso `.specify/`, costituzione, blocco SDLC, init generati. Test di non-regressione su host
`tmp` con `specify` mockato (il mock emette il layout Claude atteso). La suite `sertor-flow` esistente
(106/107 test) resta verde.

## Decisioni confermate

- Client target = VS Code Copilot agent mode. Codex = fuori taglio (Could).
- Selettore `--assistant` = quello di FEAT-007 (default `claude`), riusato dal kit.
- Renderer condiviso nel kit (spostamento), non duplicato.

## Domande aperte → design

- **DA-4 — comando/versione spec-kit:** forma esatta dell'invocazione (`uvx --from git+... specify init`
  vs `specify` su PATH), versione pinnata (oggi 0.8.18 era vendorata), e gestione del caso offline. Da
  fissare nei task (è *how*, confinato in `speckit_launch.py`).
- **Migrazione ospiti già vendorati:** fuori ambito (dichiarato in spec).
