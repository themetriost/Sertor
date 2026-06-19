# Requisiti — Visibilità del RAG nella TUI (dimostrabilità)

<!-- Deriva da: FEAT-015 (epica `osservabilita`) — realizza l'opt-in raw-text REQ-E9/E8 dell'epic.md -->

## 1. Contesto e problema (perché)

La TUI di osservabilità (F3/F4) e lo store F1 mostrano oggi **conteggi e metadati** delle operazioni
(`retrieve`/`hybrid_query`: `results`/`fused_k`, `provider`, `elapsed_ms`; `embeddings`: `tokens`),
ma **mai il testo della query né il contenuto dei risultati** — per privacy-by-default (REQ-E8: di
default solo metriche, niente testo). Questo rende difficile **vedere e dimostrare come il RAG sta
funzionando**: non si vede *cosa* è stato chiesto, *cosa* è tornato, e se quella specifica query è
andata a buon fine (hit) o a vuoto (miss).

Le **operazioni MCP** sono già catturate come eventi (`mcp.<tool>`, es. `mcp.search_code`,
`mcp.find_symbol`), ma anch'esse senza il testo/argomenti.

**Decisione cardine dell'utente:** i dati sono **locali**; chi lancia la TUI ha gli **stessi
privilegi** di chi usa la LLM, quindi **per uso locale non c'è niente da nascondere**. La feature
**rilassa la privacy-by-default come OPT-IN esplicito** (il default resta privacy-safe): realizza
l'opt-in raw-text già previsto dall'epica (REQ-E9). **Scopo = dimostrabilità/spiegazione del RAG, NON
audit/controllo/tracciamento.**

## 2. Obiettivi e criteri di successo

- **OBJ-1:** con l'opt-in attivo, dalla TUI si **vede** per le operazioni di retrieval recenti: il
  **testo della query**, il **risultato**, e un **verdetto hit/miss**.
- **OBJ-2:** dalla TUI si vedono le **operazioni MCP** (quale tool) associate alla loro query/risultato.
- **OBJ-3 (privacy preservata):** con l'opt-in **spento** (default), il comportamento è **identico a
  oggi** (solo conteggi/metadati, nessun testo persistito).
- **CS-1:** con opt-in on, dopo N ricerche la TUI mostra N voci con query+risultato+verdetto.
- **CS-2:** con opt-in off, in **0** casi compare testo di query/contenuto (store e TUI invariati).
- **CS-3:** i segreti non compaiono mai nel testo persistito (scrub applicato).
- **CS-4:** su un ospite terzo il default resta privacy-by-default (relax = opt-in locale esplicito).

## 3. Stakeholder e attori

- **Owner/dev locale (tu):** usa la TUI per *vedere e dimostrare* il funzionamento del RAG.
- **Chi valuta/demo del RAG:** vuole capire a colpo d'occhio cosa è stato chiesto e cosa è tornato.
- **L'agente LLM / il server MCP:** sorgenti delle operazioni osservate.
- **Lo strato osservabilità (F1/F2/TUI):** consumatore; va esteso in modo additivo.

## 4. Ambito

### In ambito
- **Opt-in raw-text**: cattura del **testo della query** (ed eventuale risultato) negli eventi/store,
  **solo** quando l'opt-in è attivo, con scrub segreti.
- **Vista TUI di dimostrabilità**: query · operazione MCP · risultato · verdetto **hit/miss**, per le
  operazioni di retrieval recenti.
- **Associazione** query ↔ risultato ↔ (eventuale) operazione MCP ↔ verdetto, per la stessa ricerca.
- **Verdetto hit/miss** derivato dai segnali esistenti.

### Fuori ambito
- **Audit / access-control / attribuzione per-utente / a prova di manomissione** (NON è lo scopo).
- **Ricerca semantica** sul contenuto persistito (resta opt-in ulteriore, REQ-E9 — qui basta
  full-text/lettura locale).
