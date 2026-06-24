# Requisiti — Enforcement deterministico della freschezza RAG (hook)

<!-- Deriva da: FEAT-011 (epica debito-tecnico, E10) -->

## 1. Contesto e problema (perché)

Il **rituale di step** del progetto (`CLAUDE.md`, sezione *Rituale di step / Definition of Done*)
prevede due passi **meccanici** a chiusura di ogni step significativo:

- **punto 5 — re-index del corpus toccato:** ricostruire l'indice RAG così che il dogfooding non
  serva mai contesto stantio;
- **punto 8 — smoke test del RAG di dogfooding:** esercitare il server MCP per verificare che sia
  *vivo e fresco*, non solo che l'indice su disco esista.

Questi due passi **si saltano nei fatti**. La lezione registrata il 2026-06-20 lo spiega: un passo
viene eseguito in modo affidabile solo se è **cheap + delegato + incondizionato** (è il caso del
commit, sempre delegato al `configuration-manager`); i passi del re-index/smoke sono invece
**costosi + condizionati + auto-eseguiti dall'agente**, e la condizionalità è proprio il buco da cui
scivolano. Il risultato è il rischio centrale della mission ([[project_essenza_contesto_reale]]):
l'agente ragiona su **contesto non reale** perché l'indice è stantio e nessuno se ne accorge.

La causa non è la volontà dell'agente ma la **collocazione** dei passi: finché restano «standing
behavior» (discrezione dell'agente) saranno saltabili. Spostare la parte **meccanica** in un
**harness deterministico** (hook del client agente) la rende *enforced* — è l'applicazione del
confine D↔N ([[deterministic-vs-judgment]]): ciò che è meccanico va all'harness, all'agente resta il
giudizio.

La capacità è **host-facing**: come gli altri hook del rituale (cattura memoria, uso-vehicle), deve
poter essere **distribuita agli ospiti** via installer, non vivere solo nel `.claude/` di Sertor —
altrimenti viola il Principio X e la regola «una feature è completa solo se installabile su un
ospite».

Complementa, senza sovrapporsi, la **drift-detection** dell'epica `osservabilita` (FEAT-012): quella
*osserva* il drift, questa lo *previene a monte* tenendo l'indice fresco.

## 2. Obiettivi e criteri di successo

- **OBJ-1:** i passi meccanici di freschezza (re-index + verifica salute) avvengono **senza
  dipendere dalla memoria/discrezione dell'agente**.
- **OBJ-2:** quando l'indice è stantio o la salute RAG è degradata, il fatto è **visibile e non si
  perde** tra una sessione e l'altra (fail-loud che sopravvive alla chiusura).
- **OBJ-3:** la capacità è **distribuita agli ospiti** dall'installer con parità Claude / Copilot CLI
  e lifecycle completo.

Criteri di successo (misurabili, tech-agnostici):

- **CS-1:** in N sessioni che modificano file indicizzati, l'indice risulta aggiornato in **100%** dei
  casi a fine sessione, **senza** alcuna azione manuale dell'agente (oggi: dipende dalla memoria,
  saltato di frequente).
- **CS-2:** dopo una sessione che ha lasciato lo stato di salute degradato, **la sessione successiva
  rende il fatto evidente e induce l'azione correttiva** prima che l'agente cominci a lavorare; lo
  stato degradato non è mai silenziosamente ignorato.
- **CS-3:** l'esecuzione dell'hook **non blocca né fa fallire** la chiusura/avvio della sessione in
  nessuno scenario (exit 0 sempre); un suo errore interno è segnalato ma non fatale.
- **CS-4:** un ospite che installa la capacità `rag` riceve l'hook nel **formato nativo** del proprio
  assistente e può disinstallarlo/aggiornarlo **senza** toccare gli altri hook; un test di guardia lo
  verifica (parità + isolamento).
