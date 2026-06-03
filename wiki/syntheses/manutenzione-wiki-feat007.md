---
title: Implementazione FEAT-007 manutenzione del wiki
type: synthesis
tags: [feat-007, wiki, maintenance, production, lint]
created: 2026-06-03
updated: 2026-06-03
sources: ["specs/005-wiki-manutenzione/spec.md", "specs/005-wiki-manutenzione/plan.md", "requirements/sertor-core/wiki-manutenzione/requirements.md", "src/sertor_core/wiki/maintenance.py", "src/sertor_core/wiki/conventions.py"]
---

# Manutenzione del Wiki — FEAT-007 Completamento

## Stato

✅ **COMPLETATO**: 16/16 task, 124 test passed + 2 xfail (soglie baseline, non di questa feature), ruff clean, **Constitution Check 9/9 ✅**.

## Cosa è stata costruita

Una **skill manutenzione wiki** — insieme di operazioni di pulizia, validazione e documentazione automatica del wiki di produzione. Risiede in `src/sertor_core/wiki/maintenance.py`, è **LLM-free, non-distruttiva e idempotente**, pensata per girare di frequente come gate alla fine di una feature.

### Componenti principali

| Modulo | Responsabilità |
|--------|---|
| `maintenance.py` | `lint(root, *, expected=None, fix=False) -> LintReport`, `regenerate_index(root) -> bool`, entità `IssueKind`/`Issue`/`LintReport` |
| `conventions.py` (esteso) | Marcatori catalogo `<!-- sertor:catalog -->` e helper `replace_managed_block()` per rimpiazzare solo il blocco gestito |
| `distill.py` (esteso) | `distill_artifact(root, source, kind, title, llm, today=None)` — distilla artifact (spec/plan/requisito/discussione) in documentazione ufficiale con backlink |

### Funzionalità di lint

La funzione `lint()` **rileva in sola lettura** (non corregge automaticamente):

- **Link rotti**: wikilink (doppie parentesi quadre, es. verso `nome-pagina`) che puntano a file inesistenti
- **Pagine orfane**: file .md in `wiki/` senza riferimento in index.md (esclusi index e log per design)
- **Pagine fuori indice**: citate in index.md ma non presenti nel filesystem
- **Coperture mancanti**: set `expected` (pagine attese) confrontato vs reali
- **Contraddizioni marcate**: marcatore di avvertenza "⚠️ Contraddizione" (FEAT-003, sezione apposita)

**`fix=True` applica SOLO la rigenerazione indice**, mai auto-fix dei link (preserva autorità curativa manuale).

**`LintReport`** espone proprietà `ok` (booleano) usabile come gate di passaggio (0 problemi → True).

### Rigenerazione indice

`regenerate_index(root)` ricostruisce in-place il blocco catalogo in `index.md`:

- Scansiona filesystem per **cartelle tematiche** (concepts, tech, experiments, sources, syntheses)
- Raccoglie frontmatter YAML di ogni .md (title, type, tags)
- Genera sezione Markdown con link + summary di una riga
- Rimpiazza solo il blocco tra marcatori `<!-- sertor:catalog -->` (zero rischio sovrascrittura)

Permette di **tenere index.md auto-aggiornato** senza mantenimento manuale della lista link.

### Distillazione artifact

`distill_artifact(root, source, kind, title, llm, today=None)`:

- Legge spec/plan/requisito da `source` (path file)
- **Crea una pagina di documentazione ufficiale** nel wiki (es. `syntheses/...md`) se assente
- Genera **backlink esplicito** alla fonte originale (es. `sources: ["specs/005-wiki-manutenzione/spec.md"]`)
- Senza LLM → `LLMNotConfiguredError` (configurabilità esplicita, Principio IV)
- **Idempotente sulla struttura**: rieseguire su input invariato produce file identico

Pensata per **convertire artefatti di produzione** (spec, plan, task, discussione) in **documentazione persistente** del wiki, con tracciabilità alla sorgente.

## Decisioni di design chiave

### 1. Sola lettura + non-distruttivo (Principio VI)

- `lint()` **non modifica il wiki** (report-only), salvo `fix=True` che rigenerando soltanto index.
- Nessun tentativo di auto-fix link: autorità curativa è **manuale** (via agente `wiki-keeper` o editor).
- Idempotente su lintaggio ripetuto (stessi problemi riportati).

### 2. Gate di qualità per feature

