# Feature Specification: Ciclo di vita dell'installer (upgrade e uninstall)

**Feature Branch**: `048-lifecycle-installer`

**Created**: 2026-06-17

**Status**: Draft

**Input**: Deriva da `requirements/sertor-cli/lifecycle-installer/requirements.md` (FEAT-008, epica
`sertor-cli`). Oggi l'installer copre solo il **primo install** (`sertor install wiki/rag`,
`sertor-flow install`): gli artefatti si creano se assenti, si saltano se presenti, si uniscono in
modo additivo. Mancano i due verbi del ciclo di vita: **aggiornare** un'installazione quando il
prodotto avanza, e **rimuovere** in modo affidabile ciò che è stato installato. Decomposizione chiusa
con 4 decisioni risolte (§10 dei requisiti): **Q1 (a)** wiki mai rimosso di default (flag
`--purge-wiki` + `--yes`); **Q2 (a)** obsoleti tracciati via diff a posteriori contro una lista
statica di path Sertor-owned dichiarata in codice, nessun manifest persistente; **Q3 (c)**
`sertor uninstall` rimuove tutto **e** supporta la forma per-capacità; **Q4 (a)** `sertor-flow
upgrade`/`uninstall` **in ambito** in questo ticket (simmetria piena).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rimuovere il runtime e gli asset standalone di una capacità (Priority: P1)

Un maintainer dell'ospite vuole smettere di usare una capacità di Sertor (per cambio di tecnologia,
abbandono del progetto, o riconfigurazione) e chiede di **rimuoverla**. Con un comando ottiene la
sparizione del runtime isolato e di tutti gli asset interamente di proprietà di Sertor, senza dover
conoscere la struttura interna degli artefatti né eseguire procedure manuali.

**Why this priority**: È il taglio minimo che consegna valore: rendere Sertor *rimovibile* in modo
ripetibile e sicuro. Il runtime isolato e gli asset standalone sono le rimozioni più usate e più sicure
(nessun rischio di toccare contenuto utente). Senza questa storia l'uninstall resta una procedura
manuale documentata, fragile e non host-agnostica.

**Independent Test**: Su un ospite di riferimento con la capacità installata, eseguire l'uninstall
della sola capacità e verificare che il runtime isolato e gli asset standalone Sertor-owned siano
spariti dal filesystem, e che il report elenchi ogni artefatto rimosso con il relativo esito.

**Acceptance Scenarios**:

1. **Given** un ospite con la capacità `rag` installata, **When** il maintainer esegue
   `sertor uninstall rag`, **Then** la directory di runtime isolata (`.sertor/`, con venv, env, store
   vettoriale, file SQLite, code graph, manifest di pacchetto e lockfile) è rimossa per intero e il
   report registra l'esito `removed` per quell'artefatto.
2. **Given** un ospite con asset standalone Sertor-owned, **When** il maintainer esegue l'uninstall di
   quella capacità, **Then** ogni asset standalone interamente di proprietà di Sertor è rimosso e ogni
   altro file resta intatto.
3. **Given** un ospite dove la capacità non è installata, **When** il maintainer esegue l'uninstall di
   quella capacità, **Then** il comando termina con successo (exit `0`) e riporta tutti gli artefatti
   come `skipped` (idempotenza).

---

### User Story 2 - Pulire i file condivisi senza toccare il contenuto utente (Priority: P1)

Sertor installa anche modificando file **condivisi** con l'utente: blocchi a marker dentro file di
istruzioni dell'assistente, voci di hook nei settings, linee in `.gitignore`, entry nei file di
configurazione del client MCP. Il maintainer che disinstalla vuole che spariscano **solo** le porzioni
di Sertor, lasciando il resto del file byte-per-byte invariato.

**Why this priority**: È l'invariante di sicurezza più delicato (R-01): un errore qui distrugge
contenuto utente. Senza questa storia l'uninstall lascia residui nei file condivisi oppure rischia di
troncarli; è ciò che oggi viene fatto a mano con una regex documentata, esattamente il punto più
soggetto a errore umano.

**Independent Test**: Su file condivisi che contengono sia porzioni Sertor sia paragrafi/entry
dell'utente, eseguire l'uninstall e verificare con un confronto byte-per-byte che solo le porzioni
Sertor siano sparite e il resto sia identico all'originale.

**Acceptance Scenarios**:

1. **Given** un file di istruzioni dell'assistente con un blocco a marker Sertor circondato da testo
   utente, **When** il maintainer disinstalla la capacità, **Then** solo il blocco delimitato dalla
   coppia di marker Sertor è rimosso e tutto il resto del file resta invariato.
2. **Given** un file di settings con voci di hook miste (Sertor e non-Sertor), **When** il maintainer
   disinstalla, **Then** solo le voci il cui comando referenzia uno script Sertor sono rimosse e le
   altre restano.
