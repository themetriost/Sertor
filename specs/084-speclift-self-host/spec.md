# Feature Specification: Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Feature Branch**: `084-speclift-self-host` · **Created**: 2026-07-01 · **Status**: Draft

<!-- Deriva da: FEAT-001 (epica speclift) — requirements/speclift/self-host/requirements.md
     Fonti a monte: wiki/sources/input-other-agents/speclift-handoff-sinthari.md (handoff),
     wiki/sources/input-other-agents/speclift-recon.md (ricognizione ancorata a file:riga). -->

**Input**: FEAT-001 dell'epica `speclift`. **SpecLift** (handoff da Sinthari,
`github.com/themetriost/Sinthari` `master @ be4da28`, PR #5, MVP mergiato con 104 test verdi) è una
capacità `diff → requisiti EARS ancorati multi-quota`: dato un changeset git genera requisiti su tre
livelli insieme (capacità utente / comportamento / implementazione), ognuno legato a `file:righe` +
simbolo + (se esiste) il test che fallirebbe se il requisito si rompesse, **riverificato sul filesystem**
prima di essere reso (il "moat"). Il meccanismo è un "sandwich deterministico": una CLI meccanica a due
marce (`speclift bundle` estrae l'evidenza, `speclift assemble` la riverifica e la rende) più **un solo
stadio di giudizio** — l'agente chiamante che scrive le frasi EARS via la skill `speclift`.

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
> mantiene sano nel tempo.

> **Natura del cambiamento: ADDITIVA / vendoring di un nuovo membro del workspace, ZERO runtime di
> `sertor_core` (Principio XI).** La feature aggiunge il pacchetto `packages/speclift` al workspace `uv` e
> deposita la skill per il dogfood; **non** importa né invoca `sertor_core`, non aggiunge porte/adapter/
> engine/comandi al core, non introduce un LLM interno alla CLI. SpecLift consuma il retrieval di Sertor
> **esclusivamente** tramite il vehicle CLI `sertor-rag search --type code --json` (subprocess). Il
> pacchetto core resta **byte-identico**: zero modifica, zero nuovo import.

> **Decisioni di scope — FISSATE (ratificate; non riaprire).**
> - **Vendoring:** SpecLift diventa un nuovo membro del workspace `packages/speclift`, self-contained
>   (hatchling, dominio puro ports&adapters, ZERO import `sertor_core` — verificato dal recon).
> - **Solo self-host:** la distribuzione su ospiti esterni (installer/packaging) è **FEAT-002**, epica a
>   parte, con casa di distribuzione non ancora decisa — **fuori ambito qui**.
> - **`sertor_core` INVARIATO** (Principio XI): il legame con Sertor è un solo comando CLI, mai un import.
> - **Onestà doc↔codice (non negoziabile):** il legame reale col RAG è **un solo comando**
>   `sertor-rag search --type code --json`, **NON** i tool MCP di navigazione del code-graph
>   (`find_symbol`/`who_calls`) che la narrativa upstream (handoff/wiki Sinthari) descrive. Questa
>   discrepanza va **dichiarata** in questo artefatto e in ogni documento derivato — non propagata.
> - **IT invariata:** codice/commenti/skill restano in italiano per il self-host; la traduzione IT→EN
>   host-facing è tema trasversale (E12), fuori ambito.
> - **Nessuna automazione:** SpecLift resta uno strumento su richiesta, non un gate automatico né un passo
>   forzato del rituale di step.

> **Ancoraggio all'esistente (dato di partenza verificato dal recon — ancora i requisiti, non prescrive il
> *come*).**
> - Il pacchetto `speclift` è self-contained sotto `src/speclift/`; il grep `import sertor_core` su `src/`
>   dà **zero import** (le uniche occorrenze sono commenti «mai `import sertor_core`» in `config.py:26`,
>   `rag_sertor.py:3`).
> - Consumo RAG = un solo sottocomando `sertor-rag search <q> --type code --json -k 5` via subprocess
>   (`rag_sertor.py:86`); l'output atteso è un array JSON piatto con almeno `path` (opzionale `chunk_id`)
>   — **compatibile** con la CLI Sertor odierna (`--type code` non è impattato dal breaking change di
>   `--type both`, feature 070).
> - Fail-loud RAG: indice mancante/irraggiungibile/output non-JSON → `RagUnavailableError` → **exit 3**
>   (`rag_sertor.py:87-99,120-124`). SpecLift **consuma** l'indice, non lo costruisce.
> - Vehicle di default hardcodato `("uv","run","--project",".sertor","sertor-rag")` (`config.py:27`, campo
>   `Config.sertor_rag_vehicle`, letto come costante module-level `DEFAULT_CONFIG` in `cli.py`); **nessun**
>   flag CLI né env var di override esiste oggi. Nel repo Sertor il RAG vive a **root** (`uv run
>   sertor-rag`), non in `.sertor/`.
> - `requires-python = ">=3.12"` + `target-version = "py312"`; nessuna sintassi 3.12-only trovata nel grep
>   (`StrEnum` è 3.11+) → il pin è **probabilmente riducibile** a `>=3.11`, da confermare con la suite.
> - Unica dipendenza runtime dichiarata: `jsonschema>=4.0`, usata **solo** nei test di contratto.
> - La skill (`skills/speclift/SKILL.md`) è già **host-agnostica** (verificato: nessun path assistente,
>   nessuno slash-command, nessun nome-modello).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — SpecLift produce evidenza ancorata dai changeset reali di Sertor (P1, Must)
Un contributore di Sertor, con l'indice RAG del repo costruito e fresco, esegue `speclift bundle <ref>`
su un commit reale di Sertor e ottiene un **fascicolo di evidenza non vuoto** con àncore su file/simboli
Sertor reali. Dopo aver scritto le frasi EARS (lo stadio di giudizio) e passato il tutto a `speclift
assemble`, ottiene un **report canonico** (JSON + Markdown) le cui àncore sono **riverificate** sul
filesystem di Sertor — nessuna àncora non verificata accettata in silenzio (finisce sotto `excluded`).

