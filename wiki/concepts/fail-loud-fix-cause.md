---
title: Fail Loud, Fix the Cause (Principio XII)
type: concept
tags: [costituzione, principio-xii, governance, osservabilita, errori, anti-skip, dogfooding, fail-loud]
created: 2026-07-22
updated: 2026-07-22
sources: [".specify/memory/constitution.md", "wiki/log/2026-06-20.md"]
---

# Fail Loud, Fix the Cause

**Principio XII** della [[constitution]] (dal 2026-06-20, v1.3.0): quando una capacità fallisce, si **rimuove
la causa** — MUST NOT disattivare, azzittire o aggirare la capacità solo per **far sparire l'errore**.

- **Il feedback precoce e visibile è un valore, non rumore:** i fallimenti MUST **emergere presto**.
- **Degradazione graziosa ammessa solo se SEGNALA** (warning/finding). La **soppressione silenziosa è
  vietata**, così come spegnere una funzione per non affrontarne l'errore.
- Rimuovere/disabilitare una capacità è legittimo **solo come decisione esplicita e tracciata**, mai come
  riflesso per schivare un errore.

## Perché

Un errore visto presto costa meno; spegnere la funzione che erra **distrugge il segnale** e sposta il difetto
più a valle. Non contraddice il [[constitution|Principio IV]] (errori espliciti) né la *policy errori voluta*
(core tollerante con warning ↔ motore baseline strict): la degradazione che **segnala** è conforme; ciò che il
principio vieta è il **silenzio** o il **disattivare per non vedere**.

## Origine

Episodio **OTel** (2026-06-20): l'export di telemetria falliva perché il collector non c'era; la mossa
corretta fu **riparare il collector**, non spegnere l'export. Generalizza a ogni capacità e veicolo la regola
standing **«errori = segnale, non rumore»** — nata nel dogfooding dell'MCP (un tool `mcp__sertor-rag__*` che
erra è un *finding*, non rumore da seppellire ripiegando su `Read`/`Grep`).

## Dove si manifesta (rete di attuazioni)

Il Principio XII è la spina dorsale di una famiglia di meccanismi che rendono *impossibile* nascondere un
difetto:
- **Errori MCP = finding** (regola standing MCP-first): un tool RAG che erra si segnala, non si degrada in
  silenzio. Vedi [[mcp-server]].
- **Breadcrumb fail-loud negli hook** (E10-FEAT-019): gli hook host-facing scrivono `.sertor/.last-hook-error`
  invece di fallire muti.
- **Anti-skip del rituale wiki** ([[ritual-check]] FEAT-026, [[daily-distill-floor]] FEAT-039): distill/lint
  non si saltano in silenzio — il pavimento del distill è Fail Loud applicato al *processo*.
- **[[product-plane-vs-fixture-plane|Principio XIII]]**: è **Fail Loud applicato al dogfooding** — un buco di
  prodotto tappato da un workaround-fixture va registrato come OPEN PRODUCT QUESTION, non nascosto.

Gate: entra nel **Constitution Check** a plan-time. Vedi [[constitution]], [[step-ritual]].
