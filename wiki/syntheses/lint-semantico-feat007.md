---
title: FEAT-007 Lint Semantico — Rilevazione Obsolescenza e Contraddizioni nel Wiki
type: synthesis
tags: [FEAT-007, wiki, manutenzione, lint, LLM, semantica, provenance]
created: 2026-06-04
updated: 2026-06-04
provenance: generated
sources: ["specs/006-wiki-lint-semantico/plan.md", "specs/006-wiki-lint-semantico/requirements.md", "src/sertor_core/wiki/semantic.py", "src/sertor_core/wiki/conventions.py", "tests/test_wiki_semantic.py"]
---

# FEAT-007: Lint Semantico del Wiki — Rilevazione e Proposta Fix

## Panoramica

**Estensione semantica di FEAT-007 (Skill: mantenere il wiki):** nuovo modulo `src/sertor_core/wiki/semantic.py` implementa un **linter semantico** che confronta le **claim del wiki** col **codice reale** (via facade di retrieval) e **coerenza interna** tra pagine, rilevando obsolescenza, contraddizioni e lacune di copertura. Sola lettura. Conforme a [[costituzione-v1]] (Principi I–IX).

## Cosa è stato fatto

### Modulo principale: `semantic_lint()`

Firma:
```python
def semantic_lint(
    root: Path,
    llm: LLMProvider,
    facade: RetrievalFacade,
    *,
    threshold: float = 0.5,
    k_code: int = 3,
    max_pages: int | None = None,
    pages: list[str] | None = None,
) -> SemanticReport
```

**Funzionalità:**
1. **Obsolescenza vs codice:** per ogni claim in una pagina, recupera contesto dal RAG (k=`k_code`); LLM giudica se claim e codice sono allineati
2. **Coerenza interna:** confronta claim tra pagine interconnesse (via wikilink `[[...]]`)
3. **Lacune:** identifica claim non supportate da nessun contesto di codice
4. **Sommari stantii:** rileva pagine generate il cui sommario (prima riga dopo frontmatter) è scaduto

**Parametri:**
- `threshold` (default 0.5): soglia di severità per il gate pass/fail
- `k_code`: numero di chunk da recuperare dal RAG per supporto codice (default 3)
- `max_pages` / `pages`: limiti di scansione (MVP: trial su 6/17 pagine in ~85 s/pagina)

**Entità di output:**

- `Severity` (ordinale): LOW, MEDIUM, HIGH
- `SemanticIssueKind`: enum con 4 tipi
  - `OBSOLETE_VS_CODE` — claim contraddice/diverge da codice reale
  - `INTERNAL_CONTRADICTION` — claim contraddice un'altra pagina
  - `COVERAGE_GAP` — claim non ha contesto di codice supportivo
  - `STALE_SUMMARY` — sommario di pagina generata è obsoleto
- `SemanticIssue`: kind + severity + claim + reasoning LLM + suggerimenti
- `SemanticReport`: lista issue + flag `ok` (True se max severity ≤ threshold) + stats (cobertura, pagine senza contesto)

### Provenienza pagine: `provenance` frontmatter

Nuovi campi in `conventions.py`:

```yaml
provenance: generated | curated  # generata da tool LLM vs curata a mano
```

Funzioni ausiliarie:
- `read_provenance(page_path) -> Provenance` — legge il campo (default: **curated**, sicuro)
- `mark_provenance(page_path, provenance, overwrite=False)` — marca la pagina (non distruttivo)
- Integrato in `distill_artifact()`: pagine create dallo script sono automaticamente marcate `generated`

### Generazione proposte: `propose_fixes()`

```python
def propose_fixes(report: SemanticReport) -> list[FixProposal]
```

**Politica di auto-fix:**
- **Solo pagine `provenance: generated`** (riscritture chirurgiche)
- **Non scrive file** (phase pre-commit dichiarata); genera proposte YAML strutturate:
  - `action: rewrite_claim | delete_page | add_backlink`
  - `page_path`, `section`, `old_text`, `new_text`, `reasoning`
- **Pagine curate:** report solo (nessuna proposta)

### Degradazione senza LLM

Se `llm` non è configurato (LLMNotConfiguredError), il report contiene:
- `skipped=True`
- `severity=NONE` (gate sempre passa)
- Messaggio esplicito: "lint semantico degradato a strutturale; indicizzare contesto di codice per migliorare"

Conseguenza: **local-first mantenuto** (gira con Ollama); Azure opzionale per migliore qualità.

### Robustezza

- **Parsing JSON difensivo:** il modello LLM potrebbe restituire JSON malformato; catch + retry con template più semplice
- **Gate pass/fail:** `report.ok = True` se `max(severity in report) ≤ threshold`
- **Override dichiarato:** fase pre-commit può scegliere di procedere anche con gate rosso (override su decision gate, policy esplicita in Phase 0–1 SpecKit)

## Requisiti implementati (EARS)

**Gruppo H — Estensione semantica FEAT-007, requisiti REQ-070..098:**

