# Feature Specification: `sertor-rag doctor` — verifica di salute deterministica (E12-FEAT-001)

**Feature Branch**: `074-doctor-salute` · **Created**: 2026-06-23 · **Status**: Draft

<!-- Deriva da: FEAT-001 (epica usabilità E12) — requirements/usabilita/sertor-rag-doctor/requirements.md -->

**Input**: FEAT-001 dell'epica `usabilita` (E12). Dopo `sertor install rag` + `sertor configure` non
esiste un modo **deterministico** per rispondere alla domanda più semplice e più importante: *«ha
funzionato?»*. Gli strumenti di stato esistono ma sono **sparsi e da esperto** — `eval validate-path`
per l'indice, `Settings.validate_backend()` per i campi env mancanti, il self-test del server MCP, gli
eventi di osservabilità — e nessuno offre un **quadro unico e azionabile**. La conseguenza: l'utente
scopre i problemi solo quando un comando d'uso fallisce, spesso con un errore non correlato alla causa
vera. Per riprova concreta, il probe `--check` del wizard `sertor configure` (E2/FEAT-003, US5) è
rimasto *deferred* da quando è stato costruito: il suo punto d'estensione invoca già
`sertor-rag check` in subprocess, ma quel comando **non esiste** nel core, quindi `--check` degrada
onestamente a «probe live non disponibile». Questa feature consegna la **primitiva deterministica** che
mancava: `sertor-rag doctor` fotografa lo stato di salute dell'installazione su **quattro aree** e per
ogni problema dice **causa + rimedio concreto**, con esito umano e `--json`, ed exit code non-zero se un
check critico fallisce. Una volta presente, il wizard chiude finalmente il suo `--check`.

---