3. **Given** un `.gitignore` con le linee aggiunte dall'install RAG accanto a regole dell'utente,
   **When** il maintainer disinstalla, **Then** solo le linee Sertor (prefissate dalla directory di
   runtime) sono rimosse e le altre restano.
4. **Given** un file di configurazione del client MCP che contiene il server `sertor-rag` accanto ad
   altri server, **When** il maintainer disinstalla, **Then** solo la voce `sertor-rag` è rimossa e gli
   altri server sono preservati; se la voce `sertor-rag` era l'unica, il file viene rimosso.

---

### User Story 3 - De-registrare il server MCP dal client (Priority: P1)

Quando il RAG è stato installato registrando il server MCP presso il client (scope `local`, fuori dal
repository), il maintainer che disinstalla vuole che il server **non risulti più registrato** presso il
client, non solo che spariscano i file nel repo.

**Why this priority**: Senza questo passo l'uninstall lascia un riferimento a un server che non esiste
più, e il client tenta di avviarlo a vuoto. Completa la rimozione del RAG per gli ospiti che usano la
registrazione lato client.

**Independent Test**: Su un ospite dove il RAG è stato installato con registrazione lato client,
eseguire l'uninstall del RAG e verificare che la registrazione del server presso il client sia
rimossa; se il client non è disponibile, verificare che il comando fallisca con un messaggio azionabile
e un fallback manuale.

**Acceptance Scenarios**:

1. **Given** un RAG installato con registrazione del server presso il client (scope `local`), **When**
   il maintainer esegue l'uninstall del RAG, **Then** il server è de-registrato presso il client.
2. **Given** un RAG installato con registrazione lato client ma il client non è disponibile,
   **When** il maintainer esegue l'uninstall del RAG, **Then** il comando si ferma (fail-fast) con un
   messaggio azionabile e indica il comando manuale di fallback.

---

### User Story 4 - Aggiornare un'installazione quando il prodotto avanza (Priority: P2)

Il prodotto avanza su `master`: nuovi artefatti, asset standalone modificati, blocchi a marker con
contenuto cambiato, artefatti diventati obsoleti. Il maintainer dell'ospite vuole un comando di
**upgrade** che porti l'installazione all'allineamento con il bundle corrente: sovrascrive gli asset
cambiati, rinfresca i blocchi a marker, rimuove gli obsoleti — senza l'attuale workaround di forzare il
rebuild dell'installer e ri-eseguire un install che salta i file già presenti.

**Why this priority**: È la seconda metà del ciclo di vita. È P2 perché subordinata all'uninstall (le
primitive di rimozione e di confronto contenuto sono il fondamento) e perché il workaround attuale
copre già parzialmente i file assenti e i merge additivi; ciò che manca è l'aggiornamento dei file
presenti e la rimozione degli obsoleti.

**Independent Test**: Su un ospite con una versione installata, eseguire l'upgrade con un bundle che
differisce (asset cambiato + blocco a marker cambiato + un artefatto rimosso dal bundle) e verificare
che l'asset risulti sovrascritto, il blocco aggiornato, l'obsoleto rimosso, e che gli artefatti già
allineati siano lasciati invariati (`skipped`).

**Acceptance Scenarios**:

1. **Given** un asset standalone il cui contenuto nel bundle differisce dalla versione installata,
   **When** il maintainer esegue l'upgrade, **Then** il file installato è sovrascritto con la versione
   del bundle e l'esito registrato è `updated`.
2. **Given** un blocco a marker il cui contenuto nel bundle differisce dal contenuto dentro i marker
   sul disco, **When** il maintainer esegue l'upgrade, **Then** il contenuto dentro i marker è
   aggiornato e il contenuto fuori dai marker resta invariato.
3. **Given** un artefatto presente su disco sotto un path Sertor-owned ma assente dal bundle corrente,
   **When** il maintainer esegue l'upgrade, **Then** l'artefatto obsoleto è rimosso e l'esito è
   `removed`.
4. **Given** un artefatto già allineato al bundle, **When** il maintainer esegue l'upgrade, **Then**
   l'artefatto è lasciato invariato e l'esito è `skipped`.
5. **Given** un file su disco che **non** corrisponde a nessun path Sertor-owned, **When** l'upgrade lo
   valuterebbe come obsoleto, **Then** la rimozione è saltata, viene emesso un avviso e l'operazione
   continua.

---

### User Story 5 - Cambiare assistente target mantenendo solo gli artefatti giusti (Priority: P2)

Il maintainer cambia l'assistente target (es. da un assistente a un altro tra quelli supportati) e
ri-esegue l'upgrade indicando il nuovo target. Vuole che vengano aggiunti gli artefatti del nuovo
assistente e rimossi quelli del vecchio che non sono condivisi, senza toccare gli artefatti comuni a
entrambi.

