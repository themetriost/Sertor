# Requisiti — Motore RAG ibrido + reranking
<!-- Deriva da: FEAT-004 (backlog epica sertor-core) -->
<!-- Stato: elicitato — 2026-06-11 -->

## 1. Contesto e problema (perché)

Il motore RAG attuale (`BaselineEngine`, `src/sertor_core/engines/baseline.py`) esegue
**solo retrieval per similarità vettoriale**: trasforma la query in un embedding e recupera
i k chunk più vicini nello spazio vettoriale. Questa strategia ha una debolezza osservata
direttamente nel dogfooding quotidiano (utilizzo del server MCP `sertor-rag` su
`src/sertor_core/`): `search_code` produce risultati deboli sulle **query lessicali** —
nomi esatti di simboli (es. `EmbeddingProvider`, `IndexNotFoundError`, `collection_name`),
termini rari, acronimi, nomi di configurazione — perché il modello di embedding può
"avvicinarle" semanticamente a concetti sbagliati e allontanarle dalla corrispondenza
lessicale esatta.

Il prototipo (`prototype/02-hybrid-reranking/`) ha già dimostrato empiricamente (sul corpus
FastAPI) che la combinazione **retrieval lessicale BM25 + dense fusi con Reciprocal Rank
Fusion (RRF) + reranking cross-encoder** risolve esattamente questo problema: sui simboli
esatti il MRR sale da 0.13 a 0.94 con embedder locale debole; anche con embedder forte
migliora la robustezza sulle query lessicali. Il materiale è confermato da fonte esterna
(`wiki/sources/llm-wiki-v2-agentmemory.md`, sezione hybrid search con RRF) come la ricetta
di riferimento per il retrieval su codebase.

La porta `VectorStore` (`src/sertor_core/domain/ports.py`) espone oggi solo similarità
vettoriale; Chroma locale non offre retrieval lessicale nativo; Azure AI Search lo offre
nativamente con hybrid query + semantic ranker, che sulla via Azure è il percorso naturale.
I due test di qualità marcati `xfail` nei test di integrazione
(`tests/integration/test_baseline_quality.py`, `tests/integration/test_precision_at_k.py`)
sono lo spazio designato per fissare il ground-truth e dimostrare il miglioramento: questa
feature li completa.

---

## 2. Obiettivi e criteri di successo (LSC)

