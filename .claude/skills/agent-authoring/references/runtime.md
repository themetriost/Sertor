# Il runtime `skillauthor` per la correzione di un agente

`skillauthor` è il runtime deterministico della capability di cui questa skill fa parte. Non chiama mai un
modello e non scrive mai sui file che esamina: legge e stampa la risposta (testo, oppure JSON con `--json`).

## Come si invoca sul tuo ospite

- **Nel repository che sviluppa la capability:** `uv run skillauthor <comando> …` dalla radice.
- **Installata come pacchetto** (per esempio con il motore d'installazione della federazione): l'installer mette il
  runtime in un ambiente suo, con un lanciatore il cui percorso finisce in `kaelen/skill-authoring/launch.py`. La
  cartella che lo contiene cambia da ospite a ospite: cercalo con quel suffisso. Si invoca come `python
  <percorso>/launch.py skillauthor <comando> …`. Le istruzioni che la capability aggiunge a quelle
  dell'assistente riportano la forma esatta.
- **Se non lo trovi: fermati e dillo.** Questa skill non ha un ripiego a occhio: impronta, differenze, forme e
  gate sono proprio ciò che non deve dipendere dal tuo giudizio.
- **Se lo trovi, controlla la versione.** Lancia `skillauthor --help`: se non elenca `agent-diff` e
  `agent-forms`, il runtime installato è di una versione precedente a questa skill. Fermati e dillo come per un
  runtime non trovato. Non correggere gli argomenti: l'errore d'ingresso che riceveresti non dipende da loro.

## Codici d'uscita

| Codice | Significato |
|---|---|
| 0 | esito positivo |
| 1 | esito negativo nel dominio (forme che divergono, `not-ready`, bloccanti di `agent-lint`) |
| 2 | errore d'uso o d'ingresso: il messaggio nomina il file o l'argomento. Si corregge l'ingresso |

## I comandi

### `skillauthor digest <file-agente> [--json]`

L'impronta dell'agente: `{"agent_file", "agent_digest"}`. È lo sha256 del contenuto con i fine riga normalizzati
(CRLF e CR diventano LF), **senza il nome del file**: una copia identica in un'altra cartella ha la stessa
impronta. Per un file solo l'impronta non dipende dal sistema operativo. Un file con un byte NUL conta byte per
byte.

### `skillauthor agent-diff <prima> <dopo> [--json]`

Le differenze fra due versioni dello **stesso** agente, nella stessa forma:
- `fields`: ogni campo dell'intestazione `added`, `removed` o `changed`, con prima e dopo;
- `tools`: strumenti aggiunti e tolti, confrontati come insieme (filtro compreso); `null` se nessuna delle due
  versioni dichiara `tools`;
- `prompt`: se è cambiato, e quante righe sono entrate e uscite. I fine riga non contano.

Esce con 0. Con due forme diverse esce con 2: per quelle c'è `agent-forms`.

### `skillauthor agent-forms <sorgente> <forma>... [--json]`

Confronta ogni forma con la sorgente. La destinazione si deduce dal suffisso: `.agent.md` Copilot, `.toml` Codex,
`.md` Claude Code. Per ogni forma dà uno stato:
- `in-sync`;
- `declared-losses-only`: mancano solo campi che, secondo la tabella di parità (fonte in `reference`),
  quell'assistente non rappresenta o rappresenta in modo diverso. Nel secondo caso (oggi `tools` e `model` su
  Copilot) la perdita non è inevitabile: leggi ogni voce di `differences`;
- `unverified`: un campo che quell'assistente rappresenta in modo diverso (oggi `tools` e `model` su Copilot)
  è presente, e non si può confrontare per valore. Il dettaglio porta i due valori: confrontali tu;
- `diverges`: con `missing`, `different` o `prompt-differs`.

Il prompt si confronta senza le righe vuote in testa e in coda e senza i fine riga. Esce con 0 se nessuna forma
diverge, con 1 altrimenti.

### `skillauthor agent-lint <file-agente> [--targets …] [--skills-dir …] [--json]`

