---
name: "speclift"
description: "Genera requisiti EARS multi-quota ANCORATI al codice da un changeset git (commit, range A..B o diff staged): la CLI deterministica estrae l'evidenza (diff → simboli/test), l'agente chiamante scrive le frasi EARS, la CLI le riverifica sul filesystem (il 'moat'). Usa questa skill ogni volta che l'utente vuole sollevare un diff a requisiti, capire o documentare COSA FA DAVVERO il codice dopo una modifica, riconciliare codice e requisiti, generare EARS da un commit o una PR, o validare un changeset — anche se non nomina esplicitamente 'SpecLift' o 'EARS'."
argument-hint: "Un riferimento git: un commit (sha o ref), --range A..B, oppure --staged (default: HEAD)"
compatibility: "Richiede la CLI `speclift` installata nel progetto e `git` su PATH"
metadata:
  author: "sinthari"
  capability: "speclift"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

`$ARGUMENTS` indica il changeset da analizzare (un commit/sha/ref, `--range A..B`, o `--staged`). Se
vuoto, usa `HEAD`.

## Cosa sei, in questo flusso

Tu sei **la parte intelligente** del sandwich deterministico di SpecLift. La CLI fa tutto il lavoro
meccanico e verificabile (estrae il diff, localizza simboli e test, àncora, **verifica**); **tu scrivi
le frasi EARS** a partire dall'evidenza già ancorata. Non inventi àncore: referenzi gli item del
fascicolo per **indice**, e la CLI li riverifica (il "moat"): è il contratto del port EarsAuthor di
SpecLift.

> Invoca la CLI come `speclift …` (se il progetto la espone via un runner, es. `uv run speclift …`). Se
> un comando `speclift` fallisce *loud* (ref invalido, RAG giù, bundle invalido), **fermati e riporta**:
> non aggirare l'errore.

## Quale percorso usare

- **Percorso A (default — usa questo se non sai quale scegliere):** il progetto espone `sertor-rag`
  come comando invocabile (CLI-vehicle, es. `uv run --project .sertor sertor-rag`). Vai a **Procedura A**.
- **Percorso B (alternativo):** il progetto NON espone una CLI-vehicle invocabile da subprocess, ma tu
  hai accesso diretto ai tool MCP di Sertor (`search_code`/`find_symbol`/`who_calls`) — es. il
  dogfooding di Sertor su se stesso. Vai a **Procedura B**. In questo percorso partecipi a **due**
  stadi (localizzazione + stesura EARS), non uno solo: è un compromesso dichiarato, non nascosto —
  vedi `contracts/evidence-locator-port.md`.

## Procedura A (CLI-vehicle — default)

### 1 — Emetti il fascicolo di evidenza (marcia 1, deterministica)

Esegui:

```text
speclift bundle <ref> --out <TMP>/speclift-evidence
```

dove `<ref>` deriva da `$ARGUMENTS` (`<commit>`, oppure `--range A..B`, oppure `--staged`) e `<TMP>` è
una cartella temporanea di lavoro. Produce `<TMP>/speclift-evidence.bundle.json`.

Il fascicolo è già **filtrato**: specifica e requisiti (`specs/`, `requirements/`, `.specify/`) sono
sempre esclusi (non sono fonte di requisiti); codice e configurazioni sono inclusi. La **documentazione**
è esclusa di default — aggiungi `--include-docs` se vuoi la vista che la include (i "due SpecLift"). I
file esclusi sono elencati in `excluded_sources` nel fascicolo: riportali per trasparenza.

### 2 — Leggi il fascicolo e scrivi le frasi EARS (la TUA parte)

Leggi `<TMP>/speclift-evidence.bundle.json`. Il campo `items` è una lista; per ogni item hai: `index`,
`file`, `lines`, `symbol` (o null), `test` (o null), `granularity`, `identifiers` e `diff` (il contenuto
della modifica da descrivere).

Per **ogni item rilevante**, scrivi requisiti EARS su **tutte e tre le quote** quando hanno senso:

- **`user_capability`** — cosa l'utente/sistema ora può fare ("l'utente può X", "il sistema ha capacità Y").
- **`behaviour`** — cosa fa il componente a fronte di un evento/stato ("quando W, fa Z").
- **`implementation`** — cosa fa il codice ("chiama `symbol()`", "il test asserisce P").

Usa la notazione EARS standard (statement in inglese):

- Ubiquitous: `The <system> SHALL <requisito>.`
- Event-driven: `WHEN <trigger>, the <system> SHALL <risposta>.`
- State-driven: `WHILE <stato>, the <system> SHALL <requisito>.`
- Unwanted: `IF <condizione>, THEN the <system> SHALL <risposta>.`
- Optional: `WHERE <feature>, the <system> SHALL <requisito>.`

