# Requisiti — Parità MCP per la lettura della memoria (`memory list`/`show`/`search`)
<!-- Deriva da: E4-FEAT-010 (epica memoria-conversazioni) -->

## 1. Contesto e problema (perché)

L'archivio della memoria conversazioni (FEAT-001/002/003) è **leggibile solo dalla CLI**:
`sertor-rag memory list` (sessioni recenti), `memory show <key>` (una sessione), `memory search <q>`
(full-text FTS5, «ne avevamo già parlato?»). Il **server MCP** `sertor-rag` — la superficie **nativa**
con cui l'agente consuma Sertor — espone oggi **7 tool** (3 search sul corpus + 4 navigazione grafo) ma
**nessuno sulla memoria**.

Conseguenza: per interrogare la memoria episodica l'agente deve **uscire dall'MCP** e fare subprocess
sulla CLL. È in tensione con:
- il **valore dichiarato dell'epica** («memoria **interrogabile nativamente dall'agente**, non solo da
  terminale»);
- il **Principio XI / contratto pubblico** (i consumatori — specie esterni — usano l'**MCP**, non la CLI:
  l'MCP è il contratto rilasciato apposta perché l'esterno non dipenda dalla CLI, cfr.
  [[feedback_external_consumers_use_mcp_not_cli]]).

La lettura del corpus ha già la sua superficie MCP; la **memoria no**. Questa feature colma la parità
**di lettura**.

## 2. Obiettivi e criteri di successo

**Obiettivo:** l'agente può **elencare, aprire e cercare** nell'archivio della memoria **via MCP**, con la
stessa semantica e gli stessi gate di privacy della CLI, senza subprocess.

Criteri di successo (misurabili, tech-agnostici):
- **CS-1 (parità di lettura):** i tre read della CLI (`list`, `show`, `search` full-text) sono
  **esercitabili via MCP** e ritornano gli **stessi dati** (stessa sorgente, stesso ordinamento) della CLL
  a parità di archivio.
- **CS-2 (gate di privacy identico):** con `SERTOR_MEMORY` **spento** (default), i tool MCP di memoria
  **non leggono** l'archivio e ritornano uno **stato «disabilitato» esplicito** (né errore opaco, né lista
  vuota che si confonde con «nessun risultato»). Con `SERTOR_MEMORY=true` operano.
- **CS-3 (contenuto già scrubbato):** i tool restituiscono **solo** il contenuto già presente
  nell'archivio (scrubbed alla cattura); nessun nuovo path di persistenza né de-scrub.
- **CS-4 (citabilità):** ogni risultato porta l'identificatore che permette il passo successivo
  (`session_key` per aprire una sessione; sessione+turno per un hit di ricerca), coerente col principio
  «cita sempre» dei tool MCP esistenti.
- **CS-5 (thin, nessuna logica riscritta):** i tool delegano ai servizi core esistenti
  (`MemoryArchive.list_recent`/`get`, `EpisodicSearch.search`) senza reimplementare lettura o ricerca
  (Principio I, come i 7 tool attuali).
- **CS-6 (host-agnostico):** i tool operano su qualunque ospite senza modifiche al corpo; nessun assunto
  host-specifico (Principio X). Viaggiano col pacchetto (installabili per costruzione).

## 3. Stakeholder e attori
- **Agente LLM (consumatore primario):** interroga la memoria episodica **nativamente** durante il lavoro.
- **Consumatore esterno (tool/agente di terzi):** integra Sertor **via MCP** (contratto pubblico), non via CLI.
- **Owner/maintainer:** beneficia della memoria interrogabile senza cambiare superficie.
- **Server MCP `sertor-rag`:** ospita i nuovi tool accanto ai 7 esistenti.

## 4. Ambito

