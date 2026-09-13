# Research — Il server MCP funziona su entrambe le linee dell'SDK

**Feature**: 128-porting-mcp-sdk-v2 · **Data**: 2026-09-13

Ogni decisione qui sotto è **misurata**, non dedotta, salvo dove è detto il contrario. Le sonde sono
state eseguite su `mcp` **2.2.0** (versione attuale a monte) e **1.29.0** (ultima della linea che usiamo),
in venv usa-e-getta, con due piani di misura: le firme dell'API e — quello che conta —
**il protocollo stdio con un client MCP reale** (→ [[misura-al-confine-pubblico]]).

---

## R-1 — Forma del meccanismo di selezione fra le due linee

**Decisione: un modulo di compatibilità dedicato che esporta DUE nomi** — la classe del server e la
classe d'errore «previsto» — e che è l'**unico** punto del codice a sapere che esistono due linee.

```
sertor_mcp/_sdk.py     (nuovo, ~15 righe)  →  esporta: ServerClass, ToolError, SDK_LINE
sertor_mcp/server.py   importa da ._sdk    →  non contiene alcun riferimento a una linea specifica
```

**Rationale.** La misura ha mostrato che servono **due** cose dall'SDK, non una: la classe del server
*e* la classe d'errore che consegna il messaggio al modello (vedi R-2). Se il `try/except` vivesse in
cima a `server.py` avremmo due blocchi condizionali in un file da 595 righe, e il resto del modulo
resterebbe pieno di nomi che esistono solo su una linea. Concentrandoli in un modulo si ottiene:

- **un solo punto di variabilità**, quindi un solo punto da rileggere quando la prossima major esce;
- un modulo **testabile in isolamento** (si può asserire che entrambi i rami producano nomi usabili);
- `SDK_LINE` come **valore derivato** dall'import riuscito — non una costante dichiarata (Principio XIV):
  serve ai test e alla diagnosi di R-5, e nessuno deve *scriverlo* da nessuna parte.

**Fatti misurati che la rendono possibile** (su 2.2.0 *e* 1.29.0, esito identico):

| Elemento usato da `server.py` | v1.29.0 | v2.2.0 |
|---|---|---|
| classe server | `mcp.server.fastmcp.FastMCP` | `mcp.server.MCPServer` (anche `mcp.server.mcpserver.MCPServer`) |
| `instructions=` come kwarg del costruttore | ✔ | ✔ |
| `.tool(description=…)` | ✔ | ✔ |
| `@tool()` nudo → docstring come descrizione | ✔ | ✔ |
| `.run(transport='stdio', **kwargs)` | ✔ | ✔ |
| classe d'errore «previsto» | `…fastmcp.exceptions.ToolError` | `…mcpserver.exceptions.ToolError` |
| payload di un tool `list[dict]` **al client** | `{"result": [...]}` | `{"result": [...]}` |

**Alternative considerate e scartate.**
- *`try/except` in cima a `server.py`*: nessun modulo nuovo, ma due blocchi condizionali e nomi
  specifici sparsi nel file. Scartata per il costo di rilettura futura.
- *Selezione a runtime su `mcp.__version__`*: l'attributo **non esiste** (misurato: `hasattr` falso su
  entrambe), quindi si tratterebbe di leggere i metadati del pacchetto per poi importare — più
  fragile dell'import stesso, che è già il test definitivo di ciò che c'è.
- *Vendorare un adapter per ciascuna linea*: sproporzionato (Principio III, YAGNI) — le due linee
  differiscono per **un nome di classe e un percorso di modulo**.

---

## R-2 — Dove avviene la mappatura degli errori, e su quali eccezioni

**Decisione: dentro `_guard`, e SOLO per le eccezioni `SertorError`.** Un `SertorError` viene ri-sollevato
come `ToolError(str(exc))`; ogni altra eccezione viene **ri-sollevata invariata**, come oggi.

**Rationale — è il design dell'SDK, e coincide con D-1.** La sonda ha mostrato che v2 distingue:

| Cosa solleva il tool | Cosa riceve il client su v2.2.0 | su v1.29.0 |
|---|---|---|
| `ToolError("index not found for corpus 'sertor': run …")` | `isError=True` · `Error executing tool X: index not found for corpus 'sertor': run …` | **identico** |
| `RuntimeError("...")` (crash) | `isError=True` · `Error executing tool X` — testo **trattenuto** | `… : <messaggio>` |

