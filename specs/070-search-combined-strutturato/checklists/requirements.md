# Checklist di qualità — Specifica `070-search-combined-strutturato`

Validazione della `spec.md` (Tempo 2 FEAT-003). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive il contratto reso (due flussi etichettati) e il perché (la fusione è rotta), niente codice/strutture imposte.
- [x] **C2** Nessun dettaglio implementativo prescrittivo (struttura entità, allocazione k, strategia flatten) è nei requisiti; è confinato alle Forche di design / Fuori ambito. **PASS**
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — etichettati come «Ancoraggio all'esistente».

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..009 hanno esito osservabile (contratto, flatten, invarianza mono-tipo, consumatori, resa, metrica, baseline, numero, determinismo).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US4.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — coppia con lista vuota, flatten su vuoti, miss su una sola lista, determinismo.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili. **PASS** — SC-004 (fusion coverage > 0.17), SC-003 (flatten deterministico ripetibile), SC-006 (suite verde/lint pulito), SC-008 (numeri identici).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di contratto/forma/numeri, non di tipi Python specifici (relegati alle Forche).
- [x] **C9** Esiste un criterio che dimostra l'obiettivo del refactor con un numero. **PASS** — SC-004 ancorato alla baseline misurata 0.17.

## Completezza e confini
- [x] **C10** Scope chiaro; Fuori ambito esplicito. **PASS** — qualità per-superficie docs, HyDE/contextual/metadata, eval cloud, soglie astensione tutti fuori.
- [x] **C11** Gli Out-of-Scope reali sono promossi a casa durevole (backlog d'epica). **PASS** — FEAT-002/004/005/006/007 citati; nota di tracciamento presente.
- [x] **C12** Key Entities presenti e coerenti col contratto. **PASS** — risultato fuso strutturato, flatten, mono-tipo, fusion coverage adattata, baseline ri-registrata.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C13** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — sezione stella polare: ripara la fusione code+doc.
- [x] **C14** La deviazione dall'additività (Principi I/III) è dichiarata onestamente e giustificata (Principio XII + gate missione). **PASS** — RNF-1, SC-010, riquadro «Natura del cambiamento».
- [x] **C15** Principi V (misurabilità), II (local-first/deterministico), XI (accesso via vehicle) riflessi nei requisiti. **PASS** — RNF-2/3, FR-009, SC-008.

## Chiarimenti
- [x] **C16** Nessun `[NEEDS CLARIFICATION]` aperto: lo scope è deciso (contratto strutturato a due flussi + flatten). **PASS** — solo Forche di *come* per il plan, che non cambiano scope.

---

**Esito complessivo: PASS (16/16).** Nessun blocco. Pronta per `/speckit-plan` (le 4 Forche DA-a..d sono
questioni di design, risolvibili in plan; opzionalmente `/speckit-clarify` se si vuole fissare prima
l'allocazione dei k / la strategia di flatten).
