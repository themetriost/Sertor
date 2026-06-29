# Checklist di qualità — Specifica `077-fail-loud-hook-agent`

Validazione della `spec.md` (E10-FEAT-019 epica debito-tecnico). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il problema reale (hook che inghiottono errori in silenzio → invisibili per settimane; agent che procedono a vuoto su asset mancante) e il valore «una rottura lascia una traccia ispezionabile; gli agent si fermano invece di procedere a vuoto»; i requisiti parlano di breadcrumb/persistenza/fallback/parità, non di sintassi PowerShell.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — i punti esatti di scrittura nei singoli hook, la forma della guardia anti-regressione e i punti dell'installer/ignore sono confinati a Forche di design (DA-D-r1/r2) e Fuori ambito; la decisione del breadcrumb (`.sertor/.last-hook-error`) è codificata come scelta di prodotto fissata con l'utente, non come prescrizione di codice.
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: gli hook e i body in scope (path `assets/...`), il pattern `.sertor/.rag-health.json` (FEAT-011) e le guardie `test_assets_sync.py`/parità — accertati e usati per ancorare i requisiti agli asset/meccanismi reali, non per imporre il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..017 hanno esito osservabile (breadcrumb su fallimento / contenuto hook-ts-reason / persistenza oltre sessione / no-op gated senza traccia / scrittura best-effort mai fatale / lettura cieca → breadcrumb / exit 0 in ogni path / nessun segreto / convenzione condivisa / fallback nei 3 body / fallback host-agnostico / sync dogfood↔bundle / guardia anti-regressione / artefatto runtime non versionato / additività installer).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US9 (traccia ispezionabile, persistenza + non-fatalità, no-op gated senza traccia, lettura cieca → traccia, nessun segreto, agent STOP su asset mancante, fallback host-agnostico byte-identico, guardia anti-regressione, sync + lifecycle additivo).
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — path degradato muto, scrittura breadcrumb fallita, no-op gated, errori in successione (ultimo-errore), lettura cieca di stato runtime, output con materiale sensibile, asset agent non risolvibile, hook fuori scope, drift dogfood↔bundle, reintroduzione catch silenzioso/perdita fallback.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili/verificabili. **PASS** — CS-1 (provoca il fallimento → trova la traccia coi 3 campi), CS-2 (exit 0 sempre, scrittura best-effort non fatale), CS-3 (istruzione presente e inequivocabile nel body), CS-4 (nessun segreto nella traccia), CS-5 (body byte-identici + guardie verdi), CS-6 (guardia fallisce su regressione).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (traccia ispezionabile, non-fatalità, agent che si ferma, assenza di segreti, parità/byte-identità, guardia che fallisce su regressione), non di sintassi PowerShell/Markdown o struttura interna degli asset.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (rottura silenziosa lascia traccia) + CS-3 (agent si ferma sull'asset mancante) sono la prova diretta dei due valori della feature.
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..6 mappano CS-1..6 dei requirements; coprono REQ-001..017 (FR-001..017) e i due obiettivi (hook fail-loud + agent fallback).

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: 4 hook (memory-capture, rag-freshness path catastrofici, wiki-pending-check, version-check), fallback nei 3 agent, convenzione breadcrumb, sync `.claude/` + guardie. Fuori: modifiche al core, portabilità OS/surface Copilot (FEAT-018), pulizia stile (FEAT-021/022), consumo attivo della traccia (follow-up Could), hook read-only/già-loud, il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — nota «Tracciamento dello scope»: portabilità OS + onestà surface Copilot → FEAT-018; pulizia stile/altitude → FEAT-021/022; consumo attivo automatico della traccia → follow-up Could (epica debito-tecnico). Nessun rinvio reale sepolto in `specs/`.
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — breadcrumb persistito (`.sertor/.last-hook-error`), hook in scope, hook fuori scope (classificati), body agent con fallback, guardia anti-regressione.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: un hook che inghiotte in silenzio il fallimento del re-index/archiviazione è il modo in cui il contesto reso all'agente degrada senza che nessuno se ne accorga; rendere fail-loud protegge la stella polare (il guasto si vede); D↔N (hook meccanico senza LLM, fallback agent = giudizio del body); complementa FEAT-011.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO + host-facing, ZERO codice di core»: solo asset (script hook + body markdown) + test di guardia; hook non importano `sertor_core` e non chiamano LLM; a comportamento sano funzionamento invariato (exit 0 senza scrivere nulla).
- [x] **C16** Principi riflessi: X (host-agnostico, fallback byte-identico Claude↔Copilot), XI (vehicle-only, no `sertor_core`, no LLM negli hook), XII (fail-loud — breadcrumb su degrado + agent STOP), privacy (no segreti). **PASS** — FR-013/RNF-4, FR-008/RNF-2/RNF-6, FR-001/006/010..012/RNF-1, FR-008/RNF-3.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese con l'utente sono codificate come **RISOLTE**, non riaperte. **PASS** — DA-1 (scope hook = 4 hook ancorati al §4), DA-2 (fallback agent uniforme STOP per i 3), DA-3 (breadcrumb = file singolo `.sertor/.last-hook-error` JSON sovrascritto «ultimo errore» + nota stderr, gemello di `.rag-health.json`) marcate RISOLTE con le decisioni vincolanti dell'utente; la forca aperta del §10 dei requirements (meccanismo breadcrumb) è ora chiusa nella spec.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-r1 punti esatti di scrittura nei singoli hook + no-op gated per ciascuno; DA-D-r2 forma della guardia anti-regressione) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
le tre decisioni di scope (scope hook, fallback agent uniforme, meccanismo del breadcrumb) sono risolte con
decisioni vincolanti dell'utente e codificate come fissate (DA-1..3) — incluso il meccanismo del breadcrumb
che era l'unica forca ancora aperta nei requirements (§10), ora chiusa. Le forche residue DA-D-r1/r2 sono
questioni di *come* (punti di scrittura nei singoli hook; forma della guardia), risolvibili in plan. Non sono
emerse ambiguità genuinamente nuove. Pronta per `/speckit-plan` (`/speckit-clarify` opzionale e non necessaria).