**Why this priority**: È un caso d'uso concreto della tracciatura per diff a posteriori (Q2) e una
delle ragioni per cui il primo install da solo non basta. P2 perché è una raffinatezza dell'upgrade,
non il taglio minimo.

**Independent Test**: Su un ospite installato per un assistente, eseguire l'upgrade indicando un
assistente diverso e verificare che gli artefatti specifici del vecchio assistente siano rimossi,
quelli del nuovo aggiunti, e gli artefatti comuni invariati.

**Acceptance Scenarios**:

1. **Given** un ospite installato per l'assistente A, **When** il maintainer esegue l'upgrade
   indicando l'assistente B, **Then** gli artefatti specifici di A non condivisi sono rimossi, quelli
   specifici di B sono aggiunti e gli artefatti comuni a A e B restano invariati.

---

### User Story 6 - Proteggere il wiki ed esprimere consenso esplicito alla sua rimozione (Priority: P1)

Il `wiki/` può contenere documentazione reale prodotta dall'utente dopo l'installazione. Il maintainer
che disinstalla il wiki vuole, di default, che le pagine **restino**; solo se lo chiede esplicitamente,
e dopo aver visto quanto sta per perdere, il wiki viene cancellato.

**Why this priority**: È la protezione di un dato utente di alto valore (R-03, CS-9). Va consegnato col
primo taglio dell'uninstall perché altrimenti un `uninstall wiki` ingenuo rischia di distruggere lavoro
non riproducibile.

**Independent Test**: Eseguire l'uninstall del wiki senza flag e verificare che la directory del wiki e
le sue pagine restino, mentre gli altri artefatti del wiki sono rimossi; poi eseguirlo con il flag di
rimozione e verificare che richieda consenso e mostri il conteggio prima di cancellare.

**Acceptance Scenarios**:

1. **Given** un ospite con il wiki installato e pagine utente, **When** il maintainer esegue
   l'uninstall del wiki **senza** il flag di rimozione del wiki, **Then** la directory del wiki è
   preservata mentre ogni altro artefatto del wiki è rimosso.
2. **Given** lo stesso ospite, **When** il maintainer esegue l'uninstall del wiki **con** il flag di
   rimozione del wiki, **Then** prima di cancellare viene mostrato il numero di pagine e la dimensione
   approssimativa, ed è richiesta una conferma (interattiva o flag di conferma esplicito).
3. **Given** la richiesta di rimozione del wiki, **When** essa è combinata con la modalità di sola
   simulazione, **Then** la combinazione è rifiutata (il flag di rimozione del wiki non è combinabile
   con la sola simulazione).

---

### User Story 7 - Simulare l'operazione prima di eseguirla (dry-run) (Priority: P1)

Prima di un'operazione potenzialmente distruttiva, il maintainer vuole **vedere cosa accadrebbe** senza
modificare nulla: quali file verrebbero aggiornati, rimossi o lasciati invariati.

**Why this priority**: È l'invariante di sicurezza trasversale: nessuna operazione distruttiva senza
visibilità. Abilita un workflow "guarda, poi esegui" su entrambi i verbi del ciclo di vita.

**Independent Test**: Eseguire upgrade e uninstall in modalità di sola simulazione e verificare che lo
stato del filesystem sia immutato e che il report descriva ogni operazione che **sarebbe** stata
eseguita, con i conteggi proiettati.

**Acceptance Scenarios**:

1. **Given** un'operazione di upgrade, **When** la si esegue in sola simulazione, **Then** nessun file
   è scritto e il report riporta gli esiti proiettati (updated / removed / skipped).
2. **Given** un'operazione di uninstall, **When** la si esegue in sola simulazione, **Then** nessuna
   rimozione o modifica avviene e il report descrive cosa sarebbe stato rimosso.

---

### User Story 8 - Rimuovere o aggiornare tutto Sertor in un colpo solo (Priority: P2)

Il caso comune è togliere Sertor **interamente** dall'ospite. Il maintainer vuole un singolo
`sertor uninstall` (senza argomento di capacità) che rimuova tutte le capacità installate, e
analogamente potersi aggiornare. La forma per-capacità resta disponibile per rimozioni/aggiornamenti
parziali.

**Why this priority**: Ergonomia del caso d'uso più frequente (Q3 (c)). P2 perché si compone sopra le
operazioni per-capacità (US1–US7); una volta che quelle funzionano, l'aggregato è un orchestratore.

**Independent Test**: Su un ospite con più capacità installate, eseguire l'uninstall senza argomento e
verificare che equivalga alla rimozione di tutte le capacità installate (wiki, rag, governance), con un
unico report aggregato.

**Acceptance Scenarios**:

