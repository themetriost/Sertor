# Feature Specification: auto-update version check (avviso d'aggiornamento al SessionStart) (E2-FEAT-013)

**Feature Branch**: `feat013-version-check-backlog` · **Created**: 2026-06-25 · **Status**: Draft

<!-- Deriva da: FEAT-013 (epica sertor-cli E2) — requirements/sertor-cli/version-update-check/requirements.md -->

**Input**: FEAT-013 dell'epica `sertor-cli` (E2). Sertor è distribuito in modo **interim via `git+url`
non-PyPI** (DA-4 dell'epica), e `uvx` **cacha** la build per revisione: dopo che `master` si muove, un
ospite può restare **silenziosamente** su una versione vecchia di Sertor (installer, runtime RAG in
`.sertor/.venv`, asset wiki/governance). Oggi l'unico modo per accorgersene è la sezione manuale
«Refreshing to the latest» della doc (`docs/install.md §10.1`): **nessun segnale automatico**. Questa
feature aggiunge un **avviso non invasivo a inizio sessione**: se la versione installata di Sertor non è
l'ultima, l'agente/utente lo **vede** e riceve il comando per aggiornare; **l'utente decide** se e quando
farlo (mai auto-upgrade). È il **gemello concettuale di E10-FEAT-011** (hook di freschezza dell'indice):
stesso confine **D↔N** — un harness deterministico **segnala**, l'utente **agisce** — e stesso pattern
host-facing (hook distribuito dall'installer, parità Claude / Copilot CLI). La fonte di verità della
versione è il file **`/VERSION`** a radice del repo, già letto dinamicamente da tutti e quattro i
`pyproject` (singola fonte per `sertor`, `sertor-flow`, `sertor-core`, `sertor-install-kit`).

---

> **Allineamento alla missione (gate Constitution).** La missione di Sertor è la qualità del contesto
> reso all'agente; un ospite **silenziosamente stantio** ne è una minaccia *indiretta* ma reale —
> retrieval, wiki e governance dell'agente girano su una versione vecchia senza che nessuno lo sappia, e
> i fix/miglioramenti non arrivano. Rendere **visibile** la disponibilità di un aggiornamento serve
> l'**adozione e la portabilità** (Principio X, host-agnostico): un ospite qualsiasi sa da solo quando è
> indietro. È coerente col confine **D↔N**: il check è **meccanico** (segnala, **non chiama mai un LLM**,
> **non importa `sertor_core`**); la decisione e l'azione restano all'utente. La feature è **periferica**
> al differenziatore (fusione code+doc) ma ne è un abilitatore: tiene gli ospiti su una Sertor corrente.

> **Natura del cambiamento: ADDITIVO (harness + distribuzione), nessun codice di core.** La feature
> **non** modifica il runtime del core né i comandi d'aggiornamento: **raccomanda** i comandi esistenti
> (`sertor upgrade` / `uvx --refresh`), mai li reimplementa e mai applica un aggiornamento da sé.
> Introduce: un **check cachato (~1/giorno)** che confronta la versione installata con l'ultima pubblicata
> e ne persiste l'esito; un **avviso a inizio sessione** che, se l'ospite è indietro, lo rende evidente e
> nomina il comando d'aggiornamento; il **wiring di distribuzione** host-facing via `sertor install` /
> `sertor-flow install` con parità Claude / Copilot CLI e lifecycle install/upgrade/uninstall; la voce
> `.gitignore` per lo stato runtime. A feature non installata il comportamento e il costo sono **identici
> a oggi**. È il corollario «feature completa»: non è *done* finché un ospite Claude **e** uno Copilot
> ricevono l'asset via l'installer.

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Il **meccanismo installer per hook
> host** (asset + voce `SessionStart`/`SessionEnd` per-assistente + lifecycle install/upgrade/uninstall)
> è collaudato dal gemello E10-FEAT-011 (`rag-freshness.ps1` / `rag-freshness-start.ps1`, wiring in
> `packages/sertor/src/sertor_installer/install_rag.py`) e da `memory-capture`; il **seam di parità**
> `AssistantProfile` traduce il formato hook/prompt nel nativo di ciascun assistente (Claude script ↔
> Copilot CLI prompt statico, lezione FEAT-011/049); `RUNTIME_IGNORES`
> (`packages/sertor-install-kit/.../gitignore_append.py`) è il punto per la voce dello stato; **`/VERSION`**
> a radice è la fonte unica già letta dai `pyproject`. I riferimenti **ancorano** i requisiti, non
> prescrivono il *come* (URL esatto del `/VERSION` remoto, formato del file di stato, voce hook a cui
> agganciare il check e l'avviso, fusione vs separazione dall'hook di freschezza = design).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — L'ospite indietro lo scopre a inizio sessione (P1, Must)
L'ospite ha una versione installata di Sertor più vecchia dell'ultima pubblicata su `master`. All'avvio
della sessione vede un avviso non invasivo che nomina la versione installata, l'ultima disponibile e il
**comando d'aggiornamento** (`sertor upgrade` / `uvx --refresh …`). Senza l'avviso resterebbe
silenziosamente su una Sertor stantia.

**Independent Test**: con una versione installata più vecchia di quella in `/VERSION` su `master`, l'avvio
sessione produce un avviso che nomina versione installata, ultima versione e comando d'aggiornamento;
nessun aggiornamento è applicato automaticamente.

**Acceptance**:
1. **Given** un ospite con una capacità Sertor installata e versione installata più vecchia dell'ultima,
   **When** la sessione inizia, **Then** l'utente vede un avviso che nomina versione installata, ultima
   versione e il comando d'aggiornamento raccomandato.
2. **Given** la versione installata uguale o più nuova dell'ultima, **When** la sessione inizia, **Then**
   **nessun avviso** è presentato.
3. **Given** l'avviso presentato, **When** lo si osserva, **Then** la feature **non** applica alcun
   aggiornamento da sé: notifica soltanto, lasciando decisione e azione all'utente.

### User Story 2 — Determinazione «installato vs ultimo» da `/VERSION` (P1, Must)
La feature determina l'ultima versione disponibile leggendo il file **`/VERSION`** dalla sorgente di
distribuzione `git+url` su `master` e la confronta con la versione installata. La sorgente di verità è il
bump di `/VERSION` (non il SHA di commit): «c'è una nuova versione» = `/VERSION` è cresciuto.

**Independent Test**: la feature ottiene l'ultima versione dal `/VERSION` remoto su `master` e la confronta
con l'installata, derivando un verdetto indietro / allineato / più-nuovo; non usa il SHA di commit.

**Acceptance**:
1. **Given** una sorgente di distribuzione `git+url`, **When** il check gira, **Then** ottiene l'ultima
   versione leggendo `/VERSION` su `master` e la confronta con la versione installata.
2. **Given** il `/VERSION` remoto cresciuto rispetto all'installato, **When** si confronta, **Then** il
   verdetto è «indietro».
3. **Given** l'installato uguale o più nuovo del remoto (es. dev locale), **When** si confronta, **Then**
   il verdetto **non** è «indietro» (nessun falso «sei indietro»).

### User Story 3 — Economico: al più ~1 chiamata di rete al giorno (P1, Must)
Il check costa **al più ~1 chiamata di rete al giorno** per ospite: l'esito è cachato e, finché è ancora
fresco, riusato senza una nuova lettura di rete. L'avvio di sessione non è appesantito da una GET a ogni
apertura.

**Independent Test**: a cache valida, una nuova sessione riusa l'esito senza alcuna chiamata di rete; una
nuova lettura avviene solo quando la cache è scaduta (~24h) o un re-check è forzato.

**Acceptance**:
1. **Given** un esito cachato ancora fresco (entro ~24h), **When** la sessione inizia, **Then** il
   sistema riusa l'esito **senza** una nuova chiamata di rete.
2. **Given** la cache scaduta (oltre ~24h), **When** la sessione inizia, **Then** il sistema esegue al più
   una nuova chiamata di rete e ricacha l'esito.
3. **Given** più sessioni nello stesso giorno, **When** si contano le chiamate di rete, **Then** sono al
   più ~1 per ospite (cache rispettata).

### User Story 4 — Offline e fallimenti: skip silenzioso, mai bloccante (P1, Must)
Se la rete non è disponibile o la lettura della versione fallisce, il check **salta silenziosamente** (nessun
avviso, nessun errore) e la sessione parte normalmente (exit 0). Allo stesso modo, se `/VERSION` non è
interpretabile o la versione installata non è determinabile, il check è trattato come **indeterminato** e
salta — mai un falso «sei indietro».

**Independent Test**: senza rete (o con lookup fallito) la sessione parte normalmente senza avviso né
errore; con `/VERSION` non parsabile o installato non determinabile, il check è indeterminato e silenzioso.

**Acceptance**:
1. **Given** rete non disponibile o lookup della versione fallito, **When** la sessione inizia, **Then**
   il check salta silenziosamente (nessun avviso, nessun errore) e la sessione parte (exit 0).
2. **Given** `/VERSION` non parsabile o versione installata non determinabile, **When** il check gira,
   **Then** è trattato come indeterminato e salta — mai un falso «sei indietro».
3. **Given** un qualunque fallimento del check, **When** si verifica, **Then** **non** blocca né fa
   fallire l'avvio della sessione.

### User Story 5 — Stato persistito sotto `.sertor/` (P2, Should)
Il check persiste l'ultimo esito (ultima versione vista, versione installata, timestamp, verdetto) sotto la
cartella runtime `.sertor/` (es. `.sertor/.version-check.json`), così la cache attraversa il confine di
sessione e lo stato è leggibile dall'avviso d'avvio. Lo stato runtime è aggiunto al `.gitignore`
dell'ospite (mai versionato).

**Independent Test**: dopo un check, esiste un file di stato sotto `.sertor/` che riporta ultima versione,
installata, timestamp e verdetto; il file è coperto dal `.gitignore` dell'ospite.

**Acceptance**:
1. **Given** un check eseguito, **When** completa, **Then** persiste l'esito (ultima versione vista,
   versione installata, timestamp, verdetto) sotto `.sertor/`.
2. **Given** lo stato persistito, **When** lo legge l'avviso d'avvio, **Then** vi trova quanto basta per
   decidere se avvisare senza una nuova chiamata di rete.
3. **Given** la voce di stato runtime, **When** si verifica il `.gitignore` dell'ospite, **Then**
   `.sertor/.version-check.json` vi è incluso (stato rigenerabile, mai versionato).

### User Story 6 — Copertura delle 3 dimensioni con fonte unica (P2, Should)
Il check copre **tutte le dimensioni installate** — RAG + wiki (pacchetto `sertor`) e governance
(`sertor-flow`) — usando `/VERSION` come **fonte unica**. Quando più pacchetti Sertor sono installati e
riportano versioni installate diverse, l'avviso nomina **quale/i dimensione/i** è indietro.

**Independent Test**: con `sertor` e `sertor-flow` installati a versioni diverse, l'avviso nomina la/le
dimensione/i indietro; con una sola dimensione installata, il check copre quella.

**Acceptance**:
1. **Given** una o più dimensioni Sertor installate, **When** il check gira, **Then** copre ogni
   dimensione installata usando `/VERSION` come fonte unica di confronto.
2. **Given** più pacchetti Sertor a versioni installate diverse, **When** uno è indietro, **Then** l'avviso
   nomina quale/i dimensione/i è indietro.
3. **Given** una sola dimensione installata, **When** il check gira, **Then** si applica solo a quella
   (le dimensioni non installate non producono avviso).

### User Story 7 — La loop si chiude dopo l'aggiornamento (P2, Should)
Dopo che l'utente ha aggiornato Sertor, al check successivo il sistema riflette la nuova versione installata
e riporta il verdetto ad allineato: l'avviso non si ripresenta. L'aggiornamento a metà giornata invalida lo
stato cachato così non si avvisa a vuoto.

**Independent Test**: dopo un aggiornamento, il check successivo riflette la nuova versione installata e
torna ad «allineato» (nessun avviso); se la versione installata cambia, lo stato cachato non riavvisa a vuoto.

**Acceptance**:
1. **Given** l'utente ha aggiornato Sertor, **When** il check successivo gira, **Then** riflette la nuova
   versione installata e il verdetto torna ad allineato.
2. **Given** il verdetto allineato, **When** la sessione inizia, **Then** nessun avviso è presentato (la
   loop si chiude).
3. **Given** un aggiornamento a metà giornata mentre lo stato cachato dice «indietro», **When** il check
   rileva la nuova versione installata, **Then** lo stato è invalidato/aggiornato così non si avvisa a vuoto.

### User Story 8 — Asset host-facing con parità Claude / Copilot CLI (P2, Should)
Eseguendo `sertor install` (o `sertor-flow install`), un ospite riceve l'asset di version-check e il suo
wiring **nel formato nativo** del proprio assistente (Claude script di sessione vs Copilot CLI prompt
statico al SessionStart), mai il formato Claude su Copilot. L'avviso è veicolato dal meccanismo di sessione
dell'assistente: su Copilot, dove il SessionStart è un prompt statico che non può fare rete, il prompt
istruisce l'agente a leggere lo stato persistito e relayare l'avviso. È il completamento della feature:
senza distribuzione resta dogfood-only e non è *done*.

**Independent Test**: l'installer deposita l'asset (asset + wiring) nel contenitore nativo di ciascun
assistente; su Copilot il formato è quello nativo Copilot, non Claude; l'avviso è raggiungibile dal
meccanismo di sessione di entrambi.

**Acceptance**:
1. **Given** un ospite Claude e uno Copilot, **When** eseguo l'installer per la capacità che lo include,
   **Then** l'asset di version-check è depositato con il suo wiring su ciascuno, non-distruttivamente e
   idempotentemente.
2. **Given** il target Copilot, **When** l'asset è depositato, **Then** è nel formato nativo Copilot (prompt
   statico al SessionStart che legge lo stato e relaya l'avviso), mai il formato Claude (parità —
   FEAT-011/049).
3. **Given** l'asset depositato, **When** se ne osserva il wiring, **Then** è coerente con il ciclo di vita
   install/upgrade/uninstall (lifecycle FEAT-008).

### User Story 9 — Re-check forzato (P3, Could)
Quando l'utente richiede un re-check forzato, il sistema ri-esegue il check ignorando la cache giornaliera,
così può verificare immediatamente dopo un aggiornamento o quando sospetta di essere indietro.

**Independent Test**: con un re-check forzato richiesto, il sistema esegue una nuova lettura ignorando la
cache fresca; senza la richiesta, rispetta la cache (US3).

**Acceptance**:
1. **Given** la cache ancora fresca, **When** l'utente richiede un re-check forzato, **Then** il sistema
   ri-esegue il check ignorando la cache giornaliera.
2. **Given** un re-check forzato, **When** completa, **Then** aggiorna lo stato persistito con l'esito
   fresco.

## Edge Cases
- **Offline / lookup fallito**: skip silenzioso, sessione normale (exit 0); nessun avviso, nessun errore
  (US4, REQ-008).
- **`/VERSION` non parsabile o installato non determinabile**: check indeterminato → skip; mai un falso
  «sei indietro» (US4, REQ-009).
- **Installato più nuovo del remoto (dev locale)**: verdetto «non indietro», nessun avviso (US2,
  REQ-004/DA-5).
- **Cache fresca**: zero rete, esito riusato (US3, REQ-006).
- **Aggiornamento a metà giornata con cache «indietro»**: stato invalidato sulla nuova versione installata
  → niente avviso a vuoto (US7, REQ-017, R-5).
- **Più dimensioni a versioni diverse**: l'avviso nomina la/le dimensione/i indietro (US6, REQ-011).
- **Una sola dimensione installata**: il check si applica solo a quella; le non installate non avvisano
  (US6, REQ-010).
- **Copilot CLI senza script al SessionStart**: il SessionStart è prompt statico (niente rete) → il check
  «vivo» va eseguito da uno script (a chi tocca = DA-1, design); il prompt si limita a leggere lo stato e
  relayare (US8, R-3).
- **`pwsh` assente sull'ospite**: niente check automatico; la doc resta la via manuale (assunzione, NFR
  portabilità).