- **CS-5:** quando nulla è cambiato dall'ultimo re-index, l'esecuzione a fine sessione **non produce
  alcun ri-embedding** (costo dominato dall'incrementale del core).

## 3. Stakeholder e attori

- **Owner/maintainer (dogfood):** smette di saltare i passi meccanici; il proprio RAG resta fresco.
- **Agente frontier (Claude / Copilot CLI):** riceve, all'avvio, un segnale chiaro se deve agire;
  non deve più «ricordarsi» di re-indicizzare.
- **Ospite terzo:** riceve la stessa garanzia di freschezza via `sertor install rag`.
- **L'hook (harness deterministico):** nuovo attore non-LLM; *segnala e induce*, non ragiona.
- **`sertor-rag` (vehicle CLI):** esecutore deterministico di `index` e `doctor`.

## 4. Ambito

### In ambito
- Un **hook a fine sessione** (`SessionEnd`) che re-indicizza il corpus via vehicle e ne verifica la
  salute, persistendo un esito di salute.
- Un **segnale a inizio sessione** (`SessionStart`) che ripesca l'esito persistito e, se degradato,
  **induce un'azione correttiva** prima del lavoro dell'agente.
- La **persistenza dello stato di salute** RAG su file locale, leggibile tra sessioni.
- La **reclassificazione nel `CLAUDE.md`** degli step 5 e 8 del rituale: da «standing behavior
  (agente)» a «enforced via hook», con la sfumatura del confine D↔N (l'hook induce, l'agente esegue).
- La **distribuzione host-facing** dell'hook via installer (`sertor install rag`), con parità
  Claude / Copilot CLI e lifecycle install/upgrade/uninstall.
- La **coesistenza** non-fatale e indipendente con l'hook `memory-capture` già presente su `SessionEnd`.

### Fuori ambito (promossi a casa durevole, non sepolti)
- **Smoke col filtro metadata `where`** — l'hook si ferma a `sertor-rag doctor` e **non** esegue una
  query reale che eserciti il path del filtro metadata di `search_code`/`search_docs` (il guasto
  storico del 2026-06-19). Questo check resta affidato all'agente (rituale punto 8). → **promosso**:
  estensione futura di `doctor` con un *check-query* deterministico = nuova voce nel backlog
  dell'epica `usabilità` (E12, owner di `doctor`) — vedi §10/QA-1.
- **Verifica diretta del server MCP vivo dall'hook** (client MCP standalone) — un hook a `SessionEnd`
  non può interrogare in modo affidabile il server in chiusura; la verifica «server fresco» è coperta
  indirettamente via il segnale di reconnect al `SessionStart`. La rilevazione *forte* cross-processo
  dello staleness del server resta debito di **`osservabilita`/server MCP** (già tracciato, cfr.
  finding 2026-06-23).
- **Rilevazione del drift** (segnale «è cambiato qualcosa che andrebbe re-indicizzato») → epica
  `osservabilita` FEAT-012. Qui si *previene*, non si *osserva*.
- Qualunque modifica al **motore di re-index** o a `doctor` stessi: questa feature li **consuma** come
  vehicle, non li estende.

## 5. Requisiti funzionali (EARS)

> Soggetto: l'**hook di freschezza RAG** (componente harness), salvo dove indicato. ID `REQ-NNN`.

### Re-index a fine sessione (punto 5 del rituale → enforced)
- **REQ-001 (Event-driven):** *When a session ends, the freshness hook shall re-index the project
  corpus by invoking the `sertor-rag index .` vehicle command.*
- **REQ-002 (Ubiquitous):** *The freshness hook shall invoke the re-index unconditionally and shall
  not implement any change-detection logic of its own, delegating skip-when-unchanged to the core
  incremental indexer (manifest + embedding cache).*
- **REQ-003 (Unwanted):** *If nothing indexed has changed since the last re-index, then the operation
  shall complete without producing any new embeddings (no added cost beyond process start and
  filesystem walk).*
- **REQ-004 (Ubiquitous):** *The freshness hook shall access Sertor capabilities only through the
  vehicle CLI (`sertor-rag`), never by importing or invoking the `sertor_core` library directly
  (Principio XI).*

### Verifica di salute a fine sessione (punto 8 del rituale → enforced, scope = doctor)
- **REQ-005 (Event-driven):** *When the re-index completes at session end, the freshness hook shall
  assess RAG health by invoking `sertor-rag doctor` over its four areas (config/env, provider, index,
  MCP).*
- **REQ-006 (Ubiquitous):** *The freshness hook shall determine a health verdict (healthy /
  degraded) from the `doctor` outcome (its per-area pass/warn/fail and exit code).*
- **REQ-007 (Ubiquitous):** *The in-hook health verification shall be limited to `doctor` and shall
  NOT execute a metadata-filtered (`where`) query against `search_code`/`search_docs`* (buco
  dichiarato, vedi §4 Fuori ambito).

### Persistenza dell'esito (fail-loud, tempo 1)
- **REQ-008 (Event-driven):** *When the session-end health verdict is degraded (stale index or a
  failing/warning `doctor` area), the freshness hook shall persist a RAG health state to a local file
  that survives the session boundary.*
- **REQ-009 (Event-driven):** *When the verdict is degraded, the freshness hook shall also emit a
  prominent message at session end.*
- **REQ-010 (Event-driven):** *When the session-end health verdict is healthy, the freshness hook
  shall record a healthy state (clearing any prior degraded marker), so that a recovered corpus does
  not keep triggering corrective action.*
- **REQ-011 (Ubiquitous):** *The persisted health state shall record at least: the verdict, a
  timestamp, and the reason/area that failed, in a form readable by the session-start signal.*

### Segnale a inizio sessione e azione correttiva indotta (fail-loud, tempo 2)
- **REQ-012 (Event-driven):** *When a session starts, the freshness signal shall read the persisted
  RAG health state.*
- **REQ-013 (State-driven):** *While the persisted state is degraded, the session-start signal shall
  make the degraded state evident to the agent and induce a deterministic corrective action
  (re-index and/or MCP-server reconnect) before the agent proceeds with project work.*
- **REQ-014 (Ubiquitous):** *The session-start signal shall only signal and induce; it shall not
  itself decide or perform judgment — the corrective vehicle command is executed by the agent (D↔N
  boundary).*
- **REQ-015 (Event-driven):** *When the induced corrective action has restored a healthy verdict, the
  degraded marker shall be cleared so the inducement does not repeat.*

### Coesistenza, non-fatalità, isolamento
- **REQ-016 (Ubiquitous):** *The freshness capability shall be a dedicated hook (separate script and
  its own `SessionEnd` registration entry), distinct from the existing `memory-capture` hook; the two
  shall not be merged into a single script.*
- **REQ-017 (Unwanted):** *If the freshness hook errors for any reason, then it shall not block or
  fail the session lifecycle: it shall always exit 0 and report the error non-fatally (pattern of the
  existing `wiki-pending-check` / `memory-capture` hooks).*
- **REQ-018 (Unwanted):** *If the freshness hook and the `memory-capture` hook both run on
  `SessionEnd`, then a failure of one shall not prevent the other from running.*

### Reclassificazione della governance (CLAUDE.md)
- **REQ-019 (Ubiquitous):** *The `CLAUDE.md` step ritual shall reclassify steps 5 (re-index) and 8
  (smoke) from agent "standing behavior" to "enforced via hook", documenting the D↔N nuance (the hook
  signals and induces; the agent executes the deterministic command).*

### Distribuzione host-facing (installer)
- **REQ-020 (Event-driven):** *When `sertor install rag` runs, the installer shall deposit the
  freshness hook (asset + per-assistant `SessionEnd` settings entry) on the host.*
- **REQ-021 (Ubiquitous):** *The installer shall deposit the freshness hook in the native format of
  the target assistant (Claude vs Copilot CLI), never the Claude format on Copilot (parità — lezione
  FEAT-011/049).*
- **REQ-022 (Ubiquitous):** *The freshness hook shall be wired to the `rag` capability, so that its
  install/upgrade/uninstall lifecycle is granular and independent of the memory/wiki hooks.*
- **REQ-023 (Event-driven):** *When `sertor upgrade`/`uninstall` runs for the `rag` capability, the
  freshness hook shall be updated/removed without disturbing other hooks' entries (asset + settings
  entry), and a leftover-empty dedicated hook file shall be cleaned up.*
