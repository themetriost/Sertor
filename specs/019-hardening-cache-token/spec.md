# Feature Specification: Cache embeddings per content-hash + token nei log

**Feature Branch**: `019-hardening-cache-token`

**Created**: 2026-06-14

**Status**: Draft

**Input**: User description: "Hardening produzione del retrieval — gruppo C (costo dell'indicizzazione), i due Should del requirement `requirements/sertor-core/hardening-produzione/requirements.md`: REQ-H4 (cache embeddings per content-hash: ri-indicizzare un corpus invariato non ri-embedda i chunk identici) + REQ-H5 (token nei log: l'evento di embedding logga `usage.total_tokens` quando disponibile, come segnale di costo). Obiettivo OB-3: re-indicizzare un corpus invariato non ri-paga l'embedding. Vincoli: dietro manopola `Settings`, default retro-compatibili, testabile senza rete, contratto invariato. Fuori ambito: i Could (H7/H8/H9/H10/H11) e il refresh incrementale FEAT-009."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ri-indicizzare un corpus invariato non ri-paga l'embedding (Priority: P1)

Chi gestisce un indice (operatore della CLI `sertor-rag`, dogfood di Sertor, ospite installato) ricostruisce
periodicamente l'indice del proprio corpus per restare allineato alla realtà del progetto. Oggi ogni rebuild
re-embedda **tutti** i chunk anche se la maggior parte del corpus non è cambiata: con un provider a pagamento
(Azure `text-embedding-3-*`) questo significa ripagare per intero il costo di embedding a ogni ricostruzione,
anche quando la modifica ha toccato pochi file. Con la cache abilitata, un chunk il cui **contenuto** è
identico a uno già embeddato in passato viene servito dalla cache invece di chiamare il provider, così il
secondo rebuild di un corpus invariato non emette alcuna chiamata di embedding.

