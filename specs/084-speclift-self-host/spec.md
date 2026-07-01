# Feature Specification: Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Feature Branch**: `084-speclift-self-host` · **Created**: 2026-07-01 · **Status**: Draft (rigenerata
dopo cambio di decisione: retrieval via **MCP dentro una skill**, non via CLI)

<!-- Deriva da: FEAT-001 (epica speclift) — requirements/speclift/self-host/requirements.md (REVISIONATO)
     Fonti a monte: wiki/sources/input-other-agents/speclift-handoff-sinthari.md (handoff),
     wiki/sources/input-other-agents/speclift-recon.md (ricognizione ancorata a file:riga). -->

**Input**: FEAT-001 dell'epica `speclift`. **SpecLift** (handoff da Sinthari,
`github.com/themetriost/Sinthari` `master @ 5ee6fc1`, PR #5, versione pluggable mergiata con ~122 test
verdi) è una capacità `diff → requisiti EARS ancorati multi-quota`: dato un changeset git genera requisiti su tre
livelli insieme (capacità utente / comportamento / implementazione), ognuno legato a `file:righe` +
simbolo + (se esiste) il test che fallirebbe se il requisito si rompesse, **riverificato sul filesystem**
prima di essere reso (il "moat"). Il meccanismo è un "sandwich deterministico": stadi meccanici a due
marce (`speclift bundle` impacchetta l'evidenza, `speclift assemble` la riverifica e la rende) più
**stadi di giudizio** affidati all'agente chiamante, che orchestra la localizzazione dell'evidenza e
scrive le frasi EARS via la skill `speclift`.

Questa feature è **solo** il primo dei due punti dell'handoff: **rendere SpecLift utilizzabile nel repo
Sertor** (self-hosting/dogfooding) per generare requisiti EARS ancorati dai changeset reali di Sertor,
**senza toccare `sertor_core`** (Principio XI). La distribuzione su ospiti esterni (FEAT-002) è fuori
ambito. Il valore: **Sertor può generare requisiti ancorati e riverificati dai propri changeset**,
alimentando il "lint semantico" del rituale di step con evidenza ancorata invece di un confronto libero.

---

> **Allineamento alla missione (gate Constitution) — dichiarato con onestà.** La stella polare di Sertor
> è dotare l'ospite di auto-conoscenza interrogabile, portabile e senza lock-in, il cui differenziatore è
> la **fusione code+doc resa al retrieval**. SpecLift **non tocca** quel differenziatore diretto: non è un
> motore di retrieval, non modifica `search_combined`/gli engine, non aggiunge una porta al core, non
> migliora hit-rate/MRR/fusion coverage. È **periferico** al differenziatore. Il suo contributo alla
> missione è **indiretto ma reale**: produce un artefatto — requisiti ancorati e riverificabili — che tiene
> i documenti (`requirements/`, wiki, `CLAUDE.md`) **onesti rispetto al codice reale**, prevenendo il drift
> che il punto 3 del rituale di step («lint semantico di allineamento») oggi cerca di correggere a mano.
> Rafforza dunque la **veridicità e freschezza del contesto** che il RAG poi serve — non lo produce, ma lo
> mantiene sano nel tempo. In più, questa versione self-host **consuma il contratto d'integrazione stabile
> che Sertor pubblica per gli agenti — il server MCP** — rispettando il principio per cui i consumatori
> esterni si integrano via MCP, non via CLI.

> **Natura del cambiamento: ADDITIVA / vendoring di un nuovo membro del workspace, ZERO runtime di
> `sertor_core` (Principio XI).** La feature aggiunge il pacchetto `packages/speclift` al workspace `uv` e
> deposita la skill per il dogfood; **non** importa né invoca `sertor_core`, non aggiunge porte/adapter/
> engine/comandi al core, non introduce un LLM interno alla CLI. SpecLift consuma il retrieval di Sertor
> **esclusivamente** tramite il vehicle **MCP** (tool `search_code`), invocato dall'agente orchestratore
> dentro la skill — **mai** tramite la CLI `sertor-rag search` e **mai** importando la libreria. Il
> pacchetto core resta **byte-identico**: zero modifica, zero nuovo import.

> **Cambio di decisione del proprietario (vincolante, sostituisce l'approccio CLI iniziale — non
> riaprire).** L'approccio iniziale metteva in ambito «configurare il vehicle CLI (`sertor-rag search`)
> per la root Sertor». È **SUPERATO**. Principio guida: **Sertor pubblica il server MCP proprio perché i
> consumatori esterni NON dipendano dalla CLI** — la CLI `sertor-rag` è un consumatore interno/sottile,
> l'**MCP è il contratto d'integrazione** per gli agenti. Quindi il self-host di SpecLift **non deve
> dipendere dalla CLI**: la localizzazione dell'evidenza avviene tramite il tool MCP `search_code`,
> orchestrato dall'agente dentro la skill; l'adapter CLI vendorato `adapters/rag_sertor.py`
> (`SertorRagLocator`, Adapter A) resta **vendorato ma dormiente** (non usato) — il self-host adotta
> l'Adapter B pluggable (`ProvidedEvidenceLocator`, MCP-via-agente) presente nella stessa copia upstream.

> **Decisioni di scope — FISSATE (ratificate; non riaprire).**
> - **Vendoring:** SpecLift diventa un nuovo membro del workspace `packages/speclift`, self-contained
>   (hatchling, dominio puro ports&adapters, ZERO import `sertor_core` — verificato dal recon), con **nota
>   di provenienza** esplicita (repo/commit/versione).
> - **Retrieval via MCP dentro una skill, NON via CLI:** il self-host **non** dipende dalla CLI
>   `sertor-rag search`; l'adapter `SertorRagLocator`/`rag_sertor.py` (Adapter A) resta **vendorato ma
>   dormiente** (non usato). La localizzazione dell'evidenza (simboli/test) avviene tramite
>   il tool MCP `search_code`, invocato dall'agente orchestratore dentro la skill. La porta
>   `EvidenceLocator` è **alimentata** dall'evidenza già ottenuta dall'agente, attraverso un'interfaccia
>   esplicita e ispezionabile.
> - **Deviazione dichiarata dal «sandwich a un solo stadio intelligente» di Sinthari:** ora l'agente tocca
>   **due stadi** — localizza l'evidenza (via MCP) **E** scrive le frasi EARS — non uno solo. È una
>   deviazione **intenzionale e dichiarata**, non un'estensione silenziosa; il feedback CLI→MCP è **già
>   stato recepito** da Sinthari (commit `5ee6fc1`, Adapter B pluggable) — qui lo si registra come
>   confermato, non come divergenza aperta.
> - **Solo self-host:** la distribuzione su ospiti esterni (installer/packaging) è **FEAT-002**, epica a
>   parte, con casa di distribuzione non ancora decisa — **fuori ambito qui**.
> - **`sertor_core` INVARIATO** (Principio XI): il legame con Sertor è il tool MCP `search_code`, mai un
>   import, mai la CLI.
> - **Onestà sul retrieval (Gruppo H):** il self-host **adotta** l'Adapter B pluggable (`ProvidedEvidenceLocator`,
>   MCP-via-agente) già presente nel codice vendorato/upstream (commit `5ee6fc1`); il feedback CLI→MCP è
>   quindi già recepito, non una divergenza aperta. Resta comunque da dichiarare il gap rispetto alla
>   narrativa upstream (navigazione code-graph `find_symbol`/`who_calls`) — `search_code` è ricerca
>   semantica, non navigazione del code-graph.
> - **IT invariata:** codice/commenti/skill restano in italiano per il self-host; la traduzione IT→EN
>   host-facing è tema trasversale (E12), fuori ambito.
> - **Nessuna automazione:** SpecLift resta uno strumento su richiesta, non un gate automatico né un passo
>   forzato del rituale di step.

