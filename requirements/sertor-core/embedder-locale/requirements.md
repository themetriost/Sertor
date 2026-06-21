# Requisiti — Embedder locale (local-first per indicizzazione, eval e CI)

<!-- Deriva da: FEAT-011 (epica sertor-core) -->

## 1. Contesto e problema (perché)

Per **indicizzare** un progetto Sertor serve **sempre** un provider di embeddings: la pipeline di
indicizzazione embedda i chunk per popolare il vector store (`build_embedder` in
`src/sertor_core/composition.py:63`). Oggi i due provider disponibili sono **Ollama** (modello locale)
e **Azure OpenAI** (cloud). In molti **contesti enterprise**, abilitare *uno qualsiasi* dei due —
installare/eseguire un model server come Ollama, **oppure** ottenere credenziali e quota su
Azure/Foundry — richiede **cicli di autorizzazione, security/legal review, budget**. Finché quei
cicli non si chiudono, **Sertor non si può nemmeno avviare**: senza embedder non c'è indicizzazione,
e senza indice non c'è retrieval.

Serve quindi un **profilo base davvero local-first**: un provider di embeddings **deterministico,
senza modello e senza credenziali**, che permetta a un ospite di **indicizzare e cercare da subito**,
con un **percorso di upgrade pulito** verso Ollama/Azure quando le autorizzazioni arrivano. Questo
onora il **Principio II (local-first)** e la **missione** (framework installabile *ovunque*, sui tre
profili `code+doc` / `doc-only` / `code-only`).

Beneficio collaterale rilevante: un provider deterministico rende il **gate di non-regressione
dell'eval** (FEAT-001/011 dell'epica `retrieval-qualita`) **eseguibile senza rete** — **prerequisito
della CI** (epica `debito-tecnico`, FEAT-003), che non deve dipendere da Azure/Ollama.

La feature introduce **due provider locali** che coprono due esigenze distinte:

- un provider **lessicale puro** (zero-dipendenze, zero-download), **pavimento** per ambienti
  *airgapped*/offline e per la CI;
- un provider a **vettori statici pre-addestrati** (semantica NL superficiale), **nuovo default**,
  che serve in particolare gli host **doc-heavy** e il profilo **doc-only**, dove il segnale
  lessicale è più debole e la semantica conta di più (coerente col differenziatore *fusione
  code+doc* della missione).

## 2. Obiettivi e criteri di successo

- **CS-1** Su una macchina **senza Ollama, senza credenziali cloud e senza alcuna configurazione di
  provider**, un ospite riesce a **indicizzare e cercare** un corpus con un solo comando, senza
  modificare codice.
- **CS-2** In ambiente **airgapped/offline** (nessuna rete), esiste **almeno un** provider che
  indicizza e cerca **senza alcun download**.
- **CS-3** A parità di input (testo, provider, dimensione, file di vettori), gli embeddings prodotti
  sono **deterministici e ripetibili** (stessa run → stessi vettori); per il provider lessicale anche
  **cross-macchina e cross-versione Python**.
- **CS-4** La scelta del provider avviene **solo via configurazione**; il comportamento dei provider
  esistenti (Ollama/Azure) è **invariato** quando non si seleziona un provider locale nuovo.
- **CS-5** Quando un provider non può operare (es. vettori statici richiesti ma assenti e senza rete),
  il sistema **fallisce in modo rumoroso e azionabile** (nomina le vie d'uscita), **mai** in silenzio
  e **mai** degradando di nascosto a un altro provider.
- **CS-6** Le manopole introdotte sono **installabili**: compaiono nel template `.env` dell'installer
  e nella documentazione utente, con **nota di migrazione** sul cambio di default.

## 3. Stakeholder e attori

- **Operatore ospite** (chi installa/usa Sertor su un progetto terzo, spesso in contesto enterprise
  vincolato): vuole valore immediato senza cicli di autorizzazione.
- **Ufficio legale/security dell'ospite**: deve poter approvare gli artefatti (licenza e provenienza
  dei dati) senza review onerose.
