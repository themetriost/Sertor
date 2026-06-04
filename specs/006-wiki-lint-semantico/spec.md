# Feature Specification: Lint semantico del wiki (FEAT-007 — estensione semantica)

**Feature Directory**: `specs/006-wiki-lint-semantico/` (estende FEAT-007, parte semantica)
**Branch**: `spec/005-wiki-manutenzione` (ospita FEAT-007 strutturale + semantico)
**Created**: 2026-06-04 · **Updated**: 2026-06-04
**Status**: Draft (scope ampliato — US3/US5/US4-scrittura ora in implementazione)
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

> **Stato dell'implementazione (questo ciclo).** Il **P1 è già implementato e testato** (US1
> rilevazione, US2 provenienza, US4 in forma *proposta*). Questa revisione della spec porta in
> **scope pieno di implementazione** le user story finora dichiarate ma rinviate: **US3** (verifica
> incrementale git-driven), **US4-scrittura** (applicazione assistita su working tree), **US5** (gate
> pre-commit/pre-push). Il P1 resta invariato.

## User Scenarios & Testing

### User Story 1 — Rilevazione semantica (obsolescenza, contraddizioni, lacune, sommari) [P1 ✅ fatto]

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

### User Story 2 — Provenienza delle pagine [P1 ✅ fatto]

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

### User Story 3 — Verifica incrementale git-driven [P2 — ora in scope] 🎯

Come maintainer voglio che, dopo il primo baseline completo, il lint ricontrolli **solo le pagine
collegate alle entità cambiate** nei commit/nel change set, così è veloce a ogni commit.

**Test di accettazione**:
1. **Baseline** — Senza watermark, sono verificate tutte le pagine (REQ-087).
2. **Incrementale** — Con watermark, sono verificate solo le pagine associate alle entità del change
   set: gli elementi **staged/working** per un'esecuzione pre-commit, oppure i **commit dal watermark**
   per pre-push/periodica (REQ-088).
3. **Watermark** — Il **commit SHA** dell'ultimo lint completato è persistito in
   `wiki/.sertor/semantic-watermark` (file di stato testuale sotto la radice wiki) (REQ-089).
4. **Mappa entità↔pagine** — L'associazione file/entità di codice → pagine wiki è **derivata** dal
   frontmatter `sources:` delle pagine e dai backlink/wikilink; un cambiamento a un file seleziona le
   pagine che lo citano (REQ-090).
5. **Fallback** — Senza git o con watermark mancante/invalido → **baseline completo**, **segnalato**
   nel report (REQ-091).
6. **No-op** — Se il change set non tocca pagine associate, il run è un **no-op rapido** (REQ-093).
7. **Re-index del change set** — Prima del confronto, il sistema tenta un **re-index incrementale** dei
   file del change set; **se non disponibile** (FEAT-009 non costruita) **degrada** leggendo i file
   direttamente dalla **working tree** e **segnalando** che il contesto d'indice può essere stantio
   (REQ-096/097).

> **Vincolo dichiarato (finding D1 dell'analyze).** Il re-index incrementale reale dipende da
> **FEAT-009** (indicizzazione incrementale), **non ancora costruita**. In questo ciclo US3 è
> implementata **solo nella modalità fallback working tree** (REQ-097), con segnalazione esplicita; il
> path "re-index vero" è predisposto ma inattivo finché FEAT-009 non esiste.

### User Story 4 — Auto-fix assistito su pagine generate [P2 — proposta ✅ fatta · scrittura ora in scope]

Come maintainer voglio che lo strumento **proponga** (✅ fatto) e, assistito, **applichi** correzioni —
incluse **cancellazioni** di pagine generate obsolete — **solo** sulle pagine generate, come **diff
revisionabile**.

**Test di accettazione (proposta — già coperti):**
1. **Proposta** — Per ogni issue correggibile su pagina generated, è prodotta una proposta (testo +
   pagina + motivazione).
2. **Solo generate** — Una pagina curated produce **solo proposta**, mai scrittura/cancellazione.
3. **Cancellazione (proposta)** — Una pagina generated obsoleta e non aggiornabile è **proposta** per la
   cancellazione (revisionabile).
4. **Chirurgico** — La modifica proposta tocca la **claim** interessata (diff minimo).

**Test di accettazione (scrittura — nuovo scope):**
5. **Applicazione su working tree** — Data una `FixProposal` `rewrite_claim` su pagina **generated**,
   **quando** si applica, **allora** il file su working tree è modificato in modo **chirurgico** (solo
   la claim) e la modifica è un **diff revisionabile** (REQ-078/079).
6. **Cancellazione applicata** — Data una proposta `delete_page` su pagina **generated**, **quando** si
   applica, **allora** il file è rimosso dalla working tree (revisionabile via git) (REQ-085).
7. **Protezione curated** — L'applicazione su una pagina **curated** è **rifiutata** (nessuna
   scrittura/cancellazione), anche se richiesta esplicitamente (REQ-080).
8. **Provenienza preservata** — Una pagina generated riscritta dall'auto-fix **resta generated** (la
   riscrittura è della tooling, non manuale).

