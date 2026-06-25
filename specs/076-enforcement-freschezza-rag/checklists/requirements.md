# Checklist di qualità — Specifica `076-enforcement-freschezza-rag`

Validazione della `spec.md` (E10-FEAT-011 epica debito-tecnico). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il problema reale (i passi 5/8 del rituale si saltano perché discrezionali; rischio «contesto non reale») e il valore «freschezza enforced senza dipendere dalla memoria dell'agente»; i requisiti parlano di re-index/verifica/persistenza/induzione/distribuzione, non di codice.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — nome/posizione/formato esatti del file di stato, voce hook a cui agganciare il segnale d'avvio, punti precisi dell'installer/della guardia confinati a Forche di design (DA-D-r1/r2) e Fuori ambito; il `.sertor/.rag-health` è marcato «proposto».
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — riquadro «Ancoraggio all'esistente»: `sertor-rag index .` (incrementale FEAT-009 + cache FEAT-019), `sertor-rag doctor` (E12-FEAT-001), meccanismo installer hook (`memory-capture`/`sertor-rag-usage-check`), seam `AssistantProfile` — accertati e usati per ancorare i requisiti ai vehicle/meccanismi reali, non per imporre il come.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..024 hanno esito osservabile (re-index via vehicle incondizionato / zero embedding a corpus invariato / solo-vehicle / health via doctor / verdetto / smoke limitato a doctor / persistenza+messaggio / clear a sano / contenuto stato / lettura+induzione allo start / solo-segnala-induce / clear a guarigione / hook dedicato non-fatale isolato / riclassificazione CLAUDE.md / deposito installer formato-nativo per-capacità / upgrade-uninstall granulare / guardia di sync).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US9 (no salto re-index/smoke, zero costo a corpus invariato, degrado evidente+indotto allo start, stato sopravvive alla chiusura, smoke limitato a doctor + buco dichiarato, hook separato/non-fatale/isolato, riclassificazione governance, installabile con parità, lifecycle granulare + sync).
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — nulla cambiato, indice stantio/area fail-warn, corpus recuperato, errore interno hook, coesistenza con memory-capture, guasto filtro `where`, server MCP stantio, marker non pulito, drift bundlato↔dogfood, host senza MCP/senza capacità `rag`.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili. **PASS** — CS-1 (indice aggiornato nel 100% delle sessioni senza azione manuale), CS-2 (degrado evidente+indotto prima del lavoro, mai ignorato), CS-3 (exit 0 sempre, errore non fatale), CS-4 (formato nativo + isolamento + sync via guardia), CS-5 (zero ri-embedding a corpus invariato).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di esiti (freschezza, evidenza+induzione, non-fatalità, parità nativa, zero costo), non di linguaggio/SDK/struttura interna dell'hook.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — CS-1 (freschezza enforced senza azione manuale) + CS-2 (degrado evidente e indotto tra sessioni) sono la prova diretta del valore.
- [x] **C10** Parità con i criteri della fonte. **PASS** — CS-1..5 mappano CS-1..5 dei requisiti; coprono REQ-001..024 (FR-001..024) e gli obiettivi OBJ-1/2/3.

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — in ambito: hook SessionEnd (re-index+doctor+persistenza), segnale SessionStart (ripesco+induzione), reclassificazione CLAUDE.md, distribuzione host-facing con parità e lifecycle. Fuori: smoke `where`, client MCP standalone, drift-detection (FEAT-012), modifiche a index/doctor, il *come* di dettaglio.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole. **PASS** — nota «Tracciamento dello scope»: buco filtro-metadata → nuova FEAT epica `usabilità` (E12, owner doctor); staleness forte server MCP → debito `osservabilita`; drift-detection → FEAT-012; corollario «feature completa» reso esplicito (host-facing in ambito FR-020..024, non rinviato).
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — hook di freschezza (harness), stato di salute persistito, vehicle orchestrati (index/doctor), verdetto di salute, voci hook per-assistente, step 5/8 del rituale.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — riquadro stella polare: la freschezza è al cuore della qualità del contesto reso all'agente nel tempo; un indice stantio è il fallimento che RAG+wiki+lint esistono per prevenire; previene a monte (vs FEAT-012 che osserva); core senza LLM (D↔N).
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO (harness + distribuzione), nessun codice di core»: consuma index/doctor come vehicle, non li estende; a indice fresco comportamento invariato; corollario «feature completa».
- [x] **C16** Principi riflessi: X (host-agnostico, formato nativo per assistente), XI (vehicle-only, no `sertor_core`), D↔N (hook induce, agente esegue, no LLM), XII (fail-loud su degrado). **PASS** — FR-021/RNF-4, FR-004/RNF-1, FR-014/RNF-5, FR-008/009/013.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già prese con l'utente sono codificate come **RISOLTE**, non riaperte. **PASS** — DA-1 (re-index incondizionato via vehicle, skip al core), DA-2 (fail-loud a due tempi SessionEnd/SessionStart), DA-3 (smoke = solo doctor + buco dichiarato), DA-4 (hook separato/indipendente/non-fatale/per-capacità/parità) marcate RISOLTE con le decisioni vincolanti dell'utente.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (DA-D-r1 nome/formato del file di stato, DA-D-r2 aggancio del segnale d'avvio) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
le quattro decisioni di scope (trigger re-index, fail-loud a due tempi, scope smoke, coesistenza) sono
state risolte con decisioni vincolanti dell'utente e codificate come fissate (DA-1..4); il buco del
filtro-metadata è dichiarato e promosso a E12. Le forche residue DA-D-r1/r2 sono questioni di *come*
(nome/formato del file di stato, aggancio del segnale d'avvio), risolvibili in plan. Non sono emerse
ambiguità genuinamente nuove oltre a quelle già risolte. Pronta per `/speckit-plan` (`/speckit-clarify`
opzionale e non necessaria).
