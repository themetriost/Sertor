# Feature Specification: Dedup dei risultati near-duplicate nel retrieval

**Feature Branch**: `090-retrieval-result-dedup`

**Created**: 2026-07-07

**Status**: Draft

**Input**: Leva A-07 (audit SWOT) / epica `retrieval-qualita` (E5-FEAT-003). Diagnosi in
`wiki/log/2026-07-07.md`. Direttiva: dedup dei risultati **prima del cut finale**, MVP esatto per
content-hash, config `SERTOR_DEDUP`, host-agnostico, lift **misurato** sull'eval.

## User Scenarios & Testing *(mandatory)*

Attori: l'**agente** che consuma il retrieval (via CLI/MCP) e il **manutentore** che ne misura la qualità.

### User Story 1 — I risultati del top-k sono distinti, i doc canonici non vengono sepolti (Priority: P1)

Quando l'agente interroga il corpus, i primi risultati (top-k) **non** devono contenere lo **stesso
contenuto ripetuto** proveniente da path diversi. Oggi lo stesso testo vive in più punti (es. i blocchi di
`CLAUDE.md` sono **byte-identici** alle copie nel bundle installer `assets/**`); questi duplicati saturano
il top-k e **schiacciano** le pagine canoniche (`wiki/concepts/*.md` finiscono a rank 4-6, fuori dai primi
risultati che l'agente legge). Con la dedup, di ogni gruppo di risultati a **contenuto identico** ne resta
**uno** (quello col rank più alto), liberando gli slot per contenuto **diverso** e riportando i doc
canonici nel top-k.

**Why this priority**: è il cuore della feature e della leva sulla **missione** (fusione code+doc): la
metà `search_docs` è quella debole, e la causa misurata è la duplicazione. Senza questa storia non c'è
feature.

**Independent Test**: su un corpus con un contenuto ripetuto in ≥2 path, una query che matcha quel
contenuto restituisce **una sola** istanza nel top-k (non N), e un doc **distinto** ma pertinente che
prima era a rank > k rientra nel top-k. Verificabile su un corpus di test e sull'eval reale.

**Acceptance Scenarios**:

1. **Given** due (o più) chunk con **testo identico** (a meno di whitespace) da path diversi, entrambi
   candidati per una query, **When** si esegue il retrieval, **Then** il top-k contiene **una sola**
   istanza di quel contenuto (quella col rank più alto), non i duplicati.
2. **Given** il corpus del dogfood (blocchi `CLAUDE.md` duplicati in `assets/**`), **When** si interroga
   «the step ritual and definition of done», **Then** `wiki/concepts/step-ritual.md` rientra nel top-3
   (prima era a rank 4 dietro le copie duplicate).
3. **Given** risultati **senza** duplicati, **When** si esegue il retrieval, **Then** l'ordine e il
   contenuto del top-k restano **invariati** (la dedup è un no-op sui risultati già distinti).

### User Story 2 — Comportamento configurabile e host-agnostico (Priority: P2)

Il manutentore (e ogni ospite) deve poter **disattivare** la dedup senza toccare il codice, e la capacità
deve funzionare su **qualsiasi** progetto ospite (non solo il dogfood), senza assunzioni sul suo contenuto.

**Why this priority**: configurabilità centralizzata (Principio VIII) e host-agnosticità (Principio X)
sono vincoli costituzionali; la dedup vale per ogni host con contenuto ripetuto (`CLAUDE.md` + una wiki
che lo cita), non è un fix dogfood-specifico.

**Independent Test**: con la manopola **disattivata**, il retrieval si comporta esattamente come prima
(nessuna dedup); con la manopola al default, la dedup è attiva. La stessa capacità gira su un progetto
ospite diverso senza modifiche al corpo.

**Acceptance Scenarios**:

1. **Given** `SERTOR_DEDUP=false`, **When** si esegue il retrieval, **Then** i risultati sono identici al
   comportamento pre-feature (dedup bypassata).
2. **Given** il default (`SERTOR_DEDUP=true`), **When** si esegue il retrieval, **Then** la dedup è attiva.

### Edge Cases

- **Boilerplate legittimo ripetuto** (es. header di licenza in molti file): la dedup lo collassa a una
  sola istanza nel top-k — accettabile (l'agente non trae valore da N copie identiche).
- **Duplicati che occupano *tutto* il pool**: se dopo la dedup restano < k risultati distinti, si
  restituiscono quelli disponibili (nessun riempimento con duplicati); il segnale di
  confidenza/low-confidence esistente resta invariato.
- **Near-duplicate NON identici** (stesso testo con 1-2 parole diverse): **fuori ambito MVP** (vedi *Out
  of Scope*) — la dedup esatta non li collassa; è un miglioramento futuro, non una regressione.
- **Reranker attivo**: la dedup non deve alterare il contratto del reranker; opera sul pool di candidati
  in modo che il rerank/cut lavori su contenuto distinto.
- **Determinismo**: a parità di input, la scelta dell'istanza da tenere (rank più alto; tie-break stabile)
  è **deterministica** (Principio VI) — nessuna dipendenza da ordine non stabile.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il retrieval MUST rimuovere dai risultati, **prima del cut finale al top-k**, le istanze a
  **contenuto duplicato**, tenendo per ogni gruppo di duplicati **una sola** istanza — quella col **rank
  più alto** (tie-break stabile e deterministico).
- **FR-002**: Il criterio di duplicazione dell'MVP MUST essere l'**uguaglianza esatta del contenuto** del
  risultato **normalizzato** (whitespace collassato); MUST NOT richiedere un LLM né embedding aggiuntivi
  (deterministico, economico — RNF-1).
- **FR-003**: La dedup MUST essere un **no-op** sui risultati già distinti (nessun cambio di ordine o
  contenuto quando non ci sono duplicati) — FR-testabile via lo scenario US1.3.
- **FR-004**: La dedup MUST essere applicata **coerentemente** su tutte le superfici di retrieval che
  restituiscono risultati all'agente (`search_code`, `search_docs`, `search_combined`) e su entrambi i
  motori pertinenti (ibrido di default e baseline), all'interno di ciascuna superficie/`doc_type`.
- **FR-005**: La dedup MUST essere governata da un'**unica manopola di configurazione centralizzata**
  (`SERTOR_DEDUP`, default **on**), attivabile/disattivabile senza modifiche al codice (Principio VIII);
  con la manopola off il comportamento MUST essere identico al pre-feature.
- **FR-006**: La capacità MUST essere **host-agnostica** — nessuna assunzione sul contenuto o sulla
  struttura del progetto ospite; MUST operare su un progetto ospite diverso senza modifiche al corpo
  (Principio X). **Nessun asset distribuito** MUST cambiare (la manopola nel template `.env` è l'unico
  tocco host-facing).
- **FR-007**: La creazione degli embeddings/indicizzazione MUST restare **invariata** — la dedup opera
  **a query-time** sui risultati, non modifica il corpus indicizzato né gli id dei chunk.
- **FR-008**: L'operazione MUST emettere osservabilità sufficiente (Principio IX): almeno il conteggio dei
  risultati **rimossi** come duplicati nel log della query, senza segreti.

### Key Entities

- **Risultato di retrieval**: l'unità restituita all'agente (path, chunk, testo, score/rank). *Attributo
  rilevante:* il **contenuto testuale**, base della chiave di dedup.
- **Gruppo di duplicati**: insieme di risultati con contenuto normalizzato identico. *Invariante:* nel
  top-k ne sopravvive **uno** (rank più alto).
- **Manopola `SERTOR_DEDUP`**: configurazione centralizzata (default on) che abilita/disabilita la dedup.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Su una query con contenuto ripetuto in ≥2 path, il top-k contiene **0** coppie di risultati
  a contenuto identico (dedup verificata su un corpus di test).
- **SC-002**: **Lift misurato** sull'eval reale a **ground-truth fissa**: il gate `eval run --fused` che
  oggi è **rosso** torna **verde** — `search_docs` hit@3 risale ad **almeno** il baseline (≥ 0.75) e union
  hit-rate risale (≥ il baseline pertinente), senza **ri-registrare** il baseline finché il lift non è reale.
- **SC-003**: Con `SERTOR_DEDUP=false`, le metriche eval sono **identiche** al comportamento pre-feature
  (la dedup è realmente bypassabile).
- **SC-004**: `search_code` (già robusto, MRR ~0.74) **non regredisce** (nessun falso-dedup che rimuove
  risultati legittimamente distinti).
- **SC-005**: `sertor-core` invariato fuori dal punto d'inserimento del retrieval; suite (`-m "not cloud"`)
  + `ruff` verdi pre-merge (gate E15-FEAT-008); nessun asset distribuito reso Sertor-specifico.

## Out of Scope

- **Near-duplicate *fuzzy*** (stesso significato con testo leggermente diverso: MinHash/shingling/soglia di
  similarità): **rinviato** come miglioramento successivo dell'epica `retrieval-qualita` (promosso al
  backlog E5, non sepolto). L'MVP esatto risolve la pollution **misurata** (byte-copy); il fuzzy è additivo.
- **Cambiare cosa viene indicizzato** (es. escludere `assets/**` dal corpus): è una mitigazione **di
  config**, blunt e dogfood-specifica; questa feature risolve il problema **nel retrieval**, per ogni host,
  senza perdere retrievabilità di alcun contenuto.
- **Re-ranking semantico avanzato / diversità MMR**: oltre l'MVP; valutabile solo se l'esatto non basta.

## Assumptions

- **Normalizzazione:** l'uguaglianza di contenuto usa il testo del chunk con **whitespace collassato**,
  **case-preserving** (evita over-merge di testi diversi che differiscono solo per maiuscole). Default
  ragionevole; affinabile al plan se l'eval lo richiede.
- **La duplicazione misurata è per lo più esatta** (byte-copy `assets/**` ↔ blocchi `CLAUDE.md`) — il
  dry-run/diagnosi 2026-07-07 lo conferma; quindi l'MVP esatto sposta l'ago. Se dopo la misura resta un
  residuo fuzzy significativo, si promuove il follow-up.
- **Punto d'inserimento:** dentro il retrieval, **prima del cut finale** (post-materialize, pre-rerank/
  top-k), coerente con la pipeline esistente dei motori — dettaglio confermato al plan.
- **Confine dev↔dogfood invariato:** i test girano sull'editable `.venv`; la manopola default-on vale sia
  per il dogfood sia per gli ospiti (nel template `.env` dell'installer).
