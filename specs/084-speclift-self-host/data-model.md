# Data Model — Self-hosting di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` · **Fase**: 1 (Design)

**Natura.** Questa feature è **strutturale/di integrazione**, non introduce entità di dominio runtime
nuove: SpecLift porta con sé il proprio dominio puro (`domain/models.py`: `Quota`, `Hunk`, `Changeset`,
`EvidenceItem`, `Anchor`, `Symbol`, `TestRef`, `SpecLiftReport`, …) **invariato** dal vendoring. Le
"entità" rilevanti qui sono gli **artefatti di integrazione nel workspace** e la loro configurazione.
Nessuna nuova entità entra in `sertor_core` (byte-identico — Principio XI).

---

## Entità di integrazione

### E1 — Membro del workspace `packages/speclift`
Copia vendorata self-contained del pacchetto `speclift`.

| Attributo | Valore | Fonte / vincolo |
|-----------|--------|-----------------|
| Percorso | `packages/speclift/` | FR-001/REQ-001 |
| Build backend | `hatchling`, `packages = ["src/speclift"]` | fedele upstream |
| Layout | `src/speclift/{cli,pipeline,config,serialize,observability}.py` + `domain/` + `adapters/` + `stages/` + `skills/speclift/SKILL.md` | recon §3 |
| `requires-python` | `>=3.11` (era `>=3.12`) | D-4, FR-017 |
| Dipendenze runtime | `[]` (era `["jsonschema>=4.0"]`) | D-2, RNF-2 |
| Dipendenze dev | `["pytest>=8.0","ruff>=0.6","jsonschema>=4.0"]` | D-2 |
| Versione | `0.1.0` **statica** (non `dynamic`/`/VERSION`) | D-8 |
| Dipendenze da altri membri | **nessuna** (zero import `sertor_core`) | FR-012/013, CS-3/CS-5 |
| Entry point | `speclift = "speclift.cli:main"` | fedele upstream |

**Invarianti.** Nessun ciclo di dipendenze (E1 non dipende da alcun membro). `uv sync --all-packages`
risolve pulito. `sertor-core` invariato.

### E2 — Nota di provenienza (`packages/speclift/VENDORING.md`)
Artefatto ispezionabile che documenta lo stato upstream e le divergenze intenzionali.

