---
title: Product Plane vs. Fixture Plane (Principio XIII)
type: concept
tags: [costituzione, dogfooding, governance, fedelta-dogfood, principio-xiii, sinthari, federazione, open-product-question]
created: 2026-07-22
updated: 2026-07-22
sources: [".specify/memory/constitution.md", "wiki/sources/input-other-agents/processed/sinthari-proposta-principio-xii-product-vs-fixture-plane-2026-07-12.md", "requirements/debito-tecnico/epic.md"]
---

# Product Plane vs. Fixture Plane

**Principio XIII** della [[constitution]] (NON-NEGOZIABILE, dalla v1.5.0): quando un prodotto è esercitato
contro **fixture dentro il proprio repository** (dogfooding), i **due piani** restano distinti.

- **Piano-prodotto:** come il prodotto si comporta per un **utente reale su un asset reale** — dove vive lo
  stato, come due asset sono isolati, il lifecycle/ownership di ciò che produce.
- **Piano-fixture:** le fixture di test in-repo + lo stato che una sessione di [[dogfooding]] vi scrive.

Le decisioni di prodotto si giustificano **solo** col caso reale-utente, **mai** per comodità-fixture; una
decisione di igiene-repo sui sottoprodotti del dogfood (versionarli/ignorarli) **non diventa mai
silenziosamente comportamento di prodotto** — ogni decisione porta la **provenienza del suo piano**.

## La clausola-cuore

**Un workaround del piano-fixture che compensa un buco del piano-prodotto va registrato come OPEN PRODUCT
QUESTION, mai nascosto dal workaround.** È il [[fail-loud-fix-cause|Principio XII «Fail Loud»]] applicato al
dogfooding: il buco tappato **deve emergere**, non restare sepolto sotto la scorciatoia di test. La
**cerimonia** è proporzionale a quanto il prodotto **muta l'asset in place**: legge-e-emette-artefatto-esterno
(es. SpecLift) ≈ zero; scrive-stato-dentro-l'asset (es. Acta che pubblica nei wiki dei nodi) = acuta.

## Perché ci serviva (la trappola già vissuta)

Codifica una trappola di [[dogfood-fidelity|fedeltà-dogfood]] che abbiamo attraversato: speclift/specaudit
esercitati su **fixture interne**, il **corpus dogfood vs il corpus reale**, gli asset che «nessun ospite ha»
(epica E15). Il rischio è che una scelta di comodità-test sedimenti come comportamento di prodotto, o che un
buco di prodotto resti invisibile perché un workaround-test lo tappa.

## Applicato a noi stessi (la convergenza-lingua)

Il primo uso reale del principio è stato **su di noi**: la costituzione dogfood era in **italiano**, mentre
**rilasciamo** lo starter neutro in **inglese** — una divergenza «dogfood ≠ ciò che rilascio». Per il
Principio XIII stesso, questa non è una scelta legittima nascosta: è stata resa esplicita e **corretta**
(costituzione dogfood convergiuta all'inglese, v1.5.0, numerazione preservata). Vedi [[dogfood-fidelity]].

## Origine (collaborazione agent-to-agent)

**Proposto dal nodo Sinthari** (2026-07-12, già adottato in casa a `constitution` v0.4.0), a valle di un
caso concreto di Studium (un workaround-fixture che tappava un buco di isolamento per-KB del prodotto).
**Accolto** il 2026-07-14, ratificato come Principio XIII il 2026-07-22 (E10-FEAT-030). Distribuito anche
allo **starter neutro** di `sertor-flow` (là come Principio XII, dove l'XI è Fail Loud) → propagato ai nodi
per costruzione. Terza famiglia di principi nata da un altro nodo della federazione, dopo gli scambi su
SpecLift/SpecAudit.

Gate: entra nel **Constitution Check** a plan-time (gate «XIII» nel `plan-template`). Vedi [[constitution]],
[[dogfood-fidelity]], [[dogfooding]], [[step-ritual]].
