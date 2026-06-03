# Contratto — Operazioni del wiki (create / record / ingest / distill)

Operazioni strutturali della skill LLM Wiki sul filesystem. Tutte idempotenti per struttura
(REQ-050). LLM-free tranne `distill` (REQ-031). Ogni operazione emette log strutturato (REQ-013).

## Interfacce

```python
def create_wiki(root: Path | str, today: str | None = None) -> WikiOpResult: ...
def record(root: Path | str, brief: Brief, today: str | None = None) -> WikiOpResult: ...
def ingest(root: Path | str, source: SourceBrief, today: str | None = None) -> WikiOpResult: ...
def distill(root: Path | str, brief: Brief, llm: LLMProvider | None,
            today: str | None = None) -> WikiOpResult: ...
```

`today` (default = data odierna) rende deterministici i test nello stesso giorno.

## Contratto comportamentale

| # | Operazione | Precondizione | Comportamento | Postcondizione | Req |
|---|------------|---------------|---------------|----------------|-----|
| 1 | create | repo senza wiki | crea cartelle tematiche + `index.md`/`log.md` minimi | struttura conforme presente | REQ-001 |
| 2 | create | wiki esistente | non sovrascrive/tronca `index.md`/`log.md` | contenuto pre-esistente intatto | REQ-002 |
| 3 | (tutte) | pagina nuova | frontmatter YAML completo, kebab-case, sottocartella corretta, wikilink | pagina conforme | REQ-003/004/005 |
| 4 | record | brief | crea/aggiorna la pagina del tema (no duplicati), aggiorna index, **1** voce log | pagina + index + log | REQ-010/011/012 |
| 5 | record | input identico, wiki invariato | **no-op** (nessuna riscrittura/voce/timestamp) | output identico (`changed=False`) | REQ-013/050 |
| 6 | ingest | fonte | pagina `sources/` + propaga ref nelle pagine correlate + index + log `ingest` | pagina sources + ref | REQ-020/021/022 |
| 7 | ingest | fonte che contraddice | marca esplicitamente la contraddizione nella pagina interessata | contraddizione marcata | REQ-023 |
| 8 | distill | brief + LLM configurato | genera pagina conforme nel tema corretto + log `record` | pagina distillata | REQ-030/032/033 |
| 9 | distill | nessun LLM | `LLMNotConfiguredError` | operazione bloccata, esplicita | REQ-031 |
| 10 | (tutte) | qualunque repo / path config | nessun path hardcoded | funziona su ≥2 repo | REQ-006/012, SC-005 |

## Invarianti

- **Idempotenza strutturale**: scrivere solo se il contenuto cambia; `created` preservato, `updated`
  cambia solo a modifica reale; `log.md` append-only (REQ-050).
- La struttura cartelle è fissa (DA-W6).
- Nessuna operazione strutturale richiede un LLM, eccetto `distill` (REQ-031).
- Log strutturato per ogni operazione (operazione, file, esito) (REQ-013).

## Test (contract tests, su wiki sandbox)

create idempotente + non-distruttivo (#1/#2), conformità pagina (#3), record dedup + 1 log (#4),
record re-run no-op (#5), ingest sources + propagazione + contraddizione (#6/#7), distill con
`FakeLLM` (#8) ed errore senza LLM (#9). Tutti in `tmp_path` (RNF-002).
