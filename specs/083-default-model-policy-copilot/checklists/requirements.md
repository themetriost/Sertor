# Checklist di qualità — Specifica `083-default-model-policy-copilot`

Validazione della `spec.md` (E2-FEAT-015 epica sertor-cli). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il problema reale (variabilità non voluta del modello implicito tra installazioni; agenti con profili cognitivi diversi sullo stesso modello) e il valore («ogni agente Copilot CLI riceve un default ragionato, modificabile»). I requisiti parlano di esiti osservabili (default esplicito nel frontmatter, fail-loud nominante, path Claude invariato), non del codice.
- [x] **C2** Nessun dettaglio implementativo prescrittivo nei requisiti. **PASS** — la forma del profilo, il punto di innesto della sostituzione nel renderer, la forma degli assert riconciliati e il meccanismo di fail-loud sono confinati nelle «Forche di design» (DA-D-1..6). Le decisioni di prodotto (meccanismo A, kit condiviso, scope 5 agenti, default iniziali) sono scelte fissate, non prescrizioni di edit.
- [x] **C3** I riferimenti a file/simboli ancorano, non prescrivono il come. **PASS** — il riquadro «Ancoraggio all'esistente» cita renderer/punti di deposito/guardie da riconciliare come stato verificato di partenza; la tabella dei default è marcata «vive nel profilo versionato, non hardcoded».

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..018 hanno esito osservabile (model esplicito non-vuoto per-agente / sostituzione dell'alias / deposito non distruttivo / coerenza cross-pacchetto / profilo unico / leggibile senza dipendenza vietata / marcatore versione / fail-loud nominante / nessun deposito parziale / idempotenza byte-identica / lifecycle / Claude invariato / non-regressione FEAT-011/049 / distribuzione via installer / doc utente / default modificabile / confine speckit.* / disponibilità onesta).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US8 (default esplicito, fail-loud profilo incompleto, fonte unica, zero impatto Claude + no leak, DoD distribuzione+doc, idempotenza/lifecycle, default modificabile/override, confine speckit.*+tenant) hanno ciascuna Independent Test e acceptance G/W/T.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — alias canonico da sostituire (US1/US4), profilo incompleto (US2), model-ID datato/non-tenant (US8), host con entrambi i pacchetti (US3), edit manuale vs `/subagents` (US7), drift bundlato↔dogfood (R-5).

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (5 agenti con `model:` esplicito, 0 impliciti), CS-2 (0 alias Claude), CS-3 (ID in un solo posto, 0 hardcoded), CS-4 (byte-identico su ripetizione), CS-5 (fail-loud nominante, 0 install incomplete), CS-6 (solo via installer + doc aggiornata), CS-7 (0 regressioni Claude, byte-identico).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (campo presente/assente, conteggio occorrenze, byte-identità, fallimento nominante, offline), non di scelte implementative; sono tech-agnostici e verificabili offline.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (ogni agente ha un default esplicito invece della selezione implicita) è la prova diretta del valore risolto; CS-5 (fail-loud) e CS-7 (zero impatto Claude) proteggono la correttezza.
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..7 della spec mappano CS-1..7 dei requirements (default esplicito, no leak, fonte unica, idempotenza, fail-loud, DoD, zero impatto Claude); FR-001..018 coprono REQ-001..016 + NFR-001..008, incluse le DA risolte (meccanismo A, override sicuro, no probe, kit condiviso).

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: i 5 custom-agent Copilot, il profilo versionato condiviso, l'emissione del `model:`, il fail-loud su profilo incompleto, la riconciliazione delle guardie, la doc utente. Fuori: core/runtime, `speckit.*`, Claude, Codex, probe tenant install-time, nuovi provider/routing, il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — l'unico rinvio reale (assegnazione modello agli `speckit.*`) è dichiarato da promuovere a nuova voce `FEAT-NNN` nel backlog dell'epica `sertor-cli` al plan (previa spike); gli altri fuori-ambito sono confini di scope o questioni di plan.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — profilo versionato (nuovo, nel kit), i 5 custom-agent in ambito, renderer del frontmatter Copilot, guardie da riconciliare, documentazione utente, prompt-file `speckit.*` (fuori ambito).

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: un modello adeguato al compito migliora qualità/prevedibilità del lavoro dell'agente ospite sul corpus fuso e rende più reale la host-agnosticità (Principio X); è distribuzione host-facing sul confine D↔N, nessun core/LLM.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVA / distribuzione-installer, ZERO runtime di `sertor_core`»; zero impatto sul path Claude (frontmatter Claude byte-identici).
- [x] **C16** Principi riflessi: X (host-agnostico), XI (zero `sertor_core`, nessun LLM), non-regressione FEAT-011/049. **PASS** — RNF-1 (zero core/LLM), RNF-8 (`sertor-core` invariato), FR-012/CS-7 (Claude invariato), FR-013/CS-2 (non-regressione garanzia anti-leak).

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese sono codificate come **RISOLTE**. **PASS** — meccanismo A confermato (B scartato); scope 5 agenti + speckit.* fuori; solo Copilot; profilo nel kit condiviso; override utente al sicuro per costruzione (DA-1 risolta); no probe tenant install-time (DA-2 risolta); fail-loud install-time solo su profilo incompleto. Tutte tradotte in FR/Assumptions (A-001..006).
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-1 forma profilo, DA-D-2 innesto renderer, DA-D-3 forma guardie, DA-D-4 meccanismo fail-loud, DA-D-5 sync, DA-D-6 fallback per-agente) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
tutte le forche di scope (meccanismo A/B, override utente, probe tenant, collocazione profilo, ambito
speckit.*) sono **risolte** e ratificate dall'utente. Le forche residue DA-D-1..6 sono questioni di *come*
(forma del profilo, innesto della sostituzione, forma degli assert riconciliati, meccanismo del fail-loud,
sync, fallback), risolvibili in plan. Pronta per `/speckit-plan` (`/speckit-clarify` opzionale e non
necessaria).
