# Feature Specification: Rituale wiki resistente allo skip silenzioso (scoperta deterministica + dichiarazione forzata)

**Feature Branch**: `097-rituale-anti-skip`

**Created**: 2026-07-12

**Status**: Draft

**Input**: E10 `debito-tecnico` **FEAT-026** (MVP = parte 1 + parte 3). Requisiti di dettaglio in
[`requirements/debito-tecnico/rituale-anti-skip/requirements.md`](../../requirements/debito-tecnico/rituale-anti-skip/requirements.md)
(REQ-001..011). Origine: convergenza indipendente di due feedback ospiti (`hermes-nunzio-ha` + `Noetix`,
2026-07-01).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - La scoperta dei candidati non dipende più dalla memoria (Priority: P1)

Chiudendo uno step significativo, l'agente **esegue un'operazione deterministica** del wiki-tooling che gli
**elenca i candidati a distillazione** — insiemi di pagine che, per segnali strutturali, fanno
probabilmente emergere un'entità durevole non ancora distillata. La *scoperta* smette di dipendere dal
fatto che l'agente «se ne ricordi»: il tool la produce da solo, deterministicamente, da leggere prima di
decidere.

**Why this priority**: è la causa-radice dei due feedback (il pattern «notato ma mai distillato» di Noetix,
il distill saltato di hermes-nunzio-ha). Senza scoperta deterministica, il resto resta discrezionale.

**Independent Test**: su uno stato-wiki che soddisfa l'euristica (più pagine cambiate insieme con nuovi
backlink incrociati e nessuna nuova pagina `concepts/`/`tech/`), il tool elenca quell'insieme come
candidato; su uno stato che non la soddisfa, non lo elenca. Ripetibile, offline, senza LLM.

**Acceptance Scenarios**:

1. **Given** più pagine toccate nello stesso step con ≥2 backlink incrociati nuovi e 0 nuove pagine
   `concepts/`/`tech/`, **When** l'agente esegue l'operazione, **Then** quell'insieme compare tra i
   candidati a distillazione (JSON + summary).
2. **Given** uno stato-wiki che non soddisfa l'euristica, **When** l'operazione gira, **Then** non produce
   candidati spuri (nessun falso «entità non distillata»).
3. **Given** l'operazione, **When** gira, **Then** non invoca alcun LLM e non crea/modifica pagine (sola
   lettura, il giudizio resta all'agente).

---

### User Story 2 - Lo skip diventa visibile (dichiarazione forzata) (Priority: P1)

La chiusura di ogni step significativo **deve dichiarare** l'esito dei passi di giudizio: una riga
esplicita `Rituale: record ✅ · distill: <verdetto> · lint: <verdetto>`. Anche un verdetto «non serve» va
**dichiarato**, mai omesso. Un passo saltato diventa un'assenza *visibile*, non silenziosa.

**Why this priority**: è ciò che rende il fallimento **loud** (Principio XII). Il danno reale (contraddizione
nell'EXEC per un'intera sessione) è passato proprio perché nulla forzava la dichiarazione.

**Independent Test**: una chiusura di step priva della riga di dichiarazione (o con distill/lint omessi) è
**non conforme** al contratto rituale; una con i tre verdetti espliciti è conforme. Verificabile leggendo
la chiusura.

**Acceptance Scenarios**:

1. **Given** un step significativo chiuso, **When** manca la riga di dichiarazione o distill/lint non hanno
   verdetto, **Then** lo step non è «chiuso» secondo il contratto (il gap è visibile).
2. **Given** un verdetto «non serve» per distill/lint, **When** è **dichiarato** esplicitamente, **Then** la
   chiusura è conforme (l'assenza è una scelta dichiarata, non un'omissione).

---

### User Story 3 - I candidati a drift alimentano il lint (Priority: P2)

L'operazione elenca anche i **candidati a drift** — pagine che potrebbero essersi scollegate dalla realtà
del repo — come **candidati deterministici** che l'agente poi giudica col lint semantico. Il tool **non**
esegue il lint semantico (resta giudizio); fornisce solo la lista da guardare.

**Why this priority**: complementa US1 sul lato-lint; utile ma il nucleo anti-skip regge anche con la sola
dichiarazione forzata (US2) e la scoperta distill (US1).

**Independent Test**: dato un segnale strutturale di possibile drift (definito in design), la pagina compare
tra i candidati a drift; il tool non emette alcun verdetto semantico su di essa.

**Acceptance Scenarios**:

1. **Given** una pagina con un segnale strutturale di possibile drift, **When** l'operazione gira, **Then**
   la elenca come candidato a drift senza giudicarla.

---

### Edge Cases