### In ambito
- **Tre tool MCP di sola lettura** sulla memoria, parità coi read CLI:
  - **list** — sessioni archiviate recenti (key, istante, #turni), limite configurabile;
  - **show** — una sessione per `session_key` (turni: ordine/ruolo/timestamp/testo);
  - **search** — ricerca episodica **full-text** (FTS5): hit turno-granulari (sessione, ruolo, turno,
    snippet, score), limite configurabile.
- **Gate di privacy** identico alla CLI (`SERTOR_MEMORY`): spento → stato «disabilitato» esplicito.
- **Degradazione non-fatale** coerente col resto dell'MCP (archivio assente/vuoto/illeggibile → stato
  vuoto/esplicito, mai crash); errori reali tracciati (`mcp.<tool>.error`, come `_guard`).
- **Osservabilità** per-tool (`log_event`), coerente coi 7 tool (query **hashata** per la ricerca, come
  già fa `EpisodicSearch` — nessun testo di query in chiaro nei log).
- **Doc utente** (`docs/…`): i nuovi tool MCP nella superficie memoria.

### Fuori ambito
- **Ricerca semantica** della memoria via MCP (doppio gate `SERTOR_MEMORY_SEMANTIC`, path embedding):
  **rinviata** — il full-text copre il caso «ne avevamo parlato?»; si valuta come **follow-up** (nuova
  FEAT dell'epica) solo se emerge il bisogno. *(Decisione utente 2026-07-20.)*
- **Scrittura** via MCP (`archive`, `index-semantic`): la memoria si **legge** via MCP; la cattura resta
  un hook/CLI (fuori dalla parità di *lettura*).
- Nuovi campi nell'archivio o cambi di schema SQLite.
- Cambi ai 7 tool esistenti o al formato dei loro risultati.

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous):** *The MCP server shall expose a tool to list the most recent archived memory
  sessions, returning for each an identifier, its capture instant, and its turn count.*
- **REQ-002 (Ubiquitous):** *The MCP server shall expose a tool to retrieve a single archived session by
  its key, returning its turns in order with role, timestamp and text.*
- **REQ-003 (Ubiquitous):** *The MCP server shall expose a tool to search the archive by full text,
  returning turn-grained hits with the session key, role, turn index, a snippet and a relevance score.*
- **REQ-004 (Event-driven):** *When a memory read tool is invoked while conversation memory is disabled,
  the system shall return an explicit disabled state (not an empty result and not an opaque error),
  naming the knob to enable it.*
- **REQ-005 (Ubiquitous):** *The memory read tools shall delegate to the existing core read services and
  reimplement no listing/retrieval/search logic (thin surface, Principio I).*
- **REQ-006 (Ubiquitous):** *The memory read tools shall return only content already present in the
  archive (scrubbed at capture); they shall neither persist nor expose any additional content.*
- **REQ-007 (Ubiquitous):** *Each memory read result shall carry the identifier needed for the next step
  (session key to open a session; session + turn for a search hit).*
- **REQ-008 (Unwanted):** *If the archive is absent, empty, or unreadable, then the read tools shall
  degrade to an explicit empty/So-stated result and not crash; a genuine fault shall be recorded as a
  tool error event, consistent with the existing `_guard`.*
- **REQ-009 (Ubiquitous):** *The search tool shall emit its observability event with the query hashed,
  never in clear, consistent with the CLI episodic search.*
- **REQ-010 (Ubiquitous):** *The memory read tools shall contain no host-specific hardcoded assumption
  (Principio X) and travel with the package so they are installable by construction.*

## 6. Requisiti non funzionali
- **Deterministico, offline, privacy-safe:** il full-text non contatta alcun servizio esterno (path di
  query locale, come `EpisodicSearch`); nessun LLM.
- **Consumo via vehicle (Principio XI):** i tool sono **nel server MCP** (un vehicle), che delega al core;
  nessun accesso diretto alla libreria introdotto per i consumatori.
- **Non-regressione:** invariati i 7 tool esistenti, il warm-up/self-test d'avvio, lo schema `memory.sqlite`,
  i gate CLI, i builder di composition.
- **Parità di configurazione:** stessi default della CLI (`Settings.memory_list_limit`,
  `Settings.episodic_limit`, `Settings.episodic_snippet_tokens`) — nessun nuovo default introdotto.