- **REQ-024 (Ubiquitous):** *The bundled installer asset and the dogfood `.claude/` copy of the
  freshness hook shall be kept in sync, verified by a guard test (as for the other host assets).*

## 6. Requisiti non funzionali
- **NFR-1 (costo):** a fine sessione, con nulla cambiato, **zero embedding** e overhead dominato
  dall'avvio processo + walk filesystem (cfr. REQ-003); l'incrementale del core è l'unico costo reale.
- **NFR-2 (non-bloccante):** l'esecuzione dell'hook non aggiunge attesa percepibile bloccante alla
  chiusura/avvio; lavoro pesante eventuale resta best-effort e interrompibile, mai fatale.
- **NFR-3 (privacy/locale):** l'hook opera solo su file e vehicle locali; nessun segreto nello stato
  persistito (riusa lo scrub già garantito dai vehicle); il file di stato è gitignored come gli altri
  artefatti runtime sotto `.sertor/`.
- **NFR-4 (host-agnostico):** lo script dell'hook non contiene assunzioni hardcoded su Sertor;
  funziona su un ospite qualsiasi che abbia installato la capacità `rag` (Principio X).
- **NFR-5 (determinismo):** l'hook non invoca alcun LLM; il giudizio resta all'agente (D↔N).
- **NFR-6 (idempotenza):** ri-eseguire il segnale di avvio a stato sano è un no-op; lo stato non
  oscilla né si auto-rigenera (cfr. REQ-010/REQ-015).