> **Ancoraggio all'esistente (dato di partenza verificato dal recon — ancora i requisiti, non prescrive il
> *come*).**
> - Il pacchetto `speclift` è self-contained sotto `src/speclift/`; il grep `import sertor_core` su `src/`
>   dà **zero import** (le uniche occorrenze sono commenti «mai `import sertor_core`» in `config.py:26`,
>   `rag_sertor.py:3`).
> - **Fatto di provenienza (NON usato nel self-host):** l'adapter CLI vendorato consuma il RAG con un solo
>   sottocomando `sertor-rag search <q> --type code --json -k 5` via subprocess (`rag_sertor.py:86`), con
>   vehicle di default hardcodato `("uv","run","--project",".sertor","sertor-rag")` (`config.py:27`, campo
>   `Config.sertor_rag_vehicle`). Questo path — `SertorRagLocator`/`rag_sertor.py` (Adapter A) — resta
>   **vendorato ma dormiente** (non usato) nella copia vendorata (vedi DA-D-3); è riportato qui solo come
>   tracciabilità.
> - **Vehicle del self-host = tool MCP `search_code`** del server `sertor-rag` (le istruzioni del server
>   prescrivono di citare sempre `path#chunk`): ricerca semantica sul codice, **non** navigazione del
>   code-graph (`find_symbol`/`who_calls`).
> - Precedente più vicino a un adapter «alimentato» invece che «attivo»: `FakeLocator` in
>   `tests/unit/test_locate_evidence.py` (implementa `locate_symbols`/`locate_tests` restituendo dati
>   precostituiti) — la classe di produzione del self-host può ricalcarne la forma (stessa interfaccia di
>   porta, dati letti da un artefatto invece che cablati nel test).
> - Fail-loud RAG upstream: indice mancante/irraggiungibile/output non-JSON → `RagUnavailableError` → exit
>   dedicato. SpecLift **consuma** l'indice, non lo costruisce (NFR-4).
> - `requires-python = ">=3.12"` + `target-version = "py312"`; nessuna sintassi 3.12-only trovata nel grep
>   (`StrEnum` è 3.11+) → il pin è **probabilmente riducibile** a `>=3.11`, da confermare con la suite.
> - Unica dipendenza runtime dichiarata: `jsonschema>=4.0`, usata **solo** nei test di contratto.
> - La skill (`skills/speclift/SKILL.md`) è già **host-agnostica** (verificato: nessun path assistente,
>   nessuno slash-command, nessun nome-modello); il self-host la **estende** a orchestrare anche la
>   localizzazione dell'evidenza via MCP (assente nell'upstream, la cui CLI la esegue internamente).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — SpecLift produce evidenza ancorata dai changeset reali di Sertor, end-to-end (P1, Must)
Un contributore di Sertor, con l'indice RAG del repo costruito e fresco, esegue il flusso self-host su un
commit reale: l'agente **localizza l'evidenza** interrogando il tool MCP `search_code` (guidato dalla
skill), la passa allo stadio deterministico `speclift bundle` che produce un **fascicolo di evidenza non
vuoto** con àncore su file/simboli Sertor reali. Dopo aver scritto le frasi EARS (uno stadio di giudizio)
e passato il tutto a `speclift assemble`, ottiene un **report canonico** (JSON + Markdown) le cui àncore
sono **riverificate** sul filesystem di Sertor — nessuna àncora non verificata accettata in silenzio
(finisce sotto `excluded`).

**Independent Test**: eseguire il ciclo `localizza-evidenza (agente + MCP search_code) → bundle → autoring
→ assemble` su un commit dogfood scelto con l'indice fresco; il bundle referenzia path Sertor reali, il
report finale riverifica ogni àncora sul filesystem e segnala esplicitamente le escluse.

**Acceptance**:
1. **Given** l'indice RAG di Sertor costruito e fresco, **When** l'agente localizza l'evidenza via
   `search_code` e la passa a `speclift bundle`, **Then** il fascicolo di evidenza è non vuoto e le sue
   voci referenziano path Sertor reali e (dove risolvibili) simboli reali.
2. **Given** un bundle autorato (frasi EARS scritte dall'agente chiamante, ancorate per indice), **When**
   si esegue `speclift assemble`, **Then** viene prodotto un report canonico JSON + Markdown le cui àncore
   sono riverificate sul filesystem di Sertor.
3. **Given** un'àncora che non verifica sul filesystem, **When** il report è reso, **Then** compare sotto
   `excluded` con motivo, mai scartata in silenzio né tenuta come valida.

### User Story 2 — Il retrieval passa dall'MCP dentro una skill, mai dalla CLI (P1, Must)
Il self-host **non** invoca la CLI `sertor-rag`: l'adapter CLI vendorato (`SertorRagLocator`/
`rag_sertor.py`, Adapter A) resta vendorato ma dormiente (non usato). La localizzazione dell'evidenza (simboli e test di
copertura) avviene **esclusivamente** tramite il tool MCP `search_code`, invocato dall'agente
orchestratore dentro la skill; la porta `EvidenceLocator` è **alimentata** dall'evidenza già localizzata
dall'agente, attraverso un'interfaccia **esplicita e ispezionabile** (mai una convenzione implicita), mai
eseguendo query live dalla porta e mai importando `sertor_core`.

