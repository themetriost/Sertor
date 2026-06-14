# Quickstart — Report sfogliabili nel pannello (feature 023)

## Aprire il pannello (lo stesso di F3)

```bash
SERTOR_OBSERVABILITY=true     # raccolta dati attiva
sertor-rag observe            # apre il pannello (richiede l'extra [tui])
```

Il pannello ora ha **schede**: **Live** (lo stato corrente, come prima) + **Cache**, **Cost**,
**Corpus** (le viste di report). Ci si sposta tra le schede da tastiera.

## Sfogliare i report

- **Cache** — hit/miss giorno per giorno + totali + risparmio stimato.
- **Cost** — token per provider e per giorno.
- **Corpus** — ultimo stato (documenti/chunk/dimensione) + **freschezza** (da quanto non si re-indicizza).

Premi **`t`** per cambiare l'**intervallo**: tutto → ultimi 7 giorni → ultime 24 ore → tutto. L'intervallo
corrente è indicato in alto.

## Note

- **Sola lettura:** le viste osservano i dati conservati; non scrivono nulla.
- **Nessun dato → stato vuoto onesto** (non un errore); abilita `SERTOR_OBSERVABILITY` e svolgi
  un'operazione per popolare i dati.
- **Costo in token:** la conversione in euro è una capacità separata (in arrivo); qui si vedono i token.
- **Solo metriche:** mai il testo delle query.
