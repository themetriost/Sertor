# Il runtime: `skillauthor agent-lint`

`skillauthor` è il runtime deterministico della capability di cui questa skill fa parte. Non chiama mai un
modello e non scrive mai sul file che esamina: legge e stampa la risposta (testo, oppure JSON con
`--json`). Per la review di un agente serve un solo comando, `agent-lint`.

## Come si invoca sul tuo ospite

- **Nel repository che sviluppa la capability:** `uv run skillauthor agent-lint …` dalla radice.
- **Installata come pacchetto** (per esempio con il motore d'installazione della federazione): l'installer
  mette il runtime in un ambiente suo, con un lanciatore il cui percorso finisce in
  `kaelen/skill-authoring/launch.py` (la cartella che lo contiene cambia da ospite a ospite: cercalo con
  quel suffisso). Si invoca come `python <percorso>/launch.py skillauthor agent-lint …`. Le istruzioni che la
  capability aggiunge a quelle dell'assistente riportano la forma esatta.
- **Se non lo trovi:** dillo nel rapporto ("controlli meccanici non eseguiti: runtime non trovato") e fai i
  controlli dell'intestazione leggendo il file, dichiarando che sono a occhio. Non presentarli come esito
  del runtime.

## Il comando

```text
skillauthor agent-lint <file-agente> [--targets claude-code,github-copilot,codex] [--skills-dir <cartella>]... [--json]
```

- `<file-agente>`: `.md` (intestazione fra `---`), `.agent.md` (stessa forma) o `.toml` (`name`,
  `description`, `developer_instructions`).
- `--targets`: gli assistenti a cui l'agente è destinato. Ometterlo quando è per un solo assistente: la
  parità risulta `not-applicable`. Con due o più destinazioni un percorso proprio di un assistente nel
  prompt diventa bloccante.
- `--skills-dir`: le cartelle dove l'ospite tiene le skill (una o più). Servono per sapere se le skill che
  il prompt nomina esistono. Senza, i nomi risultano `unchecked`. Per trovarle, cerca le cartelle che
  contengono `<nome>/SKILL.md`: di solito una per assistente nella radice del repository, più la cartella
  sorgente delle skill se il repository ne produce. Una cartella che non esiste è un errore d'ingresso
  (exit 2), non un insieme di skill assenti.

## Codici d'uscita

| codice | significato |
|---|---|
| 0 | nessun finding bloccante |
| 1 | almeno un finding bloccante |
| 2 | errore d'ingresso: file assente, forma non riconosciuta, intestazione illeggibile, destinazione sconosciuta, `--skills-dir` inesistente. Il messaggio nomina il file o l'argomento. La review dell'intestazione si ferma e lo dice |

## Cosa risponde

Lo schema completo è `references/schemas/agent-lint.schema.json`.

- **`facts`**: i campi dell'intestazione con il valore come scritto; `tools_declared` e `model_declared`;
  `skills_named` (nome, stato `found`, `missing`, `unchecked`, e `match`: `backtick` se il nome è citato
  fra backtick, `plain` se l'ha trovato solo l'euristica); `shell_tools`: le shell dichiarate in `tools`
  (`declared`) e i sistemi operativi su cui l'agente resta senza shell (`uncovered`: `linux`, `macos`,
  `windows`), oppure `null` quando la regola non si applica (nessun `tools`, forma Copilot `.agent.md`,
  forma Codex `.toml`). Con `declared` vuoto l'agente non ha alcuna shell, e `uncovered` vuoto **non**
  vuol dire «coperto»: se il prompt chiede comandi, è il caso che il runtime non vede (dimensione 1). Sono **fatti, non difetti**: li giudichi tu con `references/dimensions.md`.
- **`parity`**: la fonte di riferimento e, per ogni destinazione e campo, `represented`, `different`,
  `dropped` o `unknown` (vedi `references/parity.md`). Oppure `status: not-applicable`.
- **`findings`**, con `rule`, `severity`, `location`, `detail`:

| regola | cosa | gravità |
|---|---|---|
| F | manca `name` o `description` | bloccante |
| F | `name` diverso dal nome del file | avviso |
| H | percorso o invocazione propria di un assistente nel prompt | bloccante con ≥ 2 destinazioni, altrimenti avviso |
| R | allegato citato che non esiste accanto al file, o skill citata fra backtick assente nelle `--skills-dir` | bloccante |
| R | skill trovata solo dall'euristica (senza backtick) e assente | avviso |
| P | campo `dropped` o `different` su una destinazione | avviso |
| S | prompt oltre 500 righe | avviso |
| T | agente in forma Claude Code che dichiara in `tools` una shell garantita solo su alcuni sistemi (`Bash` → Linux, macOS; `PowerShell` → Windows); `location` è `claude-code:tools` | bloccante |

## Dai finding del runtime al rapporto

| esito del runtime | nel rapporto |
|---|---|
| F, H o R `blocking` | bloccante, con la stessa prova, dopo aver controllato nel prompt che il riferimento sia reale. Un falso positivo va nelle note, con riga e motivo |
| R `warning` (skill nominata riconosciuta solo dall'euristica, assente) | verifica nel prompt: se è davvero una skill che l'agente usa, bloccante; se è una parola comune ("della skill ad-hoc"), nota |
| F `warning` (nome diverso dal file) | miglioria |
| H `warning` (un solo assistente) | nota, o miglioria se il prompt sarà distribuito |
| P | lo giudichi con la dimensione 5: bloccante solo se un confine importante sta solo in un campo `dropped` |
| S | miglioria (rimandare a una skill o a un allegato) |
| T | dimensione 1 («gli strumenti bastano?»): vedi «La regola T nel rapporto», sotto |

### La regola T nel rapporto

Verifica nel prompt, e nella skill delegata, se l'agente esegue comandi.

- **Sì** → bloccante. Prova: il campo `tools` (con i sistemi di `shell_tools.uncovered`) e la riga che
  esegue il comando. Proposta: dichiarare anche la shell degli altri sistemi e controllare che i comandi
  girino su entrambe. Non si declassa perché l'agente «gira solo» su un sistema (vedi la dimensione 1).
- **No** → miglioria: la shell non serve, proposta toglierla. Un confine del prompt che la shell
  scavalca si giudica con la scala dei confini della dimensione 1 (`references/dimensions.md`).

Il `detail` del runtime («se il prompt esegue comandi, aggiungi …») vale solo per il primo caso.

## Confini dichiarati

- Il runtime **non** decide se un `tools` assente o un `model` fissato è un difetto: dipende da cosa il
  prompt e i brief si aspettano.
- La regola T vede solo la shell dichiarata, e solo nel vocabolario di Claude Code. Non vede un `tools`
  senza shell il cui prompt chiede comandi, né uno senza scrittura il cui prompt chiede di scrivere: per
  quello serve leggere il prompt, ed è la dimensione 1.
- Il riconoscimento delle skill nominate è un'euristica: un nome fra backtick, o con un trattino, accanto
  alla parola «skill». Un nome semplice senza backtick può sfuggire. Per questo leggi comunque tutto il
  prompt.
- Le regole H e R riconoscono un'invocazione slash a inizio riga o fra backtick, e un allegato citato fra
  backtick o in un link. Un'invocazione o un percorso scritti in testo semplice a metà frase possono
  sfuggire: rileggi il prompt anche per questo.
- Un'eccezione alla regola H si dichiara come per le skill, in `metadata.lint-allow` dell'intestazione;
  compare nell'esito sotto `allowed`.
