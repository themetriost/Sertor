---
title: Costituzione di Sertor
type: concept
tags: [costituzione, governance, clean-code, clean-architecture, produzione, principio-x, host-agnostico, principio-xi, principio-xii, principio-xiii, missione, fail-loud, product-fixture-plane]
created: 2026-05-31
updated: 2026-07-22
sources: [".specify/memory/constitution.md", ".specify/templates/plan-template.md", "packages/sertor-flow/src/sertor_flow/assets/constitution-starter.md"]
---

# Costituzione di Sertor

La **Costituzione di Sertor** è il documento di governance che codifica i **13 principi vincolanti** del
progetto (Clean Architecture, qualità del codice, host-agnosticità del **Principio X**, consumo via vehicles
del **Principio XI**, Fail Loud del **XII**, Product-vs-Fixture-Plane del **XIII**) sotto una **Missione &
stella polare** vincolante; un **Constitution Check** ne fa da gate al design. Fonte unica:
`.specify/memory/constitution.md`. Ratificata v1.0.0 il 2026-05-31; **corrente: v1.5.0 (2026-07-22)**.

> **Lingua (dalla v1.5.0):** la costituzione dogfood è ora **in inglese** — la stessa lingua di ciò che
> **rilasciamo** (lo starter neutro di `sertor-flow`). Prima era in italiano: una divergenza «dogfood ≠ ciò
> che rilascio» corretta applicando a noi stessi il **Principio XIII** appena ratificato. Numerazione I–XIII
> preservata (per non rompere i cross-reference). Vedi [[product-plane-vs-fixture-plane]].

## Cosa

Fonte unica dei principi vincolanti che governano design, architettura e governance di produzione di Sertor
(ogni capacità + veicoli, non solo core+CLI — vedi Principio X). Sotto questi principi operano SpecKit e gli
agenti; il **Constitution Check** è il gate al `plan`. Documento:
[`.specify/memory/constitution.md`](../../.specify/memory/constitution.md).

## Missione & stella polare (sezione, dalla v1.4.0)

Prima dei principi, la costituzione àncora la **missione**: Sertor dota qualsiasi progetto (*code+doc*,
*solo-doc*, *solo-code*) di auto-conoscenza interrogabile, portabile e senza lock-in; il **differenziatore**
è la **fusione code+doc** in un unico corpus. La **stella polare** (vincolante): ogni capacità/feature/
decisione DEVE servire la missione e rafforzare la fusione code+doc; in conflitto vince la missione. Un gate
di **allineamento alla missione** entra nel Constitution Check. Vedi [[mission-vision]].

## I 13 principi (vincolanti)

- **I. Core a dipendenze verso l'interno** (NON-NEGOZIABILE) — la libreria è il prodotto; il core non
  importa SDK provider né CLI. → REQ-E1, CS-5
- **II. Provider/backend intercambiabili dietro boundary; local-first** — scelta via config; eseguibile
  senza cloud. → REQ-E2/E4/E7, CS-7
- **III. Semplicità giustificata (YAGNI) e unità piccole** — niente astrazioni senza evidenza; SRP/DRY.
- **IV. Gestione errori esplicita; niente null silenzioso** (NON-NEGOZIABILE) — eccezioni di dominio, mai
  stato parziale. → FEAT-002 REQ-004
- **V. Testabilità e qualità provata da misure** — F.I.R.S.T.; retrieval misurato hit@k/MRR, baseline =
  prototipo. → CS-1/CS-4
- **VI. Idempotenza, determinismo, non-distruttività** — re-run stabile; install ≠ run; no overwrite
  silenzioso. → REQ-E6
- **VII. Leggibilità come comunicazione** — naming di dominio, guard clause/early return, SESE non richiesto
  (il problema è il nesting).
- **VIII. Configurabilità centralizzata del core** — tutte le scelte via config unica, nessun default
  hardcoded. → REQ-030
- **IX. Osservabilità: tutto loggato a runtime** — log strutturati su embedding/index e retrieval; nessun
  segreto. → FEAT-001 REQ-031
- **X. Capacità host-agnostiche** (NON-NEGOZIABILE, dal 2026-06-05) — ogni capacità disaccoppiata
  dall'ospite; l'ospite si configura, non si presume; il dogfooding non è licenza per violare il confine.
  → Mission, Principio I generalizzato