- **CI / manutentore** (epica `debito-tecnico`): vuole un gate di non-regressione deterministico,
  offline, senza cloud.
- **Agente / flusso principale**: consuma il retrieval via i *vehicles* (CLI/MCP), non sceglie il
  provider a runtime se non via config.

## 4. Ambito

### In ambito

- Due nuovi provider di embeddings locali e deterministici dietro la porta `EmbeddingProvider`
  esistente:
  - **lessicale** (char-n-gram hashing), solo libreria standard, zero-download;
  - **vettori statici** (GloVe 6B, dimensione 300, licenza **PDDL**/pubblico dominio), **default**.
- Una **manopola di selezione dedicata** del provider di embeddings, con i valori per i quattro
  provider (i due nuovi + i due esistenti), come **unica** superficie di scelta.
- **Semplificazione della configurazione:** **rimozione di `RAG_BACKEND`** (master-switch ambiguo che
  selezionava sia il provider sia, di default, lo store). Restano due manopole **ortogonali**: la
  selezione dell'embedder (questa feature) e la selezione dello store (già esistente,
  `SERTOR_STORE_BACKEND`), quest'ultima con un proprio default sul local store.
- **Acquisizione on-demand** del file di vettori statici alla **prima indicizzazione**, con **cache
  utente condivisa per-macchina** e **override** di un percorso fornito dall'utente (airgapped).
- **Diagnostica fail-loud** (errori azionabili e avvisi) coerente col Principio XII.
- **Corollario installabile**: manopole nel template `.env` dell'installer, documentazione utente,
  nota di migrazione per il cambio di default.

### Fuori ambito

- La **CI vera** (workflow `.github/workflows`) — appartiene all'epica `debito-tecnico` (FEAT-003);
  qui si consegnano provider + manopole + test + template installabili che la abilitano.
- **Altre fonti di vettori statici** oltre GloVe (es. word2vec, fastText, Model2Vec): scartate per
  questioni di licenza/provenienza (CC BY-SA, file non licenziati, provenienza da web scraping) che
  reintrodurrebbero la frizione legale che la feature vuole eliminare; GloVe/PDDL è la scelta pulita.
- Qualsiasi **modello neurale locale** (es. sentence-transformers/torch): contraddice il vincolo
  zero-dipendenze.
- **Reranking, motori, code-graph**: non toccati (ortogonali).
- **Modifiche alla porta `EmbeddingProvider`, ai servizi o agli engine**: la feature è additiva e si
  innesta nel solo composition root + nuovi adapter.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Selezione del provider

- **REQ-001 (Ubiquitous):** *The system shall expose a dedicated configuration knob to select the
  embedding provider among at least four values: the two new local providers (lexical, static-vectors)
  and the two existing ones (Ollama, Azure).*
- **REQ-002 (Ubiquitous):** *The system shall default the embedding provider to the static-vectors
  (GloVe) provider when no provider is explicitly configured.*
- **REQ-003 (Event-driven):** *When the configured provider value is not one of the recognised
  values, the system shall raise an actionable configuration error that names the knob and the allowed
  values.*
- **REQ-004 (Ubiquitous):** *The system shall make the dedicated embedding-provider knob the SOLE
  selector of the embedding provider; the legacy `RAG_BACKEND` knob shall be removed and no longer
  consulted (single, unambiguous configuration surface).*
- **REQ-005 (Optional feature):** *Where a local provider (lexical or static-vectors) is selected,
  the static configuration validation shall report no required-but-missing fields (a local provider
  never blocks on credentials).*
- **REQ-006 (Ubiquitous):** *The system shall select the vector-store backend through its own
  dedicated knob, independent from the embedding provider, defaulting to the local store — so that
  embeddings provider and store backend remain fully orthogonal.*
