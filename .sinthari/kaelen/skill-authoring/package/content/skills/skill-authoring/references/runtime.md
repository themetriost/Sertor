# Il runtime `skillauthor`: come si invoca e cosa risponde

`skillauthor` è la metà deterministica di questa skill. Non chiama mai un modello e non scrive mai dentro
la skill che esamina: legge, decide ciò che si può decidere senza giudizio e stampa la risposta (testo,
oppure JSON con `--json`).

## Come si invoca sul tuo ospite

Il comando si chiama `skillauthor`. Come raggiungerlo dipende da come è stata installata la capability:

- **Nel repository che la sviluppa (Sinthari):** `uv run skillauthor <comando> …` dalla radice.
- **Installata come pacchetto** (per esempio con il motore d'installazione della federazione): l'installer
  mette il runtime in un ambiente suo e ne indica il punto d'ingresso. Usa quello; se non lo sai, leggi il
  rapporto dell'installer.
- **Se non lo trovi:** fermati e dillo. Non sostituire un comando del runtime con un controllo "a occhio":
  il runtime serve proprio a dare una risposta che non dipende dal tuo giudizio.

## Codici d'uscita (tutti i comandi)

| Codice | Significato |
|---|---|
| 0 | esito positivo |
| 1 | esito negativo nel dominio (finding bloccanti, copie diverse, `not-ready`) |
| 2 | errore d'uso o d'ingresso: il messaggio nomina il file e il campo. Si corregge l'ingresso, mai il runtime |

## Comandi

### `skillauthor lint <skill-dir> [--json]`

Controlli di forma sulla skill.

- **Bloccanti:**
  - **H**: percorsi di un assistente o invocazioni slash nel corpo;
  - **R**: un allegato citato che non esiste;
  - **F**: `name` diverso dalla cartella, oppure `description` mancante o oltre 1024 caratteri;
  - **L**: materiale vendorizzato senza `LICENSE` e `NOTICE`.
- **Avvisi:**
  - **S**: corpo oltre 500 righe;
  - **M**: nessun esempio lavorato o nessuna sezione sui modi di guasto, cercati per titolo.

Un'eccezione si dichiara nel frontmatter, mai in silenzio, come array JSON su una riga:

```yaml
metadata:
  lint-allow: '[{"rule": "H", "match": "<testo della riga>", "why": "<il motivo>"}]'
```

Ogni eccezione usata compare nell'esito sotto `allowed`. Il lint controlla la **forma**: non giudica se una
regola è giusta, né se una regola di giudizio porta il suo perché. Quello è compito della revisione.

### `skillauthor cost <skill-dir> [--evals <file>] [--runs N] [--json]`

Valida i casi di prova (di default `<skill-dir>/evals/evals.json`) e calcola il costo: casi × 2
configurazioni × giri esecuzioni, più altrettante valutazioni. Il default è 3 casi × 1 giro (6 + 6). Di'
questo numero all'autore **prima** di lanciare qualunque cosa.

### `skillauthor verdict <workspace> --evals <evals.json> [--skill <cartella-skill>] [--json]`

Legge `<workspace>/eval-<id>/{with_skill,without_skill}/run-<n>/grading.json` e, per ogni asserzione,
confronta il tasso di successo con la skill e quello del baseline. Il verdetto è:

- `validated`: separa almeno un'asserzione di **merito**;
- `protocol-only`: separano solo asserzioni di protocollo;
- `no-separation`: non separa niente;
- `incomplete`: manca una valutazione o una configurazione (elencate in `missing`).

Le contestazioni del tipo fatte dal valutatore sono riportate accanto all'asserzione, non applicate. Un
verdetto è un dato: `verdict` esce con 0 anche con `no-separation`.

Il verdetto registra l'**impronta** della skill (`skill_digest`): uno sha256 di tutta la cartella della
skill, `evals/` compreso, escluso `__pycache__/`. La skill è quella indicata con `--skill`; di default è la
cartella che contiene `evals/`. Se non si può ricavare, l'impronta è `null` e il gate non accetterà il
verdetto.

**Confine:** l'impronta è quella della skill **quando si calcola il verdetto**, non quando sono state fatte
le esecuzioni. Rilanciare `verdict` su valutazioni vecchie dopo aver cambiato la skill la riallinea senza
ricollaudare, e `ready` non lo può sapere. Per questo non si fa: dopo una modifica si rifanno esecuzioni e
valutazioni.

### `skillauthor ready <skill-dir> --review <review.json> --verdict <verdict.json> [--previous-review <file>] [--accept-unvalidated "<motivo>"] [--json]`

È l'**unico** modo di dichiarare pronta una skill. Ricalcola il lint, legge il registro della revisione e il
verdetto, e risponde:

- `ready`;
- `ready-unvalidated`: solo con `--accept-unvalidated` e un motivo non vuoto;
- `not-ready`, con i motivi:
  - `lint-blocking`;
  - `review-open-blocking`, con "ricomparso" se un bloccante dichiarato risolto torna aperto (serve
    `--previous-review`);
  - `verdict-unvalidated`;
  - `verdict-stale`: la skill è cambiata dopo il collaudo (l'impronta non coincide), oppure il verdetto non
    ha impronta;
  - `verdict-incomplete`;
  - `review-missing`;
  - `verdict-missing`.

**Confini dichiarati:**
- `ready` si fida di `review.json`, che trascrivi tu dall'output di `skill-review`. Ti impedisce di chiudere
  con un bloccante registrato aperto, ma non può sapere se la trascrizione è fedele. Per questo trascrivi
  ogni finding, con l'id e la gravità che gli ha dato la revisione.
- `ready` controlla che un motivo di accettazione (`--accept-unvalidated`, `acceptance_reason`) ci sia, non
  che venga dall'autore. Per questo il motivo cita le parole dell'autore fra virgolette, e il rapporto lo
  riporta.
- `review.json`, `verdict.json` e il workspace del collaudo stanno fuori dalla cartella della skill: un file
  scritto dentro cambia l'impronta.

### `skillauthor digest <skill-dir> [--json]`

Stampa l'impronta della cartella-skill, la stessa che `verdict` registra in `skill_digest`. Con `--json`:
`{"skill_name": ..., "skill_digest": "sha256:..."}`. Esce con 0; con 2 se la cartella non esiste.

Serve a due cose:
- annotare l'impronta **prima** delle esecuzioni e confrontarla con quella del verdetto;
- sapere a quale versione appartiene un verdetto che ricevi.

Cosa entra nell'impronta: ogni **file** della cartella, con il suo percorso relativo e il suo contenuto, in
ordine; `__pycache__/` è escluso. Le cartelle vuote non contano. I fine riga non contano: nei file di testo
CRLF e CR diventano LF prima del calcolo, quindi la stessa skill salvata con fine riga diversi ha la stessa
impronta. `parity`, invece, i fine riga li vede (vedi sotto).

Dove la normalizzazione non arriva:
- un file che contiene anche un solo byte NUL è binario e conta byte per byte. Un file di testo in UTF-16 ne
  contiene, quindi per l'impronta è binario e i suoi fine riga contano;
- se in un allegato i fine riga fanno parte del contenuto (per esempio un file di prova che deve essere in
  CRLF), l'impronta non vede la differenza: due versioni che differiscono solo lì hanno la stessa impronta.
  Per quelle usa `parity`.

**Confine:** l'impronta dipende dal sistema su cui la calcoli. L'ordine dei file cambia fra Windows (dove
maiuscole e minuscole non contano) e Linux o macOS, quindi la stessa skill ha due impronte diverse. Un
verdetto si verifica con `ready` sullo stesso sistema su cui è stato preso. Se `ready` risponde
`verdict-stale` su una skill che `parity` dà identica a quella collaudata, la causa può essere il sistema
diverso: dillo all'autore con questa causa. Vale comunque la regola del gate: finché non si ricollauda su
questo sistema, qui la skill non è pronta.

### `skillauthor parity <a> <b> [--json]`

Confronto byte per byte di due cartelle (o due file), ignorando `__pycache__/`. Riporta la prima differenza.
Si usa fra la sorgente di una skill e la sua copia installata.

Vede anche i fine riga: due copie che differiscono solo per quelli, per `parity` sono diverse e per `digest`
uguali. Per una copia installata vuol dire che è stata scritta con fine riga diversi (per esempio da un
checkout su Windows): ricopiala dalla sorgente e rilancia `parity`. Non è una modifica del contenuto, e il
verdetto non scade.

## Schemi

I documenti JSON che il runtime legge e scrive sono definiti in `references/schemas/`:
`evals.schema.json`, `grading.schema.json`, `verdict.schema.json`, `review.schema.json`, `lint.schema.json`,
`ready.schema.json`.
