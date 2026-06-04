# Feature Specification: Lint semantico del wiki (FEAT-007 — estensione semantica)

**Feature Branch**: `spec/005-wiki-manutenzione` (estende FEAT-007, parte semantica)
**Created**: 2026-06-04
**Status**: Draft
**Deriva da**: `requirements/sertor-core/wiki-manutenzione/requirements.md` (Gruppo H, REQ-070..098)

## Sintesi

Il lint **strutturale** (Gruppi A–G, già realizzato) verifica solo la *forma* del wiki e dà un
"verde ingannevole": il wiki può essere formalmente sano ma descrivere **funzionalità obsolete**.
Questa feature aggiunge il **lint semantico** assistito da LLM, che giudica la **sostanza** del wiki
confrontandola con il **codice reale** (corpus di dogfooding + working tree) e con la **coerenza
interna** tra pagine, **a livello di singola affermazione**. Dove i problemi riguardano pagine
**generate dallo strumento**, propone (e, assistito, applica) correzioni; le pagine **curate a mano**
ricevono solo proposte. È pensato come **trigger pre-commit/pre-push**, reso pratico
dall'**incrementalità git-driven**.

## User Scenarios & Testing

### User Story 1 — Rilevazione semantica (obsolescenza, contraddizioni, lacune, sommari) [P1] 🎯 MVP

Come maintainer voglio che il lint, con un LLM configurato, mi segnali **dove il wiki non è più vero
o coerente** rispetto al codice, indicando l'**affermazione precisa**, così da fidarmi della
documentazione ufficiale.

**Perché P1**: è il cuore eseguibile e la ragione della feature; senza, il "verde" resta ingannevole.

**Test di accettazione**:
1. **Obsolescenza** — Data una pagina che afferma una funzionalità non presente nel codice fornito,
   **Quando** si esegue il lint semantico, **Allora** è prodotta una issue `obsolete` che cita la
   pagina e la **frase** divergente.
2. **Contraddizione semantica** — Date due pagine con affermazioni in conflitto nel merito, **Quando**
   si esegue, **Allora** è prodotta una issue `semantic_contradiction` con le pagine coinvolte.
3. **Lacuna** — Data un'entità presente nel codice ma non documentata, **Quando** si esegue, **Allora**
   è prodotta una issue `coverage_gap`.
4. **Sommario stantio** — Dato un sommario di indice/roadmap non più aderente, **Quando** si esegue,
   **Allora** è prodotta una issue `stale_summary`.
5. **Granularità** — Ogni issue di obsolescenza/contraddizione identifica la **claim** specifica
   (non solo la pagina).
6. **Severità & gate** — Ogni issue ha una **severità**; il report ha un esito **pass/fail** secondo
   una **soglia configurabile**.
7. **Degrado senza LLM** — **Se** nessun LLM è configurato, **Allora** il lint semantico è **saltato
   senza errore** e il lint strutturale resta operativo.

### User Story 2 — Provenienza delle pagine [P1]

Come sistema devo sapere quali pagine sono **generate** dallo strumento e quali **curate a mano**, per
non riscrivere mai il lavoro manuale.

**Perché P1**: prerequisito di sicurezza dell'auto-fix; va in piedi prima di qualunque scrittura.

**Test di accettazione**:
1. **Auto-marcatura** — Quando `distill_artifact`/`record` produce una pagina, questa è marcata
   **generated**.
2. **Default sicuro** — Una pagina priva di marcatore è trattata come **curated**.
3. **Riclassifica** — Se una pagina **generated** viene modificata a mano, diventa **curated**.
4. **Classificazione iniziale** — È possibile una passata che marca le pagine prodotte dalla tooling
   come generated e lascia curate quelle a mano (roadmap sempre curated).

### User Story 3 — Verifica incrementale git-driven [P2]

Come maintainer voglio che, dopo il primo baseline completo, il lint ricontrolli **solo le pagine
collegate alle entità cambiate** nei commit/nel change set, così è veloce a ogni commit.

**Test di accettazione**:
1. **Baseline** — Senza watermark, sono verificate tutte le pagine.
2. **Incrementale** — Con watermark, sono verificate solo le pagine associate alle entità del change
   set (staged/working pre-commit; commit dal watermark altrimenti).
3. **Watermark** — Il commit dell'ultimo lint completato è persistito.
4. **Fallback** — Senza git/watermark valido → baseline completo, segnalato.
5. **No-op** — Se il change set non tocca pagine, il run è un no-op rapido.

### User Story 4 — Auto-fix assistito su pagine generate [P2]

Come maintainer voglio che lo strumento **proponga** (e, assistito, **applichi**) correzioni — incluse
**cancellazioni** di pagine generate obsolete — **solo** sulle pagine generate, come **diff
revisionabile**.

**Test di accettazione**:
1. **Proposta** — Per ogni issue correggibile su pagina generated, è prodotta una proposta (testo +
   pagina + motivazione).
