# Checklist di qualità — Specifica `081-stub-copilot`

Validazione della `spec.md` (E10-FEAT-023 epica debito-tecnico). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il problema reale (un tree di quattro directory vuote con soli `.gitkeep` che suggerisce un'architettura di asset Copilot statici inesistente, mentre i payload sono generati a runtime) e il valore «lo stato del repo riflette la realtà, senza file da manutenere»; i requisiti parlano di rimozione/non-regressione/non-ricomparsa, non di comandi `git rm` specifici.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — la forma esatta della guardia anti-ricomparsa (test nuovo vs estensione) e l'eventuale commento in `install_rag.py` sono confinati a «Forche di design» (DA-D-1/2); la decisione di scope (Opzione A vs B) è codificata come scelta di prodotto fissata, non come prescrizione di edit.
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: l'inventario (`assets/copilot/{agents,hooks,instructions,prompts}/.gitkeep`), la pipeline generativa (`render_copilot_hooks`/`render_custom_agent`/`render_prompt_file`, `build_rag_plan`) e le guardie/packaging ancorano i requisiti allo stato reale, non impongono il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..008 hanno esito osservabile (`.gitkeep` rimossi / directory vuote rimosse / nessun file di rimpiazzo / generazione Copilot invariata / verifica zero-consumatori / build+packaging verdi / guardie+suite verdi / guardia anti-ricomparsa fallisce alla ricomparsa).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US6 (no directory fuorviante, no file di rimpiazzo, generazione Copilot invariata, build/packaging integri, suite/guardie verdi, stub non riappare) hanno ciascuna Independent Test e acceptance G/W/T.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — consumatore introdotto dopo la verifica grep (FR-005), ricomparsa stub (FR-008), wheel vecchio-vs-nuovo (FR-006), directory vuota residua dopo `git rm` (FR-002).

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (`git ls-files .../assets/copilot/` vuoto), CS-2 (`uv build` + test packaging verdi), CS-3 (zero nuovi fallimenti di suite, guardia anti-ricomparsa verde), CS-4 (`build_rag_plan(copilot-cli)` stessi artefatti, test install copilot verdi).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (directory assente, build verde, suite verde, artefatti identici), non di tool di rimozione specifici; le verifiche `git ls-files`/`uv build` sono criteri di accettazione meccanici osservabili, non prescrizioni d'implementazione.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (zero stub fuorvianti) è la prova diretta del valore «lo stato del repo riflette la realtà», affiancata da CS-4 (comportamento installer invariato) che dimostra l'assenza di regressione.
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..4 della spec mappano CS-1..4 dei requirements (zero stub / no regressione build-wheel / no regressione suite / comportamento installer invariato); coprono FR-001..008 (REQ-001..008 + R-2).

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: rimozione del tree `assets/copilot/**` (4 `.gitkeep` + 4 dir + `copilot/`), nessun file di rimpiazzo, verifica di non-regressione, guardia anti-ricomparsa. Fuori: core, `surfaces.py`/`install_rag.py`/`install_wiki.py`/`sertor_install_kit`, `assets/claude|rag/**`, test esistenti, README Opzione B (scartato), doc editoriale, budget altitude (FEAT-024), parity guard esteso (FEAT-024), fork IT eval (FEAT-025), portabilità OS hook (FEAT-018), il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — nota «Tracciamento dello scope»: budget altitude / parity guard esteso → FEAT-024; riconciliazione fork IT eval → FEAT-025; documentazione editoriale → intervento autonomo separato. Nessun rinvio reale sepolto in `specs/`.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — tree stub `assets/copilot/`, pipeline di generazione Copilot (non modificata), guardie esistenti (verdi), guardia anti-regressione.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: un tree di directory vuote sotto `assets/` è contesto fuorviante (comunica un'architettura di asset statici inesistente); rimuoverlo fa sì che il repo rifletta la realtà; D↔N (solo igiene host-facing, nessun core, nessun LLM, nessun cambiamento di comportamento); complementa FEAT-022.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «SOTTRATTIVA / igiene host-facing, ZERO codice di core»: tocca solo 4 `.gitkeep` + 4 dir vuote; generazione Copilot 100% derivata a runtime, identica prima/dopo; rimozione puramente sottrattiva, nessun piano d'installazione alterato.
- [x] **C16** Principi riflessi: X (host-agnostico, generazione Copilot invariata), XI (zero `sertor_core`, nessun codice di runtime toccato), igiene senza regressione. **PASS** — RNF-1 (zero core), RNF-2 (comportamento installer byte-identico per entrambi gli assistenti), FR-004 (generazione Copilot invariata); cross-ref a FEAT-024/025/018.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese sono codificate come **RISOLTE**, non riaperte. **PASS** — la forca §1.4/DA-1 dei requirements (rimozione vs README) è marcata FISSATA: **Opzione A — RIMOZIONE**, Opzione B scartata con motivazione (file da manutenere, contraddice il guard test); tradotta in FR-001/002/003 (nessun file di rimpiazzo).
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-1 forma guardia anti-ricomparsa, DA-D-2 commento esplicativo in `install_rag.py`) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
la sola forca di scope dei requirements (§1.4 / DA-1 — rimozione vs README) è **risolta** con decisione
vincolante (Opzione A — rimozione, nessun README). Le forche residue DA-D-1/2 sono questioni di *come*
(forma della guardia anti-ricomparsa, eventuale commento esplicativo), risolvibili in plan. Pronta per
`/speckit-plan` (`/speckit-clarify` opzionale e non necessaria).
