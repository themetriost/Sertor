# Research — 145 memoria semantica: turni grandi e rifiuti del provider

Tutte le decisioni sono ancorate al codice esistente (`src/sertor_core/services/memory_semantic.py`,
`services/chunking/_tokens.py`, `adapters/embeddings/_openai_protocol.py`, `cli/output.py`). Nessuna
incognita esterna: niente da ricercare fuori dal repo.

## R-1 — Come si spezza un turno oltre il budget

- **Decision:** riusare `cap_to_tokens(text, settings.max_chunk_tokens, settings.chunk_overlap)` da
  `services/chunking/_tokens.py`, la stessa funzione che il corpus applica ai suoi pezzi
  (`chunking/dispatch.py::_cap_oversized`).
- **Rationale:** un solo tetto e un solo conteggio dei token per tutto il prodotto (DRY, Principio III e
  VIII): `SERTOR_MAX_CHUNK_TOKENS` vale già per il corpus, è documentato, ha un ripiego prudente senza
  `tiktoken` (~2 caratteri/token, sovrastima) e non serve una manopola nuova.
- **Alternatives considered:** una manopola dedicata alla memoria (`SERTOR_MEMORY_MAX_TOKENS`) — YAGNI:
  il limite è del **modello di embedding**, che è lo stesso per corpus e memoria sullo stesso nodo;
  troncare — scartato in spec (perde il contenuto da ritrovare).

## R-2 — Identità dei pezzi e compatibilità con gli indici esistenti

- **Decision:** un turno entro il budget conserva `chunk_id = f"{session_key}#{turn_index}"` e il payload
  attuale, byte per byte. Un turno spezzato produce `f"{session_key}#{turn_index}/{part}"` (`part` da 0)
  con payload esteso da `part` e `parts`.
- **Rationale:** FR-002/REQ-036 — gli indici già costruiti restano validi senza rebuild; i turni persi in
  passato non hanno alcun id presente e risultano nuovi al run successivo. Gli id restano deterministici
  (Principio VI): stesso testo + stesso budget → stessi pezzi → stessi id, `upsert` idempotente.
- **Alternatives considered:** id con pezzo anche per i turni non spezzati (`#i/0`) — romperebbe
  l'incrementalità di ogni indice esistente (tutto ri-embeddato una volta); bump della versione di
  logica della collezione — stesso costo, nessun beneficio.

## R-3 — Incrementalità con la nuova granularità

- **Decision:** si calcolano prima le unità di ogni turno, poi si interroga `contains_ids` su **tutti** gli
  id delle unità; un turno è «già indicizzato» se tutti i suoi id sono presenti.
- **Rationale:** NFR-009 della 072 (zero chiamate al provider su un indice completo) resta vero; il costo
  aggiunto è la tokenizzazione locale dei turni, trascurabile rispetto a una chiamata HTTP.
- **Note:** un cambio di `SERTOR_MAX_CHUNK_TOKENS` cambia i pezzi dei soli turni spezzati: i loro nuovi
  id risultano assenti e vengono embeddati; i vecchi pezzi restano orfani nella collezione. Effetto
  accettato (caso raro, nessuna risposta sbagliata: la deduplicazione per turno di R-5 assorbe i
  doppioni); lo stesso accade oggi al corpus fino al prossimo rebuild.

## R-3b — Un turno indicizzato intero resta indicizzato (seguito, branch 146)

- **Trovato sul campo, dopo il merge (2026-10-20):** il primo run sul dogfood ha dato
  `embedded=237 skipped=13548` invece dei previsti `175 / 13610`. Causa: il runtime `.sertor/` non ha
  l'extra `tokenizer`, quindi `cap_to_tokens` usa la stima prudente (~2 caratteri/token). Turni fra
  ~16.000 e ~30.000 caratteri, che il modello aveva **accettato interi**, risultavano «oltre il budget»:
  venivano spezzati, ri-embeddati (62) e il loro record intero restava orfano. FR-002 era rispettato
  solo con il tokenizzatore preciso.