2. **Solo generate** — Una pagina curated produce **solo proposta**, mai scrittura/cancellazione.
3. **Cancellazione** — Una pagina generated obsoleta e non aggiornabile è proposta per la
   **cancellazione** (revisionabile).
4. **Chirurgico** — La modifica proposta tocca la **claim** interessata (diff minimo).

### User Story 5 — Gate pre-commit/pre-push [P2]

Come maintainer voglio che il lint semantico+auto-fix scatti **prima del commit/push** (a monte del
configuration-manager) e **blocchi** sopra una soglia di severità, con **override** esplicito.

**Test di accettazione**:
1. **Trigger a monte** — Le correzioni alle pagine generate entrano nello **stesso commit** imminente.
2. **Blocco** — Con issue aperte ≥ soglia, l'operazione è **bloccata**; sotto soglia → warning.
3. **Override** — Con override esplicito, l'operazione procede ed è **registrata**.

### Edge cases
- Wiki senza LLM → solo strutturale (US1.7).
- Corpus stantio → re-index incrementale del change set prima del confronto; fallback lettura working
  tree con segnalazione.
- Allucinazione "correttiva" su contenuto corretto → auto-fix solo su generate + diff revisionabile +
  soglia/gate.
- Rename di entità non rilevato → fallback baseline / baseline periodico.

## Requirements

### Functional (mappati ai requisiti EARS)
- **FR-001** Rilevazione per-claim di obsolescenza vs codice (REQ-071/098).
- **FR-002** Rilevazione contraddizioni semantiche tra pagine (REQ-072).
- **FR-003** Rilevazione lacune di copertura semantiche (REQ-073).
- **FR-004** Rilevazione sommari/pagine vive stantii (REQ-074).
- **FR-005** Riferimento di verità duplice: coerenza interna + codice via retrieval/working tree (REQ-075).
- **FR-006** Severità per issue + esito pass/fail con soglia configurabile (REQ-082).
- **FR-007** Degrado senza LLM, strutturale sempre operativo (REQ-081).
- **FR-008** Limiti di costo LLM + report di copertura (no troncamento silenzioso) (REQ-083).
- **FR-009** Idempotenza della **rilevazione** (non del testo generato) (REQ-084).
- **FR-010** Provenienza pagine: marcatore, auto-marcatura, default curated, riclassifica, classificazione iniziale (REQ-076/077/077b/077c/086).
- **FR-011** Verifica incrementale git-driven + watermark + mappa entità↔pagine + fallback completo (REQ-087..091).
- **FR-012** Trigger pre-commit/pre-push a monte del configuration-manager; no-op se irrilevante (REQ-092/093).
- **FR-013** Gate: blocco sopra soglia + override tracciato (REQ-094/095).
- **FR-014** Re-index incrementale del change set prima del confronto, fallback working tree (REQ-096/097).
- **FR-015** Auto-fix assistito: proposta + applicazione su pagine generate (riscrittura/cancellazione) come diff (REQ-078/079/080/085).
- **FR-016** Osservabilità: log strutturati incl. conteggio chiamate LLM e copertura (REQ-051/NFR-06).

### Key Entities
- **SemanticIssue**: `kind` {obsolete, semantic_contradiction, coverage_gap, stale_summary}, `page`,
  `claim` (frase/paragrafo), `severity`, `detail`, `evidence` (riferimento al codice).
- **SemanticReport**: lista di SemanticIssue + esito pass/fail (soglia) + copertura (coperto/saltato).
- **Provenance**: per pagina, `generated` | `curated` (marcatore nel frontmatter).
- **FixProposal**: issue → testo proposto / cancellazione, pagina bersaglio, motivazione (solo generate).
- **Watermark**: commit git dell'ultimo lint completato.

## Success Criteria
- **SC-001** Su un wiki con una pagina deliberatamente obsoleta vs codice, il lint la individua citando la claim. (US1)
- **SC-002** Senza LLM, il lint semantico è saltato senza errore e lo strutturale resta verde/rosso come prima. (US1.7)
- **SC-003** Le pagine curate non vengono mai scritte/cancellate dall'auto-fix; solo proposte. (US4.2)
- **SC-004** Re-run su wiki+codice invariati → stesso insieme di issue/severità. (US1, FR-009)
- **SC-005** Il run sul **wiki di produzione attuale** produce un report semantico leggібile con eventuali obsolescenze/lacune reali. (payoff)

## Scope dell'implementazione (questo ciclo)
- **MVP (P1, completo + test)**: US1 (rilevazione, in modalità **baseline completo**, sufficiente per il
  primo run senza watermark) + US2 (provenienza). Riusa `LLMProvider`, la facade di retrieval e le
  convenzioni.
- **Incrementale (P2, per quanto pulito)**: US4 nella forma **proposta** (FR-015 senza scrittura
  automatica), US3/US5 specificati; la scrittura su working tree, l'hook pre-commit e il watermark
  git completo sono il passo successivo, dichiarati nei task.

## Tracciabilità
US1→FR-001..009/016 · US2→FR-010 · US3→FR-011/014 · US4→FR-015 · US5→FR-012/013.
