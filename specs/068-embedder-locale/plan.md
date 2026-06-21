# Implementation Plan: Embedder locale (local-first per indicizzazione, eval e CI) (FEAT-011)

**Branch**: `068-embedder-locale` | **Date**: 2026-06-21 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification da `/specs/068-embedder-locale/spec.md` + requisiti
`requirements/sertor-core/embedder-locale/requirements.md` (REQ-001..062, RNF-1..6).

> **Rigenerazione (2026-06-21).** Questo plan e tutti gli artefatti di design SOVRASCRIVONO una run
> interrotta, basata su una config ora cambiata. **Decisione utente vincolante:** `RAG_BACKEND` è
> **rimosso**; il provider di embeddings si sceglie SOLO con `SERTOR_EMBED_PROVIDER` (default `glove`);
> lo store con `SERTOR_STORE_BACKEND` (default proprio `local`). Nessuna logica «se RAG_BACKEND=azure →
> azure».

## Summary

La feature aggiunge **due provider di embeddings locali e deterministici** dietro la porta
`EmbeddingProvider` esistente — `glove` (GloVe 6B 300d, PDDL, **nuovo default**, semantica NL locale) e
`hash` (char-n-gram stdlib, pavimento airgapped/CI) — e **semplifica la config rimuovendo `RAG_BACKEND`**:
il provider si sceglie con la sola manopola `SERTOR_EMBED_PROVIDER`, lo store con `SERTOR_STORE_BACKEND`
(default `local`). GloVe è acquisito on-demand alla prima indicizzazione, con cache utente condivisa
per-macchina e override di percorso (`SERTOR_GLOVE_PATH`) per l'airgapped; l'assenza fail-loud produce un
errore azionabile (Principio XII), mai un degrado silenzioso. L'approccio è **additivo** (composition root +
nuovi adapter + Settings + un errore di dominio + template/doc installer), salvo la rimozione mirata di
`RAG_BACKEND`; porta, servizi ed engine restano invariati. Risolve l'avvio local-first zero-credenziali (CS-1)
e abilita il gate eval offline (prerequisito CI, FEAT-003).

## Technical Context

**Language/Version**: Python ≥ 3.11.
**Primary Dependencies**: stdlib (`hashlib`, `urllib`, `zipfile`, `os`); `numpy` **già transitiva** da
`chromadb` (`pyproject.toml:16`), importata **lazy** dall'adapter GloVe. **Nessun nuovo extra**, nessuna
nuova dipendenza diretta.
**Storage**: vector store esistente (Chroma locale default / Azure Search opt-in); file dati GloVe in cache
utente per-macchina (XDG-style), git-ignored per costruzione (fuori dal repo).
**Testing**: pytest (unit offline, FIRST; subprocess per il determinismo cross-`PYTHONHASHSEED`); ruff.
**Target Platform**: Windows/macOS/Linux (CLI host-agnostica).
**Project Type**: libreria + CLI (`sertor-core`), 4-pacchetti `uv` workspace.
**Performance Goals**: footprint runtime GloVe 300d ≈ centinaia di MB (RNF-5, documentato); `hash`
trascurabile. Nessun costo monetario per i locali; download GloVe una-tantum (RNF-6).
**Constraints**: determinismo cross-macchina/cross-Python (`hash`); lazy/zero-download per il core
importabile; nessun LLM nel core (confine D↔N); accesso solo via vehicle (Principio XI).
**Scale/Scope**: additivo; `sertor-core` invariato fuori da `composition.py`, `config/settings.py`,
`domain/errors.py`, e i nuovi `adapters/embeddings/{hashing,glove,glove_cache}.py`; + template/doc/test
installer.

## Constitution Check (PRE-design)

Gate dalla costituzione v1.4.0 (12 principi + gate missione). Esito: **PASS 12/12 + missione PASS**.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. I due adapter vivono in `adapters/`
  dietro la porta `EmbeddingProvider`; `numpy` è importata **lazy** dentro l'adapter GloVe; il wiring resta
  solo in `composition.py`. Il core resta esercitabile con mock (`hash` è già stdlib-puro e mockabile).
