# Feature Specification: enforcement deterministico della freschezza RAG (hook) (E10-FEAT-011)

**Feature Branch**: `076-enforcement-freschezza-rag` · **Created**: 2026-06-24 · **Status**: Draft

<!-- Deriva da: FEAT-011 (epica debito-tecnico E10) — requirements/debito-tecnico/enforcement-freschezza-rag/requirements.md -->

**Input**: FEAT-011 dell'epica `debito-tecnico` (E10). Il **rituale di step** del progetto
(`CLAUDE.md`, *Definition of Done*) prevede due passi **meccanici** a chiusura di ogni step
significativo — **punto 5** (re-index del corpus toccato, perché il dogfooding non serva mai contesto
stantio) e **punto 8** (smoke test del RAG di dogfooding, perché il server sia *vivo e fresco*, non
solo che l'indice su disco esista). Questi due passi **si saltano nei fatti**: la lezione del
2026-06-20 li classifica come **costosi + condizionati + auto-eseguiti dall'agente**, e la
condizionalità è il buco da cui scivolano (il commit invece sopravvive perché **cheap + delegato +
incondizionato**). Il risultato è il rischio centrale della mission: l'agente ragiona su **contesto
non reale** perché l'indice è stantio e nessuno se ne accorge. La causa non è la volontà dell'agente
ma la **collocazione** dei passi. Questa feature li sposta dalla discrezione dell'agente a un
**harness deterministico** (hook del client agente): la parte **meccanica** (re-index + verifica di
salute) diventa *enforced*, mentre all'agente resta il **giudizio** — applicazione del confine **D↔N**.
La capacità è **host-facing**: come gli altri hook del rituale (cattura memoria, uso-vehicle), va
**distribuita agli ospiti** via installer, non vivere solo nel `.claude/` di Sertor (Principio X +
regola «una feature è completa solo se installabile su un ospite»).

---

> **Allineamento alla missione (gate Constitution).** La freschezza del RAG è **al cuore** della
> stella polare di Sertor: la qualità del contesto reso all'agente *nel tempo*. Un indice stantio è
> esattamente «l'agente ragiona su contesto non reale» — il fallimento che tutto l'apparato (RAG +
> wiki + lint) esiste per prevenire. Spostare i passi meccanici di freschezza in un harness
> deterministico **realizza** quella prevenzione invece di affidarla alla memoria dell'agente. È
> coerente col confine **D↔N**: l'hook è **meccanico** (segnala e induce, non ragiona, **non chiama
> mai un LLM**); il giudizio resta all'agente. Complementa — senza sovrapporsi — la *drift-detection*
> dell'epica `osservabilita` (FEAT-012): quella **osserva** il drift, questa lo **previene a monte**.

