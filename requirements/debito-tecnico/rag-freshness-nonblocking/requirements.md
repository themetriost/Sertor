# Requisiti — rag-freshness: re-index a SessionEnd non-bloccante

<!-- Deriva da: FEAT-016 (epica debito-tecnico / E10) -->

## 1. Contesto e problema (perché)

L'hook `rag-freshness.ps1` (consegnato con **E10-FEAT-011**, enforcement deterministico della freschezza
RAG) esegue a **ogni chiusura di sessione** (`SessionEnd`) due passi **sincroni**:

1. `uv run sertor-rag index .` — re-index **incondizionato** del corpus dogfood
   (`assets/rag/hooks/rag-freshness.ps1:65`);
2. `uv run sertor-rag doctor --json` — verdetto di salute per area
   (`assets/rag/hooks/rag-freshness.ps1:71`),

e poi deriva un verdetto `healthy`/`degraded` che persiste in `.sertor/.rag-health.json`.

Il wiring host (`assets/rag/settings.rag-freshness.json:9`) impone all'intero hook un **timeout di 15
secondi**. Su repository **non banali** (corpus grande, molti file modificati) il re-index **non termina
in 15s** → l'harness host **uccide il processo** → `doctor` **non gira mai** → `.sertor/.rag-health.json`
resta **stantio o assente**. Il meccanismo di freschezza **si auto-sabota** (audit utente
[[sertor-strumenti-audit]] ISSUE-01, 2026-06-26): proprio lo strumento che dovrebbe garantire un contesto
RAG sempre fresco produce uno **stato di salute non aggiornato** e introduce uno **stallo a ogni chiusura
di sessione** percepito dall'utente.

