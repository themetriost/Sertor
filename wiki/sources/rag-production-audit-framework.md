---
title: RAG Production Audit Framework
type: source
tags: [rag, audit, production-readiness, evaluation, reference-framework]
created: 2026-06-20
updated: 2026-06-20
sources: ["freeCodeCamp Production RAG with LangChain & Vector Databases (Paulo Dichone)", "https://www.freecodecamp.org/"]
---

# RAG Production Audit Framework

**A comprehensive audit framework for evaluating Retrieval-Augmented Generation (RAG) systems against production best practices**, derived from the freeCodeCamp course *Production RAG with LangChain & Vector Databases* (Paulo Dichone). Provides a scored rubric spanning foundation (pillar A–I), stringent gates (hard gates HG-1…HG-8), advanced rigor (J–N), and a fixed-format report with four readiness tiers.

## Purpose and scope

The framework asserts that **most RAG projects fail in production, not in the demo**, because retrieval quality, grounding, observability, cost, security, and reliability were never engineered. The audit targets the **behavior** of a system (not the imports), making it **stack-agnostic**: it applies equally to LangChain, LlamaIndex, Haystack, raw vector-DB clients, or custom pipelines.

## The rubric: pillars A–I (foundation) and J–N (advanced rigor)

### Baseline pillars (A–I)

**A. Indexing & ingestion pipeline**
- Loaders preserve source + metadata (A1)
- Chunking strategy is deliberate, not default (A2)
- Chunk size matched to retrieval need (A3)
- Embedding model is conscious choice + consistent (A4)
- Embedding cost controlled via batching & caching (A5)
- Vector store fits the production stage (A6)

**B. Retrieval quality**
- Similarity scores are used, not discarded (B1)
- Hybrid search (BM25 + semantic) where corpus needs it (B2)
- Query transformation for recall (B3)
- Context focused, not dumped (B4)
- Reranking for precision (B5)
- Metadata filtering available (B6)

**C. Generation & grounding**
- Answer strictly from context (C1)
- Explicit fallback / abstention (C2)
- Sources / citations surfaced (C3)
- Structured output where downstream consumes it (C4)
- Low temperature for factual RAG (C5)

**D. Observability** — three pillars
- Tracing on every LLM/chain/retrieval call (D1)
- Structured (JSON) logging (D2)
- Metrics collected (D3)
- Evaluation set exists (D4)

**E. Cost control**
- Model routing (cheap for simple, expensive only when needed) (E1)
- Response / semantic caching (E2)
- Token budgeting (E3)
- Vector-search cost is understood (E4)

**F. Reliability & error handling**
- Retries with backoff + jitter (F1)
- Circuit breaker / graceful degradation (F2)
- Timeouts and fallbacks (F3)

**G. Security** (baseline)
- Input sanitization / prompt-injection screening (G1)
- PII detection & masking (G2)
- Output validation / guardrails (G3)
- Defense-in-depth pipeline (G4)
- Secrets & endpoint hygiene (G5)

**H. Deployment & serving**
- Real API/service boundary (not a script) (H1)
- Stateful orchestration where needed (H2)
- Production-grade persistence (H3)
- Config/secrets externalized & environment-aware (H4)

**I. Advanced techniques** (maturity, not table stakes)
- Long-context vs RAG considered (I1)
- Contextual Retrieval / chunk context (I2)
- Late vs early chunking (I3)
- Agentic / self-correcting RAG (I4)
- GraphRAG / multi-hop (I5)
- Multimodal RAG (I6)

### Advanced rigor pillars (J–N)

**J. Evaluation & continuous quality** — *the single biggest divider between serious and toy RAG*
- Component-level eval (retrieval scored separately from generation) (J1)
- Faithfulness & relevance metrics with human-labeled subset (J2)
- Golden regression set in CI (blocks merge/deploy on regression) (J3)
- Negative & adversarial suite (injection/jailbreak/hard cases) (J4)
- Online evaluation loop (production signals fed back) (J5)

**K. Faithfulness verification at inference**
- Runtime groundedness check (each answer verified against context) (K1)
- Citation correctness (cited spans actually support the claim) (K2)
- Calibrated abstention threshold (tuned vs eval set) (K3)

**L. Data lifecycle & governance**
- Freshness / re-index strategy (incremental, not stale-forever or full-rebuild-every-run) (L1)
- Deletion & update propagation (purges vectors + cached answers) (L2)
- Embedding-model & dimension versioning (no silent corruption) (L3)
- Deduplication (collapse near-dupes) (L4)
- Provenance & lineage (each chunk traces to document and source version) (L5)

