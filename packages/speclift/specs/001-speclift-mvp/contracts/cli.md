# Contract — CLI `speclift`

Interfaccia pubblica (Principio III). Host-agnostica; la skill sottile la invoca, non la reimplementa.

## Sintassi

```text
speclift <ref> [--staged] [--range <A>..<B>] [--format json|md|both] [--out <path>] [--include-docs] [--verbose]
```

- `<ref>`: un commit (sha o riferimento). Mutuamente esclusivo con `--range`/`--staged`.
- `--staged`: analizza il diff *staged* (ignora `<ref>`).
- `--range <A>..<B>`: analizza il range.
- `--format`: `json` (canonico), `md` (vista), `both` (default).
- `--out <path>`: directory/percorso base dell'output (default: stdout per `md`, file per `json`).
- `--include-docs`: include la **documentazione** come fonte (vedi *Filtro sorgenti*).
- `--verbose`: log strutturati per stadio.

## Filtro sorgenti (G3)

SpecLift solleva requisiti da *cosa fa il codice*. Prima della localizzazione, il changeset è filtrato:

- **Sempre esclusi**: **specifica** e **requisiti** (cartelle `specs/`, `requirements/`, `.specify/`) —
  sono ciò CONTRO cui l'output va confrontato (lavoro di SpecAudit), non la fonte: generarli dalla spec
  sarebbe circolare.
- **Sempre inclusi**: codice, **configurazioni**, test.
- **Documentazione** (`.md`, `.rst`, `docs/`, …): esclusa di default, inclusa con `--include-docs` — i
  "due SpecLift" (vista codice vs vista codice+doc).

I file esclusi sono **dichiarati** (stderr nella marcia `bundle`; nota in `open_questions` del report) —
mai scartati in silenzio (Principio XI). Le liste sono in `config.py`, sovrascrivibili.

## Comportamento (mappa ai requisiti)

- Risolve il changeset (FR-001); changeset vuoto → esce 0 con report vuoto esplicito.
- Esegue il sandwich; emette `SpecLiftReport` conforme a `output.schema.json` (FR-011).
- **Exit codes**: `0` ok (anche report vuoto); `2` riferimento git invalido (`InvalidRefError`);
  `3` RAG non disponibile/indice mancante (`RagUnavailableError`, fail-loud); `4` capacità
  `requirements` non disponibile (`EarsAuthorUnavailableError`); `5` bundle/contratto non valido.
- Nessun output parziale silenzioso su errore: la causa (e lo stadio) sono dichiarati su stderr
  (Principio VI/XI). Nessun segreto nei log (Principio X).

## Esempi

```text
speclift HEAD                       # ultimo commit, output JSON+MD
speclift --staged --format md       # diff staged, solo vista Markdown su stdout
speclift --range main..HEAD --out ./speclift-report
```

## Modalità agente-autore (due marce) — realizzazione di F1

La stesura EARS è a carico dell'**agente chiamante** (vedi `ears-author-port.md`). La pipeline si spezza
al confine del bundle in due sottocomandi, orchestrati dalla skill sottile `speclift`:

```text
speclift bundle <ref> [--staged] [--range A..B] [--repo <path>] [--out <path>] [--include-docs]
speclift assemble --bundle <path> --authored <path> [--repo <path>] [--format json|md|both] [--out <path>]
```

- **`bundle`** (deterministico): esegue ingest → parse → locate → bundle e **emette il fascicolo di
  evidenza** (`<out>.bundle.json`): per ogni item, `index` + àncora + il `diff` da descrivere. È l'input
  per l'agente. `--repo` indica il repo da analizzare (default `.`).
- **`assemble`** (deterministico): rilegge il fascicolo + il file `--authored` scritto dall'agente
  (`{requirements: [{item, quota, statement}], open_questions}`), àncora ogni frase all'item per
  **indice** (mai àncora nuova: REQ-X01), **verifica** sul filesystem (`--repo`, default `.`) ed emette
  il `SpecLiftReport`. Un indice fuori range o un'àncora non verificabile → fail-loud / esclusione.

Il comando monolitico `speclift <ref>` resta per l'uso **offline/test** (autore stub → placeholder): la
capacità piena è `bundle` + agente + `assemble`.

## Modalità locator alternativo (tre marce) — Adapter B, `EvidenceLocator` pluggable

Per gli host dove l'agente ha accesso diretto ai tool MCP di Sertor (`search_code`/`find_symbol`/
`who_calls`) ma **non** alla CLI-vehicle `sertor-rag` (vedi `evidence-locator-port.md`), la
localizzazione si sposta a monte del `bundle`:

```text
speclift changeset <ref> [--staged] [--range A..B] [--repo <path>] [--out <path>] [--include-docs]
speclift bundle --changeset <path> --located <path> [--out <path>]
speclift assemble --bundle <path> --authored <path> [--repo <path>] [--format json|md|both] [--out <path>]
```

- **`changeset`** (deterministico): ingest → parse → filtro sorgenti → **stop** (nessuna
  localizzazione). Emette `<out>.changeset.json`: hunk con `candidate_identifiers` e `lines` (il diff
  leggibile dall'agente), più `excluded_sources` (stessa trasparenza G3 di `bundle`).
- **`bundle --changeset <path> --located <path>`**: alternativa a `<ref>`/`--staged`/`--range`
  (mutuamente esclusivi, exit 2 se combinati). Ricostruisce il changeset, costruisce un
  `ProvidedEvidenceLocator` dal file `--located` (evidenza già localizzata dall'agente — schema in
  `evidence-locator-port.md`), e produce lo **stesso** `<out>.bundle.json` del percorso a due marce.
  `--changeset` e `--located` vanno usati **insieme** (exit 2 se uno manca).
- Da qui, `assemble` è **identico** al percorso di default: non distingue da quale Adapter è arrivato
  il bundle.

## Invocazione del RAG (interna, via vehicle o via evidenza fornita dall'agente)

L'adapter di default usa `uv run --project .sertor sertor-rag <cmd> --json`, mai `import sertor_core`.
L'adapter alternativo (`ProvidedEvidenceLocator`) non invoca nulla: rilegge `--located` (vedi sopra).