- **Decision:** un turno è «già indicizzato» anche se il suo id **intero** (`session_key#turn_index`) è
  nella collezione, qualunque sia la scomposizione calcolata oggi. Il probe di incrementalità chiede
  anche gli id interi.
- **Rationale:** il fatto che il provider abbia già accettato il turno intero è la prova più forte che
  rientrava nel limite; il conteggio dei token di oggi è una stima. Vale anche quando l'utente abbassa
  `SERTOR_MAX_CHUNK_TOKENS`: non si rifà ciò che è già valido.
- **Effetto residuo sul dogfood:** i 62 record interi orfani e i pezzi creati prima di questo seguito
  restano nella collezione (doppioni assorbiti dalla deduplicazione per turno in ricerca). Nessuna
  azione: un ospite che aggiorna direttamente alla versione con il seguito non li crea.

## R-4 — Isolare un rifiuto

- **Decision:** il percorso normale resta **un** `embed()` per sessione sui pezzi nuovi. Se solleva
  `EmbeddingError` con un motivo di **rifiuto dell'input** — `http 400`, `http 413`, `http 422`, gli
  stessi codici per `openai`, `azure` e `ollama`, che classificano già l'errore come
  `reason=f"http {status}"` — si passa al ripiego: per ogni turno nuovo, si embeddano i suoi
  pezzi **uno per chiamata**; un turno con anche un solo pezzo rifiutato è registrato come rifiutato e
  nessun suo pezzo è scritto (tutto o niente). Se durante il ripiego arriva un errore `retriable=True`, il
  ripiego si ferma e i turni rimanenti contano come `provider_unavailable`. Ogni altro errore iniziale
  (rete, `429`/`5xx`, ma anche `401`/`403`/`404`) mantiene il comportamento di oggi: tutti i turni nuovi
  in errore, motivo `provider_unavailable`, nessun ripiego.
- **Rationale:** i codici 400/413/422 dicono «questo testo», gli altri dicono «il servizio o la
  configurazione»: ripiegare su una chiave errata (`401`) moltiplicherebbe chiamate destinate a
  fallire tutte e registrerebbe come «rifiutato» ogni turno. Pezzo per chiamata invece di turno per
  chiamata: un turno spezzato in molti pezzi potrebbe superare il limite **per richiesta** del provider
  anche con pezzi singolarmente validi.
- **Alternatives considered:** usare `retriable=False` come criterio (include `401`, vedi sopra);
  bisezione del batch (meno chiamate, più complessità — YAGNI per un percorso raro); ripiego anche sugli
  errori ritentabili (martellerebbe un servizio giù, contro `FR-006`).

## R-5 — Un risultato per turno in ricerca

- **Decision:** `_results_to_hits` deduplica per `(session_key, turn_index)` tenendo il primo (il più
  pertinente, perché lo store restituisce in ordine di punteggio); la query chiede `2 × limit` candidati
  per compensare i doppioni prima del taglio.
- **Rationale:** REQ-010/FR-003: l'unità di citazione resta il turno.

## R-6 — Esito e osservabilità

- **Decision:** `SemanticIndexReport` guadagna `rejected: tuple[RejectedTurn, ...] = ()`. L'output CLI
  aggiunge righe/campo **solo se** ci sono rifiuti: con zero rifiuti l'esito è byte per byte quello di
  oggi (compatibilità con chi lo analizza). Gli eventi: `memory_semantic_index_failed` con
  `reason=input_rejected`, `detail=<motivo>`, `rejected=<n>` (nessun id di sessione); l'evento finale
  `memory_semantic_index` aggiunge il conteggio `rejected`.
- **Rationale:** REQ-035 + REQ-026; il dettaglio per sessione/turno serve a chi lancia il comando, gli
  eventi servono alle metriche.
- **Alternatives considered:** campo `rejected` sempre presente nel JSON — più regolare, ma cambierebbe
  l'esito di ogni run esistente; scelta la compatibilità.
