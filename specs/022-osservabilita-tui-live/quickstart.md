# Quickstart — Pannello live dell'osservabilità (feature 022)

## Installare il componente del pannello

Il pannello è un'estensione opzionale (`[tui]`):

```bash
uv add "sertor-core[tui] @ git+https://github.com/themetriost/Sertor"   # textual
```

Senza, il resto del prodotto funziona e il comando del pannello dà un messaggio con questa istruzione.

## Abilitare la raccolta dati (prerequisito)

Il pannello mostra i dati conservati dallo strato persistente (feature 020):

```bash
SERTOR_OBSERVABILITY=true     # altrimenti il pannello mostra "nessun dato — abilita l'osservabilità"
```

## Aprire il pannello

```bash
sertor-rag observe
```

Si apre un cruscotto da terminale con: ultima indicizzazione (documenti/chunk/dimensione), efficacia
della cache (hit/miss + risparmio stimato), consumo di token per provider, ultimi eventi, e
affidabilità (errori/ritentativi/astensioni). Si **aggiorna da solo** (default ogni 2 s,
`SERTOR_OBSERVABILITY_REFRESH`). Esci con `q`/`Ctrl-C`.

## Note

- **Sola lettura:** il pannello osserva e basta — non scrive nulla, non rallenta le operazioni.
- **Vista live, non storica:** mostra lo stato corrente e gli ultimi eventi; i report sfogliabili nel
  tempo (hit/miss storici, costo per giorno) sono la feature successiva (F4).
- **Solo metriche:** mai il testo delle query.
