---
title: Osservabilità (subsystem)
type: concept
tags: [osservabilita, observability, logging, opentelemetry, otel, genai-semconv, privacy, telemetria, e-osservabilita]
created: 2026-07-21
updated: 2026-07-21
sources: ["requirements/osservabilita/epic.md", "src/sertor_core/observability/logging.py", "src/sertor_core/observability/capture.py", "src/sertor_core/observability/otel.py", "src/sertor_core/composition.py", "wiki/log/2026-06-19.md", "wiki/log/2026-06-20.md"]
---

# Osservabilità (subsystem)

Sertor deve poter **dimostrare** il proprio funzionamento, non solo eseguirlo. La domanda che
l'osservabilità rende rispondibile è quella che la [[mission-vision]] mette al centro del valore reso
all'agente — *quanto è buono, quanto costa, quanto è fresco il retrieval?* — e che senza uno strato
dedicato resta senza risposta. Il core **già** emette log strutturati ricchi a ogni operazione via
`log_event` (`observability/logging.py`): `index`, `embeddings` (token), `embeddings_cache`
(hit/miss), `low_confidence`, gli eventi di ricerca/rerank. Ma quei log sono **effimeri**: vanno su
stderr e si perdono a fine comando. Il subsystem di osservabilità dà a quegli eventi un **luogo dove
restano**, una **superficie dove si vedono** e un **ponte verso lo stack enterprise** — senza toccare
i call-site che li producono.

## L'architettura in un colpo d'occhio: sink additivi sullo stesso evento

Il principio di design che tiene insieme tutto il subsystem: **`log_event` è la sorgente unica**, e
ogni consumatore è un `logging.Handler` **additivo** agganciato al logger `sertor_core`. Aggiungere una
capacità di osservabilità = aggiungere un sink, mai cambiare la firma di `log_event` né i punti che lo
chiamano (Principio I/IV, additività non-breaking). I sink oggi sono due, gemelli per costruzione:

