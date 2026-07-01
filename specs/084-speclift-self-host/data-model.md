# Data Model — Self-hosting di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` · **Fase**: 1 (Design)

> **Rigenerato al design MCP-skill.** Le entità riflettono lo **swap del solo locator** (rimozione
> dell'adapter CLI, aggiunta dell'adapter alimentato dall'evidenza dell'agente) e l'interfaccia
> evidenza agente→SpecLift.

**Natura.** Feature **strutturale/di integrazione**: SpecLift porta il proprio dominio puro
(`domain/models.py`: `Quota`, `Hunk`, `Changeset`, `EvidenceItem`, `Anchor`, `Symbol`, `TestRef`,
`SpecLiftReport`, …) **invariato**. Le "entità" rilevanti sono gli **artefatti di integrazione** + lo
**swap dell'adapter di localizzazione** + l'**interfaccia evidenza**. Nessuna nuova entità entra in
`sertor_core` (byte-identico — Principio XI).

---

## Entità di integrazione

### E1 — Membro del workspace `packages/speclift`
Copia vendorata self-contained del pacchetto `speclift`.

| Attributo | Valore | Fonte / vincolo |
|-----------|--------|-----------------|
| Percorso | `packages/speclift/` | FR-001/REQ-001 |
| Build backend | `hatchling`, `packages = ["src/speclift"]` | fedele upstream |
| Layout | `src/speclift/{cli,pipeline,config,serialize,observability}.py` + `domain/` + `adapters/` + `stages/` + `skills/speclift/SKILL.md` | recon §3 |
| `requires-python` | `>=3.11` (era `>=3.12`) | D-4, FR-018 |
| Dipendenze runtime | `[]` (era `["jsonschema>=4.0"]`) | D-2, RNF-2 |
| Dipendenze dev | `["pytest>=8.0","ruff>=0.6","jsonschema>=4.0"]` | D-2 |
| Versione | `0.1.0` **statica** | D-8 |
| Dipendenze da altri membri | **nessuna** (zero import `sertor_core`, zero SDK MCP) | FR-012/013, CS-3/CS-5 |
| Entry point | `speclift = "speclift.cli:main"` | fedele upstream |

**Invarianti.** Nessun ciclo (E1 non dipende da alcun membro). `uv sync --all-packages` risolve pulito.
`sertor-core` invariato.

### E2 — Nota di provenienza (`packages/speclift/VENDORING.md`)
Artefatto ispezionabile: stato upstream + divergenze intenzionali.