| Campo | Contenuto |
|-------|-----------|
| `upstream_repo` | `https://github.com/themetriost/Sinthari` |
| `upstream_commit` | `be4da28` (`master`, PR #5) |
| `upstream_version` | `0.1.0` |
| `vendored_at` | 2026-07-01 |
| `handoff` | first-party, stessa org `themetriost` |
| `upstream_license` | **assente** al momento del vendoring (finding, D-7) — copia integrata sotto MIT Sertor |
| `divergences[]` | (1) `jsonschema` runtime→dev (D-2); (2) `requires-python`/`ruff target` 3.12→3.11 (D-4); (3) vehicle `SERTOR_RAG_VEHICLE` → `("uv","run","sertor-rag")` (D-3); (4) messaggio `RagUnavailableError` con rimedio `sertor-rag index .` (D-3, Should); (5) `[tool.ruff]` proprio + escluso dal ruff di root (D-5); (6) `LICENSE` MIT aggiunta (D-7); (7) versione statica (D-8) |

**Invariante (FR-003/REQ-003).** A ogni re-vendoring da uno stato upstream più recente, `upstream_commit`/
`upstream_version`/`vendored_at` e la lista `divergences[]` vanno aggiornati — mai lasciati stantii.

### E3 — Configurazione del vehicle RAG
Il valore che fa invocare a SpecLift il RAG alla **root** Sertor.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Locus | `packages/speclift/src/speclift/config.py`, costante `SERTOR_RAG_VEHICLE` | `config.py:27` |
| Valore self-host | `("uv", "run", "sertor-rag")` | FR-004/REQ-007 |
| Valore upstream | `("uv", "run", "--project", ".sertor", "sertor-rag")` | divergenza tracciata (E2) |
| Meccanismo | patch della costante (D-3, opzione a) | esplicito/ispezionabile (FR-005) |
| Override runtime | **nessuno** (zero-config: funziona dalla root senza flag/env) | FR-006/REQ-009 |

**Invariante.** La configurazione è in `config.py` (config centralizzata, non nel corpo della capacità)
→ la skill resta host-agnostica (Principio VIII/X). La generalizzazione a env var/config-all'install è
**FEAT-002**.

### E4 — Errore RAG-unavailable azionabile
Il fallimento fail-loud sul prerequisito RAG (comportamento upstream, esteso nel messaggio).

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Tipo | `RagUnavailableError(SpecLiftError)` | `domain/errors.py` |
| Exit code | `3` | `cli.py:8-10`, `contracts/cli.md:37-41` |
| Trigger | vehicle exit≠0 · output non-JSON · array non-lista · indice mancante | `rag_sertor.py:87-99,120-124` |
| Messaggio (Must) | esplicito su stderr, nomina la causa | FR-007/REQ-012 (upstream **invariato**) |
| Rimedio (Should) | raccomanda `sertor-rag index .` dalla root | FR-008/REQ-013 (divergenza D-3, E2 #4) |

**Invariante (Principio XII).** Mai degrado silenzioso né risultati vuoti/fabbricati come se la query
fosse riuscita. Gli stadi che **non** toccano il RAG (`ingest`/`parse_diff`/`filter_sources`) restano
operativi senza indice (RNF-4).

### E5 — Skill dogfood (`.claude/skills/speclift/SKILL.md`)
Copia host-agnostica depositata per la scoperta/invocazione dall'agente ospite.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Percorso dogfood | `.claude/skills/speclift/SKILL.md` | FR-009/REQ-010 |
| Sorgente vendorato | `packages/speclift/skills/speclift/SKILL.md` | D-9 |
| Host-agnostica | sì (no path assistente, no slash-command, no nome-modello) | FR-010/REQ-011, `SKILL.md` verificata |
| Onestà code-graph | la skill **non** cita `find_symbol`/`who_calls` (già pulita) | D-9 |
| Sync sorgente↔dogfood | manuale/one-shot; guardia = FEAT-002 | D-9 |

### E6 — Suite di test vendorata (104 test)
Integrata nell'infrastruttura CI del workspace.

| Attributo | Valore | Fonte |
|-----------|--------|-------|
| Percorso | `packages/speclift/tests/{contract,integration,unit}` | recon §struttura |
| Marker | `contract`, `integration` (nel pyproject di speclift) | D-6, evita conflitto con root `cloud`/`integration` |
| Invocazione CI | step dedicato `uv run pytest packages/speclift/tests -m "not cloud"` | D-6, `ci.yml` per-pacchetto |
| Verifica 3.11 | `uv run --python 3.11 pytest` (accettazione di FR-018) | D-4 |
| Offline | sì (contract usa jsonschema; integration usa git-fixture locale) | D-6, RNF |

---

## Modifiche ai file di configurazione del workspace (non entità, ma stato)

| File | Modifica | Riferimento |
|------|----------|-------------|
| `pyproject.toml` (root) | `[tool.uv.workspace] members += "packages/speclift"` | FR-001 |
| `pyproject.toml` (root) | `[tool.ruff] extend-exclude += "packages/speclift"` | D-5 |
| `uv.lock` | rigenerato da `uv sync --all-packages` | CS-5 |
| `.github/workflows/ci.yml` | step `Tests — speclift` (+ opz. `Lint — speclift`) | D-6/D-5 |
| `packages/speclift/pyproject.toml` | proprio `[tool.ruff]` (110/`SIM`/`py311`) + `[tool.pytest.ini_options]` (marker) | D-5/D-6 |

**`sertor-core` / `src/sertor_core/**` / `packages/{sertor,sertor-install-kit,sertor-flow}`: INVARIATI**
(zero modifica come conseguenza della feature — CS-3, RNF-3/RNF-7).
