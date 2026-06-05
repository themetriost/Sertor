---
title: Nucleo Wiki Deterministico Host-Agnostico — FEAT-003-D
type: synthesis
tags: [FEAT-003-D, wiki-deterministico, host-agnostico, implementation, completed, python, cli]
created: 2026-06-05
updated: 2026-06-05
sources: [
  "specs/006-nucleo-wiki-deterministico/**",
  "src/sertor_core/wiki_tools/**",
  "wiki.config.toml",
  "tests/fixtures/doc_only_host/**"
]
---

# FEAT-003-D: Nucleo Wiki Deterministico Host-Agnostico

Completamento della **metà deterministica** del wiki LLM (FEAT-003 decomporta in FEAT-003-D + FEAT-003-N). Implementazione via SpecKit (specify → clarify → plan → tasks → implement) del nucleo che **orchestr a tutte le operazioni meccaniche** del wiki locale: scan, lint, struttura, enumerazione, registri, indicizzazione. **Zero LLM, zero rete, offline per costruzione.** Guidato da un file di configurazione unico (`wiki.config.toml`): lo **stesso codice** immodificato esegue le sue operazioni su **qualsiasi progetto** — prova vivente del **Principio X** (host-agnosticità).

## Stato Generale

- **Phase realizzate:** specify → clarify → plan (Phase 0/1) → tasks → implement (Phase 2).
- **Trama US1–US5 + CLI:** ✅ Implementate (11 moduli, 8 test, 44 verdi).
- **Code quality:** ✅ ruff clean.
- **Constitution Check:** ✅ PASS su **tutti e 10 i principi**, inclusi i NON-NEGOZIABILI (I, IV, X); Complexity Tracking vuoto.
- **Branch:** `spec/006-nucleo-wiki-deterministico` (commit impl. `4ac4eaa`) → **mergiata su `master`** via **PR #13** (merge `17569da`, 2026-06-05); branch conservato. Fix post-test inclusi: CLI forza UTF-8 e correzione di link rotti scoperti dal lint stesso.
- **Console-script:** `sertor-wiki-tools` (entry-point via `__main__.py`, registrato in `pyproject.toml`).

## Architettura Realizzata

### Domain: Configurazione come UNICA fonte di specificità (Principio X + VIII)

**`profile.py` — `WikiProfile` (dataclass, frozen):**
- Caricata da `wiki.config.toml` con **`tomllib` (stdlib, zero dipendenze)**.
- Contiene **tutta** la specificità dell'ospite:
  - Radice del wiki (`root`)
  - File indice/registro (`index_file`, `log_file`)
  - Tassonomia (cartelle tematiche: `concepts/`, `tech/`, `experiments/`, `sources/`, `syntheses/`)
  - Cartelle-sorgente da monitorare (`source_dirs`); esclusioni (`exclude`)
  - Lingua (`language`) per stringhe localizzate
  - Profilo dell'ospite (`profile`: `code+doc` | `solo-doc` | `solo-code`)
  - Frontmatter obbligatorio/opzionale
  - Style e formato del wiki link
  - Stringhe di messaggio (`pending`, `clean`)
  - Config RAG (collezione isolata per indicizzazione)
- **Nessun default è hard-coded nei componenti:** il profilo di Sertor è un **file esterno, sostituibile**. Validazione esplicita via `ConfigError` (Principio IV).

### Operazioni Meccaniche (US1–US5)

#### US1 — Configura, non presumere (Priority P1)

**`scan.py` — Ricerca lavoro pendente (mtime-based):**
- Confronta il timestamp dell'**ultima voce di log** con i tempi di modifica dei file nelle `source_dirs` (con esclusioni della config).
- Host-agnostico: usa **`mtime` del filesystem**, non git (funziona su ospiti senza git o con git disabilitato).
- Riporta: numero di file più recenti, anchor (data di ultima voce), elenco cartelle scansionate, messaggio nella lingua configurata.
- Contratto: `wiki.scan/1` (JSON versionato con schema).

#### US2 — Struttura e convenzioni (Priority P2)

**`structure.py` — Inizializzazione idempotente:**
- Crea la struttura del wiki (tassonomia di cartelle + file `index.md` + `log.md`) dal profilo.
- **Non-distruttivo:** se un file esiste, non lo tocca.
- Contenuto minimale valido (frontmatter richiesto, formattazione conforme).
- Contratto: `wiki.structure/1`.

