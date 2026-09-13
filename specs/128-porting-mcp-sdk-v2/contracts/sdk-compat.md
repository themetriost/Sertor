# Contract — Il layer di compatibilità dell'SDK (`sertor_mcp/_sdk.py`)

**Feature**: 128-porting-mcp-sdk-v2 · **Data**: 2026-09-13

Questo è il contratto **interno al vehicle**: la superficie che `server.py` consuma e l'unico punto del
codice che sa dell'esistenza di due linee dell'SDK. Non è una superficie pubblica per gli ospiti — quella
resta il protocollo MCP (vedi [`tool-error-surface.md`](./tool-error-surface.md)).

## Superficie esportata — tre nomi, non più

| Nome | Tipo | Contratto |
|---|---|---|
| `ServerClass` | classe | costruibile come `ServerClass(name, instructions=…)`; espone `.tool(description=…)`, `.tool()` e `.run(transport=…, **kwargs)` |
| `ToolError` | classe d'eccezione | sollevata da un tool per un guasto **previsto**: il suo messaggio raggiunge il client nel contenuto dell'esito d'errore |
| `SDK_LINE` | `str` | `"v2"` o `"v1"`, **derivato** dall'import riuscito |

Nient'altro. Ogni nome aggiuntivo che il server dovesse servirgli in futuro passa da qui, e il fatto che
la lista sia corta è la proprietà che rende il layer leggibile.

## Obblighi

**Il layer DEVE:**
1. Tentare **prima** la linea più recente supportata, poi la precedente. L'ordine non è arbitrario: la
   linea nuova è quella su cui l'ecosistema si muove, e un ambiente che ha entrambe (impossibile con
   `uv`, possibile a mano) deve ottenere la nuova.
2. Fallire con un messaggio che nomina **la versione installata** e **l'intervallo supportato** se nessuna
   linea è importabile (FR-003). Il fallimento DEVE avvenire all'import del modulo, non alla prima
   chiamata: un server che parte per morire al primo tool è la forma peggiore.
3. Derivare `SDK_LINE` dal ramo che ha funzionato. **Non** DEVE leggerlo da metadati, variabili
   d'ambiente o costanti: se fosse dichiarato potrebbe contraddire ciò che è realmente importato, che è
   esattamente la classe di difetto del Principio XIV.

**Il layer NON DEVE:**
- esporre una manopola per scegliere la linea (Principio VIII: non è una scelta dell'utente);
- importare `sertor_core` (è un layer sull'SDK, non sul dominio);
- contenere logica di prodotto: nessun tool, nessuna formattazione, nessuna decisione di retrieval.

**`server.py` NON DEVE** contenere alcun riferimento a un modulo o a un nome specifico di una linea: dopo
questa feature, una ricerca di `fastmcp` o `mcpserver` nel file deve dare **zero** risultati. È
l'invariante verificabile che dice se il layer sta facendo il suo lavoro.

## Verifiche

| Verifica | Dove | Cosa fallisce se il contratto è rotto |
|---|---|---|
| entrambi i rami dell'import producono i tre nomi | `tests/unit/test_sdk_compat.py` | il layer non regge su una delle due linee |
| `SDK_LINE` corrisponde alla linea realmente installata | idem, **primo test del passo CI** sull'altra linea | il passo CI sarebbe verde senza aver cambiato linea (R-5) |
| `server.py` non nomina alcuna linea | idem (verifica testuale sul sorgente) | il layer è stato aggirato |
| il fallimento d'import nomina versione e intervallo | idem, simulando l'assenza di entrambe | un ospite riceve di nuovo un errore illeggibile |

## Nota sull'evoluzione

Quando la linea 1.x verrà abbandonata, questo layer **si cancella** e `server.py` torna a importare
direttamente: il contratto è pensato per essere temporaneo e per sparire senza lasciare tracce nel resto
del codice. È il motivo per cui esporta i nomi con i nomi dell'SDK e non con nomi propri: il giorno della
rimozione, gli import cambiano riga e nient'altro.
