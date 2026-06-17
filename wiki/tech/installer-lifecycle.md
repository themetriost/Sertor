---
title: Ciclo di vita dell'installer (upgrade / uninstall)
type: tech
tags: [installer, lifecycle, upgrade, uninstall, sertor-install-kit, sertor-flow, feat-008]
created: 2026-06-17
updated: 2026-06-17
sources: ["specs/048-lifecycle-installer/plan.md", "specs/048-lifecycle-installer/research.md", "requirements/sertor-cli/lifecycle-installer/requirements.md", "packages/sertor-install-kit/src/sertor_install_kit/lifecycle.py", "docs/install.md"]
---

# Ciclo di vita dell'installer (upgrade / uninstall)

FEAT-008 (epica `sertor-cli`, feature 048, PR #71, 2026-06-17) estende l'installer **oltre il primo
install**: i verbi **`upgrade`** e **`uninstall`** per i pacchetti `sertor` e `sertor-flow`. Prima
esisteva solo l'install (additivo, idempotente, `CREATE_IF_ABSENT`/`MERGE_*`): aggiornare un ospite
dopo un avanzamento su `master` lasciava i file già presenti `SKIPPED` e gli artefatti obsoleti
orfani; rimuovere Sertor era una procedura manuale (`docs/install.md §10.3`). Ora è un comando.

## I comandi

- **`sertor upgrade [capacità…]`** — rinfresca gli asset standalone cambiati, aggiorna i blocchi a
  marker se il contenuto del bundle differisce, rimuove gli artefatti diventati obsoleti.
- **`sertor uninstall [capacità…]`** — rimozione completa e selettiva. **Tutto-in-uno** (≡ `wiki rag
  governance`) **e** per-capacità (decisione Q3). Il `wiki/` è **preservato di default** (vedi
  `--purge-wiki`).
- **`sertor-flow upgrade`/`uninstall`** — simmetrici, per la governance/SDLC (decisione Q4: in ambito
  nello stesso ticket). Riusano le stesse primitive del kit; **nessuna dipendenza da `sertor-core`/`sertor`**.

Flag comuni: `--assistant claude|copilot|copilot-cli`, `--dry-run`, `--json`. Fail-fast no-rollback,
exit `0` successo · `1` errore di dominio · `2` usage error. `install ≠ run` vale anche qui: nessuna
indicizzazione parte mai.

## Le decisioni di design (D1–D4)

- **D1 — un verbo ortogonale, non una tassonomia inversa.** Scartato il raddoppio di
  `WriteStrategy`/`ArtifactKind` (un `REMOVE_*` per ogni additivo). Scelto un enum **`LifecycleOp`
  `{INSTALL, UPGRADE, UNINSTALL}`** + due `Outcome` nuovi (`UPDATED`, `REMOVED`) + **funzioni inverse
  pure**, duali 1:1 delle additive, tutte nel `sertor-install-kit`. Una sola tassonomia, una sola
  fonte di verità: la divergenza tra install e uninstall è **impossibile per costruzione** (guard di
  simmetria a 0 divergenze nei test).
- **D2 — riuso dello stesso plan-builder.** Upgrade e uninstall percorrono gli **stessi**
  `build_rag_plan`/`build_install_plan`/`build_governance_plan` dell'install, col verbo passato a
  `execute_plan(plan, op)`; il dispatch `apply(artifact, op)` sceglie la funzione additiva o inversa.
  Niente secondo plan-builder da tenere allineato.
- **Q2/D3 — diff a posteriori, niente manifest.** Per sapere cosa è obsoleto non serve uno store
  persistente: una funzione pura **`sertor_owned_paths(capability, assistant)`** dichiara i path
  Sertor-owned (derivati dalle costanti già nei plan-builder + `AssistantProfile`). Un artefatto è
  obsoleto se è su disco sotto un path owned ma assente dal bundle corrente. Un **test invariante
  `plan ⊆ owned`** garantisce che la dichiarazione copra ogni artefatto prodotto — sostituisce il
  manifest che sarebbe stato il punto critico (Q2).
- **Q1/D4 — `--purge-wiki` opt-in e CI-safe.** `uninstall wiki` **non** cancella mai la cartella
  `wiki/` di default (contiene documentazione reale): rimuove tutto il resto della capacità. Per
  cancellarla serve `--purge-wiki` + `--yes` (o conferma su TTY). Senza TTY e senza `--yes` la dir è
  **preservata** con avviso azionabile (deterministico in CI); `--purge-wiki --dry-run` è un usage
  error (exit 2); `--purge-wiki` su `rag`/`governance` è un usage error.

## Tipi di artefatto e operazioni inverse

L'uninstall rispetta le quattro tipologie già note dall'install:

| Tipo | Esempio | Operazione di rimozione |
|------|---------|--------------------------|
| **A** runtime isolato | `.sertor/` (venv, `.env`, store, indici) | rimozione in blocco (interamente Sertor-owned) |
| **B** asset standalone | skill, agenti, prompt-file, hook script | rimozione del file |
| **C** file condivisi | `CLAUDE.md`, `.gitignore`, `.claude/settings.json` | rimozione dei **soli** blocchi a marker Sertor / linee / entry — il resto **byte-per-byte intatto** |
| **D** registrazione MCP | server `sertor-rag` nel client | de-registrazione (`claude mcp remove` per scope `local`; entry-only per scope `project`) |

I blocchi a marker rimossi sono `SERTOR:WIKI-RITUAL`, `SERTOR:RAG-USAGE`, `SERTOR:SDLC-RITUAL`. Il
report usa lo **schema `install.report/1` esteso in modo additivo** con gli outcome `updated`/`removed`
— non un secondo schema (NFR-06).

## Invarianti

Non-distruttività (mai toccare contenuto non-Sertor nei file condivisi), idempotenza (ri-eseguire
converge), fail-fast no-rollback, primitive **stdlib-only** nel kit (NFR-07). Le primitive inverse
sono nel `sertor-install-kit` (sede unica) e consumate sia da [[sertor-installer]] (`sertor`) sia da
[[sertor-flow]] — è l'embodiment del confine [[deterministic-vs-judgment|meccanico]] e del riuso DRY
imposto dalla [[constitution]].

Vedi anche: [[sertor-install-kit]] · [[sertor-installer]] · [[sertor-flow]] · [[assistant-targeting]].
