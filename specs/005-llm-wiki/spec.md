# Feature Specification: LLM Wiki end-to-end (FEAT-010)

**Feature Directory**: `specs/005-llm-wiki/`
**Branch**: `spec/005-llm-wiki`
**Created**: 2026-06-04 · **Status**: Draft
**Deriva da**: `requirements/sertor-core/llm-wiki/requirements.md` (FEAT-010; D-1..D-17, FR-001..042, SC-001..010)

## Sintesi

Capacità **end-to-end** dell'**LLM Wiki** ispirata al pattern di Karpathy: una base di conoscenza
Markdown che il sistema **genera e mantiene** da un progetto e che entra nel **RAG** come corpus
interrogabile. Due momenti distinti: **(a) generazione** del wiki (linguaggio naturale, concetti
linkati, incrementale) da un insieme **configurabile** di fonti-input; **(b) retrieval** via RAG con
**collezioni separate** wiki/codice interrogate insieme. Il popolamento è **agentico** (una skill che
riusa le primitive esistenti, invocata **al commit**); la manutenzione (lint + verifica di freschezza)
è un **gate human-in-the-loop**. Vale anche su **progetti senza codice**. Questa feature **consolida**
la creazione/indicizzazione (ex FEAT-003) e **assorbe** la manutenzione del wiki (ex FEAT-007).

## User Scenarios & Testing

### User Story 1 — Setup del wiki su un repo (`sertor wiki init`) [P1] 🎯

Come maintainer di un progetto inizializzo l'LLM Wiki in **un'unica** operazione, ottenendo la
struttura e l'**aggancio automatico** che terrà il wiki vivo ai commit successivi.

**Perché P1**: senza setup non esiste né struttura né trigger; è il prerequisito di tutto.

**Acceptance**:
1. **Given** un repo git senza wiki, **When** eseguo il setup, **Then** sono create la struttura wiki
   (cartelle tematiche, `index.md`, `log.md`) e **installato il binding del trigger** al commit; un
   ingest iniziale è eseguito se fornito. (FR-040)
2. **Given** il setup completato, **When** eseguo un commit, **Then** la generazione del wiki **scatta
   davvero** (il trigger non si perde). (SC-008)
3. **Given** un repo **non** git, **When** tento il setup, **Then** ricevo un errore esplicito (git è
   prerequisito). (assunzione D-5)

### User Story 2 — Generazione del wiki al commit (incrementale) [P1] 🎯

Come maintainer voglio che, a ogni commit, il wiki si **aggiorni da solo** elaborando **solo ciò che è
cambiato**, così resta vivo senza lavoro manuale.

**Perché P1**: è il cuore "vivo" del pattern Karpathy e la ragione della feature.

**Acceptance**:
1. **Given** un wiki inizializzato, **When** un commit tocca N file, **Then** l'aggiornamento è
   **limitato alle pagine collegate alle entità del changeset** (non un full rebuild). (FR-018/037, SC-001)
2. **Given** la generazione, **When** produce/aggiorna pagine, **Then** queste sono in **linguaggio
   naturale**, a **concetti linkati** (wikilink), conformi alle convenzioni. (FR-008)
3. **Given** le fonti-input, **When** si configura il loro insieme, **Then** la generazione le usa
   (versionate al commit; `ingested_sources/` a trigger manuale). (FR-009)
4. **Given** la generazione invocata al commit, **When** completa, **Then** è eseguita da una **skill
   distinta** dal versioning, **invocata dal** configuration-manager (o equivalente del client), e gli
   output entrano **nello stesso commit** (sincrona; fallback follow-up). (FR-025/026, D-8)
5. **Given** input invariato, **When** la si riesegue, **Then** l'esito strutturale è **identico**
   (idempotenza; id chunk = path relativo). (SC-006)

### User Story 3 — Ingest di documentazione esterna in `ingested_sources/` [P2]

Come maintainer importo documentazione esterna **non versionabile** in un'area dedicata, che il wiki usa
come **input** per generare/arricchire concetti.

**Acceptance**:
1. **Given** documentazione esterna, **When** invoco l'ingest (alla creazione, on-demand, o su update),
   **Then** `ingested_sources/` è (ri)popolata con quella documentazione. (FR-030, SC-010)
