# Contratto — Interfaccia evidenza agente → SpecLift (design MCP-skill)

**Feature**: speclift FEAT-001 (self-host) · **Branch**: `084-speclift-self-host`

> **Sostituisce** il vecchio `rag-vehicle-contract.md` (design CLI, SUPERATO): il self-host **non**
> invoca più la CLI `sertor-rag`. La localizzazione dell'evidenza è orchestrata dall'**agente** coi tool
> **MCP** (`search_code`) dentro la skill; l'evidenza rientra in SpecLift attraverso un **artefatto JSON
> esplicito e ispezionabile**. Questo file definisce quell'interfaccia (REQ-009/FR-006, DA-D-3).

L'interfaccia ha **due lati**: (1) i **candidati** che *escono* da SpecLift (cosa localizzare — da
`parse_diff`) e (2) l'**evidenza localizzata** che *rientra* in SpecLift (i simboli/test trovati
dall'agente). In mezzo, l'agente esegue il retrieval via MCP `search_code` — **fuori** dal codice
deterministico di SpecLift.

## Flusso (tre passi deterministici + due stadi di giudizio dell'agente)

```
[det]  speclift bundle <ref> --candidates-out cand.json     (ingest → parse_diff → filter_sources)
[llm]  agente: per ogni identificatore → MCP search_code → mappa gli hit a Symbol/TestRef       ← giudizio 1
[llm]  agente: scrive evidence.json (forma sotto)
[det]  speclift bundle <ref> --evidence evidence.json --out bundle.json  (… → locate → bundle)
[llm]  agente: legge il bundle → scrive le frasi EARS (authored.json)                            ← giudizio 2
[det]  speclift assemble --bundle bundle.json --authored authored.json  (lift → verify[moat] → render)
```

L'agente tocca **due** stadi di giudizio (localizza **e** scrive EARS): è la **deviazione dichiarata dal
sandwich a un solo stadio intelligente** (RNF-6, feedback a Sinthari FR-017). Gli stadi `[det]` restano
deterministici e **non toccano il RAG**; il **moat** (`verify`/`anchor_fs.py`) riverifica ogni àncora sul
**filesystem** — garanzia preservata.

## Lato 1 — Candidati in uscita (localization request)

Prodotto da `speclift bundle <ref> --candidates-out <PATH>`: esegue `ingest → parse_diff →
filter_sources` e serializza, per ogni file non-fonte, gli identificatori candidati che l'agente deve
localizzare. Deriva da `Hunk.candidate_identifiers` (`domain/models.py:47`, popolato da `parse_diff`).

```json
{
  "changeset_ref": "<ref>",
  "files": [
    {
      "path": "src/sertor_core/composition.py",
      "hunks": [
        { "candidate_identifiers": ["build_facade", "build_indexer"],
          "snippet": "def build_facade(...):\n    ..." }
      ]
    }
  ],
  "excluded_sources": [["specs/001/…", "non-source top dir"]]
}
```

- **Determinismo:** nessun RAG toccato; solo git + parsing del diff. Funziona anche a **indice assente**
  (RNF-4).
- **`excluded_sources`**: i file filtrati (`specs/`/`requirements/`/`.specify/`, doc salvo
  `--include-docs`), riportati per trasparenza — invariante del filtro sorgenti.

## Lato 2 — Evidenza in ingresso (artefatto dell'agente)

Prodotto dall'**agente** dopo il retrieval MCP e consumato da `speclift bundle <ref> --evidence <PATH>`.
**Forma = riuso diretto dei modelli di dominio `Symbol`/`TestRef`** (`domain/models.py:88-108`), zero
schema nuovo. La struttura ricalca il precedente `FakeLocator` (`tests/unit/test_locate_evidence.py`):
`symbols` chiavati per **file_path**, `tests` chiavati per **nome simbolo**.

```json
{
  "changeset_ref": "<ref>",
  "symbols": {
    "src/sertor_core/composition.py": [
      { "name": "build_facade", "path": "src/sertor_core/composition.py",
        "line": 0, "kind": "function", "provenance": "src/sertor_core/composition.py#12" }
    ]
  },
  "tests": {
    "build_facade": [
      { "name": "test_build_facade", "path": "tests/unit/test_composition.py",
        "covers_symbol": "build_facade", "provenance": "…#3" }
    ]
  }
}
```