- **Rilassamento del default su ospiti terzi** (il default resta privacy-by-default ovunque).
- **Export del contenuto** verso OTel/altri backend (l'export resta metrics-only; vedi NFR).
- Il *come* (schema store, correlazione tecnica, widget Textual): fase di **design**.

## 5. Requisiti funzionali (EARS)

### Cattura opt-in del contenuto
- **REQ-001 (Optional):** *Where content visibility is explicitly enabled, the system shall persist the
  query text of retrieval operations so the panel can display it.*
- **REQ-002 (Unwanted):** *If content visibility is not enabled, then the system shall not persist any
  query text or result content (privacy-by-default, identical to today).*
- **REQ-003 (Ubiquitous):** *The persisted query text shall be passed through the existing secret
  scrubbing, so no secret ever appears in the stored content.*
- **REQ-004 (Optional):** *Where content visibility is enabled, the system shall apply a configurable
  retention to the persisted content, bounded by a recent-entries count (default conservative).*
  (Risolta: retention **a numero di voci recenti**, configurabile.)

### Vista TUI (dimostrabilità)
- **REQ-005 (Optional):** *Where content visibility is enabled, the TUI shall present, for recent
  retrieval operations, the query text, its result, and a hit/miss verdict.*
- **REQ-006 (Optional):** *Where content visibility is enabled, the TUI shall present the MCP operation
  (the invoked tool) associated with its query and result.*
- **REQ-007 (Ubiquitous):** *The TUI shall associate, for a single retrieval, its query, its result,
  its hit/miss verdict and (when applicable) the originating MCP operation.* (Associazione confermata;
  il **criterio di correlazione** è materia di design.)
- **REQ-008 (Ubiquitous):** *The TUI shall classify each retrieval as one of THREE states:* **hit**
  (≥1 result above the `min_score` threshold), **miss** (0 results), **abstained** (candidates existed
  but all below threshold → `low_confidence`). (Risolta: 3 stati hit/miss/astenuto.)
- **REQ-009 (Ubiquitous):** *The TUI shall show, for a query, the **top-k results as path + score**,
  plus a **short snippet of the top-1** result.* (Risolta: path+score dei top-k + snippet del 1°;
  snippet per-ogni-risultato resta Could.)
- **REQ-010 (Ubiquitous):** *The demonstrability view shall live in a **dedicated TUI tab** (e.g.
  "RAG"/"Queries"), populated only when content visibility is enabled; it shall be presented as
  observe/demonstrate, NOT as an audit log (no per-user attribution, no tamper-evidence). The existing
  "Live" tab stays metrics-only.* (Risolta: scheda dedicata nuova.)

### Gate e default
- **REQ-011 (Ubiquitous):** *Content visibility shall be governed by a single, **dedicated** explicit
  opt-in, defaulting to OFF (privacy-safe), and shall require the observability store to be enabled
  (the content lives in the store).* (Risolta: manopola dedicata, default off, dipende dallo store.)
- **REQ-012 (Unwanted):** *If the capability is installed on a third-party host, then the default shall
  remain privacy-by-default — the relaxation is an explicit local opt-in, never enabled by default.*

## 6. Requisiti non funzionali
- **NFR-01 (additività):** la cattura è additiva sugli eventi/store esistenti; F1/F2 e i loro test
  restano verdi; `log_event`/firma invariati nel percorso default.
- **NFR-02 (privacy-by-default):** il default NON cambia; il contenuto esiste solo con opt-in esplicito;
  scrub segreti sempre applicato.
- **NFR-03 (confine export):** l'export OTel (FEAT-005) resta **metrics-only** anche con questo opt-in,
  salvo decisione esplicita separata (qui fuori ambito).
- **NFR-04 (host-agnostico / thin consumer):** funziona su qualunque ospite via config; la TUI resta un
  consumatore sottile del core; `sertor-core` resta importabile.
- **NFR-05 (non-bloccante/non-fatale):** la cattura non rallenta né fa fallire il percorso caldo.
- **NFR-06 (offline):** nessuna rete nel percorso di cattura/visualizzazione del contenuto locale.

## 7. Vincoli, assunzioni e dipendenze
- **Dipendenza:** realizza REQ-E9 dell'epica `osservabilita` (opt-in raw-text + scrub + retention).
- **Assunzione (cardine, utente):** per uso **locale** TUI-user ≡ LLM-user → nessun segreto *aggiuntivo*
  esposto dal mostrare la query (il contenuto del repo è già accessibile a entrambi).
- **Deciso:** sotto l'opt-in, gli eventi MCP (`mcp.<tool>`) **includono l'argomento query**, così la
  vista mostra *cosa* è stato chiesto via MCP (default off: nessun argomento persistito).
- **Vincolo:** il verdetto hit/miss usa segnali **già presenti** (`results`/`fused_k`, `low_confidence`,
  soglia `min_score`) — nessun nuovo concetto di retrieval.

## 8. Rischi
- **R-1 (deriva verso audit):** la feature potrebbe essere percepita/usata come tracciamento. *Mitig.:*
  scopo dichiarato (dimostrabilità), nessuna attribuzione per-utente, default off, doc esplicita.
- **R-2 (esposizione segreti nel testo):** una query potrebbe contenere un segreto. *Mitig.:* scrub
  già esistente esteso al contenuto (come REQ-E9/scrub memoria); ripiego conservativo.
- **R-3 (crescita store col contenuto):** il testo pesa più dei conteggi. *Mitig.:* retention
  configurabile (REQ-004); opt-in.
- **R-4 (default sbagliato su ospite):** rischio di accendere il contenuto fuori dal locale. *Mitig.:*
  REQ-012, default off ovunque, opt-in esplicito.

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, 002, 003, 005, 008, 011, 012 (opt-in capture + privacy default + vista
  query/risultato/hit-miss + gate).
- **Should:** REQ-004 (retention), REQ-006 (operazioni MCP nella vista), REQ-007 (associazione esplicita).
- **Could:** REQ-009 con snippet di contenuto (oltre path/score), scheda TUI dedicata ricca.
- **Won't (qui):** audit/attribuzione, ricerca semantica sul contenuto, export del contenuto via OTel,
  relax del default su ospiti.

## 10. Domande aperte — RISOLTE (2026-06-19, utente)
1. **Hit/miss** → ✅ **3 stati**: hit (≥1 sopra soglia) · miss (0 risultati) · **astenuto**
   (`low_confidence`, candidati sotto soglia). *(REQ-008)*
2. **Cosa mostrare del risultato** → ✅ **top-k path + score** + **snippet del 1°**; snippet per ogni
   risultato resta Could. *(REQ-009)*
3. **Gate** → ✅ **manopola dedicata, default off**, richiede lo store osservabilità attivo. *(REQ-011)*
4. **Superficie TUI** → ✅ **scheda dedicata nuova** (es. "RAG"); "Live" resta metriche. *(REQ-010)*
5. **Operazioni MCP** → ✅ sotto opt-in gli eventi `mcp.<tool>` **includono l'argomento query**. *(REQ-006/§7)*
6. **Retention** → ✅ **a numero di voci recenti**, configurabile, default conservativo. *(REQ-004)*

> Forche di design rimaste (→ `/speckit-plan`, non di scope): il **criterio di correlazione**
> query↔risultato↔MCP-op; il nome esatto della manopola; lo schema di persistenza del contenuto.
