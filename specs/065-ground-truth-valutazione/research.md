# Phase 0 — Research & Decisioni: Ground-truth & valutazione della pertinenza (FEAT-001)

**Branch**: `065-ground-truth-valutazione` · **Spec**:
[`spec.md`](spec.md) · **Requisiti**:
`requirements/retrieval-qualita/ground-truth-valutazione/requirements.md`

> Le **5 forche di design** (DA-a..DA-e della spec §«Forche») sono **già decise dall'utente** (vedi
> brief del plan). Questa fase non le riapre: le **progetta**, ne risolve le *implicazioni di come* e
> chiude i nodi residui (DOVE vive la suite/baseline, come il run ottiene l'elenco documenti senza
> violare il Principio XI, forma del report di non-regressione).
>
> **Nota di processo.** `.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> sono **assenti** nel repo (come nei plan 049..064): parametri ricavati per convenzione dal nome
> branch; nessun hook SpecKit eseguito. MCP `sertor-rag` **interrogato** per ancorare al codice
> (`evaluate`/`composition`/`IndexManifest`/installer): tutti i tool hanno risposto (nessun errore da
> riportare).

---

## Quadro di ancoraggio (cosa esiste già — promuovere, non reinventare)

| Asset esistente | Dove | Ruolo nel design |
|---|---|---|
| `evaluate(engine, ground_truth, ks) → EvalReport` | `engines/evaluation.py:41` | **Cuore deterministico riusato as-is** (firma invariata). |
| `QueryableEngine` Protocol (`provider` + `query`) | `engines/evaluation.py:18` | Tipo a cui i `build_*` engine già aderiscono (structural). |
| `EvalReport(hit_rate, mrr, queries, provider)` | `engines/evaluation.py:32` | Reso interno; il report host-facing lo **avvolge** (per-query + kind). |
| `GROUND_TRUTH` (11 coppie `query/expected/kind`) + `relative_to` | `tests/fixtures/ground_truth.py` | **Migrato a TOML** come esempio dogfood (`eval/suite.toml`). |
| `build_baseline_engine` / `build_engine` / `build_facade` | `composition.py:344/434/296` | Vehicle: il comando `eval` costruisce l'engine da qui (Principio XI). |
| `IndexManifest.load(collection).files` (path indicizzati) | `services/index_manifest.py:122` | Sorgente dell'**elenco documenti indicizzati** per la validazione path (REQ-012/DA-e). |
| Pattern sottocomandi CLI (argparse, `_resolve_settings`, `_check_backend`, `enable_observability`, exit 0/1/2) | `cli/__main__.py` | Modello per il nuovo `eval`. |
| `output.py` (format umano + `--json`, equivalenza informativa) | `cli/output.py` | Modello per `format_eval_report` / `format_regression_report`. |
| `install_rag.py` plan-builder (`ENV_MERGE`, `FILE`, `MARKER_BLOCK`, asset) | `packages/sertor/.../install_rag.py` | Per cablare manopole `.env` + eventuale skill host-facing. |
| Skill-pattern `derive-entity-types` | `.claude/commands/derive-entity-types.md` | **Pattern** (non codice) per la genesi assistita FEAT-008. |

---

## DA-a — Formato dell'artefatto-suite = **TOML** (deciso)

### Decisione
La suite è un file **TOML** versionato (`eval/suite.toml`), array di tabelle `[[case]]`:

```toml
# Esempio (migrazione del fixture dogfood). kind ∈ {"symbol","nl"} opzionale.
[[case]]
query = "EmbeddingProvider"
expected = ["src/sertor_core/domain/ports.py"]
kind = "symbol"

