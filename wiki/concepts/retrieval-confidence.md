---
title: Confidence signal & score threshold (grounding lever)
type: concept
tags: [retrieval, grounding, abstention, confidence, soglia, hardening, feat-018]
created: 2026-06-13
updated: 2026-06-13
sources: [requirements/sertor-core/hardening-produzione/requirements.md, specs/018-hardening-retrieval/plan.md, src/sertor_core/services/retrieval.py]
---

# Confidence signal & score threshold (grounding lever)

Il **segnale di confidenza** è il modo con cui Sertor dice all'agente consumer *«il retrieval qui è
debole»*, così l'agente può **astenersi** invece di rispondere su contesto irrilevante. È l'anello di
grounding che spetta al retriever nel [[mission-vision|modello agentico composito]]: l'*atto* di
astenersi resta dell'agente (genera lui), ma il *materiale* per astenersi — sapere quando il corpus
non è vicino alla query — è responsabilità di Sertor. Prima della feature 018 mancava: si restituiva
sempre top-k, anche fuori dominio (gap B1 del RAG production audit, 2026-06-13).

## Come funziona (feature 018, Must)

- **Manopola unica:** `Settings.retrieval_min_score` (env `SERTOR_MIN_SCORE`), **soglia di similarità
  coseno**. Default `None` ⇒ disattivata ⇒ comportamento storico invariato (retro-compatibilità).
- **Filtro:** funzione pura `apply_min_score(results, min_score)` in `services/retrieval.py` — esclude
  i risultati con `score < soglia` e segnala `low_confidence` quando c'erano candidati ma nessuno
  supera la soglia. Riusata da facade e motori (DRY).
- **Segnale:** la **lista (filtrata) vuota** è il materiale di astensione consumer-detectable; in più
  un evento strutturato `low_confidence` (collection, provider, soglia, best_score) per l'osservabilità.
  Il contratto `RetrievalResult` e le firme `search_*`/`query` **non cambiano** (additivo): chi ignora
  il segnale continua a ricevere liste.

## L'asimmetria denso ↔ RRF (decisione chiave)

La soglia è una **similarità coseno**. Si applica direttamente dove lo `score` *è* una similarità:
facade (percorso denso + multi-collection) e [[indexing-and-retrieval|baseline]]. Ma nello
[[hybrid-retrieval|motore ibrido]] lo score finale è **RRF** (rank-based, `Σ 1/(c+rank)`), **non** una
similarità: applicarvi una soglia di coseno sarebbe semanticamente errato. Quindi nell'ibrido la soglia
filtra il **pool denso prima della fusione RRF**; se il ramo denso si svuota → astensione (`[]` +
`low_confidence`). È un'asimmetria **voluta**, sorella di quella tollerante↔strict del nucleo: non va
"uniformata".

## Confine e seguito

- **Non** è generazione né abstention-nella-risposta (quelle sono del consumer — vedi
  [[mission-vision]], [[thin-consumer]]).
- Un esito-oggetto ricco con `.confidence` esplicito (per distinguere «fuori dominio» da «indice
  vuoto») è un **Could differito**: oggi lista-vuota + log è sufficiente.
- Compagno di feature: la **resilienza degli embedder** (retry+backoff, stessa 018) — vedi il record
  datato e `requirements/sertor-core/hardening-produzione/` per gli incrementi Should/Could.
