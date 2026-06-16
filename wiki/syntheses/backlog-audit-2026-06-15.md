---
title: Backlog audit (2026-06-15) — censimento di tutto il non-fatto
type: synthesis
tags: [backlog, audit, roadmap, planning, todo, censimento]
created: 2026-06-15
updated: 2026-06-15
sources: ["requirements/**/epic.md", "requirements/**/requirements.md", "specs/*/spec.md", "specs/*/research.md", "wiki/syntheses/roadmap.md", "wiki/log/*.md", "memoria episodica (sertor-rag memory)"]
---

# Backlog audit — censimento di tutto il "citato ma non fatto" (2026-06-15)

> **Scopo:** base per **rifare la roadmap**. Censimento profondo, deduplicato, di OGNI feature/opzione/idea
> citata e **non ancora realizzata**, da epiche · requirements di feature · spec/research SpecKit · roadmap ·
> idee wiki · log · memoria episodica (interrogata via vehicle, nessun errore MCP). Gli obsoleti sono
> marcati ⛔. ~~**Prossimo passo (sessione successiva): costruire la nuova roadmap da qui.**~~
>
> ✅ **ESEGUITO (2026-06-16):** l'audit è stato convertito in **6 nuove epiche** (`retrieval-qualita`,
> `backend-store-scala`, `ingestione-estesa`, `conoscenza-schema-sql`, `second-brain`, `debito-tecnico`)
> e i leak minori (§6) promossi nelle epiche esistenti (`sertor-core`/`sertor-cli`/`osservabilita`/
> `memoria-conversazioni`). La [[roadmap]] (EXEC table + PLANNED) riflette ora questa struttura.

Metodo: 4 agenti paralleli (epiche · out-of-scope spec+requirements · roadmap+idee wiki · log+memoria),
sintesi nel flusso principale. Le ~40 domande di pura ingegneria interna a feature già consegnate
(schema store, framework TUI, refresh rate, forma API report) sono escluse: non sono capacità future.

## 1. Capacità con casa durevole (backlog d'epica)

### `sertor-core`
- **FEAT-008** Arricchimento bidirezionale Wiki↔RAG — Could · da decomporre
- **FEAT-009** Refresh incrementale dell'indice (solo file cambiati) — Could · mitigata operativamente, non risolta
- **FEAT-010** Ingestione estesa: repo remoti via URL + formati non-testo (PDF/DOCX/notebook) — Could
- **FEAT-006** Agenzia RAG **incorporata** (`sertor-rag ask`, porta `LLMProvider`, digest MCP) — Could, dote differita (36 REQ in `requirements/sertor-core/motore-agentico/`); agentic RAG composito ✅

### `sertor-cli`
- **FEAT-001** Packaging del pacchetto `sertor` (distribuzione) — Must · rinviato
- **FEAT-003** Wizard di configurazione interattivo (provider LLM + vector DB) — Should · rinviato
- **FEAT-008** Ciclo di vita installer: `upgrade` + `uninstall` — Could
- **FEAT-006** Pubblicazione su **PyPI** + hardening supply-chain — Won't (per ora)

### `osservabilita` (oltre l'MVP F1–F4 consegnato)
- **FEAT-005** Export **OpenTelemetry** (extra `[otel]`; assorbe H9) — Should
- **FEAT-006** Metriche aggregate (p95/p99, cache-hit, throughput; assorbe H10) — Should
- **FEAT-007** **Stima costi in €** — Should *(confermato NON consegnato)*
- **FEAT-008** Web mode (dashboard browser) — Could
- **FEAT-009** Trend qualità retrieval (`low_confidence`/query a vuoto/score) — Could
- **FEAT-010** Metriche code-graph & wiki — Could

### `memoria-conversazioni` (oltre l'MVP)
- **FEAT-004** Ricerca **semantica** opt-in (embedding transcript) — Should
- **FEAT-005** Cattura selettiva "remember this" — Could
- **FEAT-006** Governance/retention (gancio `RETENTION_DAYS` non agganciato) — Could
- **FEAT-007** Ponte verso il second-brain — Could
- **FEAT-008** Cattura multi-assistente (oltre Claude Code) — Could
- **FEAT-009** **Distribuzione memoria via installer** (manopole `.env`, hook `memory-capture.ps1`+SessionEnd, claude-md-block) — **Must/debito di completamento**

### `multiutente` (epica aperta, differita)
- **M01** ownership + mono/team (Must) · **M02** collab. RAG (Should) · **M03** collab. Wiki (Should) · **M04** quando/come condividere (Should) · **M05** segreti/config per-utente (Must) · **M06** governance leggera ruoli (Could) · + **7 domande aperte** DA-M-a…g

## 2. Hardening produzione — Could residui
- **REQ-H7** Query transformation (multi-query/HyDE) · **REQ-H8** filtro metadata esteso · **REQ-H11** contextual retrieval (Anthropic) — Could
- H9 (tracing/OTel) e H10 (metriche aggregate) → **ricollocati** in osservabilità FEAT-005/006