- **Bump di `/VERSION` raro**: se la versione non è bumpata a ogni cambiamento di `master`, l'avviso
  sotto-segnala la staleness — accettato per decisione (low-noise; il SHA di commit è fuori ambito) (R-1).
- **Coesistenza con l'hook di freschezza (FEAT-011)**: due segnali a inizio/fine sessione devono coesistere,
  entrambi non-fatali, asset/voci distinti (o piggyback condiviso — DA-4 design) (R-4).

## Requirements *(mandatory)*

### Requisiti funzionali

**Check a inizio sessione e avviso (rituale di aggiornamento)**
- **FR-001 (check event-driven all'avvio).** Quando una sessione inizia su un ospite con una capacità
  Sertor installata, il sistema determina se la versione installata di Sertor è l'ultima disponibile.
  *(REQ-001; CS-1)*
- **FR-002 (ultima versione da `/VERSION`).** Il sistema determina l'ultima versione disponibile leggendo
  il file `/VERSION` dalla sorgente di distribuzione `git+url` del progetto (`master`) e confrontandola con
  la versione installata. *(REQ-002; CS-3)*
- **FR-003 (avviso quando indietro).** Quando la versione installata è più vecchia dell'ultima, il sistema
  presenta all'utente un avviso che nomina la versione installata, l'ultima versione e il comando
  d'aggiornamento raccomandato (`sertor upgrade` / `uvx --refresh …`). *(REQ-003; CS-1)*
- **FR-004 (nessun avviso quando allineato/più nuovo).** Se la versione installata è uguale o più nuova
  dell'ultima, il sistema **non** presenta alcun avviso d'aggiornamento. *(REQ-004; CS-1)*
- **FR-005 (mai auto-upgrade).** Il sistema **non** applica mai un aggiornamento automaticamente; notifica
  soltanto, lasciando la decisione e l'azione all'utente. *(REQ-005; CS-4)*

**Cadenza e caching (~1/giorno)**
- **FR-006 (check al più ~1/giorno).** Il version check gira al più una volta ogni ~24h per ospite; finché
  un esito cachato è ancora fresco, il sistema lo riusa **senza** una nuova chiamata di rete. *(REQ-006;
  CS-2)*
- **FR-007 (stato persistito).** Il sistema persiste l'ultimo esito del check (ultima versione vista,
  versione installata, timestamp, verdetto) sotto la cartella runtime `.sertor/` (es.
  `.sertor/.version-check.json`). *(REQ-007; CS-2)*