[[case]]
query = "where concrete adapters are chosen and the configuration is wired"
expected = ["src/sertor_core/composition.py"]
kind = "nl"
```

### Implicazione critica risolta: lettura vs scrittura
- **Lettura**: `tomllib` (stdlib 3.11+, già il floor del progetto). Zero dipendenze. ✅
- **Scrittura**: `tomllib` è **read-only**. Il tool DEVE scrivere/aggiornare (authoring interattivo,
  persistenza candidati approvati FEAT-008, feedback FEAT-009).

**Scelta: serializzatore TOML minimale fatto a mano** (`services/eval/suite_io.py`), *non* `tomli-w`.

*Razionale (Principio II/III — niente dipendenze pesanti senza evidenza):* lo schema è **deliberatamente
piatto e chiuso** — array di tabelle con solo `query: str`, `expected: list[str]`, `kind: str?` (+
commento di linea opzionale). La serializzazione di questo sottoinsieme è **banale e robusta** se:
1. si **legge sempre con `tomllib`** dopo ogni scrittura (round-trip validato → il writer non può
   produrre TOML invalido senza che un test lo prenda — SC-001/REQ-004);
2. si **escapano** solo i due casi che contano per stringhe basic TOML (`"` → `\"`, `\` → `\\`), e le
   query multilinea usano il **basic multiline** `"""…"""`;
3. niente tabelle annidate, niente tipi esotici (date/float/inline-table) nello schema.

Il writer emette tabelle `[[case]]` in **ordine stabile** (idempotenza, Principio VI): preserva l'ordine
dei casi esistenti, append in coda. Una **regola di fragilità esplicita**: se una query contiene una
sequenza che il writer non sa escapare in sicurezza (controllo difensivo), **solleva** `SuiteWriteError`
invece di emettere TOML ambiguo (Principio IV — mai stato corrotto silenzioso) — segnale che faremmo il
fallback a `tomli-w`. *(Promemoria di valutazione documentato qui: se in implementazione il round-trip
fallisce su casi reali del dogfood, si adotta `tomli-w` come extra opzionale; ad oggi lo schema non lo
giustifica.)*

### Import/export JSON per la genesi (FEAT-008)
La raccomandazione-fonte (export JSON per la genesi LLM) è un **dettaglio della skill** (FEAT-008): la
skill può proporre candidati in JSON e poi farli **persistere via il writer TOML** (un solo formato
canonico sul disco). Non serve un secondo formato persistente nell'MVP → non lo introduciamo (YAGNI).

---

## DA-b — Non-regressione = **baseline su file versionato + tolleranza** (deciso)

### Decisione
La baseline è un **file versionato** del progetto (`eval/baseline.toml`) che registra le metriche
accettate; il confronto usa una **tolleranza configurabile**. Pavimento assoluto **opzionale, NON
nell'MVP**.

### Forma del file baseline (TOML, gemello della suite)
```toml
# Generated/updated by `sertor-rag eval --record-baseline`. Versioned project data.
recorded_at = "2026-06-20T11:30:00Z"   # informativo
provider = "ollama:nomic-embed-text"   # provenienza della misura
queries = 11
mrr = 0.83
[hit_rate]                              # hit-rate@k per ogni k
1 = 0.55
3 = 0.82
5 = 0.91
10 = 1.0
```

### Logica (REQ-040..044)
- **REQ-040 (registrazione se assente)**: `--record-baseline` scrive `eval/baseline.toml` dalle metriche
  correnti. Se la baseline esiste e l'utente NON passa il flag, il run **non** la tocca (Principio VI,
  non-distruttività).
- **REQ-042 (confronto)**: a baseline presente, il run calcola il **delta** per ogni metrica chiave.
  Metrica di gate = **`mrr`** e **`hit_rate@k`** sui `k` registrati; il report mostra `current`,
  `baseline`, `delta`.
- **REQ-043 (gate)**: se una metrica scende **sotto** baseline **oltre `tolerance`** → **exit 1**
  (`RegressionDetected`, `SertorError`). Entro tolleranza → exit 0. Tolleranza da
  `SERTOR_EVAL_TOLERANCE` (default `0.0` = nessuna regressione ammessa; un valore es. `0.02` ammette
  fluttuazioni). La tolleranza è **assoluta sul punteggio** (semplice, deterministica).
- **REQ-044 (aggiornamento)**: solo su `--record-baseline` esplicito (mai automatico). Riscrivere la
  baseline su una misura migliore è **accettazione esplicita** dell'utente.

