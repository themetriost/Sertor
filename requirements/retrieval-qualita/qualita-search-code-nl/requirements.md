# Requisiti — Qualità del retrieval fuso code+doc (`search_combined`) su query NL/architetturali

<!-- Deriva da: FEAT-003 (epica retrieval-qualita) -->
<!-- Nota: cartella `qualita-search-code-nl/` mantenuta per stabilità del path; il baricentro è la FUSIONE code+doc. -->

## 1. Contesto e problema (perché)

Il **differenziatore** di Sertor (mission/vision: [[mission-vision]], `README.md`) è **fondere codice e
documenti** (requisiti, spec, wiki) in **un unico corpus interrogabile insieme**: *il codice dice cosa
fa, la documentazione dice perché*. La superficie che incarna questo valore è **`search_combined`**
(`services/retrieval.py`), affiancata da `search_code` (solo `doc_type=code`) e `search_docs` (solo
`doc`).

Su questo terreno il retrieval è **debole per le query NL/architetturali** (intento ampio: «come
funziona X», «quali sono i requisiti di Y e dove è implementato»). **Misurato** (2026-06-20, harness
FEAT-001/011): i casi `nl` colpiscono a **rank 3-6**, con casi reali in cui un **documento** ranka
sopra il sorgente quando serve il codice — o viceversa. L'audit RAG (skill `rag-production-audit`) ha
indicato come cause B3 (no query transformation) e B4 (no contextual compression).

**Sfumatura cardine (decisione utente):** il «buono» è **intent-dependent** — *«where defined»* →
sorgente; *«where applied/used»* → anche un test; *«come funziona / quali requisiti»* → la **doc** **e**
il codice **insieme**. Il caso d'uso-firma della mission è proprio **requisito→implementazione**: una
query deve far emergere `requirements/…`/`specs/…` (il *perché*) **fusi** col `src/…` (il *cosa*). Una
metrica che premia «almeno uno» non basta: nasconde il caso in cui un tipo **annega** l'altro.

Lo strumento di misura esiste già (la suite `sertor-rag eval`, hit@k/MRR); questa feature lo **estende**
con una misura di **fusione**, non lo reinventa.

## 2. Obiettivi e criteri di successo
- **CS-1 (set NL onesto e multi-superficie):** esiste un set NL/architetturale versionato con `expected`
  **intent-dependent**, che copre query **doc-oriented**, **code-oriented** e **cross-artefatto
  (requisito→implementazione)**.
- **CS-2 (baseline per-superficie):** sono registrate baseline distinte di `search_code`,
  `search_docs` e `search_combined` *prima* di ogni intervento.
- **CS-3 (miglioramento per-superficie):** la pertinenza NL di `search_docs` **e** di `search_code`
  migliora di un margine **misurabile** rispetto alla baseline (P1.c — si attaccano le cause isolate).
- **CS-4 (integrazione fusa):** la `search_combined` **integra** i guadagni per-superficie ed è
  misurata come **test d'integrazione** con una metrica di **fusion coverage** (P2.b).
- **CS-5 (additività):** a leve spente, comportamento e costo identici a oggi; nessuna regressione sui
  casi e baseline esistenti.

## 3. Stakeholder e attori
- **Owner/maintainer (tu):** vuole che una query architetturale/«requisiti» restituisca **doc + codice
  fusi**, e poterlo dimostrare con un numero.
- **Agente LLM (consumatore via MCP):** beneficiario diretto — meno iterazioni; oggi compensa la
  debolezza con query multiple.
- **La suite di valutazione (FEAT-001/011):** strumento di accettazione, qui esteso con la fusione.

## 4. Ambito

### In ambito
- Un **set NL** con `expected` intent-dependent su **tutte e tre** le superfici, inclusa una
  **categoria dedicata** per i casi **cross-artefatto** (requisito↔implementazione) [P3.a].
- **Baseline e miglioramento per-superficie** (`search_docs`, `search_code`), con **`search_combined`
  come test d'integrazione** [P1.c].
- Una **metrica di fusion coverage** per i casi che richiedono entrambi i tipi [P2.b].
- La valutazione **guidata-da-misura** di una o più **leve** opt-in (query transformation, filtro
  metadata, contextual retrieval) e l'adozione solo di ciò che migliora.
