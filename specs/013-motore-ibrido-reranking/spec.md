# Feature Specification: Motore RAG ibrido + reranking

**Feature Branch**: `013-motore-ibrido-reranking`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Motore RAG ibrido + reranking (FEAT-004 dell'epica sertor-core). Fonte EARS completa: requirements/sertor-core/motore-ibrido/requirements.md (domande D1..D4 tutte risolte — vedi §10). Punti chiave: secondo motore RAG del core che fonde BM25 (lessicale) + retrieval vettoriale via RRF, con reranking opzionale; selettore SERTOR_ENGINE con default hybrid e degradazione a vettoriale + warning strutturato su indici pre-ibrido (REQ-034); core store-agnostico (percorso nativo per-store = Could); latenza qualitativa con misura empirica nel dogfood; ground-truth set 5-6 coppie query→file-atteso nel design (≥10 in implementazione) per dimostrare il miglioramento di search_code su query architetturali e chiudere i 2 xfail."

> **Fonte a monte:** `requirements/sertor-core/motore-ibrido/requirements.md` (EARS, rev. 2026-06-11,
> D1..D4 + DA-1b risolte). I requisiti funzionali qui sotto mappano 1:1 sui REQ EARS
> (riferimento `REQ-NNN` accanto a ogni FR).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ricerca ibrida: query lessicali che trovano il bersaglio (Priority: P1)

Un agente LLM (via server MCP o CLI) cerca nel corpus un **nome esatto di simbolo** — ad esempio
`EmbeddingProvider`, `IndexNotFoundError`, `collection_name` — o un termine raro/di configurazione.
Oggi il retrieval solo-vettoriale spesso "allontana" la corrispondenza lessicale esatta; con il
motore ibrido la ricerca interroga **due vie in parallelo** (similarità semantica + rilevanza
lessicale) e fonde i due ranking in un'unica lista ordinata, così la corrispondenza esatta risale
in cima senza perdere la capacità semantica sulle query in linguaggio naturale.

Al momento dell'indicizzazione, accanto all'indice vettoriale viene costruito un **indice
lessicale** sugli stessi chunk, con un trattamento del testo che preserva identificatori,
sotto-token degli snake_case e termini rari (è il differenziatore sulle query a simbolo).

**Why this priority**: è il cuore della feature e il valore dimostrato dal prototipo (MRR da 0.13
a 0.94 sui simboli esatti con embedder debole): senza fusione ibrida non esiste il motore. Da sola
costituisce un MVP: indicizza, interroga, restituisce risultati migliori sulle query lessicali.

**Independent Test**: indicizzare un piccolo corpus con il motore ibrido, lanciare una query con
un identificatore esatto presente in un solo file e verificare che quel file sia in cima ai
risultati; lanciare una query NL e verificare che i risultati semantici restino pertinenti.
Eseguibile interamente con provider e store mock, senza rete.

**Acceptance Scenarios**:

1. **Given** un corpus indicizzato con il motore ibrido (indice vettoriale + lessicale costruiti
   insieme), **When** l'utente cerca un nome esatto di simbolo presente nel corpus, **Then** il
   file/chunk che definisce quel simbolo compare nei primi risultati della lista fusa.
2. **Given** lo stesso corpus, **When** l'utente pone una query in linguaggio naturale
   (architetturale/concettuale), **Then** i risultati restano pertinenti almeno quanto il motore
   baseline (la componente semantica non viene penalizzata dalla fusione).
3. **Given** due ranking parziali (vettoriale e lessicale) con sovrapposizione parziale,
   **When** avviene la fusione, **Then** la lista risultante è deterministica: a parità di input
   l'ordine è sempre lo stesso e i pareggi sono risolti in modo consistente.
4. **Given** un corpus re-indicizzato da zero, **When** l'indicizzazione termina, **Then** indice
   vettoriale e lessicale risultano coerenti (stesso insieme di chunk, stesso namespace di corpus
   e provider).

---

### User Story 2 - Selezione del motore e retro-compatibilità (Priority: P2)

L'owner/maintainer sceglie il motore di retrieval **dalla sola configurazione** (manopola
`SERTOR_ENGINE`): `hybrid` è il default ("il motore migliore è il default"), `baseline` resta
selezionabile e produce risultati identici a oggi. I consumatori esistenti (facade di retrieval,
server MCP, CLI) **beneficiano dell'ibrido senza alcuna modifica** alla loro superficie.