**Why this priority**: È il valore portante della feature e l'unico dei due Should che incide direttamente sul
costo operativo (obiettivo OB-3 dell'audit). Mitiga, nell'immediato e senza refresh incrementale (FEAT-009),
il vincolo di costo che oggi scoraggia i re-index frequenti — re-index che il rituale di step rende ricorrenti.

**Independent Test**: indicizzare un corpus con un embedder fittizio che conta le chiamate, poi ri-indicizzare
lo stesso corpus invariato con la cache attiva e verificare che la seconda esecuzione non produca nuove
chiamate di embedding (zero chunk ri-embeddati) e che l'indice risultante sia equivalente. Interamente
offline, senza rete.

**Acceptance Scenarios**:

1. **Given** un corpus indicizzato con la cache abilitata, **When** lo si re-indicizza invariato, **Then** nessun chunk viene ri-embeddato (tutti serviti dalla cache) e l'indice prodotto è equivalente al precedente.
2. **Given** un corpus indicizzato con la cache abilitata, **When** si modifica il contenuto di alcuni chunk e si re-indicizza, **Then** vengono ri-embeddati **solo** i chunk il cui contenuto è cambiato (o nuovo), mentre i chunk invariati arrivano dalla cache.
3. **Given** la cache **disabilitata** (default), **When** si re-indicizza un corpus invariato, **Then** il comportamento è identico a quello odierno (rebuild full, tutti i chunk ri-embeddati): nessuna regressione.
4. **Given** un corpus indicizzato con un provider/modello di embedding, **When** si re-indicizza con un provider o modello **diverso** (dimensione/spazio vettoriale diverso), **Then** la cache **non** serve gli embedding del provider precedente: i chunk vengono ri-embeddati col nuovo modello.
5. **Given** una voce di cache mancante, illeggibile o corrotta per un chunk, **When** si indicizza, **Then** quel chunk viene embeddato normalmente (la cache degrada in modo non-fatale, mai un errore d'indicizzazione).

---

### User Story 2 - Vedere quanto costa un'indicizzazione (token nei log) (Priority: P2)

Chi osserva un'operazione di indicizzazione (via `-v`/`--log-json` della CLI, o leggendo i log strutturati)
oggi non ha alcun segnale del costo consumato: l'evento di embedding non riporta i token. Quando il provider
restituisce il conteggio token (Azure espone `usage.total_tokens` nella risposta), l'evento di log
dell'embedding deve includerlo, così l'operatore può stimare e confrontare il costo delle indicizzazioni e,
insieme alla cache (US1), **misurare** il risparmio (cache hit → token non consumati).

**Why this priority**: È il segnale di costo #1 oggi assente (REQ-H5/D3), additivo e a basso rischio. Dipende
concettualmente dalla US1 perché è ciò che rende il risparmio della cache **osservabile/misurabile** (SC-3),
ma ha valore anche da solo e si implementa indipendentemente.

**Independent Test**: eseguire un'indicizzazione con un embedder fittizio che riporta un conteggio token noto
e verificare che l'evento di log dell'embedding contenga quel conteggio; con un provider che non riporta token
verificare che l'evento sia comunque emesso senza il campo (nessun errore). Offline.

**Acceptance Scenarios**:

1. **Given** un provider che riporta il conteggio token, **When** si indicizza, **Then** l'evento di log dell'embedding include il numero di token consumati.
2. **Given** un provider che non riporta token, **When** si indicizza, **Then** l'evento di log è emesso regolarmente senza il campo token (assenza, non zero fittizio) e senza errori.
3. **Given** la cache abilitata che serve dei chunk dalla cache, **When** si indicizza, **Then** l'osservabilità distingue i chunk serviti dalla cache da quelli effettivamente embeddati (rendendo misurabile SC-3 — i cache-hit non consumano token).

---

### Edge Cases

- **Due chunk con contenuto testuale identico** (stesso testo in file diversi): producono lo stesso embedding per uno stesso modello → la chiave di cache è il contenuto (più il modello), quindi il secondo è un cache-hit. Comportamento atteso e corretto.
- **Cambio di chunking** che altera il testo di un chunk pur lasciando il file "uguale a occhio": il contenuto del chunk cambia → cache miss → ri-embedding (corretto: si embedda ciò che cambia).
- **Cache che cresce indefinitamente** su corpora molto volatili: in assenza di refresh incrementale, voci non più riferite possono accumularsi → vedi Assumptions (nessuna eviction sofisticata nell'MVP; la cache resta sicura da cancellare).
- **Concorrenza**: due indicizzazioni simultanee sullo stesso corpus → fuori ambito (l'indicizzazione è single-writer, come oggi).
- **Disabilitazione a caldo**: passare da cache-on a cache-off tra due rebuild deve degradare al comportamento odierno senza richiedere pulizia manuale.

## Requirements *(mandatory)*

### Functional Requirements

#### Gruppo A — Cache embeddings per content-hash (REQ-H4, US1)

- **FR-001**: Dove la cache di embedding è abilitata, il sistema MUST evitare di ri-embeddare un chunk il cui contenuto è identico a uno già embeddato in una indicizzazione precedente, servendo l'embedding dalla cache.
- **FR-002**: La cache MUST essere indirizzata da una chiave derivata dal **contenuto** del chunk e dall'identità del **modello/provider** di embedding, in modo che embedding di modelli diversi (spazi vettoriali diversi) non si mescolino né si servano a vicenda.
- **FR-003**: La cache MUST persistere tra esecuzioni di indicizzazione distinte (un rebuild successivo beneficia degli embedding calcolati in un rebuild precedente), senza dipendere dal contenuto vivo dell'indice vettoriale.
- **FR-004**: Quando una voce di cache è assente, illeggibile o non valida per un chunk, il sistema MUST embeddare quel chunk normalmente; un guasto della cache MUST degradare in modo non-fatale (warning, mai errore d'indicizzazione).
- **FR-005**: Quando la cache è abilitata e produce embedding, l'indice risultante MUST essere equivalente a quello prodotto senza cache per lo stesso corpus e modello (la cache non cambia il risultato, solo il costo).
- **FR-006**: Il sistema MUST aggiornare la cache con gli embedding appena calcolati per i chunk in cache-miss, così da renderli disponibili al rebuild successivo.
- **FR-007**: La cache MUST essere controllata da una manopola di configurazione centralizzata, con default **disabilitato** (comportamento odierno = rebuild full); abilitarla è una scelta esplicita dell'operatore.

#### Gruppo B — Token nei log (REQ-H5, US2)

- **FR-008**: Quando il provider di embedding restituisce un conteggio token, l'evento di log dell'embedding MUST includere quel conteggio come segnale di costo.
- **FR-009**: Quando il provider non restituisce un conteggio token, l'evento di log MUST essere emesso comunque, semplicemente senza il campo token (assenza esplicita, non un valore fittizio), senza errori.
- **FR-010**: L'osservabilità dell'indicizzazione MUST permettere di distinguere i chunk serviti dalla cache da quelli effettivamente embeddati, così che il risparmio (cache-hit → token non consumati) sia misurabile.

#### Vincoli trasversali (NFR del requirement padre)

- **FR-011**: Le aggiunte MUST essere additive: il contratto dei risultati di retrieval e delle porte esistenti non cambia in modo da rompere i consumer (CLI, server MCP, libreria).
- **FR-012**: Tutto il comportamento MUST essere verificabile senza rete (embedder fittizio per cache hit/miss e per il conteggio token), coerentemente con la CI offline del progetto.
- **FR-013**: Con la cache disabilitata e nessun conteggio token disponibile, il comportamento osservabile MUST essere identico a quello odierno (nessuna regressione di default).

### Key Entities *(include if feature involves data)*

- **Voce di cache embedding**: associa una chiave (contenuto del chunk + identità del modello/provider) all'embedding calcolato; persistente, leggibile/scrivibile durante l'indicizzazione, sicura da cancellare (la sua perdita causa al più un ri-embedding).
- **Evento di log di embedding**: il record strutturato emesso durante l'indicizzazione; esteso con il conteggio token (quando disponibile) e con il segnale che distingue cache-hit da embedding effettivi.
- **Manopola di configurazione della cache**: l'impostazione centralizzata che abilita/disabilita la cache (default disabilitata) e ne individua la sede di persistenza.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Re-indicizzare un corpus invariato con la cache abilitata produce **zero** nuove chiamate di embedding (100% cache-hit), verificabile contando le chiamate verso il provider.
- **SC-002**: Modificando una frazione dei chunk e re-indicizzando, il numero di chunk ri-embeddati è pari ai soli chunk con contenuto cambiato o nuovo (nessun ri-embedding dei chunk invariati).
- **SC-003**: Con la cache disabilitata (default), il numero di chunk embeddati a ogni rebuild è invariato rispetto al comportamento odierno (nessuna regressione).
- **SC-004**: Cambiando provider/modello di embedding, nessun embedding del modello precedente viene servito dalla cache (zero cache-hit cross-modello).
- **SC-005**: Quando il provider riporta i token, l'evento di log dell'embedding contiene il conteggio token in almeno il 100% degli eventi in cui il dato è disponibile; quando non lo riporta, il 100% degli eventi è comunque emesso senza errori.
- **SC-006**: A partire dai log di due rebuild consecutivi (primo a freddo, secondo a cache calda su corpus invariato), è possibile quantificare il risparmio in token tra le due esecuzioni.

## Assumptions

- **Default cache disabilitata**: coerente con NFR-1 del requirement padre ("default retro-compatibili"). L'abilitazione è una scelta esplicita; il dogfood di Sertor potrà abilitarla dopo il merge.
- **Nessuna eviction sofisticata nell'MVP**: la cache può crescere; resta sicura da cancellare manualmente (la perdita causa solo ri-embedding). Politiche di eviction/scadenza sono fuori ambito (eventuale follow-up).
- **Chiave sul contenuto del chunk effettivamente embeddato**: l'unità di cache è il chunk come oggi prodotto dal chunker; un cambio di chunking che altera il testo è correttamente un cache-miss.
- **Conteggio token "best effort"**: dipende da ciò che il provider espone (Azure espone `usage.total_tokens`; provider locali come Ollama potrebbero non esporlo) — l'assenza è gestita, non è un errore.
- **Single-writer**: l'indicizzazione resta un'operazione a scrittore singolo per corpus; nessuna garanzia di concorrenza sulla cache.
- **Refresh incrementale fuori ambito**: rilevare *quali file* sono cambiati per evitare di ri-chunkare/ri-leggere resta FEAT-009; qui la cache agisce a valle, sul passo di embedding, anche se il corpus viene riletto e ri-chunkato per intero.
- **Could fuori ambito**: query transformation (H7), filtro metadata esteso (H8), tracing/metriche (H9/H10), contextual retrieval (H11) non fanno parte di questa feature.
- **Prototipo congelato**: nessuna modifica a `prototype/`.