2. **Given** l'ingest, **When** completa, **Then** **non** scrive pagine-riassunto: l'import è
   **distinto** dalla compilazione in concetti (che avviene in generazione). (FR-031)
3. **Given** un file **binario non leggibile** in `ingested_sources/`/`manual_edited/`, **When** si
   processa, **Then** **non** viene ingerito. (FR-022)

### User Story 4 — Retrieval su collezioni separate (wiki + codice) [P1] 🎯

Come consumatore (umano o agente) interrogo un'unica "verità" che restituisce sia il **perché** (wiki)
sia il **come** (codice), tenendo però i due aggiornabili indipendentemente.

**Perché P1**: è il valore d'uso ("una sola verità interrogabile") e abilita il dogfooding.

**Acceptance**:
1. **Given** wiki generato + codice indicizzati in **collezioni separate**, **When** interrogo,
   **Then** ricevo risultati da **entrambi** (query congiunta, peso paritario). (FR-010, SC-003)
2. **Given** le cartelle di **input** (`manual_edited/`, `ingested_sources/`), **When** interrogo,
   **Then** **non** compaiono nel RAG: ricevo i **concetti compilati** che ne derivano. (FR-023, SC-002)
3. **Given** una collezione, **When** la rigenero, **Then** **non** intacca l'altra (refresh
   indipendente). (FR-011)
4. **Given** una pagina wiki con riferimenti alle fonti di input, **When** indicizzo, **Then** quei
   riferimenti **non** sono indicizzati. (FR-024)

### User Story 5 — Manutenzione (lint + freschezza) con gate al commit [P2]

Come maintainer voglio che il sistema mi segnali quando il wiki si rompe (link/orfani) o **non è più
vero** (vs codice/decisioni), e che al commit mi **fermi** con proposte di rimedio.

**Acceptance**:
1. **Given** il wiki, **When** eseguo il lint, **Then** sono rilevati link rotti, pagine orfane,
   copertura/cross-reference mancanti. (FR-035)
2. **Given** una pagina che contraddice il **codice/test** (comportamento) **o** una **decisione**
   registrata, **When** eseguo la verifica di freschezza, **Then** è segnalata **obsoleta**. (FR-017/036, SC-009)