### User Story 5 — Gate pre-commit/pre-push [P2 — ora in scope]

Come maintainer voglio che il lint semantico+auto-fix scatti **prima del commit/push** (a monte del
configuration-manager) e **blocchi** sopra una soglia di severità, con **override** esplicito.

**Test di accettazione**:
1. **Trigger a monte** — Il gate è invocabile **prima** dell'operazione di versionamento; le correzioni
   alle pagine generate possono entrare nello **stesso commit** imminente (REQ-092).
2. **No-op irrilevante** — Se il change set non tocca pagine, il gate è un **no-op rapido** (REQ-093).
3. **Blocco** — Con issue aperte ≥ soglia dopo auto-fix, l'operazione è **bloccata** (`report.ok`
   falso → **exit ≠ 0**); le issue **sotto** soglia passano con **warning** (REQ-094).
4. **Override** — Con override esplicito, l'operazione **procede** ed è **registrata** in modo
   tracciabile (escape hatch dichiarato, non bypass silenzioso) (REQ-095).

> **Confine architetturale (finding C1/A1 dell'analyze).** Il **core** resta una libreria che produce
> un `SemanticReport` con `ok` (pass/fail); il **gate vero** — exit code, blocco del commit, lettura
> dell'override — vive nel **wrapper CLI / hook**, non nel dominio. L'accesso a git passa da una
> **porta dedicata** (Principio I): il dominio non importa git direttamente.

### Edge cases
- Wiki senza LLM → solo strutturale (US1.7).
- Corpus stantio → re-index incrementale del change set prima del confronto; **fallback** lettura
  working tree con segnalazione (US3.7, REQ-096/097).
- Allucinazione "correttiva" su contenuto corretto → auto-fix solo su generate + diff revisionabile +
  soglia/gate (US4/US5).
- Rename di entità non rilevato dal diff → fallback baseline / baseline periodico (REQ-091, R-M10).
- Watermark stantio o mappa entità↔pagine incompleta → baseline forzabile + report segnala ambito
  coperto vs saltato (REQ-083/090, R-M11).

## Requirements

### Functional (mappati ai requisiti EARS)
- **FR-001** Rilevazione per-claim di obsolescenza vs codice (REQ-071/098). *(✅)*
- **FR-002** Rilevazione contraddizioni semantiche tra pagine (REQ-072). *(✅)*
- **FR-003** Rilevazione lacune di copertura semantiche (REQ-073). *(✅)*
- **FR-004** Rilevazione sommari/pagine vive stantii (REQ-074). *(✅)*
- **FR-005** Riferimento di verità duplice: coerenza interna + codice via retrieval/working tree (REQ-075). *(✅)*
- **FR-006** Severità per issue + esito pass/fail con soglia configurabile (REQ-082). *(✅)*
- **FR-007** Degrado senza LLM, strutturale sempre operativo (REQ-081). *(✅)*
- **FR-008** Limiti di costo LLM + report di copertura (no troncamento silenzioso) (REQ-083). *(✅)*
- **FR-009** Idempotenza della **rilevazione** (non del testo generato) (REQ-084). *(✅)*
- **FR-010** Provenienza pagine: marcatore, auto-marcatura, default curated, riclassifica, classificazione iniziale (REQ-076/077/077b/077c/086). *(✅)*
- **FR-011** Verifica incrementale git-driven: baseline alla prima esecuzione, incrementale con watermark, mappa entità↔pagine **derivata da `sources:`/backlink**, fallback completo segnalato (REQ-087..091). *(nuovo scope)*
- **FR-012** Trigger pre-commit/pre-push **a monte** del configuration-manager (il core è il trigger, non esegue git); no-op se irrilevante (REQ-092/093). *(nuovo scope)*
- **FR-013** Gate: blocco sopra soglia (`report.ok`→exit≠0) + warning sotto soglia + **override tracciato** (REQ-094/095). *(nuovo scope)*
- **FR-014** Re-index incrementale del change set prima del confronto **se disponibile**; altrimenti **fallback working tree segnalato** (dipendenza FEAT-009, REQ-096/097). *(nuovo scope, solo fallback in questo ciclo)*
- **FR-015** Auto-fix assistito: **proposta** (✅) **+ applicazione** su pagine generate — riscrittura chirurgica e cancellazione — come **diff revisionabile**; mai su curated (REQ-078/079/080/085). *(scrittura = nuovo scope)*
- **FR-016** Osservabilità: log strutturati incl. conteggio chiamate LLM, copertura, modalità (baseline/incrementale), fallback attivati (REQ-051/NFR-06). *(esteso)*
- **FR-017** **Porta git (`GitPort`)**: il dominio accede a git (file changed staged/working, commit dal watermark, rename) **solo** dietro una porta astratta; implementazione `subprocess` fuori dal dominio (Principio I). *(nuovo, da finding C1)*
- **FR-018** **Watermark persistente** in `wiki/.sertor/semantic-watermark` (commit SHA testuale); lettura/scrittura non distruttiva, assente → baseline (REQ-089). *(nuovo, da finding U2)*

### Key Entities
- **SemanticIssue**: `kind` {obsolete, semantic_contradiction, coverage_gap, stale_summary}, `page`,
  `claim` (frase/paragrafo), `severity`, `detail`, `evidence` (riferimento al codice). *(esistente)*
- **SemanticReport**: lista di SemanticIssue + esito pass/fail (soglia) + copertura (coperto/saltato) +
  **modalità** (baseline/incrementale) + **fallback** segnalati. *(esteso)*
- **Provenance**: per pagina, `generated` | `curated` (marcatore nel frontmatter). *(esistente)*
- **FixProposal**: issue → testo proposto / cancellazione, pagina bersaglio, motivazione (solo generate). *(esistente)*
- **FixApplication** *(nuovo)*: esito dell'applicazione di una `FixProposal` su working tree
  (rewrite chirurgico o delete), con riferimento al file modificato/rimosso; rifiuta le curated.
- **Watermark** *(formalizzato)*: commit git dell'ultimo lint completato, persistito in
  `wiki/.sertor/semantic-watermark`.
- **EntityPageMap** *(nuovo)*: associazione file/entità di codice → pagine, **derivata** dal frontmatter
  `sources:` e dai wikilink/backlink delle pagine.
- **GitPort** *(nuovo)*: porta astratta — `changed_paths(scope)` (staged/working o dal watermark),
  `head_commit()`, rilevazione rename; implementazione concreta fuori dal dominio.
- **GateOutcome** *(nuovo)*: pass | warning | blocked, con eventuale **override** registrato.

## Success Criteria
- **SC-001** Su un wiki con una pagina deliberatamente obsoleta vs codice, il lint la individua citando la claim. (US1) *(✅)*
- **SC-002** Senza LLM, il lint semantico è saltato senza errore e lo strutturale resta verde/rosso come prima. (US1.7) *(✅)*
- **SC-003** Le pagine curate non vengono mai scritte/cancellate dall'auto-fix; solo proposte. (US4.2/US4.7)
- **SC-004** Re-run su wiki+codice invariati → stesso insieme di issue/severità. (US1, FR-009) *(✅)*
- **SC-005** Il run sul **wiki di produzione attuale** produce un report semantico leggibile con eventuali obsolescenze/lacune reali. (payoff) *(✅)*
- **SC-006** Con un watermark valido e un change set che tocca **una sola** pagina, il run incrementale
  verifica **solo** quella pagina (le altre risultano non ri-verificate nel report). (US3)
- **SC-007** Applicando una `FixProposal` `rewrite_claim` su pagina generated, il file su working tree
  cambia **solo** nella claim interessata e la pagina **resta generated**. (US4-scrittura)
- **SC-008** Il gate restituisce **exit ≠ 0** quando esistono issue ≥ soglia dopo auto-fix, ed esegue
  comunque l'operazione (registrando l'override) quando l'override esplicito è fornito. (US5)

