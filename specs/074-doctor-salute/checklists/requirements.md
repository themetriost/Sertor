# Checklist di qualità — Specifica `074-doctor-salute`

Validazione della `spec.md` (E12-FEAT-001 epica usabilità). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il «ha funzionato?» deterministico che oggi manca e il perché (strumenti sparsi, `--check` inerte, problemi scoperti solo a comando fallito); niente codice/strutture imposte nei requisiti.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — schema esatto del JSON, forma del probe provider, criteri critico/warn, nome del flag di rete, rilevazione dello stantio-dopo-reindex MCP confinati a Forche di design / Fuori ambito (DA-D4/D5).
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: `validate_backend`, `index_manifest.sqlite` (mtime/hash/logic_version), `.mcp.json`, `scrub.py`, `configure._probe_live` accertati nel codice e usati per ancorare i requisiti ai segnali reali, non per imporre il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..018 hanno esito osservabile (quadro 4 aree/azionabilità, chiave env mancante/fonte unica, indice assente→fail/freschezza, provider statico/probe opt-in, MCP statico/stantio, JSON/exit-code, offline-safe/zero-segreti, sola-lettura/no-LLM, cablaggio `--check`/invarianza/degrado).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US8.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — sano, env incompleto, indice assente vs stantio, provider non config/irraggiungibile, offline con/senza flag, MCP non registrato/stantio-dopo-reindex, segreto in output, area critica singola, `--check` senza `doctor`, sola lettura.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili. **PASS** — SC-001 (4 aree in un comando), SC-004 (exit non-zero/zero), SC-005 (zero traffico di rete / skipped-unknown), SC-006 (zero segreti), SC-007 (pass/warn senza falsi positivi), SC-008 (no indicizzazione di prova), SC-012 (suite verde, nessuna nuova dipendenza).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti per-area/exit-code/rete/redazione/comportamento, non di tipi o SDK specifici.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — SC-001 + SC-002 (azionabilità) + SC-011 (`configure --check` reso vivo).
- [x] **C10** Parità con i criteri della fonte. **PASS** — SC-001..006 mappano CS-1..6 dei requisiti; SC-007/008 coprono R-1/R-2; SC-010 copre CS-6 d'epica (no LLM); SC-011 copre DA-D3.

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — auto-fix, spiegazione conversazionale, LLM nel core, probe pesanti, storicizzazione drift, distribuzione asset, e il *come* di dettaglio tutti fuori; quattro aree + opt-in rete + `configure --check` in ambito.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — debito `configure --check` ancorato a E2/FEAT-003 US5 (già nell'epica `sertor-cli`); eventuale knob env del probe rete promosso al template `.env` installer (owner E2); nota di tracciamento esplicita + clausola «installabile per costruzione, da verificare».
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — report di salute, area, esito per-area, problema diagnosticato, flag di rete opt-in, segnali riusati.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: `doctor` è il substrato deterministico di adozione/portabilità (Principio X), abilita le skill agentiche senza farle diagnosticare alla cieca; il core non chiama LLM (D↔N).
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO» (comando nuovo, sola lettura, nessun effetto collaterale; `configure --check` attiva un punto d'estensione inerte) + RNF-5, SC-012.
- [x] **C16** Principi riflessi: X (host-agnostico, config-driven), XI (vehicle-only, no import per scorciatoie), D↔N (no LLM nel core), XII (verifica reale, non claim). **PASS** — FR-004/RNF-2, FR-015/RNF-3, FR-013/RNF-4, US1/SC-002.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese con l'utente sono codificate come **RISOLTE**, non riaperte. **PASS** — DA-D1 (flag opt-in, offline-safe by default), DA-D2 (freschezza leggera sul manifest FEAT-009), DA-D3 (`--check` = sottoinsieme config che invoca `doctor`, scope esteso a `sertor`) marcate RISOLTE; 4 aree tutte nel primo taglio (provider/MCP statici); probe rete opt-in incluso.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D4 criteri critico/warn, DA-D5 forma del probe provider e rilevazione stantio-dopo-reindex MCP) per il plan, che non cambiano lo scope; default ragionevoli documentati in A-007.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
le tre forche di scope (DA-D1/D2/D3) sono state risolte con decisioni vincolanti dell'utente e codificate
come fissate. Le forche residue DA-D4/D5 sono questioni di *come* (criteri critico/warn, forma del probe
provider, rilevazione stantio-dopo-reindex MCP), risolvibili in plan. Pronta per `/speckit-plan`
(`/speckit-clarify` opzionale solo se si vuole fissare a monte i criteri critico/warn per area, oggi
coperti da un default ragionevole in A-007).