Questa feature rende il re-index di fine sessione **non-bloccante** e la freschezza **affidabile**, senza
perdere il valore di FEAT-011: stesso confine **D↔N** (l'hook è **meccanico**, non invoca alcun LLM),
stesso pattern **host-facing** (asset distribuito dall'installer, parità Claude / Copilot CLI),
**non-fatale** (exit 0 sempre). È un **difetto di FEAT-011**: la decisione «re-index incondizionato e
sincrono» (FR-002 di FEAT-011, skip delegato all'incrementale del core) non aveva considerato il caso in
cui l'incrementale **non basta** a rientrare nel timeout dell'hook.

> Il *come* (background/async vs change-gate vs timeout realistico, meccanismo di processo staccato in
> pwsh, separazione fisica `doctor`↔`index`) è materia della fase di **design**. Qui solo *cosa* e
> *perché*.

## 2. Obiettivi e criteri di successo

- **CS-1 (chiusura non-bloccante):** la chiusura di sessione **non subisce stallo** anche su repository
  grandi; il ritorno di controllo all'host avviene in tempi brevi (NFR di latenza, target ~1–2s), **a
  prescindere** dalla durata del re-index.
- **CS-2 (freschezza affidabile):** `.sertor/.rag-health.json` riflette **sempre** l'ultimo stato di
  salute noto — non resta **mai** stantio/assente perché un re-index lungo è stato ucciso dal timeout.
- **CS-3 (nessun processo ucciso):** in **0** casi il log dell'host mostra il processo dell'hook
  **ucciso** dal timeout su un repository grande.
- **CS-4 (valore di FEAT-011 preservato):** il verdetto `healthy`/`degraded`, il messaggio **fail-loud**
  su `degraded` a fine sessione e l'**induzione** della correzione al `SessionStart`
  (`rag-freshness-start.ps1`) restano funzionanti e invariati nel comportamento osservabile.
- **CS-5 (D↔N & invarianti):** la soluzione **non invoca alcun LLM** e **non importa `sertor_core`**
  (consuma i vehicle `sertor-rag index`/`doctor`, Principio XI); resta **idempotente**, **non-distruttiva**
  e **non-fatale** (exit 0 sempre).
- **CS-6 (host-agnostico & installabile):** la correzione è distribuita su **Claude e Copilot CLI** via
  `sertor install`, con **parità** e ciclo di vita (install/upgrade/uninstall), additiva e non
  distruttiva; l'eventuale modifica del **timeout** nel wiring host è coerente fra i target.

## 3. Stakeholder e attori

- **Owner/utente dell'ospite:** subisce oggi lo stallo a fine sessione; beneficia della chiusura rapida.
- **Agente frontier dell'ospite (Claude/Copilot):** consuma `.sertor/.rag-health.json` al SessionStart
  per indurre l'eventuale correzione.
- **L'hook `rag-freshness.ps1` (SessionEnd):** l'asset da rendere non-bloccante.
- **L'hook `rag-freshness-start.ps1` (SessionStart):** consumatore dello stato persistito (invariato).
- **Vehicle `sertor-rag index` (incrementale, FEAT-009 manifest + FEAT-019 cache embeddings):** il
  re-index che, su corpus invariato, è già a costo ~nullo.
- **Vehicle `sertor-rag doctor`:** la fonte del verdetto di salute (E12-FEAT-001).
- **L'installer `sertor` (FEAT-008 lifecycle):** deposita e mantiene l'asset e il suo wiring.

## 4. Ambito

### In ambito
- Rendere il re-index di `SessionEnd` **non-bloccante** rispetto alla chiusura di sessione su repository
  grandi.
- Garantire che `.sertor/.rag-health.json` rifletta **sempre** l'ultimo verdetto di salute (separare
  **logicamente** il calcolo del verdetto `doctor` dal re-index potenzialmente lungo).
- Eventuale **rivisitazione del timeout** del wiring host (`settings.rag-freshness.json`) coerente con la
  soluzione scelta.
- Preservare il messaggio **fail-loud** su `degraded` e l'induzione al `SessionStart`.
- **Distribuzione** della correzione via installer (parità Claude / Copilot CLI + lifecycle).
- Portabilità del meccanismo non-bloccante in `pwsh` su **Windows** e **POSIX**.

### Fuori ambito
- **Invocazione CLI `uv run` bare** negli hook (cwd-fragile, contro `CLAUDE.md`): è **E10-FEAT-017**
  (*Invocazione CLI standardizzata negli hook*), debito separato; questa feature **non** lo include e
  **non** lo presuppone risolto.
- La **rilevazione del drift** dell'indice cross-processo e la staleness forte del server MCP:
  `osservabilita` FEAT-012 (cross-ref, già fuori ambito in FEAT-011).
- Il **buco del filtro metadata `where`** dello smoke (`search_code`/`search_docs`): promosso a
  **E12-FEAT-011** in FEAT-011; non riaperto qui.
- La **robustezza dell'invocazione manuale** dell'hook (stdin non-bloccante, `[Console]::In.ReadToEnd()`):
  è **E10-FEAT-014** (debito separato, già tracciato).
- Modifiche a **`sertor-core`**: la feature è host-facing (asset installer), additiva; il core resta
  **invariato** (i vehicle `index`/`doctor` esistono già).

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Event-driven):** *When a session ends on a host with the RAG capability installed, the
  system shall trigger the freshness routine without blocking the session close.*
- **REQ-002 (Ubiquitous):** *The session-close path shall return control to the host promptly,
  independently of how long the corpus re-index takes.*
- **REQ-003 (Unwanted):** *If the corpus re-index does not complete quickly, then the system shall not let
  it delay or block the session close (the re-index must not run synchronously to completion within the
  host timeout on large repositories).*
- **REQ-004 (Ubiquitous):** *The system shall keep `.sertor/.rag-health.json` reflecting the latest known
  health verdict, and shall never leave it stale or absent because a long re-index was killed by the host
  timeout.*
- **REQ-005 (Ubiquitous):** *The system shall separate, logically, the computation of the health verdict
  (`sertor-rag doctor`) from the corpus re-index (`sertor-rag index`), so that the verdict is produced and
  persisted even when the re-index is long-running or deferred.*
- **REQ-006 (Unwanted):** *If the re-index is still running (or has been deferred) when the verdict is
  written, then the persisted state shall remain valid and shall not be corrupted (no partial/torn write).*
- **REQ-007 (Event-driven):** *When the health verdict is `degraded`, the system shall present a prominent
  fail-loud message at session close and persist the reason, preserving FEAT-011 behaviour.*
- **REQ-008 (Event-driven):** *When the persisted verdict is `degraded`, the SessionStart routine
  (`rag-freshness-start.ps1`) shall continue to induce the corrective action before agent work, preserving
  FEAT-011 behaviour.*
- **REQ-009 (Ubiquitous):** *The re-index shall continue to consume the `sertor-rag index` vehicle
  (incremental: FEAT-009 manifest + FEAT-019 embedding cache) and shall never import `sertor_core`
  (Principio XI).*
- **REQ-010 (Ubiquitous):** *The freshness routine shall remain idempotent: repeated session closes on an
  unchanged corpus shall not produce a different or corrupt state.*
- **REQ-011 (Ubiquitous):** *The freshness routine shall remain non-destructive: it shall only write its
  own runtime state under `.sertor/` and shall not alter project files.*
- **REQ-012 (Unwanted):** *If any step (re-index, verdict, or state write) fails or is unavailable
  (missing `uv`/`sertor-rag`, catastrophic error), then the routine shall remain non-fatal and exit 0,
  never breaking the session close.*
- **REQ-013 (Ubiquitous):** *The routine shall invoke no LLM; all work shall be done through the
  deterministic `sertor-rag` vehicles (Principio D↔N).*
- **REQ-014 (Event-driven):** *When the corpus is unchanged since the last run, the system should perform
  the freshness routine at near-zero cost (the incremental indexer already skips unchanged files; an
  optional fast change-gate may avoid spawning the re-index at all).*
- **REQ-015 (Optional/State-driven):** *Where the host timeout is the upper bound of the hook, the system
  shall set a timeout consistent with a non-blocking design (i.e. the timeout shall not cause a long
  re-index to be killed mid-way and so leave the verdict uncomputed).*
- **REQ-016 (Optional):** *Where the host or OS lacks a usable mechanism to run the re-index without
  blocking (e.g. no background-process facility in the available `pwsh`), the system shall degrade
  honestly to a safe behaviour (still produce a verdict, never block) rather than silently regress.*
- **REQ-017 (Optional):** *Where the user installs the RAG capability, the installer shall deposit the
  corrected freshness asset and its wiring for the chosen assistant (Claude / Copilot CLI),
  non-destructively and idempotently, with full lifecycle (install / upgrade / uninstall) and parity.*
- **REQ-018 (Ubiquitous):** *The routine shall transmit no project content or secrets off-machine; it
  shall reuse the already-scrubbed `doctor --json` output and shall not compose new text from
  `.sertor/.env`.*

## 6. Requisiti non funzionali

- **Performance / non-blocking:** la chiusura di sessione **non eccede ~1–2s** percepiti, anche su
  repository grandi; il re-index non prolunga la chiusura oltre questo budget (NFR cardine, gemello del
  vincolo di latenza di FEAT-011/version-check).
- **Affidabilità:** **non-fatale** — la routine esce sempre **0** e non blocca mai la sessione (gemello
  `memory-capture.ps1` / `rag-freshness.ps1` originale); lo stato non viene mai scritto in forma
  corrotta/parziale.
- **Freschezza:** lo stato di salute persistito è **sempre aggiornato** rispetto all'ultima esecuzione;
  nessun «processo killed» nel log dell'host su repository grande (criterio dell'audit ISSUE-01).