*Pavimento assoluto (Could)*: rinviato. Una manopola `SERTOR_EVAL_MIN_MRR` futura potrebbe imporre un
floor a prescindere dalla baseline. Non serve all'MVP «non peggiorare» → non si implementa (YAGNI). Voce
promossa al backlog (vedi §Tracciamento scope).

---

## DA-c — Genesi assistita = **skill NUOVA che riusa il PATTERN** di `derive-entity-types` (deciso)

### Decisione
FEAT-008 (Should, P2) è una **skill host-facing dedicata** (es. `derive-eval-suite`/`eval-author`),
**non** un modulo di codice che chiama un'API LLM. Riusa il **pattern** (non il codice) di
`derive-entity-types`: l'**agente conversazionale** legge il corpus via i tool RAG/MCP, **propone**
candidati `query → atteso`, l'utente approva; **solo gli approvati** si persistono via il writer TOML.

### Seam progettato ora, skill dopo
Il **run deterministico non dipende mai** dalla skill né da un LLM (RNF-4, Principio XI). Il seam che la
skill consumerà è **già tutto deterministico e CLI-side**:
- **lettura corpus**: i tool RAG/MCP esistenti (`search_code`/`search_docs`) — la skill li usa per
  proporre query e vedere quali path tornano;
- **validazione candidato**: `sertor-rag eval validate-path` (vedi DA-e) — la skill verifica che gli
  `expected` proposti esistano nell'indice **prima** di proporre la persistenza;
- **persistenza**: `sertor-rag eval add-case` (writer TOML, non-distruttivo idempotente) — la skill
  scrive **solo** i casi approvati.

Così FEAT-008 è **puro giudizio dell'agente** sopra primitive deterministiche: nessun nuovo codice LLM
nel core/CLI. La skill può seguire l'MVP (P2) senza bloccare il P1.

---

## DA-d — Superficie: **sottocomando `sertor-rag eval`** + skill per authoring/feedback (deciso)

### Decisione (confine D↔N netto)
| Capacità | Superficie | D o N |
|---|---|---|
| RUN suite + metriche (REQ-030/033/035) | `sertor-rag eval run` | **D** (deterministico, via vehicle) |
| Confronto 2 config locali (REQ-034) | `sertor-rag eval run --compare baseline,hybrid` | **D** |
| Registra/confronta baseline + gate (REQ-040..044) | `sertor-rag eval run --record-baseline` / gate by default | **D** |
| Authoring interattivo (REQ-010..012) | `sertor-rag eval add-case` (write-time validation) | **D** (deterministico: raccolta input, non giudizio LLM) |
| Validazione path contro indice (REQ-012/DA-e) | `sertor-rag eval validate-path` | **D** (primitiva per la skill e per `add-case`) |
| Genesi assistita (FEAT-008, REQ-020..023) | **skill** `derive-eval-suite` | **N** (giudizio agente) |
| Feedback esplicito (FEAT-009, REQ-050..052) | **skill** + `eval add-case`/`amend-case` | **N** (giudizio agente) |

**Il comando `eval` è un thin consumer**: costruisce l'engine via `build_engine`/`build_baseline_engine`
(Principio XI), chiama `evaluate` (servizio core), formatta via `output.py`. Nessuna logica di retrieval
nel CLI (Principio I). `--compare` chiama `evaluate` due volte (una per config) — il codice esiste già
nel test `test_baseline_quality.py`, lo si promuove.

### Distinzione `add-case` D vs skill N
`add-case` è **deterministico** anche se «authoring»: raccoglie `query`/`expected`/`kind` dall'utente (CLI
args o prompt), valida il path, persiste. Non c'è giudizio LLM → vive nel CLI. La **genesi assistita** è
diversa: l'agente *ragiona* su quali query siano buone → è N → skill. Il confine è «c'è un LLM che
ragiona?», non «si scrive sulla suite?».

---