- [x] **II — Boundary & local-first:** PASS. Rafforza il local-first: due provider che girano **interamente
  in locale** senza credenziali; la scelta è guidata da config (`SERTOR_EMBED_PROVIDER`). Store ortogonale,
  default `local`.
- [x] **III — YAGNI & unità piccole:** PASS. Nessun nuovo extra/dipendenza; cache risolta con stdlib (no
  `platformdirs`); niente idf/pesatura (pavimento grezzo); funzioni piccole (resolver, tokenizzazione,
  aggregazione).
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. Nuovo `GloveUnavailableError` ricco di contesto;
  valore-manopola non valido → `ConfigError(key=…)`; nessun `None` silenzioso (OOV/testo vuoto → vettore zero
  deterministico, è un risultato valido, non un'assenza nascosta).
- [x] **V — Testabilità & misure:** PASS. Test FIRST offline per entrambi gli adapter (determinismo, OOV,
  fail-loud, cache); il provider deterministico **abilita** la misura di non-regressione offline (eval).
- [x] **VI — Idempotenza & non-distruttività:** PASS. Stesso input → stesso vettore; download atomico
  (`os.replace`); install≠run (acquisizione legata alla sola indicizzazione, lazy load); cache derivata e
  rigenerabile, fuori dal repo.
- [x] **VII — Leggibilità:** PASS. Naming di dominio (`resolve_glove_file`, `ensure_glove`,
  `HashingEmbedder`, `GloveEmbedder`); guard clause nelle risoluzioni.
- [x] **VIII — Configurabilità centralizzata:** PASS. **Migliora** la centralizzazione: una sola manopola per
  il provider (non più master-switch ambiguo); default solo in `Settings`; `glove_path` da env.
- [x] **IX — Osservabilità:** PASS. Eventi `embeddings_provider_selected`/`glove_download`/`glove_cache_hit`
  metrics-only, coerenti con gli esistenti; nessun segreto/path con username.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS. Cache utente per-macchina condivisa fra progetti (non
  dipende dalla struttura dell'ospite); override path configurabile; manopole nel template `.env` per ogni
  ospite. Nessuna assunzione sul progetto ospite.
- [x] **XI — Consumo via vehicles:** PASS. Provider costruito via `build_embedder`/composizione; eval/CI lo
  ottiene via vehicle (REQ-062); adapter mai importati fuori dai test.
- [x] **XII — Fail Loud, Fix the Cause:** PASS. GloVe assente → errore azionabile (non si spegne né si
  ripiega in silenzio); `RAG_BACKEND` residuo → **warning** esplicito (non lettura silenziosa); avviso `hash`
  «NL limitata». Nessuna soppressione.
- [x] **Allineamento alla missione:** PASS. Abilita il retrieval **semantico locale sul versante doc**
  (profilo doc-only/doc-heavy) — cuore del differenziatore fusione code+doc — senza cloud; sblocca l'adozione
  enterprise e il gate eval in CI; semplifica la config (meno frizione). Non deriva su concern periferici.

## Constitution Check (POST-design)

Rivalutato dopo Phase 0/1 (research + data-model + contracts). Esito: **PASS 12/12 + missione PASS**, nessuna
deroga.

- **I:** confermato — `build_embedder` a 4 rami con import lazy per ramo; `numpy` lazy in `glove.py`; il
  `domain` non importa SDK (l'eccezione vive in `domain/errors.py`, stdlib).
- **II/VIII:** la rimozione di `RAG_BACKEND` e le manopole `SERTOR_EMBED_PROVIDER`/`SERTOR_STORE_BACKEND`
  rendono la config **più** centralizzata e meno ambigua (vedi `contracts/provider-resolution.md`).
- **III:** design senza nuovi extra né `platformdirs`; nessuna entità di dominio nuova (solo adapter + 1
  errore).
- **IV/XII:** `GloveUnavailableError` (REQ-040/041) + warning `config_rag_backend_ignored` (REQ-007) +
  `ConfigError` su valore non valido (REQ-003): tre punti fail-loud progettati esplicitamente.
- **V:** matrice di test offline definita nei contratti (incl. subprocess per `PYTHONHASHSEED`).
- **VI:** acquisizione atomica + lazy load confermati; cache git-ignored fuori dal repo.
- **IX:** tre eventi metrics-only definiti, nessun campo sensibile.
- **X:** cache per-macchina e override path confermati host-agnostici; template `.env` per ogni ospite.
- **XI:** nessun nuovo seam — riuso delle factory esistenti; adapter non importati fuori dai test.
- **Missione:** confermato. **Nota di scope onesta (non una deroga):** la piena installabilità (REQ-060/061)
  richiede di allineare anche il concetto installer `backend` (`rag_profile`/`configure`/`--backend`); è
  tracciata come **debito di completamento P2** (gruppo G Should) — la feature non conta come *done* finché
  l'installer non depone le manopole nuove. Il valore minimo P1 (provider + determinismo offline) è completo
  senza quel pezzo.

## Project Structure

### Documentation (this feature)
```text
specs/068-embedder-locale/
├── plan.md              # questo file
├── research.md          # Phase 0 (8 decisioni DA-1..DA-8 + corollario installer)
├── data-model.md        # Phase 1 (Settings, adapter, errore, eventi, pyproject, installer)
├── quickstart.md        # Phase 1 (7 scenari operativi via vehicle)
├── contracts/
│   ├── provider-resolution.md   # DA-1: manopole + tabella decisionale + validate_backend
│   └── local-providers.md       # hash + glove: contratto, acquisizione, fail-loud, test
└── checklists/requirements.md   # (preesistente)
```

### Source Code (impatto reale — enumerazione)
```text
src/sertor_core/
├── domain/errors.py                         # + GloveUnavailableError
├── config/settings.py                       # - backend; - embed_provider(property); - RAG_BACKEND;
│                                            #   + embed_provider(campo, def glove); store_backend def local;
│                                            #   + glove_path; validate_backend ri-chiavata; warning REQ-007
├── composition.py                           # build_embedder → 4 rami; eventi selezione (build_store invariato)
└── adapters/embeddings/
    ├── hashing.py                           # NUOVO — HashingEmbedder (stdlib)
    ├── glove.py                             # NUOVO — GloveEmbedder (numpy lazy)
    └── glove_cache.py                       # NUOVO — resolver + download/estrazione (stdlib)

packages/sertor/src/sertor_installer/
├── assets/rag/env.local.tmpl               # - RAG_BACKEND; + SERTOR_EMBED_PROVIDER; + # SERTOR_GLOVE_PATH
├── assets/rag/env.azure.tmpl               # - RAG_BACKEND; + SERTOR_EMBED_PROVIDER=azure
├── rag_profile.py / configure.py / __main__.py  # allinea concetto backend→provider (debito P2, Should)
docs/install.md · packages/sertor/docs/install.md  # 4 provider, nuovo default, nota di migrazione (REQ-061)
```

**Structure Decision**: layer-respecting Clean Architecture esistente; tutta la logica nei nuovi adapter +
composition + settings, niente nei servizi/engine (REQ-050).

## Punti del repo che referenziano `RAG_BACKEND` / `Settings.backend` (cambiamento trasversale)

Enumerazione completa (produzione; esclusi `prototype/`, `wiki/`, vecchie `specs/`). Da modificare/migrare:

**Core (codice):**
1. `src/sertor_core/config/settings.py:93` — campo `backend` → **rimuovere**.
2. `src/sertor_core/config/settings.py:211-213` — property `embed_provider` derivata da `backend` →
   **campo** risolto da `SERTOR_EMBED_PROVIDER`.
3. `src/sertor_core/config/settings.py:224` — `validate_backend` su `backend == "azure"` → su
   `embed_provider == "azure"`.
4. `src/sertor_core/config/settings.py:254-264` — lettura `RAG_BACKEND` + warning `config_no_env_found`
   condizionato a `RAG_BACKEND` → **rimuovere `RAG_BACKEND`**, riformulare il warning, **aggiungere** warning
   `config_rag_backend_ignored` (REQ-007).
5. `src/sertor_core/config/settings.py:273-277` — `backend=…`, `store_backend=os.getenv(…, backend)` →
   `embed_provider=os.getenv("SERTOR_EMBED_PROVIDER","glove")`, `store_backend=os.getenv(…, "local")`,
   `glove_path=…`.
6. `src/sertor_core/composition.py:82` — `if settings.embed_provider == "azure"` → estendere a 4 rami
   (resta valido come ramo azure).

> Nota: gli usi di `backend=` in `adapters/vectorstores/{chroma,azure_search}.py` e in
> `domain/errors.py` (`VectorStoreError.backend`) sono un **omonimo non correlato** (il *backend dello
> store* nell'errore), NON `Settings.backend` — **non si toccano**.

**Core (test):**
7. `tests/unit/test_settings.py:9,16,24,33-37,40-55` — asserzioni su `s.backend` e `RAG_BACKEND` →
   riscrivere su `embed_provider`/`SERTOR_EMBED_PROVIDER` e `store_backend` default `local`. Il test
   `test_embed_provider_follows_backend` e `test_store_backend_defaults_to_rag_backend` vanno **sostituiti**.
8. `tests/unit/test_settings_runtime.py:31,39,43,50,53,55` — `.env` con `RAG_BACKEND` → `SERTOR_EMBED_PROVIDER`.
9. `tests/unit/test_settings_validate_backend.py:22,27,35,45-46` — `Settings(backend=…)` →
   `Settings(embed_provider=…)`.
10. `tests/unit/test_composition.py:22,30,35,53,66,70` — `RAG_BACKEND` e `backend=azure` →
    `embed_provider`/`store_backend`; il commento «local store despite backend=azure» resta valido come
    «despite embed_provider=azure».
11. `tests/unit/test_cli_index.py:23 (commento),108` — `Settings(backend="azure",…)` →
    `Settings(embed_provider="azure",…)`.
12. `tests/unit/test_cli_graph_eval.py:67`, `test_cli_eval_compare.py:43`, `test_cli_eval.py:59`,
    `tests/integration/test_graph_eval_gate.py:84`, `test_eval_gate.py:47` — `Settings(... backend="local" ...)`
    → rimuovere il kwarg `backend` (default ok) o `embed_provider="hash"/"ollama"` secondo il caso.
13. `tests/integration/test_local_only.py:3,16,28` — `RAG_BACKEND=local` → `SERTOR_EMBED_PROVIDER=ollama`
    (il test verifica che la composizione locale instanzi Ollama+Chroma).
14. `tests/unit/test_baseline_engine.py:110` — `RAG_BACKEND=local` → `SERTOR_EMBED_PROVIDER=ollama`.
15. `tests/unit/test_mcp_server.py:44 (commento)` — riferimento a `RAG_BACKEND` nel commento → aggiornare.
16. `tests/unit/test_logging.py:34,38` — usa `backend="local"` come **campo di log** (`log_event`), NON
    `Settings.backend` → **non correlato, non toccare**.

**Installer (codice + asset):**
17. `packages/sertor/src/sertor_installer/assets/rag/env.local.tmpl:3` — `RAG_BACKEND=local` → rimuovere; +
    `SERTOR_EMBED_PROVIDER=glove` + `# SERTOR_GLOVE_PATH=`.
18. `packages/sertor/src/sertor_installer/assets/rag/env.azure.tmpl:3` — `RAG_BACKEND=azure` →
    `SERTOR_EMBED_PROVIDER=azure` (mantiene `SERTOR_STORE_BACKEND=local`).
19. `packages/sertor/src/sertor_installer/rag_profile.py:19,30-40,57-58,87` — concetto `backend=azure|local`
    + `compose_extras` → allineare a provider `glove|hash|ollama|azure` (extra `azure` solo per provider azure).
20. `packages/sertor/src/sertor_installer/configure.py:205,222,258,307-311,343` — scrive `RAG_BACKEND` →
    scrive `SERTOR_EMBED_PROVIDER`; `Settings(backend=…)` → `Settings(embed_provider=…)`.
21. `packages/sertor/src/sertor_installer/configure_report.py:27-28,94,127` — campo `backend` del report →
    rinominare/allineare a provider.
22. `packages/sertor/src/sertor_installer/install_rag.py:175,265` — `env.{profile.backend}.tmpl` →
    selezione template da provider.
23. `packages/sertor/src/sertor_installer/__main__.py:138,244,291,316` — help `--backend → RAG_BACKEND` e
    passaggi di `args.backend` → allineare a `--provider`/`SERTOR_EMBED_PROVIDER`.

> Punti 19-23 = **debito di completamento P2** (gruppo G Should): allineamento del wizard/profilo installer.
> I punti 17-18 (template) e la doc (24) sono Must del corollario (REQ-060/061) e vanno con la feature.

**Installer (test):**
24. `packages/sertor/tests/test_install_rag.py:126-128` (`RAG_BACKEND=local`), `test_env_merge.py:10,21,49`,
    `packages/sertor-install-kit/tests/unit/test_env_merge.py:10,21,49`, `test_cli_configure.py` (multipli),
    `test_configure_write.py` (multipli), `test_config_fields.py:90-107`, `test_configure_check.py:33`,
    `test_configure_report.py:114` — aggiornare a `SERTOR_EMBED_PROVIDER`/provider.

**Documentazione utente:**
25. `docs/install.md`, `packages/sertor/docs/install.md`, `README.md` (se cita `RAG_BACKEND`),
    `.env.example` (root) — descrivere i 4 provider, nuovo default, override airgapped, nota di migrazione
    (REQ-061).

> **`.sertor/.env` del dogfood / ospiti:** NON va toccata dal codice né committata — si **documenta** solo
> la migrazione manuale (`RAG_BACKEND=azure` → `SERTOR_EMBED_PROVIDER=azure`). L'avviso REQ-007 la segnala a
> runtime.

## Forche di design risolte (vedi `research.md`)

| # | Forca | Decisione |
|---|-------|-----------|
| DA-1 | Rimozione `RAG_BACKEND` | `embed_provider` campo da `SERTOR_EMBED_PROVIDER` (def `glove`); store da `SERTOR_STORE_BACKEND` (def `local`); warning fail-loud su `RAG_BACKEND` residuo |
| DA-2 | Provider `hash` | char-n-gram n=3..5, `blake2b` sign-hashing, dim **512**, L2-norm, `name="hash:512"`, solo stdlib |
| DA-3 | Provider `glove` | GloVe 6B 300d; media token in-vocab + L2-norm; OOV via split camel/snake; tutto-OOV→zero; `name="glove:300"`; numpy lazy |
| DA-4 | Cache & download | dir XDG-style stdlib; `glove.6B.zip` da Stanford NLP via `urllib`+`zipfile`; atomic replace; `SERTOR_GLOVE_PATH` override; download legato all'indicizzazione |
| DA-5 | Fail-loud | `GloveUnavailableError` azionabile (entrambe le vie); mai fallback silenzioso; avvisi download/`hash` |
| DA-6 | Osservabilità | 3 eventi metrics-only (`embeddings_provider_selected`/`glove_download`/`glove_cache_hit`) |
| DA-7 | `validate_backend` | ri-chiavata su `embed_provider`/`store_backend`; locali → `[]` (mai blocco) |
| DA-8 | Wiring eval/CI | nessun nuovo seam; via `build_embedder`/composizione (Principio XI) |

## Complexity Tracking

Nessuna violazione costituzionale: tabella vuota. L'unico elemento «aperto» è di **scope** (allineamento
installer `backend`→`provider` come debito di completamento P2 Should), non una deroga a un principio.