- **F1 — persistenza (`EventPersistenceHandler`, `capture.py`)**: intercetta gli eventi e li scrive in
  uno **store locale interrogabile** (gitignored, rigenerabile). È la *memoria* senza cui non esistono
  report storici; sopra vive l'aggregazione (F2) e il pannello **TUI** (F3/F4), un *thin consumer* che
  mostra live lo stato del RAG (ultimo index, #doc/#chunk, cache, costo, eventi recenti) e ne fa report.
- **OTel export (`OtelExportHandler`, `otel.py`, FEAT-005)**: mappa ogni evento a uno **span
  OpenTelemetry** e lo spedisce a un backend esterno (Langfuse/Phoenix/Grafana/Jaeger), **in aggiunta**
  allo store, mai al suo posto (REQ-E4).

Entrambi ereditano gratis dal framework di logging le tre proprietà che rendono l'osservabilità sicura:
**additiva** (call-site invariati), **non-fatale** (un'eccezione del handler va a `Handler.handleError`,
mai al chiamante — un guasto dell'export non può far fallire un index/una search), **privacy-safe**
(`log_event` mette sul record campi già redatti).

## Il seam: `enable_observability` al confine dei vehicles

Tutti i sink si attaccano in **un solo punto**: `enable_observability(settings)` in `composition.py`.
Legge `Settings`, aggancia `EventPersistenceHandler` se `observability_enabled`, e
`OtelExportHandler` se `observability_otel_enabled` (che richiede l'extra `[otel]`; assente+richiesto →
`ConfigError` azionabile, non silenzioso). È **idempotente**: non duplica un handler già presente.

Questo è il legame diretto col **Principio XI** (accesso solo via vehicles): la CLI e il server MCP
chiamano `enable_observability` **per te**, cablando l'osservabilità come cross-cutting concern. Chi
importasse `sertor_core` a mano — `build_indexer().index(...)` — **bypasserebbe silenziosamente** il
seam, e l'operazione non finirebbe in telemetria (caso reale già osservato). L'osservabilità è quindi
una delle ragioni concrete per cui i vehicles esistono: sono l'unico posto dove i concern trasversali si
attaccano una volta per tutte.

## L'export OTel in dettaglio: GenAI semconv, metrics-only, opt-in

L'export è la fetta più **auto-contenuta** del subsystem e vale spiegarla per intero, perché incarna la
sua postura sui dati.

- **GenAI semantic conventions.** La mappa evento→span è centralizzata in `otel.py` (fonte unica,
  facile da aggiornare quando le convenzioni evolvono): `provider→gen_ai.provider.name`,
  `tokens→gen_ai.usage.input_tokens`, `model→gen_ai.request.model`, `dim→gen_ai.embeddings.dimension.count`;
  le operazioni di ricerca (`search`/`retrieve`/`query`/`hybrid_query`) mappano a
  `gen_ai.operation.name=retrieval`. Gli eventi senza convenzione GenAI ottengono uno span nel namespace
  `sertor.*`. Il retrieval osservato è quello dell'[[hybrid-retrieval]], l'operazione `hybrid_query`.
- **Privacy metrics-only (la postura sui dati).** Oltre alla redazione che `log_event` fa a monte,
  l'handler esporta **solo** campi numerici/bool + una **whitelist** di stringhe categoriche sicure
  (`provider`, `backend`, `model`, `engine`, `store`, `corpus`, `reason`, `kind`); **qualsiasi altra
  stringa viene scartata** — testo delle query, snippet, path non raggiungono **mai** il backend. È la
  stessa privacy-by-default a strati dell'epica (REQ-E8): di default si persistono/esportano solo
  metriche; il testo grezzo è un opt-in esplicito e locale (la scheda "RAG" della TUI, FEAT-015),
  l'export resta metrics-only.
- **Opt-in a impatto nullo.** Manopola `SERTOR_OBSERVABILITY_OTEL` (default off) + extra `[otel]`: le
  dipendenze OTel sono lazy, il core resta importabile senza (0 `opentelemetry` in `sys.modules`).
  Endpoint/trasporto dalle env standard `OTEL_EXPORTER_OTLP_*`. Non-bloccante (BatchSpanProcessor). Con
  l'export spento **nulla cambia** (REQ-E3/CS-7).
- **Esito e severità nel backend (FEAT-013).** Polish additivo emerso dal dogfooding su Jaeger — si
  vedeva l'*operazione* ma non l'*esito*: ora lo **span status** deriva dal livello del log (un evento
  ERROR → span rosso con reason), ogni span porta `sertor.level`, e il `service.name=sertor` di default
  evita `unknown_service`.

**Limite dichiarato (onesto):** span **flat/post-hoc**, uno per evento — niente tracing nidificato con
context propagation (follow-up). Estensione pianificata (FEAT-016): espandere il dict `hit_rate` in tag
scalari `sertor.hit_rate.<k>`, oggi scartato perché non scalare, così l'IR è completo in Jaeger.

## L'osservabilità come applicazione del "Fail Loud"

Non è un caso che il **Principio XII «Fail Loud, Fix the Cause»** (costituzione v1.3.0) sia nato proprio
da un **episodio OTel**: il dogfood aveva l'export acceso verso `localhost:4318` senza collector →
«connection refused» a ogni comando (OTLP è HTTP/TCP: senza listener il send non parte). La cura non fu
disattivare l'export ma **riparare la causa** — riavviare il collector Jaeger. Il subsystem incarna la
regola che ha generato: rendere visibile ciò che accade è esattamente ciò che impedisce ai guasti di
marcire invisibili. Ed è *early feedback* reso strumento: la telemetria è il posto dove costo, freschezza
e qualità del retrieval smettono di essere invisibili sia all'operatore sia (indirettamente) all'agente.

## Stato (epica `osservabilita`)

| Fetta | Stato |
|---|---|
| **F1** strato di osservabilità persistente nel core (`EventPersistenceHandler`) | ✅ (PR #34) |
| **F2** servizio di aggregazione/report | ✅ (PR #35) |
| **F3/F4** pannello TUI — vista live + report sfogliabili | ✅ (PR #36/#38) |
| **FEAT-014/015** TUI: eventi in tabella · visibilità RAG (opt-in raw-text, scheda "RAG") | ✅ (feature 063/064) |
| **FEAT-005** export OpenTelemetry (GenAI semconv, metrics-only, `[otel]`) | ✅ (feature 061) |
| **FEAT-013** arricchimento span OTel (status/severità/service.name) | ✅ (feature 062) |
| **FEAT-006** metriche aggregate · **FEAT-007** stima costi € · **FEAT-016** eval in TUI+OTel | da decomporre |

## Vedi anche
- Il valore reso all'agente (confidenza/freschezza) che l'osservabilità rende misurabile: [[mission-vision]].
- Il retrieval osservato negli span: [[hybrid-retrieval]].
- Il seam dei vehicles che aggancia i sink: Principio XI (accesso solo via vehicles).
- L'epica completa (backlog F1–F16, criteri di successo, privacy a strati): `requirements/osservabilita/epic.md`.
