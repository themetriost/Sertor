# Data Model — LLM Wiki end-to-end (FEAT-010)

Entità del dominio (in `src/sertor_core/wiki/` + porte in `domain/ports.py`). Riuso delle entità
FEAT-003 (`Brief`, convenzioni frontmatter/wikilink, `WikiOpResult`).

## Aree del wiki (convenzioni, estensione di `conventions.py`)
- **Wiki generato** (l'LLM scrive): `concepts/ tech/ experiments/ syntheses/` + `index.md`, `log.md`.
- **Input — versionato**: `manual_edited/` (umano, immutabile per l'LLM, compilato in pagine derivate).
- **Input — non versionato**: `ingested_sources/` (esterno, popolato dall'ingest a trigger manuale).
- **Stato**: directory dedicata (es. `.sertor/`) esclusa da scoperta pagine e indicizzazione.

## GitPort (porta dominio)
| Metodo | Comportamento |
|--------|---------------|
| `changed_paths(scope: "staged"\|"working"\|"since_watermark", watermark=None) -> list[str]` | file del changeset |
| `head_commit() -> str \| None` | SHA HEAD (watermark) |
| `renamed_paths() -> list[tuple[str,str]]` | rename (opz.) |

Adapter `SubprocessGitAdapter` fuori dal dominio. Best-effort: errori → `[]`/`None` (fallback baseline).

## SourceSet (fonti-input configurabili)
Insieme **configurabile** (Settings) delle fonti: `code`, `tests`, `specs`, `discussion_logs`,
`manual_edited`, `ingested_sources`. Ogni fonte: tipo, glob/percorsi, **regime di trigger**
(`versioned`@commit | `manual`). Modificabile durante il ciclo di vita. (FR-009)

## EntityPageMap (derivata)
`code/file → set[pagine]`, derivata da frontmatter `sources:` + wikilink. Un path del changeset
seleziona le pagine collegate da (ri)generare/verificare. Nessun indice persistito. (FR-018/037)

## GenerationReport
| Campo | Note |
|-------|------|
| `mode` | `baseline` \| `incremental` |
| `pages_written` | pagine generate/aggiornate |
| `pages_total` | copertura |
| `llm_calls` | costo/osservabilità |
| `fallbacks` | es. `stale-index`, `async-followup` |

## Provenance & manual_edited
`generated` | `manual` (input). L'LLM non modifica i file in `manual_edited/`; ne **compila** pagine
derivate (con eventuale link di provenienza, **non indicizzato**). (D-1/D-7/FR-016/024)

## AuthorityModel (verità stratificata)
- `behavior_authority = {code, tests}` ; `rationale_authority = {discussion_logs, specs, manual_edited}`.
- **Gerarchia** di default + **configurabile** (Settings). Conflitto che coinvolge `manual_edited` →
  esito `needs_user` (human-in-the-loop). (D-4/FR-012..015)

## LintReport (strutturale, LLM-free)
`issues`: link rotti · pagine orfane · copertura/cross-ref mancanti. `ok` = gate strutturale. (FR-035)

## FreshnessReport (LLM)
`issues`: pagina **obsoleta** (vs codice/test = comportamento, o vs decisione = perché), con la **claim**
e l'evidenza; `severity`. (FR-017/036)

## GateOutcome (confine, US5)
| Campo | Note |
|-------|------|
| `status` | `pass` \| `warning` \| `blocked` |
| `lint` / `freshness` | report sottostanti |
| `proposals` | ≥1 soluzione proposta (incl. "ignora e committa") |
| `override` / `override_record` | override esplicito **tracciato** |

Prodotto al confine (`services/wiki_gate.py`); il blocco/exit vive lì, non nel dominio. (D-17/FR-041/042)

## TriggerBinding (setup)
Aggancio del momento "commit" alla generazione/gate. Per Claude Code: configuration-manager / hook.
Installato dal setup; assente → il trigger si perde (R-03). Contratto **client-agnostico**. (D-8/D-16/FR-027/028)

## Collezioni RAG (retrieval)
Due collezioni **separate**: `wiki_generato`, `code`. Interrogate **insieme** (query congiunta, peso
paritario). Rigenerabili in modo **indipendente**. Input non indicizzati. (D-3/D-7/FR-010/011/023)
