# Checklist di qualità — Specifica `073-cattura-copilot-cli`

Validazione della `spec.md` (FEAT-008 epica memoria-conversazioni). Esito per voce: PASS / FAIL.

## Orientamento al valore (COSA/PERCHÉ, non COME)
- [x] **C1** La spec descrive il valore utente/consumatore e il perché, non l'implementazione. **PASS** — descrive la memoria resa operativa sul secondo assistente (Copilot) e il perché (hook inerte, manca la sorgente); niente codice/strutture imposte.
- [x] **C2** Nessun dettaglio implementativo prescrittivo è nei requisiti. **PASS** — schema esatto evento→turno, ricomposizione testo, politica progetto-indeterminabile, nomi esatti delle manopole di override sono confinati a Forche di design / Fuori ambito.
- [x] **C3** I riferimenti a file/simboli servono ad ancorare, non a prescrivere il come. **PASS** — etichettati «Ancoraggio all'esistente»; le decisioni fissate (sorgente `events.jsonl`, solo dialogo, filtro cwd/gitRoot, nome `copilot-cli`, legacy ignorata, cloud-sync documentato) vincolano lo scope per accertamento empirico, non il come di dettaglio.

## Requisiti funzionali testabili
- [x] **C4** Ogni FR è verificabile/testabile. **PASS** — FR-001..021 hanno esito osservabile (selezione/errore/default, discovery/override/id stabile, turni ordinati/best-effort/solo-dialogo, associazione/no-misattribuzione, idempotenza/scrub, privacy/local-only/trasparenza, host-confinato, parità tier, sorgente-assente/formato-inatteso, hook reso vivo).
- [x] **C5** Gli scenari utente hanno Independent Test + Acceptance Given/When/Then. **PASS** — US1..US7.
- [x] **C6** Gli Edge Cases sono elencati e coerenti coi requisiti. **PASS** — memoria off, valore ignoto, sorgente assente, sessione altrui, associazione indeterminabile, riga malformata, evento non-dialogo, cambio formato, cloud-sync, ricattura, legacy.

## Success criteria misurabili e tech-agnostici
- [x] **C7** I Success Criteria sono misurabili. **PASS** — SC-001 (#archiviate = N), SC-004 (zero traffico di rete), SC-005 (#record invariato), SC-007 (zero → N), SC-003/011 (suite verde, nessuna regressione), SC-009 (solo sessioni corrispondenti).
- [x] **C8** I Success Criteria evitano vincoli di stack non necessari. **PASS** — parlano di conteggi/rete/comportamento/parità, non di tipi o SDK specifici.
- [x] **C9** Esiste un criterio che dimostra il valore della feature con un esito osservabile. **PASS** — SC-001 (cattura su Copilot) + SC-007 (hook reso vivo) + SC-002 (parità di tier).
- [x] **C10** Parità con i criteri della fonte. **PASS** — SC-001..007 mappano CM-CS-1..7; SC-008..012 coprono solo-dialogo, associazione, default invariato, additività, testabilità.

## Completezza e confini
- [x] **C11** Scope chiaro; Fuori ambito esplicito. **PASS** — tier a monte/affiancato, modifiche al tier, altri assistenti, legacy/`session.db`, cloud-sync, distribuzione installer tutti fuori; il *come* di dettaglio relegato a design.
- [x] **C12** Gli Out-of-Scope reali sono promossi a casa durevole (backlog d'epica). **PASS** — debito distribuzione adapter cross-ref FEAT-009; legacy `history-session-state` tracciata Could nei requisiti d'epica; nota di tracciamento esplicita + clausola «non done finché un ospite Copilot non riceve il valore adapter».
- [x] **C13** Key Entities presenti e coerenti coi requisiti. **PASS** — adapter Copilot, sorgente di sessione, evento, turno, selettore adapter, associazione progetto.

## Allineamento costituzionale (gate riportati nella spec)
- [x] **C14** Gate «Allineamento alla missione» riportato e argomentato. **PASS** — sezione stella polare: stessa capacità portabile sul secondo assistente, host-agnosticità (Principio X) resa reale, nessun lock-in.
- [x] **C15** Natura del cambiamento dichiarata onestamente. **PASS** — riquadro «ADDITIVO, a leva spenta = nessun costo»; RNF-3/7, SC-011 (nessuna deviazione da additività; default `claude-code` invariato).
- [x] **C16** Principi riflessi: X (host-specificità confinata nell'adapter), I (tier riusato senza modifica), II (local-first/offline), XI (cattura via vehicle CLI/hook). **PASS** — FR-017, FR-018/RNF-5, RNF-2, RNF-8.

## Decisioni fissate vs chiarimenti
- [x] **C17** Le decisioni di scope già accertate empiricamente (sorgente `events.jsonl`, solo dialogo, filtro cwd/gitRoot, nome `copilot-cli`, legacy ignorata, cloud-sync solo-doc) sono codificate come **fissate**, non riaperte. **PASS** — riquadro «Decisioni di scope GIÀ fissate» con chiusura esplicita di DA-CM-1/2/3/4/5/6.
- [x] **C18** Nessun `[NEEDS CLARIFICATION]` aperto sullo scope. **PASS** — restano solo Forche di *come* (ricomposizione testo, politica progetto-indeterminabile, nome manopola override, forma filtro cwd/gitRoot) per il plan, che non cambiano lo scope.

---

**Esito complessivo: PASS (18/18).** Nessun blocco. Nessun `[NEEDS CLARIFICATION]` da girare all'utente:
le forche di scope sono state risolte empiricamente (dogfooding su sessioni Copilot reali) e codificate
come fissate. Pronta per `/speckit-plan`. Le Forche DA-CM-1/2/3/4 residue sono questioni di design (il
*come* dell'estrazione e dell'associazione), risolvibili in plan leggendo eventi reali; `/speckit-clarify`
opzionale solo se si vuole fissare prima la **politica per progetto indeterminabile** (FR-011) o la
**forma del filtro cwd/gitRoot** (DA-CM-4).
