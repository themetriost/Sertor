# Cambi d'intestazione: poteri prima e dopo

L'intestazione decide prima del prompt. Il brief non la può cambiare, e chi delega di solito non la legge. Per
questo una correzione che la tocca si propone e si approva **a parte**.

## Cosa conta come cambio di potere

| Campo | Cosa cambia |
|---|---|
| `tools` | gli strumenti che l'agente può usare. Senza `tools` l'agente li ha tutti, compreso avviare altri agenti e scrivere file |
| `model` | il modello, e con esso ciò che dipende dal modello (per esempio la firma di un commit) |
| altri campi letti dall'assistente (permessi, colore, …) | ciò che quell'assistente ne fa: se non lo sai, scrivilo |

## Come si presenta

Per ogni cambio d'intestazione:

1. **Poteri prima:** cosa poteva fare l'agente, campo per campo.
2. **Poteri dopo:** cosa potrà fare.
3. **Che cosa ne segue:** quali azioni del prompt cambiano, in meglio o in peggio. Per esempio: aggiungere
   `PowerShell` dà una shell su Windows; togliere `Bash` lascia l'agente senza shell su Linux e macOS.
4. **La richiesta di approvazione,** separata da quella delle modifiche al prompt.

Dopo la scrittura, l'elenco dei cambi lo dà il runtime, non la memoria:

```text
skillauthor agent-diff <copia-di-prima> <sorgente> --json
```

Riporta nel rapporto `fields` e `tools` così come escono. `tools` si confronta come insieme: lo stesso strumento
scritto in un altro ordine, o come lista a blocco, non è un cambio. Un filtro invece sì: `Bash(git *)` e `Bash`
sono strumenti diversi.

## Restringere `tools`

Quando una correzione toglie strumenti, verifica per **ogni azione** che il prompt o la sua skill delegata
richiedono (eseguire comandi, scrivere file, versioning, avviare agenti) che uno strumento dichiarato la permetta
ancora:
- **su ogni assistente di destinazione:** un assistente può non leggere `tools`, e allora il limite non vale lì
  (vedi `forms.md`);
- **su ogni sistema operativo su cui l'agente può girare.** Una shell dichiarata può esistere solo su alcuni
  sistemi: `Bash` senza `PowerShell` lascia l'agente senza shell su Windows senza bash, e `PowerShell` senza
  `Bash` lo lascia senza shell su Linux e macOS.

`skillauthor agent-lint <sorgente>` riporta la seconda verifica come regola **T**. Lancialo dopo ogni cambio a
`tools`, e anche sulla copia di prima: un bloccante T che c'è solo dopo è una correzione che ha rotto l'agente; uno
che c'era già è un finding che l'autore non ha chiuso, e si riporta come tale.

Se un'azione resta senza strumento, non scrivere la modifica: presentala all'autore con l'azione e il sistema
scoperto. Le opzioni sono aggiungere lo strumento mancante oppure togliere l'azione dal prompt, e la scelta è
sua.

**La regola T guarda `tools`, non il prompt.** È bloccante ogni volta che `tools` dichiara una sola delle due
shell, qualunque cosa il prompt chieda. Se l'autore sceglie di togliere i comandi dal prompt e di tenere una sola
shell, il gate resta `not-ready` finché quella scelta non è **dichiarata** nell'intestazione dell'agente, come
eccezione con il suo perché:

```yaml
metadata:
  lint-allow: '[{"rule": "T", "match": "claude-code:tools", "why": "<il motivo, citato dall autore>"}]'
```

Nel motivo usa l'apostrofo tipografico (’) al posto di quello dritto: così citi le parole dell'autore senza
chiudere la stringa fra apici singoli. **Confine:** `agent-lint` non verifica che l'intestazione sia YAML valido.
Un apostrofo dritto passa il lint e il gate, e può impedire all'assistente di caricare l'agente.

L'eccezione è una modifica d'intestazione come le altre: la propone la skill e la approva l'autore, a parte. Il
perché cita le sue parole. Resta visibile nell'esito di `agent-lint` (`allowed`). Non cambiare `tools` di tua
iniziativa per far tacere la regola: è piegare l'agente per zittire un controllo.

## Allargare i poteri

Aggiungere strumenti o togliere un limite è un cambio di potere come gli altri: prima e dopo, approvazione a
parte. Non è più sicuro perché «risolve» un finding. Un agente con più poteri ha più modi di fare ciò che il brief
non chiede.