**`frontmatter.py` — Parse e validazione frontmatter:**
- Estrae YAML dal frontmatter (regex robusta, stdlib solo).
- Valida campi richiesti/opzionali.
- Estrae i wikilink uscenti (sintassi a doppie parentesi quadre, con alias dopo la barra `|`) per il lint.

#### US3 — Lint strutturale (Priority P2)

**`lint.py` — Difetti strutturali (meccanico):**
- **Link rotti**: wikilink che puntano a pagine inesistenti.
- **Pagine orfane**: non raggiungibili da `index.md` né da altre pagine.
- **Frontmatter mancante/incompleto**: campi richiesti assenti.
- **Naming violations**: pagine non conformi al kebab-case o collocate in cartella sbagliata (per tipo).
- **Giudizio semantico escluso:** contraddizioni, claim superati, validità contenuto → FEAT-003-N.
- Contratto: `wiki.lint/1`.

#### US4 — Mappa e registri idempotenti (Priority P3)

**`collect.py` — Enumerazione pagine:**
- Mappa strutturata di tutte le pagine del wiki con metadati (percorso, tipo, titolo, tags, created/updated, linee in sorgente) — **senza il corpo**.
- Identità stabile = **path relativo POSIX**: garantisce che rieseguire su input invariato non genera nuovi ID/duplicati.

**`registry.py` — Meccanica indice/log idempotente:**
- Append di **una** voce di log nel formato configurato (data + operazione + titolo + bullet).
- Inserimento link+sommario in `index.md` (nuovo link nella sezione appropriata, niente duplicati).
- Contratti: `wiki.registry/1`.

#### US5 — Orchestrazione indicizzazione separata (Priority P3)

**`indexing.py` — Indicizzazione a collezioni separate:**
- Orchestra il **rebuild idempotente** del wiki in una collezione Chroma/Azure AI Search separata dalle sorgenti (corpus `wiki`).
- **Riusa il facade di retrieval** (`build_indexer`) di `sertor-core` (Chroma via adapter già presente).
- Import **lazy** del facade: offline garantito per le altre operazioni (Principio I).
- Contratto: `wiki.index/1`.

### CLI Sottile (Principio I)

**`__main__.py` — Entry-point console-script `sertor-wiki-tools`:**

```bash
sertor-wiki-tools <op> [--config <path>] [--root <override>] [--json]
```

Operazioni: `scan`, `lint`, `structure`, `validate`, `collect`, `index`.

- Parsing → carica config → chiama funzione pura → emette contratto JSON o output umano.
- Exit code: `0` ok · `1` errore esplicito (`ConfigError`) con stderr.
- `--json` emette contratto versionato; altrimenti output sintetico per umani.

### Contratti Versionati (FR-011)

**`contracts.py` — Dataclass puri + serializzazione JSON:**

```python
@dataclass(frozen=True)
class ScanResult:
    pending: int                      # conteggio file più recenti
    anchor: str | None                # data di ultima voce di log
    dirs_scanned: list[str]           # cartelle effettivamente scansionate
    message: str                      # messaggio nella lingua della config
    schema: str = "wiki.scan/1"       # versionamento forward-compatible

@dataclass(frozen=True)
class LintResult:
    broken_links: list[dict]          # [{"page": "...", "target": "...", ...}, ...]
    orphans: list[str]                # ["pagina1.md", ...]
    missing_frontmatter: list[dict]
    naming_violations: list[dict]
    schema: str = "wiki.lint/1"
```

Consumati da hook (thin wrapper sulla CLI `scan`), skill, e FEAT-003-N (metà LLM).

## Decisioni di Design Chiave

### 1. Configurazione come Codifica dell'Ospite (Principio X + VIII)

**Ogni scelta operativa vive in `wiki.config.toml`:** radice, tassonomia, cartelle-sorgente, lingua, profilo dell'ospite. Il **corpo del codice è zero-assunzionista** — legge la config e opera. **Prova SC-001:** lo **stesso nucleo** (zero modifiche al codice Python) esegue perfettamente su Sertor (`code+doc`, radice `wiki/`) e su un ospite finto `doc_only_host` (solo doc, radice diversa, lingua diversa) cambiando **solo** il file config.

**Conseguenza:**
- Portabilità immediata su qualsiasi progetto (host-agnostico per vero, non per slogan).
- La ricerca di lavoro pendente nell'hook diventa un thin wrapper sulla CLI `scan` (no logica incapsulata).