- **Insieme di pagine dello step indeterminabile:** se il tool non riesce a determinare quali pagine
  appartengono allo step, **fallisce esplicitamente** (fail-loud) invece di restituire «0 candidati» come se
  non ci fosse nulla da distillare (che sarebbe un falso-negativo silenzioso — l'anti-pattern stesso).
- **Euristica rumorosa:** troppi candidati → l'agente li ignora; il verdetto resta all'agente, un falso
  positivo costa una dichiarazione «non serve», non una pagina spuria.
- **Dichiarazione come cerimonia vuota:** l'agente scrive «distill: non serve» senza guardare i candidati →
  mitigato dallo scaffold pre-popolato che mette i candidati *davanti* al verdetto.
- **Deriva D↔N:** tentazione di far giudicare al tool (semantic lint) → vietato; il tool si ferma ai
  candidati.

## Requirements *(mandatory)*

### Functional Requirements

<!-- Tracciano REQ-001..011 di requirements.md. -->

- **FR-001**: Il wiki-tooling MUST offrire un'operazione **deterministica e offline (no LLM)** che elenca
  **candidati a distillazione** per il lavoro di uno step (REQ-001).
- **FR-002**: La rilevazione MUST basarsi **solo su segnali strutturali** del wiki (pagine cambiate insieme,
  backlink incrociati nuovi, assenza di nuova pagina `concepts/`/`tech/`), senza giudizio semantico (REQ-002).
- **FR-003**: L'operazione MUST elencare anche i **candidati a drift** (pagine da far giudicare col lint),
  **senza** eseguire il lint semantico (REQ-003).
- **FR-004**: L'operazione MUST emettere un contratto **JSON** (`--json`) e un **summary umano**, coerente con
  gli altri sottocomandi `sertor-wiki-tools` (REQ-004).
- **FR-005**: L'operazione MUST essere **host-agnostica**: scope/tassonomia da `wiki.config.toml`, nessuna
  assunzione sulla struttura del progetto (REQ-005, Principio X).
- **FR-006**: Se l'insieme di pagine dello step non è determinabile, l'operazione MUST **fallire in modo
  esplicito** (fail-loud), non restituire un insieme vuoto silenzioso (REQ-006, Principio XII).
- **FR-007**: Il contratto rituale distribuito (blocco host-facing + playbook) MUST richiedere che la chiusura
  di ogni step significativo emetta la **dichiarazione** con i verdetti di `record`/`distill`/`lint` (REQ-007).
- **FR-008**: Se la chiusura omette il verdetto di `distill` o `lint` (invece di dichiararlo, «non serve»
  incluso), allora lo step **non** conta come chiuso (REQ-008).
- **FR-009**: Dove l'operazione di parte 1 è disponibile, il suo output SHOULD includere uno **scaffold di
  dichiarazione** pre-popolato coi candidati (REQ-009).
- **FR-010**: Il contratto di dichiarazione e l'operazione MUST essere **distribuibili via installer** (tool
  bundlato + `claude-md-block`/playbook, parità Claude/Copilot, guardia sync), non dogfood-only (REQ-010).
- **FR-011**: L'operazione MUST NOT invocare alcun LLM né decidere (crea-pagina/corregge); **solo candidati**
  — l'agente giudica (REQ-011, D↔N).

### Key Entities

- **Report dei candidati a distillazione** — insiemi di pagine (con i segnali strutturali che li hanno
  qualificati) prodotti dall'operazione; input al giudizio dell'agente.
- **Report dei candidati a drift** — pagine segnalate come possibilmente scollegate dalla realtà, da
  giudicare col lint semantico.
- **Riga di dichiarazione rituale** — `Rituale: record <v> · distill: <v> · lint: <v>`, l'artefatto che rende
  lo skip visibile a fine step.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dato uno stato-wiki che soddisfa l'euristica, l'operazione **elenca** i candidati a
  distillazione **senza** dipendere dalla memoria dell'agente; dato uno stato che non la soddisfa, **0**
  candidati spuri (OB-1).
- **SC-002**: **Nessuna** chiusura di step significativo conta come completa senza la **riga di dichiarazione**
  con verdetto esplicito per record/distill/lint (OB-2).
- **SC-003**: L'operazione **non** invoca alcun LLM e **non** modifica alcuna pagina (sola lettura); il
  giudizio resta nel flusso principale (OB-3, D↔N).
- **SC-004**: L'operazione gira su un **ospite diverso** (config da `wiki.config.toml`) senza modifiche al suo
  corpo, ed è **distribuita** dall'installer (tool + blocco/playbook) con parità Claude/Copilot (OB-4).
- **SC-005**: Su un insieme di pagine **indeterminabile**, l'operazione **fallisce esplicitamente** invece di
  restituire «0 candidati» (nessun falso-negativo silenzioso).

## Assumptions

- **A-1** *(confermata in clarify 2026-07-12, DA-1)*: il tool determina «le pagine dello step» via **git
  diff rispetto a una base** (branch corrente vs `master`/merge-base, o un range git esplicito) — preciso
  (uno step/feature ≈ un branch), deterministico, offline (git locale). Assume che il progetto usi git (vero
  per gli ospiti Sertor).
- **A-2** *(confermata in clarify 2026-07-12, DA-2)*: l'operazione è un **nuovo sottocomando** dedicato (es.
  `ritual-check`) con output JSON+summary proprio, non un'estensione di `scan` (superficie chiara,
  distribuzione esplicita, richiamabile nel rituale).
- **A-3** *(design, → plan DA-3)*: quali segnali *strutturali* costituiscono il «candidato a drift» (es.
  `updated` più vecchio dell'ultima modifica git; pagina toccata da change di codice della stessa area) è
  deciso in **plan/research**; confine netto: **niente giudizio semantico** nel tool.
- **A-4** *(confermata in clarify 2026-07-12, DA-4)*: il tool **emette lo scaffold** di dichiarazione con i
  candidati pre-popolati (parte 3 agganciata all'output di parte 1) — mette i candidati davanti al verdetto,
  difficile scrivere «non serve» senza guardarli.
- **A-5**: la dichiarazione forzata è un **contratto di comportamento** dell'agente (non hook-enforced: è
  giudizio, a differenza dei passi meccanici di FEAT-011); la sua leva è avere un **artefatto deterministico**
  a cui rispondere.
- **A-6**: MVP = parte 1 + parte 3; parte 2 (wiki-curator restituisce sempre candidati) e parte 4
  (propagazione ai moduli `ops/*.md`) sono **fuori scope** (follow-up).