- **REQ-007 (Unwanted):** *If the removed `RAG_BACKEND` variable is still present in the environment,
  then the system shall emit a warning that it is no longer honoured and name the replacement knobs
  (the embedding-provider knob and the store-backend knob), without silently changing behaviour.*

### Gruppo B — Provider lessicale (pavimento zero-download)

- **REQ-010 (Ubiquitous):** *The lexical provider shall produce embedding vectors using only the
  Python standard library, with no external model, no credentials and no network access.*
- **REQ-011 (Ubiquitous):** *The lexical provider shall derive each vector from character-level
  n-grams of the text, so that out-of-vocabulary tokens (e.g. code identifiers) still contribute
  signal.*
- **REQ-012 (Ubiquitous):** *The lexical provider shall output vectors of a fixed, stable dimension
  and shall expose a stable provider name that encodes that dimension.*
- **REQ-013 (Ubiquitous):** *The lexical provider shall be fully deterministic: identical input text
  shall yield identical vectors across runs, machines and Python versions* (no reliance on
  salted/process-specific hashing).
- **REQ-014 (State-driven):** *While the lexical provider is the active provider, the system shall
  emit a warning that natural-language (semantic) queries are limited and that GloVe/Ollama/Azure can
  be configured for semantic retrieval.*

### Gruppo C — Provider a vettori statici (GloVe, default)

- **REQ-020 (Ubiquitous):** *The static-vectors provider shall produce each text embedding from
  pre-trained GloVe word vectors (GloVe 6B, dimension 300), without running any model.*
- **REQ-021 (Ubiquitous):** *The static-vectors provider shall compose a text vector deterministically
  from the vectors of its tokens (token-vector aggregation), yielding stable output for identical
  input and a fixed vector dimension.*
- **REQ-022 (Ubiquitous):** *The static-vectors provider shall expose a stable provider name that
  encodes its dimension, distinct from other providers' names.*
- **REQ-023 (Event-driven):** *When a token has no GloVe vector (out-of-vocabulary), the provider
  shall handle it deterministically without failing the embedding call.*
- **REQ-024 (Ubiquitous):** *The static-vectors provider shall depend only on the GloVe data file and
  on dependencies imported lazily, so that selecting another provider neither downloads the file nor
  imports those dependencies.*

### Gruppo D — Acquisizione e cache dei vettori statici

- **REQ-030 (Event-driven):** *When the static-vectors provider is used for the first time during
  indexing and the vectors file is not present in cache, the system shall download the official GloVe
  data file before producing vectors.*
- **REQ-031 (Ubiquitous):** *The system shall store the downloaded GloVe vectors in a per-machine
  shared user cache (e.g. an XDG-style cache directory), reused across all projects and corpora.*
- **REQ-032 (Optional feature):** *Where the user provides an explicit path to a local GloVe vectors
  file, the system shall use that file and shall not attempt any download (airgapped support).*
- **REQ-033 (Event-driven):** *When the GloVe download starts, the system shall emit a one-time notice
  that a large data file (~822 MB) is being fetched.*
- **REQ-034 (Ubiquitous):** *The system shall not download or require the GloVe file at install time
  nor at query time when the cache already exists; acquisition is bound to indexing.*
- **REQ-035 (Event-driven):** *When a cached or user-provided GloVe file is present, the system shall
  reuse it without re-downloading.*

### Gruppo E — Diagnostica fail-loud (Principio XII)

- **REQ-040 (Unwanted):** *If the static-vectors provider is required but the vectors file is absent
  from cache, no user path is set, and the network is unavailable, then the system shall fail with an
  actionable error that names both escape hatches (set the explicit GloVe path, or select the lexical
  provider).*
- **REQ-041 (Unwanted):** *If acquiring or loading the GloVe file fails, then the system shall surface
  the error explicitly and shall not silently fall back to another provider.*
- **REQ-042 (Ubiquitous):** *The system shall record provider-selection and acquisition outcomes as
  structured observability events consistent with existing events (metrics-only, no secrets).*