Quindi la riga che ci serve — **il guasto previsto arriva con la sua diagnosi** — si ottiene con lo
**stesso codice su entrambe le linee**, e `ToolError` esiste su entrambe (R-1). Non c'è nulla da
«preservare con fatica»: c'è da **dire quale errore è previsto**, e la risposta esiste già nel dominio
(`sertor_core/domain/errors.py`: `SertorError` con 11 sottoclassi — `IndexNotFoundError`,
`EmbeddingError`, `VectorStoreError`, `ConfigError`, `GraphNotFoundError`, `ProviderMismatchError`,
`IndexLockedError`, `SessionNotFoundError`, `GloveUnavailableError`, `IngestionError`,
`InvalidTimeWindowError`).

**Conseguenza da dichiarare, non da nascondere.** Per le eccezioni **inattese** il testo al client
resta **diverso fra le due linee** (v1 lo mostra, v2 no). Non è una violazione di FR-004, che riguarda i
guasti previsti; è una differenza che l'SDK impone e che D-1 ha accettato esplicitamente. In compenso
diventa **impossibile** che il testo grezzo di un'eccezione interna raggiunga il client su v2 — mentre
oggi accade, e `scrub_text` è applicato **solo** all'evento di osservabilità, non al payload.

**Effetto collaterale positivo, verificato sui test:** i quattro test che asseriscono il re-raise
(`test_tool_error_emits_event_and_reraises`, `test_combined_tool_error_emits_event_and_reraises`,
`test_tool_error_detail_is_secret_scrubbed`, `test_internal_error_propagates_then_server_recovers`)
sollevano `RuntimeError`, che **non** è un `SertorError`: restano verdi **senza modifiche**. Se la
mappatura fosse stata «tutte le eccezioni», sarebbero stati quattro test da riscrivere — e riscrivere un
test perché il codice è cambiato è il modo più comune di perdere ciò che il test presidiava.

**Alternative considerate e scartate.**
- *Mappare ogni eccezione a `ToolError`*: comportamento identico fra le linee anche per i crash, ma
  reintroduce l'inoltro del testo grezzo (che D-1 ha scelto di chiudere) e costa quattro test riscritti.
- *Mappare nel corpo di ogni tool*: dieci punti invece di uno, e `_guard` esiste proprio per questo.
- *Passare `scrub_text` sul messaggio dei `SertorError`*: **scartata per ora** — i messaggi di dominio
  sono scritti da noi e non contengono segreti; aggiungere lo scrub qui nasconderebbe il fatto che il
  canale-client non è scrubbato *in generale*. Se un domani un `SertorError` portasse un valore
  dall'ambiente, il posto giusto è il messaggio, non il canale.

---

## R-3 — Quali test esistenti presidiano FR-008 e FR-009

**Decisione: sono già presidiati, e i test sono nominati qui invece di essere presunti.** Era la riserva
n. 2 della checklist della spec.