**Independent Test**: grep di invocazioni della CLI `sertor-rag`/import di `rag_sertor` sul path di
localizzazione evidenza del self-host → assente; verificare che l'interfaccia con cui l'agente consegna
l'evidenza a SpecLift è documentata/ispezionabile e che il retrieval usa il tool MCP `search_code`.

**Acceptance**:
1. **Given** il self-host, **When** localizza l'evidenza, **Then** lo fa solo tramite il tool MCP
   `search_code` invocato dall'agente nella skill, **non** tramite la CLI `sertor-rag search` (subprocess)
   e **non** con una fase deterministica che interroga il RAG da sé.
2. **Given** l'adapter CLI vendorato `rag_sertor.py` (Adapter A), **When** si ispeziona il pacchetto
   vendorato, **Then** quel path non è usato dal composition root del self-host (resta vendorato ma
   dormiente — DA-D-3).
3. **Given** la porta `EvidenceLocator` del self-host, **When** riceve l'evidenza dall'agente, **Then** la
   riceve attraverso un'interfaccia esplicita e ispezionabile (es. un artefatto documentato), non da una
   query live eseguita dalla porta.

### User Story 3 — `sertor_core` resta invariato e non nasce alcun ciclo di dipendenze (P1, Must)
Un manutentore che aggiunge `packages/speclift` al workspace verifica che il pacchetto core sia
**byte-identico** (zero modifica, zero nuovo import) e che `uv sync --all-packages` risolva senza errori:
il nuovo membro **non** introduce un ciclo tra `sertor-core`, `sertor`, `sertor-install-kit`,
`sertor-flow`, `speclift`.

**Independent Test**: `git diff` limitato al pacchetto core → vuoto; grep di `import sertor_core`/`from
sertor_core` su `packages/speclift` → zero occorrenze (fuori dai commenti che *dichiarano* di non farlo);
`uv sync --all-packages` → risoluzione pulita.

**Acceptance**:
1. **Given** il vendoring completato, **When** si ispeziona `sertor_core`, **Then** risulta invariato
   (zero modifica, zero nuovo import come conseguenza di questa feature).
2. **Given** `packages/speclift` aggiunto, **When** si esegue `uv sync --all-packages`, **Then** la
   risoluzione riesce senza errori e senza ciclo di dipendenze tra i membri del workspace.