## DA-e — Validazione `expected_path` contro l'indice, **via vehicle** (deciso + nodo Principio XI risolto)

### Il problema
REQ-012: a write-time, un `expected_path` assente dal corpus → **warning + conferma esplicita** prima di
persistere. Serve l'**elenco dei documenti indicizzati**. `IndexManifest.load(collection).files` lo
contiene (path → mtime/hash/logic) — ma **importarlo direttamente dal CLI di eval violerebbe il
Principio XI** (consumo della libreria fuori dai vehicle)? No: il CLI **è** un vehicle. Il vincolo XI è
sui *consumatori a runtime esterni* (agente/script/skill), che NON devono importare `sertor_core`. Il
comando `sertor-rag eval` è parte del vehicle CLI: può costruire un servizio core via composition.

### Decisione
1. **Servizio core** `IndexedDocuments` (o riuso diretto del manifest) esposto da una **factory
   composition** `build_indexed_docs(settings)` che ritorna l'elenco path della collezione corrente
   (legge `IndexManifest.load(collection_name(...))`). Restituisce l'**insieme dei path indicizzati**.
   Se il manifest è assente/incompatibile → ritorna `None` (manifest non disponibile): la validazione
   degrada a **warning «non posso verificare, indice non disponibile»** (Principio IV — esplicito, mai
   `None` silenzioso che finge «tutto ok»).
2. **`sertor-rag eval validate-path <path>...`**: comando deterministico che la **skill** (consumatore
   esterno, Principio XI) invoca per verificare i candidati — la skill non importa `sertor_core`, chiama
   il vehicle CLI.
3. **`add-case`** usa lo stesso servizio internamente (è già dentro il vehicle): path assente → warning +
   richiede `--confirm` (o conferma interattiva su TTY) prima di scrivere (REQ-012).

*Nota:* il manifest registra i **path relativi alla root indicizzata**. La validazione e il rebase
(`relative_to`, REQ-005) lavorano sulla stessa convenzione → coerenza by construction.

---

## Nodo N1 — DOVE vivono suite e baseline nel progetto ospite (REQ-002/041)

### Decisione: cartella **`eval/`** a root del progetto ospite (versionata)
- `eval/suite.toml` — la suite (dato versionato, REQ-001/006).
- `eval/baseline.toml` — il riferimento (dato versionato, REQ-041).

*Razionale:*
- **NON `.sertor/`**: è la sede runtime **gitignored** (RUNTIME_IGNORES); la suite/baseline sono **dato
  versionato del progetto, non output rigenerabile** (REQ-006, RNF-6) → starebbero nel posto sbagliato.
- **`eval/` a root**, convenzione semplice e prevedibile (asse «igiene radice» della feature 016).
  Override via `SERTOR_EVAL_DIR` (Principio VIII — config centralizzata, host-agnostico: l'ospite con
  layout diverso cambia config, non codice; Principio X).
- Default `Settings.eval_dir = Path("eval")`. Il comando risolve `suite.toml`/`baseline.toml` sotto
  `eval_dir`.

---

## Nodo N2 — Forma del report (umano + JSON) e osservabilità

### Report di valutazione (REQ-033) — host-facing, avvolge `EvalReport`
Campi: per-`k` `hit_rate`, `mrr`, `queries`, `provider`, **dettaglio per-query** (`query`, `kind`,
`hit: bool`, `rank: int|null`, `expected`, `top_path`). Reso **umano** (tabella/blocchi, stile
`format_search_results`) **e JSON** (equivalenza informativa, invariante SC-002 esistente).

`evaluate` oggi NON ritorna il dettaglio per-query → **estensione non-breaking** (vedi data-model): si
aggiunge un campo opzionale `per_query` a `EvalReport` (default vuoto, retrocompatibile) **oppure** una
funzione gemella `evaluate_detailed` che ritorna il dettaglio. **Scelta**: estendere `EvalReport` con un
campo `per_query: tuple[QueryOutcome, ...] = ()` (additivo, i consumatori esistenti ignorano il campo;
i 2 test strict e `test_baseline_quality` restano verdi). `kind` **non** entra nella firma di
`evaluate` (resta metadato del solo artefatto/report): `evaluate` riceve `(query, expected)`; il `kind`
viaggia parallelo dalla suite al report (il chiamato CLI lo riassocia per indice). Così la firma core
`GroundTruth = list[(query, expected)]` resta invariata (Principio I/III).

