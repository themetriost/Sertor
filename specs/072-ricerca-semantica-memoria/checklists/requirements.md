# Checklist di qualità — Specifica `072-ricerca-semantica-memoria`

Validazione della `spec.md` (FEAT-004 epica memoria-conversazioni). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il recupero per significato e il perché (lacuna del match lessicale); niente codice/strutture imposte.
- [x] **C2** Nessun dettaglio implementativo prescrittivo (granularità, forma del marker, nome manopola, superficie comando) è nei requisiti; è confinato alle Forche di design / Fuori ambito. **PASS**
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — etichettati come «Ancoraggio all'esistente»; le decisioni fissate (Opzione B, watermark, trigger) vincolano lo scope, non il come di dettaglio.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..032 hanno esito osservabile (opt-in/dipendenza, auto-index/incrementalità/idempotenza, citazione/limite/finestra, modo separato/no-fallback, riuso/isolamento, on-machine/off-machine esplicito, degradazione, host-agnostico, osservabilità metrics-only, ricostruibilità).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US6.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — cattura-off, rebuild su cambio provider, cloud+auto-index, finestra temporale, isolamento corpus, artefatto derivato, re-index senza nuovo.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili. **PASS** — SC-002 (zero unità embeddate), SC-003 (zero traffico di rete), SC-006 (zero nuove chiamate di embedding), SC-013 (≥2 ospiti), SC-001 (top-k dove la full-text fallisce).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di comportamento/conteggi/rete/risultati, non di tipi o SDK specifici (relegati alle Forche/plan).
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — SC-001 (recupero per significato) e SC-006 (incrementalità O(nuovo)).

## Completezza e confini
- [x] **C10** Scope chiaro; Fuori ambito esplicito. **PASS** — FEAT-001/002 (a monte/affiancata), MCP, installer, retention, multi-assistente, roll-up, scrub aggiuntivo tutti fuori; il *come* di dettaglio relegato a design.
- [x] **C11** Gli Out-of-Scope reali sono promossi a casa durevole (backlog d'epica). **PASS** — FEAT-010/009/006/008/007 citati; nota di tracciamento + debito DA-SS-6 cross-ref FEAT-009.
- [x] **C12** Key Entities presenti e coerenti coi requisiti. **PASS** — indice semantico isolato, unità indicizzata, risultato, marker watermark, opt-in semantico, modo di ricerca.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C13** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — sezione stella polare: qualità del contesto nel tempo, riuso del motore, on-machine col locale.
- [x] **C14** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO, a leva spenta = nessun costo»; RNF-2/3, SC-011 (nessuna deviazione da additività I/III).
- [x] **C15** Principi riflessi: I/III (riuso, no nuovo motore), V (misurabilità), II (local-first/deterministico), X (host-agnostico), XI (via vehicle CLI). **PASS** — FR-019/020, SC-008, RNF-1, FR-027/028, e l'esercizio via CLI assunto.

## Decisioni fissate vs chiarimenti
- [x] **C16** Le decisioni di scope già prese (Opzione B store dedicato, watermark incrementale, trigger auto a fine sessione, modo separato opt-in, manopola distinta) sono codificate come **fissate**, non riaperte. **PASS** — riquadro «Decisioni di scope GIÀ fissate».
- [x] **C17** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (granularità, forma marker, superficie comando, nome manopola) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (17/17).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente
(le forche di scope erano già decise e sono codificate come fissate). Pronta per `/speckit-plan`; le
Forche DA-SS-2/3/4(residuo)/5 sono questioni di design risolvibili in plan — opzionalmente
`/speckit-clarify` se si vuole fissare prima la **granularità** (impatta la soglia di latenza NFR-009/RNF-9).