### 2. Zero LLM, Zero Rete (Principio II + SC-005)

- **Tutte le dipendenze sono stdlib** (tomllib, pathlib, re, json, dataclasses, datetime).
- **Zero nuove dipendenze di terze parti** — nessun beautifulsoup, nessun frontmatter lib, nessun parser esterno.
- Indicizzazione (US5) riusa il facade di `sertor-core` (che già vede Chroma), con import **lazy** → le altre operazioni non dipendono dal vector store.
- Offline garantito per SC-005: offline import, offline execution, testabile senza rete.

### 3. Identità Stabile = Path Relativo POSIX (SC-002 + SC-009)

- ID di pagina = percorso relativo POSIX (`syntheses/nucleo-wiki-deterministico-feat003d.md`).
- Non cambia tra esecuzioni: rieseguire su input invariato produce output **identico**.
- Idempotenza forte: duplicati = zero.

### 4. Errori Espliciti (Principio IV)

- Config assente/malformata → `ConfigError` con messaggio azionabile.
- Indice/registro mancante → errore esplicito o avviso+skip documentato (non stato parziale).
- **Niente `None` silenzioso**, niente eccezioni interne non gestite.

### 5. Separazione di Responsabilità: Meccanico vs Giudizio (FEAT-003-D vs FEAT-003-N)

**In questa feature (deterministica):**
- Struttura del wiki.
- Convenzioni formali (frontmatter, naming, wikilink).
- Ricerca di lavoro pendente (mtime-based).
- Lint meccanico (link rotti, orfani, frontmatter).
- Enumerazione e idempotenza di registri/indice.

**Fuori scope (FEAT-003-N, metà LLM):**
- Contenuto delle pagine (record, ingest, distillazione).
- Giudizio semantico (contraddizioni, obsolescenza, relevance).
- Gate al commit (controllo git).

**Questa linea è netta e vincolante:** il nucleo è una **libreria meccanica**, consumabile anche da agenti non-LLM.

## Testing

### Fixture Nuova: Ospite Finto `doc_only_host`

Per dimostrare SC-001 (host-agnosticità):

```
tests/fixtures/doc_only_host/
├── wiki.config.toml           # profilo diverso (solo-doc, lingua it, source_dirs diversi)
├── wiki/
│   ├── index.md
│   ├── log.md
│   └── concepts/
│       └── esempio.md
└── doc_source_1/
    └── docs/                   # cartella-sorgente configurata (no src/, specs/)
```

Lo **stesso nucleo** produce scansioni/lint coerenti con questa config, senza cambi al codice.

### Test Suite (8 test, 44 verdi)

- **unit:** profile, frontmatter, scan, lint, collect, structure, registry.
- **Offline F.I.R.S.T.:** repo finto in `tmp_path`, niente rete.
- **Cloud marker** (`pytest -m "not cloud"`): tutti i test passano senza Azure/cloud.

## Punti Aperti Segnalati

### (1) Import package-root — VERIFICATO NON-PROBLEMA (2026-06-05)

Si era temuto che `sertor_core/__init__.py` (importando `composition`) caricasse `chromadb` a ogni import. **Verifica empirica:** `import sertor_core` e `import sertor_core.wiki_tools.scan` **non** caricano `chromadb` (gli SDK pesanti sono importati lazy *dentro* le `build_*`, Clean Architecture). Chromadb si carica solo invocando l'operazione `index`. Nessun intervento necessario.

### (2) Link rotti scoperti dal lint — CORRETTI (2026-06-05)

Il lint dello strumento ha scoperto link rotti reali (auto-referenziale): in `syntheses/chiusura-prototipo-dogfooding.md` un wikilink al target `architettura-attuale` (pagina inesistente) — corretto. Nota: il lint meccanico segnala anche i wikilink usati come *esempi* dentro code-span (la sintassi documentata): limitazione nota → possibile miglioria futura = ignorare i code-span.

### (3) CLI: crash su console non-UTF-8 — CORRETTO (2026-06-05)