1. **Given** un ospite con wiki, rag e governance installati, **When** il maintainer esegue
   `sertor uninstall` senza argomento, **Then** tutte e tre le capacità installate sono rimosse,
   equivalentemente a `sertor uninstall wiki rag governance`.
2. **Given** lo stesso ospite, **When** il maintainer esegue `sertor uninstall rag`, **Then** è rimossa
   solo la capacità `rag` e le altre restano installate.

---

### User Story 9 - Gestire il ciclo di vita anche per la governance/SDLC (Priority: P2)

Il prodotto di governance/SDLC è un pacchetto separato (`sertor-flow`) operato da un proprio CLI. Il
maintainer vuole gli stessi verbi del ciclo di vita — upgrade e uninstall — anche per la governance,
con la stessa semantica e le stesse garanzie di `sertor`.

**Why this priority**: Simmetria piena richiesta (Q4 (a)): chiudere governance e RAG in un'unica
passata e far nascere subito le primitive condivise simmetriche, prevenendo la divergenza (R-05). P2
perché riusa le primitive definite dalle storie precedenti.

**Independent Test**: Su un ospite con la governance installata, eseguire l'upgrade e l'uninstall via
il CLI di governance e verificare la stessa semantica di `sertor` (aggiornamento asset, rinfresco
blocchi a marker, rimozione obsoleti; rimozione del solo blocco a marker SDLC dai file condivisi;
idempotenza; stesso schema di report).

**Acceptance Scenarios**:

1. **Given** un ospite con la governance installata, **When** il maintainer esegue l'upgrade della
   governance, **Then** gli asset di governance cambiati sono aggiornati, i blocchi a marker SDLC
   rinfrescati e gli artefatti obsoleti rimossi, con la stessa semantica di `sertor upgrade`.
2. **Given** un file condiviso con il blocco a marker SDLC e contenuto utente, **When** il maintainer
   disinstalla la governance, **Then** solo il blocco a marker SDLC è rimosso e il resto resta intatto.
3. **Given** un ospite privo di artefatti di governance, **When** il maintainer disinstalla la
   governance, **Then** il comando termina con successo (exit `0`) e riporta ogni artefatto come
   `skipped` (idempotenza).

---

### Edge Cases

- **File su disco sotto un path Sertor-owned ma sostituito da contenuto utente** → in upgrade un
  obsoleto va rimosso solo se appartiene davvero a Sertor; in caso di dubbio (path non riconosciuto)
  si salta con avviso (US4 scenario 5).
- **File condiviso senza i marker attesi** (utente li ha cancellati) → la rimozione del blocco è un
  no-op osservabile, non un errore.
- **`.gitignore`/settings con porzioni Sertor duplicate o riformattate dall'utente** → la rimozione
  deve essere robusta alla riformattazione e non eliminare linee/voci non-Sertor.
- **Errore di dominio su un singolo artefatto** → fail-fast no-rollback: l'artefatto è registrato come
  errore, nominato nel report, e gli artefatti già processati restano nel loro nuovo stato.
- **Uninstall del wiki con flag di rimozione ma senza conferma né flag di conferma** → la cancellazione
  non avviene; serve consenso esplicito.
- **Upgrade su ospite già allineato** → exit `0`, `0 updated`, `0 removed` (idempotenza).
- **Cambio di assistente con artefatti comuni a entrambi** → gli artefatti comuni non vanno né rimossi
  né duplicati.
- **De-registrazione MCP con client assente dal PATH** → fail-fast con messaggio azionabile e comando
  manuale di fallback.
- **`sertor uninstall governance`** → resta un **puntatore** a `sertor-flow uninstall` (come
  `sertor install governance`); la rimozione reale degli artefatti di governance avviene tramite il CLI
  di governance.
- **Il comando di ciclo di vita non avvia mai indicizzazione o operazioni RAG** (install ≠ run).
- **Dati del progetto (indice, file SQLite di osservabilità/memoria/cache)** sotto il runtime isolato:
  rimossi solo come parte della rimozione in blocco del runtime isolato della capacità RAG; la feature
  non rimuove dati del progetto al di fuori del runtime Sertor.

## Requirements *(mandatory)*

> **Capacità e tipi di artefatto (vocabolario, da §1 e §4 dei requisiti):**
> - **Capacità installabili via `sertor`:** `wiki`, `rag`, `governance` (quest'ultima un **puntatore**
>   al CLI di governance). Capacità via il CLI di governance: la governance/SDLC.
> - **Assistenti supportati:** tre target (`claude`, `copilot`, `copilot-cli`).
> - **Tipi di artefatto (tassonomia A/B/C/D dei requisiti):** **A** runtime isolato (la directory
>   `.sertor/` con venv, env, store, file SQLite, code graph, manifest e lockfile); **B** asset
>   standalone interamente Sertor-owned; **C** file condivisi editati con porzioni Sertor (blocchi a
>   marker, voci di settings, linee `.gitignore`); **D** registrazione del client MCP.