> **Natura del cambiamento: ADDITIVO (harness + distribuzione), nessun codice di core.** La feature
> **non** modifica il motore di re-index né `doctor`: li **consuma** come vehicle (`sertor-rag index .`
> e `sertor-rag doctor`), mai importando `sertor_core` (Principio XI). Introduce: un **hook a fine
> sessione** che re-indicizza e verifica la salute persistendone l'esito; un **segnale a inizio
> sessione** che ripesca l'esito e, se degradato, induce l'azione correttiva; la **reclassificazione**
> dei due passi nel `CLAUDE.md`; il **wiring di distribuzione** host-facing via `sertor install rag`
> con parità Claude / Copilot CLI e lifecycle install/upgrade/uninstall. A indice fresco il
> comportamento è invariato (l'incrementale del core non produce embedding). È il corollario «feature
> completa»: non è *done* finché un ospite Claude **e** uno Copilot ricevono l'hook via
> `sertor install rag`.

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** I vehicle che l'hook orchestra
> esistono già e sono accertati: `sertor-rag index .` (re-index **incrementale** del corpus —
> manifest SQLite FEAT-009 + cache embeddings FEAT-019, su `master`: lo skip-quando-nulla-cambia è già
> nel core); `sertor-rag doctor` (E12-FEAT-001, su `master`: quadro quattro aree env/provider/indice/MCP
> con pass/warn/fail, exit-code gate, offline-safe). Il **meccanismo installer per hook host** (asset
> + voce `SessionEnd`/`SessionStart` per-assistente + lifecycle install/upgrade/uninstall) è collaudato
> per `memory-capture` / `sertor-rag-usage-check`; il **seam di parità** `AssistantProfile` traduce il
> formato hook nel nativo di ciascun assistente (lezione FEAT-011/049). I riferimenti **ancorano** i
> requisiti, non prescrivono il *come* (nome/formato esatto del file di stato, voce hook a cui agganciare
> il segnale di avvio = design).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Il maintainer dogfood non salta più re-index/smoke (P1, Must)
Il maintainer chiude una sessione che ha modificato file indicizzati. Senza alcuna azione manuale e
senza «ricordarsi» dei passi meccanici, l'hook a fine sessione re-indicizza il corpus via vehicle e ne
verifica la salute. I due passi del rituale che oggi scivolano (re-index + smoke) avvengono in modo
**deterministico**, non più alla discrezione dell'agente.

**Independent Test**: in una sessione che modifica file indicizzati, a chiusura l'indice risulta
aggiornato e la salute verificata, **senza** che l'agente abbia eseguito alcun comando manuale; il
re-index è invocato via il vehicle `sertor-rag index .`, mai importando `sertor_core`.

**Acceptance**:
1. **Given** una sessione che ha modificato file indicizzati, **When** la sessione termina, **Then**
   l'hook re-indicizza il corpus invocando `sertor-rag index .` in modo **incondizionato** (nessuna
   logica di delta-check propria dell'hook).
2. **Given** il re-index completato, **When** la sessione termina, **Then** l'hook verifica la salute
   del RAG invocando `sertor-rag doctor` sulle sue quattro aree e ne deriva un verdetto.
3. **Given** l'hook in esecuzione, **When** accede alle capacità di Sertor, **Then** lo fa **solo**
   tramite la CLI vehicle, mai importando o invocando direttamente `sertor_core` (Principio XI).

### User Story 2 — Niente costo quando nulla è cambiato (P1, Must)
Una sessione si chiude senza aver toccato file indicizzati. Il re-index a fine sessione, pur invocato
**incondizionatamente**, non produce alcun ri-embedding: lo skip-quando-nulla-cambia è delegato
all'**incrementale del core** (manifest + cache), non a una logica nell'hook. Il costo è dominato
dall'avvio processo e dal walk del filesystem.

**Independent Test**: a parità di corpus tra due esecuzioni consecutive, la seconda non genera nuovi
embedding; l'hook non implementa alcuna decisione propria di «salta se nulla è cambiato».

**Acceptance**:
1. **Given** nulla di indicizzato cambiato dall'ultimo re-index, **When** l'hook a fine sessione
   esegue, **Then** l'operazione completa senza produrre nuovi embedding.
2. **Given** l'hook, **When** decide se re-indicizzare, **Then** **non** implementa change-detection
   propria: invoca sempre il vehicle e delega lo skip all'incrementale del core.
3. **Given** un corpus invariato, **When** l'hook esegue, **Then** l'unico costo è avvio processo +
   walk del filesystem (nessun costo di embedding aggiuntivo).

### User Story 3 — A inizio sessione un indice degradato è evidente e induce correzione (P1, Must)
La sessione precedente si è chiusa lasciando lo stato di salute **degradato** (indice stantio oppure
un'area `doctor` in warn/fail). All'avvio della sessione successiva il segnale ripesca quell'esito e,
poiché è degradato, lo rende **evidente** all'agente e **induce un'azione correttiva deterministica**
(re-index e/o reconnect del server MCP) **prima** che l'agente cominci a lavorare. Lo stato degradato
non è mai silenziosamente ignorato. Coerente col confine **D↔N**: il segnale **induce**, l'agente
**esegue** il comando correttivo.

**Independent Test**: dopo una sessione che ha lasciato lo stato degradato, l'avvio successivo rende
il fatto evidente e induce l'azione correttiva prima del lavoro di progetto; il segnale non esegue da
sé la correzione né compie giudizio. A guarigione, il marker è pulito e l'induzione non si ripete.

**Acceptance**:
1. **Given** uno stato persistito degradato, **When** la sessione inizia, **Then** il segnale legge lo
   stato, lo rende evidente all'agente e induce un'azione correttiva (re-index e/o reconnect MCP) prima
   del lavoro di progetto.
2. **Given** il segnale di avvio, **When** induce la correzione, **Then** **solo** segnala e induce;
   non decide né esegue il comando da sé — il vehicle correttivo è eseguito dall'agente (D↔N).
3. **Given** l'azione correttiva indotta ha riportato il verdetto a sano, **When** la sessione
   prosegue, **Then** il marker degradato è pulito e l'induzione non si ripete (no loop a ogni avvio).

### User Story 4 — Lo stato di salute degradato sopravvive alla chiusura (P1, Must)
A fine sessione, quando il verdetto è degradato, l'hook **persiste** lo stato di salute RAG su file
locale (che attraversa il confine di sessione) ed emette un **messaggio prominente**. Quando invece il
verdetto è sano, registra lo stato sano **pulendo** ogni marker degradato precedente, così un corpus
recuperato non continua a innescare azioni correttive. Lo stato persistito riporta almeno: il verdetto,
un timestamp e la causa/area che ha fallito.

**Independent Test**: con verdetto degradato, l'hook scrive uno stato persistito leggibile dal segnale
d'avvio ed emette un messaggio; con verdetto sano dopo un degrado, l'hook registra «sano» e rimuove il
marker degradato; lo stato persistito contiene verdetto, timestamp e causa.

**Acceptance**:
1. **Given** un verdetto di fine sessione degradato (indice stantio o un'area `doctor` in fail/warn),
   **When** la sessione termina, **Then** l'hook persiste lo stato di salute su file locale che
   sopravvive al confine di sessione ed emette un messaggio prominente.
2. **Given** un verdetto di fine sessione sano, **When** la sessione termina, **Then** l'hook registra
   lo stato sano e pulisce ogni marker degradato precedente (no inducement perpetuo).
3. **Given** lo stato persistito, **When** lo legge il segnale d'avvio, **Then** vi trova almeno
   verdetto, timestamp e causa/area che ha fallito.

### User Story 5 — Lo smoke dentro l'hook è limitato a `doctor`, con il buco dichiarato (P2, Should)
La verifica di salute dentro l'hook si ferma a `sertor-rag doctor` (quattro aree, exit-code gate) e
**non** esegue una query reale col filtro metadata `where` su `search_code`/`search_docs` — il path del
guasto storico del 2026-06-19. Questo è un **buco dichiarato**, non sepolto: resta affidato all'agente
(rituale punto 8) e va **promosso** come estensione futura di `doctor` (nuova FEAT nell'epica
`usabilità` E12, owner di `doctor`).

**Independent Test**: l'hook esercita `doctor` e non emette alcuna query `where`; il buco
(filtro-metadata non coperto dall'hook) è documentato nella spec e promosso al backlog E12, non lasciato
implicito.

**Acceptance**:
1. **Given** la verifica di salute in-hook, **When** l'hook esegue lo smoke, **Then** invoca solo
   `sertor-rag doctor` e **non** esegue una query metadata-filtrata (`where`) su
   `search_code`/`search_docs`.
2. **Given** il buco (doctor non coglie il guasto del filtro metadata), **When** si traccia lo scope,
   **Then** è dichiarato esplicitamente e promosso a estensione futura di `doctor` nell'epica E12 (non
   sepolto in `specs/`).
3. **Given** il buco aperto, **When** l'hook riporta «verde», **Then** la spec riconosce che il rituale
   punto 8 dell'agente resta la rete fino a quando l'estensione di `doctor` non chiude il buco.

### User Story 6 — Hook separato, non-fatale, isolato dagli altri (P1, Must)
La capacità di freschezza è un **hook dedicato** (script proprio + propria voce `SessionEnd`), distinto
dall'hook `memory-capture` già presente: i due **non** sono fusi in un unico script. Se l'hook di
freschezza fallisce per qualunque motivo, **non blocca né fa fallire** il ciclo di vita della sessione
(esce sempre 0, segnala l'errore in modo non fatale); e se freschezza e `memory-capture` girano
entrambi su `SessionEnd`, il fallimento di uno non impedisce all'altro di girare.

**Independent Test**: l'hook di freschezza ha uno script e una voce dedicati, distinti da
`memory-capture`; un suo errore non blocca la sessione (exit 0) e non impedisce a `memory-capture` di
eseguire, e viceversa.

**Acceptance**:
1. **Given** la capacità di freschezza, **When** è installata, **Then** è uno script dedicato con la
   propria voce `SessionEnd`, distinto e non fuso con `memory-capture`.
2. **Given** un errore interno dell'hook di freschezza, **When** si verifica, **Then** l'hook esce 0 e
   segnala l'errore in modo non fatale, senza bloccare o far fallire il ciclo di vita della sessione.
3. **Given** freschezza e `memory-capture` entrambi su `SessionEnd`, **When** uno dei due fallisce,
   **Then** l'altro gira comunque (isolamento reciproco).

### User Story 7 — La governance riclassifica i due passi come enforced (P1, Must)
Il rituale di step nel `CLAUDE.md` **riclassifica** gli step 5 (re-index) e 8 (smoke) da «standing
behavior (agente)» a «enforced via hook», documentando la sfumatura del confine **D↔N**: l'hook segnala
e induce, l'agente esegue il comando deterministico. Così la fonte di verità del rituale riflette la
nuova collocazione e non lascia i passi descritti come discrezionali.

**Independent Test**: nel `CLAUDE.md` gli step 5 e 8 sono marcati «enforced via hook» con la nota D↔N
(l'hook induce, l'agente esegue); non restano descritti come passi che l'agente deve ricordarsi.

**Acceptance**:
1. **Given** il rituale di step, **When** lo si legge dopo la feature, **Then** gli step 5 e 8 sono
   riclassificati da «standing behavior» a «enforced via hook».
2. **Given** la riclassificazione, **When** la si legge, **Then** documenta la sfumatura D↔N (l'hook
   segnala e induce; l'agente esegue il comando deterministico).
3. **Given** la nuova descrizione, **When** un agente apre uno step, **Then** non gli è richiesto di
   «ricordarsi» di re-indicizzare/smoke-testare come comportamento discrezionale.

### User Story 8 — L'ospite riceve la garanzia di freschezza via installer, con parità (P2, Should)
Eseguendo `sertor install rag`, un ospite riceve l'hook di freschezza (asset + voce `SessionEnd`
per-assistente) **nel formato nativo** del proprio assistente (Claude vs Copilot CLI), mai il formato
Claude su Copilot. L'hook è cablato alla capacità `rag`, così il suo lifecycle è indipendente dagli hook
di memoria/wiki. È il completamento della feature: senza distribuzione la capacità resta dogfood-only e
non è *done*.

**Independent Test**: `sertor install rag` deposita l'hook (asset + voce `SessionEnd`) nel contenitore
nativo di ciascun assistente; su Copilot il formato è quello nativo Copilot, non Claude; l'hook è legato
alla capacità `rag`.

**Acceptance**:
1. **Given** un ospite Claude e uno Copilot, **When** eseguo `sertor install rag`, **Then** l'hook di
   freschezza è depositato (asset + voce `SessionEnd` per-assistente) su ciascuno.
2. **Given** il target Copilot, **When** l'hook è depositato, **Then** è nel formato nativo Copilot, mai
   il formato Claude (parità — lezione FEAT-011/049).
3. **Given** l'hook depositato, **When** se ne osserva il wiring, **Then** è cablato alla capacità `rag`,
   indipendente dagli hook di memoria/wiki.

### User Story 9 — Lifecycle granulare e asset in sync (P2, Should)
Eseguendo `sertor upgrade`/`uninstall` per la capacità `rag`, l'hook di freschezza è aggiornato/rimosso
**senza disturbare** le voci degli altri hook (asset + voce settings), e un file hook dedicato rimasto
vuoto è ripulito. L'asset bundlato dell'installer e la copia dogfood `.claude/` dell'hook sono tenuti in
sync, verificato da un test di guardia (come per gli altri asset host).

**Independent Test**: `sertor upgrade`/`uninstall rag` aggiorna/rimuove solo l'hook di freschezza
(asset + voce) lasciando intatte le altre voci hook; un file hook svuotato è ripulito; un test di guardia
verifica la parità asset bundlato↔dogfood.

**Acceptance**:
1. **Given** `sertor upgrade`/`uninstall` per la capacità `rag`, **When** esegue, **Then** l'hook di
   freschezza è aggiornato/rimosso senza toccare le voci degli altri hook; un file hook dedicato rimasto
   vuoto è ripulito.
2. **Given** l'asset bundlato e la copia dogfood `.claude/` dell'hook, **When** si verificano, **Then**
   sono in sync, controllato da un test di guardia (come per gli altri asset host).
3. **Given** la reintroduzione di un drift tra bundlato e dogfood, **When** la guardia gira, **Then**
   segnala la divergenza.

## Edge Cases
- **Nulla cambiato a fine sessione**: re-index incondizionato ma **zero embedding** (incrementale del
  core); costo dominato da avvio processo + walk (US2, NFR-1).
- **Indice stantio o area `doctor` in fail/warn**: verdetto degradato → stato persistito + messaggio
  prominente a fine sessione; ripescato e indotto all'avvio successivo (US3/US4).
- **Corpus recuperato (degrado → sano)**: verdetto sano pulisce il marker degradato → nessun inducement
  perpetuo (US4, REQ-010; US3, REQ-015).
- **Errore interno dell'hook**: exit 0 sempre, errore segnalato ma non fatale; non blocca né
  sessione né `memory-capture` (US6).
- **Freschezza e `memory-capture` entrambi su `SessionEnd`**: isolamento reciproco — il fallimento di
  uno non impedisce all'altro (US6).
- **Guasto del filtro metadata `where`**: non coperto dall'hook (solo `doctor`) → buco dichiarato e
  promosso a E12; il rituale punto 8 dell'agente resta la rete (US5, R-4).
- **Server MCP stantio dopo re-index**: non interrogato direttamente dall'hook a fine sessione; mitigato
  dal reconnect indotto al `SessionStart` (US3); la rilevazione forte cross-processo resta debito
  `osservabilita`.
- **Marker non pulito a guarigione**: rischio di loop di re-index a ogni avvio → mitigato dal clear
  esplicito a verdetto sano (US4/US3, R-1).
- **Distribuzione su un solo target / drift bundlato↔dogfood**: la guardia di parità impedisce drift e
  leak di formato tra Claude e Copilot (US8/US9, R-5).
- **Host privo di server MCP / capacità `rag` non installata**: l'hook opera solo se la capacità `rag`
  è installata; dove non c'è, non si applica (confine dichiarato, non un crash) (NFR-4).

## Requirements *(mandatory)*

### Requisiti funzionali

**Re-index a fine sessione (rituale punto 5 → enforced)**
- **FR-001 (re-index event-driven via vehicle).** Quando una sessione termina, l'hook re-indicizza il
  corpus invocando il comando vehicle `sertor-rag index .`. *(REQ-001; CS-1)*
- **FR-002 (incondizionato, skip delegato al core).** L'hook invoca il re-index **incondizionatamente**
  e non implementa alcuna logica di change-detection propria; lo skip-quando-nulla-cambia è delegato
  all'incrementale del core (manifest + cache embeddings). *(REQ-002; CS-5)*
- **FR-003 (zero costo a corpus invariato).** Se nulla di indicizzato è cambiato dall'ultimo re-index,
  l'operazione completa **senza produrre nuovi embedding** (nessun costo oltre avvio processo + walk).
  *(REQ-003; CS-5; NFR-1)*
- **FR-004 (solo vehicle, Principio XI).** L'hook accede alle capacità di Sertor **solo** tramite la CLI
  vehicle (`sertor-rag`), mai importando o invocando `sertor_core` direttamente. *(REQ-004; RNF-1)*

**Verifica di salute a fine sessione (rituale punto 8 → enforced, scope = doctor)**
- **FR-005 (health via doctor).** Quando il re-index a fine sessione completa, l'hook verifica la salute
  del RAG invocando `sertor-rag doctor` sulle sue quattro aree (config/env, provider, indice, MCP).
  *(REQ-005; CS-2)*
- **FR-006 (verdetto sano/degradato).** L'hook deriva un verdetto (sano / degradato) dall'esito di
  `doctor` (pass/warn/fail per-area + exit code). *(REQ-006)*
- **FR-007 (smoke limitato a doctor, buco dichiarato).** La verifica di salute in-hook è limitata a
  `doctor` e **non** esegue una query metadata-filtrata (`where`) su `search_code`/`search_docs` (buco
  dichiarato; vedi Fuori ambito e tracciamento dello scope). *(REQ-007)*

**Persistenza dell'esito (fail-loud, tempo 1)**
- **FR-008 (persistenza su verdetto degradato).** Quando il verdetto di fine sessione è degradato
  (indice stantio o un'area `doctor` in fail/warn), l'hook persiste uno stato di salute RAG su file
  locale che sopravvive al confine di sessione. *(REQ-008; CS-2)*
- **FR-009 (messaggio prominente).** Quando il verdetto è degradato, l'hook emette anche un messaggio
  prominente a fine sessione. *(REQ-009)*
- **FR-010 (clear a verdetto sano).** Quando il verdetto di fine sessione è sano, l'hook registra lo
  stato sano e pulisce ogni marker degradato precedente, così un corpus recuperato non continua a
  innescare azione correttiva. *(REQ-010; NFR-6)*
- **FR-011 (contenuto dello stato).** Lo stato persistito riporta almeno il verdetto, un timestamp e la
  causa/area che ha fallito, in forma leggibile dal segnale d'avvio. *(REQ-011)*

**Segnale a inizio sessione e azione correttiva indotta (fail-loud, tempo 2)**
- **FR-012 (lettura allo start).** Quando una sessione inizia, il segnale di freschezza legge lo stato di
  salute RAG persistito. *(REQ-012)*
- **FR-013 (induzione su stato degradato).** Mentre lo stato persistito è degradato, il segnale d'avvio
  rende evidente il degrado all'agente e induce un'azione correttiva deterministica (re-index e/o
  reconnect del server MCP) **prima** che l'agente prosegua col lavoro di progetto. *(REQ-013; CS-2)*
- **FR-014 (solo segnala e induce, D↔N).** Il segnale d'avvio **solo** segnala e induce; non decide né
  compie giudizio da sé — il comando correttivo vehicle è eseguito dall'agente (confine D↔N). *(REQ-014;
  RNF-5)*
- **FR-015 (clear a guarigione).** Quando l'azione correttiva indotta ha riportato il verdetto a sano,
  il marker degradato è pulito così l'induzione non si ripete. *(REQ-015; NFR-6)*

**Coesistenza, non-fatalità, isolamento**
- **FR-016 (hook dedicato).** La capacità di freschezza è un hook dedicato (script proprio + propria
  voce `SessionEnd`), distinto da `memory-capture`; i due non sono fusi in un unico script. *(REQ-016)*
- **FR-017 (non-fatale, exit 0 sempre).** Se l'hook fallisce per qualunque motivo, non blocca né fa
  fallire il ciclo di vita della sessione: esce sempre 0 e segnala l'errore in modo non fatale (pattern
  di `wiki-pending-check` / `memory-capture`). *(REQ-017; NFR-2)*
- **FR-018 (isolamento reciproco).** Se l'hook di freschezza e `memory-capture` girano entrambi su
  `SessionEnd`, il fallimento di uno non impedisce all'altro di girare. *(REQ-018)*

**Reclassificazione della governance (CLAUDE.md)**
- **FR-019 (riclassificazione step 5/8).** Il rituale di step nel `CLAUDE.md` riclassifica gli step 5
  (re-index) e 8 (smoke) da «standing behavior (agente)» a «enforced via hook», documentando la
  sfumatura D↔N (l'hook segnala e induce; l'agente esegue il comando deterministico). *(REQ-019)*

**Distribuzione host-facing (installer)**
- **FR-020 (deposito via install).** Quando `sertor install rag` gira, l'installer deposita l'hook di
  freschezza (asset + voce settings `SessionEnd` per-assistente) sull'ospite. *(REQ-020; CS-4)*
- **FR-021 (formato nativo per target).** L'installer deposita l'hook nel formato nativo
  dell'assistente target (Claude vs Copilot CLI), mai il formato Claude su Copilot (parità —
  FEAT-011/049). *(REQ-021; CS-4)*
- **FR-022 (cablato alla capacità `rag`).** L'hook è cablato alla capacità `rag`, così il suo lifecycle
  install/upgrade/uninstall è granulare e indipendente dagli hook di memoria/wiki. *(REQ-022)*
- **FR-023 (upgrade/uninstall granulare).** Quando `sertor upgrade`/`uninstall` gira per la capacità
  `rag`, l'hook di freschezza è aggiornato/rimosso senza disturbare le voci degli altri hook (asset +
  voce settings), e un file hook dedicato rimasto vuoto è ripulito. *(REQ-023)*
- **FR-024 (guardia di sync bundlato↔dogfood).** L'asset bundlato dell'installer e la copia dogfood
  `.claude/` dell'hook sono tenuti in sync, verificato da un test di guardia (come per gli altri asset
  host). *(REQ-024; CS-4)*