- **FR-008 (re-check forzato).** Quando è richiesto un re-check forzato, il sistema ri-esegue il check
  ignorando la cache giornaliera. *(REQ-018; US9)*

**Degradazione non-fatale**
- **FR-009 (offline → skip silenzioso).** Se la rete non è disponibile o il lookup della versione
  fallisce, il sistema salta il check silenziosamente (nessun avviso, nessun errore) e la sessione parte
  normalmente (exit 0). *(REQ-008; CS-2; NFR affidabilità)*
- **FR-010 (indeterminato → skip silenzioso).** Se `/VERSION` non è interpretabile o la versione installata
  non è determinabile, il sistema tratta il check come indeterminato e salta silenziosamente — mai un falso
  «sei indietro». *(REQ-009)*

**Copertura delle dimensioni**
- **FR-011 (copre rag+wiki+governance).** Il check copre ogni dimensione Sertor installata — RAG + wiki
  (pacchetto `sertor`) e governance (`sertor-flow`) — usando `/VERSION` come fonte unica di verità.
  *(REQ-010; CS-3)*
- **FR-012 (nomina la dimensione indietro).** Quando più pacchetti Sertor sono installati e riportano
  versioni installate diverse, il sistema nomina quale/i dimensione/i è indietro. *(REQ-011; US6)*