- **XI. Consumo attraverso i vehicles (CLI/MCP), non la libreria a runtime** (dal 2026-06-15) — i consumatori
  a runtime accedono solo via CLI/MCP, mai importando `sertor_core` (test esclusi); i vehicles cablano
  osservabilità/config/errori in modo uniforme.
- **XII. Fail Loud, Fix the Cause** (dal 2026-06-20) — si rimuove la causa, non si disattiva/silenzia per
  schivare l'errore; la degradazione è ammessa solo se **segnala**. Origine: episodio OTel (riparare il
  collector, non spegnere l'export). Vedi [[fail-loud-fix-cause]].
- **XIII. Product Plane vs. Fixture Plane** (NON-NEGOZIABILE, dal 2026-07-22) — nel dogfooding piano-prodotto
  e piano-fixture restano distinti; un buco di prodotto tappato da un workaround-fixture = **OPEN PRODUCT
  QUESTION**, mai nascosto (è il XII applicato al dogfooding). Proposto dal nodo Sinthari, accolto 2026-07-14.
  Vedi [[product-plane-vs-fixture-plane]].

## Sezioni aggiuntive nella Costituzione

- **Missione & stella polare** (v1.4.0) — vedi sopra.
- **Sicurezza, segreti e provenienza** (REQ-E5): no hardcoded secret, `.env` only, corpus pulito.
- **Governance:** branch + PR post-ratifica, Constitution Check gate in planning, semantic versioning.

## Origine

Derivata da zero (ignorando le bozze del prototipo). Fonti: i due wiki di riferimento **Clean Code** e **Clean
Architecture** (in `ExternalRepos/`) + l'allineamento ai requisiti Sertor (epiche sertor-core/cli, REQ-E*, CS,
OBJ, SC — vedi [[decomposizione-must-core]]). Sinergia centrale: «core riusabile come libreria, provider
intercambiabili via config» → Dependency Rule + Plugin Architecture; «production-grade» → disciplina Clean Code.
I principi più recenti nascono anche dalla **federazione**: il XIII è una proposta del nodo **Sinthari**.

## Perché vincola

- Vincola il **design di ogni feature** via il gate Constitution Check in `plan.md` (Phase 0 e Phase 1),
  incluso il gate **allineamento alla missione**.
- **Principi I e IV** sono gate non-negoziabili (falliscono il Check se non soddisfatti).
- Chiude i dibattiti di design su basi condivise: «questo non soddisfa il Principio X/XIII» è un argomento,
  non un'opinione.

## Versioning e emendamenti

- **v1.0.0** — 2026-05-31, ratificata (9 principi).
- **v1.1.0** — 2026-06-05, MINOR (+ Principio X — host-agnosticità).
- **v1.1.1** — 2026-06-14, PATCH (chiarimento Principio VII: nesting, non i return; SESE non richiesto).
- **v1.2.0** — 2026-06-15, MINOR (+ Principio XI — consumo via vehicles; chiude un gap di osservabilità).
- **v1.3.0** — 2026-06-20, MINOR (+ Principio XII — Fail Loud, Fix the Cause; origine episodio OTel).
- **v1.4.0** — 2026-06-20, MINOR (+ sezione **Missione & stella polare** + gate di allineamento alla missione).
- **v1.5.0** — 2026-07-22, MINOR (+ Principio XIII — Product Plane vs. Fixture Plane, proposta Sinthari; **+
  convergenza in inglese** dell'intera costituzione dogfood per fedeltà a ciò che rilasciamo — E10-FEAT-030).

## Riferimenti

- **Fonte unica:** [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) (v1.5.0, EN)
- **Starter neutro rilasciato:** `packages/sertor-flow/.../constitution-starter.md` (v0.4.0 — vi il XIII è il
  Principio XII, dove l'XI è Fail Loud).
- **Template planning:** [`.specify/templates/plan-template.md`](../../.specify/templates/plan-template.md)
  (Constitution Check con gate I–XIII + allineamento alla missione).
- [[product-plane-vs-fixture-plane]] · [[fail-loud-fix-cause]] · [[mission-vision]] · [[dogfood-fidelity]] ·
  [[decomposizione-must-core]]