Caso critico: un corpus indicizzato **prima** di questa feature non ha l'indice lessicale. Con il
default `hybrid`, la query **non fallisce**: degrada a retrieval solo-vettoriale (risultati
equivalenti al baseline) emettendo un **warning strutturato** che dichiara l'indice lessicale
mancante e indica che un re-index abilita l'ibrido.

**Why this priority**: il default `hybrid` (decisione utente D1) rende la degradazione onesta la
condizione di sicurezza dell'intero rollout: senza di essa ogni indice esistente si romperebbe al
primo aggiornamento. È ciò che rende la feature adottabile senza azioni manuali.

**Independent Test**: con un indice costruito pre-ibrido (solo vettoriale), eseguire una query con
configurazione di default e verificare che restituisca risultati (equivalenti al baseline) e che il
log contenga il warning strutturato; impostare `SERTOR_ENGINE=baseline` e verificare risultati
identici al sistema attuale.

**Acceptance Scenarios**:

1. **Given** nessuna configurazione esplicita del motore, **When** un consumatore esegue una
   ricerca su un corpus indicizzato con l'ibrido, **Then** il motore attivo è quello ibrido e i
   risultati arrivano nello stesso formato di sempre (nessun cambiamento richiesto al consumatore).
2. **Given** `SERTOR_ENGINE=baseline`, **When** si esegue qualunque ricerca, **Then** i risultati
   sono identici a quelli del sistema attuale (il baseline resta immutato e pienamente funzionante).
3. **Given** un corpus indicizzato prima della feature (indice lessicale assente) e il default
   `hybrid`, **When** si esegue una ricerca, **Then** la query NON fallisce, restituisce risultati
   solo-vettoriali equivalenti al baseline e viene emesso un warning strutturato che spiega come
   abilitare l'ibrido (re-index).
4. **Given** un valore non riconosciuto della manopola motore, **When** il sistema viene composto,
   **Then** l'errore è esplicito e indica i valori ammessi (nessun fallback silenzioso).

---

### User Story 3 - Qualità misurata: ground-truth e chiusura dei 2 xfail (Priority: P3)

L'owner/maintainer dispone di un **ground-truth set** sul corpus sertor (coppie query → file
atteso, almeno 10: query a simbolo esatto + query architetturali NL) e di una **valutazione
comparativa** che misura baseline, ibrido e ibrido+rerank sullo stesso set, riportando hit@1/3/5/10
e MRR@10 per ciascuna modalità. I due test di pertinenza oggi marcati `xfail` vengono completati
con questo set e convertiti a verifiche strict che passano con il motore ibrido.

**Why this priority**: trasforma "funziona" in "misurato" (Principio V): il confronto è il
criterio di accettazione della feature e chiude il debito dei 2 xfail. Dipende dall'esistenza del
motore (US1) ma non dal reranking.

**Independent Test**: eseguire la valutazione comparativa sul ground-truth e ottenere il report
con le metriche per modalità; eseguire i 2 test di pertinenza e verificarne il passaggio strict.

**Acceptance Scenarios**:

1. **Given** il ground-truth set (≥ 10 coppie, miste simbolo/NL), **When** la valutazione
   comparativa viene eseguita, **Then** il report espone hit@1, hit@3, hit@5, hit@10 e MRR@10 per
   baseline, ibrido e (se il reranker è disponibile) ibrido+rerank.
2. **Given** il ground-truth fissato, **When** i 2 test di pertinenza (già esistenti come xfail)
   vengono eseguiti, **Then** passano in modalità strict con soglie: hit@5 ibrido ≥ hit@5 baseline
   e MRR ibrido ≥ MRR baseline.
3. **Given** il sottoinsieme di query a simbolo/termine esatto, **When** si confrontano ibrido e
   baseline, **Then** l'ibrido raggiunge hit@5 ≥ baseline + 10 punti percentuali.
4. **Given** una riorganizzazione del repository ospite, **When** il ground-truth viene riletto,
   **Then** il set resta esprimibile (path relativi / identificatori di chunk) senza assunzioni
   sulla struttura interna del progetto.

