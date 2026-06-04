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
| `mode` | str (`baseline`\|`incremental`) | **nuovo** — modalità di esecuzione (US3) |
| `fallbacks` | list[str] | **nuovo** — fallback attivati e segnalati (baseline forzato, working-tree stantio…) (REQ-091/097) |

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

## FixApplication (US4-scrittura)
| Campo | Tipo | Note |
|-------|------|------|
| `proposal` | FixProposal | proposta sorgente applicata |
| `page` | str | file bersaglio (relativo alla radice wiki) |
| `outcome` | enum {applied, deleted, refused_curated, skipped_no_match} | esito dell'applicazione |
| `detail` | str | spiegazione (es. "claim non trovata", "pagina curated: rifiutato") |

`apply_fixes(proposals, root, *, dry_run=False) -> list[FixApplication]`: applica su **working tree**
**solo** su pagine `generated`; `rewrite_claim` = sostituzione **chirurgica** della claim (preserva il
resto e il marcatore `generated`); `delete_page` = rimozione file; pagina **curated** → `refused_curated`
(nessuna scrittura); claim non più presente → `skipped_no_match` (non errore); `dry_run=True` non tocca il
filesystem. Diff revisionabile via git (Principio VI). (REQ-078/079/080/085)

## Watermark (US3)
Commit SHA dell'ultimo lint semantico completato, persistito in **`wiki/.sertor/semantic-watermark`**
(file testuale, una riga). `read_watermark(root) -> str | None` (None se assente → baseline),
`write_watermark(root, sha)` (non distruttivo). La directory `.sertor/` è **esclusa** dalla scoperta
pagine del lint e dall'indicizzazione. (FR-018, REQ-089)

## EntityPageMap (US3, derivata)
Associazione **file/entità di codice → pagine wiki**, **derivata** a ogni run (no indice persistito) dal
frontmatter `sources:` e dai wikilink/backlink delle pagine. `_entity_page_map(root) -> dict[str, set[str]]`
(chiave = path/glob di codice, valore = pagine che lo documentano). Un `changed_path` seleziona le pagine
da ri-verificare. (REQ-090)

## GitPort (porta, dominio)
`Protocol` in `domain/ports.py`. Metodi:
- `changed_paths(scope: "staged"|"working"|"since_watermark", watermark: str | None = None) -> list[str]`
- `head_commit() -> str | None`
- `renamed_paths() -> list[tuple[str, str]]` (opzionale; per R-M10, può tornare `[]`)

Implementazione concreta **`SubprocessGitAdapter`** in `adapters/git/` (fuori dal dominio). Test con
`FakeGit` deterministico. (FR-017, Principio I)

## GateOutcome (US5, confine CLI/hook)
| Campo | Tipo | Note |
|-------|------|------|
| `status` | enum {pass, warning, blocked} | esito del gate |
| `report` | SemanticReport | report sottostante |
| `applied` | list[FixApplication] | auto-fix applicati alle pagine generated |
| `override` | bool | True se override esplicito ha forzato il passaggio |
| `override_record` | str \| None | record tracciabile dell'override (chi/quando/perché), per REQ-095 |

Prodotto da `run_semantic_gate(...)` **fuori dal dominio** (CLI/services): mappa `report.ok`/soglia →
`status`; `blocked` → exit ≠ 0; `override` → `pass` forzato e **registrato**. (REQ-092..095, finding A1/C1)

## Riuso
`maintenance._pages`, `conventions` (frontmatter/slug/provenance/watermark), `semantic_lint(pages=)`,
`composition.build_facade/build_llm`, porte `LLMProvider`/`GitPort`.