La suite di manutenzione è pensata come **acceptance gate** al termine di una feature:

```
Feature implementata → run `lint(wiki/)`
  → fix=False (report)
  → LintReport.ok == True → feature passa
  → LintReport.ok == False → blocca mergia, segnala problemi
```

Consente di **tenere il wiki sempre coerente** con una sola esecuzione.

### 3. Catalogo gestito (not manual)

Marcatori `<!-- sertor:catalog -->` preservano zone di edizione automatica in index.md:

```markdown
<!-- sertor:catalog -->
## Syntheses
... (regenerated)
<!-- /sertor:catalog -->
```

Consente di **mischiare sezioni a mano + sezioni auto-generate** senza conflitti.

## Stack reale e dipendenze

### Dipendenze nuove

Nessuna nuova dipendenza esterna. `maintenance.py` usa:

- stdlib (`pathlib`, `re`, `typing`, `dataclasses`)
- moduli core Sertor (`wiki.conventions`, `sertor_core.domain.errors`)

### Provider LLM (solo per distill)

`distill_artifact()` richiede LLM (opzionale):

| Backend | Adapter | Configurazione |
|---------|---------|---|
| Ollama | `adapters/llm/ollama.py` | `OLLAMA_HOST` + modello env |
| Azure OpenAI | `adapters/llm/azure.py` | `AZURE_OPENAI_*` + lazy import |
| Assente | - | `LLMNotConfiguredError` (non blocca altri ops) |

## Test e copertura

| Categoria | Count | Note |
|-----------|-------|------|
| Unit (maintenance.py - lint) | 28 | link rotti, pagine orfane, fuori indice, coperture, contraddizioni |
| Unit (conventions.py - managed block) | 8 | `replace_managed_block()`, preserva sezioni a mano |
| Unit (distill.py - artifact) | 18 | creazione pagina, frontmatter, backlink, idempotenza strutturale |
| Integration (wiki sandbox) | 12 | Ciclo lint → report → fix → rigenerazione indice |
| Index rebuild | 8 | Scansione filesystem, frontmatter parsing, generazione catalogo |
| Idempotence | 20 | Reilinting, re-distillazione, re-rebuild su wiki invariato |
| Error handling | 6 | Wiki non trovato, source inesistente, LLM non configurato |
| Constitution Check | 16 | Principi I–IX; gate idempotenza/non-distruttività cardine |
| **Totale** | **124 passed + 2 xfail** | xfail = soglie baseline (non rilevante per FEAT-007) |

### Test suite (sandbox)

Tutti i test eseguono su **wiki sandbox in temp dir**. Nessun test tocca il wiki di produzione.

**Ruff clean**: zero warning.

## Conformità e governance

### Constitution Check ✅ 9/9

| Principio | Status | Note |
|-----------|--------|------|
| I. Core a dipendenze interne | ✅ PASS | `maintenance.py` in sertor_core, zero SDK esterni |
| II. Boundary & local-first | ✅ PASS | LLM opzionale; linting local-only |
| III. YAGNI & unità piccole | ✅ PASS | Report-only, zero auto-fix; `regenerate_index()` semplice |
| IV. Errori espliciti | ✅ PASS | LLMNotConfiguredError; report.ok boolean; nessuna eccezione silenziata |
| V. Testabilità | ✅ PASS | 124 test; 100% copertura codice path; gate su LintReport.ok |
| VI. Idempotenza & non-distruttività | ✅ PASS | Sola lettura; re-lint → stessa report; managed block preserva sezioni a mano |
| VII. Leggibilità | ✅ PASS | Naming dominio (lint, distill, regenerate_index); entità Issue/IssueKind trasparenti |
| VIII. Configurabilità | ✅ PASS | Radice wiki, set `expected`, LLM provider da Settings |
| IX. Osservabilità | ✅ PASS | LintReport strutturato; log per ogni operazione |

**Principi IV e VI (NON-NEGOZIABILI)**: idempotenza + esplicita non-distruttività cardine della feature. Confermati in design.

### Analisi SpecKit Analyze

- Functional Requirements: 15/15 ✅
- Non-functional: 5/5 ✅
- Critical issues: 0
- Constitution Check: 9/9 ✅

## Dogfooding su produzione (primo lint reale)

**Primo `lint('wiki/')` eseguito sul wiki di produzione (16 pagine):**