### Functional Requirements

**Gruppo A — Comuni a upgrade e uninstall**

- **FR-001**: Il sistema MUST accettare una modalità di **sola simulazione** (`--dry-run`) sia per
  `upgrade` sia per `uninstall`; quando attiva, MUST non modificare alcun file ed emettere un report che
  descrive ogni operazione che sarebbe stata eseguita.
- **FR-002**: Il sistema MUST accettare l'opzione di output machine-readable (`--json`) su `upgrade` e
  `uninstall`, emettendo un report conforme allo **stesso schema** del report di install, esteso con gli
  esiti `updated` e `removed`.
- **FR-003**: Il sistema MUST accettare la selezione dell'**assistente target** (`--assistant`, tra i
  tre supportati, con default `claude`) su `upgrade` e `uninstall`, per scegliere su quale insieme di
  artefatti specifici dell'assistente operare.
- **FR-004**: Se `upgrade` o `uninstall` incontra un errore di dominio su un singolo artefatto, il
  sistema MUST registrare l'esito di errore, nominare l'artefatto fallito nel report e fermarsi
  (fail-fast, no-rollback), lasciando gli artefatti già processati nel loro nuovo stato.
- **FR-005**: Il sistema MUST terminare con codice `0` quando l'operazione si completa senza errori
  (anche se ogni artefatto è risultato `skipped`), `1` su errore di dominio e `2` su uso errato.
- **FR-006**: Quando `upgrade` o `uninstall` si completa, il sistema MUST stampare un report sommario
  con l'esito per ogni artefatto e i conteggi aggregati (updated / removed / skipped / created /
  errori).
- **FR-007**: Al termine di ogni operazione il sistema MUST emettere un evento di osservabilità
  (operazione = `upgrade` o `uninstall`) con i conteggi e la capacità, coerente con il contratto di
  osservabilità esistente.

**Gruppo B — Upgrade**

- **FR-010**: Quando il maintainer esegue l'upgrade di una capacità, il sistema MUST confrontare il
  contenuto di ogni asset standalone (tipo B) del bundle con la versione installata; se differiscono,
  MUST sovrascrivere il file installato con la versione del bundle e registrare l'esito `updated`.
- **FR-011**: Quando il maintainer esegue l'upgrade di una capacità, il sistema MUST aggiornare il
  contenuto di ogni blocco a marker se il contenuto del bundle differisce da quello attualmente dentro i
  marker; il contenuto fuori dai marker MUST non essere modificato.
- **FR-012**: Quando il maintainer esegue l'upgrade e un artefatto presente nella versione precedente
  non è più presente nel bundle corrente (obsoleto), il sistema MUST rimuovere l'artefatto obsoleto dal
  filesystem dell'ospite e registrare l'esito `removed`.
- **FR-013**: Se un artefatto è marcato come obsoleto dall'upgrade ma il suo path non corrisponde ad
  alcun path Sertor-owned, il sistema MUST saltare la rimozione, emettere un avviso e continuare.
- **FR-014**: Quando il maintainer esegue l'upgrade e un artefatto è già allineato (contenuto del bundle
  uguale al contenuto installato), il sistema MUST lasciarlo invariato e registrare l'esito `skipped`.
- **FR-015**: In modalità di sola simulazione durante l'upgrade, il sistema MUST calcolare la differenza
  (updated / removed / skipped) senza scrivere su disco e riportare l'esito proiettato.
- **FR-016**: Quando il maintainer esegue l'upgrade del RAG cambiando l'assistente target rispetto a
  quello precedentemente installato, il sistema MUST aggiungere gli artefatti del nuovo assistente e
  rimuovere gli artefatti del vecchio non condivisi, senza toccare gli artefatti comuni a entrambi.
- **FR-017**: Il sistema MUST determinare gli artefatti obsoleti via **diff a posteriori** (Q2 (a)):
  MUST mantenere, in codice, una dichiarazione **statica** dei path Sertor-owned per capacità e
  assistente; un artefatto è obsoleto quando esiste su disco sotto un path Sertor-owned ed è assente dal
  bundle corrente. **NON** si introduce alcun manifest d'installazione persistente.

**Gruppo C — Uninstall: runtime, asset, file condivisi, MCP**

- **FR-020**: Quando il maintainer esegue l'uninstall di una capacità, il sistema MUST rimuovere ogni
  asset standalone (tipo B) installato da quella capacità che sia **interamente** Sertor-owned (non un
  file condiviso).
- **FR-021**: Quando il maintainer esegue l'uninstall di una capacità, il sistema MUST rimuovere **solo**
  i blocchi a marker Sertor (identificati dalla loro coppia di marker) da ciascun file condiviso (tipo
  C), lasciando il resto del file intatto byte-per-byte.
