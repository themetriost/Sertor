# Contract — Cosa arriva al client quando un tool fallisce

**Feature**: 128-porting-mcp-sdk-v2 · **Data**: 2026-09-13

Questa è la superficie **pubblica** che la feature tocca: ciò che un client MCP — quindi l'agente
dell'ospite — riceve quando un tool non riesce. Il contratto è espresso in termini di protocollo, perché è
lì che passa il confine (→ [[misura-al-confine-pubblico]]); tutte le righe sono **misurate end-to-end** su
`mcp` 1.29.0 e 2.2.0.

## La tabella normativa

| Il tool incontra | `isError` | Contenuto testuale | Evento registrato | Identico sulle due linee? |
|---|---|---|---|---|
| **niente** (successo) | `false` | il risultato serializzato | `mcp.<tool>` | ✅ sì |
| **guasto previsto** (`SertorError`) | `true` | `Error executing tool <nome>: <diagnosi>` | `mcp.<tool>.error` con `detail` scrubbato | ✅ **sì** — è il requisito centrale (FR-004) |
| **guasto inatteso** | `true` | v2 `Error executing tool <nome>` · v1 `… : <messaggio>` | `mcp.<tool>.error` con `detail` scrubbato | ❌ **no, e accettato** (D-1) |

## Esempio normativo — il caso che ha motivato la feature

Un ospite invoca una ricerca su un corpus non ancora indicizzato. Ciò che l'agente DEVE ricevere, su
**entrambe** le linee:

```
isError: true
content:  Error executing tool search_code: index not found for corpus 'sertor': run `sertor-rag index .`
```

Ciò che l'agente NON DEVE ricevere (è lo stato in cui il porting senza classificazione lo lascerebbe su v2):

```
isError: true
content:  Error executing tool search_code
```

La differenza è la ragione per cui questa feature non è «due righe»: il secondo messaggio è vero e
inutile, e la regola standing del progetto è che **un errore è un segnale**. Un agente che riceve il
secondo non ha modo di suggerire il rimedio, e ripiegherà su una lettura a mano dei file — che è
esattamente ciò che i nodi colpiti hanno fatto per 34 e 36 giorni.

## Obblighi

**Il server DEVE:**
1. Consegnare la diagnosi del dominio per ogni guasto previsto, su ogni linea supportata.
2. Registrare l'evento `mcp.<tool>.error` per **entrambe** le classi di guasto, con `detail` passato allo
   scrubber: la classificazione decide cosa esce verso il client, **non** cosa viene registrato.
3. Identificare il tool nel contenuto d'errore in ogni caso — anche quando il testo è generico, il
   chiamante deve sapere *quale* tool ha fallito.

**Il server NON DEVE:**
- inserire il testo grezzo di un'eccezione **inattesa** nel payload su v2 (è la restrizione che la feature
  introduce, e il guadagno di D-1);
- restituire un esito di successo con dati parziali quando un guasto è avvenuto (Principio IV);
- silenziare un guasto per far sembrare funzionante il tool (Principio XII).

## Cosa questo contratto NON copre

- **`structuredContent` per i tool che ritornano una struttura singola**: assente su **entrambe** le linee,
  quindi non è una regressione e non è materia di questa feature → **E10-FEAT-076**.
- **Cancellazione, timeout, payload di grandi dimensioni, concorrenza**: non misurati (research.md,
  *Perimetro del non misurato*). Nessuna riga di questo contratto li riguarda, e nessuna verifica li
  asserisce.
- **Cosa fa `doctor`** di fronte a un server che non parte: è **E10-FEAT-072**, e resta aperta. Questa
  feature rimuove la causa del guasto, non la cecità del controllo che non l'ha visto.

## Verifica

`tests/contract/test_mcp_protocol_e2e.py` — un client MCP reale lanciato contro il server come processo:
handshake, elenco dei dieci tool, payload di un tool `list[dict]`, e **il contenuto diagnostico di un
guasto previsto**. Eseguito su entrambe le linee (R-5). È la verifica che oggi non esiste e la cui assenza
ha permesso a una conclusione sbagliata di entrare nel backlog.