| Campo | Origine (dagli hit MCP `search_code`) | Note |
|-------|----------------------------------------|------|
| `symbols[file].name` | l'identificatore candidato cercato | come `SertorRagLocator` upstream (`name=query`) |
| `symbols[file].path` | `hit.path` | path Sertor reale |
| `symbols[file].line` | `0` | `search_code` non fornisce la riga → l'àncora usa le righe dell'hunk (invariante upstream) |
| `symbols[file].provenance` | `hit.chunk` (`path#chunk`) | tracciabilità del retrieval |
| `tests[symbol].path` | `hit.path` che l'agente giudica un test (`test_*`/`*_test.py`/`/tests/`) e che referenzia il simbolo | il **moat** lo riverifica sul filesystem |

**Come lo consuma SpecLift.** `speclift bundle --evidence` costruisce l'adapter **`AgentEvidenceLocator`**
(`adapters/agent_evidence.py`, implementa la porta `EvidenceLocator`) e lo inietta in `Components`. La
porta è **alimentata**: `locate_symbols(file_path, identifiers, snippet)` → `symbols.get(file_path, [])`;
`locate_tests(symbol)` → `tests.get(symbol.name, [])`. È **esattamente** il contratto di `FakeLocator` →
lo stadio `locate_evidence` (`stages/locate_evidence.py`) è **invariato** e i suoi 8 test restano verdi
con un adapter reale «alimentato» al posto del fake.

## Fail-loud (Principio XII)

| Condizione | Dove emerge | Effetto | Ancora |
|------------|-------------|---------|--------|
| **MCP/indice RAG non disponibile** durante `search_code` | **skill/agente** (SpecLift non tocca più il RAG) | l'agente **si ferma** e lo segnala, nominando il componente + rimedio (`sertor-rag index .`) | FR-009/REQ-012, `SKILL.md` (nuovo passo) |
| Artefatto evidenza **assente/illeggibile** | `AgentEvidenceLocator.__init__` | `EvidenceInputError` (exit **6**) esplicito | FR-010/REQ-013 |
| Evidenza **malformata / non conforme** (chiavi mancanti, tipi errati) | `AgentEvidenceLocator.__init__` (validazione `_symbol_from`/`_test_from`) | `EvidenceInputError` (exit 6), mai ripiego su evidenza vuota/di default né àncora fabbricata | FR-010/REQ-013 |

> **Spostamento del fail-loud (conseguenza del design MCP).** Nel design CLI upstream il fallimento RAG
> emergeva dentro `rag_sertor.py` (exit 3). Ora il fallimento RAG (MCP/indice giù) emerge **nell'agente**
> (che esegue `search_code`), mentre SpecLift acquisisce un **nuovo** modo di fallire fail-loud:
> l'evidenza consegnata dall'agente può essere malformata → `EvidenceInputError`. È il guasto «più
> subdolo» del design (R-3): non c'è più un unico comando CLI che fallisce in modo osservabile, perciò
> l'`AgentEvidenceLocator` valida **all'ingresso** e fallisce forte.

## Invarianti del contratto

1. **Vehicle = MCP, mai CLI, mai import** (Principio XI): la localizzazione passa per il tool MCP
   `search_code`; SpecLift non invoca la CLI `sertor-rag` e non importa `sertor_core`. L'adapter CLI
   `rag_sertor.py` è **rimosso** dalla copia vendorata (DA-D-3).
2. **Interfaccia esplicita e ispezionabile** (REQ-009): due artefatti JSON documentati (candidati out,
   evidenza in), non una convenzione implicita.
3. **Riuso dei modelli di dominio** (`Symbol`/`TestRef`): zero schema nuovo; la validazione riusa
   `serialize._symbol_from`/`_test_from`.
4. **Moat invariato** (RNF-6): il RAG *propone* (via l'agente), il **filesystem** *dispone*
   (`anchor_fs.py:26-62`). Un'evidenza mal-localizzata che non regge alla riverifica finisce in
   `excluded`, mai accettata in silenzio.