**Independent Test**: eseguire il ciclo `bundle → autoring → assemble` su un commit dogfood scelto con
l'indice fresco; il bundle referenzia path Sertor reali, il report finale riverifica ogni àncora e
segnala esplicitamente le escluse.

**Acceptance**:
1. **Given** l'indice RAG di Sertor costruito e fresco, **When** si esegue `speclift bundle <ref>` su un
   commit reale, **Then** il fascicolo di evidenza è non vuoto e le sue voci referenziano path Sertor
   reali e (dove risolvibili) simboli reali.
2. **Given** un bundle autorato (frasi EARS scritte dall'agente chiamante, ancorate per indice), **When**
   si esegue `speclift assemble`, **Then** viene prodotto un report canonico JSON + Markdown le cui àncore
   sono riverificate sul filesystem di Sertor.
3. **Given** un'àncora che non verifica sul filesystem, **When** il report è reso, **Then** compare sotto
   `excluded` con motivo, mai scartata in silenzio né tenuta come valida.

### User Story 2 — `sertor_core` resta invariato e non nasce alcun ciclo di dipendenze (P1, Must)
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
3. **Given** SpecLift che localizza evidenza, **When** consuma il retrieval di Sertor, **Then** lo fa
   esclusivamente via il vehicle CLI `sertor-rag search` (subprocess), mai importando la libreria core.

### User Story 3 — Fallimento onesto e azionabile quando l'indice RAG non c'è (P1, Must)
Un utente che esegue SpecLift su un repo/indice non ancora costruito ottiene un **fallimento esplicito**
con l'exit code dedicato (3) e un messaggio che identifica la causa (RAG non raggiungibile) e, idealmente,
indica il comando di rimedio (`sertor-rag index .` dalla root) — mai un degrado silenzioso né risultati
vuoti/fabbricati come se la query fosse riuscita.

**Independent Test**: eseguire SpecLift con l'indice RAG assente; l'esecuzione esce con codice 3 e stampa
su stderr un messaggio che nomina la causa e (idealmente) il comando di rimedio.

**Acceptance**:
1. **Given** l'indice RAG mancante/irraggiungibile, **When** lo stadio di localizzazione dell'evidenza
   gira, **Then** SpecLift esce con exit code 3 e un messaggio esplicito su stderr.
2. **Given** il fallimento RAG-unavailable, **When** il messaggio è reso, **Then** raccomanda il comando
   di rimedio concreto (`sertor-rag index .` dalla root), non un generico «RAG non raggiungibile».
3. **Given** l'assenza di indice, **When** SpecLift fallisce, **Then** non restituisce risultati vuoti o
   fabbricati come se la query fosse riuscita.

### User Story 4 — Il vehicle RAG punta alla root di Sertor, non a `.sertor/` (P1, Must)
Un utente che invoca SpecLift dalla root del repo Sertor raggiunge l'indice RAG **senza passare flag o
variabili d'ambiente ad-hoc ogni volta**: il vehicle è configurato per la root Sertor (equivalente a `uv
run sertor-rag`), non per il default upstream che assume un sotto-progetto `.sertor/`. Il meccanismo di
configurazione è **esplicito e ispezionabile** (documentato nel pacchetto vendorato o nella sua
configurazione), mai una modifica locale non tracciata che diverga silenziosamente dalla nota di
provenienza.

**Independent Test**: invocare SpecLift dalla root Sertor senza flag/env ad-hoc; raggiunge l'indice e
restituisce risultati. Ispezionare come è impostato il vehicle: la configurazione è tracciata, non un
edit locale nascosto.

**Acceptance**:
1. **Given** l'istanza self-hosted, **When** invoca il RAG di Sertor, **Then** usa il vehicle applicabile
   alla root del repo (equivalente a `uv run sertor-rag`), non il default upstream `.sertor/`.
2. **Given** un'invocazione dalla root Sertor, **When** SpecLift interroga il RAG, **Then** raggiunge
   l'indice e ritorna risultati senza richiedere flag/env ad-hoc a ogni chiamata.
3. **Given** il meccanismo di configurazione del vehicle, **When** lo si ispeziona, **Then** è esplicito e
   documentato (non una modifica locale non tracciata che diverga dalla provenienza).

### User Story 5 — La suite di test vendorata è verde nel workspace Sertor (P1, Must)
Un manutentore esegue `uv run pytest` nel workspace Sertor e la suite di test vendorata di SpecLift (104
test all'atto dell'handoff) **gira ed è verde** accanto alle suite degli altri membri del workspace — non
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

### User Story 6 — Provenienza del vendoring tracciata e mantenuta (P1, Must)
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

### User Story 7 — La skill del dogfood è depositata e host-agnostica (P1, Must)
Un agente frontier del dogfood Sertor (Claude Code oggi) trova la skill `speclift` depositata in
`.claude/skills/speclift/SKILL.md` e può scoprirla e invocarla. Il corpo della skill resta
**host-agnostico**: nessun path specifico d'assistente, nessuna sintassi slash-command, nessun nome di
modello — coerente con la proprietà già verificata nell'upstream.

**Independent Test**: verificare la presenza di `.claude/skills/speclift/SKILL.md`; il corpo non contiene
path assistente hardcoded, slash-command, né nomi-modello.

**Acceptance**:
1. **Given** il repo Sertor, **When** la feature è completa, **Then** esiste `.claude/skills/speclift/
   SKILL.md`, scopribile e invocabile dall'agente ospite durante il dogfooding.
2. **Given** il corpo della skill depositata, **When** lo si ispeziona, **Then** resta host-agnostico (no
   path assistente, no slash-command, no nomi-modello), coerente con l'upstream.

### User Story 8 — La discrepanza doc↔codice sul legame RAG è dichiarata, non propagata (P1, Must)
Chi legge la documentazione di questa feature (questo artefatto e ogni pagina wiki distillata da esso)
apprende **esplicitamente** che il legame runtime reale di SpecLift con Sertor è un **singolo comando CLI**
(`sertor-rag search --type code --json`), **non** i tool MCP di navigazione del code-graph
(`find_symbol`/`who_calls`) che l'handoff e la narrativa wiki Sinthari descrivono — così nessun agente del
dogfood si aspetta una navigazione del code-graph che SpecLift non usa.

**Independent Test**: la documentazione derivata contiene la precisazione esplicita «legame reale = un solo
comando `sertor-rag search --type code --json`, non `find_symbol`/`who_calls`».

**Acceptance**:
1. **Given** questo artefatto di specifica e ogni pagina wiki derivata, **When** descrivono il legame di
   SpecLift col RAG di Sertor, **Then** dichiarano esplicitamente che è un solo comando CLI, non i tool MCP
   di code-graph.
2. **Given** la narrativa upstream che cita `find_symbol`/`who_calls`, **When** viene recepita nel dogfood
   Sertor, **Then** la discrepanza è dichiarata lato Sertor, non ripetuta acriticamente (e non si tenta di
   correggerla a monte in Sinthari — fuori ambito).

### User Story 9 — Riconciliazione della versione Python con verifica empirica (P2, Should)
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
- **Vehicle non riconfigurato** — se il vehicle restasse al default upstream (`uv run --project .sertor
  sertor-rag`), SpecLift fallirebbe fail-loud (exit 3) ma la causa reale (vehicle sbagliato, non «RAG giù»)
  non sarebbe ovvia senza un messaggio azionabile → US3/US4 (R-3).
- **Indice RAG stantio/assente** — SpecLift **consuma** l'indice, non lo costruisce: assenza/irraggiungibilità
  = exit 3 azionabile (US3). Gli stadi che non toccano il RAG (`ingest`, `parse_diff`, `filter_sources`)
  continuano a funzionare senza indice (NFR-4).
- **Costrutto 3.12-only irriducibile** — se la verifica empirica su 3.11 fallisse contro l'evidenza del
  grep, il pin resta a 3.12 e va dichiarato l'impatto sul pavimento del workspace (US9, R-2).
- **Deriva silenziosa del vendoring** — senza nota di provenienza/processo di aggiornamento, la copia può
  divergere dall'upstream Sinthari nel tempo (US6, R-4).
- **Conflitto configurazione pytest/lint** — marker (`contract`/`integration` Sinthari vs `cloud`/
  `integration` Sertor) e stile ruff (`line-length` 110/`py312` vs 100/`py311`) potrebbero richiedere
  riconciliazione perché la suite resti verde (US5, R-5); esito richiesto = verde, meccanismo = plan.
- **Àncora non verificata dal moat** — sempre elencata sotto `excluded` con motivo, mai scartata in
  silenzio (US1) — invariante ereditato dall'handoff, da non alterare.

## Requirements *(mandatory)*

### Requisiti funzionali

**Gruppo A — Vendoring e provenienza (Must)**
- **FR-001 (nuovo membro del workspace).** Il workspace Sertor include un nuovo pacchetto membro
  `packages/speclift`, contenente il codice sorgente di speclift, risolvibile come parte del workspace
  `uv`. *(REQ-001; CS-3/CS-5)*
- **FR-002 (nota di provenienza).** Il pacchetto vendorato porta una nota di provenienza esplicita (URL
  repository upstream, commit hash, versione al momento del vendoring), ispezionabile senza lookup esterno.
  *(REQ-002; US6)*
- **FR-003 (provenienza mantenuta).** Se la copia vendorata è aggiornata da uno stato upstream più recente,
  la nota di provenienza è aggiornata di conseguenza, senza diventare silenziosamente stantia. *(REQ-003;
  US6)*

**Gruppo B — Vehicle RAG configurato per Sertor (Must)**
- **FR-004 (vehicle alla root Sertor).** L'istanza self-hosted invoca il RAG di Sertor tramite il vehicle
  applicabile alla root del repository (equivalente a `uv run sertor-rag`), non tramite il default upstream
  che assume un sotto-progetto `.sertor/`. *(REQ-007; CS-1)*
- **FR-005 (meccanismo esplicito e ispezionabile).** Il meccanismo usato per configurare il vehicle RAG del
  self-host è esplicito e ispezionabile (documentato nel pacchetto vendorato o nella sua configurazione),
  mai una modifica locale non tracciata che diverga silenziosamente da ciò che la nota di provenienza
  (FR-002) implica sul sorgente vendorato. *(REQ-008; US4)*
- **FR-006 (raggiungibilità senza flag ad-hoc).** Invocando SpecLift dalla root del repo Sertor, esso
  raggiunge con successo l'indice RAG e ritorna risultati, senza richiedere all'invocante flag o variabili
  d'ambiente ad-hoc e non documentate a ogni chiamata. *(REQ-009; CS-1)*

**Gruppo C — Fail-loud sul prerequisito RAG (Must)**
- **FR-007 (fail-loud con exit dedicato).** Se l'indice RAG di Sertor è mancante, non costruito o
  irraggiungibile quando lo stadio di localizzazione dell'evidenza gira, SpecLift esce con l'exit code
  dedicato non-zero (3) e stampa un messaggio d'errore esplicito su stderr, invece di degradare in silenzio
  o restituire risultati vuoti/fabbricati come se la query fosse riuscita. *(REQ-012; CS-6)*
- **FR-008 (messaggio azionabile).** Dove l'istanza self-hosted solleva l'errore RAG-unavailable, il
  messaggio raccomanda il comando di rimedio concreto (`sertor-rag index .`, dalla root del repo), invece
  di un generico «RAG non raggiungibile» senza prossimo passo. *(REQ-013; CS-6)*

**Gruppo D — Skill depositata per il dogfood (Must)**
- **FR-009 (skill depositata).** Il repo Sertor include una copia della skill speclift in
  `.claude/skills/speclift/SKILL.md`, così che l'agente ospite di Sertor possa scoprire e invocare la
  capacità durante il dogfooding. *(REQ-010; US7)*
- **FR-010 (skill host-agnostica).** Il corpo della skill depositata resta host-agnostico (nessun path
  d'assistente hardcoded, nessuna sintassi slash-command, nessun nome-modello), coerente con la proprietà
  host-agnostica già verificata nella skill upstream. *(REQ-011; US7)*

**Gruppo E — Test integrati e non-regressione (Must)**
- **FR-011 (suite verde nel workspace).** La suite di test vendorata di speclift (104 test all'handoff)
  gira e passa nell'infrastruttura di test del workspace Sertor (`uv run pytest`), invocata accanto alle
  suite esistenti degli altri membri del workspace. *(REQ-014; CS-4)*
- **FR-012 (`sertor-core` invariato).** Il pacchetto `sertor-core` resta invariato — zero modifica, zero
  nuovo import — come conseguenza diretta del vendoring e del self-hosting di speclift (Principio XI).
  *(REQ-015; CS-3)*
- **FR-013 (nessun ciclo di dipendenze).** Se l'aggiunta del membro `speclift` introducesse un ciclo di
  dipendenze tra i membri del workspace (`sertor-core`, `sertor`, `sertor-install-kit`, `sertor-flow`,
  `speclift`), l'approccio di vendoring va rivisto prima che la feature sia considerata completa. *(REQ-016;
  CS-5)*

**Gruppo F — Verifica di dogfooding end-to-end (Must)**
- **FR-014 (bundle su commit reale).** Quando `speclift bundle <ref>` è eseguito su un commit reale di
  Sertor con l'indice RAG costruito e fresco, il comando produce un fascicolo di evidenza non vuoto le cui
  voci referenziano path Sertor reali e (dove risolvibili) simboli reali. *(REQ-017; CS-1)*
- **FR-015 (report verificato dal moat).** Quando il bundle risultante è autorato (frasi EARS scritte
  dall'agente chiamante, ancorate per indice) e passato a `speclift assemble`, il comando produce un report
  canonico (JSON + Markdown) le cui àncore sono riverificate contro il filesystem reale di Sertor, con ogni
  àncora non verificata elencata sotto `excluded` invece che scartata in silenzio. *(REQ-018; CS-2)*

**Gruppo G — Onestà sulla discrepanza doc↔codice (Must)**
- **FR-016 (discrepanza dichiarata).** La documentazione di questa feature (questo artefatto e ogni pagina
  wiki entità distillata da esso) dichiara esplicitamente che il legame runtime reale di speclift con
  Sertor è un singolo comando CLI (`sertor-rag search --type code --json`), non i tool MCP di navigazione
  del code-graph (`find_symbol`/`who_calls`) che l'handoff upstream e la narrativa wiki Sinthari descrivono.
  *(REQ-019; US8)*

**Gruppo H — Riconciliazione versione Python (Should / condizionale)**
- **FR-017 (riconciliazione con floor del workspace).** Il `requires-python` del pacchetto speclift
  vendorato è riconciliato con il pavimento del workspace Sertor (`>=3.11`), a meno che una feature di
  linguaggio genuinamente Python-3.12-only sia verificata come richiesta dal codice. *(REQ-004; US9)*
- **FR-018 (verifica empirica su 3.11).** Quando il vincolo `requires-python` di speclift è abbassato a
  `>=3.11`, la suite di test vendorata è eseguita su un interprete Python 3.11 e passa, come condizione di
  accettazione del vincolo abbassato. *(REQ-005; US9)*
- **FR-019 (pin 3.12 irriducibile dichiarato).** Se un costrutto genuinamente Python-3.12-only risultasse
  richiesto dal codice di speclift, il vincolo NON è abbassato in silenzio: la discrepanza è documentata
  esplicitamente insieme al suo impatto sul pavimento effettivo del workspace Sertor. *(REQ-006 — Could,
  condizionale; US9)*

### Requisiti non funzionali
- **RNF-1 (Principio XI — vehicle-only):** SpecLift consuma il retrieval di Sertor esclusivamente tramite
  il vehicle CLI (subprocess), mai importando `sertor_core`; questa feature non introduce alcuna nuova via
  di accesso diretto alla libreria. *(NFR-1)*
- **RNF-2 (isolamento dipendenze runtime):** la dipendenza runtime dichiarata da Sinthari (`jsonschema`,
  usata solo dai test di contratto per quanto verificato) dovrebbe restare/diventare una dipendenza di
  solo-test/dev quando possibile, per non gonfiare l'installazione runtime — Should (vedi DA-D-2). *(NFR-2)*
- **RNF-3 (additività del workspace):** l'aggiunta di `packages/speclift` non altera comportamento o
  dipendenze risolte degli altri membri; `uv sync --all-packages` continua a risolvere per tutti. *(NFR-3)*
- **RNF-4 (non-fatale sugli stadi che non toccano il RAG):** le fasi che non interrogano il RAG (`ingest`,
  `parse_diff`, `filter_sources`) continuano a funzionare senza indice costruito; solo `locate_evidence`
  (e quindi l'intera marcia `bundle`) richiede il prerequisito RAG — comportamento upstream **non
  alterato**. *(NFR-4)*
- **RNF-5 (lingua):** codice, commenti e skill di SpecLift restano in italiano per il self-host; la
  traduzione host-facing è fuori ambito. *(NFR-5)*
- **RNF-6 (determinismo del sandwich):** nessuna modifica introdotta da questa feature (vendoring,
  riconciliazione versione, vehicle, skill) altera la proprietà «un solo stadio intelligente»: la CLI resta
  deterministica in ingresso e in uscita. *(NFR-6)*
- **RNF-7 (`sertor-core` invariato):** nessuna modifica a porte/adapter/composition/engine/comandi del core
  come conseguenza di questa feature.

### Key Entities
- **`packages/speclift` (nuovo membro del workspace)** — copia vendorata self-contained del pacchetto
  speclift (hatchling, dominio puro ports&adapters, zero import `sertor_core`), risolvibile nel workspace
  `uv`, con nota di provenienza (repo/commit/versione).
- **Nota di provenienza** — artefatto ispezionabile che documenta lo stato upstream da cui la copia è
  derivata; mantenuto aggiornato a ogni re-vendoring.
- **Vehicle RAG configurato per la root Sertor** — la configurazione (esplicita e ispezionabile) che fa sì
  che SpecLift invochi `uv run sertor-rag` alla root del repo invece del default upstream `.sertor/`.
- **Skill del dogfood (`.claude/skills/speclift/SKILL.md`)** — la skill host-agnostica depositata; è il
  «cervello» del sandwich (l'agente chiamante scrive le frasi EARS leggendo il bundle, per indice).
- **Errore RAG-unavailable (exit 3) azionabile** — il fallimento fail-loud sul prerequisito RAG, con
  messaggio che indica il comando di rimedio.
- **Suite di test vendorata (104 test)** — integrata e verde in `uv run pytest` del workspace.
- **Legame RAG reale = un solo comando CLI** — `sertor-rag search --type code --json`, non i tool MCP di
  code-graph: entità di *onestà documentale*, non un componente da costruire.

## Success Criteria *(mandatory)*
- **CS-1 (gira nel repo Sertor):** `speclift bundle <ref>` su un commit reale di Sertor con indice fresco
  produce un fascicolo di evidenza non vuoto con àncore su file/simboli Sertor reali — verificabile
  eseguendo il comando su un commit dogfood. *(FR-004/006/014, US1/US4)*
- **CS-2 (report verificato prodotto):** il fascicolo, autorato e passato a `speclift assemble`, produce un
  report canonico (JSON + Markdown) le cui àncore risultano riverificate sul filesystem di Sertor; nessuna
  àncora non verificata accettata in silenzio. *(FR-015, US1)*
- **CS-3 (`sertor_core` invariato):** zero modifica e zero nuovo import di `sertor_core` come conseguenza
  della feature — verificabile con `git diff` sul core e grep di `import sertor_core` su `packages/speclift`
  (atteso: zero fuori dai commenti dichiarativi). *(FR-012, US2)*
- **CS-4 (test integrati verdi):** la suite vendorata gira ed è verde in `uv run pytest` nel workspace
  Sertor, non solo isolatamente nel repo Sinthari. *(FR-011, US5)*
- **CS-5 (nessun ciclo di dipendenze):** `uv sync --all-packages` risolve senza errori con il nuovo membro
  `packages/speclift`. *(FR-001/013, US2)*
- **CS-6 (fail-loud azionabile):** su un repo senza indice RAG costruito, SpecLift fallisce con l'exit code
  3 e un messaggio che identifica la causa, idealmente indicando `sertor-rag index .` — verificabile
  eseguendo SpecLift su un indice assente. *(FR-007/008, US3)*
- **CS-7 (provenienza + onestà doc):** `packages/speclift` porta una nota di provenienza ispezionabile e la
  documentazione dichiara esplicitamente il legame RAG reale (un solo comando CLI, non i tool MCP di
  code-graph). *(FR-002/003/016, US6/US8)*

## Assumptions
- **A-001 — Vendoring one-shot come direzione (DA in plan):** la modalità di vendoring (copia versionata
  pinnata al commit `be4da28` vs meccanismo di sync) è una forca di *come* rinviata a plan (DA-D-1); il
  requisito qui è solo che la copia sia un membro del workspace con provenienza tracciata (FR-001/002).
- **A-002 — `git` già prerequisito:** SpecLift invoca `git` via subprocess (`git show`/`git diff`); il repo
  Sertor lo soddisfa per definizione — nessun requisito aggiuntivo.
- **A-003 — Indice RAG mantenuto dai meccanismi esistenti:** l'indice resta fresco tramite
  `sertor-rag index .` + hook `rag-freshness` (E10-FEAT-011/016); questa feature **non** introduce un
  refresh proprio — SpecLift consuma l'indice.
- **A-004 — Compatibilità CLI verificata:** `sertor-rag search --type code --json` ritorna un array JSON
  piatto con `path`/`chunk_id`; SpecLift legge `path`/`chunk_id` → combacia; `--type code` non è impattato
  dal breaking change di `--type both` (feature 070).
- **A-005 — MVP upstream stabile:** l'MVP Sinthari è mergiato e verde (104 test) e non subirà modifiche
  upstream imminenti che invaliderebbero il vendoring nel breve periodo.
- **A-006 — Pin 3.12 probabilmente riducibile:** nessuna sintassi 3.12-only rilevata nel grep del recon
  (`StrEnum` è 3.11+); la verifica empirica su 3.11 (FR-018) è la condizione di accettazione — resta il
  ramo FR-019 se il grep si rivelasse incompleto.

### Fuori ambito (dichiarato)
- **Distribuzione su ospiti esterni** (installer/packaging per chi installa Sertor da zero): **FEAT-002**,
  epica separata — casa di distribuzione non ancora decisa.
- **Traduzione IT→EN** degli asset SpecLift: tema linguistico trasversale (E12), tracciato altrove.
- **Implementazione della famiglia futura** (SpecAudit, Debrief, Guida al test): capacità distinte e future
  (backlog epica `speclift` FEAT-003/004/005), non in ambito qui.
- **Contribuire a monte a Sinthari** (nessuna PR verso `github.com/themetriost/Sinthari`).
- **Qualunque modifica a `sertor_core`**: la libreria resta byte-identica (Principio XI).
- **Automatizzare l'invocazione di SpecLift nel rituale di step** (gate automatico o innesco a ogni commit):
  resta uno strumento su richiesta.
- **Correggere la narrativa upstream** sulla discrepanza doc↔codice: si dichiara lato Sertor, non si
  corregge a monte.
- **Il *come* di dettaglio** (modalità di vendoring, collocazione di `jsonschema`, meccanismo di
  configurazione del vehicle): fase di **design/plan**.

> **Tracciamento dello scope.** I rinvii reali di questa feature sono già promossi a case durevoli: la
> distribuzione su ospiti è **FEAT-002** (backlog epica `speclift`); la famiglia SpecAudit/Debrief/Guida al
> test è **FEAT-003/004/005** (stesso backlog); la traduzione IT→EN è tema **E12**. Nessun rinvio reale
> resta sepolto in `specs/`. La feature è *done* quando: SpecLift gira nel repo Sertor producendo evidenza
> ancorata e un report riverificato (US1); `sertor_core` è invariato e il workspace risolve senza cicli
> (US2/US5); il fail-loud su indice assente è azionabile (US3); il vehicle punta alla root Sertor (US4); la
> provenienza è tracciata (US6); la skill host-agnostica è depositata (US7); la discrepanza doc↔codice è
> dichiarata (US8); la versione Python è riconciliata con verifica empirica o l'irriducibilità è dichiarata
> (US9).

### Forche di design — per `/speckit-plan` (sono *come*, non scope)
- **DA-D-1 — Copia versionata vs sync del vendoring.** (a) copia one-shot pinnata al commit `be4da28`,
  documentata dalla nota di provenienza, con aggiornamenti futuri come azione manuale esplicita; (b)
  meccanismo di sync analogo a `sync.py`/`generate.py` di `sertor-flow`. Nota: il precedente SpecKit ha
  abbandonato il vendoring per un launch-installer, ma SpecLift ha **codice runtime proprio eseguibile** →
  il pattern launch-installer non si applica direttamente. Raccomandazione debole (a); decisione al plan.
  *(FR-001/002/003)*
- **DA-D-2 — `jsonschema` runtime → dev.** Il recon conferma che `jsonschema` è usata **solo** dai test di
  contratto; spostarla in `[dev]` ridurrebbe l'impronta runtime senza perdere copertura, ma è una
  divergenza dal `pyproject.toml` upstream da documentare (FR-005) e verificare (nessun import runtime
  nascosto). Raccomandazione debole: spostarla; decisione al plan. *(RNF-2)*
- **DA-D-3 — Meccanismo di configurazione del vehicle RAG.** (a) patchare la costante `DEFAULT_CONFIG`
  nella copia vendorata, documentando la divergenza puntuale; (b) estendere il codice vendorato con una
  variabile d'ambiente (es. `SPECLIFT_RAG_VEHICLE`) letta da `config.py`, riusabile anche da un futuro
  ospite (FEAT-002) ma modifica funzionale da ri-applicare a ogni sync; (c) wrapper/composition locale che
  costruisce `Config` programmaticamente, bypassando l'entry-point console. Il requisito comportamentale
  (FR-004) resta valido indipendentemente dal meccanismo. *(FR-004/005)*