## 3. Idee / visione (roadmap "🧭 da discutere")
- **Second-brain cross-progetto / Meta-Sertor** — 💡 da espandere ([[second-brain-cross-progetto]]); bivi: solo-io vs team, meta-corpus vs fan-out, meta-grafo, nome
- **Conoscenza-schema SQL come corpus** — 💡 ricerca fatta ([[conoscenza-schema-sql-rag]]), scope da decidere; 4 domande di design aperte
- **Adapter VectorStore PGVector / MongoDB su Azure** — 💡 idea
- **Promuovere PowerShell / T-SQL / PL-SQL (+ Bash) a chunking sintattico** — 💡 idea (oggi fallback, R-N2)
- **Misurare la pertinenza / chiudere xfail con ground-truth** + **eval comparativa live** (REQ-051, `cloud`) — 🗣️
- **Migliorare qualità `search_code`** su query architetturali — 🗣️
- **Timeout espliciti su embed/query** — 💡 ridimensionata (hang risolto PR #23)

## 4. Questioni aperte trasversali
- **Licenza di Sertor** (MIT/Apache vs copyleft) — pre-requisito a PyPI · DA APRIRE
- **Soglie di pertinenza** non fissate — da misurare su ground-truth

## 5. Multi-assistente — residui (Copilot ✅ FEAT-007+009)
- **Codex** (AGENTS.md + MCP; SpecKit `--ai codex`) — Could, to-do esplicito (roadmap PLANNED)
- **Client Copilot ≠ VS Code agent mode** (coding agent cloud, altri IDE) — Won't per ora
- **Multi-target install** (Claude + Copilot in un colpo) — non-MVP

## 6. ⚠️ Leak SENZA casa durevole — *da promuovere* (regola out-of-scope)
Capacità reali citate **solo** dentro spec/research, mai promosse a FEAT/roadmap — il materiale più a rischio di perdersi:
- **MCP**: trasporti non-stdio (HTTP/SSE) + auth di rete; tool **health/status** (corpus+indice)
- **Retrieval**: indici **multi-provider in parallelo**; query su **>2 corpora** / fan-out a N collezioni; `search_docs` esteso al wiki + **dedup cross-collezione v2**
- **Wiki**: **no-code-first** (progetti senza codice); **gerarchia di autorità configurabile** nel ranking (FR-014)
- **Enforcement Principio XI**: **FR-007** restringere export `__init__`; hook modalità **"block"** (oggi warn) — solo in `specs/041`/`042`
- **install-rag**: fallback **`pip`** (oltre `uv`); **avviso target non-Python**
- **Hook Linux** (sh/Python) per ospiti senza PowerShell — ricorre in più spec
- **Osservabilità minori**: export report **CSV/MD**; bucket **"hour"**; **eviction cache** sofisticata (019)
- **Code-graph**: limite scala **~50k nodi** (in-memory); profondità archi per-linguaggio non-Python
- **CI**: **test Linux nativo** (debito, rag-baseline DA-2)
- **Reviewer "clean-code" attivo** — ricorre 3× (governance req+spec, memory) senza FEAT/roadmap
- **Parità MCP per `memory show`/`list`** · **GraphRAG "alla Microsoft"** (knowledge-graph LLM) — citati in roadmap, non promossi a FEAT

## 7. Debiti di wiki / governance / infra
- **Refactor host-agnostico** di skill wiki / playbook / rituale (oggi Sertor-coupled)
- **Riesportare il rituale come plugin portabile** repo-agnostico (parz. assorbito da [[sertor-flow]])
- **Hub/overview per-area** del wiki · **tassonomia più fine** · **distill pagina osservabilità** · ripasso [[tree-sitter-language-pack]] (pagina gonfia) · override **seed `[strings]`** · **trigger periodico `reconcile`** (oggi solo doc)
- **Selettività bundle `sertor-flow`** (vs all-or-nothing) · hook harness governance (DA-g)
- **Unificare i due venv** `.venv`/`.venv-core` (footgun divergenza)

## 8. ⛔ Obsoleti / superati
- ⛔ **Probe deterministici di freschezza** wiki (FR-036) — Won't (D1)
- ⛔ **Esclusione `wiki/` dal corpus** (`SERTOR_EXCLUDE_PATTERNS`) — superata da **corpus unico** (D-21)
- ⛔ **FR-026/027/028** (generazione `/wiki` automatica al commit) + **FR-041/042** (gate bloccante) + cartelle `manual_edited/`/`ingested_sources/` (D-18/19/20)
- ⛔ **`upsert_index`** (out-of-scope meccanica-log) — consegnato in feature 010
- ⛔ **Indicizzazione wiki in corpus dedicato** — superata da corpus unico
- ⛔ **Fallback `--source`** installer (REQ-116/117) — superato da package-data
- ⛔ **Localizzazione asset** manutenzione-wiki (D4) + **probe gruppo A** (Won't)
- ◐ **"Logging come strategia runtime"** — largamente assorbita dall'epica osservabilità; refactor porta+adapter as-such non fatto
- ◐ **Tema lingua asset installer** — risolto da `tema-lingua-runtime`; residuo = traduzione graduale error-string/docstring profonde

## 9. 🔧 Igiene (non feature): disallineamenti epica↔realtà da riconciliare
Domande marcate "DA CHIARIRE" nelle epiche ma **già risolte** in design dai plan: **DA-O-c, DA-O-f**
(osservabilità), **DA-M-a, DA-M-b** (memoria). Aggiornare le epiche.

---

## Come usare questo audit (domani)
1. Decidere i **temi/fasi** della nuova roadmap (es. retrieval avanzato · osservabilità 2 · memoria 2 · distribuzione/PyPI · multiutente · second-brain).
2. **Promuovere i leak della §6** alle loro case (righe FEAT nei backlog d'epica / voci roadmap).
3. Riprioritizzare MoSCoW alla luce di ciò che è ✅ (Copilot, Principio XI, MVP memoria/osservabilità).
4. Riconciliare i disallineamenti della §9.
5. Rigenerare il blocco EXEC + la mappa-feature di [[roadmap]] coerenti con l'esito.
