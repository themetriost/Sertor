# Requisiti — `rag-freshness`: verdetto post-riparazione + auto-heal del lock stantio
<!-- Deriva da: E10-FEAT-034 (fonde E10-FEAT-035) — epica debito-tecnico -->

## 1. Contesto e problema (perché)

L'hook `rag-freshness` (SessionEnd, E10-FEAT-011) tiene fresco il RAG: al termine di ogni sessione
ri-indicizza e registra un verdetto di salute in `.sertor/.rag-health.json`; al SessionStart successivo,
se il verdetto era `degraded`, l'agente è indotto a riparare prima di lavorare. Due difetti nello **stesso
hook** ne minano l'affidabilità.

### Difetto A — il verdetto è persistito PRIMA della riparazione (FEAT-034)

`_worker()` in `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.py` esegue nell'ordine:
1. `sertor-rag doctor --json` → deriva `verdict`/`reason`;
2. **scrive** `.sertor/.rag-health.json` (`os.replace`, riga ~87);
3. **poi** il re-index incondizionato (`sertor-rag index .`).

Il verdetto persistito è **per costruzione una misura pre-riparazione**, e **nulla riscrive lo stato dopo
lo step 3** (`os.replace` compare una sola volta). `rag-freshness-start.py` non misura nulla: ristampa ciò
che trova. Quindi il **caso normale** (indice stantio a fine sessione → re-index lo ripara) persiste
comunque `degraded`, e all'avvio dopo l'agente riceve un allarme per un problema **che l'hook stesso ha già
riparato**.

**Costo: la svalutazione dell'allarme.** Un avviso che «grida al lupo» nel caso *normale* insegna a
scartarlo; il giorno del degrado **reale** l'allarme arriva con la stessa faccia e passa liscio — e la
direttiva è forte («Do not proceed on potentially stale context»).

**Piegato qui (stesso hook, stesso fix):** il `reason` tiene solo il **primo** warn
(`if not reason: reason = …`). Con `index: warn` **e** `mcp: warn` il messaggio ne dichiara **uno solo** →
chi legge non sa quante aree sono degradate.

Il fix è a valle di **E10-FEAT-038** (`doctor` ancorato alla radice, già consegnato): «rimisurare con
`doctor`» ha senso solo se `doctor` è affidabile indipendentemente dal CWD.

### Difetto B — un worker interrotto lascia un lock stantio che blocca ogni re-index (FEAT-035)

Il worker gira **detached** (`_spawn_detached`: `DETACHED_PROCESS` su Windows / `start_new_session` su
POSIX). Se l'albero di processi muore mentre il re-index è in corso, il single-writer lock
`.sertor/.index/.index.lock` resta con dentro un **PID morto**, e **nulla lo ripulisce**. Ogni
`sertor-rag index` successivo fallisce con `IndexLockedError` («index is locked: another process is
indexing … remove the stale lock file if no process is running») finché non si interviene **a mano**.

**Osservato dal vivo (2026-07-17):** lock del PID 33516 (inesistente) lasciato dall'hook, che bloccava il
re-index post-merge; rimosso manualmente dopo aver verificato l'assenza del processo. Il messaggio è onesto
ma scarica su un umano un lavoro che la macchina può fare: **il lockfile registra già il PID** — basta
verificare se è vivo, come già facciamo per l'auto-heal di Chroma/code-graph.

`_IndexLock.__enter__` (`src/sertor_core/services/indexing.py:345`) fa `os.open(..., O_CREAT | O_EXCL)` e
scrive `str(os.getpid())`; su `FileExistsError` solleva **sempre** `IndexLockedError`, **senza mai
verificare se il PID nel lockfile è ancora vivo**.

**Perché A e B nella stessa feature:** stesso hook, difetti complementari (A: il worker *riporta* salute
prima di riparare; B: il worker che *muore* lascia il danno). Il backlog nota esplicitamente «valutare se
la stessa feature li chiude entrambi». Decisione utente (2026-07-20): **fondere**.

## 2. Obiettivi e criteri di successo

**Obiettivo A:** lo stato persistito riflette la salute del RAG **dopo** la riparazione, non prima →
l'allarme è vero quando compare, quindi merita di essere creduto.
**Obiettivo B:** un worker che muore non lascia il RAG bloccato → il lock è **auto-guarente** (PID morto ⇒
lock stantio ⇒ acquisibile), senza intervento manuale, come già per Chroma/code-graph.

Criteri di successo (misurabili, tech-agnostici):
- **CS-1 (verdetto post-riparazione):** nel caso normale (indice stantio a fine sessione, riparabile dal
  re-index), lo stato persistito a fine worker è `healthy` → **0** allarmi al SessionStart successivo per un
  problema già riparato.
