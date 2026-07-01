# Contract — `EvidenceLocator` port (localizzazione simboli/test)

Il port che risolve, per ogni hunk, i **simboli** e i **test** toccati (Constitution I/II). Non è lo
stadio di giudizio (quello è `EarsAuthor`, vedi `ears-author-port.md`): è retrieval, non scrittura —
ma **da dove** viene quel retrieval è pluggable, e questo contratto documenta le due vie ammesse.

> **Storia della decisione.** L'MVP (2026-06-29) aveva un solo adapter, `SertorRagLocator`
> (subprocess sulla CLI `sertor-rag search --type code --json`). Il 2026-07-01 Sertor, facendo il
> proprio self-hosting di SpecLift (dogfooding), ha segnalato che negli host dove l'agente ha accesso
> diretto ai tool MCP di navigazione (`search_code`/`find_symbol`/`who_calls`) ma **non** alla
> CLI-vehicle, l'unico adapter esistente lo esclude a priori (vedi
> `wiki/sources/input-other-agents/sertor-feedback-speclift-cli-to-mcp.md`). Risposta: **rendere il
> locator pluggable** aggiungendo un secondo adapter che consuma evidenza già localizzata
> dall'agente, senza toccare il resto della pipeline (ports & adapters, Constitution I).

## Interfaccia (port, invariata)

```text
EvidenceLocator.locate_symbols(file_path: str, identifiers: list[str], snippet: str) -> list[Symbol]
EvidenceLocator.locate_tests(symbol: Symbol) -> list[TestRef]
```

Entrambi i metodi possono sollevare `RagUnavailableError` (fail-loud); un "non trovato" onesto è
`[]`, mai un'eccezione. Nessuna àncora nasce qui: `locate_evidence` la costruisce da questi risultati
e il **moat** (`AnchorResolver.verify`, adapter `anchor_fs`) la riverifica sul filesystem prima che
sopravviva al report — **indipendentemente** da quale adapter l'abbia proposta.

## Adapter A (default) — `SertorRagLocator`: CLI-vehicle

Interroga `sertor-rag search --type code --json -k 5` via subprocess (mai `import sertor_core`).
Un solo stadio di giudizio nella pipeline: la stesura EARS (`EarsAuthor`). Percorso di default,
invariato — vedi `rag_sertor.py`.

## Adapter B (alternativo) — `ProvidedEvidenceLocator`: evidenza fornita dall'agente/MCP

Non fa alcuna ricerca propria: rilegge una mappa **già calcolata** (`located.json`) da chi ha accesso
diretto ai tool MCP di Sertor (`search_code`/`find_symbol`/`who_calls`) ma non alla CLI-vehicle. Usato
quando l'host non espone `sertor-rag` come comando invocabile da un subprocess Python (il caso del
dogfooding Sertor-su-Sertor).

**Implicazione onesta (non nascosta):** con l'Adapter B l'agente partecipa a **due** stadi — la
localizzazione (quali query fare, quali risultati accettare) **e** la stesura EARS — non uno solo. Il
`deterministic-sandwich` "un solo stadio di giudizio" resta il comportamento di **default** (Adapter
A); l'Adapter B è un'**opzione esplicita** con un compromesso dichiarato: la garanzia forte che resta
intatta in entrambi i casi è il **moat** (nessun'àncora sopravvive se non verificabile sul
filesystem), non "l'agente non ha mai visto il retrieval".

### Le tre marce con l'Adapter B

1. **CLI — `speclift changeset <ref>`** (deterministico): ingest → parse → filtro sorgenti → **stop**
   (nessuna localizzazione). Emette `<out>.changeset.json`: per ogni file, gli hunk con
   `candidate_identifiers` e le `lines` del diff — ciò che serve all'agente per decidere cosa cercare.
2. **Agente — localizza** (via i propri tool MCP): per ogni hunk, deriva le query con la STESSA
   regola G6 del locator CLI (`domain/query_keys.build_identifier_queries` — identificatori
   deduplicati e limitati a `max_queries_per_symbol`, fallback alla prima riga dello snippet solo se
   è un identificatore singolo), interroga `search_code`/`find_symbol`, e per ogni simbolo risolto
   interroga `who_calls`/`search_code` per i test che lo coprono. Scrive `located.json`:
   ```json
   {
     "symbols": { "<file_path>::<query>": [ {"name","path","line","kind"?,"provenance"?} ] },
     "tests":   { "<symbol_name>": [ {"name","path","covers_symbol","line"?,"provenance"?} ] }
   }
   ```
   Una chiave assente è un "non trovato" onesto (`[]`), non un errore.
3. **CLI — `speclift bundle --changeset <path> --located <path>`** (deterministico): ricostruisce il
   changeset, costruisce un `ProvidedEvidenceLocator(located.json)`, e produce lo **stesso**
   `<out>.bundle.json` che produrrebbe l'Adapter A. Da qui in poi (`assemble`) il flusso è
   **identico** al percorso di default: non c'è alcuna differenza per la marcia 2.

`speclift bundle <ref>` (senza `--changeset`/`--located`) resta il percorso di default con l'Adapter
A. I due flag sono **alternativi** a `<ref>`/`--staged`/`--range`, mai componibili con essi (exit 2).

## Perché non rompe il resto del contratto

- **Il moat non cambia.** `verify`/`anchor_fs` non sanno né si curano di quale adapter ha proposto un
  simbolo o un test: verificano sempre sul filesystem reale.
- **Il bundle non cambia.** `evidence-bundle.schema.json` e `output.schema.json` sono identici;
  `assemble` non distingue da dove viene arrivato il bundle.
- **La skill resta host-agnostica** (Principio X): sceglie il Percorso A o B in base a cosa l'host
  espone (CLI-vehicle vs soli tool MCP), non hardcoda un assistente specifico.