### User Story 4 — Fallimento onesto quando l'MCP/indice non è disponibile (P1, Must)
Quando il server MCP di Sertor o il suo indice RAG non sono disponibili/raggiungibili mentre l'agente
tenta di localizzare l'evidenza via `search_code`, la skill **si ferma e lo segnala esplicitamente**,
nominando il componente non disponibile e (quando applicabile) il rimedio (es. ricostruire/aggiornare
l'indice RAG con `sertor-rag index .` dalla root) — mai proseguendo con un insieme di evidenza parziale,
vuoto o **fabbricato** come se il retrieval fosse riuscito.

**Independent Test**: eseguire il flusso con l'MCP/indice non disponibile; la skill si arresta con un
messaggio esplicito che nomina la causa e (idealmente) il comando di rimedio, senza produrre evidenza.

**Acceptance**:
1. **Given** il server MCP o l'indice RAG non disponibile/irraggiungibile, **When** l'agente tenta di
   localizzare l'evidenza via `search_code`, **Then** la skill si ferma e lo segnala esplicitamente,
   nominando il componente non disponibile.
2. **Given** il fallimento, **When** il messaggio è reso, **Then** indica (quando applicabile) il rimedio
   concreto (es. ricostruire/aggiornare l'indice RAG), non un generico «RAG non raggiungibile».
3. **Given** l'MCP/indice assente, **When** il flusso fallisce, **Then** non prosegue con evidenza
   parziale, vuota o fabbricata come se il retrieval fosse riuscito.

### User Story 5 — Fallimento onesto quando l'evidenza fornita dall'agente è malformata (P1, Must)
Quando l'artefatto di evidenza che l'agente consegna a SpecLift (l'interfaccia di US2) è assente,
malformato, o non conforme alla sua interfaccia documentata, lo stadio di SpecLift che consuma l'evidenza
**fallisce fail-loud** con un errore esplicito e azionabile che identifica il problema — mai ripiegando in
silenzio su evidenza vuota/di default né fabbricando un'àncora.

**Independent Test**: fornire a SpecLift un file di evidenza assente o malformato; lo stadio di consumo
fallisce con un errore esplicito che identifica il problema, senza degradare in silenzio.

**Acceptance**:
1. **Given** l'artefatto di evidenza assente/malformato/non conforme, **When** lo stadio di consumo di
   SpecLift lo elabora, **Then** fallisce con un errore esplicito e azionabile che identifica il problema.
2. **Given** un'evidenza non valida, **When** SpecLift fallisce, **Then** non ripiega in silenzio su
   evidenza vuota/di default né fabbrica un'àncora.

### User Story 6 — La suite di test vendorata è verde nel workspace Sertor (P1, Must)
Un manutentore esegue `uv run pytest` nel workspace Sertor e la suite di test vendorata di SpecLift (~122
test nella versione pluggable) **gira ed è verde** accanto alle suite degli altri membri del workspace — non
solo isolatamente nel repo Sinthari originale.

**Independent Test**: `uv run pytest` nel workspace include ed esegue la suite di SpecLift; tutti i test
passano; nessuna regressione nelle suite degli altri membri.

**Acceptance**:
1. **Given** `packages/speclift` integrato, **When** si esegue `uv run pytest`, **Then** la suite di
   SpecLift gira e passa nell'infrastruttura di test del workspace.
2. **Given** l'aggiunta del membro `speclift`, **When** si eseguono le suite esistenti, **Then** il
   comportamento e le dipendenze risolte degli altri membri (`sertor`, `sertor-install-kit`,
   `sertor-flow`) restano invariati.
3. **Given** un conflitto di configurazione pytest/lint tra convenzioni Sinthari e Sertor, **When** i test
   sono integrati, **Then** l'esito richiesto è comunque una suite verde (il meccanismo di
   riconciliazione è materia di plan, non un requisito qui).

### User Story 7 — Provenienza del vendoring tracciata e mantenuta (P1, Must)
Un contributore che ispeziona `packages/speclift` trova una **nota di provenienza esplicita** (URL del
repository upstream, commit hash, versione al momento del vendoring), leggibile senza consultazioni
esterne, che documenta da quale stato upstream la copia è derivata. Se in futuro la copia è aggiornata da
uno stato upstream più recente, la nota è aggiornata di conseguenza — mai lasciata silenziosamente stantia.

**Independent Test**: leggere la nota di provenienza in `packages/speclift`: contiene repo, commit,
versione; corrisponde allo stato vendorato.

**Acceptance**:
1. **Given** `packages/speclift` vendorato, **When** lo si ispeziona, **Then** porta una nota di
   provenienza esplicita (repo URL + commit hash + versione), leggibile senza lookup esterno.
2. **Given** un aggiornamento della copia da uno stato upstream più recente, **When** avviene, **Then** la
   nota di provenienza è aggiornata di conseguenza, senza diventare silenziosamente stantia.

### User Story 8 — La skill del dogfood è depositata, host-agnostica e orchestra il retrieval (P1, Must)
Un agente frontier del dogfood Sertor (Claude Code oggi) trova la skill `speclift` depositata in
`.claude/skills/speclift/SKILL.md` e può scoprirla e invocarla. Per il self-host la skill **istruisce
anche** l'agente a orchestrare la localizzazione dell'evidenza — interrogare il tool MCP `search_code` per
ogni hunk cambiato e consegnare l'evidenza allo stadio deterministico `bundle` (tramite l'interfaccia di
US2) — **prima** di scrivere le frasi EARS. Il corpo della skill resta **host-agnostico**: nessun path
specifico d'assistente, nessuna sintassi slash-command, nessun nome di modello.

**Independent Test**: verificare la presenza di `.claude/skills/speclift/SKILL.md`; il corpo istruisce
l'orchestrazione del retrieval via `search_code` e non contiene path assistente hardcoded, slash-command,
né nomi-modello.

**Acceptance**:
1. **Given** il repo Sertor, **When** la feature è completa, **Then** esiste `.claude/skills/speclift/
   SKILL.md`, scopribile e invocabile dall'agente ospite, che istruisce anche a orchestrare la
   localizzazione dell'evidenza via MCP `search_code` prima dell'autoring EARS.
2. **Given** il corpo della skill depositata, **When** lo si ispeziona, **Then** resta host-agnostico (no
   path assistente, no slash-command, no nomi-modello), coerente con l'upstream.

### User Story 9 — Il retrieval MCP e il gap residuo sono dichiarati; il feedback CLI→MCP è recepito da Sinthari (P1, Must)
Chi legge la documentazione di questa feature (questo artefatto e ogni pagina wiki distillata da esso)
apprende **esplicitamente** che il meccanismo di localizzazione dell'evidenza del self-host usa il tool
MCP `search_code` orchestrato dall'agente nella skill, adottando l'**Adapter B pluggable**
(`ProvidedEvidenceLocator`) che il codice vendorato/upstream Sinthari **contiene già** (commit `5ee6fc1`):
il feedback CLI→MCP è quindi **già stato recepito e mergiato a monte**, non una divergenza aperta.
Apprende inoltre che questa adozione **non colma** del tutto la narrativa upstream di navigazione del
code-graph (`find_symbol`/`who_calls`): `search_code` è ricerca semantica, non navigazione del grafo,
quindi resta un gap doc↔meccanismo più piccolo e spostato. L'avvenuto recepimento del feedback è
**registrato** sul canale `input-other-agents`.

**Independent Test**: la documentazione derivata contiene la dichiarazione esplicita dell'adozione
dell'Adapter B MCP (`search_code`) + del gap residuo (non è navigazione code-graph); esiste una voce che
registra a `wiki/sources/input-other-agents/` l'avvenuto recepimento del feedback CLI→MCP.

**Acceptance**:
1. **Given** questo artefatto e ogni pagina wiki derivata, **When** descrivono il meccanismo di
   localizzazione dell'evidenza, **Then** dichiarano esplicitamente che usa l'MCP `search_code` (Adapter B
   pluggable già presente upstream), e che resta un gap rispetto alla narrativa di navigazione del
   code-graph.
2. **Given** l'adozione dell'Adapter B per il self-host, **When** avviene, **Then** è registrato sul canale
   `input-other-agents` che il feedback CLI→MCP è stato recepito e mergiato da Sinthari (commit `5ee6fc1`).

### User Story 10 — Riconciliazione della versione Python con verifica empirica (P2, Should)
Un manutentore riconcilia il `requires-python` di SpecLift (`>=3.12`) verso il pavimento del workspace
Sertor (`>=3.11`), **solo dopo** aver verificato empiricamente che la suite gira ed è verde su un
interprete Python 3.11. Se invece un costrutto genuinamente 3.12-only risultasse richiesto, il pin **non**
viene abbassato in silenzio: la discrepanza è documentata esplicitamente insieme al suo impatto sul
pavimento effettivo del workspace.

**Independent Test**: se il pin è abbassato a `>=3.11`, la suite è stata eseguita su Python 3.11 e passa;
se resta a `>=3.12`, esiste una dichiarazione esplicita del costrutto 3.12-only e del suo impatto.

**Acceptance**:
1. **Given** l'intento di abbassare `requires-python` a `>=3.11`, **When** lo si fa, **Then** la suite
   vendorata è stata eseguita su un interprete Python 3.11 e passa (condizione di accettazione del pin
   abbassato).
2. **Given** un costrutto genuinamente 3.12-only richiesto dal codice, **When** lo si scopre, **Then** il
   pin NON è abbassato in silenzio e la discrepanza è documentata con l'impatto sul pavimento effettivo del
   workspace.

## Edge Cases
- **Path CLI tentato per errore** — se il path di localizzazione evidenza tentasse di invocare la CLI
  `sertor-rag` (o l'adapter `rag_sertor.py`), è **scorretto per il self-host**: il vehicle è il tool MCP
  `search_code`, non la CLI (US2, R-2). L'adapter CLI (Adapter A) resta vendorato ma dormiente (DA-D-3).
- **MCP/indice RAG stantio/assente** — SpecLift **consuma** l'indice, non lo costruisce: MCP non
  raggiungibile o indice assente durante la localizzazione = fail-loud esplicito con rimedio (US4). Gli
  stadi che non toccano il RAG (`ingest`, `parse_diff`, `filter_sources`) continuano a funzionare senza
  indice (NFR-4).
- **Evidenza fornita dall'agente malformata** — assente/malformata/non conforme all'interfaccia = fail-loud
  esplicito, mai ripiego silenzioso su evidenza vuota o àncora fabbricata (US5, R-3). È il guasto più
  subdolo del design MCP-skill: non c'è più un unico comando CLI che fallisce in modo osservabile.
- **Costrutto 3.12-only irriducibile** — se la verifica empirica su 3.11 fallisse contro l'evidenza del
  grep, il pin resta a 3.12 e va dichiarato l'impatto sul pavimento del workspace (US10, R-4).
- **Deriva silenziosa del vendoring** — senza nota di provenienza/processo di aggiornamento, la copia può
  divergere dall'upstream Sinthari nel tempo (US7, R-5).
- **Conflitto configurazione pytest/lint** — marker (`contract`/`integration` Sinthari vs `cloud`/
  `integration` Sertor) e stile ruff (`line-length` 110/`py312` vs 100/`py311`) potrebbero richiedere
  riconciliazione perché la suite resti verde (US6, R-6); esito richiesto = verde, meccanismo = plan.
- **Àncora non verificata dal moat** — sempre elencata sotto `excluded` con motivo, mai scartata in
  silenzio (US1) — invariante ereditato dall'handoff, da non alterare. Il moat verifica sul **filesystem**,
  mai via RAG.

## Requirements *(mandatory)*

### Requisiti funzionali

**Gruppo A — Vendoring e provenienza (Must)**
- **FR-001 (nuovo membro del workspace).** Il workspace Sertor include un nuovo pacchetto membro
  `packages/speclift`, contenente il codice sorgente di speclift, risolvibile come parte del workspace
  `uv`. *(REQ-001; CS-3/CS-5)*
- **FR-002 (nota di provenienza).** Il pacchetto vendorato porta una nota di provenienza esplicita (URL
  repository upstream, commit hash, versione al momento del vendoring), ispezionabile senza lookup esterno.
  *(REQ-002; US7)*
- **FR-003 (provenienza mantenuta).** Se la copia vendorata è aggiornata da uno stato upstream più recente,
  la nota di provenienza è aggiornata di conseguenza, senza diventare silenziosamente stantia. *(REQ-003;
  US7)*

**Gruppo B — Retrieval via MCP dentro una skill, non via CLI (Must)**
- **FR-004 (nessuna dipendenza dalla CLI).** Il path di localizzazione dell'evidenza del self-host **non**
  invoca la CLI `sertor-rag` (subprocess) — incluso l'adapter upstream `SertorRagLocator`
  (`rag_sertor.py`): quel path è scorretto per il self-host e non è usato. *(REQ-007; CS-1/CS-3)*
- **FR-005 (evidenza solo via tool MCP `search_code`).** Il self-host localizza l'evidenza (simboli
  candidati e test di copertura) **esclusivamente** tramite il tool MCP `search_code` di Sertor, invocato
  dall'agente orchestratore dentro la skill — mai da una fase deterministica che interroga il RAG da sé, mai
  importando `sertor_core`. *(REQ-008; CS-1)*
- **FR-006 (`EvidenceLocator` alimentato + interfaccia esplicita).** L'implementazione della porta
  `EvidenceLocator` usata dal self-host è **alimentata** dall'evidenza già localizzata dall'agente (via MCP),
  invece di eseguire query di retrieval live; l'interfaccia con cui l'agente consegna l'evidenza a SpecLift è
  **esplicita e ispezionabile** (es. un artefatto documentato prodotto dall'agente), mai una convenzione
  implicita o non documentata. La forma dell'interfaccia è quella dell'Adapter B pluggable upstream
  (`located.json` chiavata `"<file_path>::<query>"`, DA-D-3). *(REQ-009; US2)*

**Gruppo C — Skill depositata per il dogfood (Must)**
- **FR-007 (skill depositata + orchestra il retrieval).** Il repo Sertor include una copia della skill
  speclift in `.claude/skills/speclift/SKILL.md`, scopribile e invocabile dall'agente ospite durante il
  dogfooding. Per il self-host la skill istruisce **anche** l'agente a orchestrare la localizzazione
  dell'evidenza — interrogare il tool MCP `search_code` per ogni hunk cambiato — e a consegnare l'evidenza
  risultante allo stadio deterministico `bundle` (tramite l'interfaccia di FR-006), prima di scrivere le
  frasi EARS. *(REQ-010; US8)*
- **FR-008 (skill host-agnostica).** Il corpo della skill depositata resta host-agnostico (nessun path
  d'assistente hardcoded, nessuna sintassi slash-command, nessun nome-modello), coerente con la proprietà
  host-agnostica già verificata nella skill upstream. *(REQ-011; US8)*

**Gruppo D — Fail-loud sulla localizzazione dell'evidenza (Must)**
- **FR-009 (fail-loud su MCP/indice non disponibile).** Se il server MCP di Sertor o il suo indice RAG è
  non disponibile o irraggiungibile quando l'agente tenta di localizzare l'evidenza via `search_code`, la
  skill si ferma e lo segnala esplicitamente, nominando il componente non disponibile e (quando applicabile)
  il rimedio (es. ricostruire/aggiornare l'indice RAG), invece di proseguire con un insieme di evidenza
  parziale, vuoto o fabbricato come se il retrieval fosse riuscito. *(REQ-012; CS-6)*
- **FR-010 (fail-loud su evidenza malformata).** Se l'artefatto di evidenza che l'agente consegna a
  SpecLift (FR-006) è assente, malformato o non conforme alla sua interfaccia documentata, lo stadio di
  SpecLift che consuma l'evidenza fallisce fail-loud con un errore esplicito e azionabile che identifica il
  problema, invece di ripiegare in silenzio su evidenza vuota/di default o fabbricare un'àncora. *(REQ-013;
  CS-6)*

**Gruppo E — Test integrati e non-regressione (Must)**
- **FR-011 (suite verde nel workspace).** La suite di test vendorata di speclift (~122 test nella versione
  pluggable) gira e passa nell'infrastruttura di test del workspace Sertor (`uv run pytest`), invocata accanto alle
  suite esistenti degli altri membri del workspace. *(REQ-014; CS-4)*
- **FR-012 (`sertor-core` invariato).** Il pacchetto `sertor-core` resta invariato — zero modifica, zero
  nuovo import — come conseguenza diretta del vendoring e del self-hosting di speclift (Principio XI).
  *(REQ-015; CS-3)*
- **FR-013 (nessun ciclo di dipendenze).** Se l'aggiunta del membro `speclift` introducesse un ciclo di
  dipendenze tra i membri del workspace (`sertor-core`, `sertor`, `sertor-install-kit`, `sertor-flow`,
  `speclift`), l'approccio di vendoring va rivisto prima che la feature sia considerata completa. *(REQ-016;
  CS-5)*

**Gruppo F — Verifica di dogfooding end-to-end (Must)**
- **FR-014 (bundle su commit reale).** Quando il flusso self-host — evidenza localizzata dall'agente via il
  tool MCP `search_code`, poi impacchettata dallo stadio deterministico `bundle` — è eseguito su un commit
  reale di Sertor con l'indice RAG costruito e fresco, produce un fascicolo di evidenza non vuoto le cui
  voci referenziano path Sertor reali e (dove risolvibili) simboli reali. *(REQ-017; CS-1)*
- **FR-015 (report verificato dal moat).** Quando il bundle risultante è autorato (frasi EARS scritte
  dall'agente chiamante, ancorate per indice) e passato a `speclift assemble`, il comando produce un report
  canonico (JSON + Markdown) le cui àncore sono riverificate contro il **filesystem** reale di Sertor (mai
  via RAG), con ogni àncora non verificata elencata sotto `excluded` invece che scartata in silenzio.
  *(REQ-018; CS-2)*

**Gruppo G — Onestà sul retrieval MCP e sul gap residuo (Must)**
- **FR-016 (retrieval MCP dichiarato + gap residuo).** La documentazione di questa feature (questo artefatto e
  ogni pagina wiki entità distillata da esso) dichiara esplicitamente che il meccanismo di localizzazione
  dell'evidenza del self-host usa il tool MCP `search_code` orchestrato dall'agente nella skill, adottando
  l'**Adapter B pluggable** (`ProvidedEvidenceLocator`) che il codice vendorato/upstream Sinthari **contiene
  già** (commit `5ee6fc1`); e che questa adozione **non realizza del tutto** la narrativa upstream di
  navigazione del code-graph (`find_symbol`/`who_calls`), perché `search_code` è ricerca semantica, non
  navigazione del grafo — resta quindi un gap doc↔meccanismo più piccolo e spostato. *(REQ-019; US9)*
- **FR-017 (recepimento del feedback registrato).** Il feedback CLI→MCP è **già stato recepito e mergiato**
  da Sinthari (Adapter B pluggable, commit `5ee6fc1`); questo avvenuto recepimento è **registrato/confermato**
  sul canale di intake esistente `input-other-agents` (`wiki/sources/input-other-agents/`), a chiusura del
  ciclo di feedback verso l'upstream `speclift`. *(REQ-020; US9)*

**Gruppo H — Riconciliazione versione Python (Should / condizionale)**
- **FR-018 (riconciliazione con floor del workspace).** Il `requires-python` del pacchetto speclift
  vendorato è riconciliato con il pavimento del workspace Sertor (`>=3.11`), a meno che una feature di
  linguaggio genuinamente Python-3.12-only sia verificata come richiesta dal codice. *(REQ-004; US10)*
- **FR-019 (verifica empirica su 3.11).** Quando il vincolo `requires-python` di speclift è abbassato a
  `>=3.11`, la suite di test vendorata è eseguita su un interprete Python 3.11 e passa, come condizione di
  accettazione del vincolo abbassato. *(REQ-005; US10)*
- **FR-020 (pin 3.12 irriducibile dichiarato).** Se un costrutto genuinamente Python-3.12-only risultasse
  richiesto dal codice di speclift, il vincolo NON è abbassato in silenzio: la discrepanza è documentata
  esplicitamente insieme al suo impatto sul pavimento effettivo del workspace Sertor. *(REQ-006 — Could,
  condizionale; US10)*

### Requisiti non funzionali
- **RNF-1 (Principio XI — vehicle-only, MCP):** SpecLift consuma il retrieval di Sertor esclusivamente
  tramite il vehicle **MCP** (tool `search_code`), mai tramite CLI subprocess e mai importando
  `sertor_core`; questa feature non introduce alcuna nuova via di accesso diretto alla libreria. Sertor
  pubblica sia CLI sia MCP come vehicle legittimi, ma il self-host sceglie l'MCP come **unico** vehicle del
  proprio path di localizzazione evidenza, disattivando l'adapter CLI vendorato. *(NFR-1)*
- **RNF-2 (isolamento dipendenze runtime):** la dipendenza runtime dichiarata da Sinthari (`jsonschema`,
  usata solo dai test di contratto per quanto verificato) dovrebbe restare/diventare una dipendenza di
  solo-test/dev quando possibile, per non gonfiare l'installazione runtime — Should (vedi DA-D-2). *(NFR-2)*
- **RNF-3 (additività del workspace):** l'aggiunta di `packages/speclift` non altera comportamento o
  dipendenze risolte degli altri membri; `uv sync --all-packages` continua a risolvere per tutti. *(NFR-3)*
- **RNF-4 (non-fatale sugli stadi che non toccano il RAG):** le fasi che non interrogano il RAG (`ingest`,
  `parse_diff`, `filter_sources`) continuano a funzionare senza indice costruito; solo la localizzazione
  dell'evidenza (`locate_evidence` / marcia `bundle`) richiede il prerequisito MCP/RAG — comportamento
  upstream **non alterato**. *(NFR-4)*
- **RNF-5 (lingua):** codice, commenti e skill di SpecLift restano in italiano per il self-host; la
  traduzione host-facing è fuori ambito. *(NFR-5)*
- **RNF-6 (determinismo del sandwich — flusso Adapter B):** con l'Adapter B pluggable (upstream,
  MCP-via-agente) la localizzazione dell'evidenza passa dall'agente (che la ottiene coi tool MCP, guidato
  dalla skill), così l'agente tocca **due stadi** del sandwich — localizzazione **E** stesura EARS — anziché
  il solo stadio di stesura dell'MVP CLI originario. È il flusso **già supportato a monte** dall'Adapter B
  (feedback CLI→MCP recepito, FR-017), dichiarato esplicitamente. Le fasi di impacchettamento (bundle), verifica delle àncore
  (**il moat**, sul filesystem) e resa (render) **restano** deterministiche e NON toccano il RAG — è lì che
  il moat preserva la garanzia forte (nessuna àncora accettata senza riverifica sul filesystem). *(NFR-6)*
- **RNF-7 (`sertor-core` invariato):** nessuna modifica a porte/adapter/composition/engine/comandi del core
  come conseguenza di questa feature.

### Key Entities
- **`packages/speclift` (nuovo membro del workspace)** — copia vendorata self-contained del pacchetto
  speclift (hatchling, dominio puro ports&adapters, zero import `sertor_core`), risolvibile nel workspace
  `uv`, con nota di provenienza (repo/commit/versione); include l'adapter CLI `rag_sertor.py` (Adapter A)
  **vendorato ma dormiente** e l'Adapter B pluggable (`ProvidedEvidenceLocator`) che il self-host usa.
- **Nota di provenienza** — artefatto ispezionabile che documenta lo stato upstream da cui la copia è
  derivata; mantenuto aggiornato a ogni re-vendoring.
- **Adapter B pluggable `ProvidedEvidenceLocator`** — l'implementazione di porta upstream (commit `5ee6fc1`)
  che riceve l'evidenza già localizzata dall'agente (via MCP `search_code`) attraverso un'interfaccia
  esplicita e ispezionabile (`located.json`), invece di eseguire query live; è l'adapter che il self-host
  adotta verbatim, accanto all'Adapter A CLI (`SertorRagLocator`) che resta dormiente.
- **Interfaccia evidenza agente→SpecLift** — il canale esplicito e documentato con cui l'agente consegna
  l'evidenza a SpecLift: la `located.json` dell'Adapter B pluggable upstream, chiavata `"<file_path>::<query>"`
  (DA-D-3).
- **Skill del dogfood (`.claude/skills/speclift/SKILL.md`)** — la skill host-agnostica depositata; per il
  self-host orchestra **due stadi** di giudizio: la localizzazione dell'evidenza via MCP `search_code` e la
  stesura delle frasi EARS leggendo il bundle (per indice).
- **Fail-loud MCP/indice non disponibile** — l'arresto esplicito e azionabile quando il server MCP o
  l'indice RAG non è disponibile durante la localizzazione.
- **Fail-loud evidenza malformata** — l'errore esplicito quando l'artefatto di evidenza dell'agente è
  assente/malformato/non conforme.
- **Suite di test vendorata (~122 test, versione pluggable)** — integrata e verde in `uv run pytest` del workspace.
- **Legame RAG reale = tool MCP `search_code` (Adapter B pluggable adottato verbatim)** — entità
  di *onestà documentale*: il self-host usa l'Adapter B MCP che l'upstream contiene già (commit `5ee6fc1`);
  resta un gap rispetto alla navigazione del code-graph descritta dalla narrativa upstream.

## Success Criteria *(mandatory)*
- **CS-1 (gira nel repo Sertor):** il flusso self-host — evidenza localizzata dall'agente via il tool MCP
  `search_code`, poi impacchettata da `speclift bundle` — eseguito su un commit reale di Sertor con indice
  fresco, produce un fascicolo di evidenza non vuoto con àncore su file/simboli Sertor reali — verificabile
  eseguendo il flusso su un commit dogfood. *(FR-004/005/006/014, US1/US2)*
- **CS-2 (report verificato prodotto):** il fascicolo, autorato e passato a `speclift assemble`, produce un
  report canonico (JSON + Markdown) le cui àncore risultano riverificate sul filesystem di Sertor; nessuna
  àncora non verificata accettata in silenzio. *(FR-015, US1)*
- **CS-3 (`sertor_core` invariato):** zero modifica e zero nuovo import di `sertor_core` come conseguenza
  della feature — verificabile con `git diff` sul core e grep di `import sertor_core` su `packages/speclift`
  (atteso: zero fuori dai commenti dichiarativi). *(FR-012, US3)*
- **CS-4 (test integrati verdi):** la suite vendorata gira ed è verde in `uv run pytest` nel workspace
  Sertor, non solo isolatamente nel repo Sinthari. *(FR-011, US6)*
- **CS-5 (nessun ciclo di dipendenze):** `uv sync --all-packages` risolve senza errori con il nuovo membro
  `packages/speclift`. *(FR-001/013, US3)*
- **CS-6 (fail-loud azionabile):** con l'MCP/indice RAG non disponibile durante la localizzazione, **o** con
  un artefatto di evidenza malformato, il flusso fallisce esplicitamente — mai evidenza vuota o fabbricata —
  con un messaggio che identifica la causa e (quando applicabile) il rimedio — verificabile eseguendo il
  flusso in quelle condizioni. *(FR-009/010, US4/US5)*
- **CS-7 (provenienza + onestà sul retrieval):** `packages/speclift` porta una nota di provenienza
  ispezionabile e la documentazione dichiara esplicitamente l'adozione dell'Adapter B MCP (`search_code`,
  già presente upstream al commit `5ee6fc1`) più il gap residuo sulla navigazione del code-graph, con
  l'avvenuto recepimento del feedback CLI→MCP registrato a Sinthari. *(FR-002/003/016/017, US7/US9)*

## Assumptions
- **A-001 — Vendoring one-shot come direzione (DA in plan):** la modalità di vendoring (copia versionata
  pinnata al commit `5ee6fc1` vs meccanismo di sync) è una forca di *come* rinviata a plan (DA-D-1); il
  requisito qui è solo che la copia sia un membro del workspace con provenienza tracciata (FR-001/002).
- **A-002 — `git` già prerequisito:** SpecLift invoca `git` via subprocess (`git show`/`git diff`); il repo
  Sertor lo soddisfa per definizione — nessun requisito aggiuntivo.
- **A-003 — MCP/indice RAG mantenuto dai meccanismi esistenti:** l'indice resta fresco tramite
  `sertor-rag index .` + hook `rag-freshness` (E10-FEAT-011/016), e il server MCP `sertor-rag` è quello
  registrato nel repo; questa feature **non** introduce un refresh/registrazione propri — SpecLift consuma
  l'indice via il tool MCP.
- **A-004 — Tool MCP `search_code` disponibile e adeguato:** il server `sertor-rag` espone `search_code`
  (ricerca semantica sul codice, cita `path#chunk`); è sufficiente a localizzare simboli candidati e (dove
  presenti) test di copertura per alimentare il bundle. Non fornisce navigazione del code-graph
  (`find_symbol`/`who_calls`) — gap dichiarato (FR-016).
- **A-005 — Versione upstream stabile:** la versione pluggable Sinthari è mergiata e verde (~122 test,
  commit `5ee6fc1`) e non subirà modifiche upstream imminenti che invaliderebbero il vendoring nel breve periodo.
- **A-006 — Pin 3.12 probabilmente riducibile:** nessuna sintassi 3.12-only rilevata nel grep del recon
  (`StrEnum` è 3.11+); la verifica empirica su 3.11 (FR-019) è la condizione di accettazione — resta il
  ramo FR-020 se il grep si rivelasse incompleto.

### Fuori ambito (dichiarato)
- **Distribuzione su ospiti esterni** (installer/packaging per chi installa Sertor da zero): **FEAT-002**,
  epica separata — casa di distribuzione non ancora decisa.
- **Traduzione IT→EN** degli asset SpecLift: tema linguistico trasversale (E12), tracciato altrove.
- **Implementazione della famiglia futura** (SpecAudit, Debrief, Guida al test): capacità distinte e future
  (backlog epica `speclift` FEAT-003/004/005), non in ambito qui.
- **Contribuire a monte a Sinthari** (nessuna PR verso `github.com/themetriost/Sinthari`): il recepimento
  del feedback CLI→MCP si registra (FR-017), non come contributo di codice a monte.
- **Qualunque modifica a `sertor_core`**: la libreria resta byte-identica (Principio XI).
- **Automatizzare l'invocazione di SpecLift nel rituale di step** (gate automatico o innesco a ogni commit):
  resta uno strumento su richiesta.
- **Colmare il gap sulla navigazione del code-graph**: il self-host adotta la ricerca semantica
  (`search_code`), non `find_symbol`/`who_calls`; il gap residuo si **dichiara**, non si chiude qui.
- **Il *come* di dettaglio** (modalità di vendoring, collocazione di `jsonschema`, forma esatta
  dell'interfaccia evidenza agente→SpecLift dell'Adapter B): fase di **design/plan**.

> **Tracciamento dello scope.** I rinvii reali di questa feature sono già promossi a case durevoli: la
> distribuzione su ospiti è **FEAT-002** (backlog epica `speclift`); la famiglia SpecAudit/Debrief/Guida al
> test è **FEAT-003/004/005** (stesso backlog); la traduzione IT→EN è tema **E12**; il recepimento del
> feedback CLI→MCP è **registrato a Sinthari** (`input-other-agents`, commit `5ee6fc1`), non un debito interno. Nessun rinvio reale
> resta sepolto in `specs/`. La feature è *done* quando: SpecLift gira nel repo Sertor producendo evidenza
> ancorata via MCP e un report riverificato (US1); il retrieval passa dall'MCP dentro la skill, mai dalla
> CLI, con interfaccia evidenza esplicita (US2); `sertor_core` è invariato e il workspace risolve senza
> cicli (US3); il fail-loud è azionabile sia su MCP/indice assente sia su evidenza malformata (US4/US5); la
> suite è verde (US6); la provenienza è tracciata (US7); la skill host-agnostica orchestra il retrieval
> (US8); l'adozione dell'Adapter B MCP è dichiarata e il recepimento del feedback è registrato a Sinthari (US9); la versione Python è
> riconciliata con verifica empirica o l'irriducibilità è dichiarata (US10).

### Forche di design — per `/speckit-plan` (sono *come*, non scope)
- **DA-D-1 — Copia versionata vs sync del vendoring.** (a) copia one-shot pinnata al commit `5ee6fc1`,
  documentata dalla nota di provenienza, con aggiornamenti futuri come azione manuale esplicita; (b)
  meccanismo di sync analogo a `sync.py`/`generate.py` di `sertor-flow`. Nota: il precedente SpecKit ha
  abbandonato il vendoring per un launch-installer, ma SpecLift ha **codice runtime proprio eseguibile** →
  il pattern launch-installer non si applica direttamente. Raccomandazione debole (a); decisione al plan.
  *(FR-001/002/003)*
- **DA-D-2 — `jsonschema` runtime → dev.** Il recon conferma che `jsonschema` è usata **solo** dai test di
  contratto; spostarla in `[dev]` ridurrebbe l'impronta runtime senza perdere copertura, ma è una
  divergenza dal `pyproject.toml` upstream da documentare (FR-002/003) e verificare (nessun import runtime
  nascosto). Raccomandazione debole: spostarla; decisione al plan. *(RNF-2)*
- **DA-D-3 — Adozione dell'Adapter B pluggable upstream.** La forca è **risolta a monte**: il codice
  vendorato (commit `5ee6fc1`) contiene già l'**Adapter B** (`ProvidedEvidenceLocator`, MCP-via-agente)
  accanto all'**Adapter A** CLI (`SertorRagLocator`). Il self-host lo **adotta verbatim**, senza inventare
  un adapter o un errore proprio. L'interfaccia è la loro `located.json`, chiavata `"<file_path>::<query>"`,
  che l'agente popola dopo il retrieval MCP; il flusso è a tre marce: `changeset` → localizza via MCP →
  `bundle --changeset --located` → `assemble`. L'Adapter A CLI resta **vendorato ma dormiente** (non usato),
  non va escluso fisicamente — mantenerlo semplifica un re-vendoring «tutto il tree» (DA-D-1) e riflette la
  natura pluggable dell'upstream. Il requisito comportamentale (FR-004/005/006) è soddisfatto dall'Adapter B.
  *(FR-004/005/006)*
  > **Nota:** la vecchia forca «meccanismo di configurazione del vehicle CLI» (ex DA-D-3 del design CLI) è
  > **SUPERATA**: non esiste più un vehicle CLI da configurare, e l'interfaccia evidenza non è più da
  > inventare — è quella pluggable già fornita dall'upstream.