- **CS-2 (degrado reale preservato):** se un problema **sopravvive** alla riparazione (re-index fallito,
  o un'area di `doctor` ancora `warn`/`fail` dopo il re-index), lo stato persistito è `degraded` → l'allarme
  compare quando deve.
- **CS-3 (`reason` completo):** con ≥2 aree degradate, `reason` le **elenca tutte** (nessuna informazione
  persa) → chi legge sa quante e quali aree sono degradate.
- **CS-4 (auto-heal del lock su PID morto):** dato un `.index.lock` che contiene il PID di un processo
  **non più vivo**, un `index()` successivo **acquisisce** il lock (ripulendolo) e procede → **0** blocchi
  manuali richiesti.
- **CS-5 (lock vivo rispettato):** dato un `.index.lock` il cui PID è **vivo**, un `index()` concorrente
  fallisce ancora con `IndexLockedError` → la protezione single-writer contro la corruzione **resta**.
- **CS-6 (auto-heal visibile, non silenzioso):** quando il lock stantio viene reclamato, il sistema emette
  un **segnale osservabile** (evento/warning strutturato che nomina il PID morto) → il guasto **si vede**,
  non è degradato in silenzio (Principio XII).
- **CS-7 (stato mai lacero):** durante la finestra di re-index (potenzialmente lunga), `.rag-health.json`
  non è mai in uno stato **lacero** (scrittura atomica preservata); un lettore vede sempre un JSON valido
  (al più il verdetto della sessione precedente).
- **CS-8 (consegna agli ospiti che aggiornano):** l'ospite che esegue `sertor upgrade rag` riceve il nuovo
  corpo dell'hook (l'ordine post-riparazione), verificabile da un **guard test sull'esito d'upgrade** — non
  solo sulla forma dell'asset (lezione E10-FEAT-032).

## 3. Stakeholder e attori
- **Agente/owner (a valle):** riceve al SessionStart un allarme che, dopo il fix, è **credibile**.
- **Hook `rag-freshness` (SessionEnd):** ripara e poi misura; `rag-freshness-start` (SessionStart): induce.
- **Servizio di indicizzazione del core (`IndexingService._IndexLock`):** deve auto-guarire il lock stantio.
- **Ospite terzo:** riceve entrambi i fix via `sertor install rag` (hook) e col pacchetto `sertor-core`
  (lock); il fix hook raggiunge chi aggiorna via `upgrade`.

## 4. Ambito

### In ambito
- **Riordino di `_worker()`** in `rag-freshness.py`: re-index (ripara) → `doctor` (rimisura) → scrittura
  atomica del verdetto **post-riparazione**; se il re-index fallisce, forza `degraded`.
- **`reason` completo:** accumula **tutte** le aree degradate (non solo la prima).
- **Auto-heal del lock** in `_IndexLock.__enter__`: su `FileExistsError`, se il PID registrato è
  **confermato morto**, rimuove il lockfile stantio e ritenta l'acquisizione; altrimenti fail-loud.
- **Rilevamento liveness del PID cross-OS, solo stdlib**, senza il footgun di `os.kill(pid, 0)` su Windows
  (che *termina* il processo).
- **Segnale osservabile** alla reclamazione del lock stantio (`log_event`).
- **Sync bundle↔dogfood** dell'asset hook + **guard test** (ordine post-riparazione, esito d'upgrade,
  auto-heal, liveness).
- **Doc utente:** aggiornare `docs/install.md` §10.1 (descrive l'ordine vecchio e «at most one session
  behind») + eventuale nota CHANGELOG.

### Fuori ambito
- Spostare la rimisura nel **SessionStart** (violerebbe il confine D↔N: lo start-hook induce, non esegue un
  vehicle — `test_freshness_start_content` asserisce «no `uv run`»). La rimisura resta nel SessionEnd.
- La **spiegabilità** del verdetto `index` di `doctor` e il naming `last_index` (E10-FEAT-037, investigata).
- Cambi allo **schema** `rag.health/1` (i campi restano; cambia solo *quando* e *cosa* si scrive).
- Un lock basato su qualcosa di diverso dal PID (lease/mtime): il PID-liveness è l'approccio specificato.
- La finestra di **PID reuse** (un PID morto riassegnato a un processo estraneo): limite accettato e
  documentato del lock PID-based (il caso peggiore è un raro falso «locked», mai una corruzione).

## 5. Requisiti funzionali (EARS)

**Verdetto post-riparazione (A)**
- **REQ-001 (Event-driven):** *When the RAG-freshness worker runs at session end, the system shall perform
  the re-index (the repair) before measuring health with `doctor`.*
- **REQ-002 (Event-driven):** *When the worker persists the health state, the system shall persist the
  verdict measured after the re-index, not before.*
- **REQ-003 (Unwanted):** *If the re-index fails, then the worker shall persist a `degraded` verdict with a
  reason identifying the re-index failure.*
- **REQ-004 (Ubiquitous):** *The persisted `reason` shall enumerate every degraded area reported by
  `doctor`, not only the first.*
- **REQ-005 (Ubiquitous):** *The health state file shall be written atomically, so a concurrent reader never
  observes a torn file during the re-index window.*

**Auto-heal del lock stantio (B)**
- **REQ-006 (Event-driven):** *When an indexing run finds the index lockfile already present, the system
  shall determine whether the process recorded in the lockfile is still alive.*