| Campo | Contenuto |
|-------|-----------|
| `upstream_repo` | `https://github.com/themetriost/Sinthari` |
| `upstream_commit` | `be4da28` (`master`, PR #5) |
| `upstream_version` | `0.1.0` |
| `vendored_at` | 2026-07-01 |
| `handoff` | first-party, stessa org `themetriost` |
| `upstream_license` | **assente** al vendoring (finding, D-7) — copia integrata sotto MIT Sertor |
| `divergences[]` | (1) `jsonschema` runtime→dev (D-2); (2) `requires-python`/`ruff target` 3.12→3.11 (D-4); (3) **swap del locator**: `rag_sertor.py`+`SERTOR_RAG_VEHICLE` **rimossi**, `AgentEvidenceLocator` aggiunto (D-3); (4) `cli.py` `bundle` += `--candidates-out`/`--evidence` (D-3); (5) `EvidenceInputError` exit 6 (D-3); (6) `serialize.py` += candidates/evidence helper (D-3); (7) `test_rag_sertor.py` rimosso, `test_agent_evidence.py` aggiunto (D-3/D-6); (8) `[tool.ruff]` proprio + escluso dal ruff di root (D-5); (9) `LICENSE` MIT aggiunta (D-7); (10) SKILL.md esteso (orchestrazione MCP, D-9) |

**Invariante (FR-003/REQ-003).** A ogni re-vendoring: aggiornare `upstream_commit`/`upstream_version`/
`vendored_at` e riapplicare/aggiornare `divergences[]` — mai lasciarli stantii. *(Il design MCP amplia
`divergences[]` rispetto al design CLI: costo di re-vendoring più alto, tutto tracciato.)*

### E3 — Adapter `AgentEvidenceLocator` (lo swap del locator)
Implementazione **alimentata** della porta `EvidenceLocator`, in sostituzione dell'adapter CLI rimosso.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Locus | `adapters/agent_evidence.py` (NUOVO) | D-3 |
| Porta implementata | `EvidenceLocator` (`domain/ports.py:31-41`), strutturale | invariata |
| `locate_symbols(file_path, identifiers, snippet)` | `self._symbols.get(file_path, [])` | ricalca `FakeLocator` |
| `locate_tests(symbol)` | `self._tests.get(symbol.name, [])` | ricalca `FakeLocator` |
| Fonte dati | artefatto JSON prodotto dall'agente (E5), letto/validato a `__init__` | contratto E5 |
| Sostituisce | `SertorRagLocator`/`adapters/rag_sertor.py` — **RIMOSSO** (D-3) | grep: importato solo da `pipeline.py`+`test_rag_sertor` |
| Fail-loud | file assente/illeggibile/malformato → `EvidenceInputError` (E7) | FR-010/REQ-013 |

**Invariante.** Non esegue query di retrieval live (Principio XI/D↔N): riceve l'evidenza già localizzata
dall'agente. Lo stadio `locate_evidence` (`stages/locate_evidence.py`) resta **invariato** (chiama solo la
porta); i suoi 8 test restano verdi con l'adapter reale al posto del `FakeLocator`.

### E4 — Localization request (candidati in uscita)
Ciò che *esce* da SpecLift per dire all'agente **cosa** localizzare (da `parse_diff`).

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Prodotto da | `speclift bundle <ref> --candidates-out <PATH>` | D-3, `cli.py` (nuovo flag) |
| Pipeline | `ingest → parse_diff → filter_sources` (funzione `emit_candidates`, no locator) | `pipeline.py` (nuovo) |
| Serializzato da | `serialize.changeset_to_candidates_dict(changeset, excluded)` | D-3 (nuovo) |
| Forma | `{changeset_ref, files:[{path, hunks:[{candidate_identifiers, snippet}]}], excluded_sources}` | contratto Lato 1 |
| Origine dati | `Hunk.candidate_identifiers` (`domain/models.py:47`) | invariante `parse_diff` |
| Determinismo | non tocca il RAG; funziona a indice assente | RNF-4 |

### E5 — Interfaccia evidenza agente→SpecLift (evidenza in ingresso)
Il canale esplicito e ispezionabile con cui l'agente consegna l'evidenza localizzata (REQ-009/FR-006).

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Prodotto da | l'**agente** dopo il retrieval MCP `search_code` | skill (D-9) |
| Consumato da | `speclift bundle <ref> --evidence <PATH>` → `AgentEvidenceLocator` (E3) | D-3 |
| Forma | `{changeset_ref, symbols:{file_path:[Symbol]}, tests:{symbol_name:[TestRef]}}` | contratto Lato 2 |
| Riuso di dominio | `Symbol`/`TestRef` (`domain/models.py:88-108`); de-serializza con `_symbol_from`/`_test_from` | zero schema nuovo |
| Chiavi | `symbols` per `file_path`, `tests` per nome simbolo | identico al `FakeLocator` |
| Collocazione | file temporaneo (es. `<TMP>/speclift-evidence-input.json`) accanto agli artefatti del sandwich | D-3 |
| `line` dei simboli | `0` (search_code non dà la riga; l'àncora usa le righe dell'hunk) | invariante upstream |

**Invariante (REQ-009).** Interfaccia **documentata e ispezionabile** (`contracts/agent-evidence-interface.md`),
mai una convenzione implicita. Fail-loud su non-conformità (E7).

