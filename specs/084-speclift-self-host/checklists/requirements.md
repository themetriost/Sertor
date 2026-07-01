# Checklist di qualità — Specifica `084-speclift-self-host` (rigenerata: design MCP-skill)

Validazione della `spec.md` (speclift FEAT-001 — self-hosting/dogfooding di SpecLift su Sertor, retrieval
via **tool MCP `search_code` dentro una skill**, non via CLI). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** —
  il valore («Sertor genera requisiti EARS ancorati e riverificati dai propri changeset, alimentando il
  lint semantico del rituale di step») e il perché (self-host prima di distribuire; Sertor pubblica l'MCP
  perché i consumatori esterni non dipendano dalla CLI; onestà sulla divergenza) sono espliciti; i
  requisiti parlano di esiti osservabili (bundle non vuoto, report riverificato, fail-loud esplicito, suite
  verde, core invariato).
- [x] **C2** Nessun dettaglio implementativo prescrittivo nei requisiti. **PASS** — le tre scelte di *come*
  (modalità di vendoring, `jsonschema` runtime→dev, adozione dell'Adapter B pluggable upstream) sono
  confinate nelle «Forche di design» DA-D-1/2/3; i requisiti fissano solo il
  comportamento (retrieval via `search_code`, `EvidenceLocator` alimentato con interfaccia esplicita,
  fail-loud, provenienza tracciata).
- [x] **C3** I riferimenti a file/simboli ancorano, non prescrivono il come. **PASS** — il riquadro
  «Ancoraggio all'esistente» cita `rag_sertor.py:86`, `config.py:27`, `FakeLocator`, `StrEnum`,
  `requires-python >=3.12` come fatti verificati dal recon che ancorano i requisiti; l'adapter CLI è citato
  come **fatto di provenienza non usato**, non come edit da imporre.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..020 hanno esito osservabile (membro del
  workspace risolvibile / nota di provenienza ispezionabile / no CLI / evidenza solo via `search_code` /
  `EvidenceLocator` alimentato con interfaccia esplicita / skill depositata host-agnostica che orchestra il
  retrieval / fail-loud su MCP-indice assente / fail-loud su evidenza malformata / suite verde / core
  invariato / no ciclo / bundle non vuoto / report riverificato / divergenza dichiarata + feedback / pin
  riconciliato con verifica su 3.11).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US10
  (end-to-end MCP→bundle→assemble; retrieval via MCP non CLI + interfaccia evidenza; core invariato + no
  cicli; fail-loud MCP/indice; fail-loud evidenza malformata; suite verde; provenienza; skill
  host-agnostica che orchestra; onestà divergenza + feedback; riconciliazione Python) hanno ciascuna
  Independent Test e acceptance G/W/T.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — path CLI tentato per errore
  (US2, R-2), MCP/indice stantio/assente + NFR-4, evidenza fornita malformata (US5, R-3), costrutto
  3.12-only irriducibile (US10, R-4), deriva del vendoring (US7, R-5), conflitto pytest/lint (US6, R-6),
  àncora non verificata dal moat (US1, moat sul filesystem).

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (bundle non vuoto via MCP su
  commit dogfood), CS-2 (report riverificato, nessuna àncora silenziata), CS-3 (git diff vuoto + grep zero
  import), CS-4 (suite verde in `uv run pytest`), CS-5 (`uv sync --all-packages` senza cicli), CS-6
  (fail-loud su MCP/indice assente **o** evidenza malformata), CS-7 (provenienza + divergenza dichiarata +
  feedback).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti
  osservabili (bundle/report, diff/grep, suite verde, fail-loud); i riferimenti a `uv`/`pytest`/`git`/
  `search_code`/`sertor-rag` sono vehicle e comandi di verifica del workspace, non scelte implementative
  interne.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** —
  CS-1 + CS-2 (il ciclo localizza-evidenza-via-MCP → bundle → autoring → assemble su un commit reale di
  Sertor produce un report con àncore riverificate) sono la prova diretta che il self-host funziona nel repo
  Sertor col nuovo design.
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..7 della spec mappano CS-1..6 dei
  requirements (self-host via MCP, report verificato, core invariato, suite verde, no cicli, fail-loud MCP +
  evidenza) più l'onestà sulla divergenza (REQ-019/020); FR-001..020 coprono REQ-001..020 e NFR-1..6.

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: vendoring + provenienza, retrieval
  via MCP dentro la skill (no CLI a runtime, Adapter A dormiente), interfaccia evidenza esplicita, fail-loud (MCP/indice +
  evidenza), skill del dogfood che orchestra, test integrati, verifica end-to-end, onestà sulla divergenza +
  feedback, riconciliazione Python. Fuori: distribuzione su ospiti (FEAT-002), IT→EN (E12),
  SpecAudit/Debrief/Guida al test (FEAT-003/004/005), PR upstream, modifiche al core, automazione nel
  rituale, chiusura del gap code-graph, il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — distribuzione = **FEAT-002**,
  famiglia futura = **FEAT-003/004/005** (backlog epica `speclift`), IT→EN = **E12**, convergenza upstream =
  **feedback a Sinthari** (`input-other-agents`); nessun rinvio reale resta sepolto in `specs/`.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — `packages/speclift` (Adapter A
  dormiente + Adapter B `ProvidedEvidenceLocator`), nota di provenienza, adapter `EvidenceLocator` (Adapter B)
  alimentato, interfaccia evidenza agente→SpecLift (`located.json` upstream), skill del dogfood (due stadi di
  giudizio), fail-loud MCP/indice, fail-loud evidenza malformata, suite vendorata, legame RAG reale = tool
  MCP `search_code` via Adapter B pluggable upstream — coerenti con FR e US.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato — con **onestà** sul contributo
  indiretto. **PASS** — il riquadro dichiara che SpecLift è periferico al differenziatore code+doc (non
  tocca engine/hit-rate/MRR/fusion coverage) ma rafforza la veridicità/freschezza del contesto tenendo i
  documenti onesti rispetto al codice; aggiunge che il self-host consuma il contratto d'integrazione MCP
  come previsto per i consumatori esterni.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVA / vendoring nuovo
  membro del workspace, ZERO runtime di `sertor_core`»: nessuna porta/adapter/engine/comando al core,
  nessun LLM interno alla CLI, consumo RAG solo via vehicle **MCP** (`search_code`), mai CLI; più il riquadro
  «Cambio di decisione» che dichiara il superamento dell'approccio CLI.
- [x] **C16** Principi riflessi: X (host-agnostico — skill host-agnostica, MCP come contratto d'integrazione),
  XI (zero `sertor_core`, vehicle-only via MCP), XII (fail-loud su MCP/indice + evidenza malformata),
  additività/non-regressione (workspace risolve, core invariato). **PASS** — RNF-1 (vehicle-only MCP), RNF-3
  (additività workspace), RNF-6 (determinismo sandwich + deviazione dichiarata a due stadi), RNF-7 (core
  invariato), FR-009/010 (fail-loud), FR-012/013 (core invariato + no cicli).

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese sono codificate come **RISOLTE**. **PASS** — vendoring come
  `packages/speclift`, retrieval via MCP dentro la skill (no CLI a runtime, Adapter A dormiente), deviazione
  dichiarata dal sandwich a un solo stadio (scelta upstream), scope solo self-host, core invariato, onestà
  sul retrieval MCP + recepimento del feedback, IT invariata, nessuna automazione sono nel riquadro
  «Decisioni di scope — FISSATE»; le tre forche di *come* restano DA-D-1/2/3 per il plan; la vecchia forca
  «vehicle CLI» è marcata SUPERATA.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo forche di *come*
  (DA-D-1 modalità di vendoring, DA-D-2 collocazione `jsonschema`, DA-D-3 adozione dell'Adapter B pluggable
  upstream), che non cambiano lo scope; la condizionalità del pin 3.12 (FR-020)
  è un ramo dichiarato, non un chiarimento aperto.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente: le
decisioni di scope sono fissate a monte (vendoring, retrieval via MCP dentro la skill, no CLI a runtime,
Adapter A dormiente, deviazione dichiarata a due stadi (scelta upstream), solo self-host, core invariato,
onestà sul retrieval MCP + recepimento del feedback, IT invariata) e le forche residue DA-D-1/2/3 sono
questioni di *come* (modalità di vendoring, `jsonschema` runtime/dev, adozione dell'Adapter B pluggable
upstream), risolvibili in plan. Pronta per `/speckit-plan` (`/speckit-clarify` opzionale e non necessaria).