### Gruppo F — Determinismo, isolamento, non-regressione

- **REQ-050 (Ubiquitous):** *The system shall keep both new providers behind the existing
  `EmbeddingProvider` port without changing the port, the services or the engines.*
- **REQ-051 (Ubiquitous):** *The system shall namespace stored vectors by `(corpus, provider)` so
  that vectors from different providers (different dimensions/semantics) are never mixed in the same
  collection.*
- **REQ-052 (Ubiquitous):** *The system shall preserve the existing behaviour of the Ollama and Azure
  providers unchanged when a local provider is not selected (additivity).*
- **REQ-053 (Ubiquitous):** *The system shall keep the lexical provider importable and usable with no
  optional extra installed, and shall import any static-vectors dependencies lazily.*

### Gruppo G — Host / installabile

- **REQ-060 (Ubiquitous):** *The installer shall include the new embedding-provider knob (and the
  GloVe path override) in the `.env` template it deposits on the host.*
- **REQ-061 (Ubiquitous):** *The user-facing documentation shall describe the four providers, the new
  default, the airgapped path override, and a migration note covering BOTH changes: (a) `RAG_BACKEND`
  is removed — the embedding provider is now selected only by the dedicated knob, and the store
  backend only by its own knob; (b) the default provider has changed (previously local-first implied
  Ollama; now it is the static-vectors provider; Ollama/Azure must be selected explicitly).*
- **REQ-062 (Ubiquitous):** *The evaluation/CI path shall obtain the embedding provider through the
  composition vehicle (`build_embedder`/composition), never by importing adapters directly outside
  tests (Principio XI).*

## 6. Requisiti non funzionali

- **RNF-1 (Determinismo):** output ripetibile per stessi input; il provider lessicale deterministico
  anche cross-macchina/cross-Python (hashing stabile, non salted).
- **RNF-2 (Isolamento dipendenze):** lessicale = solo stdlib; vettori statici = dipendenze importate
  in modo lazy; il core resta importabile senza scaricare GloVe.
- **RNF-3 (Local-first / privacy):** nessuna chiamata cloud e nessuna credenziale per i provider
  locali; nessun segreto negli eventi.
- **RNF-4 (Non-regressione):** zero impatto su costo/comportamento dei provider esistenti quando non
  selezionati; nessuna modifica fuori da composition + nuovi adapter + Settings + (eventuale)
  superficie di validazione/errori.
- **RNF-5 (Memoria):** footprint runtime del provider GloVe 300d coerente con l'ordine di grandezza
  atteso (≈ centinaia di MB), documentato; il lessicale ha footprint trascurabile.
- **RNF-6 (Costo):** nessun costo monetario per i provider locali; il download GloVe è una-tantum
  per-macchina.

## 7. Vincoli, assunzioni e dipendenze

- **Vincoli costituzionali:** Principio II (local-first), Principio X + corollario installabile,
  Principio XI (accesso via vehicle), Principio XII (fail-loud), additività (I/III), confine D↔N (il
  core resta deterministico, nessun LLM nel core).