**Chiusura della loop**
- **FR-013 (riflette l'aggiornamento).** Quando l'utente ha aggiornato Sertor, al check successivo il
  sistema riflette la nuova versione installata e riporta il verdetto ad allineato (la loop si chiude).
  *(REQ-017; US7)*

**D↔N e privacy**
- **FR-014 (no LLM, no `sertor_core`).** Il check **non** invoca alcun LLM e **non** importa `sertor_core`;
  usa solo mezzi deterministici (una GET semplice di `/VERSION` + una lettura/confronto di file). *(REQ-015;
  RNF determinismo)*
- **FR-015 (nessun contenuto/segreto in rete).** Il check **non** trasmette alcun contenuto o segreto del
  progetto; l'unico traffico di rete in uscita è la lettura del `/VERSION` pubblico. *(REQ-016; CS-6)*

**Distribuzione host-facing (installer)**
- **FR-016 (deposito via install, parità).** Quando l'utente installa una capacità Sertor, l'installer
  deposita l'asset di version-check e il suo wiring per l'assistente scelto (Claude / Copilot CLI),
  non-distruttivamente e idempotentemente, nel formato nativo dell'assistente. *(REQ-012/013; CS-5)*
- **FR-017 (lifecycle completo).** L'asset di version-check ha ciclo di vita completo install / upgrade /
  uninstall, coerente con la macchina lifecycle dell'installer (FEAT-008). *(REQ-013; CS-5)*
- **FR-018 (voce `.gitignore`).** Il sistema aggiunge `.sertor/.version-check.json` al `.gitignore`
  dell'ospite (stato rigenerabile, mai versionato). *(REQ-014; CS-5)*

### Requisiti non funzionali
- **RNF-1 (performance):** con cache valida → **zero rete**; il check live ha un timeout breve e non
  prolunga l'avvio oltre il timeout dell'hook host (NFR gemello di FEAT-011). *(NFR Performance; FR-006/009)*
- **RNF-2 (affidabilità, non-fatale):** l'asset esce sempre **0** e non blocca mai la sessione (gemello di
  `rag-freshness.ps1`). *(NFR Affidabilità; FR-009)*