## 7. Vincoli, assunzioni e dipendenze
- **Dipende da** `sertor-rag index` (incrementale, FEAT-009 + cache FEAT-019) e `sertor-rag doctor`
  (E12-FEAT-001) — entrambi **già su `master`**; questa feature li *consuma*, non li modifica.
- **Dipende dal** meccanismo installer per gli hook host (asset + `settings_merge` per-assistente +
  lifecycle), già esistente per `memory-capture` / `sertor-rag-usage-check`; e dal seam di parità
  `AssistantProfile` per il formato hook nativo Copilot.
- **Assunzione:** il client agente espone gli eventi `SessionEnd` e `SessionStart` su entrambi gli
  assistenti (vero per Claude Code; per Copilot CLI il `SessionStart` è `type:"prompt"`, il
  `SessionEnd` esiste — cfr. FEAT-008 cattura Copilot).
- **Assunzione:** lo staleness del server MCP dopo un re-index è reale finché non si riconnette
  (finding 2026-06-23); il reconnect indotto al `SessionStart` (REQ-013) ne è la mitigazione lato
  rituale, non un fix del server (quello resta debito `osservabilita`).
- **Vincolo:** Principio XI (solo vehicle), non-distruttività e idempotenza dell'installer,
  non-regressione delle suite esistenti.

## 8. Rischi
- **R-1 — Loop di re-index a ogni avvio:** se il marker non si pulisce a guarigione (REQ-010/015),
  il `SessionStart` indurrebbe l'azione all'infinito. *Mitigazione:* clear esplicito a verdetto sano.
- **R-2 — Inducement che sconfina nel giudizio:** se il `SessionStart` «agisse» da solo si violerebbe
  il confine D↔N e si renderebbe ostile l'avvio. *Mitigazione:* REQ-014 — l'hook induce, l'agente
  esegue.
- **R-3 — Costo nascosto a fine sessione:** se l'incrementale non fosse efficace il re-index
  incondizionato costerebbe. *Mitigazione:* NFR-1/REQ-003, ancorati al manifest+cache già misurati.
- **R-4 — Falsa sicurezza dal solo `doctor`:** `doctor` non coglie il guasto del filtro metadata →
  un indice «verde» per `doctor` potrebbe comunque servire male su query `where`. *Mitigazione:* buco
  dichiarato (§4) + promozione a estensione `doctor` (QA-1); il rituale punto 8 dell'agente resta come
  rete fino ad allora.
- **R-5 — Drift asset bundlato↔dogfood:** un nuovo hook host è una nuova superficie di drift.
  *Mitigazione:* REQ-024, guard test come per gli altri asset.

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001..004 (re-index enforced via vehicle), REQ-005/006 (doctor health),
  REQ-008/009/011 (persistenza + messaggio), REQ-012/013/014/015 (segnale e inducement al avvio),
  REQ-016/017/018 (hook separato, non-fatale, isolato), REQ-019 (reclassificazione CLAUDE.md).
- **Should:** REQ-007 e REQ-010 (esplicitare il buco + clear a guarigione), REQ-020..024
  (distribuzione host-facing completa con parità e lifecycle) — *host-facing è il completamento della
  feature (regola «installabile su un ospite»): senza, la capacità resta dogfood-only e non è done.*
- **Could:** —
- **Won't (questa feature):** smoke col filtro metadata `where`; client MCP standalone dall'hook;
  rilevazione forte cross-processo dello staleness del server.

## 10. Domande aperte
- **QA-1 [promozione, non blocco]:** l'estensione di `doctor` con un *check-query* deterministico
  (che eserciti il path del filtro metadata `where` e colmi il buco di §4) va aperta come **nuova
  FEAT nell'epica `usabilità` (E12)**, owner di `doctor`. Da inserire nel backlog di E12 al `plan`
  (regola: gli Out-of-Scope reali si promuovono).
- **QA-2 [design, non requisito]:** nome/posizione esatti del file di stato (`​.sertor/.rag-health`
  proposto) e formato — da fissare in `plan` (è un *come*).
- **QA-3 [design]:** se il `SessionStart` di Sertor abbia già un hook a cui agganciare il ripesco
  dello stato (oggi esiste `wiki-session-start.ps1`) o se serva una voce dedicata — da decidere in
  `plan` rispettando REQ-016 (isolamento) e l'esistente.