**M. Security** (the hard ones)
- Authorization-aware retrieval (per-user/per-tenant ACLs mirroring source system) (M1)
- Indirect prompt-injection defense (corpus treated as untrusted) (M2)
- Denial-of-wallet protection (per-user token & spend quotas) (M3)
- PII-safe observability (traces/logs don't persist raw PII/secrets) (M4)
- Least-privilege secrets, rotation & encryption at rest (M5)

**N. Performance, SLOs & change management**
- Latency budget & SLOs (end-to-end decomposed with p95/p99 targets) (N1)
- Vector index tuned (ANN parameters set for recall/latency tradeoff) (N2)
- Streaming & connection management (responses stream, client pooling/backpressure) (N3)
- Prompt & model versioning + reproducibility (pinned, prompt regression tests, pinned dependencies) (N4)

## Hard gates (HG-1…HG-8)

Eight non-negotiable conditions: **failing one caps overall readiness at Prototype**, regardless of score. They back [[retrieval-confidence|grounding]], parity, resilience, security, data governance, and runtime verification:

| Gate | Condition | Applies when |
|------|-----------|---|
| **HG-1** | Grounded + abstention (C1+C2) | Always |
| **HG-2** | Index/query embedding parity (A4) | Always |
| **HG-3** | Request-path resilience (F1+F3) | System is served |
| **HG-4** | Secrets & endpoint hygiene (G5) | Always |
| **HG-5** | Authorization-aware retrieval (M1) | Multi-user or multi-tenant |
| **HG-6** | Untrusted-corpus injection defense (M2) | Corpus includes external/user-supplied content |
| **HG-7** | Deletion propagation (L2) | Personal/regulated data is indexed |
| **HG-8** | Runtime groundedness (K1) | High-stakes domains (medical, legal, financial) |

## Readiness tiers

Assigned by **worst binding constraint**, not average:

- **Prototype** — works in a demo; one or more applicable gates fail, or core grounding/retrieval quality is missing.
- **Pre-production** — all gates pass; baseline pillars A–H largely hold; evaluation (J) and/or observability (D) are thin.
- **Production-ready** — gates pass; A–H solid; real evaluation (J) and observability (D) in place; applicable security gates (G + M) pass.
- **Hardened** — production-ready **plus** advanced rigor pillars (J–N) substantially in place (continuous quality, runtime faithfulness, data lifecycle, hard security, performance/SLOs).

## Audit workflow

1. **Map the pipeline.** Locate the four stages: indexing, retrieval, generation, serving.
2. **Read configs and constants.** `chunk_size`, embedding model, `k`, temperature, etc. — these reveal most issues fast.
3. **Trace one query end-to-end** from API boundary to answer.
4. **Evaluate hard gates first** (before tallying scores); one fail caps verdict at Prototype.
5. **Score each pillar A–N** using the rubric: status, evidence (file:line or quote), fix.
6. **Synthesize** into the exact report structure.

## Report structure (fixed format)

A structured report with five sections:

1. **Verdict** — 2–4 sentences: overall readiness, stage/intent, single most important fix.
2. **Gate status** — table of HG-1…HG-8 (pass/FAIL/n/a + evidence).
3. **Scorecard** — table: pillar × score (x/max) × one-line state.
4. **Critical issues** — ordered list (problem, evidence, impact, fix).
5. **High/Medium findings**, **Quick wins**, **Strengths**, **Recommended next steps**.

Evidence must be concrete (file:line, short quote); prefer decisive findings over exhaustive nitpick lists.

## Relevance to Sertor

The framework **validates and extends** several architectural choices already made in [[retrieval-core]] and the [[roadmap]]:

- **Embedding parity (HG-2, A4):** Sertor enforces via collection namespacing `(corpus, provider)` and `store_backend` disaccouplment (FEAT-009), permitting heterogeneous embedders without confusion.
- **Grounding + abstention (HG-1, C1+C2):** The [[retrieval-confidence]] mechanism (SERTOR_MIN_SCORE) supplies confidence signals for the model to abstain; core does not enforce prompt-wording (that is the consumer's responsibility).
- **Evaluation (J, esp. J1 + J3):** [[valutazione-e-non-regressione]] implements J1/J3 explicitly — component-level hit-rate@k/MRR and a golden regression set in CI (`eval/suite.toml`, FEAT-001).
- **Observability (D):** The [[il-pannello-di-controllo|observability stack]] (FEAT-020 F1, FEAT-021 F2, FEAT-022 F3, FEAT-023 F4) addresses D1–D4; traces + structured logging + metrics + evaluation set.
- **Data lifecycle (L1, L2):** Manifest-based refresh (FEAT-009) addresses L1 (incremental); deletion propagation (L2) is flagged as a gate requirement for the roadmap.
- **Code-graph navigation (B3, I5):** [[code-graph]] (FEAT-005) complements hybrid retrieval for query transformation and multi-hop reasoning (GraphRAG pattern).
- **Advanced rigor (J–N):** Most of pillars K–N remain future capacity (FEAT candidates in roadmap), with J in progress.

**Gaps flagged by the framework as production requirements but not yet closed:**

- **K, M1, M5, N:** Runtime faithfulness verification, authorization-aware retrieval (multi-tenant), secret rotation, latency SLOs — tracked in roadmap as Future/Could.
- **E1, E2:** Model routing and semantic caching — not in current scope.

The framework serves as **external validation** that Sertor's architecture and roadmap are aligned with production best practices.

## See also

- [[valutazione-e-non-regressione]] — Sertor's implementation of component-level eval + regression gates (pillars J).
- [[retrieval-confidence]] — Confidence signal for model abstention (pillar C + HG-1).
- [[il-pannello-di-controllo]] — Observability stack (pillar D).
- [[code-graph]] — Query transformation via AST navigation (pillar B3, I5).
- [[roadmap]] — Map of which pillars/gates are in scope, done, or future.