### Report di non-regressione (REQ-042) — umano + JSON
Per ogni metrica: `current`, `baseline`, `delta`, `regressed: bool` (sotto baseline oltre tolleranza).
`verdict ∈ {pass, regressed, no-baseline}`. Exit code mappato dal verdetto.

### Osservabilità (RNF-3, Principio IX)
Il run emette un **evento strutturato** `eval` via `log_event` con: `provider`, `queries`,
`hit_rate@k`, `mrr`, `regressed: bool`, eventuale `tolerance`. **Solo metriche, nessun testo libero**
(niente query/path nell'evento — coerente con la policy export OTel metrics-only della feature 061). Così
l'epica `osservabilita` (FEAT-009) potrà storicizzare il trend. `enable_observability(settings)` è già
chiamato dal pattern CLI → l'evento finisce nello store se `SERTOR_OBSERVABILITY=true`.

---

## Nodo N3 — Installabilità (REQ-060/061, Principio X, corollario installabile)

### Cosa arriva all'ospite dall'installer
1. **Manopole `.env`** (REQ-061): `SERTOR_EVAL_DIR`, `SERTOR_EVAL_TOLERANCE` aggiunte ai template
   `env.local.tmpl`/`env.azure.tmpl` (commentate, default-off coerenti con le altre manopole).
2. **Comando `sertor-rag eval`**: **installabile per costruzione** — viaggia col pacchetto `sertor-core`
   (è un sottocomando della CLI già distribuita). Verifica: nessun import del codice di test di Sertor
   (la logica vive in `services/eval/`, non in `tests/`). SC-002/SC-008.
3. **Skill host-facing** (FEAT-008/FEAT-009, P2): quando arriveranno, si cablano nel plan-builder
   `build_rag_plan` come asset `FILE`/skill (stesso meccanismo del blocco RAG-usage). **Tracciato come
   debito di completamento** della capacità (regola «una feature è completa solo se installabile»): il
   P1 (run + non-regressione + authoring CLI) è completo e installabile senza skill; le skill P2
   aggiungono la genesi/feedback e vanno cablate prima che FEAT-008/009 contino come *done*.
4. **Esempio dogfood**: `eval/suite.toml` di Sertor (migrazione del fixture) vive nel **repo Sertor**,
   non viene spedito agli ospiti (è il *nostro* dato): l'ospite crea il **suo** (SC-002).

---

## Tracciamento dello scope (regola «gli Out-of-Scope si promuovono»)

| Voce rinviata | Casa durevole |
|---|---|
| Genesi assistita (skill) | **FEAT-008** epica `retrieval-qualita` (già nel backlog §8) |
| Feedback esplicito (skill) | **FEAT-009** epica `retrieval-qualita` (già nel backlog §8) |
| Pavimento assoluto (`SERTOR_EVAL_MIN_MRR`) | **Could** → riga nel backlog d'epica `retrieval-qualita` (registrazione/baseline avanzata) |
| Trend storico delle metriche | **FEAT-009 epica `osservabilita`** (fuori ambito, già tracciato) |
| Confronto live cloud/provider forte | **FEAT-002** epica `retrieval-qualita` (fuori ambito) |

Nessun rinvio reale resta sepolto solo dentro `specs/`.

---

## Fuori ambito (ribadito)
Modalità di retrieval (epica `sertor-core`) · confronto live cloud/provider forte (FEAT-002) ·
`search_code` architetturale (FEAT-003) · calibrazione soglie `SERTOR_MIN_SCORE` (FEAT-004) · tecniche
avanzate HyDE/multi-query/filtro/contextual (FEAT-005/006/007) · trend storico (`osservabilita`
FEAT-009).