- **Portabilità:** host-agnostico, Windows + POSIX (`pwsh`); il meccanismo non-bloccante deve essere
  realizzabile/degradabile su entrambi; **parità** Claude / Copilot CLI.
- **Privacy:** nessun contenuto/segreto fuori macchina; solo riuso dell'output `doctor` già scrubbato.
- **Additività:** a feature non corretta, comportamento e costo restano confrontabili; nessun LLM nel
  percorso (Principio D↔N / XI); `sertor-core` invariato.
- **Osservabilità (opz.):** un eventuale evento è **metrics-only** (nessun path/segreto), coerente con
  gli altri hook.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo core invariato:** `sertor-core` **non** va toccato; la routine consuma i vehicle
  `sertor-rag index .` (incrementale) e `sertor-rag doctor` (Principio XI).
- **Vincolo valore FEAT-011:** verdetto `healthy`/`degraded`, schema `rag.health/1` di
  `.sertor/.rag-health.json`, messaggio fail-loud e induzione al SessionStart restano funzionanti.
- **Dipendenze (consumo, non reimplementazione):**
  - **E10-FEAT-011** — pattern hook `SessionEnd`/`SessionStart` + stato in `.sertor/` (ancoraggio:
    `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1`,
    `rag-freshness-start.ps1`, `settings.rag-freshness.json`; wiring in `install_rag.py`).
  - **FEAT-009 (refresh incrementale)** + **FEAT-019 (cache embeddings)** — rendono il re-index a corpus
    invariato già a costo ~nullo; la soluzione deve **tenerne conto** (un change-gate o l'async non
    devono duplicare il lavoro che l'incrementale già evita).
  - **FEAT-008 lifecycle** — install/upgrade/uninstall + `RUNTIME_IGNORES` per lo stato `.sertor/`.
  - **Vehicle `sertor-rag doctor`** (E12-FEAT-001) — la fonte del verdetto.
- **Assunzione (cwd/venv):** la risoluzione corretta di progetto/venv dell'invocazione `uv run` è
  **E10-FEAT-017** (separata); questa feature **non** la corregge e i criteri qui non la presuppongono
  risolta (ma una soluzione async/background **non deve peggiorarla**).
- **Assunzione:** `pwsh` presente per lo script (come per gli altri hook); assente → portabilità trattata
  altrove (FEAT-018), qui si assume disponibile.
- **Sync asset bundlati:** ogni modifica all'asset bundlato richiede `sync` + la guardia
  `tests/unit/test_assets_sync.py` (lezione standing); la copia dogfood `.claude/hooks/` va riallineata.

## 8. Rischi

- **R-1 — Background/async fire-and-forget perde il verdetto:** se il re-index parte in background e il
  `doctor` gira **prima** che finisca, il verdetto potrebbe riflettere lo stato **pre**-index. *Mitigante:*
  la separazione logica REQ-005 + accettare che il verdetto sia «al più di una sessione indietro» (lo
  stato non è mai stale/assente, è solo riferito all'ultimo re-index completato) — **DA-2**.
- **R-2 — Processo background orfano:** un re-index staccato che sopravvive alla chiusura dell'host
  consuma risorse a sorpresa (CPU/embeddings cloud = centesimi). *Mitigante:* singolo writer / guardia
  anti-concorrenza (riusa `IndexLockedError` del core, FEAT-009) — **DA-3**.
- **R-3 — Change-gate diverge dall'incrementale:** un gate mtime/manifest **fuori** dal core
  duplicherebbe la logica già in `IndexManifest` e potrebbe **divergere** (falsi «invariato»). *Mitigante:*
  preferire di delegare al gate **già interno** all'incrementale, o limitarsi a un check coarse — **DA-1**.
- **R-4 — Portabilità del meccanismo non-bloccante:** `Start-Job`/`Start-Process -NoNewWindow` /
  job in background hanno semantica diversa su Windows vs POSIX `pwsh`; un async non portabile romperebbe
  la parità. *Mitigante:* meccanismo verificato su entrambi o degrado onesto (REQ-016) — **DA-4**.
- **R-5 — Timeout «realistico» è una toppa, non un fix:** alzare semplicemente il timeout (es. 60s)
  **non** elimina lo stallo (lo allunga) e fallisce comunque su repo molto grandi. *Accettato come
  fallback solo se combinato con la separazione del verdetto* — **DA-1**.
- **R-6 — Convivenza con FEAT-017 (cwd/venv):** se l'async cattura una cwd sbagliata, il problema
  cwd-fragile si **amplifica** (il job parte nel posto sbagliato e fallisce in silenzio). Da progettare
  in modo da **non** regredire su quell'asse — **DA-5**.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-007, REQ-009, REQ-012, REQ-013.
- **Should:** REQ-006 (no torn-write), REQ-008 (induzione SessionStart preservata), REQ-010 (idempotenza),
  REQ-011 (non-distruttività), REQ-015 (timeout coerente), REQ-017 (distribuzione installer), REQ-018
  (privacy).
- **Could:** REQ-014 (change-gate rapido), REQ-016 (degrado onesto se manca il meccanismo non-bloccante).

## 10. Domande aperte

- **DA-1 — Strategia non-bloccante (la scelta di design centrale, NON decisa qui):** tre opzioni da
  valutare in design, non mutuamente esclusive —
  - **(a) re-index in background/async** (job/processo staccato dalla chiusura): la sessione ritorna
    subito, il verdetto `doctor` si calcola separatamente; rischio R-1/R-2.
  - **(b) change-gate rapido**: prima del re-index, un check veloce (mtime/manifest) **salta** del tutto
    lo spawn se nulla è cambiato; sfrutta che l'index è **già incrementale** (FEAT-009/019) → su corpus
    invariato il costo è già ~nullo. Domanda: il gate va **dentro** il core (già presente nell'incrementale)
    o resta un check coarse nell'hook? (R-3).
  - **(c) timeout realistico**: alzare il timeout host; da solo **insufficiente** (R-5), accettabile solo
    come complemento alla separazione del verdetto.
  *Da decidere in design quale combinazione e come interagisce con l'incrementale già esistente.*
- **DA-2 — Semantica del verdetto con re-index asincrono:** se l'index è deferito/in background, il
  `doctor` riflette lo stato **prima** del re-index corrente. È accettabile che `.rag-health.json` sia «al
  più di una sessione indietro» (purché mai stale/assente)? Oppure il verdetto deve attendere il
  completamento (annullando il beneficio non-bloccante)? *Proposta da confermare:* verdetto sullo stato
  **corrente** (pre-index), accettando il lag di una sessione — la freschezza dell'**indice** è garantita
  dall'incrementale, la freschezza dello **stato** dal fatto che è sempre scritto.
- **DA-3 — Concorrenza / processi orfani:** come evitare due re-index sovrapposti (sessioni ravvicinate) e
  processi background orfani? Riuso della guardia single-writer del core (`IndexLockedError`, FEAT-009)
  vs lock proprio nell'hook?
- **DA-4 — Portabilità del meccanismo async in `pwsh`:** quale primitiva non-bloccante è portabile
  Windows + POSIX (`Start-Job`, `Start-Process`, `Start-ThreadJob`, redirezione a file + detach)? Esiste
  un meccanismo unico o servono due rami con degrado onesto (REQ-016)?
- **DA-5 — Valore del timeout host:** se si adotta l'async, il timeout di
  `settings.rag-freshness.json` va **ridotto** (copre solo lo spawn + `doctor`, non il re-index) o
  **mantenuto/alzato**? Coerenza del valore fra Claude e Copilot CLI.
- **DA-6 — Fusione vs separazione del passo `doctor`:** conviene calcolare il verdetto `doctor`
  **prima** di lanciare l'index in background (verdetto sempre scritto, index fire-and-forget), oppure
  separarli in due trigger? *Proposta:* nell'unico SessionEnd, scrivere il verdetto `doctor` **per primo**
  (rapido, deterministico) e poi avviare il re-index non-bloccante — così REQ-004 è soddisfatto by
  construction.
