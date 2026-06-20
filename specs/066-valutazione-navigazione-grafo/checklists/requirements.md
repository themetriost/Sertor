# Checklist di qualità dei requisiti — Valutazione della navigazione del grafo (FEAT-011)

**Scopo**: validare che `spec.md` sia orientata al valore (COSA/PERCHÉ), testabile, misurabile e
tech-agnostica, prima di `/speckit-clarify` o `/speckit-plan`. Esito per voce: PASS / FAIL.

## Orientamento al valore (no implementazione)
- [x] **CHK001** — La spec descrive COSA/PERCHÉ, non il COME (no stack/API/codice prescrittivi). *(PASS — i
  riferimenti a `CodeGraph`/`services/eval`/`eval/suite.toml` sono ancoraggi all'esistente esplicitamente
  marcati «non prescrivono il come»; schema/moduli/firme rinviati al plan.)*
- [x] **CHK002** — Il problema utente è chiaro e motivato. *(PASS — l'harness IR non sa esprimere le query
  relazionali; risposta = insieme, non rank; potenza del grafo oggi non misurata.)*
- [x] **CHK003** — Il valore è espresso in termini di esito per uno stakeholder. *(PASS — owner/maintainer
  sa se il grafo restituisce l'insieme giusto; «funziona» → «misurato e presidiato», Principio V.)*

## Scenari utente e testabilità
- [x] **CHK004** — Ogni User Story ha un Independent Test. *(PASS — US1..US4 ciascuna con Independent Test.)*
- [x] **CHK005** — I criteri di accettazione sono in forma Given/When/Then verificabili. *(PASS.)*
- [x] **CHK006** — Gli edge case rilevanti sono coperti. *(PASS — grafo non costruito, target assente
  (insieme vuoto), caso malformato, relazione non supportata, ref non verificabile, snapshot fragile, ref
  instabile ai refactor, determinismo, segreti.)*
- [x] **CHK007** — Le priorità (P1/P2 · Must/Should) sono assegnate alle storie. *(PASS — US1/US2/US4 P1
  Must; US3 P2 Should.)*

## Requisiti tracciabili
- [x] **CHK008** — Ogni gruppo di requisiti A–G è rappresentato nella sezione Requirements. *(PASS — A..G
  sintetizzati con mappatura REQ-001..061.)*
- [x] **CHK009** — I requisiti funzionali sono testabili (non vaghi). *(PASS — confronto di insiemi,
  precision/recall/F1, exit non-zero, sezione distinta, validazione `ref`.)*
- [x] **CHK010** — I requisiti non funzionali (additività, determinismo, privacy, compatibilità, dato non
  output) sono presenti. *(PASS — RNF-1..5.)*
- [x] **CHK011** — Le Key Entities sono definite senza dettagli implementativi. *(PASS — caso di
  navigazione, `ref`, insieme navigato, metrica a insiemi, baseline, report, esito non-regressione,
  candidato; descritte come concetti, non strutture dati.)*

## Success criteria misurabili e tech-agnostici
- [x] **CHK012** — I Success Criteria sono misurabili. *(PASS — metriche identiche su due run; exit non-zero
  sotto baseline; costo identico a leve spente; sezione distinta; evento metrics-only senza nomi/path.)*
- [x] **CHK013** — I Success Criteria sono tech-agnostici (esito, non meccanismo). *(PASS — formulati come
  comportamenti osservabili; nessun nome di file/funzione vincolante negli SC.)*
- [x] **CHK014** — Ogni SC traccia ai requisiti/criteri d'epica. *(PASS — SC-001..010 citano REQ e CS-1..4.)*

## Assunzioni e confini
- [x] **CHK015** — Le assunzioni con default ragionevoli sono documentate. *(PASS — indice/grafo presenti,
  `ref` stabile, «LLM»=agente, estensione non reinvenzione, installer, confine osservabilità.)*
- [x] **CHK016** — Il Fuori Ambito è esplicito e i rinvii reali sono promossi a casa durevole. *(PASS —
  relazioni Could + refresh snapshot promossi a backlog/MoSCoW; IR invariati; trend all'epica osservabilita;
  rank/@k Won't.)*
- [x] **CHK017** — I vincoli di piattaforma (Principio X host-side, Principio XI solo-vehicle, confine D↔N,
  additività, zero LLM nel run, evento metrics-only, dato in `eval/`) sono riportati. *(PASS — riquadri in
  testa + RNF + SC.)*

## Ambiguità e chiarimenti
- [x] **CHK018** — Le decisioni di scope A–E sono riportate come scelte, NON come `[NEEDS CLARIFICATION]`.
  *(PASS — riquadro «Decisioni di scope già risolte».)*
- [x] **CHK019** — Le domande aperte residue sono SOLO di design (come), non di scope (cosa). *(PASS — DA-a
  tolleranza/metrica aggregata, DA-b unità `related_docs`, DA-c re-congelamento, DA-d split file: tutte di
  design; nessuna ambiguità di scope.)*
- [x] **CHK020** — Nessun `[NEEDS CLARIFICATION]` bloccante senza default ragionevole. *(PASS — nessun
  `[NEEDS CLARIFICATION]`; le forche residue hanno default praticabili o sono rinviabili al plan senza
  bloccare il cosa/perché.)*

---

**Esito complessivo (iterazione 1): PASS — 20/20.** La spec è orientata al valore, testabile, con success
criteria misurabili e tech-agnostici; le decisioni di scope A–E sono fissate; le sole domande residue sono
di design e non bloccano. Pronta per `/speckit-clarify` (opzionale) o `/speckit-plan`.
