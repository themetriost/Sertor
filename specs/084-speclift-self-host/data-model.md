# Data Model — Self-hosting di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` · **Fase**: 1 (Design)

> **Rigenerato al design vendoring-puro / pluggable.** Le entità sono ora **quelle upstream**
> (`ProvidedEvidenceLocator`, `located.json`, `changeset.json`, `query_keys`), adottate tale-e-quali da
> Sinthari `5ee6fc1`. Non esiste più un `AgentEvidenceLocator` nostro né un `EvidenceInputError`/exit 6.

**Natura.** Feature **strutturale/di integrazione**: SpecLift porta il proprio dominio puro
(`domain/models.py`: `Quota`, `Hunk`, `Changeset`, `EvidenceItem`, `Anchor`, `Symbol`, `TestRef`,
`SpecLiftReport`, …) **invariato e verbatim**. Le "entità" rilevanti sono gli **artefatti di
integrazione** + gli **artefatti del three-gear flow upstream** che il dogfood usa. Nessuna nuova entità
entra in `sertor_core` (byte-identico — Principio XI).

---

## Entità di integrazione (nostre)

### E1 — Membro del workspace `packages/speclift`
Copia vendorata **verbatim** (src/**) del pacchetto `speclift` @ `5ee6fc1`.

| Attributo | Valore | Fonte / vincolo |
|-----------|--------|-----------------|
| Percorso | `packages/speclift/` | FR-001/REQ-001 |
| Build backend | `hatchling`, `packages = ["src/speclift"]` | fedele upstream |
| Layout | `src/speclift/{cli,pipeline,config,serialize,observability}.py` + `domain/{models,ports,errors,query_keys}.py` + `adapters/{git_diff,rag_sertor,provided_locator,anchor_fs,authored,ears_requirements}.py` + `stages/` + `skills/speclift/SKILL.md` | recon-pluggable §1-3 |
| `requires-python` | `>=3.11` (era `>=3.12`) — **divergenza di packaging** | D-4, FR-018 |
| Dipendenze runtime | `[]` (era `["jsonschema>=4.0"]`) — **divergenza di packaging** | D-2, RNF-2 |
| Dipendenze dev | `["pytest>=8.0","ruff>=0.6","jsonschema>=4.0"]` | D-2 |
| Versione | `0.1.0` **statica** | D-8 |
| Dipendenze da altri membri | **nessuna** (zero import `sertor_core`, zero SDK MCP) | FR-012/013, CS-3/CS-5 |
| Entry point | `speclift = "speclift.cli:main"` | fedele upstream |
| **Codice `src/**`** | **verbatim** upstream (nessun file modificato, `rag_sertor.py`/`config.py` intatti) | vendoring puro (D-1/D-3) |

**Invarianti.** Nessun ciclo (E1 non dipende da alcun membro). `uv sync --all-packages` risolve pulito.
`sertor-core` invariato.

### E2 — Nota di provenienza (`packages/speclift/VENDORING.md`)
Artefatto ispezionabile: stato upstream + divergenze **di packaging** (non di codice).

| Campo | Contenuto |
|-------|-----------|
| `upstream_repo` | `https://github.com/themetriost/Sinthari` |
| `upstream_commit` | **`5ee6fc1`** (`master`, PR #7 — versione pluggable) |
| `upstream_version` | `0.1.0` |
| `vendored_at` | 2026-07-01 |
| `handoff` | first-party, stessa org `themetriost`; `5ee6fc1` = recepimento del nostro feedback CLI→MCP |
| `upstream_license` | **assente** a `5ee6fc1` (finding, D-7) — copia integrata sotto MIT Sertor |
| `divergences[]` | (1) `jsonschema` runtime→dev (D-2); (2) `requires-python`/`ruff target` 3.12→3.11 (D-4); (3) `LICENSE` MIT aggiunta (D-7); (4) `[tool.ruff]`/`[tool.pytest]` proprio + escluso dal ruff di root (D-5/D-6). **Nessuna divergenza di codice `src/**`** (vendoring puro) |

**Invariante (FR-003/REQ-003).** A ogni re-vendoring: aggiornare `upstream_commit`/`upstream_version`/
`vendored_at` e riapplicare le 4 divergenze **di packaging** — mai lasciarle stantie. *(Il vendoring puro
riduce `divergences[]` a sole voci di packaging rispetto al design «swap»: re-vendoring più economico,
convergenza con upstream.)*

### E6 — Skill dogfood (`.claude/skills/speclift/SKILL.md`)
Copia **verbatim** host-agnostica della skill upstream (che ha già Procedura A/B).

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Percorso dogfood | `.claude/skills/speclift/SKILL.md` | FR-007/REQ-010 |
| Sorgente vendorato | `packages/speclift/skills/speclift/SKILL.md` (verbatim) | D-9 |
| Procedura A (default) | CLI-vehicle `sertor-rag` → bundle diretto (Adapter A) | SKILL.md upstream `:44-126` |
| **Procedura B (usata dal dogfood)** | `changeset` → **localizza via tool MCP (`search_code`/…)** → `bundle --changeset/--located` → autoring → assemble (Adapter B) | SKILL.md upstream `:128-181` |
| Host-agnostica (forma) | sì: no path-assistente, no slash-command, no nome-modello | FR-008/REQ-011 |
| Targeting Sertor (contenuto) | nomina i tool MCP di Sertor (vehicle di Sertor, non dell'ospite) — confine dichiarato | Princ. X, research D-9 |
| Fail-loud MCP | «se un comando/tool erra → fermati e riporta» (`:31-32`, Procedura B) | FR-009/REQ-012 |
| Estensione nostra | **NESSUNA** — upstream l'ha già scritta (recepimento feedback) | D-9 |

### E8 — Suite di test vendorata (verbatim)
Integrata nell'infrastruttura CI del workspace.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Percorso | `packages/speclift/tests/{contract,integration,unit}` | recon §struttura |
| Copia | **verbatim** (nessuna rimozione): include `test_provided_locator.py`(8), `test_query_keys.py`(5), `test_three_gear_flow.py`(3) **e** `test_rag_sertor.py`(8) | vendoring puro (D-3/D-6) |
| Conteggio | upstream **~122–123** (`grep -rc "def test"` ≈ 123; commit dichiara 122); esito richiesto = **verde** | D-6, FR-011 |
| Marker | `contract`, `integration` (nel pyproject di speclift) | D-6, evita conflitto col root |
| Invocazione CI | step dedicato `uv run pytest packages/speclift/tests -m "not cloud"` | D-6 |
| Verifica 3.11 | `uv run --python 3.11 pytest` (accettazione FR-019) | D-4 |
| Offline | sì (contract usa jsonschema dev; integration usa git-fixture locale; `test_rag_sertor` usa runner mockato; **nessun** RAG reale toccato) | D-6, RNF |

---

## Entità del three-gear flow upstream (adottate, NON reinventate)

Queste non sono "nostre": sono le entità reali dell'Adapter B upstream che il dogfood usa. Fonte di
verità = codice vendorato + `contracts/evidence-locator-port.md`.

### U1 — `ProvidedEvidenceLocator` (Adapter B, upstream)
Implementazione **alimentata** della porta `EvidenceLocator`: rilegge l'evidenza già localizzata
dall'agente, senza ricerca propria.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Locus | `adapters/provided_locator.py` (vendorato verbatim) | recon-pluggable §1 |
| `__init__(payload, *, config)` | legge `payload["symbols"]`/`["tests"]`; **nessuna validazione** (chiave assente → `[]`) | `provided_locator.py:28-31` |
| `locate_symbols(file_path, identifiers, snippet)` | query via G6 (`build_identifier_queries`); lookup su `_symbols["<file_path>::<query>"]` | `:33-40` |
| `locate_tests(symbol)` | lookup su `_tests[symbol.name]` | `:42-47` |
| Chiave simboli | **composita** `f"{file_path}::{query}"` | `:50-52` |
| De-serializzazione | `Symbol`/`TestRef` via `_symbol_from`/`_test_from` | `:55-72` |
| Coesistenza | affianca `SertorRagLocator` (Adapter A), non lo sostituisce | recon-pluggable §1 |

**Invariante.** Non esegue query di retrieval live (Principio XI/D↔N): riceve l'evidenza già localizzata
dall'agente. Lo stadio `locate_evidence` resta **invariato**.

### U2 — `changeset.json` (candidati in uscita, marcia 0)
Ciò che *esce* da SpecLift per dire all'agente **cosa** localizzare.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Prodotto da | `speclift changeset <ref> --out` (marcia 0) | `cli.py:119-168` |
| Pipeline | `ingest → parse_diff → filter_sources` (`pipeline.build_changeset`, no locator) | `pipeline.py:117-142` |
| Serializzato da | `serialize.changeset_to_dict(changeset, excluded)` | recon-pluggable §3b |
| Forma | `{version, changeset_ref, kind, files:[{path, change_type, old_path, is_binary, hunks:[{file_path, old_range, new_range, candidate_identifiers, lines}]}], excluded_sources}` | recon-pluggable §3b |
| Nota | l'hunk del changeset include **`lines`** (il diff, per far decidere all'agente) — a differenza dell'hunk del bundle | `serialize.py:186-189` |
| Determinismo | non tocca il RAG; funziona a indice assente | RNF-4 |

### U3 — `located.json` (evidenza in ingresso, prodotta dall'agente)
Il canale con cui l'agente consegna l'evidenza localizzata (adottato tale-e-quale).

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Prodotto da | l'**agente** dopo il retrieval MCP (`search_code`/…) | skill Procedura B |
| Consumato da | `speclift bundle --changeset … --located …` → `ProvidedEvidenceLocator` (U1) | `cli.py:213-230` |
| Forma | `{ "symbols": {"<file_path>::<query>": [Symbol]}, "tests": {"<symbol_name>": [TestRef]} }` | `evidence-locator-port.md:58-64` |
| Chiavi | `symbols` **composita** `file::query`; `tests` per nome-simbolo | recon-pluggable §3a |
| `changeset_ref` top-level | **assente** (a differenza della nostra `evidence.json` inventata) | recon-pluggable §3a |
| Campi obbligatori | `name`/`path` (simboli); `name`/`path`/`covers_symbol` (test); resto default | `provided_locator.py:55-72` |
| Chiave assente | `[]` onesto, non errore | `provided_locator.py:14-15` |
| Collocazione | file temporaneo (es. `<TMP>/speclift-located.json`) | SKILL.md upstream |

### U4 — `query_keys.build_identifier_queries` (regola G6 condivisa)
Modulo puro che deriva le query di localizzazione da un hunk.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Locus | `domain/query_keys.py` (vendorato verbatim) | recon-pluggable §3c |
| Firma | `build_identifier_queries(identifiers, snippet, max_queries) -> list[str]` | `query_keys.py:12` |
| Regola | identificatori deduplicati e limitati a `max_queries`; fallback alla 1ª riga snippet solo se `.isidentifier()` | `query_keys.py:18-23` |
| Condivisa da | **entrambi** gli adapter (`ProvidedEvidenceLocator` e `SertorRagLocator`) | recon-pluggable §3c/§6 |

### U5 — Exit code (adottati, NON exit 6)
Fail-loud upstream ereditato (`domain/errors.py` + `cli.py`).

| Condizione | Exit | Fonte |
|------------|------|-------|
| ref git invalido | 2 (`InvalidRefError`) | `errors.py` |
| RAG giù (solo Adapter A, non nel flow B) | 3 (`RagUnavailableError`) | `errors.py` |
| EarsAuthor giù | 4 | `errors.py` |
| bundle/contratto invalido · **evidenza malformata** | **5** (`BundleContractError`-range) | `cli.py:227-229` |
| flag-misuse (`--changeset`/`--located` incompleti o misti a `<ref>`) | 2 | `cli.py:203-208` |

**Invariante (FR-010).** L'evidenza malformata dell'agente cade nell'exit **5** upstream — **niente**
`EvidenceInputError`/exit 6 (era nostro, superato). Il fail-loud **MCP/indice giù** (FR-009) vive nella
**skill** (l'agente esegue il tool MCP, riceve errore, si ferma). Il moat (verifica àncore sul
**filesystem**) resta l'ultima rete a valle.

---

## Modifiche ai file di configurazione del workspace (stato, non entità)

| File | Modifica | Riferimento |
|------|----------|-------------|
| `pyproject.toml` (root) | `[tool.uv.workspace] members += "packages/speclift"` | FR-001 |
| `pyproject.toml` (root) | `[tool.ruff] extend-exclude += "packages/speclift"` | D-5 |
| `uv.lock` | rigenerato da `uv sync --all-packages` | CS-5 |
| `.github/workflows/ci.yml` | step `Tests — speclift` (+ opz. `Lint — speclift`) | D-6/D-5 |
| `packages/speclift/pyproject.toml` | divergenze di packaging (D-2/D-4) + `[tool.ruff]`/`[tool.pytest.ini_options]` propri | D-5/D-6 |
| `packages/speclift/{LICENSE,VENDORING.md}` | nuovi (nostri) | D-7, E2 |

**`sertor-core` / `src/sertor_core/**` / `src/sertor_mcp/**` / `packages/{sertor,sertor-install-kit,sertor-flow}`:
INVARIATI** (zero modifica come conseguenza della feature — CS-3, RNF-3/RNF-7). Il codice
`packages/speclift/src/**` è **verbatim upstream** (nessuna nostra modifica di runtime).