- **REQ-007 (Event-driven):** *When the recorded process is confirmed no longer alive, the system shall
  reclaim the stale lock and proceed with the indexing run.*
- **REQ-008 (Unwanted):** *If the recorded process is alive (or the lockfile holder cannot be positively
  confirmed dead), then the system shall fail with `IndexLockedError` as today.*
- **REQ-009 (Event-driven):** *When the system reclaims a stale lock, it shall emit an observable structured
  signal naming the reclaimed (dead) PID (Principio XII: no silent healing).*
- **REQ-010 (Ubiquitous):** *The process-liveness check shall be stdlib-only and cross-OS, and shall never
  terminate, signal, or otherwise perturb the inspected process (in particular on Windows).*

**Consegna (host-facing)**
- **REQ-011 (Ubiquitous):** *The updated hook body shall reach a host that runs `sertor upgrade rag`,
  verifiable by a guard asserting the upgrade outcome (not merely the asset form).*
- **REQ-012 (Ubiquitous):** *The bundled hook asset and its dogfood copy shall remain byte-identical
  (existing sync guard).*

## 6. Requisiti non funzionali
- **Deterministico e non-fatale:** l'hook resta `exit 0` sempre; nessun LLM; solo vehicle (Principio XI).
- **`sertor-core`:** il difetto B **modifica** il core (`_IndexLock`), dietro nessun vehicle nuovo; additivo,
  nessun cambio di firma pubblica di `index()`.
- **Nessuna nuova dipendenza:** liveness via stdlib (`os.kill` su POSIX; `ctypes`/`OpenProcess` su Windows).
- **Non-regressione:** invariati lo schema `rag.health/1`, il contratto `IndexLockedError` (messaggio/uso),
  la protezione single-writer contro run concorrenti **vivi**, il comportamento non-bloccante del SessionEnd
  (worker detached, ritorno immediato).
- **Conservativo sull'ambiguità:** un lockfile vuoto/illeggibile/non-PID **non** viene reclamato (potrebbe
  essere un run vivo tra `create` e `write` del PID) → fail-loud, status quo.

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo (Principio XI):** la rimisura passa per il vehicle (`doctor`/`index`), mai import di `sertor_core`.
- **Vincolo (Principio XII):** fail-loud; auto-heal **visibile**.
- **Dipendenza a monte (soddisfatta):** E10-FEAT-038 (`doctor` ancorato) — la rimisura è sensata solo con un
  `doctor` affidabile a prescindere dal CWD.
- **Assunzione:** il lockfile contiene il PID del writer come stringa decimale (comportamento attuale di
  `_IndexLock`).
- **Riferimento:** auto-heal Chroma/code-graph (PR #89/#90) come precedente della classe «rilevamento
  staleness → re-inizializzazione».

## 8. Rischi
- **R-1 — Race create→write del lockfile:** un lockfile vuoto letto tra `os.open` e `os.write` del PID
  potrebbe sembrare stantio → mitigato da REQ-008 (reclamo **solo** su PID decimale confermato morto; vuoto/
  garbage = non reclamato).
- **R-2 — PID reuse:** un PID morto riassegnato a un processo estraneo farebbe credere il lock ancora tenuto
  → falso `IndexLockedError` (raro), **mai** corruzione; limite accettato del lock PID-based (§4).
- **R-3 — Windows `os.kill(pid, 0)` termina il processo** → mitigato da REQ-010 (via `OpenProcess`, mai
  `os.kill` su Windows).
- **R-4 — Stato assente più a lungo (A):** spostando la scrittura dopo il re-index, alla **primissima**
  esecuzione lo stato è assente per l'intera finestra di re-index → lo start-hook tratta l'assenza come
  no-op (sicuro): nessun falso allarme. Le esecuzioni successive conservano lo stato della sessione prima
  (atomicità, CS-7).
- **R-5 — Consegna incompleta agli ospiti (lezione FEAT-031/032):** il fix hook conta solo se raggiunge chi
  aggiorna → REQ-011 (guard sull'esito d'upgrade). Il fix lock viaggia col pacchetto `sertor-core`.

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001..REQ-010 (i due cuori: verdetto post-riparazione + auto-heal visibile del lock).
- **Should:** REQ-011, REQ-012 (consegna verificata + byte-parity — host-facing DoD).
- **Could:** —
- **Won't (qui):** rimisura nel SessionStart, spiegabilità `index`, lease/mtime-lock, gestione PID-reuse.

## 10. Domande aperte
Nessuna: la feature è pienamente determinata. Il design (ordine esatto, helper liveness cross-OS,
conservativismo sul lockfile ambiguo) è dettagliato nel `plan`. La forcella «rimisura in SessionEnd vs
SessionStart» è già decisa (SessionEnd, per il confine D↔N — §4 Fuori ambito).

---

## Commit proposto
`docs(requirements): E10-FEAT-034 (+035) — requisiti «rag-freshness post-riparazione + auto-heal lock» (EARS)`