| REQ | Titolo | US | Stato |
|-----|--------|----|----|
| REQ-070 | `semantic_lint()` rileva claim vs codice | US1 | ✅ P1 |
| REQ-071 | Confronto coerenza interna pagine | US1 | ✅ P1 |
| REQ-072 | Identificazione lacune copertura | US1 | ✅ P1 |
| REQ-073 | Gate pass/fail su threshold severità | US1 | ✅ P1 |
| REQ-075 | `provenance` campo frontmatter | US2 | ✅ P1 |
| REQ-076 | Read/mark/distill provenienza non-distruttivo | US2 | ✅ P1 |
| REQ-077 | `propose_fixes()` su pagine generated | US4 | ✅ forma "proposta" |
| REQ-093 | LLM locale/Ollama funzionante | US1 | ✅ Ollama qwen3:30b-a3b dogfooded |
| REQ-098 | Contraddizioni tra source esterne | US1 | ✅ integrato in coerenza interna |

**Rinviati (dichiarati in task):**
- US3 (watermark git) → T100-T103 incrementale
- US5 (applicazione working tree + hook pre-commit) → T100-T103

## Testing

**Test suite (13 nuovi):**

- `test_wiki_semantic_obsolete_vs_code()` — obsolescenza rilevata
- `test_wiki_semantic_internal_contradiction()` — contraddizione tra pagine
- `test_wiki_semantic_coverage_gap()` — lacuna copertura
- `test_wiki_semantic_stale_summary()` — sommario pagina generata scaduto
- `test_wiki_semantic_report_severity()` — calcolo severity aggregato
- `test_wiki_semantic_gate_pass_fail()` — gate on threshold
- `test_wiki_semantic_degraded_no_llm()` — degrado gradevole senza LLM
- `test_wiki_semantic_json_parse_robustness()` — robustezza JSON
- `test_wiki_provenance_read_default()` — default curated
- `test_wiki_provenance_mark()` — marking non-distruttivo
- `test_wiki_provenance_distill_artifact()` — distill marca generated
- `test_wiki_semantic_fixes_proposal_generated_only()` — auto-fix gated
- `test_wiki_semantic_fixes_proposal_structure()` — struttura proposta YAML

**Mock LLM:** `ScriptedLLM` per test deterministici (senza Azure/Ollama). Suite totale **137 verdi**, ruff pulito, Constitution Check **9/9**.

## Dogfooding (2026-06-04)

Esecuzione sul **wiki di produzione** con Ollama **qwen3:30b-a3b** su 6/17 pagine (~85 s/pagina).

**Risultati:**

1. ✅ **Run end-to-end funzionante:** lint executed, report generato, severity calcolata
2. ⚠️ **Corpus di codice locale non indicizzato:** `.index-production` contiene vettori Azure 3072-dim per corpus produzione, ma non per `src/` in collezione nomic (768-dim Ollama). **Conseguenza:** controllo obsolescenza-vs-codice degradato a **sola coerenza interna** (niente contesto codice). **Miglioramento:** aggiunta segnalazione esplicita `pages_without_code_context` nel report per evitare troncamento silenzioso
3. ⚠️ **Modello locale 30B rumoroso:** contraddizioni rilevate sono dubbie (false positive lievi). **Conferma perché auto-fix è gated/assistito:** proposte generate ma mai applicate automaticamente; revision umana richiesta

**Lezione:** indicizzazione incrementale (FEAT-009) dovrà garantire che il corpus di codice locale sia sempre disponibile per lint semantico; altrimenti il controllo rimane superficiale.

## Conformità e gate

- ✅ **Constitution Check 9/9:** Principi I–IX confermati
  - **Principio I (core autonomo):** modulo indipendente, zero import SDK
  - **Principio VI (non-distruttività):** report-only; proposte solo generate, non applicate
  - **Principio IX (osservabilità):** logging strutturato, severity esplicita
- ✅ **Spec SpecKit:** EARS group H convertiti → `specs/006-wiki-lint-semantico/requirements.md`
- ✅ **Processo SpecKit:** requisiti → spec → plan → tasks → implementation
- ✅ **Phase pre-commit dichiarata:** override gate possibile con decision log esplicito

## Scope MVP vs post-MVP

**MVP (fatto):**
- Rilevazione P1 (US1: obsolescenza + coerenza + lacune + sommari)
- Provenienza P1 (US2: marcatura non-distruttiva)
- Proposte forma "proposta" (US4: YAML strutturato, niente write)

**Post-MVP (rinviato a T100-T103):**
- US3: watermark git (quale commit ha generato la pagina)
- US5: applicazione su working tree + hook pre-commit (scrittura file) + cancellazione

## Riferimenti incrociati

- **Skill wiki:** [[skill-wiki-feat003]] (crea + indicizza)
- **Manutenzione wiki (fase 1):** [[manutenzione-wiki-feat007]] (lint strutturale + distill)
- **Costituzione:** [[costituzione-v1]] (Principi I–IX vincolanti)
- **Roadmap:** [[roadmap]] (FEAT-007 stato aggiornato)

## Prossimi passi

1. **Incrementale + watermark (US3):** git metadata per tracciare quale commit ha generato una pagina
2. **Applicazione hook pre-commit (US5):** auto-apply su pagine generated o richiesta umana; gate dichiarato su Constitution Check
3. **FEAT-009 prioritaria:** refresh incrementale indici + indicizzazione locale corpus sorgenti per supportare lint semantico pieno
4. **Miglioramento modello:** sperimentare Azure OpenAI o Ollama modelli più grandi per ridurre false positive