- **RNF-3 (portabilità):** host-agnostico, Windows + POSIX (`pwsh`); **parità** Claude / Copilot CLI.
  *(NFR Portabilità; FR-016)*
- **RNF-4 (privacy):** solo GET del `/VERSION` pubblico; nessun contenuto/segreto. *(NFR Privacy; FR-015)*
- **RNF-5 (additività):** a feature non installata, comportamento e costo **identici a oggi**; nessun LLM
  nel percorso (Principio D↔N / XI). *(NFR Additività; FR-014)*
- **RNF-6 (osservabilità opzionale):** un eventuale evento è **metrics-only** (nessun path/segreto),
  coerente con gli altri hook. *(NFR Osservabilità)*

### Key Entities
- **Check di version-update (harness deterministico)** — il nuovo attore non-LLM: legge l'ultima versione
  da `/VERSION` remoto, la confronta con l'installata, applica la cache (~1/giorno) e ne persiste l'esito.
  *Segnala soltanto, non ragiona e non aggiorna.*
- **Stato di version-check (file persistito)** — l'esito scritto su file locale sotto `.sertor/` (es.
  `.sertor/.version-check.json`) che attraversa il confine di sessione; contiene almeno ultima versione
  vista, versione installata, timestamp e verdetto; gitignored; nome/formato esatti = design.