### Requisiti non funzionali
- **RNF-1 (costo):** a fine sessione con nulla cambiato, **zero embedding** e overhead dominato da avvio
  processo + walk filesystem; l'incrementale del core è l'unico costo reale. *(NFR-1; FR-003)*
- **RNF-2 (non-bloccante):** l'esecuzione dell'hook non aggiunge attesa bloccante percepibile a
  chiusura/avvio; il lavoro pesante eventuale resta best-effort e interrompibile, mai fatale. *(NFR-2;
  FR-017)*
- **RNF-3 (privacy/locale):** l'hook opera solo su file e vehicle locali; nessun segreto nello stato
  persistito (riusa lo scrub già garantito dai vehicle); il file di stato è gitignored come gli altri
  artefatti runtime sotto `.sertor/`. *(NFR-3)*
- **RNF-4 (host-agnostico, Principio X):** lo script dell'hook non contiene assunzioni hardcoded su
  Sertor; funziona su un ospite qualsiasi che abbia installato la capacità `rag`. *(NFR-4)*
- **RNF-5 (determinismo, D↔N):** l'hook non invoca alcun LLM; il giudizio resta all'agente. *(NFR-5;
  FR-014)*
- **RNF-6 (idempotenza):** ri-eseguire il segnale di avvio a stato sano è un no-op; lo stato non oscilla
  né si auto-rigenera. *(NFR-6; FR-010/015)*