- Il **gate di non-regressione** sui casi/baseline esistenti.

### Fuori ambito
- Le **modalità** di retrieval in sé (epica `sertor-core`).
- L'eval **su provider forte/cloud** (FEAT-002): qui local-first.
- La **calibrazione delle soglie** `SERTOR_MIN_SCORE` (FEAT-004): ortogonale (governa l'astensione).
- Le tecniche avanzate **come feature a sé** (FEAT-005/006/007): qui sono **leve candidate**, non
  l'oggetto.
- Il *come* (tecnica scelta, struttura): fase di **design**.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Set NL multi-superficie + categoria fusione
- **REQ-001 (Ubiquitous):** *The system shall provide a versioned NL/architectural evaluation set whose
  expected results reflect each query's intent, covering doc-oriented, code-oriented, and
  cross-artifact (requirement→implementation) queries.*
- **REQ-002 (Ubiquitous):** *The system shall mark cross-artifact/fusion cases (where the right answer
  must span documentation and source) as a distinct case category so they can be measured on their
  own.*
- **REQ-003 (Ubiquitous):** *The system shall allow an NL case's expected results to be intent-typed:
  source for "where defined", documentation for "why/how", and both for cross-artifact cases.*
- **REQ-004 (Unwanted):** *If an NL case cannot be given an intent-appropriate expected target, then it
  shall be excluded rather than scored against an arbitrary target.*

### Gruppo B — Misura e miglioramento per-superficie, combined come integrazione (P1.c)
- **REQ-010 (Ubiquitous):** *The system shall record baselines of NL pertinence separately for
  `search_code`, `search_docs`, and `search_combined` before any improvement.*
- **REQ-011 (Ubiquitous):** *The system shall improve `search_docs` NL pertinence on the set by a
  measurable margin over its baseline.*
- **REQ-012 (Ubiquitous):** *The system shall improve `search_code` architectural-NL pertinence on the
  set by a measurable margin over its baseline.*
- **REQ-013 (Ubiquitous):** *The system shall validate that `search_combined` integrates the
  per-surface gains, measured as the integration test of the fused surface.*
- **REQ-014 (Ubiquitous):** *The system shall not declare any technique an improvement unless it shows
  a measured lift on the relevant surface versus baseline.*

### Gruppo C — Metrica di fusione (fusion coverage, P2.b)
- **REQ-020 (Ubiquitous):** *For a fusion/cross-artifact case, the system shall measure fusion
  coverage: the case counts as covered only when the top-k contains at least one relevant document AND
  at least one relevant source.*
- **REQ-021 (Ubiquitous):** *The system shall report fusion coverage alongside hit-rate@k/MRR so that a
  "one type drowns the other" failure is explicitly visible.*
- **REQ-022 (Unwanted):** *If a fusion case's top-k satisfies plain hit@k but lacks one required type,
  then it shall count as a miss on fusion coverage (hit@k alone must not hide the gap).*

### Gruppo D — Leve come opt-in additive, scelte per misura
- **REQ-030 (Optional feature):** *Where an NL-improvement lever (query transformation, extended
  metadata filtering, contextual retrieval, …) is enabled, the system shall apply it while leaving
  default behaviour and cost unchanged when disabled.*
- **REQ-031 (Ubiquitous):** *The system shall let the choice and adoption of lever(s) be driven by the
  measured per-surface and fusion comparison, not prescribed in advance; an adopted lever stays
  disabled by default until a default change is justified and decided explicitly.*

### Gruppo E — Non-regressione, local-first, vehicle, confine D↔N
- **REQ-040 (Unwanted):** *If an improvement regresses the existing cases or the recorded per-surface /
  fusion baselines beyond tolerance, then it shall be rejected (non-regression gate).*
- **REQ-041 (Ubiquitous):** *The system shall keep the measurement local-first and deterministic (no
  cloud provider required).*
- **REQ-042 (Ubiquitous):** *The system shall measure through the existing vehicle (`sertor-rag eval`),
  adding fusion coverage as an additive metric rather than replacing hit-rate@k/MRR.*
- **REQ-043 (Optional feature):** *Where the NL set is authored with agent assistance
  (`eval-suite-author`), candidates shall be persisted only via the vehicle and the run shall remain
  deterministic (confine D↔N; no LLM in the run path beyond the embedder).*

## 6. Requisiti non funzionali
- **RNF-1 (additività):** a leve spente, comportamento e costo identici a oggi; `sertor-core` invariato
  fuori dai punti nuovi (Principio I/III).
- **RNF-2 (misurabilità):** nessun «miglioramento» senza numero sul ground-truth (Principio V).
- **RNF-3 (local-first/deterministico):** misura locale, ripetibile, senza rete; nessun LLM nel run
  (l'embedder è l'unico modello).
- **RNF-4 (mission-alignment):** la feature **rafforza la fusione code+doc** (stella polare della
  costituzione), non la indebolisce; le metriche per-superficie + fusion coverage lo rendono
  verificabile.
- **RNF-5 (no regressione):** casi e baseline esistenti (FEAT-001/011) restano validi.

## 7. Vincoli, assunzioni e dipendenze
- **Dipende da FEAT-001/011** (suite/metriche, su `master`) come strumento, e ne riusa l'harness
  (`engines/evaluation.py`, `services/eval/`, `eval/suite.toml`). La **fusion coverage** è una
  metrica/categoria **nuova e additiva** sull'harness.
- **Relazioni (non sovrapposizioni):** FEAT-004 (soglie/astensione) ortogonale; FEAT-005/006/007 sono
  le **leve candidate**; FEAT-002 (cloud) fuori ambito.
- **Confine D↔N:** run deterministico; giudizio su set/intento/leva = skill/utente.
- Riferimenti: `engines/hybrid.py`, `services/retrieval.py` (search_code/docs/combined, `apply_min_score`),
  `engines/evaluation.py`, `services/eval/`, `eval/suite.toml`.

## 8. Rischi
- **R-1 — Overfitting al set** (R-2 epica): set rappresentativo + valutare un hold-out separato.
- **R-2 — Etichettatura d'intento/fusione soggettiva:** `expected` intent-typed e i casi «needs both»
  richiedono giudizio → criteri espliciti e versionati col set.
- **R-3 — Leva che migliora una superficie ma rompe la fusione o costa troppo:** misurare il combined
  come integrazione (REQ-013) e il trade-off costo↔qualità.
- **R-4 — Valore marginale vs agente:** l'agente già itera via MCP (mitiga B3); misurare il guadagno
  single-shot e decidere se vale (DA-e).

## 9. Prioritizzazione (MoSCoW)
- **Must:** Gruppo A (set + categoria fusione + expected intent-typed), Gruppo B REQ-010/013/014
  (baseline per-superficie + combined integrazione + criterio misura), Gruppo C (fusion coverage),
  Gruppo E REQ-040/041/042.
- **Should:** Gruppo B REQ-011/012 (miglioramento effettivo di doc e code), Gruppo D (≥1 leva valutata
  e adottata opt-in se migliora), REQ-043.
- **Could:** adozione di più leve; cambio del default se il lift è forte; hold-out di validazione
  formale.
- **Won't (qui):** prescrivere una tecnica a monte; eval cloud (FEAT-002); calibrazione soglie
  (FEAT-004); le leve come feature dedicate (FEAT-005/006/007).

## 10. Domande aperte
- **DA-a — Quali leve per prime** (query transformation/HyDE vs filtro metadata vs contextual
  retrieval)? *(Design, guidato da costo atteso vs lift per-superficie.)*
- **DA-b — Costruzione del set NL** (quante query per superficie, come etichettare intento e «needs
  both» in modo ripetibile, hold-out)? Riusare `eval-suite-author`?
- **DA-c — Soglie di «miglioramento»** (delta minimo per-superficie su hit@k/MRR e soglia di fusion
  coverage) per dichiarare done.
- **DA-d — Rapporto con FEAT-004/005/006/007:** se una leva entra qui, la sua feature dedicata diventa
  il «come»? coordinamento con le soglie (FEAT-004, ortogonali).
- **DA-e — Valore reale vs agente:** target = migliorare il **single-shot** o documentare il pattern
  agentico? (Decide se è core-work o per lo più documentazione.)