**FR-008 (semantica di warm-up e self-test all'avvio) — 5 test in `tests/unit/test_mcp_server.py`:**

| Test | Proprietà presidiata |
|---|---|
| `test_main_warms_facade_before_stdio_loop` (:132) | la facade è costruita **prima** del loop stdio (il fix dell'hang su Windows) |
| `test_main_starts_server_even_if_warmup_fails` (:151) | un guasto di configurazione **non** impedisce l'avvio |
| `test_main_runs_self_test_before_stdio_loop` (:189) | il self-test gira all'avvio |
| `test_self_test_ok_on_healthy_facade` (:263) | esito positivo su facade sana |
| `test_self_test_is_loud_and_nonfatal_on_failure` (:272) | rumoroso su stderr **e** non fatale |

**FR-009 (nomi e campi degli eventi) — 6 test:** `test_main_wires_observability` (:175),
`test_tool_error_emits_event_and_reraises` (:205), `test_combined_tool_error_emits_event_and_reraises`
(:222), `test_tool_error_detail_is_secret_scrubbed` (:239),
`test_memory_search_does_not_log_query_in_clear` (:405),
`test_memory_search_semantic_does_not_log_query_in_clear` (:505).

**Conseguenza per il piano:** nessun requisito è scoperto, **ma** questi undici test oggi girano su una
linea sola. Il loro valore come presidio di FR-008/009 dipende da R-5: eseguiti su una linea sola,
presidiano metà di ciò che questa feature promette.

---

## R-4 — Dove si misura SC-005 (l'ospite con la major già risolta)

**Decisione: un SETTIMO esito nell'upgrade smoke, con la condizione PIANTATA.** Era la riserva n. 3
della checklist: il dogfood non può misurarlo, perché il suo runtime insegue l'ultimo commit e non
ri-risolve mai le dipendenze (→ [[dogfood-fidelity]]).

L'upgrade smoke (`upgrade-smoke-full.yml` + `tests/integration/test_host_smoke.py`) già fa la cosa
giusta: installa su un host usa-e-getta **la release precedente**, aggiorna, e il wrapper **esige sei
esiti per nome** (`pin-moved`, `host-config-preserved`, `mcp-invocation-shape`, `no-stale-divergence`,
`version-derived-from-runtime`, `health-green`) con un'asserzione anti-vacuità esplicita — *«exit code 0
says the script did not fail; it does NOT say the outcomes were asserted»*.

**Il settimo esito: `mcp-server-imports`.** Sequenza, sull'host usa-e-getta:

1. si installa la release precedente (come già oggi);
2. **si pianta la condizione**: il runtime dell'host viene forzato a risolvere `mcp` **2.x** — è
   esattamente lo stato in cui si trovano *Noetix* e *VM-WorkingFolder*, e in quello stato il server
   **non parte**;
3. si asserisce che in quello stato l'import **fallisce** (senza questa asserzione il resto sarebbe
   vacuo: se la condizione non fosse stata piantata, il passo 5 passerebbe per la ragione sbagliata);
4. si esegue l'upgrade;
5. si asserisce che l'import del modulo server **riesce**.

**Rationale.** È il pattern della **forma 2** di [[guardia-verde-non-e-una-misura]]: *le due fonti che
concordano per costruzione*. Un host appena creato risolve già la versione buona, quindi «il server parte
dopo l'upgrade» passerebbe **gratis**, senza aver misurato nulla. Piantare la condizione — e asserire che
*prima* fallisse — è ciò che rende l'esito una misura. Lo stesso mestiere che l'esito
`version-derived-from-runtime` fa già piantando uno stamp che resta indietro.

> **⚠️ Cosa l'esito NON discrimina, misurato eseguendolo (2026-09-13).** Asserisce che un host colpito
> finisce l'upgrade con un server che parte — ciò che all'ospite interessa — ma **due meccanismi diversi
> possono soddisfarlo**: il *tetto* che riporta l'SDK alla linea vecchia, o il *codice* che ora regge
> quella nuova. Sul salto corrente il merito è del tetto. Chi misura il **porting** è il passo CI
> sull'altra linea (R-5): i due presidi coprono cose diverse e nessuno sostituisce l'altro. Dirlo è
> parte dell'esito: un presidio di cui si crede che misuri altro è peggio di uno assente.

**Come è stata piantata la condizione, e le due cose che sono state imparate provandolo.** Non serve
aggiungere `mcp>=2` al manifest — una prima versione lo faceva, e **rompeva il comando sotto test**
lasciando un vincolo che nessun host reale ha. Basta **pinnare `sertor-core` alla release di partenza**,
che non ha tetto, e forzare la **ri-risoluzione del solo SDK** (`--upgrade-package mcp`): `uv sync` nudo
è conservativo e terrebbe la 1.x del lock, quindi non pianterebbe nulla. È esattamente il meccanismo che
ha colpito il campo — *Noetix* è stato rotto dal **terzo comando della nostra procedura di upgrade**,
`uv sync --upgrade`, due giorni dopo l'uscita della major.

Il pin è necessario per una ragione che vale la pena registrare: **l'installer scrive la sorgente del
runtime come riferimento git nudo**, quindi il runtime segue il **ramo di default**, non la release da cui
l'installer proviene. Misurato: un install «della v0.4.1» ha prodotto un runtime che risolve
`sertor-core 0.4.1 (de31fe6)` — un commit del ramo di default. Ne segue un difetto **collaterale**, che
non appartiene a questa feature ma è stato promosso perché non si perda: **E10-FEAT-077**.

**Alternative considerate e scartate.**
- *Misurarlo sul dogfood*: **impossibile per costruzione**, non per pigrizia (il runtime segue HEAD).
- *Dedurlo dal vincolo nel manifest*: è esattamente la deduzione che ha nascosto il difetto originale
  per dieci giorni — «fidarsi del lock». Scartata per principio.
- *Un test unitario che simuli il lock*: non misura un host, misura una simulazione. SC-005 parla di un
  ospite reale che aggiorna.

---

## R-5 — Come si eseguono i test MCP su entrambe le linee (D-3)

**Decisione: un passo aggiuntivo nel job di test della CI**, che ri-esegue **solo** i test che toccano
`sertor_mcp` con l'altra linea dell'SDK installata, usando l'isolamento che `uv` offre già
(`uv run --with "mcp==<versione>"`), senza toccare il lock del workspace.

I test coinvolti sono sei file: `tests/unit/test_mcp_server.py` (29 test),
`tests/unit/test_mcp_graph_tools.py`, `tests/unit/test_mcp_combined_graph.py`,
`tests/unit/test_score_contract.py`, `tests/unit/test_doctor.py`, `tests/unit/test_single_venv_guard.py`.

**Rationale.** R-1 introduce un ramo di fallback: se la CI gira su una linea sola, quel ramo **non viene
mai attraversato** e si romperà in silenzio — R-1 della spec, e la ragione per cui D-3 esiste. Il passo
aggiuntivo costa una risoluzione di dipendenze e ~35 test, non una seconda matrice.

**Il presidio contro la vacuità è obbligatorio, non opzionale.** Un passo che installa l'altra linea e
poi esegue i test **senza verificare quale linea sia attiva** è indistinguibile da un passo che non ha
cambiato nulla. Per questo `SDK_LINE` (R-1) è un valore derivato: un test asserisce che la linea attiva è
quella attesa, **leggendola dall'import riuscito**, e quel test è il primo a girare nel passo. Senza di
esso avremmo aggiunto un job verde che non misura — la quarta volta che questo progetto ci inciampa.

**Alternative considerate e scartate.**
- *Raddoppiare la matrice OS × Python × linea SDK*: costo alto, informazione quasi nulla (il porting non
  interagisce con OS o versione di Python).
- *Un `tox`/`nox` dedicato*: dipendenza nuova per un problema che `uv --with` risolve.
- *Lasciare il ramo non testato e fidarsi della revisione*: è la condizione di partenza del difetto che
  stiamo riparando.

---

## R-6 — Il tetto `<2.3` e il promemoria che lo rende sicuro (D-2)

**Decisione: `mcp>=1.2,<2.3` nei due punti in cui è dichiarato**, con un commento che nomina la versione
misurata (2.2.0), la data e la condizione per alzarlo. **Il promemoria non appartiene a questa feature**:
la sua casa è **E10-FEAT-071**, estesa il 2026-09-13 per coprire i due versi del problema.

**Rationale.** L'utente ha scelto il pin stretto *a condizione* che l'uscita di una versione successiva
produca una notifica e una voce di backlog. La condizione è parte della decisione, quindi va **scritta
dove qualcuno la leggerà** — e il posto non è questa feature, che verrà chiusa, ma il backlog della
guardia. Fino a quel momento il pin è sorvegliato dalla sola memoria umana: è il rischio **R-6** della
spec, dichiarato invece che presunto risolto.

> **La simmetria che vale la pena tenere:** un vincolo **senza tetto** produce un difetto che colpisce chi
> risolve — visibile, segnalato dal campo in dieci giorni. Un vincolo **troppo strettо** produce un difetto
> che non colpisce nessuno: nessuno lo segnala, e resta lì. *Un tetto senza promemoria è debito con una
> data di scadenza che nessuno legge.*

**Alternative considerate e scartate.** `<3` (scartata dall'utente in D-2: ammetterebbe minor non
misurate); nessun tetto (è il difetto originale); alzare il tetto **e** portare il codice alla 2.x come
unica linea supportata (romperebbe gli ospiti col lock su 1.x che non ri-risolvono — FR-002/FR-010).

---

## Perimetro del non misurato — dichiarato, non presunto

Le sonde hanno coperto: handshake stdio, `initialize`, `list_tools`, `call_tool` su tre forme di ritorno,
`isError`, `structuredContent`, contenuto testuale, e il comportamento di `ToolError` /
`UnexpectedToolError`. **Non** hanno coperto: cancellazione di una richiesta in volo, timeout, payload di
grandi dimensioni, invocazioni concorrenti, e le superfici che non usiamo (resources, prompts, auth,
middleware). Queste restano **non misurate**: lo smoke d'installazione reale le esercita indirettamente,
ma nessuna asserzione le riguarda.