- **Costo d'avvio:** i tool memoria **non** devono appesantire lo startup quando la memoria è spenta
  (build del reader/search **lazy** dentro il tool, come i builder tornano `None` a gate spento).

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo (Principio XI):** superficie MCP thin sopra il core; nessuna logica di lettura duplicata.
- **Vincolo (Principio XII):** memoria spenta → stato **esplicito** (non maschera con lista vuota); guasto
  reale → evento d'errore visibile.
- **Assunzione:** i servizi di lettura esistono e sono stabili (`MemoryArchive.list_recent`/`get`,
  `EpisodicSearch.search`, builder `build_memory_reader`/`build_episodic_search` gated).
- **Dipendenza:** privacy-by-default condivisa (`SERTOR_MEMORY`); il server MCP legge la stessa config
  centralizzata (`Settings.load`, `.sertor/.env`).
- **Riferimento:** i 7 tool esistenti (`server.py`) come stampo di forma (delega + `_fmt` + `_guard` +
  `log_event`); FEAT-002 (`EpisodicSearch`), 036/FEAT-003 (`list`/`show`).

## 8. Rischi
- **R-1 — Esposizione di contenuto sensibile via MCP:** la memoria è trascrizioni intere. Mitigazione:
  gate `SERTOR_MEMORY` (off di default) **identico** alla CLI + contenuto già scrubbato alla cattura;
  nessun de-scrub; la ricerca logga la query **hashata**.
- **R-2 — Payload grande su `show`:** una sessione può avere molti turni lunghi. Mitigazione: valutare in
  design un limite/troncamento del testo per turno (come `_PREVIEW=300` per i search) o la responsabilità
  lasciata al client; **decisione di design** (§10).
- **R-3 — Stato «disabilitato» che si confonde con «vuoto»:** un `[]` a memoria spenta mentirebbe.
  Mitigazione: REQ-004 — stato **esplicito** (envelope con `status`), non lista vuota.
- **R-4 — Divergenza dalla CLI:** se i tool MCP ordinano/limitano diversamente dalla CLI, la «parità»
  mente. Mitigazione: CS-1 + delega agli **stessi** servizi con gli **stessi** default di `Settings`.
- **R-5 — Rumore d'errore a gate spento:** sollevare un errore per memoria-spenta (il default) inonderebbe
  `mcp.*.error`. Mitigazione: memoria-spenta = stato benigno esplicito, **non** un evento d'errore (§10).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-003 (i tre read), REQ-004 (gate esplicito), REQ-005 (thin),
  REQ-006 (solo contenuto archiviato), REQ-008 (degrado non-fatale).
- **Should:** REQ-007 (citabilità), REQ-009 (query hashata), REQ-010 (host-agnostico/installabile).
- **Could:** —
- **Won't (qui):** ricerca semantica via MCP, scrittura via MCP, cambi di schema.

## 10. Domande aperte — da sciogliere in `clarify`/`plan`
- **DA-a — Forma dello stato «disabilitato» e dei risultati:** envelope uniforme `{status, ...}` per tutti
  e tre i tool (coerenza + onestà del disabled), **oppure** liste/dict «nudi» come i search esistenti con
  il disabled come *errore*? *Proposta:* **envelope con `status`** (`ok`/`disabled`) → il disabled è
  first-class e non maschera, senza inondare `mcp.*.error` (R-5). Da confermare in plan.
- **DA-b — Troncamento del testo su `show`/`search`:** riusare `_PREVIEW` (300) per gli snippet/turni o
  restituire il testo pieno dei turni su `show`? *Proposta:* `search` → snippet come già fa `EpisodicSearch`
  (snippet_tokens); `show` → testo pieno del turno (è il «mostra la sessione»), eventualmente con un cap
  alto configurabile. Da fissare in plan.
- **DA-c — Naming dei tool:** `memory_list`/`memory_show`/`memory_search` (prefisso `memory_`, coerente col
  gruppo CLI e distinto da `search_code`/`search_docs`). *Proposta:* sì, prefisso `memory_`. Da confermare.

---

## Commit proposto
`docs(requirements): E4-FEAT-010 — requisiti «parità MCP per la lettura della memoria» (EARS)`