- **Ancoraggio al codice esistente:** porta `EmbeddingProvider` (`src/sertor_core/domain/ports.py:26`);
  `build_embedder`/`build_store` (`src/sertor_core/composition.py:63`); `Settings` con `backend`/
  `embed_provider` (property derivata da `RAG_BACKEND`, `settings.py:211`), `validate_backend`
  (`settings.py:215`) e `load()` (`settings.py:238`, legge `RAG_BACKEND`/`SERTOR_STORE_BACKEND`);
  namespacing `(corpus, provider)` via `collection_name()`. **La rimozione di `RAG_BACKEND` tocca
  questi punti** (campo/property/validazione/load) — è una modifica di config additiva al netto della
  rimozione, da gestire con la nota di migrazione e l'avviso REQ-007. Precedente: `FakeEmbedder`
  (`tests/fixtures/mocks.py:24`) è un mock di test (hash d'identità), **distinto** dal provider
  lessicale di prodotto (che deve avere segnale lessicale).
- **Breaking change di config dichiarato:** la rimozione di `RAG_BACKEND` è un cambiamento
  incompatibile per gli ospiti che lo usano (incl. il dogfood: la `.sertor/.env` va aggiornata a
  `SERTOR_EMBED_PROVIDER=azure`); mitigato dall'avviso fail-loud (REQ-007) e dalla nota di migrazione
  (REQ-061).
- **Assunzione:** la distribuzione ufficiale GloVe 6B (`glove.6B.zip`, ~822 MB, contiene 50/100/200/300d)
  è raggiungibile dalla sorgente PDDL e redistribuibile; in airgapped si usa l'override di path.
- **Dipendenza a valle:** la CI col gate eval (epica `debito-tecnico` FEAT-003) consuma questa feature.

## 8. Rischi

- **R-1** Il file GloVe (~822 MB) può rendere la *prima* indicizzazione lenta o, in rete
  vincolata/proxy, fallire → mitigato da cache per-macchina, override di path e fail-loud azionabile.
- **R-2** Cambiare il **default** e **rimuovere `RAG_BACKEND`** può sorprendere/regredire ospiti
  esistenti (chi si attendeva Ollama dal local; chi selezionava il provider via `RAG_BACKEND`) →
  mitigato da nota di migrazione (REQ-061) e avviso fail-loud su `RAG_BACKEND` residuo (REQ-007).
- **R-3** Qualità NL del provider lessicale bassa per definizione → mitigato da default GloVe e da
  avviso che invita all'upgrade quando attivo il lessicale.
- **R-4** Determinismo del lessicale rotto da hashing salted di default di Python → mitigato dal
  requisito di hashing stabile (REQ-013).
- **R-5** Provenienza/licenza dei vettori contestata in audit enterprise → mitigato dalla scelta
  PDDL/pubblico dominio (esplicita in doc).
- **R-6** Mescolanza accidentale di vettori di provider diversi nella stessa collezione → mitigato dal
  namespacing `(corpus, provider)` (REQ-051).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001..007 (selezione + rimozione `RAG_BACKEND` + store con default proprio + avviso
  fail-loud su `RAG_BACKEND` residuo), REQ-010..014 (lessicale), REQ-040..042 (fail-loud),
  REQ-050..053 (determinismo/isolamento/non-regressione), REQ-062 (vehicle).
- **Must (default & semantica locale):** REQ-020..024 (GloVe provider), REQ-030..035 (acquisizione/
  cache/override) — sono il *nuovo default* e quindi parte del valore minimo.
- **Should:** REQ-060..061 (corollario installabile: template `.env`, doc, nota di migrazione) — da
  chiudere prima che la feature conti come *done* (regola "completa solo se installabile").
- **Could:** dimensione GloVe configurabile oltre il default 300d; verifica d'integrità (checksum) del
  file scaricato; helper CLI esplicito di pre-download.
- **Won't (qui):** CI vera (FEAT-003 `debito-tecnico`); altre sorgenti di vettori statici; modelli
  neurali locali.

## 10. Domande aperte

- Nessuna forca di prodotto aperta: scope, default (`glove`), sorgente/licenza (GloVe 6B 300d, PDDL),
  manopola dedicata (`SERTOR_EMBED_PROVIDER`) come **unica** superficie con **rimozione di
  `RAG_BACKEND`** (store via `SERTOR_STORE_BACKEND` con default proprio), distribuzione (download alla
  prima indicizzazione + cache utente condivisa + override path) e comportamento fail-loud sono **decisi**. I dettagli di
  *come* (nomi esatti delle manopole, dimensione del vettore lessicale, algoritmo di aggregazione
  token→vettore, struttura della cache) sono materia della fase di **plan/design**.