## Scope dell'implementazione (questo ciclo)
- **Già fatto (P1 + proposta)**: US1 (rilevazione baseline), US2 (provenienza), US4 in forma
  **proposta** (read-only). Restano invariati.
- **Ora in scope (P2 portato a implementazione)**:
  - **US3** verifica incrementale git-driven — baseline+incrementale, **watermark** in
    `wiki/.sertor/semantic-watermark`, **mappa entità↔pagine** derivata da `sources:`/backlink,
    **fallback** completo segnalato; re-index del change set **solo in fallback working tree** (FEAT-009
    assente — vincolo dichiarato).
  - **US4-scrittura** applicazione assistita su working tree (rewrite chirurgico + delete) solo su
    pagine generated, come diff revisionabile.
  - **US5** gate pre-commit/pre-push: il **core** espone `report.ok`; il **blocco/exit/override** vivono
    nel wrapper CLI/hook; accesso git via **`GitPort`**.
- **Fuori ambito (resta a FEAT-009/CLI)**: re-index incrementale *reale* del corpus, full re-index,
  installazione fisica dell'hook git nel repo dell'utente finale (la feature fornisce il comando/gate
  invocabile; il cablaggio dell'hook è cura della CLI/setup governance).

## Assumptions
- Il watermark vive **dentro** la radice wiki (`wiki/.sertor/`), non in `.git`, così è portabile e
  ispezionabile; la directory `.sertor/` è esclusa dall'indicizzazione del wiki.
- La mappa entità↔pagine si **deriva** (non si mantiene un indice separato): si riusano il frontmatter
  `sources:` e i wikilink già presenti (REQ-090 "maintain **or** derive").
- L'override è fornito come **parametro esplicito** al gate (flag CLI / env dedicata) e **registrato**
  in un record tracciabile (log strutturato + nota nello stato del gate); non è un bypass degli hook.
- FEAT-009 è assente: il re-index incrementale è **inattivo**; vale sempre il fallback working tree.

## Tracciabilità
US1→FR-001..009/016 · US2→FR-010 · US3→FR-011/014/016/017/018 · US4→FR-015 · US5→FR-012/013/017.