- **FR-022**: Quando il maintainer esegue l'uninstall, il sistema MUST rimuovere **solo** le voci
  Sertor-owned dal file di settings (le voci di hook il cui comando referenzia uno script Sertor),
  lasciando intatte tutte le altre voci.
- **FR-023**: Quando il maintainer esegue l'uninstall, il sistema MUST rimuovere **solo** le linee
  Sertor-owned dal `.gitignore` (le linee aggiunte dall'install RAG, prefissate dalla directory di
  runtime isolata), lasciando intatte tutte le altre linee.
- **FR-024**: Quando il maintainer esegue l'uninstall del RAG installato con registrazione del server
  MCP presso il client (scope `local`), il sistema MUST de-registrare il server `sertor-rag` presso il
  client (tipo D).
- **FR-025**: Quando il maintainer esegue l'uninstall del RAG con un assistente che usa un file di
  configurazione MCP, il sistema MUST rimuovere il file MCP **se e solo se** contiene unicamente la voce
  del server `sertor-rag`; se il file contiene altri server, MUST rimuovere solo la voce `sertor-rag` e
  preservare il resto.
- **FR-026**: Se l'uninstall di una capacità è eseguito su un target dove nessun artefatto di quella
  capacità è presente, il sistema MUST completarsi con successo (exit `0`) e riportare tutti gli
  artefatti come `skipped` (idempotenza).
- **FR-027**: Quando il maintainer esegue l'uninstall del wiki, il sistema MUST non rimuovere la
  directory del wiki a meno che non sia fornito il flag esplicito di rimozione del wiki (`--purge-wiki`,
  Q1 (a)); di default la directory del wiki è preservata mentre ogni altro artefatto del wiki è rimosso.
- **FR-028**: Dove è fornito il flag di rimozione del wiki all'uninstall del wiki, il sistema MUST
  mostrare il numero di pagine e la dimensione approssimativa della directory del wiki e richiedere una
  conferma interattiva o un flag di conferma esplicito (`--yes`) prima di cancellarla; il flag di
  rimozione del wiki MUST non essere combinabile con la sola simulazione.
- **FR-029**: In modalità di sola simulazione durante l'uninstall, il sistema MUST riportare cosa
  sarebbe rimosso senza eseguire alcuna cancellazione o modifica.
- **FR-030**: Quando il maintainer esegue l'uninstall del RAG, il sistema MUST rimuovere per intero il
  runtime isolato (tipo A: la directory `.sertor/` con venv, env, store vettoriale, file SQLite, code
  graph, manifest di pacchetto e lockfile).
- **FR-031**: Il sistema MUST non rimuovere mai alcun file o directory che Sertor non ha creato e che
  non è esplicitamente elencato come di proprietà della capacità installata.

**Gruppo D — Granularità del comando**

- **FR-032**: Il sistema MUST supportare l'uninstall **per-capacità** (`sertor uninstall <capacità>`) e
  l'uninstall **aggregato** (`sertor uninstall` senza argomento), dove l'aggregato equivale alla
  rimozione di tutte le capacità installate (`wiki rag governance`) (Q3 (c)).
- **FR-033**: Il sistema MUST limitare l'uninstall (e l'upgrade) all'istanza nella directory target
  corrente; nessuna operazione cross-utente o di sistema.

**Gruppo E — Ciclo di vita per la governance/SDLC (`sertor-flow`)**

- **FR-040**: Quando il maintainer esegue l'upgrade della governance, il CLI di governance MUST
  aggiornare gli artefatti di governance/SDLC con la stessa semantica di `sertor upgrade` (aggiornare
  gli asset standalone cambiati, rinfrescare i blocchi a marker, rimuovere gli obsoleti via il diff a
  posteriori di FR-017).
- **FR-041**: Quando il maintainer esegue l'uninstall della governance, il CLI di governance MUST
  rimuovere ogni artefatto di governance che ha installato, applicando lo stesso trattamento per tipi
  A/B/C/D di `sertor uninstall`, e MUST rimuovere **solo** il blocco a marker SDLC dai file condivisi,
  lasciando intatto il resto.
- **FR-042**: I comandi di upgrade/uninstall della governance MUST accettare gli stessi flag delle
  controparti di `sertor` (`--assistant`, `--dry-run`, `--json`) ed emettere report conformi allo stesso
  schema con gli esiti `updated`/`removed`.
- **FR-043**: Le primitive di ciclo di vita — confronto del contenuto, rimozione di asset standalone,
  rimozione di blocco a marker, rimozione di linee, de-registrazione del client MCP — MUST essere
  implementate **una sola volta** in un toolkit condiviso e consumate sia da `sertor` sia dal CLI di
  governance, così i due pacchetti restano simmetrici e non possono divergere (mitiga R-05).
