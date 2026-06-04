# Contratto — Operazioni del lint semantico

Funzioni di libreria del core. Richiedono `LLMProvider` (degradano senza). Riusano facade di retrieval
e convenzioni di FEAT-003/007.

## `semantic_lint(root, llm, facade=None, *, threshold=Severity.HIGH, k_code=5, max_pages=None, pages=None) -> SemanticReport`

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | wiki + LLM | per ogni pagina: contesto codice (facade) → LLM giudica per-claim | issue tipizzate (obsolete/contraddizione/lacuna/sommario) | REQ-071..074/098 |
| 2 | LLM = None | salta la parte semantica | `SemanticReport(skipped=True)`, nessun errore | REQ-081 |
| 3 | sempre | assegna severità; calcola `ok` su soglia | esito pass/fail consumabile come gate | REQ-082 |
| 4 | `max_pages` impostato | verifica fino al tetto | report con copertura (checked/total), niente troncamento silenzioso | REQ-083 |
| 5 | output LLM malformato | parsing difensivo | voci malformate saltate con log; lint non si rompe | REQ-051/IV |
| 6 | re-run input invariato (LLM deterministico) | stessa rilevazione | stesso insieme issue/severità | REQ-084 |
| 7 | sola lettura | nessuna scrittura sul wiki | non distruttivo | Principio VI |

## Provenance (in `conventions.py`)

| Funzione | Comportamento | Req |
|----------|---------------|-----|
| `read_provenance(text) -> "generated"\|"curated"` | legge il frontmatter; **default curated** se assente | REQ-077c |
| `mark_provenance(text, value) -> text` | inserisce/aggiorna la riga `provenance:` (non distruttivo) | REQ-076 |
| `distill_artifact(...)` | marca la pagina prodotta come **generated** | REQ-077 |

## `propose_fixes(report, root, llm) -> list[FixProposal]` (US4, proposta)

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | issue su pagina **generated** | l'LLM propone riscrittura della claim o cancellazione | `FixProposal` (no scrittura) | REQ-078/085 |
| 2 | issue su pagina **curated** | nessuna proposta di modifica | solo segnalazione (issue) | REQ-080 |
| 3 | sempre | non scrive né cancella file | non distruttivo (la scrittura è fase P2) | Principio VI |

## Invarianti
- **Non-distruttività** (VI): rilevazione e proposte sola lettura.
- **Degrado** (IV): senza LLM, semantico saltato; strutturale resta operativo.
- **Costo** (REQ-083/NFR-09): tetto pagine + copertura riportata.
- **Local-first** (NFR-10): funziona con LLM Ollama.

## Test
Wiki sandbox + **LLM scriptato** (ritorna JSON deterministico): obsolete/contraddizione/lacuna/sommario,
soglia/gate, degrado senza LLM, parsing difensivo, proposte solo su generated, provenienza read/mark/default.