Regole:
- Basati **solo** sull'evidenza dell'item (`diff`, `symbol`, `test`). Non inventare comportamenti non
  visibili nel codice.
- Una quota che non aggiunge nulla per quell'item: **omettila** (la CLI la segnala come lacuna, non è un
  errore). Non riempire con frasi vuote.
- Se qualcosa non è determinabile dal solo diff (es. evidenza cross-layer altrove), mettilo in
  `open_questions`, non in un requisito.

Scrivi un file `<TMP>/speclift-authored.json` con questa forma:

```json
{
  "changeset_ref": "<lo stesso changeset_ref del fascicolo>",
  "requirements": [
    { "item": 0, "quota": "user_capability", "statement": "WHEN …, the system SHALL …." },
    { "item": 0, "quota": "behaviour",       "statement": "WHILE …, the … SHALL …." },
    { "item": 0, "quota": "implementation",  "statement": "The … SHALL call `symbol()` …." }
  ],
  "open_questions": ["…eventuali lacune…"]
}
```

`item` è l'`index` dell'item nel fascicolo: è il solo modo per agganciare la frase all'evidenza.
Referenziare un indice inesistente fa fallire la marcia 2 (per disegno).

### 3 — Assembla e riverifica (marcia 2, deterministica)

Esegui:

```text
speclift assemble --bundle <TMP>/speclift-evidence.bundle.json --authored <TMP>/speclift-authored.json --out <OUT>/speclift-report
```

Produce `<OUT>/speclift-report.speclift.json` (canonico) e `.speclift.md` (vista). La CLI **verifica ogni
àncora sul filesystem** e **scarta** (`excluded`) ciò che non regge: è la garanzia che ogni requisito
emesso è ancorato a codice reale.

### 4 — Riporta

Mostra all'utente:
- il percorso del report (`.md` e `.json`);
- quanti requisiti confermati, quanti `excluded`, quante `open_questions`;
- gli eventuali `drifts` proposti;
- se ci sono `excluded` o `open_questions`, **dillo esplicitamente** (trasparenza del moat): indicano
  evidenza che non si è potuta ancorare o lacune da chiudere.

## Procedura B (agente + tool MCP — nessuna CLI-vehicle)

### 1 — Emetti il changeset grezzo (marcia 0, deterministica)

Esegui:

```text
speclift changeset <ref> --out <TMP>/speclift-changeset
```

Produce `<TMP>/speclift-changeset.changeset.json`: per ogni file, gli hunk con `candidate_identifiers`
e `lines` (il diff). Nessuna localizzazione è ancora avvenuta — è il tuo input per il passo 2.

### 2 — Localizza TU, coi tuoi tool MCP (la TUA parte aggiuntiva)

Leggi il changeset. Per ogni hunk, deriva le query **con la stessa regola del locator CLI**:
identificatori deduplicati (max 4 per hunk); se non ce ne sono, usa la prima riga non vuota dello
snippet **solo se** è un singolo identificatore valido (mai una riga intera: commento, import,
firma). Per ogni query, usa `search_code`/`find_symbol` per proporre simboli; per ogni simbolo
risolto, usa `who_calls`/`search_code` per i test che lo coprono.

Scrivi `<TMP>/speclift-located.json`:

```json
{
  "symbols": {
    "<file_path>::<query>": [{ "name": "...", "path": "...", "line": 12 }]
  },
  "tests": {
    "<symbol_name>": [{ "name": "...", "path": "...", "covers_symbol": "..." }]
  }
}
```

Una chiave che non trovi nulla: **ometti** l'entry (o lasciala vuota `[]`) — non inventare un
simbolo/test. Il moat (passo 4 di Procedura A, invariato) scarterà comunque ciò che non regge sul
filesystem: questo passo propone, non garantisce.

### 3 — Assembla il fascicolo dal changeset localizzato (marcia 1, deterministica)

Esegui:

```text
speclift bundle --changeset <TMP>/speclift-changeset.changeset.json --located <TMP>/speclift-located.json --out <TMP>/speclift-evidence
```

Produce lo **stesso** `<TMP>/speclift-evidence.bundle.json` che produrrebbe `speclift bundle <ref>`
in Procedura A. Da qui **prosegui con i passi 2–4 di Procedura A** (scrivi le frasi EARS, `assemble`,
riporta) — sono identici, indipendentemente da quale Procedura hai usato per arrivare al fascicolo.

## Done When

- [ ] Fascicolo di evidenza prodotto (Procedura A: marcia 1 diretta; Procedura B: `changeset` →
  localizzazione tua → `bundle --changeset/--located`).
- [ ] Frasi EARS multi-quota scritte da te, ancorate per indice, su evidenza reale.
- [ ] Marcia 2 (`assemble`) eseguita: report verificato prodotto.
- [ ] Esito riportato all'utente, con `excluded`/`open_questions`/`drifts` resi espliciti.
