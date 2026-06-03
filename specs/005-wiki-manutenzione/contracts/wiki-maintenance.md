# Contratto — Operazioni di manutenzione del wiki

Funzioni di libreria del core (DA-6). Tutte riusano le convenzioni di FEAT-003. Lint LLM-free;
distillazione richiede `LLMProvider`.

## `lint(root, *, expected=None, fix=False) -> LintReport`

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | wiki | scopre pagine, costruisce grafo wikilink | `LintReport` con issue tipizzate; **nessuna scrittura** se `fix=False` | REQ-001/005 |
| 2 | link `[[x]]` a pagina inesistente | rileva | issue `broken_link` (con sorgente) | REQ-002 |
| 3 | pagina non in index né wikilinkata | rileva (index/log esenti) | issue `orphan` | REQ-003 |
| 4 | pagina su disco non nel catalogo | rileva | issue `index_missing` | REQ-004 |
| 5 | `expected` set | confronta | issue `coverage_missing` per gli assenti | REQ-064 |
| 6 | pagina con marcatore di contraddizione | rileva | issue `contradiction` | REQ-020 |
| 7 | sempre | esito **pass/fail** (`report.ok`) | consumabile come gate | REQ-052/053 |
| 8 | `fix=True` | applica **solo** fix sicuri (rigenera indice) | mai auto-fix link | REQ-006 |

## `regenerate_index(root) -> bool` (changed)

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | wiki | rigenera il blocco tra marcatori (link+sommario per pagina) | resto di `index.md` intatto | REQ-010/011 |
| 2 | marcatori assenti | li introduce (append) | non distruttivo | REQ-011 |
| 3 | wiki invariato, re-run | nessun cambiamento | `index.md` identico (idempotente) | REQ-012 |

## `distill_artifact(root, source, kind, title, llm, today=None) -> WikiOpResult`

| # | Precondizione | Comportamento | Esito | Req |
|---|---------------|---------------|-------|-----|
| 1 | sorgente (artifact/brief) + LLM | LLM sintetizza → pagina conforme con **backlink** alla fonte | pagina creata (se assente) | REQ-061/062/063 |
| 2 | pagina già esistente | **non** sovrascrive il curato (assistita/non distruttiva) | no-op sul contenuto | REQ-063 (DA-3) |
| 3 | nessun LLM | blocca | `LLMNotConfiguredError` | REQ-065 |
| 4 | pagina distillata | **rimanda** alla fonte, non la duplica | backlink presente | REQ-062 |

## Invarianti
- **Idempotenza** (REQ-040): re-run su wiki invariato → esito identico, nessun timestamp nuovo.
- **Non-distruttività** (Principio IV/VI): lint read-only; index-rebuild solo blocco gestito; distill crea-se-assente.
- **Osservabilità** (REQ-051): ogni operazione emette log strutturati.
- Riuso del core (Principio I/III): nessuna logica di convenzioni duplicata.

## Test
Su wiki sandbox: link rotto/orfano/indice/coperture/contraddizione (#1-7), `--fix` solo indice (#8),
index-rebuild idempotente e non distruttivo, distill con `FakeLLM` (crea + non sovrascrive + errore senza LLM).