- **Verdetto di versione** — indietro / allineato / più-nuovo (e indeterminato), derivato dal confronto
  installato↔ultimo; gate dell'avviso.
- **`/VERSION` (fonte unica)** — il file a radice del repo, letto dai `pyproject`, sorgente sia
  dell'«installato» sia (via GET su `master`) dell'«ultimo». Esiste già; la feature lo **legge**.
- **Avviso d'aggiornamento** — il messaggio veicolato a inizio sessione quando l'ospite è indietro; nomina
  installato, ultimo e il comando d'aggiornamento (`sertor upgrade` / `uvx --refresh`); non applica nulla.
- **Voci/asset per-assistente** — l'asset e il wiring di sessione nel formato nativo di ciascun assistente
  (Claude script ↔ Copilot CLI prompt statico), con lifecycle install/upgrade/uninstall.

## Success Criteria *(mandatory)*
- **CS-1 (avviso corretto):** a inizio sessione, se la versione installata è più vecchia dell'ultima,
  l'utente vede un avviso che nomina versione corrente, ultima versione e comando d'aggiornamento; se è
  allineata (o più nuova), **nessun avviso**. *(FR-001/002/003/004, US1/US2)*
- **CS-2 (economico & non bloccante):** il check costa **al più ~1 chiamata di rete al giorno** per ospite
  (esito cachato); **non blocca** l'avvio; **offline → nessun avviso e nessun errore** (la sessione parte
  normalmente). *(FR-006/007/009, US3/US4)*