I controlli meccanici su un agente, gli stessi che usa `agent-review`: intestazione leggibile, percorsi di un
assistente nel prompt, skill nominate, parità dei campi, lunghezza, e la regola **T** (shell dichiarate solo per
alcuni sistemi operativi). Lancialo dopo ogni correzione, con le destinazioni (`--targets`) e le cartelle
delle skill (`--skills-dir`): senza destinazioni la parità risulta `not-applicable`.

Un'eccezione si dichiara nell'intestazione dell'agente, in `metadata.lint-allow`, con la regola, il testo da
abbinare e il perché. Per la regola H il testo è quello della riga del prompt; per la regola T è
`claude-code:tools`. Ogni eccezione usata compare nell'esito, sotto `allowed`.

### `skillauthor verdict <workspace> --evals <evals.json> --skill <file-agente> [--json]`

Il verdetto del collaudo, come per una skill (vedi `testing.md`). Con un file in `--skill`, il campo `skill_digest`
porta l'impronta dell'agente collaudato.

### `skillauthor ready <file-agente> --review <review.json> --verdict <verdict.json> [--form <forma>]... [--previous-review <review-di-prima>] [--accept-unvalidated "<motivo>"] [--json]`

Il gate. È l'**unico** modo di dichiarare pronta una correzione. L'esito porta `subject_kind: "agent"` e
`subject_digest`, l'impronta della versione a cui si riferisce: se l'agente cambia dopo, quell'esito non vale
più.

Gli stati:
- `ready`;
- `ready-unvalidated`: pronto con un verdetto non validato che l'autore ha accettato con `--accept-unvalidated`.
  Riportalo così, mai come `ready`;
- `not-ready`, con i motivi sotto.

Le `notes` dell'esito elencano ciò che va controllato a mano e non blocca, per esempio i campi `unverified` di una
forma. Riportale nel rapporto.

Con `--previous-review` passa il registro che la correzione voleva chiudere: il gate segnala un bloccante
dichiarato risolto che ricompare.

| Motivo di `not-ready` | Che cosa vuol dire | Che cosa fai |
|---|---|---|
| `lint-blocking` | `agent-lint` ha un bloccante sulla sorgente o su una forma; il dettaglio la nomina | correggi, con una proposta approvata; per la regola T, se l'autore sceglie una sola shell, l'eccezione dichiarata (vedi `agent-lint`) |
| `review-stale` | il registro non porta `subject_digest`, o è di un'altra versione | rifai la review sulla versione attuale, annotando l'impronta prima di avviarla |
| `review-open-blocking` | un bloccante della review è aperto | correggilo, oppure l'autore lo accetta con un motivo |
| `review-missing` | manca il registro | fai la review |
| `verdict-stale` | l'agente è cambiato dopo il collaudo | rifai esecuzioni e valutazioni, non solo `verdict` |
| `verdict-unvalidated` | il collaudo non separa sul merito | serve `--accept-unvalidated "<motivo>"` con le parole dell'autore |
| `verdict-incomplete`, `verdict-missing` | collaudo incompleto o assente | completa il collaudo |
| `forms-diverge` | una `--form` non coincide con la sorgente | fai rigenerare la forma |

**Confini del gate:**
- Si fida di `review.json`, che trascrivi tu: trascrivi ogni finding con l'id e la gravità che gli ha dato la
  review.
- Verifica le forme che riceve con `--form` e non le cerca da sé. Su Copilot non confronta `tools` e `model`:
  li mette fra le `notes`.
- L'impronta nel registro della review la annoti tu: il gate verifica che coincida con l'agente, non che sia stata
  presa prima della review. Annotala prima di avviarla, e non toccare l'agente finché la review non torna.
- Controlla che un motivo di accettazione ci sia, non che venga dall'autore: per questo il motivo cita le sue
  parole.

## Gli schemi

I documenti che leggi e scrivi sono definiti in `references/schemas/`: `review.schema.json` (con
`subject_digest`), `ready.schema.json`, `agent-lint.schema.json`, `agent-diff.schema.json`, `agent-forms.schema.json`,
`verdict.schema.json`, `evals.schema.json`, `grading.schema.json`.
