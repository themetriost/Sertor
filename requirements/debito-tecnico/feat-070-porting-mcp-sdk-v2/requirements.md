# Requisiti — Porting del server MCP all'SDK v2

<!-- Deriva da: E10-FEAT-070 (epica `debito-tecnico`) -->

> **Stato dell'evidenza:** ogni affermazione fattuale di questo documento è stata **misurata il
> 2026-09-13** su `mcp` **2.2.0** e **1.29.0**, con due sonde: una sulle firme dell'API e una
> **end-to-end sul transport stdio con un client MCP reale**. Quest'ultima colma il buco che la riga di
> backlog dichiarava aperto (*«l'handshake stdio end-to-end con un client vero»*). Dove un fatto è
> dedotto e non osservato, è detto.

## 1. Contesto e problema (perché)

`src/sertor_mcp/server.py` costruisce il server sull'SDK MCP **v1**: importa `mcp.server.fastmcp`
(`:25`) e istanzia `FastMCP` (`:112`). L'SDK ha rilasciato la **2.0.0 il 2026-07-28** rimuovendo quel
sottomodulo; la versione attuale è la **2.2.0**. Poiché `sertor-core` dichiarava `mcp>=1.2` senza
limite superiore, un ospite che risolveva le dipendenze dopo quella data otteneva la major nuova e il
server **moriva all'import**: nessun tool servito, e `sertor-rag doctor` verde
(→ [[guardia-verde-non-e-una-misura]], E10-FEAT-072).

Il **tetto `mcp>=1.2,<2`** (consegnato il 2026-08-07) ha fermato l'emorragia sulle installazioni che
risolvono da quel momento. Non ha chiuso il tema, per tre ragioni distinte:

1. **Il codice resta su una linea in sola manutenzione.** Un tetto è una scelta su *quando* scoprire la
   major, non un modo per non scoprirla: la 1.x a monte riceve ormai solo correzioni critiche.
2. **Chi ha già la 2.x nel proprio lock non guarisce.** Tre nodi della federazione lo hanno misurato
   (*Vestiger* 07/08, *Noetix* 02/09, *VM-WorkingFolder* 07/09): due di essi sono **CLI-only da 34 e 36
   giorni**, e *non* sono installazioni nuove — il perimetro reale comprende chiunque abbia ri-risolto
   dopo il 28/07, cioè chiunque abbia seguito la nostra procedura di upgrade
   (→ [[difetto-che-solo-un-ospite-nuovo-puo-vedere]]).
3. **Il tetto non è in nessuna release.** `git tag --contains dd76dc3` è vuoto: la riparazione vive su
   `master` dal 07/08 e l'ultima release è la v0.4.1 del 31/07. Per chi installa *per versione* la
   riparazione **non esiste**.

Il porting è ciò che chiude tutte e tre: un server che funziona su **entrambe** le linee guarisce anche
i lock già congelati sulla 2.x, **senza chiedere nulla all'ospite** oltre l'aggiornamento di
`sertor-core`.

### Il fatto che cambia la forma del lavoro

La perdita del messaggio d'errore su v2 **non è un difetto dell'SDK: è un suo design deliberato**, e il
suo stesso codice lo dichiara. `mcp.server.mcpserver.exceptions` distingue due casi:

| Eccezione | Cosa riceve il client |
|---|---|
| **`ToolError`** — *«a failure you anticipated»* | `is_error=True` **con il tuo messaggio nel `content`, perché il modello lo legga** |
| **`UnexpectedToolError`** — un crash, la solleva l'SDK | messaggio generico; *«the original text is withheld from the client»* |

In v1 **ogni** eccezione passava il proprio testo al client. Il porting, quindi, non deve *aggirare* la
v2: deve **classificare** i nostri errori. E la classificazione **esiste già nel dominio** — non va
inventata: `src/sertor_core/domain/errors.py` definisce `SertorError` con undici sottoclassi
(`IndexNotFoundError`, `EmbeddingError`, `VectorStoreError`, `ConfigError`, `GraphNotFoundError`,
`ProviderMismatchError`, `IndexLockedError`, `SessionNotFoundError`, …), che sono **esattamente** i
guasti previsti. Anche il contratto è già scritto: il commento di `main()` (`server.py:570`) promette
che *«the actionable error surfaces through `_guard` as a tool error — not as a dropped connection»*.

Oggi quella promessa è mantenuta per accidente (v1 inoltra tutto). Il porting la rende **deliberata**, e
nel farlo smette di inoltrare al client il testo grezzo di eccezioni interne — che è la direzione della
regola standing *errori MCP = segnale, non rumore*, non un compromesso con essa.

## 2. Obiettivi e criteri di successo

**Obiettivo:** il server MCP funziona, con contratto invariato verso l'agente, su **entrambe** le linee
dell'SDK supportate, e i guasti previsti restano **diagnosticabili dal client**.

| ID | Criterio di successo (misurabile) | Valore oggi |
|---|---|---|
| **SC-001** | Lo stesso codice, eseguito in un ambiente con `mcp==1.29.0` **e** in uno con `mcp==2.2.0`, completa l'handshake stdio ed espone **10 tool** con gli stessi nomi | **1 / 2** (su 2.2.0 muore all'import) |
| **SC-002** | Un guasto previsto (indice assente) arriva al client con `is_error=True` **e** il testo diagnostico del core, su entrambe le linee | **1 / 2** (v2 rende `Error executing tool X` e perde il dettaglio) |
| **SC-003** | Il vincolo di dipendenza ammette entrambe le linee in **tutti** i punti in cui è dichiarato (`pyproject.toml:52` extra `mcp`, `:91` extra `dev`) | **0 / 2** (oggi `<2`) |
| **SC-004** | Esiste almeno un test che esercita il server **parlando il protocollo** (non l'helper interno) e che fallisce se il server non parte | **0** test |
| **SC-005** | Un ospite il cui lock è già su `mcp` 2.x ottiene un server funzionante aggiornando **solo** `sertor-core`, senza ri-risolvere il lock | **non soddisfatto** |
| **SC-006** | Gate pre-merge: le sette suite (≈2616 test) e `ruff` verdi; gli smoke d'installazione (che dal 2026-08-07 girano sui cambi di dipendenza) verdi | — |

## 3. Stakeholder e attori

- **L'agente conversazionale dell'ospite** — consumatore dei tool: gli interessa che i tool esistano e
  che un guasto gli dica *cosa* è rotto. È il portatore di SC-002.
- **L'ospite (progetto terzo)** — installa/aggiorna `sertor-core`; non deve dover rattoppare a mano
  (i nodi hanno **esplicitamente rifiutato** di mettersi un tetto locale, perché il file lo rigenera il
  nostro installer).
- **Il dogfood di Sertor** — usa il server a ogni sessione, ma **non** è un rilevatore per questa classe
  di guasti: il suo runtime insegue HEAD e non ri-risolve mai (→ [[dogfood-fidelity]]).
- **Il manutentore** — deve poter alzare il tetto di major senza riscrivere i dieci tool.

## 4. Ambito

### In ambito

- Ottenere la classe del server dall'SDK in modo che funzioni su **entrambe** le linee supportate.
- Preservare invariati i **10 tool** (nomi, parametri, forme di ritorno, descrizioni, `instructions`).
- **Classificare gli errori**: i guasti previsti del core restano leggibili dal client su ogni linea.
- Allargare il **vincolo di dipendenza** nei due punti in cui è dichiarato.
- Un **test end-to-end sul protocollo**, che oggi non esiste.
- Aggiornare la **documentazione utente** (`docs/troubleshooting.md`, che oggi descrive il guasto e
  prescrive un rimedio da rivedere) e il commento che motiva il tetto in `pyproject.toml`.

### Fuori ambito — *ognuno con una casa durevole, nessuno lasciato qui*

- **`structuredContent` assente sui 5 tool che ritornano `dict`** → **E10-FEAT-076** (promossa il
  2026-09-13). *Misurato identico su 1.29.0 e 2.2.0: è il nostro design, non il porting.*
- **`doctor` che verifica la registrazione e non l'avvio** → **E10-FEAT-072**. Questa feature **non** lo
  chiude, ma lo rende più urgente: finché `doctor` non avvia il server, nulla presidia SC-001 sull'host.
- **Guardia sui vincoli di dipendenza senza tetto di major** → **E10-FEAT-071**.
- **Riscrivere l'architettura del server** (resources, prompts, middleware, auth: superfici nuove
  dell'SDK v2) — non serve al problema.

### Dipendenza di completamento (non fuori ambito, *non ancora fatta qui*)

Per la regola *una feature è completa solo se è installabile su un ospite*, questa capacità **non è
«done» finché non raggiunge gli ospiti**: serve una **release** che la porti (i nodi pinnati a un tag
non possono prenderla da `master`) e la **risposta alla domanda aperta in bacheca**, che ha undici
giorni. Sono attività di consegna, tracciate come tali, non requisiti funzionali.

## 5. Requisiti funzionali (EARS)

- **REQ-001** *(Ubiquitous)* — The MCP server shall expose its ten tools with unchanged names,
  parameters, descriptions and result shapes, whichever supported SDK line is resolved.
- **REQ-002** *(Event-driven)* — When the server module is imported, the server shall obtain its server
  class from the MCP SDK v2, and, if the v2 import fails, from the v1 line, so that tool registration
  is identical in both cases.
- **REQ-003** *(Unwanted behaviour)* — If neither supported SDK line provides a usable server class,
  then the module shall fail at import with a message naming the installed `mcp` version and the
  supported range, and shall not fail with a bare `ModuleNotFoundError` on an internal submodule.
- **REQ-004** *(Event-driven)* — When a tool body raises a `SertorError` — an anticipated failure such
  as a missing index, an unreachable embedding provider, a missing extra or a locked index — the server
  shall return a tool error whose content carries the core's diagnostic message, on **every** supported
  SDK line.
- **REQ-005** *(Event-driven)* — When a tool body raises any exception that is not a `SertorError`, the
  server shall record the `mcp.<tool>.error` observability event and return a tool error identifying the
  tool, without placing the raw exception text in the client payload.
- **REQ-006** *(Ubiquitous)* — The `mcp` dependency constraint shall admit both supported lines up to the
  measured minor (`>=1.2,<2.3`) in every place it is declared, and shall carry a comment naming the
  measured version and the condition for raising the ceiling.
- **REQ-007** *(Event-driven)* — When the test suite runs, it shall exercise the server over the stdio
  transport with a real MCP client, asserting the handshake, the ten tool names, the payload of one
  `list[dict]` tool, and the diagnostic content of one anticipated failure.
- **REQ-008** *(Optional feature)* — Where the resolved SDK is v2, the startup warm-up and the
  end-to-end self-test shall keep their current semantics: non-fatal, loud on stderr, and never
  preventing the server from starting.
- **REQ-009** *(Ubiquitous)* — The observability events emitted per tool call (`mcp.<tool>`,
  `mcp.<tool>.error`, `mcp.self_test`) shall keep their current names and fields on both lines.
- **REQ-010** *(Event-driven)* — When a host whose lock already resolves `mcp` 2.x updates
  `sertor-core` to this version, the server shall start and serve its tools without the host having to
  re-resolve its lock.
- **REQ-011** *(Ubiquitous)* — The user-facing troubleshooting documentation shall state the supported
  `mcp` range and the action an already-affected host must take.
- **REQ-012** *(Event-driven)* — When continuous integration runs the MCP server tests, it shall run them
  against **both** supported SDK lines, so that neither branch of the import fallback stays unexecuted.

## 6. Requisiti non funzionali

- **Compatibilità.** Il contratto verso l'agente è invariato: nessun consumatore deve accorgersi della
  linea SDK sottostante, **tranne** per il miglioramento di REQ-004/005.
- **Isolamento delle dipendenze.** L'SDK resta confinato nell'extra `mcp`: `sertor-core` senza quell'extra
  non deve importarlo (vincolo architetturale già in essere).
- **Avvio.** Nessuna regressione sul tempo di avvio (oggi ~1s di warm-up, entro il timeout di 30s del
  client): la scelta della classe è un import, non una probe di rete.
- **Osservabilità.** Un guasto resta visibile in **due** canali (evento persistito + payload al client);
  REQ-005 riduce ciò che finisce nel secondo, non nel primo.
- **Host-agnosticità.** Nessun percorso o comando specifico d'assistente nel codice o nella doc.

## 7. Vincoli, assunzioni e dipendenze

**Vincoli**
- Si accede al server solo via vehicles (Principio XI): niente import di `sertor_core` nei consumatori.
- Branch + PR, gate pre-merge completo (sette suite + `ruff`) prima del merge.
- La documentazione utente si aggiorna **nello stesso step** (regola standing 3).

**Assunzioni** *(e come sono state verificate)*
- `MCPServer` è importabile da `mcp.server` **e** da `mcp.server.mcpserver` su 2.2.0 — **osservato**.
- `instructions=`, `.tool(description=…)`, `@tool()` con docstring e `.run(transport='stdio', **kwargs)`
  hanno la stessa forma sulle due linee — **osservato**.
- Il payload dei tool `list[dict]` è identico sulle due linee (`{"result": [...]}`) — **osservato sul
  protocollo**.
- I dieci decoratori non richiedono modifiche — **dedotto** dalle firme osservate, da confermare
  eseguendo la suite sulle due linee.

**Dipendenze**
- Lo smoke d'installazione copre i cambi di dipendenza dal 2026-08-07 (stessa PR del tetto): questa
  feature sarà esercitata da un'installazione reale, non solo dagli unit test.
- La consegna agli ospiti dipende da una release (vedi §4).

## 8. Rischi

| ID | Rischio | Mitigazione |
|---|---|---|
| **R-1** | Un `try/except ImportError` sull'import diventa un **ramo mai eseguito** in CI: si testa una linea sola e l'altra marcisce | **Deciso (D-3):** REQ-007 + REQ-012, i test MCP girano su **entrambe** le linee. È la lezione di [[guardia-verde-non-e-una-misura]] — un ramo che nessuna esecuzione attraversa non è coperto |
| **R-2** | Allargare il vincolo a due major fa **ri-risolvere** gli ospiti verso la 2.x insieme al nostro aggiornamento: se il porting ha un difetto, lo prendono tutti | il test end-to-end come gate + lo smoke d'installazione reale; il difetto non sarebbe più «invisibile a chi ha già risolto» |
| **R-3** | La classificazione degli errori **cambia ciò che il client vede** per le eccezioni non-`SertorError`: un guasto non previsto diventa meno esplicito nel payload | l'evento persistito resta completo; la diagnosi si sposta nel canale giusto. **È un cambio deliberato: va dichiarato all'utente, non introdotto di soppiatto** (vedi §10) |
| **R-4** | Un `SertorError` sollevato **fuori** dal corpo di un tool (nel warm-up, o dentro un generatore valutato dopo il ritorno) sfugge alla classificazione | il warm-up ha già la sua gestione (`main()`); da verificare per i tool che costruiscono strutture annidate |
| **R-5** | La 2.x introduce un comportamento divergente **non** coperto dalle sonde (cancellazione, timeout, payload grandi, concorrenza) | perimetro dichiarato: le sonde coprono handshake, elenco tool, payload e errori. Il resto è **non misurato**, e va detto invece di essere presunto |
| **R-6** | **Il tetto `<2.3` diventa un tetto dimenticato.** È il rischio che D-2 crea scegliendo il pin stretto: senza un avviso, l'uscita della 2.3 ci lascia su una versione vecchia **in silenzio** — nessun ospite se ne accorge, perché tutto funziona. È la stessa classe del difetto originale col segno invertito: là un vincolo troppo largo, qui uno troppo strettо e nessuno che lo riveda | **Condizione della decisione, non mitigazione opzionale:** serve una notifica + una voce di backlog all'uscita di una versione a monte. Casa del meccanismo: **E10-FEAT-071**, estesa a coprire i due versi («ammettiamo una major non uscita?» *e* «è uscita una versione sopra il nostro tetto?»). Finché non esiste, il pin resta sorvegliato solo dalla memoria umana — e va detto, non presunto |

## 9. Prioritizzazione (MoSCoW)

- **Must** — REQ-001, REQ-002, REQ-004, REQ-006, REQ-007, REQ-010: senza questi il porting non chiude
  il problema o non è verificabile.
- **Should** — REQ-003 (diagnosi d'import azionabile), REQ-005 (l'altra metà della classificazione),
  REQ-011 (documentazione utente: condizione di completamento).
- **Could** — REQ-008, REQ-009: proprietà esistenti da **non rompere**; costano una verifica, non un
  lavoro.
- **Won't (qui)** — le superfici nuove dell'SDK v2, `structuredContent` per i tool `dict` (FEAT-076),
  `doctor` che avvia il server (FEAT-072).

## 10. Decisioni e domande aperte

### Decisioni sciolte dall'utente (2026-09-13) — non ri-aprirle

- **D-1 — Errori non previsti: messaggio generico al client, diagnosi nei log.** Si adotta la
  distinzione di v2 (REQ-004 + REQ-005): i guasti *previsti* (`SertorError`) arrivano al client col loro
  messaggio diagnostico; un crash arriva come `Error executing tool <nome>`, col dettaglio nell'evento
  persistito e su stderr. *Conseguenza accettata:* per un bug nostro l'agente vede meno nel payload e
  deve guardare i log. *Guadagno:* smettiamo di inoltrare al client il testo grezzo di eccezioni interne
  — oggi `scrub_text` è applicato all'evento, **non** al payload.
- **D-2 — Tetto `>=1.2,<2.3`: si pinna alla minor misurata**, non `<3`. Ammette solo ciò che è stato
  davvero provato (2.2.0). **Condizione posta dall'utente, che è parte della decisione e non un auspicio:**
  quando esce una versione successiva a monte, **ci deve essere una notifica e una voce di backlog**.
  Senza quel meccanismo il pin stretto diventa un tetto *dimenticato* — la stessa classe di difetto che
  il tetto doveva chiudere, col segno invertito (→ R-6, e la casa del meccanismo è **E10-FEAT-071**,
  estesa il 2026-09-13 per coprire anche questo verso).
- **D-3 — La CI esegue i test del server MCP su entrambe le linee** (REQ-012), limitatamente ai test che
  toccano `sertor_mcp`. È la sola difesa reale contro R-1: un ramo che nessuna esecuzione attraversa non
  è coperto, per quanto verde sia il report.

### Ancora aperte

- **Fuori da questa feature, ma bloccante per la consegna:** la forma della **release** che porta il
  porting agli ospiti (i nodi pinnati a un tag non possono prenderlo da `master`) e il testo della
  **risposta in bacheca**, che ha undici giorni.
- **Non misurato, e dichiarato tale:** comportamento di v2 su cancellazione, timeout, payload grandi e
  concorrenza (R-5). Le sonde coprono handshake, elenco tool, payload e errori.