---

### User Story 4 - Reranking opzionale come secondo stadio (Priority: P4)

L'owner/maintainer abilita un **secondo stadio di reranking** (cross-encoder) che ri-ordina il
pool fuso e restituisce i top-k ri-ordinati. La dipendenza del reranker è un **extra installabile
separatamente**: senza l'extra, il motore ibrido funziona normalmente (solo fusione RRF), senza
errori e senza degrado silenzioso; se il reranking è **configurato** ma l'extra è assente, il
sistema dà un errore esplicito e azionabile (la misconfigurazione è subito visibile).

**Why this priority**: il reranking è il vantaggio maggiore sul caso embedder locale/debole, ma è
dichiaratamente opzionale (Should): il valore core della feature si dimostra già con RRF. Il
prototipo ha anche mostrato che su embedder forte può lievemente peggiorare (rischio noto R-3).

**Independent Test**: con l'extra installato e il reranking abilitato, verificare che il pool fuso
venga ri-ordinato e che l'evento di log del reranker sia emesso; senza extra e senza
configurazione, verificare comportamento identico all'ibrido RRF-only; senza extra ma con
reranking configurato, verificare l'errore esplicito.

**Acceptance Scenarios**:

1. **Given** l'extra del reranker installato e il reranking abilitato, **When** si esegue una
   query ibrida, **Then** i top-k restituiti sono ri-ordinati dal punteggio del cross-encoder sul
   pool fuso.
2. **Given** reranking non configurato (o extra assente e non richiesto), **When** si esegue una
   query ibrida, **Then** i risultati sono quelli della fusione RRF, senza alcun cambio silenzioso
   di comportamento.
3. **Given** reranking configurato ma extra non installato, **When** si esegue una query ibrida,
   **Then** il sistema solleva un errore esplicito e azionabile (niente fallback silenzioso a
   RRF-only).
4. **Given** il pacchetto base installato senza l'extra del reranker, **When** il motore ibrido
   viene importato e usato, **Then** nessun errore di import si verifica (dipendenza isolata e
   caricata pigramente).

---

### Edge Cases

- **Corpus mai indicizzato** (nessun indice, né vettoriale né lessicale): la query ibrida fallisce
  con errore esplicito che nomina la collezione mancante (stesso comportamento strict del
  baseline), NON con degradazione.
- **Corpus indicizzato pre-ibrido** (vettoriale presente, lessicale assente): degradazione a
  solo-vettoriale + warning strutturato; la query non fallisce (vedi Assumptions per la
  riconciliazione REQ-004/REQ-034).
- **Pareggi nella fusione**: due chunk con lo stesso punteggio fuso → ordinamento deterministico
  con tie-break consistente (stesso pattern del merge multi-collezione esistente).
- **Risultato presente in una sola lista** (solo lessicale o solo vettoriale): la fusione lo
  considera con il contributo della sola lista in cui appare; nessuna esclusione arbitraria.
- **Valore invalido di `SERTOR_ENGINE`**: errore esplicito di configurazione con i valori ammessi.
- **Reranking configurato senza extra installato**: errore esplicito e azionabile (REQ-022), mai
  fallback silenzioso.
- **Corpora o provider distinti**: gli indici lessicali sono namespaced come le collezioni
  vettoriali; due corpora (o due provider) non condividono mai lo stesso indice lessicale.
- **Log con segreti**: gli eventi di log del motore ibrido non contengono mai valori segreti
  (chiavi API, credenziali), secondo il pattern di redazione esistente.

## Requirements *(mandatory)*

### Functional Requirements

#### Indice lessicale (Gruppo A)

- **FR-001** (REQ-001): quando il motore ibrido indicizza un corpus, il sistema DEVE costruire un
  indice lessicale sugli stessi chunk inseriti nello store vettoriale, con un trattamento del
  testo che preserva identificatori, sotto-token degli snake_case e termini rari.
- **FR-002** (REQ-002): l'indice lessicale DEVE coprire lo stesso namespace di corpus della
  collezione vettoriale che rispecchia (lessicale e vettoriale attingono sempre allo stesso
  insieme di chunk).
- **FR-003** (REQ-003): quando il corpus viene re-indicizzato (rebuild completo), il sistema DEVE
  ricostruire l'indice lessicale insieme a quello vettoriale, mantenendoli coerenti.