`collect` crashava (`UnicodeEncodeError` su `→`) stampando JSON su console Windows cp1252. Risolto forzando UTF-8 su stdout/stderr nella CLI (host-agnostico: niente crash sull'ospite).

## Conformità Costituzionale

### Constitution Check Completo (10/10 ✅)

| Principio | Esito | Note |
|-----------|-------|------|
| **I — Dipendenze verso l'interno (NON-NEGOZIABILE)** | ✅ PASS | wiki_tools dipende solo da config/, domain/errors, observability/; import lazy del facade; zero SDK provider nel body. |
| **II — Boundary & local-first** | ✅ PASS | Zero nuove dipendenze esterne; tutto in locale; offline per costruzione. |
| **III — YAGNI** | ✅ PASS | Stdlib + tomllib; regex per frontmatter; modulo piccolo per operazione (SRP). |
| **IV — Errori espliciti (NON-NEGOZIABILE)** | ✅ PASS | ConfigError su config assente/malformata; niente None silenzioso; stato coerente sempre. |
| **V — Testabilità** | ✅ PASS | Unit offline F.I.R.S.T.; repo finto; SC-004 lint rileva 100% difetti iniettati, 0 falsi positivi. |
| **VI — Idempotenza** | ✅ PASS | Read-only → idempotent; init non-distruttivo; id stabile = path relativo. |
| **VII — Leggibilità** | ✅ PASS | Naming di dominio (scan, lint, collect, structure). |
| **VIII — Configurabilità centralizzata** | ✅ PASS | Tutta la specificità in wiki.config.toml; nessun default hard-coded. |
| **IX — Osservabilità** | ✅ PASS | Log strutturati via observability.logging; operazione, profilo, conteggi, esiti. |
| **X — Host-agnostico (NON-NEGOZIABILE)** | ✅ PASS | SC-001 dimostra: stesso codice su code+doc e doc-only, solo config diversa. |

**Complexity Tracking:** Vuoto (zero violazioni).

## Integrazione e Prossimi Passi

### Hook `wiki-pending-check.ps1` — Thin Wrapper Refactorizzato

L'hook di controllo lavoro pendente diventa un **thin wrapper** sulla CLI `sertor-wiki-tools scan`:

```powershell
$result = python -m sertor_core.wiki_tools scan --config wiki.config.toml --json | ConvertFrom-Json
$pending = $result.pending
# emit promemoria se $pending > 0
```

### Interconnessione con FEAT-003-N (LLM Wiki — TODO)

FEAT-003-D **fornisce i mattoni meccanici:**
- Contratti JSON versionati per le operazioni.
- Enumerazione pagine + metadati (no corpo).
- Ricerca di lavoro pendente.
- Lint meccanico.

FEAT-003-N **costruisce sopra:**
- Ingestion (brief → record, ingest, query).
- Distillazione (giudizio LLM).
- Lint semantico (contraddizioni, obsolescenza).
- Indicizzazione nel RAG con contratti.

**Divisione netta:** determinismo ↔ giudizio, separabili e ricomponibili.

## Artefatti

### Codice

- **Libreria:** `src/sertor_core/wiki_tools/` (11 moduli: profile, frontmatter, contracts, scan, structure, lint, collect, registry, indexing, __main__, __init__)
- **Config:** `wiki.config.toml` (profilo host di Sertor, dogfooding)
- **Fixture:** `tests/fixtures/doc_only_host/` (ospite finto per SC-001)
- **Console-script:** `sertor-wiki-tools` (registrato in `pyproject.toml`)

### Documentazione

- **Spec:** `specs/006-nucleo-wiki-deterministico/spec.md`
- **Plan:** `specs/006-nucleo-wiki-deterministico/plan.md`
- **Data-model:** `specs/006-nucleo-wiki-deterministico/data-model.md`
- **Contratti:** `specs/006-nucleo-wiki-deterministico/contracts/json-contracts.md`
- **Quickstart:** `specs/006-nucleo-wiki-deterministico/quickstart.md`
- **Tasks:** `specs/006-nucleo-wiki-deterministico/tasks.md`

### Test

- **8 test suite:** `tests/unit/test_wiki_tools_*.py`
- **44 test verdi, ruff clean, Constitution Check 10/10 ✅**

## Linkage

- **Dipende da:** [[costituzione-v1]] (Principio X), [[sistema-wiki-fonte-unica]] (playbook consolidato)
- **Precede:** [[missione-visione-host-agnosticita|Missione/Vision host-agnosticità]] (realizzazione concreta)
- **Collabora con (futuro):** FEAT-003-N (LLM Wiki, giudizio semantico)
- **Consumata da:** Hook `wiki-pending-check.ps1` (refactorizzato come thin wrapper CLI)
