# Checklist di qualità — Specifica `079-altitude-claude-md`

Validazione della `spec.md` (E10-FEAT-021 epica debito-tecnico). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il problema reale (~208 righe always-on che mescolano direttive standing e dettaglio lookup-on-demand; «How to invoke» triplicata e già parzialmente divergente) e il valore («più budget di contesto per il lavoro reale» + «una sola fonte di verità per l'invocazione»); i requisiti parlano di riduzione a direttiva+pointer, fonte unica, raggiungibilità del pointer, non di sintassi di editing del Markdown o struttura interna del kit.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — il *dove* del reference (asset nuovo vs sezione di uno esistente), il criterio quantitativo per «breve», la conferma formale sul blocco SDLC e la forma della guardia sono confinati a Forche di design (DA-D-r1..r4); l'uso delle guardie esistenti e del meccanismo di blocco a marker è ancoraggio all'esistente, non prescrizione di codice nuovo.
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: i tre asset canonici, le tre copie di «How to invoke» con range di righe, il wiring a marker (`install_*.py`), le tre guardie (`test_assets_copilot_guard.py`, `test_assets_sync.py`, `test_assets_cli_invocation.py`) — accertati e usati per ancorare i requisiti agli asset/meccanismi reali, non per imporre il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..016 hanno esito osservabile (blocchi a sola direttiva standing / pointer per nome / nessun pointer a asset non depositato / blocchi host-agnostici / fonte unica «How to invoke» / asset canonico host-agnostico / raggiungibilità per capability / guided-setup e wiki-playbook referenziano non duplicano / parità+closure verde / sync verde / guardia non-reintroduzione / additività lifecycle / contenuto minimo per blocco wiki/RAG/SDLC).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US7 (blocchi più compatti, fonte unica «How to invoke», nessun pointer rotto, nessuna direttiva persa, parità host-agnostica, sync dogfood↔bundle, guardia di non-reintroduzione).
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — install solo-wiki/solo-governance senza RAG, blocco SDLC privo di «How to invoke», divergenza già esistente tra le tre copie, pointer per nome vs percorso, footgun `uv run` nudo sul nuovo asset, CLAUDE.md di radice fuori ambito, rischio over-riduzione mitigato da REQ-014/015/016.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (misura righe/byte + assenza sezioni di dettaglio), CS-2 (conteggio occorrenze della sezione autonoma), CS-3 (guardia di closure offline), CS-4 (contenuto minimo REQ-014/015/016 + raggiungibilità pointer), CS-5 (esegui `test_assets_copilot_guard.py`), CS-6 (esegui `test_assets_sync.py`).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (altitude inferiore, sezione in una sola sede, pointer che risolvono, direttive preservate, zero leak host-specifici, sync verde), non di API Python specifiche o struttura interna del kit; in particolare nessuna soglia numerica arbitraria (rinviata a FEAT-024).
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (altitude misurabilmente ridotta) + CS-2 (fonte unica «How to invoke») sono la prova diretta dei due valori (meno contesto always-on sprecato + una sola fonte di verità per l'invocazione).
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..6 della spec mappano 1:1 CS-1..6 dei requirements; coprono REQ-001..016 (FR-001..016) e i due obiettivi (altitude ridotta + dedup «How to invoke»).

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: riduzione dei tre `claude-md-block*.md`, sostituzione delle copie inline in `guided-setup` e `wiki-playbook`, reference unico «How to invoke», re-sync dogfood `.claude/`, guard tests (closure + parità + sync + non-reintroduzione). Fuori: CLAUDE.md di radice (DA-1), pulizia stile (FEAT-022), stub Copilot (FEAT-023), budget altitude CI (FEAT-024), installer/vehicle, codice core, contenuto skill oltre «How to invoke».
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — nota «Tracciamento dello scope»: pulizia stile → FEAT-022; stub `assets/copilot/` → FEAT-023; budget altitude CI → FEAT-024. Nessun rinvio reale sepolto in `specs/`.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — blocco a marker ridotto, asset canonico «How to invoke», pointer per nome, copia inline da centralizzare, guardie di asset, copie dogfood `.claude/`.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: il budget di contesto è finito, ~208 righe always-on di dettaglio diluiscono il segnale e sottraggono token al lavoro reale; ridurre a «direttiva + pointer» e centralizzare l'invocazione protegge la qualità del contesto reso all'agente; D↔N (igiene meccanica degli asset senza LLM; il giudizio load-bearing-vs-lookup fissato da REQ-014/015/016); complementa FEAT-018.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO / igiene host-facing, ZERO codice di core»: solo asset `.md` + copie dogfood + guardie; zero `sertor_core`; comportamento osservabile = blocchi più corti, stesso wiring a marker, dettaglio raggiungibile on-demand.
- [x] **C16** Principi riflessi: X (host-agnostico — pointer per nome, zero `.claude/`/slash-command/nomi-Claude, parità Copilot), XI (vehicle-only, no `sertor_core`, no LLM nell'igiene), XII (fail-loud — pointer mai rotto, guardia di closure che cattura il vicolo cieco), VI (non-regressione installabilità + suite verdi). **PASS** — FR-004/006/RNF-2, RNF-1, FR-003/RNF-5, RNF-3/RNF-4.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese con l'utente sono codificate come **RISOLTE**, non riaperte. **PASS** — DA-1 (CLAUDE.md di radice fuori ambito) e DA-2 (strategia = direttiva+pointer + fonte unica) marcate RISOLTE; nessuna riapertura.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-r1 dove vive il reference; DA-D-r2 criterio qualitativo per «breve» senza soglia; DA-D-r3 conferma formale blocco SDLC; DA-D-r4 forma della guardia), che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare
all'utente: le decisioni di scope (CLAUDE.md di radice fuori ambito; strategia = direttiva+pointer +
fonte unica «How to invoke» host-agnostica) sono risolte con decisioni vincolanti dell'utente, codificate
come fissate (DA-1/DA-2). Le forche residue DA-D-r1..r4 sono questioni di *come* (dove vive il reference;
criterio qualitativo per «breve»; conferma formale blocco SDLC; forma della guardia di
non-reintroduzione), risolvibili in plan. Non sono emerse ambiguità genuinamente nuove. Pronta per
`/speckit-plan` (`/speckit-clarify` opzionale e non necessaria).
