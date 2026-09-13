# Data Model — Il server MCP funziona su entrambe le linee dell'SDK

**Feature**: 128-porting-mcp-sdk-v2 · **Data**: 2026-09-13

La feature non introduce entità persistite: il server è stateless e indice/store appartengono al core. Le
entità che seguono sono **di runtime e di contratto** — ciò che il codice deve distinguere perché il
comportamento sia corretto su entrambe le linee.

---

## 1. Linea dell'SDK (`SDK_LINE`)

Quale generazione della libreria a monte è installata nell'ambiente.

| Campo | Valore | Note |
|---|---|---|
| identificativo | `"v2"` \| `"v1"` | **derivato** dall'import riuscito, mai dichiarato (Principio XIV) |
| origine della classe server | `mcp.server.MCPServer` · `mcp.server.fastmcp.FastMCP` | |
| origine della classe d'errore | `mcp.server.mcpserver.exceptions.ToolError` · `mcp.server.fastmcp.exceptions.ToolError` | misurate presenti su entrambe |

**Regole**
- È **osservabile solo dal layer di compatibilità e dai test.** Nessun tool, nessun consumatore, nessuna
  configurazione dell'ospite deve poterla leggere o scegliere: quale linea sia installata è un fatto
  dell'ambiente, non una decisione (Principio VIII → manopola deliberatamente assente).
- **Transizione:** nessuna a runtime. Il valore è fissato al primo import del modulo e non cambia per la
  vita del processo.
- **Stato d'errore:** se nessuna delle due origini è importabile, non esiste un terzo valore: il modulo
  **fallisce** nominando la versione installata e l'intervallo supportato (FR-003). *Non* esiste un
  `SDK_LINE = "unknown"` — un valore che significhi «non funziona» sarebbe uno stato parziale
  (Principio IV).

---

## 2. Esito di invocazione di un tool

Ciò che il chiamante riceve. **È il contratto** che questa feature deve mantenere uguale su entrambe le
linee per i casi che contano.

| Varietà | `isError` | `structuredContent` | contenuto testuale |
|---|---|---|---|
| **successo, tool `list[dict]`** | `false` | `{"result": [...]}` | JSON degli elementi |
| **successo, tool `dict`** | `false` | `null` *(identico sulle due linee — E10-FEAT-076, fuori ambito)* | JSON della struttura |
| **guasto previsto** | `true` | `null` | `Error executing tool <nome>: <diagnosi del dominio>` |
| **guasto inatteso** | `true` | `null` | v2: `Error executing tool <nome>` · v1: `… : <messaggio>` |

**Regole**
- Le prime tre righe DEVONO essere **identiche** sulle due linee (FR-001, FR-004): sono quelle misurate
  end-to-end e quelle su cui l'agente fa affidamento.
- La quarta riga **differisce per costruzione dell'SDK** e la differenza è **accettata** (decisione D-1):
  v2 trattiene il testo di un crash, v1 no. Non è un requisito che i crash siano identici.
- **Invariante che la feature aggiunge:** su v2 il testo grezzo di un'eccezione interna **non può**
  raggiungere il client. Su v1 può ancora, perché l'SDK lo inoltra: è una differenza residua, dichiarata.

---

## 3. Classe di guasto

La distinzione che rende l'esito n. 3 diverso dall'esito n. 4. **Esiste già nel dominio** e non viene
inventata qui.

| Classe | Definizione | Origine | Resa al client |
|---|---|---|---|
| **previsto** | condizione che il sistema sa descrivere e l'utente può correggere | `SertorError` e le sue 11 sottoclassi (`sertor_core/domain/errors.py`) | `ToolError` → la diagnosi arriva |
| **inatteso** | tutto il resto: un bug nostro, un guasto non modellato di una dipendenza | qualunque altra `Exception` | ri-sollevata invariata; l'SDK decide |

**Regole**
- L'appartenenza si stabilisce **per tipo**, non per ispezione del messaggio: `isinstance(exc, SertorError)`.
  Nessuna euristica sul testo (fragile, e invecchia con i messaggi).
- **Entrambe** le classi producono l'evento di osservabilità `mcp.<tool>.error` con `detail` passato
  allo scrubber: la classificazione cambia **cosa esce verso il client**, non cosa viene registrato
  (Principio IX).
- Una sottoclasse nuova di `SertorError` aggiunta in futuro al dominio eredita il comportamento
  **automaticamente**: è la ragione per cui la distinzione si appoggia alla gerarchia esistente invece di
  elencare i tipi.

---

## 4. Vincolo di dipendenza dichiarato

| Campo | Valore |
|---|---|
| intervallo | `>=1.2,<2.3` |
| punti di dichiarazione | `pyproject.toml` extra `mcp` (`:52`) · extra `dev` (`:91`) |
| versione misurata | `2.2.0` (2026-09-13) |
| riconciliatore della divergenza | **E10-FEAT-071** (estesa: *«è uscita a monte una versione sopra il nostro tetto?»*) |

**Regole**
- I due punti DEVONO restare **coerenti** (FR-006): sono la stessa decisione scritta due volte perché
  `uv` lo richiede, non due decisioni.
- Il commento che accompagna il vincolo è **prosa su un fatto a monte**: invecchia per costruzione, e il
  suo riconciliatore è nominato sopra — non affidato alla disciplina (Principio XIV).