- **CS-3 (copertura 3 dimensioni):** il check copre tutte le dimensioni installate — RAG + wiki (`sertor`)
  e governance (`sertor-flow`) — usando `/VERSION` come fonte unica. *(FR-011/012, US6)*
- **CS-4 (solo avviso):** in **0** casi la feature applica un aggiornamento da sola; notifica soltanto.
  *(FR-005, US1)*
- **CS-5 (host-agnostico & installabile):** l'asset di version-check è installabile su **Claude e Copilot
  CLI** via l'installer, con **parità** e ciclo di vita (install/upgrade/uninstall), additivo e non
  distruttivo. *(FR-016/017/018, US8)*
- **CS-6 (D↔N & privacy):** il check **non invoca alcun LLM** e **non importa `sertor_core`**; l'unico
  traffico di rete è la lettura del `/VERSION` pubblico (nessun contenuto/segreto del progetto esce).
  *(FR-014/015)*

## Assumptions
- **A-001 — `/VERSION` come fonte unica:** è letto da tutti i `pyproject` → un solo confronto copre i
  pacchetti; «ultima versione» = `/VERSION` su `master` via GET raw. Prerequisito soddisfatto (file
  presente a radice, oggi `0.1.0`). *(FR-002/011)*
- **A-002 — Meccanismo installer per hook host riusabile (E10-FEAT-011 + `memory-capture`):** asset + voce
  `SessionStart`/`SessionEnd` per-assistente + lifecycle è collaudato; questa feature lo riusa.
  *(FR-016/017)*
- **A-003 — Seam di parità `AssistantProfile`:** traduce il formato hook/prompt nel nativo di ciascun
  assistente (Claude script ↔ Copilot CLI prompt statico); riusato, non reinventato. *(FR-016)*
- **A-004 — `sertor upgrade` / `uvx --refresh` esistono:** sono l'azione raccomandata dall'avviso
  (FEAT-008 lifecycle); la feature li nomina, non li reimplementa. *(FR-003)*
- **A-005 — Rete verso la sorgente `git+url` raggiungibile quando il check live gira:** altrimenti skip
  silenzioso (FR-009). *(FR-002/009)*
- **A-006 — `pwsh` presente per lo script (come per gli altri hook):** assente → niente check automatico;
  la doc resta la via manuale. *(RNF-3)*
- **A-007 — `sertor-core` invariato:** la feature è host-facing (asset installer), additiva; nessun codice
  runtime del core. *(RNF-5)*

### Fuori ambito (dichiarato)
- **L'applicazione dell'aggiornamento** — è dei comandi esistenti `sertor upgrade` / `uvx --refresh`
  (FEAT-008): la feature li **raccomanda**, non li sostituisce.
