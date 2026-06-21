# Checklist di qualità dei requisiti — Embedder locale (FEAT-011)

**Scopo**: validare che `spec.md` sia orientata al valore (COSA/PERCHÉ), testabile, misurabile e
tech-agnostica, prima di `/speckit-clarify` o `/speckit-plan`. Esito per voce: PASS / FAIL.

## Orientamento al valore (no implementazione)
- [x] **CHK001** — La spec descrive COSA/PERCHÉ, non il COME (no stack/API/codice prescrittivi). *(PASS — i
  riferimenti a `EmbeddingProvider`/`build_embedder`/`collection_name()` sono ancoraggi all'esistente
  esplicitamente marcati «non prescrivono il come»; algoritmi, dimensione vettore lessicale, aggregazione
  token→vettore e struttura cache rinviati al plan.)*
- [x] **CHK002** — Il problema utente è chiaro e motivato. *(PASS — per indicizzare serve sempre un
  embedder; abilitare Ollama/Azure in enterprise richiede cicli di autorizzazione/legal/budget → Sertor non
  parte.)*
- [x] **CHK003** — Il valore è espresso in termini di esito per uno stakeholder. *(PASS — l'operatore ospite
  indicizza e cerca da subito con un solo comando; upgrade pulito; legale approva licenza/provenienza pulite;
  eval offline come beneficio collaterale.)*

## Scenari utente e testabilità
- [x] **CHK004** — Ogni User Story ha un Independent Test. *(PASS — US1..US5 ciascuna con Independent Test.)*
- [x] **CHK005** — I criteri di accettazione sono in forma Given/When/Then verificabili. *(PASS.)*
- [x] **CHK006** — Gli edge case rilevanti sono coperti. *(PASS — nessun provider configurato, airgapped,
  token OOV (GloVe e lessicale), GloVe assente+offline, errore di download, valore manopola non valido,
  hashing salted, mescolanza vettori, cambio default, costo locale.)*
- [x] **CHK007** — Le priorità (P1/P2 · Must/Should) sono assegnate alle storie. *(PASS — US1..US5 tutte P1
  Must; il corollario installabile US5 cita i sotto-requisiti REQ-060/061 Should con REQ-062 Must.)*

## Requisiti tracciabili
- [x] **CHK008** — Ogni gruppo di requisiti A–G è rappresentato nella sezione Requirements. *(PASS — A..G
  sintetizzati con mappatura REQ-001..062.)*
- [x] **CHK009** — I requisiti funzionali sono testabili (non vaghi). *(PASS — un solo comando senza config,
  determinismo cross-macchina, scarica-poi-riusa, errore che nomina vie d'uscita, manopola dedicata
  indipendente, namespacing per provider.)*
- [x] **CHK010** — I requisiti non funzionali (determinismo, isolamento dipendenze, local-first/privacy,
  non-regressione, memoria, costo) sono presenti. *(PASS — RNF-1..6.)*
- [x] **CHK011** — Le Key Entities sono definite senza dettagli implementativi. *(PASS — provider lessicale,
  provider GloVe, manopola di selezione, file di vettori, override di percorso, esito di
  selezione/acquisizione, errore azionabile; descritte come concetti, non come strutture dati.)*

## Success criteria misurabili e tech-agnostici
- [x] **CHK012** — I Success Criteria sono misurabili. *(PASS — indicizza/cerca con un solo comando zero-config;
  almeno un provider airgapped; vettori identici cross-run/macchina/Python; costo invariato a esistenti;
  fallimento azionabile vs degrado silenzioso; scarica-una-volta-poi-cache; manopole nel template `.env`.)*
- [x] **CHK013** — I Success Criteria sono tech-agnostici (esito, non meccanismo). *(PASS — formulati come
  comportamenti osservabili; i pochi nomi citati (`build_embedder`, `SERTOR_EMBED_PROVIDER`) sono ancoraggi e
  decisioni di scope già prese nei requisiti, non meccanismi prescritti.)*
- [x] **CHK014** — Ogni SC traccia ai requisiti/criteri d'epica. *(PASS — SC-001..010 citano REQ e CS-1..6.)*

## Assunzioni e confini
- [x] **CHK015** — Le assunzioni con default ragionevoli sono documentate. *(PASS — GloVe redistribuibile,
  default GloVe 300d, manopola dedicata, «LLM»=agente, distinzione da `FakeEmbedder`, estensione non
  reinvenzione, installer, dipendenza a valle CI.)*
- [x] **CHK016** — Il Fuori Ambito è esplicito e i rinvii reali sono promossi a casa durevole. *(PASS — CI
  vera = FEAT-003 `debito-tecnico`; altre fonti di vettori e modelli neurali esclusi con motivazione; Could
  (dim configurabile, checksum, pre-download) promossi a MoSCoW requisiti + backlog epica.)*
- [x] **CHK017** — I vincoli di piattaforma (Principio II local-first, X + corollario installabile, XI
  solo-vehicle, XII fail-loud, additività I/III, confine D↔N zero-LLM nel core) sono riportati. *(PASS —
  riquadri in testa + RNF + SC-005/008/009.)*

## Ambiguità e chiarimenti
- [x] **CHK018** — Le decisioni di scope sono riportate come scelte, NON come `[NEEDS CLARIFICATION]`.
  *(PASS — riquadro «Decisioni di scope già risolte»: provider, default, sorgente/licenza, manopola,
  distribuzione vettori, fail-loud, confine D↔N.)*
- [x] **CHK019** — Le domande aperte residue sono SOLO di design (come), non di scope (cosa). *(PASS —
  dimensione/algoritmo lessicale, aggregazione token→vettore, struttura cache, forma evento osservabilità,
  sorgente download/proxy: tutte di design; nessuna ambiguità di scope.)*
- [x] **CHK020** — Nessun `[NEEDS CLARIFICATION]` bloccante senza default ragionevole. *(PASS — nessun
  `[NEEDS CLARIFICATION]`; le forche residue sono tutte di design e rinviabili al plan senza bloccare il
  cosa/perché.)*