### E6 — Skill dogfood estesa (`.claude/skills/speclift/SKILL.md`)
Copia host-agnostica **estesa** per orchestrare il retrieval via MCP.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Percorso dogfood | `.claude/skills/speclift/SKILL.md` | FR-007/REQ-010 |
| Sorgente vendorato | `packages/speclift/skills/speclift/SKILL.md` | D-9 |
| Passi self-host (NUOVI) | candidati (`bundle --candidates-out`) → **localizza via MCP `search_code`** → scrivi evidenza (E5) → `bundle --evidence` | D-9, FR-007 |
| Passi upstream (invariati) | leggi bundle → scrivi EARS → `assemble` | SKILL.md upstream |
| Host-agnostica (forma) | sì: no path-assistente, no slash-command, no nome-modello | FR-008/REQ-011 |
| Targeting Sertor (contenuto) | nomina il tool MCP `search_code` (vehicle di Sertor, non dell'ospite) — confine dichiarato | Princ. X, research D-9 |
| Fail-loud MCP | «se `search_code` erra → fermati, nomina componente + rimedio `sertor-rag index .`» | FR-009/REQ-012 |

### E7 — Errore evidenza malformata `EvidenceInputError`
Nuovo fail-loud introdotto dal design MCP (l'evidenza dell'agente può essere malformata).

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Tipo | `EvidenceInputError(SpecLiftError)` (NUOVO) | `domain/errors.py` |
| Exit code | `6` (1–5 occupati) | `domain/errors.py` |
| Trigger | artefatto evidenza assente/illeggibile · chiavi mancanti · tipi non conformi | FR-010/REQ-013 |
| Punto | `AgentEvidenceLocator.__init__` (validazione all'ingresso) | E3 |
| Mai | ripiego su evidenza vuota/di default né àncora fabbricata | Principio XII |

**Invariante.** Il fail-loud **MCP/indice giù** (REQ-012) NON è qui: vive nella **skill** (l'agente esegue
`search_code`, riceve errore, si ferma) — conseguenza del design (SpecLift non tocca più il RAG). Il moat
(verifica àncore sul **filesystem**) resta l'ultima rete a valle.

### E8 — Suite di test vendorata
Integrata nell'infrastruttura CI del workspace.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Percorso | `packages/speclift/tests/{contract,integration,unit}` | recon §struttura |
| Divergenza | **−`test_rag_sertor.py`** (8 test, adapter rimosso) **+`test_agent_evidence.py`** | D-3/D-6 |
| Conteggio | upstream **~106** (`grep -rc def test` = 106) → netto post-swap; esito richiesto = **verde** | D-6, FR-011 |
| Marker | `contract`, `integration` (nel pyproject di speclift) | D-6, evita conflitto col root |
| Invocazione CI | step dedicato `uv run pytest packages/speclift/tests -m "not cloud"` | D-6 |
| Verifica 3.11 | `uv run --python 3.11 pytest` (accettazione FR-019) | D-4 |
| Offline | sì (contract usa jsonschema dev; integration usa git-fixture locale; **nessun** RAG toccato) | D-6, RNF |

---

## Modifiche ai file di configurazione del workspace (stato, non entità)

| File | Modifica | Riferimento |
|------|----------|-------------|
| `pyproject.toml` (root) | `[tool.uv.workspace] members += "packages/speclift"` | FR-001 |
| `pyproject.toml` (root) | `[tool.ruff] extend-exclude += "packages/speclift"` | D-5 |
| `uv.lock` | rigenerato da `uv sync --all-packages` | CS-5 |
| `.github/workflows/ci.yml` | step `Tests — speclift` (+ opz. `Lint — speclift`) | D-6/D-5 |
| `packages/speclift/pyproject.toml` | proprio `[tool.ruff]` (110/`SIM`/`py311`) + `[tool.pytest.ini_options]` (marker) | D-5/D-6 |

**`sertor-core` / `src/sertor_core/**` / `src/sertor_mcp/**` / `packages/{sertor,sertor-install-kit,sertor-flow}`:
INVARIATI** (zero modifica come conseguenza della feature — CS-3, RNF-3/RNF-7).