### Key Entities
- **Hook di freschezza RAG (harness deterministico)** — il nuovo attore non-LLM: a fine sessione
  re-indicizza via vehicle e verifica la salute via `doctor`, persistendone l'esito; a inizio sessione
  ripesca l'esito e induce la correzione se degradato. *Segnala e induce, non ragiona.*
- **Stato di salute RAG (file persistito)** — l'esito di salute scritto su file locale che attraversa il
  confine di sessione; contiene almeno verdetto (sano/degradato), timestamp, causa/area; gitignored sotto
  gli artefatti runtime; nome/formato esatti = design.
- **Vehicle orchestrati** — i comandi deterministici che l'hook richiama: `sertor-rag index .` (re-index
  incrementale, FEAT-009 + cache FEAT-019) e `sertor-rag doctor` (E12-FEAT-001, quattro aree). Esistono
  già (su `master`); l'hook li **usa**, non li estende.
- **Verdetto di salute** — sano / degradato, derivato dall'esito di `doctor` (pass/warn/fail per-area +
  exit code) e dalla staleness dell'indice; gate della persistenza e dell'induzione.
- **Voci hook per-assistente** — le registrazioni `SessionEnd` (fine sessione) e il punto di aggancio
  `SessionStart` (segnale d'avvio), nel formato nativo di ciascun assistente (Claude ↔ Copilot CLI),
  cablate alla capacità `rag`; coperte dalla guardia di sync/parità.
- **Step 5 e 8 del rituale (CLAUDE.md)** — i due passi meccanici riclassificati da «standing behavior»
  a «enforced via hook», con la nota D↔N.

## Success Criteria *(mandatory)*
- **CS-1 (freschezza enforced senza azione manuale):** in N sessioni che modificano file indicizzati,
  l'indice risulta aggiornato a fine sessione nel **100%** dei casi, senza alcuna azione manuale
  dell'agente. *(FR-001/002, US1)*
- **CS-2 (degrado evidente e indotto tra sessioni):** dopo una sessione che ha lasciato lo stato
  degradato, la sessione successiva rende il fatto evidente e induce l'azione correttiva **prima** che
  l'agente cominci; lo stato degradato non è mai silenziosamente ignorato. *(FR-008/011/012/013, US3/US4)*
- **CS-3 (non-fatale sempre):** l'esecuzione dell'hook non blocca né fa fallire chiusura/avvio in alcuno
  scenario (exit 0 sempre); un suo errore interno è segnalato ma non fatale. *(FR-017/018, US6)*
- **CS-4 (installabile con parità e isolamento):** un ospite che installa la capacità `rag` riceve l'hook
  nel formato nativo del proprio assistente e può disinstallarlo/aggiornarlo senza toccare gli altri hook;
  un test di guardia lo verifica (parità + isolamento + sync bundlato↔dogfood). *(FR-020..024, US8/US9)*
- **CS-5 (zero costo a corpus invariato):** quando nulla è cambiato dall'ultimo re-index, l'esecuzione a
  fine sessione non produce alcun ri-embedding (costo dominato dall'incrementale del core). *(FR-003, US2)*

## Assumptions
- **A-001 — `sertor-rag index` incrementale (FEAT-009 + cache FEAT-019, su `master`):** lo
  skip-quando-nulla-cambia è già nel core; l'hook può invocare il re-index incondizionatamente senza
  costo a corpus invariato. Prerequisito soddisfatto. *(FR-002/003)*
- **A-002 — `sertor-rag doctor` disponibile (E12-FEAT-001, su `master`):** è il passo di verifica
  salute dell'hook; senza, l'hook resterebbe cieco sull'esito. Prerequisito soddisfatto. *(FR-005/006)*
- **A-003 — Meccanismo installer per hook host riusabile:** asset + voce `SessionEnd`/`SessionStart`
  per-assistente + lifecycle install/upgrade/uninstall è collaudato per `memory-capture` /
  `sertor-rag-usage-check`; questa feature lo riusa. *(FR-020..023)*
- **A-004 — Seam di parità `AssistantProfile`:** traduce il formato hook nel nativo di ciascun
  assistente (Claude ↔ Copilot CLI); riusato, non reinventato. *(FR-021)*
- **A-005 — Eventi `SessionEnd` e `SessionStart` esposti dal client agente:** vero per Claude Code; per
  Copilot CLI il `SessionStart` è `type:"prompt"` e il `SessionEnd` esiste (cfr. FEAT-008 cattura
  Copilot). *(FR-012/020)*
- **A-006 — Staleness del server MCP dopo re-index reale finché non si riconnette (finding
  2026-06-23):** il reconnect indotto al `SessionStart` ne è la mitigazione lato rituale, non un fix del
  server (quello resta debito `osservabilita`). *(FR-013)*

### Fuori ambito (dichiarato)
- **Smoke col filtro metadata `where`** — l'hook si ferma a `sertor-rag doctor`; **non** esegue una query
  reale che eserciti il path del filtro metadata di `search_code`/`search_docs` (guasto storico
  2026-06-19). Resta affidato all'agente (rituale punto 8). → **promosso** a estensione futura di
  `doctor` (nuova FEAT nell'epica `usabilità` E12, owner di `doctor`).
- **Verifica diretta del server MCP vivo dall'hook** (client MCP standalone) — un hook a `SessionEnd` non
  può interrogare in modo affidabile il server in chiusura; la verifica «server fresco» è coperta
  indirettamente via il reconnect indotto al `SessionStart`. La rilevazione *forte* cross-processo dello
  staleness del server resta debito di `osservabilita`/server MCP.
- **Rilevazione del drift** («è cambiato qualcosa che andrebbe re-indicizzato») → epica `osservabilita`
  FEAT-012. Qui si **previene**, non si **osserva**.
- **Modifiche al motore di re-index o a `doctor`** — questa feature li **consuma** come vehicle, non li
  estende.
- **Il *come* di dettaglio** (nome/posizione/formato esatti del file di stato; voce hook a cui agganciare
  il segnale di avvio — se riusare un `SessionStart` esistente o aggiungerne una dedicata; punti precisi
  nell'installer e nella guardia): fase di **design/plan**.

> **Tracciamento dello scope.** Il **buco del filtro metadata** (smoke `where` non coperto dall'hook)
> non resta sepolto in `specs/`: va aperto come **nuova FEAT nell'epica `usabilità` (E12)**, owner di
> `doctor`, al `plan` (regola: gli Out-of-Scope reali si promuovono). La **staleness forte cross-processo
> del server MCP** resta debito dell'epica `osservabilita`/server MCP (già tracciato, finding 2026-06-23).
> La **drift-detection** è FEAT-012 (`osservabilita`). La feature non è *done* finché un ospite Claude
> **e** uno Copilot ricevono l'hook via `sertor install rag` (corollario «feature completa»): è in ambito
> (FR-020..024), non un debito rinviato.

### Forche di design — RISOLTE con l'utente (per `/speckit-plan`)
- **DA-1 — Trigger del re-index: RISOLTA.** Re-index **incondizionato** via il vehicle CLI
  `sertor-rag index .` (Principio XI, mai importare `sertor_core`); lo skip-quando-nulla-cambia è delegato
  all'incrementale del core (manifest SQLite FEAT-009 + cache embeddings FEAT-019). **Nessuna logica di
  delta-check nell'hook.** *(decisione utente; FR-001/002.)*
- **DA-2 — Fail-loud a due tempi: RISOLTA.** (a) `SessionEnd` re-indicizza + smoke + se degradato
  **persiste** uno stato di salute su file + messaggio; (b) `SessionStart` ripesca lo stato e, se
  degradato, **induce** un'azione correttiva forzata (re-index / reconnect server MCP) **prima** che
  l'agente proceda. Confine D↔N: l'hook segnala e induce, l'agente esegue (l'hook non ragiona, non chiama
  LLM). *(decisione utente; FR-008..015.)*
- **DA-3 — Scope dello smoke dentro l'hook: RISOLTA.** **Solo** `sertor-rag doctor` (quattro aree, exit-code
  gate). **Non** esercita il path del filtro metadata `where` di `search_code`/`search_docs` (guasto
  storico 2026-06-19) → **buco dichiarato**, promosso come estensione futura di `doctor` (nuova FEAT epica
  usabilità E12), non sepolto. *(decisione utente; FR-007.)*
- **DA-4 — Coesistenza con gli altri hook: RISOLTA.** Hook **separato e indipendente** (script dedicato +
  voce `SessionEnd` propria), accanto a `memory-capture`, **non-fatale** (exit 0 sempre), gestito
  **per-capacità** nell'installer (capability `rag`), lifecycle install/upgrade/uninstall granulare; parità
  Claude / Copilot CLI (formato hook nativo per ciascuno). *(decisione utente; FR-016/017/018/020..024.)*
- **DA-D-r1 (residuo, design) — Nome/posizione/formato del file di stato** (`.sertor/.rag-health`
  proposto): da fissare in `plan` (è un *come*).
- **DA-D-r2 (residuo, design) — Aggancio del segnale di avvio:** se riusare un hook `SessionStart`
  esistente (oggi c'è `wiki-session-start.ps1`) o aggiungere una voce dedicata, rispettando l'isolamento
  (FR-016) e l'esistente — da decidere in `plan`.