- **FR-004** (REQ-004): se il corpus non è mai stato indicizzato (nessuna collezione esistente),
  la query ibrida DEVE fallire con un errore esplicito, non restituire un risultato degradato in
  modo silenzioso. *(Per il caso "vettoriale presente, lessicale assente" vale FR-016 — vedi
  Assumptions.)*
- **FR-005** (REQ-005): l'indice lessicale DEVE essere namespaced coerentemente con la collezione
  vettoriale (stesso namespace corpus+provider); corpora o provider distinti non condividono mai
  lo stesso indice lessicale.

#### Fusione RRF (Gruppo B)

- **FR-006** (REQ-010): a ogni query ibrida il sistema DEVE recuperare un pool di candidati sia
  dallo store vettoriale sia dall'indice lessicale, fondere le due liste ordinate con Reciprocal
  Rank Fusion e restituire i top-k del ranking fuso.
- **FR-007** (REQ-011): la fusione DEVE usare una costante `c` configurabile (default 60) e una
  dimensione del pool configurabile, con default centralizzati nella configurazione e
  sovrascrivibili senza modificare codice.
- **FR-008** (REQ-012): il ranking fuso DEVE essere deterministico: a parità di input l'ordine è
  sempre lo stesso; i pareggi sono risolti in modo consistente.
- **FR-009** (REQ-013): i risultati DEVONO essere restituiti nella stessa entità di dominio usata
  dal motore baseline, così che nessun consumatore richieda modifiche.

#### Reranking opzionale (Gruppo C)

- **FR-010** (REQ-020): dove l'extra del reranker è installato, il motore ibrido DEVE poter
  applicare un cross-encoder che ri-punteggia il pool fuso e restituisce i top-k ri-ordinati.
- **FR-011** (REQ-021): la dipendenza del reranker DEVE essere isolata come extra installabile
  separatamente, con caricamento pigro; il motore ibrido DEVE essere importabile e operabile
  senza l'extra installato.
- **FR-012** (REQ-022): quando il reranking è configurato ma l'extra non è installato, il sistema
  DEVE sollevare un errore esplicito e azionabile (mai fallback silenzioso a RRF-only).
- **FR-013** (REQ-023): dove il reranking è disabilitato (non configurato o extra assente e non
  richiesto), il motore ibrido DEVE restituire direttamente i risultati della fusione RRF, senza
  degrado né cambi silenziosi di comportamento.
- **FR-014** (REQ-024): la dimensione del pool passato al reranker DEVE essere configurabile
  (default maggiore di k, es. 3×k) e centralizzata nella configurazione.

#### Selezione del motore e integrazione (Gruppo D)

- **FR-015** (REQ-030): il sistema DEVE esporre la manopola di configurazione `SERTOR_ENGINE` per
  selezionare il motore attivo (`baseline` o `hybrid`); il default È `hybrid` (il motore migliore
  è il default; `baseline` resta selezionabile esplicitamente).
- **FR-016** (REQ-034): se il motore ibrido è selezionato (anche per default) e l'indice lessicale
  della collezione target è assente (corpus indicizzato prima della feature), il sistema DEVE
  degradare con grazia al retrieval solo-vettoriale (risultati equivalenti al baseline), emettendo
  un warning strutturato che dichiara l'indice lessicale mancante e che il re-index abilita
  l'ibrido; la query NON deve fallire.
- **FR-017** (REQ-031): la selezione del motore DEVE risolversi esclusivamente nel composition
  root; nessun servizio, facade o adapter referenzia direttamente un'implementazione concreta di
  motore.
- **FR-018** (REQ-032): la facade di retrieval DEVE restare l'unica superficie stabile per tutti i
  consumatori (MCP, CLI, agenti); il passaggio all'ibrido non richiede modifiche all'interfaccia
  della facade né ad alcun consumatore.
- **FR-019** (REQ-033): il motore ibrido DEVE esporre la stessa interfaccia del motore baseline
  (stessi metodi di indicizzazione, query e verifica indice, stesso attributo nome), così che il
  composition root possa sostituirli in modo trasparente.

#### Percorso ibrido nativo per-store (Gruppo E — Could)