| ID | Criterio (misurabile, tech-agnostico) | Collegamento |
|----|---------------------------------------|--------------|
| LSC-1 | Su un set di query note sul corpus sertor (query lessicali + NL), il motore ibrido raggiunge un **hit@5 ≥ baseline vettoriale + 10 punti percentuali** sulle query a simbolo/termine esatto (misurato con `evaluate` su ground-truth fissato). | CS-2 epica, Principio V |
| LSC-2 | Il motore ibrido è **selezionabile tramite configurazione** (variabile d'ambiente / config file), senza modificare il codice; il motore baseline rimane funzionante e invariato. | CS-4 epica, Principio VIII |
| LSC-3 | I consumatori esistenti (facade `search_code`/`search_docs`/`search_combined`, server MCP, CLI `sertor-rag`) **beneficiano dell'ibrido senza cambiare la loro superficie** (nessuna modifica richiesta ai consumatori). | CS-2 epica, Principio I |
| LSC-4 | Il reranking è **opzionale**: senza la dipendenza del reranker installata, il motore ibrido funziona correttamente (fusione RRF senza secondo stadio), senza errori e senza degrado silenzioso. | Principio II, III |
| LSC-5 | Il motore ibrido è **testabile senza rete**, con provider e indice lessicale mock. | Principio V |
| LSC-6 | I **2 test `xfail`** di pertinenza (`test_baseline_quality`, `test_precision_at_k`) passano (strict) con il ground-truth fissato e le soglie calcolate sul confronto baseline vs ibrido. | Principio V, DA-003 |
| LSC-7 | Il motore ibrido funziona su **qualunque corpus** (non solo il corpus sertor): host-agnostico, nessuna assunzione sulla struttura del progetto ospite. | Principio X |

---

## 3. Stakeholder e attori

| Attore | Ruolo |
|--------|-------|
| **Agente LLM (Claude Code / MCP client)** | Principale beneficiario: `search_code` sulle query architetturali/lessicali migliora qualità del contesto fornito all'agente. |
| **Owner/maintainer** | Configura il motore ibrido; fissa il ground-truth; valuta il miglioramento. |
| **Server MCP `sertor-rag`** (`src/sertor_mcp/`) | Consumatore a valle: deve beneficiare dell'ibrido senza cambiamenti. |
| **CLI `sertor-rag`** | Consumatore a valle: idem. |
| **`sertor-core` (dipendenza a monte)** | Nucleo su cui il motore si appoggia (porte, composition root, Settings). |
| **Codebase target** | Il corpus su cui il motore viene esercitato (per il dogfooding: il repo Sertor stesso). |

---

## 4. Ambito

### In ambito

- **Componente lessicale** (BM25 o equivalente) che indicizza i chunk del corpus e li
  ordina per rilevanza rispetto a una query lessicale; costruzione al momento
  dell'indicizzazione, parallelamente al vettoriale.
- **Fusione dei ranking** con Reciprocal Rank Fusion (RRF): combina il ranking vettoriale
  e quello lessicale in un ranking unificato; parametri di fusione configurabili e con
  default centralizzati in `Settings`.
- **Reranking come secondo stadio opzionale**: cross-encoder che riordina il pool fuso;
  dipendenza isolata come extra installabile separatamente; comportamento senza extra
  definito e non silenzioso.
- **Selezione del motore**: manopola di configurazione che sceglie il motore da
  istanziare (baseline / ibrido); la scelta avviene **solo nel composition root**.
- **Percorso Azure AI Search**: quando il backend vettoriale è Azure AI Search, possibilità
  di delegare l'ibrido al backend nativo (hybrid query + semantic ranker) invece di
  eseguire RRF lato client; le due strategie sono dichiarate e selezionabili.
- **Ground-truth set** sul corpus sertor: un set minimo di coppie (query, file/chunk attesi)
  che copre query lessicali/a simbolo e query NL; usato per completare i 2 test `xfail`
  esistenti e misurare il miglioramento.
- **Valutazione comparativa**: misura hit@k e MRR del motore baseline vs ibrido vs
  ibrido+rerank sullo stesso ground-truth; il confronto è il criterio di accettazione.
- **Log strutturati** per le operazioni ibrido (retrieval lessicale, fusione, reranking),
  coerenti col pattern esistente (`log_event`, Principio IX).
- **Retro-compatibilità**: il motore baseline resta immutato e continua a funzionare.

### Fuori ambito

- Modifica della superficie pubblica della facade, del server MCP o della CLI (sono
  consumatori: beneficiano senza cambiamenti di interfaccia).
- **Motore a grafo** (FEAT-005): il retrieval strutturale su AST/knowledge graph è una
  modalità distinta.
- **Motore agentico** (FEAT-006): il retrieval multi-step è una modalità distinta.
- Costruzione dell'indice lessicale **persistente su disco** per corpus di grandi dimensioni
  (Could per FEAT-009): in questa feature la priorità è la correttezza e la testabilità; la
  persistenza è una rifiinitura.
- **GUI/web**.
- **Wizard di configurazione interattivo** (FEAT-CLI-003).
- **Distribuzione del pacchetto** (FEAT-CLI-006).

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Indice lessicale

**REQ-001 (Event-driven)** *When the hybrid engine indexes a corpus, the system shall build a
lexical index over the same chunks ingested into the vector store, using a tokenizer that
preserves identifiers, snake_case sub-tokens, and rare terms.*

> Ancora: prototipo `prototype/02-hybrid-reranking/hybrid.py` righe 26-35 (`tokenize`): il
> tokenizer che spezza gli snake_case è il differenziatore principale per le query a simbolo.

**REQ-002 (Ubiquitous)** *The lexical index shall cover the same corpus namespace as the
vector collection it mirrors, so that lexical and vector results are always drawn from the
same set of chunks.*

**REQ-003 (Event-driven)** *When the corpus is re-indexed (full rebuild), the system shall
rebuild the lexical index together with the vector index, so that the two indexes remain
consistent.*

**REQ-004 (Unwanted behaviour)** *If the lexical index is not present when a hybrid query is
issued, then the system shall raise an explicit error (not return a silently degraded result).*

> Pattern: stesso comportamento strict del `BaselineEngine` (`ensure_index`, `IndexNotFoundError`,
> `src/sertor_core/engines/baseline.py:54-62`).

**REQ-005 (Ubiquitous)** *The lexical index shall be namespaced consistently with the vector
collection it mirrors (same corpus and provider namespace), so that distinct corpora or
providers never share the same lexical index.*

### Gruppo B — Fusione RRF

**REQ-010 (Event-driven)** *When a hybrid query is issued, the system shall retrieve a
candidate pool from both the vector store and the lexical index, then fuse the two ranked
lists using Reciprocal Rank Fusion (RRF), and return the top-k results from the fused
ranking.*

> Ancora: `prototype/02-hybrid-reranking/hybrid.py` righe 38-43 (`rrf`): formula
> `score += 1/(c + rank)` per ciascuna lista.

**REQ-011 (Ubiquitous)** *The RRF fusion shall use a configurable constant `c` (default: 60)
and a configurable pool size (the number of candidates drawn from each source before fusion),
with defaults centralised in `Settings` and overridable via configuration, without modifying
code.*

> Principio VIII. La costante `c=60` è il valore standard (Cormack et al.); il pool size del
> prototipo è 30 (`POOL=30`, `evaluate.py` riga 28).

**REQ-012 (Ubiquitous)** *The fused ranking shall be deterministic: given identical inputs,
the system shall always return the same ordered list; ties shall be broken consistently (e.g.
by chunk_id, as in the existing multi-collection merge in `src/sertor_core/services/retrieval.py:131`).*

**REQ-013 (Ubiquitous)** *The system shall return results as `RetrievalResult` instances (the
same domain entity used by the baseline engine), so that consumers require no changes.*

> Principio I: i consumatori (`RetrievalFacade`, MCP, CLI) dipendono dall'entità di dominio,
> non dalla strategia di retrieval.

### Gruppo C — Reranking (secondo stadio opzionale)

**REQ-020 (Optional feature)** *Where the reranker extra is installed, the hybrid engine shall
optionally apply a cross-encoder reranker to re-score the RRF-fused pool and return the
top-k results re-ordered by the cross-encoder score.*

> Ancora: `prototype/02-hybrid-reranking/rerank.py` (`rerank()`, FlashRank ONNX senza torch).

**REQ-021 (Ubiquitous)** *The reranker dependency shall be isolated as a separately installable
extra, with lazy import; the hybrid engine shall be importable and operable without the
reranker extra installed.*

> Principio III: dipendenza pesante isolabile. Pattern già applicato per `azure` e `mcp`
> nel `composition.py` (import lazy dentro le `build_*`).

**REQ-022 (Event-driven)** *When reranking is configured but the reranker extra is not
installed, the system shall raise an explicit, actionable error (not silently fall back to
RRF-only), so that a misconfiguration is immediately visible.*

> Principio IV: niente null silenzioso / fallback opaco.

**REQ-023 (Optional feature)** *Where reranking is disabled (not configured or extra absent),
the hybrid engine shall return the RRF-fused results directly, without any degradation or
silent change in behaviour.*

**REQ-024 (Ubiquitous)** *The pool size fed to the reranker shall be configurable (default:
pool_size > k, e.g. 3× k) and centralised in `Settings`.*

### Gruppo D — Selezione del motore e integrazione con il composition root

**REQ-030 (Ubiquitous)** *The system shall expose a configuration knob (e.g. `SERTOR_ENGINE`)
to select the active engine (`baseline` or `hybrid`); the default shall be `baseline` (no
change to existing behaviour until explicitly configured).*

> [DA CHIARIRE — D1]: vedi sezione 10.

**REQ-031 (Ubiquitous)** *The engine selection shall be resolved exclusively in the
composition root (`src/sertor_core/composition.py`); no service, facade, or adapter shall
import or reference a concrete engine implementation directly.*

> Principio I: scelta delle implementazioni solo nel composition root.

**REQ-032 (Ubiquitous)** *The `RetrievalFacade` (`src/sertor_core/services/retrieval.py`)
shall remain the single, stable retrieval surface for all consumers (MCP, CLI, agents);
switching to the hybrid engine shall not require changes to the facade's interface or to any
consumer.*

**REQ-033 (Ubiquitous)** *The hybrid engine shall expose the same interface as
`BaselineEngine` (same `index`, `query`, and `ensure_index` methods and same `name`
attribute), so that the composition root can substitute them transparently.*

> Structural typing (Protocol): non richiede ereditarietà, basta conformità di interfaccia
> (coerente con il pattern `EmbeddingProvider` / `VectorStore` in `domain/ports.py`).

### Gruppo E — Percorso Azure AI Search nativo

**REQ-040 (Optional feature)** *Where the vector store backend is Azure AI Search
(`store_backend=azure`), the system shall support delegating the hybrid retrieval to the
native Azure AI Search hybrid query (combining dense and keyword search) and optional
semantic ranker, instead of performing client-side RRF.*

> [DA CHIARIRE — D2]: vedi sezione 10.

**REQ-041 (Optional feature)** *Where the Azure-native hybrid path is selected, the system
shall produce results functionally equivalent to the client-side RRF path (same `RetrievalResult`
interface, same k, same doc_type filter), so that consumers are unaffected.*

**REQ-042 (Ubiquitous)** *The choice between client-side RRF and Azure-native hybrid shall be
a configuration decision (not a code change), resolved in the composition root.*

### Gruppo F — Misura della qualità e ground-truth

**REQ-050 (Ubiquitous)** *The system shall include a ground-truth set for the sertor corpus
containing at least 10 query–expected-file pairs, covering both lexical/symbol queries
(e.g. exact symbol names from `src/sertor_core/`) and natural-language architectural queries.*

> Chiude i 2 test `xfail`: `tests/integration/test_baseline_quality.py` e
> `tests/integration/test_precision_at_k.py`. Il set minimo di 10 coppie è sufficiente per
> un confronto statisticamente indicativo (il prototipo ne usava 18: 10 NL + 8 symbol,
> `prototype/02-hybrid-reranking/eval_queries.json`).

**REQ-051 (Event-driven)** *When the evaluation runs on the ground-truth set, the system
shall compare baseline, hybrid, and hybrid+rerank (where reranker is available) reporting
hit@1, hit@3, hit@5, hit@10, and MRR@10 for each mode; the comparison shall be a gating
criterion for feature acceptance.*

**REQ-052 (Ubiquitous)** *The two existing `xfail` integration tests (`test_baseline_quality`
and `test_precision_at_k`) shall be filled with the ground-truth set defined in REQ-050,
converted to `strict=True`, and shall pass on the hybrid engine with the acceptance thresholds
set at: hybrid hit@5 ≥ baseline hit@5, and hybrid MRR ≥ baseline MRR.*

> Soglie minime conservative (non regredisce); il miglioramento reale è documentato dal
> confronto in REQ-051 e deve soddisfare LSC-1 (≥ baseline + 10 pp sulle query a simbolo).

**REQ-053 (Ubiquitous)** *The ground-truth set shall not contain assumptions about the
internal structure of the sertor project; it shall be expressed as relative file paths or
chunk identifiers, and remain valid if the repository is reorganised.*

> Principio X: host-agnostico anche per il ground-truth.

### Gruppo G — Osservabilità

**REQ-060 (Event-driven)** *When the hybrid engine executes a query, the system shall emit a
structured log event (via the existing `log_event` mechanism,
`src/sertor_core/observability/logging.py`) recording at minimum: engine name, provider,
collection, lexical_hits, dense_hits, fused_k, rerank_applied, elapsed_ms.*

**REQ-061 (Event-driven)** *When the reranker is applied, the system shall emit a separate
structured log event recording: reranker_model, pool_size, top_k, elapsed_ms.*

**REQ-062 (Ubiquitous)** *Log records shall never contain secret values (API keys,
credentials); redaction follows the existing pattern (`observability/logging.py`).*

### Gruppo H — Retro-compatibilità e non-distruttività

**REQ-070 (Ubiquitous)** *The `BaselineEngine` and its tests shall remain unchanged and fully
passing after the introduction of the hybrid engine.*

**REQ-071 (Ubiquitous)** *The default configuration (`SERTOR_ENGINE=baseline`) shall produce
identical results to the current system for all existing consumers.*

**REQ-072 (Ubiquitous)** *The hybrid engine shall be non-destructive on the target repository:
it shall not modify user source files; the lexical index shall be stored in the same
namespaced index directory as the vector store (e.g. `.index/`).*

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| NFR-01 | **Dipendenze verso l'interno** (Principio I) | Il motore ibrido dipende solo dalle porte del dominio (`EmbeddingProvider`, `VectorStore`) e dalle entità (`RetrievalResult`); non importa SDK concreti di vector store né di embeddings direttamente. |
| NFR-02 | **Isolamento dipendenze pesanti** (Principio III) | La dipendenza del reranker (cross-encoder) è installabile separatamente (extra dedicato) e importata in modo lazy; la sua assenza non impedisce l'installazione o l'uso del pacchetto base. |
| NFR-03 | **Testabilità senza rete** (Principio V) | Il motore ibrido è testabile con provider mock (`FakeEmbedder`, `InMemoryStore`) e indice lessicale mock/in-memory, senza cloud né rete; i test unitari devono passare con `pytest -m "not cloud"`. |
| NFR-04 | **Latenza doppio retrieval** | La latenza totale di una query ibrida (senza reranker) deve essere accettabile per uso interattivo da un agente LLM: il doppio retrieval (vettoriale + lessicale) non deve introdurre attesa percettibile su corpus di dimensioni tipiche di una codebase media (< 10.000 chunk). [DA CHIARIRE — D3: soglia numerica] |
| NFR-05 | **Configurabilità centralizzata** (Principio VIII) | Tutti i parametri del motore ibrido (costante RRF `c`, pool size, abilitazione reranker, selezione engine) sono in `Settings`; nessun default hardcodato nei componenti. |
| NFR-06 | **Idempotenza** (Principio VI) | Re-indicizzare lo stesso corpus produce gli stessi chunk e lo stesso indice lessicale; le query sullo stesso indice producono lo stesso risultato ordinato (determinismo). |
| NFR-07 | **Osservabilità** (Principio IX) | Ogni operazione di retrieval ibrido emette log strutturati sufficienti a diagnosticare un fallimento senza leggere il codice (REQ-060/061/062). |
| NFR-08 | **Host-agnosticità** (Principio X) | Il motore ibrido non presuppone la struttura interna del progetto ospite; funziona su qualsiasi corpus indicizzato con il nucleo sertor. |
| NFR-09 | **Retro-compatibilità** | Nessun consumatore esistente (facade, MCP, CLI) richiede modifiche di codice o di configurazione per continuare a funzionare con `SERTOR_ENGINE=baseline` (default). |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **V-1**: Il motore ibrido opera sulla porta `VectorStore` esistente (`domain/ports.py`);
  la porta può richiedere un'estensione o una porta aggiuntiva per il retrieval lessicale,
  ma le porte `EmbeddingProvider` e `VectorStore` rimangono invariate nei consumatori esistenti.
- **V-2**: La scelta del motore avviene **solo nel composition root** (Principio I, REQ-031).
- **V-3**: Nessun segreto su file versionati (REQ-E5 epica).
- **V-4**: Python ≥ 3.11 (vincolo d'epica).
- **V-5**: Il ground-truth set (REQ-050) è scritto come codice/fixture nel repo; non si
  dipende da file esterni non versionati.
- **V-6**: Il motore baseline deve restare pienamente funzionante (REQ-070/071).

### Assunzioni

- **A-1**: L'indice lessicale in-memory (caricato al momento dell'indicizzazione dalla
  collezione vettoriale) è sufficiente per il corpus sertor e per codebase di dimensioni
  tipiche (< 10.000 chunk); la persistenza su disco è una rifiinitura futura (FEAT-009).
- **A-2**: Il reranker cross-encoder di riferimento è FlashRank (ONNX, niente torch, come
  nel prototipo `rerank.py`); la scelta concreta è di design, ma il requisito di isolamento
  (extra lazy) vale per qualsiasi libreria di reranking scelta.
- **A-3**: Sulla via Azure, Azure AI Search supporta nativamente il hybrid query + semantic
  ranker; la disponibilità della feature è condizionata al tier del servizio
  configurato dall'utente.
- **A-4**: Il ground-truth set iniziale copre il corpus sertor (repo Sertor stesso); rimane
  host-agnostico come struttura (pesi relativi, non path assoluti).
- **A-5**: Il server MCP (`src/sertor_mcp/`) consuma la `RetrievalFacade` e non il motore
  direttamente; l'integrazione dell'ibrido nella facade è quindi il punto di collegamento
  naturale.

### Dipendenze

- **D-1**: `sertor-core` in `master` — nucleo retrieval (FEAT-001), motore baseline
  (FEAT-002), porte (`domain/ports.py`), `Settings` (`config/settings.py`),
  composition root (`composition.py`), `log_event` (`observability/logging.py`).
- **D-2**: `BaselineEngine` in `src/sertor_core/engines/baseline.py` — interfaccia di
  riferimento che il motore ibrido deve replicare (REQ-033).
- **D-3**: `EvalReport` e `evaluate()` in `src/sertor_core/engines/evaluation.py` — riusato
  per la valutazione comparativa (REQ-051).
- **D-4**: Test `xfail` esistenti: `tests/integration/test_baseline_quality.py` e
  `tests/integration/test_precision_at_k.py` — da completare (REQ-052).
- **D-5** (opzionale, extra): libreria cross-encoder per il reranking (FlashRank ONNX o
  equivalente); deve essere installabile separatamente senza impattare il pacchetto base.

---

## 8. Rischi

| ID | Rischio | Prob. | Impatto | Mitigazione |
|----|---------|-------|---------|-------------|
| R-1 | **Ground-truth troppo piccolo o sbilanciato**: un set di 10 coppie può produrre metriche fragili; differenze di 1 hit cambiano MRR significativamente. | Media | Medio | LSC-1 fissa il delta minimo (+10 pp sulle query a simbolo, non sul complesso); usare almeno 5 query symbol + 5 NL (come nel prototipo). |
| R-2 | **Indice lessicale stale**: se il corpus viene modificato ma l'indice lessicale non viene ricostruito, i risultati divergono. | Bassa | Alto | REQ-003: rebuild atomico (lessicale + vettoriale insieme); REQ-004: errore esplicito se mancante. |
| R-3 | **Reranker peggiora i risultati su embedder forte**: dimostrato nel prototipo (ms-marco su Azure: MRR 0.98→0.96). | Alta | Basso | REQ-020/023: reranking opzionale; default off. Il problema è noto e documentato; il confronto in REQ-051 lo evidenzierà. |
| R-4 | **Dipendenza del reranker inquina il pacchetto base**: torch o librerie pesanti entrano come dipendenza transitiva. | Media | Alto | NFR-02: extra isolato, import lazy (REQ-021); la CI di base (`pytest -m "not cloud"`) non installa l'extra. |
| R-5 | **Violazione Principio I**: logica di selezione del motore fuori dal composition root. | Bassa | Alto | REQ-031: vincolo esplicito; Constitution Check al momento del design. |
| R-6 | **Azure AI Search: feature non disponibile nel tier**: il semantic ranker richiede un tier specifico. | Media | Medio | REQ-040/041: percorso Azure è *opzionale*; fallback dichiarato sul RRF client-side. |
| R-7 | **Superfici non allineate dopo l'ibrido**: facade, MCP o CLI richiedono modifiche inaspettate. | Bassa | Medio | REQ-032/033: interfaccia del motore = stessa del baseline; verifica con test di integrazione end-to-end su MCP. |

---

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-001..005 (indice lessicale), REQ-010..013 (fusione RRF), REQ-030..033 (selezione motore), REQ-050..052 (ground-truth e xfail), REQ-070..072 (retro-compatibilità), NFR-01..03, NFR-05..06, NFR-08..09 | Il ciclo minimo dimostrabile: indice lessicale + RRF + selezione via config + test di qualità strict = la feature è "fatta" (Principio V). |
| **Should** | REQ-020, REQ-023..024 (reranking opzionale), REQ-060..062 (osservabilità), NFR-04 (latenza), NFR-07 (osservabilità) | Completano la qualità e l'osservabilità; il reranking è il vantaggio maggiore sul caso Ollama. |
| **Could** | REQ-021..022 (extra reranker isolato + errore esplicito se assente), REQ-040..042 (percorso Azure AI Search nativo), REQ-053 (robustezza ground-truth) | Importanti per robustezza e percorso Azure, ma non bloccanti per la dimostrazione del valore core. |
| **Won't (questa feature)** | Persistenza dell'indice lessicale su disco (→ FEAT-009), motore a grafo (→ FEAT-005), motore agentico (→ FEAT-006), GUI/web, distribuzione pacchetto. | Fuori ambito dichiarato. |

---

## 10. Domande aperte

### DA-1 — Selezione del motore: granularità della manopola

**Contesto.** REQ-030 introduce `SERTOR_ENGINE=baseline|hybrid` come manopola globale in
`Settings`. Due alternative si presentano:

- **Opzione A — Manopola globale** (come REQ-030): `SERTOR_ENGINE` in `Settings` seleziona
  il motore per tutti i consumatori contemporaneamente. Semplice, un solo punto di
  configurazione.
  - Pro: coerente con Principio VIII (un solo posto), nessuna proliferazione di flag.
  - Contro: non permette di usare ibrido per `search_code` e baseline per `search_docs` se
    un giorno servisse.
- **Opzione B — Manopola per-chiamata** (flag opzionale nella facade / nel MCP): ogni
  invocazione può specificare il motore da usare.
  - Pro: flessibilità massima.
  - Contro: rompe LSC-3 (i consumatori devono cambiare), complica la superficie MCP/CLI,
    viola lo spirito di "senza modificare l'interfaccia dei consumatori".

**Raccomandazione**: **Opzione A**. La manopola globale è allineata ai Principi VIII e I
(scelta di design nel composition root). La flessibilità per-chiamata non ha un caso d'uso
concreto oggi (YAGNI, Principio III). Confermare o emendare prima del design.

---

### DA-2 — Percorso Azure AI Search: equivalenza funzionale o due strategie dichiarate?

**Contesto.** Quando `store_backend=azure`, Azure AI Search supporta nativamente il hybrid
query (dense + keyword BM25 interno) + semantic ranker. Due opzioni:

- **Opzione A — Equivalenza trasparente**: il motore ibrido su Azure usa automaticamente il
  backend nativo (nessun RRF client-side); i risultati sono "funzionalmente equivalenti"
  ma potenzialmente diversi nei dettagli (Azure usa il proprio BM25 e il proprio semantic
  ranker).
  - Pro: semplicità di configurazione per l'utente; nessuna logica RRF client-side su Azure.
  - Contro: l'equivalenza è dichiarata ma non identica (diverso tokenizer, diverso ranker);
    il ground-truth set misura su una strategia sola.
- **Opzione B — Due strategie dichiarate**: `SERTOR_ENGINE=hybrid-azure` (RRF delegato al
  backend) vs `SERTOR_ENGINE=hybrid` (RRF client-side); l'utente sceglie esplicitamente;
  il confronto è trasparente.
  - Pro: nessuna ambiguità; il comportamento di ciascuna strategia è testabile e
    documentabile separatamente.
  - Contro: più manopole; più casi di test.

**Raccomandazione**: **Opzione A** con una nota esplicita in documentazione che "su Azure
l'ibrido delega al backend nativo". Evita la proliferazione di manopole; l'utente Azure
ottiene automaticamente il migliore disponibile. Da confermare; se l'utente preferisce
trasparenza esplicita, l'Opzione B è preferibile.

---

### DA-3 — Soglia numerica di latenza (NFR-04)

**Contesto.** NFR-04 richiede che la latenza del doppio retrieval sia "accettabile per uso
interattivo da un agente LLM". Il valore "< 10.000 chunk" è un'assunzione sul corpus; la
soglia numerica non è fissata.

- **Opzione A — Nessuna soglia numerica**: il requisito resta qualitativo ("non deve
  introdurre attesa percettibile"); la soglia si fissa empiricamente nella fase di misura.
- **Opzione B — Soglia esplicita**: es. "il retrieval ibrido (senza reranker) deve
  completarsi in ≤ 500 ms su un corpus di 5.000 chunk con embedder locale".

**Raccomandazione**: **Opzione A** per questa feature (FEAT-004). La latenza del retrieval
lessicale in-memory è tipicamente trascurabile rispetto alla latenza di embedding; la soglia
si fissa con misura reale in fase di design. Segnalare se ci sono vincoli di latenza
stringenti per il caso d'uso MCP interattivo.

---

### DA-4 — Ground-truth set: chi lo produce e quando

**Contesto.** REQ-050 richiede un set di almeno 10 coppie (query, file/chunk attesi) sul
corpus sertor. Il set può essere:

- **Opzione A — Prodotto insieme ai requisiti** (questa fase): alcune coppie evidenti sono
  già identificabili (es. query `"EmbeddingProvider"` → `src/sertor_core/domain/ports.py`;
  query `"come funziona la fusione multi-corpus"` → `src/sertor_core/services/retrieval.py`).
  Produrlo ora riduce il rischio di avere un test `xfail` ancora aperto a fine feature.
- **Opzione B — Prodotto in fase di design/implementazione**: il ground-truth è un artefatto
  di design che richiede di conoscere i chunk effettivi prodotti dal nucleo; meglio rimandarlo.

**Raccomandazione**: **Opzione A parziale**: identificare almeno 5-6 coppie
"ovviamente corrette" già nei requisiti (query a simbolo + file sorgente atteso), come
fixture iniziale; completare il set a 10+ in fase di design quando i chunk ID reali sono
disponibili. Questo sblocca la CI senza aspettare l'implementazione.

---

### [DA CHIARIRE — D1] Manopola engine: nome e default

**Domanda prioritaria (richiede risposta prima del design).**
Il nome della variabile di configurazione (`SERTOR_ENGINE`?) e il default (`baseline`) sono
assunzioni documentate in REQ-030. Confermare:
- Il nome `SERTOR_ENGINE` è accettabile o si preferisce un'altra convenzione (es.
  `SERTOR_RAG_MODE`, `SERTOR_RETRIEVAL_MODE`)?
- Il default `baseline` è giusto (nessun cambiamento di comportamento per chi non configura
  nulla), oppure si vuole che l'ibrido diventi il default quando disponibile?

**Contesto:** con default `baseline`, chi ha già un indice non vede cambiamenti. Con default
`hybrid`, l'ibrido diventa immediatamente attivo (richiede un re-index per costruire
l'indice lessicale). La raccomandazione è **default `baseline`** per retro-compatibilità,
con upgrade esplicito via config.

---

### [DA CHIARIRE — D2] Percorso Azure: in-scope per questa feature?

**Domanda a priorità media (influenza ambito).**
Il percorso Azure AI Search nativo (REQ-040..042) è marcato Could in MoSCoW. Confermare
se deve restare in questa feature o essere rimandato a una sotto-feature/iterazione separata.
Il costo principale è un adapter dedicato nel composition root per il percorso Azure-hybrid.
Se l'ambiente di sviluppo è primariamente Azure (dal CLAUDE.md: `RAG_BACKEND=azure`),
portarlo in Should potrebbe essere più allineato con il dogfooding reale.