> **Allineamento alla missione (gate Constitution).** L'usabilità è *periferica* al differenziatore di
> Sertor (qualità del retrieval reso all'agente), ma **serve l'adozione e la portabilità**: *un agente —
> o un umano — che sa verificare da solo se Sertor è sano su un ospite qualunque È host-agnosticità
> reale* (Principio X). `doctor` è il **substrato deterministico** su cui poggiano tutte le skill
> agentiche dell'epica (guided-setup, search-diagnose, concierge): senza un «ha funzionato?»
> verificabile, l'agente diagnostica alla cieca o dichiara «fatto» senza prova (Principio XII). Il
> comando è **puramente deterministico**: l'intelligenza e la spiegazione conversazionale vivono nelle
> skill dell'ospite, **il core non chiama mai un LLM** (confine D↔N, non negoziabile).

> **Natura del cambiamento: ADDITIVO.** `doctor` è un **comando nuovo** (NFR-5): non altera i comandi né
> i percorsi esistenti, non scrive sulla config, non tocca l'indice, non ha effetti collaterali. È sola
> lettura e diagnosi. Il cambiamento al pacchetto `sertor` (wizard `configure --check`) è **anch'esso
> additivo**: attiva un punto d'estensione già presente e oggi inerte, senza modificare il comportamento
> di `configure` quando `--check` non è richiesto.

> **Scope allargato oltre E12 (deciso con l'utente, dichiarato).** La feature tocca **due pacchetti**:
> - **`sertor-core`** — la primitiva `sertor-rag doctor` (il cuore della feature, owner E12).
> - **`sertor`** — il wizard `configure --check` (owner E2/FEAT-003): la feature chiude il debito
>   *deferred* cablando `--check` come **sottoinsieme config** che invoca `doctor`, con rimando a
>   `doctor` per il quadro completo. È uno scope deliberatamente allargato oltre i confini di E12,
>   segnalato qui esplicitamente perché il plan ne tenga conto (due suite di test, due owner d'epica).

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** I segnali che `doctor` legge
> esistono già e sono accertati: `Settings.validate_backend()` (`config/settings.py`) emette i nomi
> delle chiavi env mancanti per il provider/store selezionato; il **manifest del refresh incrementale**
> (`services/index_manifest.py`, file `<index_dir>/index_manifest.sqlite` namespaced per
> `(corpus,provider)`) persiste per ogni file sorgente `mtime + content_hash + logic_version` e i
> metadati di collezione — sufficiente a stabilire **presenza** (manifest/`index_dir` esistono?) e
> **freschezza** (last-index time, file modificati dall'ultima indicizzazione) **senza riscansionare il
> repo**; la registrazione MCP vive in `.mcp.json` (project scope) o nel registro del client (local
> scope); la redazione segreti esistente (`observability/scrub.py`/`redact`) si applica all'output.
> `configure --check` (`packages/sertor/src/sertor_installer/configure.py::_probe_live`) ha già il punto
> d'estensione che invoca `sertor-rag check`/probe in subprocess via il vehicle (Principio XI). I
> riferimenti a file ancorano i requisiti, **non** prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — «Ha funzionato?» in un comando (P1, Must)
Dopo aver installato e configurato Sertor su un ospite, l'utente (o l'agente che lo assiste) lancia un
solo comando e ottiene un quadro chiaro: configurazione/env, provider di embeddings, indice e server
MCP, ciascuno con un esito **pass / warn / fail**. Dove qualcosa non va, l'esito nomina la causa e il
rimedio concreto. Se tutto è verde, ha la prova deterministica che l'installazione è sana.

**Independent Test**: su un'installazione sana, `sertor-rag doctor` riporta le quattro aree tutte pass
ed esce con status zero; su un'installazione con un problema noto in un'area, quell'area è fail/warn,
l'output nomina causa e rimedio, e l'exit status è non-zero se il problema è critico.

**Acceptance**:
1. **Given** un'installazione sana, **When** lancio `sertor-rag doctor`, **Then** le quattro aree
   (env/config · provider embeddings · indice · MCP) sono riportate con esito per-area, tutte pass, ed
   exit status zero.
2. **Given** un'installazione con almeno un problema critico, **When** lancio `doctor`, **Then** l'area
   coinvolta è fail, l'output nomina causa e rimedio concreto, ed exit status è non-zero.
3. **Given** un problema non critico (warn), **When** lancio `doctor`, **Then** l'area è warn con
   rimedio suggerito ma l'exit status resta zero (warn non è gate).

### User Story 2 — Configurazione/env: cosa manca e quale chiave (P1, Must)
Quando la config del provider o dello store selezionato è incompleta, l'area env è in errore e l'output
nomina la **chiave d'ambiente esatta** mancante e come fornirla — senza che l'utente debba conoscere
quali chiavi richiede il backend scelto.

**Independent Test**: con un provider/store che richiede chiavi non valorizzate, l'area env è fail e
nomina ogni chiave mancante; con tutte le chiavi presenti, l'area env è pass.

**Acceptance**:
1. **Given** un provider/store selezionato a cui manca un valore richiesto, **When** lancio `doctor`,
   **Then** l'area env è fail e nomina la chiave d'ambiente esatta mancante e come fornirla.
2. **Given** un provider locale che non richiede credenziali, **When** lancio `doctor`, **Then** l'area
   env è pass (nessuna chiave richiesta è segnalata mancante).
3. **Given** la fonte dei campi richiesti è il validatore di configurazione esistente, **When**
   cambiano i campi richiesti per un backend, **Then** `doctor` riflette quel cambiamento senza una
   lista duplicata propria.

### User Story 3 — Indice: presente? fresco? (P1 presenza Must, P2 freschezza Should)
L'area indice dice se l'indice del corpus attivo **esiste** e, quando esiste, se è **fresco** o
**stantio** rispetto alle sorgenti — senza riscansionare l'intero repo. Indice assente o manifest
incompatibile → fail con il comando di re-index nominato; indice presente ma stantio → warn con
invito a ri-indicizzare.

**Independent Test**: senza indice/manifest l'area è fail e nomina il comando di re-index; con indice
fresco l'area è pass; con sorgenti modificate dopo l'ultima indicizzazione l'area è warn (stantio) e
riporta il momento dell'ultima indicizzazione.

**Acceptance**:
1. **Given** nessun indice per il corpus attivo (o manifest incompatibile), **When** lancio `doctor`,
   **Then** l'area indice è fail e nomina il comando di re-index da eseguire.
2. **Given** un indice presente e allineato alle sorgenti, **When** lancio `doctor`, **Then** l'area
   indice è pass e riporta il momento dell'ultima indicizzazione.
3. **Given** un indice presente ma con sorgenti modificate dall'ultima indicizzazione, **When** lancio
   `doctor`, **Then** l'area indice è warn (stantio) e suggerisce il re-index, usando i metadati del
   manifest (mtime/hash) e non un'euristica nuova né una riscansione completa.

### User Story 4 — Provider embeddings: config statica (Must) + raggiungibilità opt-in (Should)
Di default `doctor` verifica che la configurazione del provider di embeddings selezionato sia
**completa** (check statico, costo-rete-zero). Con un flag dedicato opt-in (es. `--online`/`--probe`),
esegue **in aggiunta** un probe minimale e non-indicizzante che riporta se il provider è
**raggiungibile** o **non-raggiungibile** e perché. Senza il flag, nessuna chiamata di rete.

**Independent Test**: senza il flag di rete, l'area provider riporta solo lo stato statico (config
completa/incompleta) e non genera traffico di rete; col flag, esegue un probe minimale che riporta
raggiungibile/non-raggiungibile con motivo, senza mai indicizzare.

**Acceptance**:
1. **Given** nessun flag di rete, **When** lancio `doctor`, **Then** l'area provider riporta solo lo
   stato statico della config del provider selezionato e non c'è traffico di rete.
2. **Given** il flag di rete attivo e un provider raggiungibile, **When** lancio `doctor`, **Then**
   l'area provider riporta «raggiungibile» tramite un probe minimale e non-indicizzante.
3. **Given** il flag di rete attivo e un provider non raggiungibile (offline, credenziali invalide),
   **When** lancio `doctor`, **Then** l'area provider riporta «non-raggiungibile» con il motivo, senza
   crash e senza tentare di indicizzare.

### User Story 5 — Server MCP: registrato? (Must statico, Should reachability) (P2)
L'area MCP riporta se il server `sertor-rag` è **registrato** nella configurazione dell'ospite (check
statico su `.mcp.json` / registro del client). Quando rilevabile, segnala una condizione di
**stantio-dopo-reindex** (il server serve un indice ricostruito e va riavviato).

**Independent Test**: con il server MCP registrato, l'area MCP è pass; senza registrazione è fail/warn
con l'indicazione di come registrarlo; la condizione stantio-dopo-reindex è segnalata quando rilevabile.

**Acceptance**:
1. **Given** il server `sertor-rag` registrato nella config dell'ospite, **When** lancio `doctor`,
   **Then** l'area MCP è pass.
2. **Given** nessuna registrazione del server MCP, **When** lancio `doctor`, **Then** l'area MCP segnala
   l'assenza con il rimedio (come registrarlo).
3. **Given** una condizione di stantio-dopo-reindex rilevabile, **When** lancio `doctor`, **Then** l'area
   MCP la segnala come warn invitando al riavvio del server.

### User Story 6 — Output machine-readable per skill e CI (P1, Must)
Oltre all'output umano, `doctor` produce un esito `--json` con **schema stabile**, così le skill di
usabilità (guided-setup, search-diagnose) e gli script CI lo consumano in modo affidabile. L'exit code
funge da gate: non-zero se un check critico fallisce, zero se tutti i check critici passano.

**Independent Test**: `doctor --json` produce un documento con uno schema stabile che riporta le aree e
i rispettivi esiti; l'exit status è non-zero quando un'area critica è fail e zero altrimenti.

**Acceptance**:
1. **Given** una skill/uno script consumatore, **When** invoca `doctor --json`, **Then** riceve un
   esito strutturato con schema stabile (le quattro aree + esito + dettagli per problema).
2. **Given** un check critico fallito, **When** lancio `doctor` (umano o `--json`), **Then** l'exit
   status è non-zero; **Given** tutti i check critici passano, **Then** l'exit status è zero.
3. **Given** un output che conterrebbe un segreto, **When** `doctor` lo emette, **Then** il segreto è
   redatto (la redazione esistente si applica all'output umano e JSON).

### User Story 7 — Offline-safe by default (P1 statici Must, P2 degrado Should)
I check statici (env, presenza indice, config provider, registrazione MCP) funzionano **offline** e non
richiedono rete. I check che richiedono rete (raggiungibilità provider, eventuale reachability MCP)
sono attivati solo dal flag opt-in e, se l'ambiente è offline, degradano onestamente (skipped/unknown),
mai con un crash.

**Independent Test**: senza connettività, `doctor` (senza flag di rete) completa e riporta tutti i
check statici; col flag di rete ma offline, i check di rete sono segnalati skipped/unknown e il comando
non va in errore non gestito.

**Acceptance**:
1. **Given** un ambiente offline e nessun flag di rete, **When** lancio `doctor`, **Then** i check
   statici girano e riportano regolarmente; non c'è alcuna chiamata di rete.
2. **Given** il flag di rete attivo ma l'ambiente offline, **When** lancio `doctor`, **Then** i check di
   rete degradano a skipped/unknown con motivo, senza crash.
3. **Given** qualunque combinazione di flag, **When** lancio `doctor`, **Then** il comando non altera la
   config né l'indice (sola lettura, nessun effetto collaterale).

### User Story 8 — `configure --check` reso vivo (P1, Must) — scope esteso a `sertor`
Il probe `--check` del wizard `sertor configure`, oggi *deferred*, diventa operativo: invoca `doctor`
come **sottoinsieme config** e rimanda a `doctor` per il quadro completo (provider/indice/MCP).
L'utente che esegue `sertor configure --check` ottiene così una verifica reale invece del messaggio
«probe live non disponibile».

**Independent Test**: su un'installazione configurata, `sertor configure --check` esegue la verifica
config tramite `doctor` (non più il degrado «non disponibile») e rimanda a `doctor` per il quadro
completo; il comportamento di `configure` senza `--check` resta invariato.

**Acceptance**:
1. **Given** un'installazione configurata, **When** eseguo `sertor configure --check`, **Then** la
   verifica config è eseguita tramite `doctor` (il punto d'estensione non degrada più a «non
   disponibile») e l'esito rimanda a `doctor` per le altre aree.
2. **Given** `sertor configure` senza `--check`, **When** lo eseguo, **Then** il comportamento è
   identico a oggi (additività: `--check` è l'unico percorso toccato).
3. **Given** il vehicle `sertor-rag doctor` non disponibile sul runtime (versione disallineata), **When**
   eseguo `configure --check`, **Then** degrada onestamente (come oggi), senza crash.

## Edge Cases
- **Installazione sana**: tutte le aree pass, exit zero.
- **Env incompleto**: ogni chiave mancante per il provider/store selezionato è nominata; locale senza
  credenziali → nessuna chiave segnalata.
- **Indice assente vs stantio**: assente/manifest incompatibile → fail + comando di re-index nominato;
  presente ma sorgenti modificate dopo l'ultima indicizzazione → warn (stantio); presente e allineato →
  pass. La distinzione usa i metadati del manifest, non una riscansione né un'euristica nuova (no falsi
  positivi su `sources` larghi).
- **Provider non configurato**: area provider fail al check statico (config incompleta), indipendente
  dal flag di rete.
- **Provider configurato ma irraggiungibile** (solo col flag di rete): non-raggiungibile + motivo, mai
  un'indicizzazione di prova.
- **Offline senza flag di rete**: tutti i check statici girano; nessuna chiamata di rete.
- **Offline con flag di rete**: i check di rete → skipped/unknown con motivo, mai crash.
- **MCP non registrato**: segnalato con il rimedio; **MCP registrato ma indice ricostruito**:
  stantio-dopo-reindex segnalato come warn (quando rilevabile).
- **Output con potenziale segreto**: redatto in output umano e JSON.
- **Solo un'area critica fallisce**: exit non-zero anche se le altre passano.
- **`configure --check` su runtime senza `doctor`**: degrado onesto, nessun crash.
- **Comando puramente diagnostico**: nessuna scrittura su config/indice in qualunque scenario.

## Requirements *(mandatory)*

### Requisiti funzionali

**Quadro per-area e azionabilità**
- **FR-001 (quadro quattro aree).** Quando `sertor-rag doctor` è invocato, il sistema riporta lo stato
  delle quattro aree — configurazione/env, provider di embeddings, indice (presenza + freschezza),
  server MCP — con un esito per-area pass/warn/fail. *(REQ-001; CS-1)*
- **FR-002 (azionabilità).** Per ogni area non-pass il sistema nomina la causa e il rimedio concreto
  (chiave mancante, provider non raggiungibile, indice assente/stantio, MCP non registrato). *(CS-2)*

**Configurazione/env**
- **FR-003 (chiave mancante nominata).** Se un valore di configurazione richiesto dal provider/store
  selezionato è mancante, il sistema lo riporta nominando la chiave d'ambiente esatta e come fornirla.
  *(REQ-002)*
- **FR-004 (fonte unica dei campi).** I campi richiesti derivano dalla fonte di validazione della
  configurazione esistente (`Settings.validate_backend()`), non da una lista duplicata propria
  (host-agnostico: ciò che varia sta in config). *(REQ-002, NFR-2)*

**Indice (presenza + freschezza)**
- **FR-005 (indice assente → fail).** Mentre l'indice per il corpus attivo è assente o il suo manifest è
  incompatibile, il sistema riporta l'area indice come fail e nomina il comando di re-index. *(REQ-003)*
- **FR-006 (freschezza).** Dove l'indice esiste, il sistema riporta la sua freschezza (momento
  dell'ultima indicizzazione e se le sorgenti sono cambiate da allora), così un indice stantio è reso
  visibile, usando i metadati del manifest (mtime/hash) coerenti col refresh incrementale e **senza**
  riscansionare il repo. *(REQ-004)*

**Provider embeddings (statico + opt-in rete)**
- **FR-007 (config provider statica).** Il sistema verifica staticamente che la configurazione del
  provider di embeddings selezionato sia completa, a costo-rete-zero, indipendentemente dal flag di rete.
  *(REQ-001/CS-5)*
- **FR-008 (probe raggiungibilità opt-in).** Dove è richiesta una verifica di raggiungibilità del
  provider (flag opt-in dedicato), il sistema esegue un probe minimale e **non-indicizzante** tramite il
  vehicle e riporta raggiungibile / non-raggiungibile con il motivo. *(REQ-005)*

**Server MCP**
- **FR-009 (MCP statico + stantio).** Dove il server MCP è configurato, il sistema riporta se è
  registrato (check statico sulla config dell'ospite) e segnala una condizione di stantio-dopo-reindex
  quando rilevabile. *(REQ-006)*

**Esito strutturato e gate**
- **FR-010 (output JSON a schema stabile).** Il comando emette un esito machine-readable (`--json`)
  oltre a quello umano, con uno schema stabile per il consumo da parte delle skill. *(REQ-007)*
- **FR-011 (exit code gate).** Se un qualsiasi check critico fallisce, il comando esce con status
  non-zero; esce zero quando tutti i check critici passano. *(REQ-008)*

**Offline-safe e privacy**
- **FR-012 (offline-safe by default).** Mentre l'ambiente è offline, i check statici (env, presenza
  indice, config provider, registrazione MCP) girano e riportano; i check che richiedono rete degradano
  onestamente (skipped/unknown), non in crash. *(REQ-009)*
- **FR-013 (zero segreti in output).** Se un campo di output conterrebbe un segreto, il sistema non lo
  include (la redazione esistente si applica all'output umano e JSON). *(REQ-010, NFR-4)*

**Diagnostica, non riparazione**
- **FR-014 (sola lettura).** Il comando diagnostica e non ripara né altera config o indice: nessun
  effetto collaterale in qualunque scenario (l'auto-fix guidato è guided-setup, fuori ambito). *(NFR-1,
  ambito §Fuori ambito)*
- **FR-015 (nessun LLM).** Il comando è puramente deterministico: non effettua alcuna chiamata a un LLM
  (confine D↔N). *(REQ-E1 d'epica, Fuori ambito)*

**Cablaggio `configure --check` (scope esteso a `sertor`)**
- **FR-016 (`--check` invoca `doctor`).** Il probe `--check` del wizard `sertor configure` (oggi
  *deferred*) invoca `doctor` come sottoinsieme config e rimanda a `doctor` per il quadro completo.
  *(epica DA-D3; debito E2/FEAT-003 US5)*
- **FR-017 (`configure` invariato senza `--check`).** Il comportamento di `sertor configure` senza
  `--check` resta identico a oggi (additività). *(NFR-5)*
- **FR-018 (degrado onesto di `--check`).** Se il vehicle `doctor` non è disponibile sul runtime,
  `configure --check` degrada onestamente senza crash (comportamento odierno preservato). *(NFR-1)*

### Requisiti non funzionali
- **RNF-1 (deterministico/veloce):** i check statici sono deterministici e completano in tempi
  trascurabili; nessun effetto collaterale su indice o config. *(NFR-1)*
- **RNF-2 (host-agnostico, Principio X):** funziona su qualunque ospite; ciò che varia sta in config,
  non in assunzioni hardcoded. *(NFR-2)*
- **RNF-3 (vehicle-only, Principio XI):** accede alle capacità via i percorsi pubblici (CLI/factory
  `build_*`), non reimplementa logica del core né importa internamente per scorciatoie; la cattura dei
  segnali avviene attraverso il vehicle. *(NFR-3)*
- **RNF-4 (privacy):** zero segreti nell'output; il probe provider non logga chiavi. *(NFR-4)*
- **RNF-5 (additività):** comando nuovo, non altera comandi/percorsi esistenti; il cablaggio di
  `configure --check` attiva un punto d'estensione esistente senza cambiare `configure` altrimenti.
  *(NFR-5)*
- **RNF-6 (offline & deterministico):** i check statici non producono traffico di rete; quelli di rete
  sono opt-in e degradano onestamente offline. *(REQ-009, CS-5)*
- **RNF-7 (snapshot, non storicizzazione):** `doctor` è uno snapshot puntuale, non duplica lo store di
  osservabilità (la storicizzazione resta a E3). *(R-3)*

### Key Entities
- **Report di salute** — l'esito strutturato del comando: insieme delle quattro aree, ciascuna con
  esito (pass/warn/fail) ed eventuali problemi (causa + rimedio); reso umano e `--json` (schema stabile).
- **Area di salute** — una delle quattro dimensioni diagnosticate: env/config, provider embeddings,
  indice, server MCP; ognuna con esito e dettagli.
- **Esito per-area** — pass / warn / fail; i fail critici determinano l'exit code non-zero, i warn no.
- **Problema diagnosticato** — un'anomalia rilevata in un'area: causa nominata (es. chiave env mancante,
  indice assente/stantio, provider irraggiungibile, MCP non registrato) + rimedio concreto.
- **Flag di rete (opt-in)** — la manopola che abilita i check che richiedono rete (probe provider,
  eventuale reachability MCP); assente di default → comando offline-safe.
- **Segnali di salute (riusati)** — i dati deterministici letti via vehicle: campi richiesti dal
  validatore di config, presenza/freschezza dal manifest dell'indice, registrazione MCP dalla config
  dell'ospite, probe minimale del provider.

## Success Criteria *(mandatory)*
- **SC-001 (quattro aree in un comando):** `sertor-rag doctor` riporta l'esito delle quattro aree
  (env/provider/indice/MCP) in una singola invocazione, con esito per-area. *(FR-001, US1; CS-1)*
- **SC-002 (azionabilità):** per ogni area non-pass l'output nomina causa e rimedio concreto, verificato
  su almeno un caso per area (chiave mancante, indice assente, provider irraggiungibile, MCP non
  registrato). *(FR-002/003/005/008/009, US1..5; CS-2)*
- **SC-003 (machine-readable):** `doctor --json` produce un documento a schema stabile consumabile da una
  skill/script; lo schema non cambia tra invocazioni equivalenti. *(FR-010, US6; CS-3)*
- **SC-004 (exit code gate):** con un check critico fallito l'exit status è non-zero; con tutti i check
  critici verdi è zero. *(FR-011, US6; CS-4)*
- **SC-005 (offline-safe):** senza flag di rete e in ambiente offline, `doctor` completa i check statici
  con zero traffico di rete (monitor a zero); col flag di rete offline i check di rete sono
  skipped/unknown, mai crash. *(FR-007/008/012, US7; CS-5)*
- **SC-006 (zero segreti):** nessun segreto compare nell'output umano o JSON (la redazione esistente si
  applica). *(FR-013, US6; CS-6)*
- **SC-007 (freschezza senza falsi positivi):** un indice presente e allineato → pass; con sorgenti
  modificate dopo l'ultima indicizzazione → warn (stantio); la valutazione usa il manifest, senza
  riscansione, senza falso positivo su `sources` larghi. *(FR-006, US3; R-1)*
- **SC-008 (no indicizzazione di prova):** il probe provider non indicizza mai per verificare la
  raggiungibilità. *(FR-008, US4; R-2)*
- **SC-009 (sola lettura):** in nessuno scenario `doctor` altera config o indice. *(FR-014, US7)*
- **SC-010 (nessun LLM):** `doctor` non effettua alcuna chiamata a un LLM (verificabile). *(FR-015; CS-6
  d'epica)*
- **SC-011 (`configure --check` reso vivo):** `sertor configure --check` esegue la verifica config
  tramite `doctor` (non più «probe live non disponibile») e rimanda a `doctor` per il quadro completo;
  `configure` senza `--check` resta invariato. *(FR-016/017, US8; DA-D3)*
- **SC-012 (additività):** a comando non invocato il comportamento è identico a oggi; nessun percorso
  esistente del core è alterato; suite verde, lint pulito; nessuna nuova dipendenza richiesta dai check
  statici. *(RNF-5)*

## Assumptions
- **A-001 — Fonte dei campi env:** `Settings.validate_backend()` è la fonte unica dei campi richiesti per
  il provider/store selezionato (E2/`sertor-cli`); `doctor` la consuma, non la duplica.
- **A-002 — Manifest del refresh incrementale (FEAT-009) disponibile:** il manifest
  `<index_dir>/index_manifest.sqlite` (namespaced per `(corpus,provider)`) persiste per file
  `mtime + content_hash + logic_version` e i metadati di collezione, sufficiente a determinare presenza e
  freschezza senza riscansione. Il drift "vero" (segnale storicizzato) resta a osservabilità (FEAT-012).
- **A-003 — Registrazione MCP leggibile staticamente:** lo stato di registrazione del server `sertor-rag`
  è determinabile dalla config dell'ospite (`.mcp.json` in project scope, o registro del client in local
  scope) senza avviare il server.
- **A-004 — Probe provider minimale possibile:** esiste un modo minimale e non-indicizzante per verificare
  la raggiungibilità del provider selezionato (il *come* esatto = design); di default non viene eseguito.
- **A-005 — Redazione segreti esistente:** la funzione di scrub/redact del core
  (`observability/scrub.py`) è applicabile all'output di `doctor` (umano e JSON).
- **A-006 — Punto d'estensione `--check` presente:** `configure._probe_live` invoca già `sertor-rag`
  in subprocess via il vehicle (Principio XI) e degrada onestamente; questa feature fornisce il comando
  che lo rende operativo, senza riscrivere il wizard.
- **A-007 — Criticità degli esiti:** quali check sono "critici" (gate dell'exit code) vs "warn"
  (informativi) è una scelta deterministica documentabile; default ragionevole: env mancante e indice
  assente sono critici, indice stantio e MCP non registrato sono warn (il design può raffinarlo).

### Fuori ambito (dichiarato)
- **Auto-fix / riparazione:** `doctor` diagnostica, non ripara; la riparazione guidata è **FEAT-002
  guided-setup** (epica E12) — cross-ref.
- **Spiegazione conversazionale dell'esito:** è la skill (l'agente dell'ospite), non il comando
  deterministico (FEAT-002/FEAT-007/FEAT-009 dell'epica E12).
- **Qualsiasi chiamata a un LLM dal core** (confine D↔N, Principio): ogni intelligenza vive nelle skill.
- **Probe pesanti/onerosi** (indicizzazione di prova, scansione completa del repo per la freschezza): il
  probe provider resta minimale, la freschezza si basa sul manifest.
- **Storicizzazione del drift / store eventi**: resta a osservabilità (E3/FEAT-012); `doctor` è uno
  snapshot puntuale.
- **Distribuzione su ospiti del comando/asset via `sertor install`**: `sertor-rag doctor` è una capacità
  di sola CLI/libreria → **installabile per costruzione** (viaggia col pacchetto `sertor-core`); va
  comunque **verificato** che eventuali manopole nuove (es. il flag/knob del probe di rete, se introdotto
  come env) compaiano nel template `.env` dell'installer — **debito di completamento** da chiudere in
  plan/tasks, ancorato all'owner di `sertor install` (E2), non un rinvio appeso solo in `specs/`.
- **Il *come* di dettaglio** (schema esatto del JSON, forma del probe provider, criteri precisi
  critico/warn per area, nome esatto del flag di rete, rilevazione esatta dello stantio-dopo-reindex MCP):
  fase di **design/plan**.

> **Tracciamento dello scope.** Lo scope esteso a `sertor` (`configure --check`) chiude il debito
> *deferred* E2/FEAT-003 US5, già tracciato nell'epica `sertor-cli`; nessun rinvio reale vive solo dentro
> `specs/`. L'eventuale knob env del probe di rete, se introdotto, va promosso al template `.env`
> dell'installer (owner E2) come debito di completamento, non sepolto qui.

### Forche di design (per `/speckit-plan`)
- **DA-D1 — Forma dei check di rete: RISOLTA.** Comando unico con esito per-area; un **flag opt-in
  dedicato** (es. `--online`/`--probe`) include i check di rete; **offline-safe by default** (solo
  statici). Il nome esatto del flag e l'eventuale granularità per-check = design (FR-008). *(decisione
  utente; DA-D1 dei requisiti chiusa.)*
- **DA-D2 — Definizione di "indice stantio": RISOLTA.** Check **leggero sul manifest** del refresh
  incrementale (FEAT-009): freschezza da last-index time + mtime/hash dei file registrati, **senza
  riscansione** e **senza euristica nuova**; il drift "vero" resta a osservabilità (FEAT-012). Il
  dettaglio esatto del confronto = design (FR-006). *(decisione utente; DA-D2 chiusa.)*
- **DA-D3 — Relazione con `configure --check`: RISOLTA.** `--check` è un **sottoinsieme config** che
  invoca `doctor`, con rimando a `doctor` per il quadro completo (non un alias dell'intero comando).
  Scope esteso al pacchetto `sertor` (owner E2). Il dettaglio del wiring = design (FR-016). *(decisione
  utente; DA-D3 chiusa.)*
- **DA-D4 (residuo, design) — Criteri critico/warn per area:** quali esiti sono gate dell'exit code vs
  informativi (vedi A-007); default proposto codificato, raffinabile in plan. *Design.*
- **DA-D5 (residuo, design) — Forma del probe provider minimale e rilevazione dello stantio-dopo-reindex
  MCP:** il *come* esatto via vehicle (senza indicizzare, senza avviare il server inutilmente). *Design.*
