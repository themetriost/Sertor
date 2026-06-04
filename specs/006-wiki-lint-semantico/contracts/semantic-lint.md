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

## `semantic_lint_incremental(root, llm, facade, git, *, watermark_path=None, threshold=Severity.HIGH, k_code=5, max_pages=None) -> SemanticReport` (US3)

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | nessun watermark | verifica **tutte** le pagine (delega a `semantic_lint`) | `mode="baseline"` | REQ-087 |
| 2 | watermark valido + git | `git.changed_paths(...)` → `_entity_page_map` → pagine collegate; `semantic_lint(pages=…)` | `mode="incremental"`, solo pagine toccate | REQ-088/090 |
| 3 | change set non tocca pagine | **no-op rapido** (0 pagine, nessuna chiamata LLM) | report vuoto, `mode="incremental"` | REQ-093 |
| 4 | git assente o watermark invalido | **fallback baseline completo**, **segnalato** | `mode="baseline"`, `fallbacks` non vuoto | REQ-091 |
| 5 | sempre (FEAT-009 assente) | re-index reale **non** eseguito: contesto da working tree/corpus | `fallbacks` include "stale-index" | REQ-096/097 |
| 6 | a fine run completato | il chiamante persiste il watermark (`write_watermark`) | watermark = `git.head_commit()` | REQ-089 |

> `.sertor/` è esclusa dalla scoperta pagine. La selezione pagine rispetta comunque `max_pages` (copertura riportata).

## `apply_fixes(proposals, root, *, dry_run=False) -> list[FixApplication]` (US4-scrittura)

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | proposta `rewrite_claim` su **generated** | sostituzione **chirurgica** della claim col `proposed_text`; preserva resto + `generated` | `FixApplication(applied)` | REQ-078/079 |
| 2 | proposta `delete_page` su **generated** | rimozione del file dalla working tree | `FixApplication(deleted)` | REQ-085 |
| 3 | pagina **curated** | **rifiuto**: nessuna scrittura/cancellazione | `FixApplication(refused_curated)` | REQ-080 |
| 4 | claim non più presente nel file | nessuna modifica | `FixApplication(skipped_no_match)` (non errore) | IV |
| 5 | `dry_run=True` | calcola gli esiti **senza** toccare il filesystem | lista `FixApplication` | VI |
| 6 | sempre | diff minimo e revisionabile via git; non interattiva | non-distruttivo/automatizzabile | VI/NFR-08 |

## `GitPort` (porta dominio) + `SubprocessGitAdapter` (adapter)

| Metodo | Comportamento | Note |
|--------|---------------|------|
| `changed_paths(scope, watermark=None)` | path cambiati: `staged`/`working` (pre-commit) o `since_watermark` (pre-push) | REQ-088 |
| `head_commit()` | SHA di HEAD o `None` | per watermark (REQ-089) |
| `renamed_paths()` | coppie (old, new) o `[]` | opzionale, R-M10 |

Il dominio dipende **solo** da `GitPort`; `SubprocessGitAdapter` (in `adapters/git/`) usa `subprocess`.
Test: `FakeGit` deterministico (nessun repo reale). (FR-017, Principio I)

## `run_semantic_gate(root, llm, facade, git, *, threshold=Severity.HIGH, apply=False, override=False, override_reason=None) -> GateOutcome` (US5 — fuori dal dominio: CLI/services)

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 0 | **default `apply=False`** | rilevazione + proposte in **dry-run**, **nessuna scrittura**; status sulle issue rilevate | gate **read-only** (default sicuro: LLM rumoroso) | — |
| 1 | `apply=True` (flag `--apply`), trigger pre-commit/pre-push | incrementale → `apply_fixes` su generated → valuta issue residue vs soglia | correzioni nello **stesso** commit imminente | REQ-092 |
| 2 | change set irrilevante | no-op rapido | `GateOutcome(status=pass)` | REQ-093 |
| 3 | issue ≥ soglia (residue dopo auto-fix se `apply`, altrimenti rilevate) | **blocco** | `status=blocked`, **exit ≠ 0** | REQ-094 |
| 4 | issue < soglia | passa con **warning** | `status=warning` (non blocca) | REQ-094 |
| 5 | `override=True` (flag/env) | procede nonostante il blocco, **registra** l'override | `status=pass`, `override_record` valorizzato | REQ-095 |

> Il **core** non conosce exit code né git: `run_semantic_gate` vive nel layer CLI/hook ed è il **trigger
> a monte** del configuration-manager (non esegue git esso stesso). Esposizione: `sertor wiki semantic-gate`.

## Invarianti
- **Non-distruttività** (VI): rilevazione e proposte sola lettura; **scrittura solo su generated**, diff
  chirurgico revisionabile; watermark non distruttivo.
- **Confine** (I): git dietro `GitPort`; gate fuori dal dominio.
- **Degrado** (IV): senza LLM, semantico saltato; **fallback** baseline/working-tree **segnalati**.
- **Costo** (REQ-083/NFR-09): tetto pagine + copertura; incrementale riduce le pagine verificate.
- **Local-first** (NFR-10): funziona con LLM Ollama + git locale.

## Test
Wiki sandbox + **LLM scriptato** (JSON deterministico) + **`FakeGit`** deterministico:
- P1 (invariati): obsolete/contraddizione/lacuna/sommario, soglia/gate-report, degrado senza LLM,
  parsing difensivo, proposte solo su generated, provenienza read/mark/default.
- US3: baseline senza watermark; incrementale seleziona solo le pagine toccate; no-op a change set vuoto;
  fallback baseline segnalato senza git; `fallbacks` include stale-index; watermark read/write.
- US4-scrittura: rewrite chirurgico su generated (resta generated); delete su generated; **rifiuto** su
  curated; `skipped_no_match`; `dry_run` non scrive.
- US5: blocco sopra soglia (exit≠0); warning sotto soglia; override forza il passaggio e lo **registra**.