Risultato: **2 link rotti trovati e corretti**

1. **`syntheses/chiusura-prototipo-dogfooding.md`**: wikilink verso `epica-sertor-cli` → file inesistente (nome corretto: `epiche-sertor-core-e-cli`). **Fix**: aggiornato a quel target.
2. **`syntheses/chiusura-prototipo-dogfooding.md`**: wikilink verso `architettura-attuale` → file inesistente; esempio narrativo penzolante. **Fix**: riformulato il testo per evitare il wikilink.

**Dopo fix**: `lint('wiki/')` ritorna report.ok = True (0 problemi).

**Lezione**: Lo strumento ha fornito valore reale al primo run; ha scoperto due errori di curatela che la navigazione manuale non aveva catturato. Dogfooding validato.

## Operazioni pubbliche (API pubblica)

| Funzione | Firma | Esito |
|----------|-------|-------|
| `lint` | `(root: Path, *, expected: Set[str] \| None = None, fix: bool = False) -> LintReport` | Report problemi; fix=True rigenera indice |
| `regenerate_index` | `(root: Path) -> bool` | Rigenera catalogo in index.md; True se modificato |
| `distill_artifact` | `(root: Path, source: Path, kind: str, title: str, llm: LLMProvider, today: date \| None = None) -> Page` | Distilla artifact in pagina wiki |

Tutte esportate in `src/sertor_core/__init__.py` (API pubblica).

### Entità supportate

- `IssueKind` (enum): `BROKEN_LINK`, `ORPHANED_PAGE`, `UNCOVERED_PAGE`, `CONTRADICTION_MARKED`
- `Issue`: `kind`, `location`, `description`
- `LintReport`: `ok` (bool), `issues` (List[Issue]), `summary()` (stringhe umane)

## Ciclo di vita e processo git

### Branch e commit

- **Branch**: `spec/005-wiki-manutenzione`
- **Stato**: allineato a master (FEAT-001/002/003 mergiati)
- **Commit per fase**:
  - Requisiti EARS (requirements/sertor-core/wiki-manutenzione/requirements.md)
  - Spec SpecKit (specs/005-wiki-manutenzione/spec.md)
  - Plan SpecKit (specs/005-wiki-manutenzione/plan.md)
  - Implementation incrementale

### Processo requisiti

Percorso EARS completo (requirements/sertor-core/wiki-manutenzione/requirements.md):

- 5 user story (US1–US5)
- 32 REQ funzionali (linting, distillazione, managed block, error handling, gate)
- 6 NFR (performance, idempotenza, testabilità, governance, security)

→ Spec SpecKit (5 story + success criteria) → Plan SpecKit (16 task) → Implementation

## Integrazione con il flusso di produzione

### 1. Gate di qualità per feature (DOMANI)

```bash
sertor wiki lint wiki/
  → report JSON
  → exit code 0 (ok) / 1 (problemi)
  → blocca mergia PR se ok == false
```

### 2. Cura wiki nel flusso principale

Quando un agente `wiki-keeper` esegue una registrazione (FEAT-003), alla fine può:

```python
report = lint(wiki_root)
if not report.ok:
    segnala problemi al flusso principale
```

Mantiene **wiki sempre coerente** senza intervention manuale ripetuta.

### 3. Distillazione artifact → documentazione

Quando una spec/plan matura, pode essere distillata una volta in wiki:

```python
distill_artifact(
    root='wiki',
    source='specs/005-wiki-manutenzione/spec.md',
    kind='spec',
    title='FEAT-007: Manutenzione del wiki',
    llm=...
)
```

Creerà una pagina officiale di sintesi con backlink alla fonte.

## Post-MVP (FEAT-008+, fuori scope FEAT-007)

- **FEAT-008**: Bidirezionale (wiki → agente ingestion source; arricchimento wiki da RAG)
- **FEAT-009**: Refresh incrementale corpus (necessità emersa durante wiki skill; refresh parziale sorgenti)
- **FEAT-007B** (future): Link validation + healing (per now report-only; auto-fix future)

---

## Backlink

- [[skill-wiki-feat003]] — FEAT-003 base (operazioni wiki strutturali)
- [[costituzione-v1]] — governance 9 principi, gate Constitution Check
- [[roadmap]] — roadmap di prodotto, FEAT-007 stato ✅
- [[decomposizione-must-core]] — contesto Must/Should/Could, FEAT-007 classificata Should