- **Rilevazione a livello di commit (SHA di `master`)** — **scartata** per decisione (low-noise sul bump di
  `/VERSION`); se mai servisse, è una capacità separata da promuovere.
- **Pubblicazione/versioning PyPI** (FEAT-006, Won't) — qui «ultimo» = `/VERSION` su `master`.
- **Pulizia degli artefatti obsoleti durante l'aggiornamento** — è **E10-FEAT-015** (debito separato).
- **Freschezza dell'indice RAG** — è **E10-FEAT-011** (gemello, già consegnato): questa feature riguarda la
  versione del *pacchetto*, non la freschezza del *corpus*.
- **Il *come* di dettaglio** (URL esatto del `/VERSION` remoto e sua parametrizzazione per fork/branch;
  nome/posizione/formato del file di stato; sorgente esatta della versione «installata»; chi esegue la GET
  su Copilot; fusione vs separazione dall'hook di freschezza; semantica del confronto di versione):
  fase di **design/plan** (DA-1..DA-5).

> **Tracciamento dello scope.** La rilevazione **commit-SHA** (più granulare del bump di `/VERSION`) è
> scartata per decisione; se mai diventasse una capacità reale va aperta come **nuova FEAT** dell'epica
> `sertor-cli` (non sepolta in `specs/`). La **pulizia artefatti obsoleti** è già **E10-FEAT-015**. La
> **freschezza del corpus** è già **E10-FEAT-011**. La feature non è *done* finché un ospite Claude **e**
> uno Copilot ricevono l'asset via l'installer (corollario «feature completa»): è in ambito
> (FR-016..018), non un debito rinviato.

### Forche di design — da chiudere in `/speckit-clarify` o `/speckit-plan`
Le quattro **decisioni di scope** sono **fissate** (incorporate sopra, non riaperte): (1) home = epica
`sertor-cli` (E2); (2) «newer» = bump di `/VERSION` su `master` via GET raw, non il SHA di commit; (3) check
cachato ~1/giorno con stato in `.sertor/.version-check.json`, non-fatale offline (exit 0, skip silenzioso);
(4) solo avviso, mai auto-upgrade. Restano **forche di *come*** (DA-1..DA-5 dei requisiti), che **non
cambiano lo scope** e si chiudono in design:

- **DA-1 (design) — Chi esegue il check su Copilot CLI (e dove conviene su Claude):** il SessionStart di
  Copilot è un **prompt statico** (nessuno script → niente GET). *Proposta (raccomandata):* eseguire il
  check in uno **script** (sul modello del `SessionEnd` di FEAT-011, script su entrambi gli assistenti) che
  fa la GET, applica la cache e **scrive** `.sertor/.version-check.json`; il **SessionStart** (script su
  Claude, prompt su Copilot) si limita a **leggere lo stato e avvisare**. Così la parità regge e nessuno fa
  rete in un prompt statico.
- **DA-2 (design) — Sorgente esatta del `/VERSION` «ultimo»:** URL raw su `master` (es.
  `raw.githubusercontent.com/<owner>/<repo>/master/VERSION`), derivabile dalla config di distribuzione; come
  parametrizzarlo per ospiti che puntano a fork/branch diversi.
- **DA-3 (design) — Sorgente della versione «installata»:** metadati del pacchetto
  (`sertor`/`sertor-flow`/`sertor-core`) vs un `/VERSION` locale copiato a install-time.
- **DA-4 (design) — Fusione vs separazione dall'hook di freschezza (FEAT-011):** asset/voce **separati**
  (gemello indipendente, come memory-capture ↔ rag-freshness) **oppure** estendere lo stesso script di fine
  sessione ad aggiornare anche `.version-check.json`. *Proposta:* separati per lifecycle granulare, ma
  valutare il piggyback sul SessionEnd per non duplicare la GET.
- **DA-5 (design) — Confronto di versione:** semantica del confronto (`semver` vs confronto lessicale del
  contenuto di `/VERSION`) e cosa fare se l'installato risulta più nuovo del remoto (dev locale → «non
  indietro», FR-004).
