# Checklist di qualità — Specifica `075-guided-setup`

Validazione della `spec.md` (E12-FEAT-002 epica usabilità). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il primo contatto fragile (install/configure/.env a mano/download/«ha funzionato?») e il valore «dal nulla a verificato» senza internals; i requisiti parlano di flusso, scelta provider, segreti, verify, consenso, distribuzione — non di codice.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — forma del body della skill/dei prompt, struttura dello stub, segnali esatti dell'euristica, punti precisi dell'installer/della guardia confinati a Forche di design (DA-D-r1/r2) e Fuori ambito.
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: `sertor install rag`, `configure`/`--set`/`getpass`/`mask_secret`, `sertor-rag doctor` (FEAT-001), `index`/avviso GloVe, pattern dual-target (`wiki-author`/`eval-suite-author`) — accertati e usati per ancorare i requisiti ai vehicle reali, non per imporre il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..013 hanno esito osservabile (flusso via vehicle / verify via doctor / fail-loud / raccomandazione locale-conferma / segreti mai stampati / annuncio GloVe / consenso prima delle mutazioni / idempotenza / dual-target byte-identico / guardia di parità / stub a un ramo / no LLM nel core).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US9 (dal nulla a verificato, scelta provider, segreti sicuri, download GloVe, verify fail-loud, consenso, idempotenza, dual-target+parità, stub concierge).
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — repo vergine, creds assenti/airgapped, creds+NL, glove senza cache, doctor rosso, segreto richiesto/già presente, passo mutante senza conferma, ri-esecuzione idempotente, host senza agente frontier, distribuzione mono-target, concierge oltre il ramo.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili. **PASS** — CS-1 (doctor verde senza conoscere comandi), CS-2 (verificato su «creds assenti→locale» e «creds presenti→cloud»), CS-3 (zero valori di segreto nell'output), CS-4 (verde→«verificato» / rosso→area+rimedio+no successo), CS-5 (installabile Claude+Copilot, byte-identico, closure, zero leak — via guardia offline).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (flusso, motivazione, segreti, fail-loud, parità), non di tipi/SDK/struttura del codice.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (dal nulla a verificato) + CS-4 (verify fail-loud) + CS-5 (ricevuta via install su entrambi i target).
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..5 mappano CS-1..5 dei requisiti; coprono REQ-001..009 (FR-001..013) e i CS d'epica CS-1/CS-5/CS-6 (D↔N via FR-013/RNF-1).

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: skill + stub + wiring dual-target + guardia. Fuori: comandi in sé (FEAT-001/E2), profilazione ricca (FEAT-004), concierge pieno (FEAT-009), progress GloVe (FEAT-003), auto-azione senza consenso, LLM nel core, il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — nota «Tracciamento dello scope»: stub → FEAT-009 tracciata **parzialmente avviata** (non sepolta in `specs/`); sinergie FEAT-003/FEAT-004 restano nel backlog d'epica; corollario «feature completa» reso esplicito (in ambito FR-010/011, non rinviato).
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — skill guided-setup, stub concierge, vehicle orchestrati, raccomandazione provider, esito di verifica (doctor), artefatti di distribuzione dual-target.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: primo strato agentico che realizza CS-1 d'epica «dal nulla a verificato» sopra `doctor`; host-agnosticità reale (Principio X); core senza LLM (D↔N).
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO + scope di distribuzione» (asset di istruzioni + wiring + guardia; nessun percorso runtime del core cambia) + RNF-7; corollario «feature completa».
- [x] **C16** Principi riflessi: X (host-agnostico, byte-identico/contenitore nativo), XI (vehicle-only, no internals), D↔N (no LLM nel core), XII (verify reale fail-loud). **PASS** — FR-010/RNF-2, FR-001/FR-013/RNF-1, FR-013, FR-002/003/RNF-4.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese con l'utente sono codificate come **RISOLTE**, non riaperte. **PASS** — DA-G1 (skill + stub concierge, anticipa FEAT-009), DA-G2 (euristica minima + conferma), DA-G3 (esegue-su-conferma: sola lettura libera, mutazioni/download su conferma) marcate RISOLTE con le decisioni vincolanti dell'utente.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-r1 forma degli asset, DA-D-r2 wiring di distribuzione) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
le tre forche di scope (DA-G1/G2/G3) sono state risolte con decisioni vincolanti dell'utente e codificate
come fissate; l'anticipo di FEAT-009 (stub) è dichiarato e tracciato. Le forche residue DA-D-r1/r2 sono
questioni di *come* (forma degli asset, wiring di distribuzione e guardia di parità), risolvibili in plan.
Pronta per `/speckit-plan` (`/speckit-clarify` opzionale e non necessaria).
