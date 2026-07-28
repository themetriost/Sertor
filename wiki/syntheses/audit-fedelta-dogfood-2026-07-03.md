---
title: Audit di fedeltà dogfood↔client (2026-07-03)
type: synthesis
tags: [audit, dogfood, fedeltà, installer, rag, wiki, governance]
created: 2026-07-03
updated: 2026-07-03
sources: ["packages/sertor/src/sertor_installer/**", "packages/sertor-flow/src/sertor_flow/**", ".claude/**", ".sertor/**", "tests/unit/test_assets*"]
---

# Audit di fedeltà dogfood↔client — RAG · wiki · governance (2026-07-03)

> Nato dalla domanda dell'utente dopo E10-FEAT-027 («il punto era su *tutto* Sertor — abbiamo fatto su
> tutto?»). Metodo: 3 ricognitori paralleli (una superficie ciascuno) + verifica empirica diretta.
> Deliverable azionabile: epica **[fedeltà-dogfood](../../requirements/fedelta-dogfood/epic.md)** (E15).

## Verdetto in una riga

**No, non su tutto.** E10-FEAT-027 ha reso fedele la **sola** fetta SpecKit. La fedeltà ha **due livelli** e
il dogfood copre solo (in parte) il primo:
- **Asset-fidelity** (stessi file, via `sertor_installer.sync`) — **parziale/disuniforme**;
- **Process-fidelity** (prodotto dai veri installer) — **assente ovunque**.

## La distinzione chiave

Il dogfood **non esegue mai** `sertor install rag/wiki` né `sertor-flow install`: ottiene gli asset per
**copia/sync**. Quindi esercitiamo (a volte) i *file*, **mai** il *processo* (merge di `settings.json`,
wiring per-assistente, blocchi marker in `CLAUDE.md`, idempotenza/preservazione, uninstall inverso). Quel
processo è testato **solo** su host sintetici in `tmp_path`, non contro l'albero dogfood reale.

## Stato per superficie

| Superficie | Asset-fidelity | Process-fidelity | Gap principali |
|---|---|---|---|
| **RAG** | **parziale** — il sync copre solo `assets/claude/**`, **non** `assets/rag/**`; guardia su **3 hook** soli | **assente** | Mancano nel dogfood: hook `sertor-rag-usage-check` + wiring, `guided-setup`, `concierge`, `sertor-cli-reference.md`, `.sertor-version`, blocco `SERTOR:RAG-USAGE`. Divergono: `.mcp.json` (dev venv-form vs runtime `.sertor/`), `.env` hand-authored |
| **Wiki** | **forte** — `assets/claude/**` sync + guardia byte | **assente** | Config **super-set** (dogfood *avanti* al template: `explainers`/`audit`/`strings`/`roles.vcs`/`rag`); `CLAUDE.md` prosa italiana **senza** blocco marker; wiring `settings` mergiato a mano (non guardato); `wiki/` cresciuto organicamente |
| **Governance** | **parziale** — agenti/skill sync; blocco SDLC **non** sync (a mano); costituzione curata by-design | **assente** | SpecKit via script isolato (FEAT-027); vedi correzione empirica sotto |

## Correzione empirica (decisiva)

Il report governance (e il mio stesso script/FEAT-028) **assumevano** che `specify init --force` clobberasse
la **costituzione** → falso. **Test isolato 2026-07-03:**
- `constitution.md` → **PRESERVATA** (`specify init` è *create-if-absent* anche con `--force`);
- `plan-template.md` → **CLOBBERATO** (sostituito con l'upstream; non è nel piano Sertor → nulla lo ripristina);
- `feature.json` → non toccato.

Quindi il rischio governance è **ristretto a `plan-template.md`** (il mission-gate), molto più piccolo del
temuto: un vero `sertor-flow install` **preserverebbe** la v1.4.0. **E10-FEAT-028 è stata ri-scoperta e
ristretta** di conseguenza (backup/restore del solo `plan-template.md`). *Lezione: l'assunzione stava nel
mock dei test e nel docstring del mio script — l'ha smentita solo l'esecuzione reale (essenza del progetto:
*impedire che un agente ragioni su contesto non reale*).*

## Sotto-finding trasversali (→ feature dell'epica)

1. **Sync incompleto** — copre solo `assets/claude/**`; `assets/rag/**`, `settings.hooks.json`, blocco SDLC
   fuori → drift silenzioso (FEAT-002).
2. **RAG non dogfoodato per intero** — mancano artefatti che ogni client riceve (FEAT-003).
3. **Divergenze dev↔client** — `.mcp.json`/`.env`/blocchi CLAUDE.md: da adottare o dichiarare (FEAT-004).
4. **Staleness inversa** — il `wiki.config.toml.tmpl` è **indietro** rispetto al dogfood: fedeltà può voler
   dire allineare il *template* alla realtà (FEAT-006).
5. **Nessuna process-fidelity** — serve un harness che installi in sandbox e confronti (FEAT-001, il cuore).

## Non verificato / aperto
Byte-diff completo di tutti gli asset RAG dogfood↔bundle; comportamento reale di `sertor install rag` sul
dogfood (solo ragionato, non eseguito — R-1: va fatto in sandbox); se altri template oltre `wiki.config` sono
indietro rispetto alla realtà.