- **FR-020** (REQ-040): dove il backend di store è Azure AI Search, il sistema PUÒ delegare il
  retrieval ibrido alla hybrid query nativa del backend (denso + keyword) con semantic ranker
  opzionale, invece di eseguire la fusione lato client.
- **FR-021** (REQ-041): dove il percorso nativo è selezionato, i risultati DEVONO essere
  funzionalmente equivalenti al percorso client-side (stessa entità risultato, stesso k, stesso
  filtro per tipo di documento): i consumatori non ne sono toccati.
- **FR-022** (REQ-042): la scelta tra fusione client-side e ibrido nativo DEVE essere una
  decisione di configurazione (non un cambiamento di codice), risolta nel composition root.

#### Qualità misurata e ground-truth (Gruppo F)

- **FR-023** (REQ-050): il sistema DEVE includere un ground-truth set per il corpus sertor con
  almeno 10 coppie query→file-atteso, che copra sia query lessicali/a simbolo sia query
  architetturali in linguaggio naturale. *(5-6 coppie "ovvie" si fissano già in fase di design,
  il set si completa a ≥10 in implementazione — DA-4.)*
- **FR-024** (REQ-051): quando la valutazione gira sul ground-truth, il sistema DEVE confrontare
  baseline, ibrido e ibrido+rerank (dove il reranker è disponibile) riportando hit@1, hit@3,
  hit@5, hit@10 e MRR@10 per ciascuna modalità; il confronto è criterio di accettazione della
  feature.
- **FR-025** (REQ-052): i 2 test di integrazione oggi `xfail` DEVONO essere completati con il
  ground-truth, convertiti a strict e passare sul motore ibrido con soglie: hit@5 ibrido ≥ hit@5
  baseline e MRR ibrido ≥ MRR baseline.
- **FR-026** (REQ-053): il ground-truth NON DEVE contenere assunzioni sulla struttura interna del
  progetto: è espresso come path relativi o identificatori di chunk e resta valido se il
  repository viene riorganizzato.

#### Osservabilità (Gruppo G)

- **FR-027** (REQ-060): a ogni query il motore ibrido DEVE emettere un evento di log strutturato
  (meccanismo esistente) che registra almeno: nome motore, provider, collezione, hit lessicali,
  hit densi, k fuso, reranking applicato, tempo trascorso.
- **FR-028** (REQ-061): quando il reranker viene applicato, il sistema DEVE emettere un evento di
  log separato con: modello del reranker, dimensione del pool, top-k, tempo trascorso.
- **FR-029** (REQ-062): i log NON DEVONO mai contenere valori segreti (chiavi API, credenziali);
  la redazione segue il pattern esistente.

#### Retro-compatibilità e non-distruttività (Gruppo H)

- **FR-030** (REQ-070): il motore baseline e i suoi test DEVONO restare immutati e pienamente
  verdi dopo l'introduzione dell'ibrido.
- **FR-031** (REQ-071): con `SERTOR_ENGINE=baseline` esplicito i risultati DEVONO essere identici
  al sistema attuale per tutti i consumatori; con il default `hybrid`, i corpora indicizzati prima
  della feature DEVONO continuare a funzionare via la degradazione di FR-016 finché non vengono
  re-indicizzati.
- **FR-032** (REQ-072): il motore ibrido DEVE essere non distruttivo sul repository target: non
  modifica file sorgente dell'utente; l'indice lessicale vive nella stessa directory di indici
  namespaced dello store vettoriale.

### Key Entities

- **Indice lessicale**: struttura di ricerca per rilevanza lessicale costruita sugli stessi chunk
  dell'indice vettoriale; namespaced per (corpus, provider); ricostruita insieme al vettoriale a
  ogni rebuild.
- **Ranking fuso (RRF)**: lista ordinata unica ottenuta combinando il ranking vettoriale e quello
  lessicale con Reciprocal Rank Fusion; parametri: costante `c` (default 60) e dimensione del
  pool per fonte; deterministico con tie-break consistente.
- **Reranker (secondo stadio, opzionale)**: cross-encoder che ri-punteggia il pool fuso e
  restituisce i top-k ri-ordinati; dipendenza isolata come extra, caricata pigramente.
