# Checklist di qualità — Specifica `084-speclift-self-host`

Validazione della `spec.md` (speclift FEAT-001 — self-hosting/dogfooding di SpecLift su Sertor). Esito per
voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** —
  il valore («Sertor genera requisiti EARS ancorati e riverificati dai propri changeset, alimentando il
  lint semantico del rituale di step») e il perché (self-host prima di distribuire; onestà doc↔codice)
  sono espliciti; i requisiti parlano di esiti osservabili (bundle non vuoto, report riverificato, exit 3
  azionabile, suite verde, core invariato).
- [x] **C2** Nessun dettaglio implementativo prescrittivo nei requisiti. **PASS** — le tre scelte di *come*
  (modalità di vendoring, `jsonschema` runtime→dev, meccanismo di configurazione del vehicle) sono
  confinate nelle «Forche di design» DA-D-1/2/3; i requisiti fissano solo il comportamento (vehicle alla
  root, provenienza tracciata, fail-loud azionabile).
- [x] **C3** I riferimenti a file/simboli ancorano, non prescrivono il come. **PASS** — il riquadro
  «Ancoraggio all'esistente» cita `rag_sertor.py:86`, `config.py:27`, exit 3, `requires-python >=3.12`,
  `StrEnum` come fatti verificati dal recon che ancorano i requisiti, senza imporre un edit.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..019 hanno esito osservabile (membro del
  workspace risolvibile / nota di provenienza ispezionabile / vehicle alla root / raggiungibilità senza
  flag / exit 3 + messaggio azionabile / skill depositata host-agnostica / suite verde / core invariato /
  nessun ciclo / bundle non vuoto / report riverificato / discrepanza dichiarata / pin riconciliato con
  verifica su 3.11).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US9
  (evidenza ancorata end-to-end, core invariato + no cicli, fail-loud azionabile, vehicle alla root, suite
  verde, provenienza, skill host-agnostica, onestà doc↔codice, riconciliazione Python) hanno ciascuna
  Independent Test e acceptance G/W/T.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — vehicle non riconfigurato
  (US3/US4, R-3), indice stantio/assente + NFR-4, costrutto 3.12-only irriducibile (US9, R-2), deriva del
  vendoring (US6, R-4), conflitto pytest/lint (US5, R-5), àncora non verificata dal moat (US1).

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (bundle non vuoto su commit
  dogfood), CS-2 (report riverificato, nessuna àncora silenziata), CS-3 (git diff vuoto + grep zero import),
  CS-4 (suite verde in `uv run pytest`), CS-5 (`uv sync --all-packages` senza cicli), CS-6 (exit 3 +
  messaggio), CS-7 (nota di provenienza + dichiarazione doc↔codice).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti
  osservabili (bundle/report, diff/grep, suite verde, exit code); i riferimenti a `uv`/`pytest`/`git`/
  `sertor-rag` sono vehicle e comandi di verifica del workspace, non scelte implementative interne.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** —
  CS-1 + CS-2 (il ciclo bundle→autoring→assemble su un commit reale di Sertor produce un report con àncore
  riverificate) sono la prova diretta che il self-host funziona nel repo Sertor.
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..7 della spec mappano CS-1..6 dei
  requirements (self-host, report verificato, core invariato, suite verde, no cicli, fail-loud) più
  l'onestà doc↔codice (REQ-019); FR-001..019 coprono REQ-001..019 e NFR-1..6.

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: vendoring + provenienza, vehicle
  alla root, fail-loud RAG, skill del dogfood, test integrati, verifica end-to-end, onestà doc↔codice,
  riconciliazione Python. Fuori: distribuzione su ospiti (FEAT-002), IT→EN (E12), SpecAudit/Debrief/Guida
  al test (FEAT-003/004/005), PR upstream, modifiche al core, automazione nel rituale, il *come* di
  dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — i rinvii reali hanno già
  casa: distribuzione = **FEAT-002**, famiglia futura = **FEAT-003/004/005** (backlog epica `speclift`),
  IT→EN = **E12**; nessun rinvio reale resta sepolto in `specs/`.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — `packages/speclift`, nota di
  provenienza, vehicle configurato per la root, skill del dogfood, errore RAG-unavailable exit 3, suite
  vendorata, legame RAG reale (un solo comando CLI) — coerenti con FR e US.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato — con **onestà** sul contributo
  indiretto. **PASS** — il riquadro dichiara che SpecLift è periferico al differenziatore code+doc (non
  tocca engine/hit-rate/MRR/fusion coverage) ma rafforza la veridicità/freschezza del contesto tenendo i
  documenti onesti rispetto al codice (lint semantico del rituale di step).
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVA / vendoring nuovo
  membro del workspace, ZERO runtime di `sertor_core`»: nessuna porta/adapter/engine/comando al core,
  nessun LLM interno alla CLI, consumo RAG solo via vehicle CLI subprocess.
- [x] **C16** Principi riflessi: X (host-agnostico — skill host-agnostica, vehicle configurabile), XI (zero
  `sertor_core`, vehicle-only), additività/non-regressione (workspace risolve, core invariato). **PASS** —
  RNF-1 (vehicle-only), RNF-3 (additività workspace), RNF-6 (determinismo sandwich), RNF-7 (core invariato),
  FR-012/013 (core invariato + no cicli).

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese sono codificate come **RISOLTE**. **PASS** — vendoring come
  `packages/speclift`, scope solo self-host, core invariato, onestà doc↔codice, IT invariata, nessuna
  automazione sono nel riquadro «Decisioni di scope — FISSATE»; le tre forche di *come* restano DA-D-1/2/3
  per il plan.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo forche di *come*
  (DA-D-1 modalità di vendoring, DA-D-2 collocazione `jsonschema`, DA-D-3 meccanismo del vehicle), che non
  cambiano lo scope; la condizionalità del pin 3.12 (FR-019) è un ramo dichiarato, non un chiarimento
  aperto.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente: le
decisioni di scope sono fissate a monte (vendoring, solo self-host, core invariato, onestà doc↔codice, IT
invariata) e le forche residue DA-D-1/2/3 sono questioni di *come* (modalità di vendoring, `jsonschema`
runtime/dev, meccanismo del vehicle), risolvibili in plan. Pronta per `/speckit-plan` (`/speckit-clarify`
opzionale e non necessaria).