- **FR-044**: Se l'uninstall della governance è eseguito su un target privo di artefatti di governance,
  il CLI MUST completarsi con successo (exit `0`) e riportare ogni artefatto come `skipped`
  (idempotenza), coerentemente con FR-026.
- **FR-045**: Né l'upgrade né l'uninstall della governance MUST introdurre una dipendenza del pacchetto
  di governance dalla libreria di retrieval o dal pacchetto `sertor`; il codice condiviso vive solo nel
  toolkit d'installazione condiviso.

**Gruppo F — Invarianti preservati (non funzionali, espressi come requisiti)**

- **FR-050** (Non-distruttività): Il sistema MUST non rimuovere o sovrascrivere contenuto utente al di
  fuori degli artefatti esplicitamente gestiti; un file con contenuto non-Sertor in una posizione
  Sertor-owned sopravvive invariato tranne per le porzioni a marker.
- **FR-051** (Install ≠ run): L'upgrade e l'uninstall MUST non avviare mai indicizzazione o operazioni
  RAG.
- **FR-052** (Host-agnosticità): Upgrade e uninstall MUST funzionare su qualsiasi repo ospite
  indipendentemente da linguaggio/tecnologia, senza presupporre prerequisiti oltre quelli necessari a
  invocare Sertor stesso (Principio X).
- **FR-053** (Sicurezza — segreti): L'upgrade MUST non sovrascrivere mai i valori del file di
  ambiente esistente (solo le chiavi assenti vengono aggiunte, coerentemente con la strategia additiva
  attuale); l'uninstall del RAG rimuove il runtime isolato incluso il file di ambiente; il report MUST
  non includere il contenuto dei file rimossi.

### Key Entities

- **Capacità installabile**: l'unità di installazione/rimozione (`wiki`, `rag`, `governance`); la
  governance è un puntatore al pacchetto di governance/SDLC. L'upgrade/uninstall opera per capacità o in
  aggregato.
- **Artefatto**: un singolo elemento gestito dall'installer, con un tipo (A runtime isolato / B asset
  standalone / C file condiviso / D registrazione client) e un esito d'operazione.
- **Esito d'operazione**: lo stato registrato per ogni artefatto, esteso dal ciclo di vita: oltre a
  `created` / `skipped` / `merged` / `block` / `error`, i nuovi `updated` e `removed`.
- **Path Sertor-owned**: l'insieme statico, dichiarato in codice per capacità e assistente, dei percorsi
  che Sertor possiede; base del diff a posteriori per identificare gli obsoleti e per garantire che
  nulla di non-Sertor venga rimosso.
- **Blocco a marker Sertor**: la porzione di un file condiviso delimitata da una coppia di marker propri
  (rituale wiki, uso RAG, rituale SDLC); l'unica parte rimovibile/aggiornabile di quel file.
- **Report del ciclo di vita**: il documento (umano e machine-readable) che riporta per ogni artefatto
  l'esito e i conteggi aggregati, conforme allo stesso schema del report di install esteso con
  `updated`/`removed`.
- **Bundle corrente**: l'insieme degli artefatti che la versione installata del prodotto sa produrre; è
  la fonte di verità rispetto a cui upgrade confronta il disco (aggiornare/rimuovere/saltare).
- **Toolkit d'installazione condiviso**: la sede unica delle primitive di ciclo di vita, consumata da
  `sertor` e dal CLI di governance per garantire simmetria e impedire divergenza.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (Rimozione completa)**: dopo l'uninstall di una capacità su un ospite di riferimento, la
  ricerca di ogni file/entry di quella capacità produce **0** artefatti residui tracciabili.
- **SC-002 (Non distruttività)**: in **0** esecuzioni di uninstall vengono eliminati o troncati file
  dell'utente che non sono interamente Sertor-owned (es. file di istruzioni dell'assistente,
  `.gitignore`, file MCP con server non-Sertor).
- **SC-003 (Upgrade esplicito)**: dopo l'upgrade di una capacità, gli asset standalone aggiornati nel
  bundle risultano sovrascritti sul disco; il conteggio `updated` nel report è > 0 **se e solo se** il
  bundle differisce dalla versione installata.
- **SC-004 (Obsoleti rimossi)**: dopo l'upgrade con cambio di assistente, i file dell'assistente
  dismesso non condivisi vengono rimossi; in **0** casi vengono rimossi file dell'utente non creati da
  Sertor.
- **SC-005 (Idempotenza)**: ri-eseguire l'uninstall su un ospite già pulito termina con exit `0` e
  **0 errori**; ri-eseguire l'upgrade su un ospite già allineato termina con exit `0` e **0 updated**.
- **SC-006 (Sola simulazione)**: eseguire in modalità di sola simulazione **non** modifica lo stato del
  filesystem (0 byte cambiati); il report descrive ogni operazione che sarebbe stata eseguita.
