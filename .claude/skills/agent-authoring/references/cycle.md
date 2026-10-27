# Il ciclo di una correzione, passo per passo

Dettaglio dei passi 1–3 e del rapporto di `SKILL.md`, con i casi di confine.

## Letture

Prima di proporre leggi:
- **l'intestazione e il prompt interi** della sorgente;
- **ogni skill o file che il prompt usa.** Un agente sottile rimanda a una skill per la procedura: leggila,
  perché la correzione non deve contraddirla;
- **la review intera**, finding aperti e chiusi. Un finding chiuso dice cosa non va riaperto.

Se un file nominato dal prompt non si trova, è un fatto da riportare. Non supporne il contenuto.

## La review è attuale?

| Situazione | Cosa fai |
|---|---|
| `subject_digest` del registro = `agent_digest` della sorgente | procedi |
| diversi | review vecchia: chiedi una review nuova o la conferma dell'autore che i finding valgono ancora |
| il registro non ha `subject_digest` (il caso normale: `agent-review` non lo scrive) | chiedi all'autore se è della versione attuale; con la conferma scrivi `agent_digest` come `subject_digest` e cita la conferma. Su delega vale solo una riga del brief che lo dice |
| nessuna review | chiedi una review di `agent-review` prima di proporre. Non inventare finding |

La conferma dell'autore va citata con le sue parole nel rapporto, perché nessun controllo può verificarla.

## Da dove viene l'agente

- **Sorgente del suo produttore, nel repository del produttore:** è il caso normale.
- **Copia installata da un altro produttore:** di solito si riconosce da un registro d'installazione, in una
  cartella che finisce in `kaelen/<capability>/`. Correggerla la allontana dal registro: dillo, e scrivi solo con
  la decisione esplicita dell'autore. La correzione vera va proposta al produttore, che la fa nel suo
  repository.
- **Copia di sviluppo accanto alla sorgente** (una copia che l'ospite tiene per provare l'agente, che nessun
  registro d'installazione elenca): non è una forma derivata. La ricopi dalla sorgente e lo dichiari; vedi
  `forms.md`.

## Proposte

Ogni proposta ha:
- **`finding`:** l'id del finding che chiude, oppure «nessuno», da segnalare;
- **`kind`:** `prompt` o `header`. Le `header` si approvano a parte, vedi `header.md`;
- **`before`** e **`after`:** il testo esatto;
- **`approval`:** `approved` (con le parole dell'autore, o la riga del brief che la autorizza), `proposed` (non
  scritta) oppure `rejected`.

**Una modifica per finding, limitata a ciò che il finding chiede.** Se l'autore chiede di chiudere un bloccante,
riscrivere il paragrafo accanto «già che ci sei» è una modifica che non ha chiesto: dichiarala, o lasciala
fuori.

**Contraddizione fra prompt e skill delegata.** Mostra le due righe, con file e numero di riga, e le opzioni.
Di solito sono tre:
1. il prompt si adatta alla skill;
2. la skill si adatta al prompt, se è dello stesso autore (cambiarla ha un costo: se è collaudata, il collaudo
   scade);
3. il prompt delega il punto in contesa a chi chiama l'agente.

Aggiungi la tua raccomandazione con il perché, poi aspetta la scelta.

**Regole di giudizio che aggiungi:** scrivi accanto il perché. **Agente sottile:** rimanda alla skill, non
copiare le sue regole nel prompt.

## Autore non raggiungibile

Il brief vale come voce dell'autore solo per ciò che dice esplicitamente. Esempi:

| Il brief dice | Puoi scrivere |
|---|---|
| «chiudi B1 aggiungendo PowerShell a tools» | quella modifica, con la riga del brief come approvazione |
| «chiudi i bloccanti» | niente: non dice come. Proponi una modifica per bloccante, e lasciale `proposed` |
| niente sulle migliorie | niente: le migliorie restano proposte |
| «accetta M3» senza un motivo | niente: `accepted` richiede le parole dell'autore con il motivo |

Il collaudo, senza autore, lo lanci solo se il brief lo autorizza e ne fissa il tetto di costo.

## Il rapporto, in quest'ordine

1. **Domande aperte:** decisione, opzioni, raccomandazione.
2. **Esito del gate:** `ready`, `ready-unvalidated` (con il motivo accettato) oppure `not-ready` con i motivi;
   poi le `notes`, ognuna con l'esito del tuo controllo a occhio. Se non l'hai lanciato, scrivi «non lanciato» e
   perché.
3. **Verdetto del collaudo:** `validated`, `protocol-only` o `no-separation`, con le asserzioni che separano.
   Oppure «non eseguito» e perché.
4. **Finding** con il loro stato dopo la correzione.
5. **Modifiche:** la tabella delle proposte, con l'esito di `agent-diff` per quelle d'intestazione.
6. **Forme:** per ognuna `corrected`, `to-regenerate` o `unchanged`, con le perdite dichiarate.
7. **File prodotti o modificati.**
8. **Costo speso:** esecuzioni e valutazioni.
9. **Scostamenti e default:** cosa non hai fatto o hai fatto diversamente dal brief, e perché; ogni valore che
   hai scelto tu dove il brief taceva.

Chi riceve il rapporto deve poter agire senza rifare il lavoro. Per questo il prima e dopo è testo esatto, non un
riassunto.