3. **Given** un commit, **When** lint/freschezza girano, **Then** sono **incrementali** sulle pagine
   collegate alle entità del changeset; **on-demand**/**periodico** girano su tutto il wiki. (FR-037/038)
4. **Given** problemi sopra soglia al commit, **When** il gate scatta, **Then** **blocca**, **avvisa**,
   **propone ≥1 soluzione** tra cui **"ignora e committa"**; scegliendo l'override il commit procede e
   l'override è **registrato**. (FR-041/042, SC-004)

### User Story 6 — Superfici di invocazione (skill + CLI + MCP) [P2]

Come utente/agente invoco le operazioni on-demand (ingest, query, rigenerazione, manutenzione, setup)
dalla superficie che preferisco.

**Acceptance**:
1. **Given** un'operazione on-demand, **When** la invoco, **Then** è raggiungibile via **skill** (del
   client LLM, primaria), **CLI** e **MCP** — stessa funzione dalle tre superfici. (FR-032, SC-007)
2. **Given** la query, **When** interrogo, **Then** avviene via **RAG** (no superficie wiki-nativa
   dedicata); il wiki resta navigabile da editor esterni (Markdown interconnesso). (FR-033/034)

### User Story 7 — Progetto senza codice [P3]

Come utente con un progetto **solo documentale** (knowledge base/ricerca) uso comunque LLM Wiki + RAG.

**Acceptance**:
1. **Given** un repo **senza codice**, **When** uso generazione/retrieval/manutenzione, **Then**
   funzionano con le sole fonti documentali (`manual_edited/`, `ingested_sources/`, log). (FR-029, SC-005)

### Edge cases
- Setup senza binding del trigger installato → segnalato/installato dal setup, altrimenti il trigger si
  perde (R-03).
- Conflitto che coinvolge `manual_edited/` → **human-in-the-loop**: avvisa e chiede, non modifica la
  fonte. (FR-015)
- Generazione sincrona troppo costosa → fallback **asincrono** (commit di follow-up). (FR-026)
- Re-index incrementale non disponibile → fallback (rigenerazione più ampia). (dipendenza FEAT-009)

## Requirements (mappati al requisito EARS sorgente)

- **FR-101 Setup** (`sertor wiki init`: struttura + binding trigger + ingest iniziale). → FR-040, FR-028
- **FR-102 Generazione al commit incrementale** (skill distinta, invocata dal versioning, output nello
  stesso commit; fallback async). → FR-001/018/025/026/037
- **FR-103 Fonti-input configurabili** (versionate al commit; `ingested_sources/` manuale). → FR-009/030/031
- **FR-104 Formato wiki** (NL, concetti linkati, incrementale, Markdown aperto). → FR-008/034
- **FR-105 Convenzioni input** (`manual_edited/` immutabile compilato; `ingested_sources/` non
  versionato; binari non leggibili esclusi). → FR-016/022
- **FR-106 Retrieval collezioni separate** (wiki generato + codice, query congiunta, paritario; refresh
  indipendente). → FR-010/011
- **FR-107 Perimetro RAG** (solo wiki generato + codice; input e riferimenti non indicizzati). → FR-023/024
- **FR-108 Verità stratificata** (codice/test=comportamento; doc/spec/manual=perché; gerarchia
  default+configurabile; conflitti manual_edited = human-in-the-loop). → FR-012/013/014/015/017
- **FR-109 Manutenzione** (lint strutturale + verifica di freschezza; trigger incrementale@commit /
  on-demand / periodico). → FR-035/036/037/038
- **FR-110 Gate al commit** (blocca/avvisa/propone soluzioni incl. override tracciato). → FR-041/042
- **FR-111 Superfici** (skill + CLI + MCP; query via RAG). → FR-032/033
- **FR-112 No-code** (codice opzionale; funziona senza). → FR-029
- **FR-113 Idempotenza strutturale** (re-run identico; id = path relativo). → assorbe FEAT-003 REQ-050/051
- **FR-114 Consolidamento** (riusa le primitive struttura/record/distill di FEAT-003; override su
  ingest/sources e indicizzazione). → D-2/D-10/D-11

## Key Entities
- **Pagina wiki generata** (concetto/sintesi/tech/esperimento): NL, frontmatter, wikilink; di proprietà
  dell'LLM.
- **Fonte-input**: codice · test · SpecKit · log discussioni · `manual_edited/` (versionato) ·
  `ingested_sources/` (non versionato). L'LLM le legge, non le scrive.
- **Changeset**: insieme delle entità modificate dal commit, che seleziona le pagine da (ri)generare e
  verificare.
- **Collezione RAG**: due collezioni separate (wiki generato, codice), interrogate insieme.
- **Trigger binding**: aggancio del momento "commit" alla skill (per Claude Code: configuration-manager
  / hook), installato dal setup.
- **Report di manutenzione**: esiti di lint + freschezza; alimenta il gate.
- **GateOutcome**: pass/warning/blocked + override tracciato.

## Success Criteria
SC-001..SC-010 come da `requirements/sertor-core/llm-wiki/requirements.md` §6 (refresh incrementale al
commit; input non indicizzati; retrieval wiki+codice; gate blocca/avvisa/propone/override; no-code;
idempotenza; tre superfici; trigger installato; obsolescenza; ingest import≠compile).

## Scope
**In scope**: setup, generazione agentica al commit + on-demand + periodico, ingest in
`ingested_sources/`, manutenzione (lint+freschezza) con gate, retrieval collezioni separate, superfici
skill/CLI/MCP, no-code. **Fuori scope**: superficie wiki-nativa dedicata, arricchimento bidirezionale
(FEAT-008), full re-index del corpus, GUI/web, traduzione automatica, chunking di trascrizioni grezze.

## Prioritizzazione (MoSCoW)
- **Must**: US1 setup · US2 generazione al commit · US4 retrieval collezioni separate · idempotenza.
- **Should**: US3 ingest on-demand · US5 manutenzione + gate · US6 superfici.
- **Could**: trigger periodico · US7 no-code-first · gerarchia di autorità configurabile.

## Tracciabilità
US1→FR-101 · US2→FR-102/103/104/113 · US3→FR-103/105 · US4→FR-106/107 · US5→FR-108/109/110 ·
US6→FR-111 · US7→FR-112. Tutti i FR rinviano ai FR-001..042 / SC-001..010 del requisito sorgente.
