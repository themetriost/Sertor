---
title: Dedup dei risultati near-duplicate (collasso a query-time)
type: concept
tags: [retrieval-qualita, dedup, near-duplicate, shingle, containment, top-k, feat-003, e5, retrieval, doc-correlati]
created: 2026-07-21
updated: 2026-07-21
sources: ["specs/090-retrieval-result-dedup/plan.md", "src/sertor_core/services/dedup.py", "wiki/log/2026-07-07.md", "wiki/log/2026-07-08.md"]
---

# Dedup dei risultati near-duplicate

La leva che impedisce alle **copie dello stesso contenuto** di saturare il top-k del retrieval,
seppellendo la pagina canonica attesa. È E5-FEAT-003 dell'epica [[roadmap|retrieval-qualita]], branch
`090-retrieval-result-dedup`, nata come *quick win* dall'audit SWOT A-07. Funzione **pura**
`dedup_results` in `src/sertor_core/services/dedup.py`, applicata a **query-time** dietro la manopola
`SERTOR_DEDUP` (default on).

## Il problema che chiude

Lo stesso testo vive spesso in **più path** dello stesso corpus. Il caso reale colto in dogfooding: i
blocchi di governance di `CLAUDE.md` sono **byte-identici** alle copie bundlate sotto `assets/**`
dell'installer (`assets/claude-md-block.md`, `assets/rag/claude-md-block-rag-usage.md`). Il retrieval
li restituiva **entrambi** ai primi ranghi, spingendo le pagine-concetto canoniche in basso
(`wiki/concepts/step-ritual.md` → rank 4, `constitution.md` → rank 6). *Ironia:* l'asset-install (E15),
aggiungendo a `CLAUDE.md` blocchi identici al bundle, ha **peggiorato** la duplicazione. La causa non è
l'algoritmo di ranking ma la **duplicazione di contenuto nel corpus** — `.claude` era già in
`SERTOR_EXCLUDE_PATTERNS`, `assets` no. Escludere `assets` è il rimedio *dogfood-specifico*; il **fix di
prodotto** vale per ogni host che ha `CLAUDE.md` + wiki: collassare i near-duplicate nel top-k.

## Perché l'MVP esatto ha fallito (misura-prima ha ribaltato l'ipotesi)

Il valore della disciplina *misura-prima* è emerso qui in modo netto. L'MVP **esatto** (sha1 sul testo
normalizzato del chunk) sembrava la scelta ovvia, ma ha dato lift **marginale**: `search_docs` @5
0.75→0.88 ma **hit@3 invariato**, gate rosso. Causa **verificata dal vivo**: lo stesso blocco chunkato
da `CLAUDE.md` (chunk immerso, confini a metà file) vs da `assets/claude-md-block.md` (chunk #0, file a
sé) ha **confini diversi** → i testi-chunk non sono byte-identici → l'hash esatto **non li collassa**, ed
entrambe le copie restavano a rank 1-2 anche con dedup on. L'ipotesi MVP («l'esatto basta») era falsa: la
duplicazione è *documentale*, non *testuale*.

## Il meccanismo: shingle + containment coefficient

L'estensione a **fuzzy** consegna il lift. Test di similarità su **word-shingle** con **coefficiente di
containment**, puro e deterministico, **zero LLM e zero embedding aggiuntivi**:

- **Shingle**: insiemi di shingle da **5 parole** sul testo con whitespace collassato (robusto a
  CRLF↔LF/indentazione), **case-preserving** (le byte-copie condividono il case). Testi più corti di uno
  shingle → un unico shingle = l'intero testo normalizzato, così i risultati brevi si matchano
  **esattamente** (nessun over-merge fuzzy su poche parole).
- **Containment** = |a ∩ b| / min(|a|, |b|): misura quanta parte dell'insieme *più piccolo* è contenuta
  nel più grande. È la scelta chiave: un chunk più corto interamente coperto da uno più lungo (stesso
  blocco, confini diversi) segna ~1.0 anche se le dimensioni differiscono — dove Jaccard fallirebbe.
  Soglia **0.8**: alta abbastanza da non collassare risultati genuinamente distinti, bassa abbastanza da
  catturare lo stesso blocco chunkato con confini diversi.

`dedup_results` tiene la **prima** occorrenza (la più in alto: l'input è già rank-ordinato) di ogni
gruppo near-duplicate e scarta le altre; è **no-op** su risultati già distinti (`removed_count == 0`) e
pienamente deterministica.

## Dove si applica: prima del cut, con pool > k

La dedup gira a **query-time** nei **5 siti** di retrieval (ibrido main+fallback, facade fallback+fused,
[[hybrid-retrieval|baseline]]) **prima del cut al top-k** — l'indicizzazione è invariata. **Punto
critico:** serve un **pool > k** (riusa `rerank_pool`) o la dedup ridurrebbe i risultati sotto k senza
**backfill**. Con il pool ampio, collassare 2 duplicati fa risalire risultati veri dal pool. La manopola
`Settings.dedup_enabled` (`SERTOR_DEDUP`, default on) tiene la leva additiva e a costo/comportamento
identico a spenta.

## Lift consegnato

`search_docs` **hit@3 0.62→0.75** (baseline ristabilito), MRR 0.55→0.57; `search_code` **intatto** (no
falso-dedup — SC-004); **gate `--fused` PASS**. Il gate **non** è stato ri-baselinato per far passare: è
verde perché il lift è reale (Principio XII, il segnale non si seppellisce). La misura sul **runtime
installato** post-merge (non solo editable) ha confermato l'A/B: dedup ON → @5 0.88, union 1.00.

## La leva residua distinta: «doc-correlati»

La misura post-merge ha rivelato — onestamente — **più del previsto**. Sul corpus fresco (cresciuto coi
+10 doc dello stesso merge: spec 090, log), `search_docs` **hit@3 = 0.625 con dedup ON *e* OFF**: la
dedup funziona (@5 0.88), ma **@3 non si muove** perché il doc atteso è ora scavalcato da contenuto
**diverso, non duplicato** — spec e log **della stessa feature** che competono col concetto atteso al
confine k=3. Questa è la **competizione tra doc correlati**, una leva **distinta** dal dedup: per
costruzione il dedup non tocca i non-duplicati. Richiede un rimedio separato — **contextual retrieval /
diversity re-ranking / query-handling** — ed è tracciata in roadmap (E5) da attivare **solo se mostra un
lift misurato**. NB a scala: ad ogni merge il corpus cresce e sposta i ranking al confine k, quindi
`hit@3` è **intrinsecamente rumoroso**; l'`union hit-rate` (metrica della fusione = la missione) resta il
segnale robusto (1.00).

## Confini

Collassa duplicati **resi** all'agente; **non** deduplica l'indice (l'indicizzazione è invariata), **non**
esclude path dal corpus (quello è config d'host, `SERTOR_EXCLUDE_PATTERNS`), e **non** affronta la
competizione tra doc correlati (leva separata). Follow-up tracciati: near-dup a scala (MinHash) e la leva
doc-correlati.

## Pagine collegate
[[valutazione-e-non-regressione]] · [[hybrid-retrieval]] · [[retrieval-core]] · [[dogfooding]] · [[roadmap]]