- **SC-007 (Osservabilità)**: il report di upgrade/uninstall riporta per ogni artefatto l'esito
  effettivo (updated / removed / skipped / created / error) e un conteggio sommario, nello **stesso
  formato** del report di install.
- **SC-008 (Multi-assistente)**: l'uninstall rimuove correttamente gli artefatti per **tutti e tre** i
  target assistenti supportati.
- **SC-009 (Dati utente protetti)**: il wiki **non** viene rimosso in assenza di consenso esplicito; un
  messaggio informativo specifica quante pagine e quanti byte contiene.
- **SC-010 (Simmetria sertor / governance)**: per ogni primitiva di ciclo di vita (confronto contenuto,
  rimozione standalone/marker/linee, de-registrazione MCP) esiste **un'unica** implementazione condivisa
  consumata da entrambi i CLI; **0** divergenze d'implementazione tra `sertor` e governance.
- **SC-011 (Performance)**: l'uninstall su un ospite tipico (< 100 artefatti) si completa in **< 10 s**
  su filesystem locale (non è un'operazione di rete).

## Assumptions

- **Stato di partenza dell'installer (ground truth dai requisiti §1):** l'installer odierno copre solo
  il primo install (creazione condizionale + merge additivi via `execute_plan` fail-fast no-rollback);
  non esiste alcun meccanismo di rimozione inversa o di sovrascrittura controllata. Le primitive del
  ciclo di vita sono ciò che questa feature introduce.
- **Tracciatura obsoleti = diff a posteriori (Q2 (a)):** la lista dei path Sertor-owned è dichiarata
  staticamente in codice (per capacità e assistente), già implicita nei plan-builder; **nessun manifest
  persistente**. Assunto: questa lista è piccola e si mantiene aggiornata insieme ai plan-builder.
- **Wiki protetto di default (Q1 (a)):** `wiki/` non viene rimosso senza `--purge-wiki`; il flag
  richiede conferma o `--yes` e non è combinabile con la sola simulazione.
- **Granularità (Q3 (c)):** `sertor uninstall` senza argomento = tutto-in-uno; la forma per-capacità per
  rimozioni parziali. Coerente con `sertor install <capacità>`.
- **Governance in ambito (Q4 (a)):** i comandi del ciclo di vita per la governance/SDLC sono inclusi in
  questo ticket, simmetrici a `sertor`, riusando le primitive del toolkit condiviso; resta invariante
  che il pacchetto di governance **non** dipenda dalla libreria di retrieval o da `sertor`.
- **`sertor uninstall/upgrade governance` = puntatore:** come `sertor install governance`, la
  rimozione/aggiornamento reale degli artefatti di governance avviene tramite il CLI di governance; il
  comando in `sertor` resta un puntatore (nessuna dipendenza tra pacchetti).
- **Identificazione tipo C senza store aggiuntivo:** le porzioni Sertor nei file condivisi si
  riconoscono dalle marker string note, dal prefisso delle linee `.gitignore` (directory di runtime) e
  dalla referenza a script Sertor nelle voci di settings; non serve un ulteriore store di tracciatura.
- **Dati del progetto vs Sertor:** la semantica è "togli Sertor dal progetto, non i dati del progetto";
  i dati che vivono **dentro** il runtime isolato della capacità RAG (indice, file SQLite) cadono con la
  rimozione in blocco di quel runtime, ma la feature non rimuove dati del progetto al di fuori del
  perimetro Sertor.
- **Schema di report unico:** si estende lo schema di report dell'install con gli esiti `updated` e
  `removed`; non si introduce un secondo schema.
- **Fuori ambito (capacità future con casa durevole):** rollback automatico a una versione precedente
  del bundle e gestione versioni (FEAT-006); upgrade del runtime Python isolato (oggi gestito dal merge
  idempotente delle dipendenze); upgrade/uninstall del corpus dati al di fuori del runtime isolato;
  distribuzione dei nuovi comandi `upgrade`/`uninstall` sugli ospiti già installati (bootstrap del
  bootstrap: l'ospite deve aggiornare il pacchetto per ottenerli); uninstall cross-utente o di sistema;
  GUI/wizard interattivo; upgrade su eventi/CI automatica.
- **Domande di design ancora aperte (→ `/speckit-plan`, non bloccano la spec):** la forma concreta delle
  nuove primitive nel toolkit (nuove `WriteStrategy`/`ArtifactKind` "inverse" vs handler dedicati);
  dove derivare i plan di upgrade/uninstall dai plan-builder esistenti come unica fonte di verità degli
  artefatti; la forma esatta della dichiarazione statica dei path Sertor-owned; il comportamento esatto
  della conferma interattiva vs `--yes` nei contesti non interattivi. Sono decisioni di *come*, non
  ambiguità di *cosa/perché*.