- **Selettore del motore (`SERTOR_ENGINE`)**: manopola di configurazione globale (`baseline` |
  `hybrid`, default `hybrid`), risolta solo nel composition root.
- **Ground-truth set**: insieme versionato di coppie (query → file/chunk atteso) sul corpus
  sertor, misto simbolo/NL, ≥ 10 coppie; alimenta la valutazione comparativa e i 2 test strict.
- **Risultato di retrieval**: entità di dominio esistente, invariata; è il contratto che tiene
  stabili facade, MCP e CLI.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (LSC-1): sul sottoinsieme di query a simbolo/termine esatto del ground-truth, il
  motore ibrido raggiunge hit@5 ≥ baseline + 10 punti percentuali.
- **SC-002** (LSC-2): il motore è selezionabile dalla sola configurazione (senza modifiche di
  codice); il baseline resta funzionante e selezionabile con risultati identici a oggi.
- **SC-003** (LSC-3): i consumatori esistenti (facade, server MCP, CLI) beneficiano dell'ibrido
  senza alcuna modifica alla loro superficie: nessun file dei consumatori cambia.
- **SC-004** (LSC-4): senza l'extra del reranker installato, il motore ibrido funziona
  correttamente (fusione RRF) senza errori né degrado silenzioso.
- **SC-005** (LSC-5): il motore ibrido è interamente testabile senza rete (provider e indici
  mock); la suite `not cloud` passa.
- **SC-006** (LSC-6): i 2 test di pertinenza oggi `xfail` passano in modalità strict con il
  ground-truth fissato e le soglie comparative (ibrido ≥ baseline su hit@5 e MRR).
- **SC-007** (LSC-7): il motore ibrido funziona su qualunque corpus indicizzato con il nucleo
  (host-agnostico): la verifica su un secondo corpus non richiede alcun adattamento.
- **SC-008** (REQ-034): su un corpus indicizzato prima della feature, una ricerca con
  configurazione di default restituisce risultati (equivalenti al baseline) senza errori, e il
  log contiene il warning strutturato di degradazione.

## Assumptions

- **Riconciliazione REQ-004 ↔ REQ-034 (strict vs degradazione)**: i due requisiti EARS si
  applicano a casi distinti. REQ-034 (posteriore, decisione utente DA-1b) governa il caso "corpus
  indicizzato pre-ibrido": collezione vettoriale presente, indice lessicale assente → degradazione
  a solo-vettoriale + warning, mai errore. REQ-004 governa il caso "corpus mai indicizzato"
  (nessuna collezione): errore esplicito, stesso comportamento strict del baseline. La spec
  codifica questa lettura in FR-004/FR-016 e negli edge case; da confermare in clarify se si
  desidera una lettura diversa.
- **Indice lessicale in-memory**: per corpus di dimensioni tipiche (< 10.000 chunk) l'indice
  lessicale ricostruito/caricato in memoria è sufficiente; la persistenza su disco è rifinitura
  futura (FEAT-009 d'epica). L'indice vive comunque nel perimetro della directory indici
  namespaced (FR-032).
- **Latenza qualitativa (D3)**: nessuna soglia numerica; il doppio retrieval non deve introdurre
  attesa percettibile per l'uso interattivo da agente; misura empirica nel dogfood, soglia da
  fissare solo se emerge un problema.
- **Reranker di riferimento**: cross-encoder leggero senza dipendenze pesanti (nel prototipo:
  FlashRank ONNX); la scelta concreta è di design, il vincolo di isolamento come extra vale per
  qualunque libreria.
- **Percorso nativo per-store (D2)**: resta Could; il core ibrido (fusione client-side) è
  store-agnostico by design e funziona su qualunque adapter dello store vettoriale; la delega
  nativa (Azure AI Search, e in futuro altri store) si implementa quando quegli store saranno in
  uso.
- **Ground-truth nel repo (V-5)**: il set è versionato come fixture/codice nel repository; 5-6
  coppie ovvie si fissano in fase di design (es. query `EmbeddingProvider` → file delle porte del
  dominio), il completamento a ≥10 avviene in implementazione.
- **Punto di aggancio dei consumatori (A-5)**: il server MCP e la CLI consumano la facade, non il
  motore direttamente; l'integrazione dell'ibrido nella facade via composition root è quindi il
  punto di collegamento naturale e sufficiente.
