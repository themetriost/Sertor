# Epica — Memoria delle conversazioni (terzo livello / episodica)

> Livello: **epica**. Aggiunge a Sertor un **tier di memoria grezza ed episodica**: l'archivio di
> **tutte le conversazioni**, conservato e **interrogabile in casi speciali** («ne avevamo già
> parlato? com'è finita quella cosa?»). È il tassello **mancante** sotto il diario del wiki — la
> sorgente grezza da cui la **distillazione** dovrebbe attingere. Si decompone in
> `requirements/memoria-conversazioni/<feature>/requirements.md` (EARS).
>
> **Epica distinta** da `osservabilita` (decisione utente 2026-06-14): quella è **telemetria**
> (numeri da aggregare/ruotare), questa è **conoscenza** (contenuto da cercare/conservare). Le due
> corrono **in parallelo**, ma **condividono il principio di privacy** (vedi §7). Ispirazione diretta:
> il **pattern di memoria di Hermes** (Nous Research).

## 1. Visione e problema (perché)

Oggi la conoscenza prodotta nelle conversazioni con l'agente viene **distillata** in pagine wiki
(FEAT-003, Gruppo D), ma il modello è **lossy**: la pagina si tiene, **il grezzo si butta**. Manca un
tier: l'**archivio episodico** delle conversazioni intere. Conseguenza: non si può rispondere a
domande di memoria episodica («cosa avevamo deciso su X tre settimane fa, e perché?») se la
distillazione non l'aveva catturato, e la distillazione stessa non ha una fonte grezza a cui tornare.

Il **pattern Hermes** (memoria a 4 strati) descrive esattamente il pezzo che ci manca:

| Strato Hermes | In Sertor (oggi) |
|---|---|
| `MEMORY.md`/`USER.md` (prompt persistenti) | wiki index + pagine distillate + `MEMORY.md` (contesto sempre caricato) |
| **Session archive (SQLite + full-text, episodico)** | **❌ assente → questa epica** |
| Skills directory (sapere procedurale) | `.claude/skills/` |
| Provider esterni (Mem0/Hindsight) | l'idea di export/integrazione (osservabilità: OTel) |

La «memoria di terzo livello» è dunque il **session archive**: il tier grezzo episodico, sotto il
**diario** del wiki ([[diary-vs-graph]]), con un filo verso il **second-brain** cross-progetto
([[second-brain-cross-progetto]]).

> Il *come* (formato dell'archivio, meccanismo di cattura, schema) è materia della **fase di design**.
> Qui solo *cosa* e *perché*.

## 2. Ambito

### In ambito
- **Cattura e archiviazione** delle conversazioni (transcript) in un **archivio locale**, conservato
  (non ruotato via come la telemetria).
- **Ricerca episodica** sull'archivio per i **casi speciali** («ne avevamo già parlato?»), di
  **default full-text locale** (il contenuto non lascia la macchina).
- **Ricerca semantica opzionale** sull'archivio (embedding → riuso del RAG esistente come tier/corpus),
  come **opt-in ulteriore** (vedi privacy, §7).
- **Aggancio alla distillazione del wiki**: l'archivio diventa la **fonte grezza** da cui le operazioni
  `distill`/`record` possono attingere (oggi distillano "al volo", senza backup grezzo).
- **Portabilità**: l'archivio e la ricerca operano su qualunque ospite (Principio X); la **cattura**,
  che è host-specifica, sta dietro un adapter configurabile (vedi Rischi/Domande aperte).

### Fuori ambito
- **Osservabilità/telemetria** (log, costo, metriche): è l'epica gemella `../osservabilita/`.
- **Roll-up cross-progetto** (promozione della memoria alla flotta): è il [[second-brain-cross-progetto]];
  qui l'archivio resta **per-progetto** (ma con un occhio a un formato compatibile, §9).
- **Distillazione automatica unattended** (un processo che distilla da solo senza un trigger): resta
  governata dal rituale/`/wiki` esistente; qui si fornisce la **fonte**, non un nuovo automatismo.
- Definizione del *come* (stack, schema, formato transcript): fase di **design**.

## 3. Criteri di successo
<!-- misurabili e tech-agnostici -->
- **CS-1 (archivio):** con la cattura attiva, dopo **N** sessioni le relative conversazioni sono
  **recuperabili** dall'archivio (verificabile: #conversazioni archiviate = #sessioni catturate).
- **CS-2 (memoria episodica):** data una domanda su qualcosa discusso in una sessione passata, la
  ricerca **full-text locale** restituisce la conversazione pertinente **senza** contattare alcun
  servizio esterno.
- **CS-3 (fonte per la distillazione):** un'operazione di distillazione può **attingere** a una
  conversazione archiviata invece di richiedere un brief riassunto a mano.
- **CS-4 (privacy-by-default):** con la cattura **disattivata** (default) non viene persistito alcun
  contenuto; attiva, il contenuto è soggetto a scrub dei segreti e a retention configurabile; la
  ricerca **semantica** (che embedda) richiede un **opt-in ulteriore** esplicito.
- **CS-5 (host-agnostico):** la ricerca e l'archivio funzionano su **≥2** ospiti diversi senza
  modifiche al corpo; la **cattura** è realizzata da un adapter per l'assistente ospite, sostituibile
  via config (Principio X).

## 4. Stakeholder e attori
- **Owner/maintainer (tu):** consulta la memoria episodica per ricostruire decisioni e contesto.
- **Agente LLM (Claude Code & altri):** attore **primario** — sia *sorgente* delle conversazioni sia
  *consumatore* della memoria episodica (la interroga "nei casi speciali").
- **Il sistema-wiki:** consumatore — la distillazione attinge all'archivio.
- **Host/assistente ospite:** fornisce i transcript (meccanismo di cattura host-specifico).

## 5. Vincoli, assunzioni e dipendenze
- **Privacy-by-default (condivisa con `osservabilita`):** nessun contenuto persistito senza opt-in;
  full-text locale come default; embedding (semantico) come opt-in ulteriore; scrub dei segreti nel
  testo; retention configurabile (vedi §7).
- **Riuso del RAG esistente:** la ricerca semantica opzionale **non** costruisce un nuovo motore —
  riusa ingestione/embeddings/store del core come un **corpus/tier** dedicato (Principio I/III).
- **Local-first & host-agnostico:** archivio e ricerca interamente locali; la cattura, host-specifica,
  sta in un **adapter** dietro config (Principio X) — **non** assunzioni nel corpo.
- **Non-distruttività & conservazione:** a differenza della telemetria, l'archivio si **conserva**
  (è memoria); cancellazione solo esplicita; idempotenza sull'archiviazione della stessa sessione.
- **Segreti:** mai persistiti — la redazione si estende dallo *schema* al **contenuto** (scrub pattern).
- **Dipendenza dal sistema-wiki:** l'aggancio alla distillazione presuppone le operazioni `distill`/
  `record` esistenti (FEAT-003 ✅) — questa epica le **alimenta**, non le ridefinisce.

## 6. Rischi
- **R-1 — Cattura host-specifica (il nodo):** *come* Sertor ottiene i transcript dipende dall'assistente
  ospite (in Claude Code stanno nell'harness; altri assistenti differiscono). È il problema centrale e
  si lega alla **distribuzione multi-assistente** (epica `sertor-cli`). Senza una strategia di cattura
  portabile, la feature vale solo su un assistente.
- **R-2 — Privacy del contenuto grezzo:** trascrizioni intere = massima sensibilità (codice
  proprietario, decisioni, segreti incollati). Mitigazione: privacy-by-default + scrub + retention + il
  default full-text locale (niente cloud).
- **R-3 — Esposizione via embedding:** la ricerca semantica manda il contenuto al provider di
  embeddings (cloud se Azure). Mitigazione: opt-in separato + opzione locale (Ollama) per restare
  on-machine.
- **R-4 — Crescita illimitata:** l'archivio cresce; serve retention/compattazione (ma "conservare" è il
  punto → retention più generosa della telemetria).
- **R-5 — Rumore vs valore:** archiviare *tutto* può seppellire il segnale. Mitigazione: la
  distillazione resta la vista ad alto segnale; l'archivio è il *fallback* episodico ("casi speciali").
- **R-6 — Confine con la distillazione:** non trasformare l'archivio in un secondo wiki; resta **fonte
  grezza**, non conoscenza curata.

## 7. Requisiti trasversali (EARS) — privacy condivisa
<!-- stesso principio dell'epica osservabilita (REQ-E8/E9) -->
- **REQ-M-E1 (Unwanted, privacy-by-default):** *If conversation capture is not explicitly enabled, then
  the system shall persist no transcript content (memory off by default).*
- **REQ-M-E2 (Optional, layered opt-in):** *Where conversation capture is enabled, the system shall
  archive transcripts with secret-pattern scrubbing and a configurable retention, searchable via local
  full-text by default; and where semantic search over the archive is enabled, embedding the content
  shall be a further, separate opt-in (kept on-machine when a local embeddings provider is configured).*
- **REQ-M-E3 (Ubiquitous):** *The archive and its search shall operate on any host without changes to
  their body; the capture mechanism shall be a host/assistant-specific adapter selected by configuration
  (Principio X).*
- **REQ-M-E4 (Event-driven):** *When the same session is archived more than once, the system shall not
  duplicate it (idempotent archival).*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Cattura & archiviazione locale dei transcript** — adapter di cattura host-specifico (Claude Code per primo) → archivio locale conservato, idempotente | Il **tier grezzo** che oggi manca: senza archivio non c'è memoria episodica | **Must** | ✅ **DONE (PR #45)** → [`cattura-archiviazione/requirements.md`](cattura-archiviazione/requirements.md) |
| FEAT-002 | **Ricerca episodica full-text locale** — interroga l'archivio nei "casi speciali" («ne avevamo già parlato?»), senza cloud | Rende l'archivio **utile**: la memoria che risponde | **Must** | ✅ **DONE (PR #47)** → `ricerca-episodica-fulltext/requirements.md` |
| FEAT-003 | **Aggancio alla distillazione del wiki** — `distill`/`record` possono attingere a una conversazione archiviata come fonte grezza | Chiude il loop lossy: la distillazione ha finalmente una **fonte** | **Should** | ✅ **DONE (PR #51)** → [`aggancio-distillazione/requirements.md`](aggancio-distillazione/requirements.md) |
| FEAT-004 | **Ricerca semantica opzionale sull'archivio** — embedding dei transcript come corpus/tier del RAG, opt-in (privacy §7) | Memoria episodica *per significato*, non solo per parola | **Should** | ✅ implementata → [`ricerca-semantica/requirements.md`](ricerca-semantica/requirements.md) · specs/072 · [[feat-004-ricerca-semantica-memoria]] · manopole `SERTOR_MEMORY_SEMANTIC*` ✅ nei template `.env` installer (debito P2 chiuso; guardia anti-drift resa auto-derivante) |
| FEAT-005 | **Cattura selettiva "remember this"** — marcatura esplicita di cosa archiviare, invece di tutto | Controllo dell'utente su cosa entra in memoria (riduce rumore e rischio privacy) | **Could** | da decomporre |
| FEAT-006 | **Governance/retention del contenuto** — politiche di scadenza, scrub configurabile, cancellazione selettiva | Igiene e privacy operativa della memoria | **Could** | da decomporre |
| FEAT-007 | **Ponte verso il second-brain** — formato/superficie compatibili con la promozione cross-progetto | Prepara il roll-up di flotta senza costruirlo qui | **Could** | da decomporre |
| FEAT-008 | **Cattura multi-assistente** — adapter di cattura oltre Claude Code (Copilot CLI per primo) | Rende la memoria portabile davvero, non legata a un assistente; **rende vivo** l'hook Copilot già distribuito (FEAT-009, oggi inerte) | **Should** *(promossa da Could 2026-06-22, tema prioritario utente)* | ✅ **DONE (2026-06-22, feature 073, merge `7dd1182`)** → [`cattura-multi-assistente/requirements.md`](cattura-multi-assistente/requirements.md) — adapter `copilot-cli` (legge `~/.copilot/session-state/<uuid>/events.jsonl`); ricognizione R-1 fatta (transcript = `~/.copilot/session-state/<uuid>/events.jsonl`); riusa la porta `TranscriptCaptureAdapter`, tier a valle invariato |
| FEAT-009 | **Distribuzione della memoria via installer** — `sertor install` cabla sull'ospite: manopole memoria nel template `.env` (`SERTOR_MEMORY`, `SERTOR_MEMORY_LIST_LIMIT`, `SERTOR_EPISODIC_*`), hook `memory-capture.ps1` + voce `SessionEnd` negli asset, cenno nel `claude-md-block`. **Recupera il rinvio A-009 di FEAT-035** (era solo in `specs/035-…`, mai promosso) | **Debito di completamento**: per la regola «feature completa = installabile» (CLAUDE.md) l'MVP memoria non è completo finché un ospite non lo riceve via installer | **Must** | ✅ **DONE (2026-06-22, merge `a36ba89`)** → [`distribuzione-installer/requirements.md`](distribuzione-installer/requirements.md) — cross-ref epica `sertor-cli` (owner di `sertor install`); si combina con FEAT-008 |
| FEAT-010 | **Parità MCP per `memory show`/`list`** — esporre via server MCP i comandi di lettura dell'archivio (oggi solo CLI) | Memoria interrogabile nativamente dall'agente, non solo da terminale | **Could** | da decomporre — **leak audit (2026-06-16)**, era solo in `specs/036` |
| FEAT-011 | **BUG: cattura memoria silenziosamente vuota su path con spazi (`encode_project_path`) + fallimento silenzioso** — `encode_project_path` (`adapters/capture/claude_code.py:34`) sostituisce `:`/`\`/`/` con `-` ma **non lo spazio**, mentre Claude Code collassa anche gli spazi quando nomina la cartella in `~/.claude/projects` → su un progetto il cui path contiene uno spazio la cartella calcolata **non combacia** con quella reale → source assente → **archivia 0 sessioni in silenzio** (`memory_capture_source_absent` = solo WARNING; `archived=0 errors=0`, exit 0). | (1) allineare l'encoding al comportamento reale di Claude Code (spazi **e** punti; es. regex `[^A-Za-z0-9]→-`, con test regressione su drive-letter/UNC/trattini/punti); (2) **fail-loud** (più importante): con `SERTOR_MEMORY=true` e source assente → **finding visibile / exit ≠ 0**, non `errors=0` silenzioso — viola il *Fail Loud* (Principio XII) che Sertor **prescrive agli ospiti**. Verificare anche l'adapter `copilot-cli` (stesso pattern `_absent`). | **Must** | 🔄 **IMPLEMENTATA (branch `108`, 2026-07-15)** — (1) `encode_project_path` → `re.sub(r"[^A-Za-z0-9]", "-", …)`, **validato dal vivo** (VM-WorkingFolder: 22 sessioni recuperate); (2) fail-loud host-agnostico: `source_available()` sul port + `ArchiveRunReport.source_absent` + WARNING nel formatter (human+JSON), exit 0 preservato. Test: 15 campioni reali + fail-loud; `copilot-cli` non affetto. `sertor-core` unico impatto. Requirements in `fix-cattura-encoding-e-fail-loud/`. **BUG confermato sul codice (verifica 2026-07-14), fonte: handoff Nunzio `memory-archive-silenzioso-path-con-spazi.md` (2026-07-09).** Impatto **misurato**: 3/13 progetti con spazi affetti (VM-WorkingFolder perde **22 sessioni**); Windows: path con spazi = norma. **Distinto dal 🐛 auto-capture E4** (Sertor no-spazi NON affetto: archive manuale = 58 sessioni, come predetto). Due fix indipendenti; il 2° avrebbe fatto emergere il bug il giorno stesso |

> **Nota sull'MVP (Must):** la prima release utile è **FEAT-001 → FEAT-002**: catturare le conversazioni
> (su Claude Code) e poterle **ritrovare** (full-text locale). L'aggancio alla distillazione e la
> ricerca semantica (Should) seguono; il resto (Could) dopo.

## 9. Domande aperte
<!-- ogni punto irrisolto resta [DA CHIARIRE: domanda] -->
- **DA-M-a — Meccanismo di cattura (il nodo):** [DA CHIARIRE: per Claude Code i transcript stanno
  nell'harness — Sertor li legge da lì? li riceve via hook? È host-specifico e va dietro un adapter.
  Vincola FEAT-001 ed è il punto di design più pesante.]
- **DA-M-b — Granularità dell'unità di memoria:** [DA CHIARIRE: l'unità archiviata è la *sessione*
  intera, il *turno*, o un *thread*? Impatta ricerca e distillazione.]
- **DA-M-c — Cattura tutto vs selettiva:** [DA CHIARIRE: di default si archivia ogni sessione (con
  opt-in di privacy) o solo ciò che l'utente marca (FEAT-005)? Default proposto: tutto-con-opt-in, ma
  rivalutabile per ridurre rumore/rischio.]
- **DA-M-d — Relazione con `prototype/raw/` e i corpora:** [DA CHIARIRE in design: l'archivio è un nuovo
  `doc_type`/corpus del RAG (riuso ingestione) o uno store dedicato affiancato? Ricade su FEAT-004.]
- **DA-M-e — Confine col second-brain:** confermato **fuori scope** il roll-up cross-progetto; aperto
  solo se in futuro si vorrà un formato compatibile (FEAT-007).
- **DA-M-f — Privacy:** ✅ **principio già fissato (2026-06-14)** condiviso con `osservabilita`
  (REQ-M-E1/E2): privacy-by-default, full-text locale di default, semantico opt-in, scrub + retention.

## 10. Riferimenti (prior art, non requisiti)
- **Pattern Hermes** (Nous Research): memoria a 4 strati, *session archive* SQLite+FTS per la memoria
  episodica; provider esterni (Mem0/Hindsight) per il tier pluggable.
- **Memori** (MemoriLabs), **Mem0**, **Zep/MemGPT**: infrastrutture di memoria agent-native (cattura,
  retrieval semantico, persistenza cross-sessione) — utili come riferimento di design.
- **Interno:** [[diary-vs-graph]] (l'archivio grezzo è il tier sotto il diario), FEAT-003 Gruppo D
  (distillazione di conversazione — oggi senza fonte grezza), [[second-brain-cross-progetto]] (il
  roll-up di flotta), epica `osservabilita` (privacy condivisa), distribuzione multi-assistente
  (`sertor-cli`, la cattura host-specifica).
