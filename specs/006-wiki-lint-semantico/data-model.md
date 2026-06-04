# Data Model — Lint semantico del wiki

Entità in `src/sertor_core/wiki/semantic.py` (+ estensioni provenienza in `conventions.py`).

## Severity (ordinale)
`info < low < medium < high < critical` — confrontabile per la soglia del gate.

## SemanticIssueKind (enum)
`obsolete` · `semantic_contradiction` · `coverage_gap` · `stale_summary`.

## SemanticIssue
| Campo | Tipo | Note |
|-------|------|------|
| `kind` | SemanticIssueKind | tipo di problema |
| `page` | str | path relativo della pagina (o area, per coverage_gap) |
| `claim` | str | la **frase/paragrafo** specifico (vuoto per coverage_gap) |
| `severity` | Severity | guida il gate |
| `detail` | str | spiegazione sintetica |
| `evidence` | str | riferimento al codice (path#chunk) o all'altra pagina |

## SemanticReport
| Campo | Tipo | Note |
|-------|------|------|
| `issues` | list[SemanticIssue] | problemi rilevati |
| `pages_checked` | int | pagine verificate |
| `pages_total` | int | pagine totali (copertura: checked vs total) |
| `skipped` | bool | True se saltato (no LLM) |
| `threshold` | Severity | soglia di blocco |
| `ok` | bool (proprietà) | pass se nessuna issue ha severità ≥ threshold |
| `llm_calls` | int | osservabilità/costo |

`render()` leggibile; `ok` consumabile come **gate** (exit ≠ 0 → blocco).

## Provenance (estensione conventions)
Frontmatter `provenance: generated | curated`. `read_provenance(text) -> "generated"|"curated"`
(default **curated** se assente). `mark_provenance(text, value) -> text` (inserisce/aggiorna la riga,
non distruttivo). `distill_artifact` marca `generated`.

## FixProposal (US4, forma proposta)
| Campo | Tipo | Note |
|-------|------|------|
| `issue` | SemanticIssue | problema sorgente |
| `page` | str | pagina bersaglio (**solo generated**) |
| `action` | enum {rewrite_claim, delete_page} | tipo di correzione proposta |
| `proposed_text` | str | testo proposto (vuoto per delete) |
| `rationale` | str | motivazione |

Le proposte su pagine **curated** non sono generate (solo segnalazione nell'issue).

## Watermark (US3, fase successiva)
Commit git dell'ultimo lint semantico completato (persistito sotto la radice wiki o stato dedicato).

## Riuso
`maintenance._pages`, `conventions` (frontmatter/slug), `composition.build_facade/build_llm`,
porta `LLMProvider`.
