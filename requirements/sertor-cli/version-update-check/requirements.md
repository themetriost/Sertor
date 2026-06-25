# Requisiti — Auto-update version check (avviso d'aggiornamento)

<!-- Deriva da: FEAT-013 (epica sertor-cli / E2) -->

## 1. Contesto e problema (perché)

Sertor è distribuito in modo **interim via `git+url` non-PyPI** (DA-4 dell'epica), e `uvx` **cacha** la
build per revisione: dopo che `master` si muove, un ospite può restare **silenziosamente** su una
versione vecchia di Sertor (installer, runtime RAG in `.sertor/.venv`, asset wiki/governance). Oggi
l'unico modo per accorgersene è la sezione manuale «Refreshing to the latest» della doc
(`docs/install.md §10.1`): nessun **segnale automatico**.

Questa feature aggiunge un **avviso non invasivo a inizio sessione**: se la versione installata di
Sertor non è l'ultima, l'agente/utente lo **vede** e riceve il comando per aggiornare; **l'utente
decide** se e quando farlo. È il **gemello concettuale di E10-FEAT-011** (hook di freschezza
dell'indice): stesso confine **D↔N** — un harness deterministico **segnala**, l'utente **agisce** —
e stesso pattern host-facing (hook distribuito dall'installer, parità Claude / Copilot CLI). La fonte
di verità della versione è il file **`/VERSION`** a radice del repo, già letto dinamicamente da tutti
e quattro i `pyproject` (singola fonte per `sertor`, `sertor-flow`, `sertor-core`,
`sertor-install-kit`).

> Il *come* (URL esatto, formato del file di stato, fusione con l'hook di freschezza) è materia della
> fase di **design**. Qui solo *cosa* e *perché*.

## 2. Obiettivi e criteri di successo

- **CS-1 (avviso corretto):** a inizio sessione, se la versione installata è **più vecchia**
  dell'ultima pubblicata, l'utente vede un avviso che nomina versione corrente, ultima versione e il
  **comando d'aggiornamento**; se è allineata (o più nuova), **nessun avviso**.
- **CS-2 (economico & non bloccante):** il check costa **al più ~1 chiamata di rete al giorno** per
  ospite (esito cachato); **non blocca** l'avvio di sessione; **offline → nessun avviso e nessun
  errore** (la sessione parte normalmente).
- **CS-3 (copertura 3 dimensioni):** il check copre tutte le dimensioni installate — RAG + wiki
  (pacchetto `sertor`) e governance (`sertor-flow`) — usando `/VERSION` come **fonte unica**.
- **CS-4 (solo avviso):** in **0** casi la feature applica un aggiornamento da sola; notifica soltanto.
- **CS-5 (host-agnostico & installabile):** l'asset di version-check è installabile su **Claude e
  Copilot CLI** via `sertor install`, con **parità** e ciclo di vita (install/upgrade/uninstall),
  additivo e non distruttivo.
- **CS-6 (D↔N & privacy):** il check **non invoca alcun LLM** e **non importa `sertor_core`**; l'unico
  traffico di rete è la lettura del `/VERSION` pubblico (nessun contenuto/segreto del progetto esce).

## 3. Stakeholder e attori

- **Owner/utente dell'ospite:** riceve l'avviso e decide se aggiornare.
- **Agente frontier dell'ospite (Claude/Copilot):** veicola l'avviso a inizio sessione.
- **L'installer `sertor`/`sertor-flow`:** deposita e mantiene l'asset (lifecycle FEAT-008).
- **`/VERSION` + distribuzione `git+url`:** fonte della «ultima versione».
- **Comandi esistenti `sertor upgrade` / `uvx --refresh`:** l'azione che l'avviso raccomanda (non
  reimplementati qui).

## 4. Ambito

### In ambito
- Determinazione «installato vs ultimo» basata sul **bump di `/VERSION`** su `master`.
- **Avviso** a inizio sessione (parità Claude script / Copilot CLI prompt), con comando d'aggiornamento.
- **Caching** dell'esito (~1/giorno) con stato persistito sotto `.sertor/`.
- Degradazione **non-fatale** (offline/errore/indeterminato → skip silenzioso).
- **Distribuzione** dell'asset via installer (parità + lifecycle) e voce `.gitignore`.

### Fuori ambito
- L'**applicazione** dell'aggiornamento: è dei comandi esistenti `sertor upgrade` / `uvx --refresh`
  (questa feature li **raccomanda**, non li sostituisce).
- Rilevazione **a livello di commit** (SHA di `master`): **scartata** per decisione (low-noise sul
  bump di `/VERSION`); se mai servisse, è una capacità separata da promuovere.
- Pubblicazione/versioning **PyPI** (FEAT-006, Won't): qui «ultimo» = `/VERSION` su `master`.
- La pulizia degli artefatti obsoleti durante l'aggiornamento: è **E10-FEAT-015** (debito separato).
- La **freschezza dell'indice** RAG: è **E10-FEAT-011** (gemello, già consegnato).

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Event-driven):** *When a session starts on a host with a Sertor capability installed, the
  system shall determine whether the installed Sertor version is the latest available.*
- **REQ-002 (Ubiquitous):** *The system shall determine the latest available version by reading the
  `/VERSION` file from the project's `git+url` distribution source (master) and comparing it to the
  installed version.*
- **REQ-003 (Event-driven):** *When the installed version is older than the latest, the system shall
  present the user a notice naming the installed version, the latest version, and the recommended
  update command (`sertor upgrade` or `uvx --refresh …`).*
- **REQ-004 (Unwanted):** *If the installed version equals or is newer than the latest, then the
  system shall present no update notice.*
- **REQ-005 (Ubiquitous):** *The system shall never apply an update automatically; it shall only notify
  and leave the decision and the action to the user.*
- **REQ-006 (Optional/State-driven):** *The version check shall run at most once per ~24h per host;
  while a cached result is still fresh, the system shall reuse it without a new network call.*
- **REQ-007 (Ubiquitous):** *The system shall persist the last check result (latest seen version,
  installed version, timestamp, verdict) under the runtime folder `.sertor/` (e.g.
  `.sertor/.version-check.json`).*
- **REQ-008 (Unwanted):** *If the network is unavailable or the version lookup fails, then the system
  shall skip the check silently (no notice, no error) and the session shall start normally (exit 0).*
- **REQ-009 (Unwanted):** *If `/VERSION` cannot be parsed or the installed version cannot be determined,
  then the system shall treat the check as inconclusive and skip silently (never a false "you are
  behind").*
- **REQ-010 (Ubiquitous):** *The check shall cover every installed Sertor dimension — RAG + wiki (the
  `sertor` package) and governance (`sertor-flow`) — using `/VERSION` as the single source of truth.*
- **REQ-011 (Event-driven):** *When more than one Sertor package is installed and they report different
  installed versions, the system shall name which dimension(s) are behind.*
- **REQ-012 (Ubiquitous):** *The version-check notice shall be delivered through the host's session
  mechanism with parity across assistants: on Claude via a hook script, on the Copilot CLI via a static
  SessionStart prompt that instructs the agent to read the persisted state and relay the notice.*
- **REQ-013 (Optional):** *Where the user installs a Sertor capability, the installer shall deposit the
  version-check asset and its wiring for the chosen assistant (Claude / Copilot CLI), non-destructively
  and idempotently, with full lifecycle (install / upgrade / uninstall).*
- **REQ-014 (Ubiquitous):** *The system shall add `.sertor/.version-check.json` to the host
  `.gitignore` (regenerable state, never versioned).*
- **REQ-015 (Ubiquitous):** *The check shall invoke no LLM and shall not import `sertor_core`; it shall
  use only deterministic means (a plain HTTP GET of `/VERSION` + a file read/compare).*
- **REQ-016 (Ubiquitous):** *The check shall transmit no project content or secrets; the only network
  egress shall be the read of the public `/VERSION`.*
- **REQ-017 (Event-driven):** *When the user has updated Sertor, the system shall, on the next check,
  reflect the new installed version and return the verdict to up-to-date (the loop closes).*
- **REQ-018 (Optional):** *Where a forced re-check is requested, the system should re-run the check
  ignoring the daily cache.*

## 6. Requisiti non funzionali

- **Performance:** con cache valida → **zero rete**; il check live ha un **timeout breve** e non
  prolunga l'avvio oltre il timeout dell'hook host (NFR gemello di FEAT-011).
- **Affidabilità:** **non-fatale** — l'asset esce sempre **0** e non blocca mai la sessione (gemello
  `rag-freshness.ps1`).
- **Portabilità:** host-agnostico, Windows + POSIX (`pwsh`); **parità** Claude / Copilot CLI.
- **Privacy:** solo GET del `/VERSION` pubblico; nessun contenuto/segreto.
- **Additività:** a feature non installata, comportamento e costo **identici a oggi**; nessun LLM nel
  percorso (Principio D↔N / XI).
- **Osservabilità (opz.):** un eventuale evento è **metrics-only** (nessun path/segreto), coerente con
  gli altri hook.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo distribuzione:** `git+url` non-PyPI (DA-4); «ultima versione» = `/VERSION` su `master`.
- **Fonte unica:** `/VERSION` è letto da tutti i `pyproject` → un solo confronto copre i pacchetti.
- **Dipendenze (consumo, non reimplementazione):**
  - **E10-FEAT-011** — pattern hook `SessionStart`/`SessionEnd` + stato in `.sertor/` (ancoraggio:
    `packages/sertor/src/sertor_installer/install_rag.py` wiring freschezza; `rag-freshness.ps1` /
    `rag-freshness-start.ps1`).
  - **FEAT-008 lifecycle** — install/upgrade/uninstall + `RUNTIME_IGNORES`
    (`packages/sertor-install-kit/.../gitignore_append.py`) per la voce `.sertor/.version-check.json`.
  - **`sertor upgrade` / `uvx --refresh`** — l'azione raccomandata dall'avviso.
- **Assunzione:** la rete verso la sorgente `git+url` (es. GitHub raw) è raggiungibile **quando** il
  check live gira; altrimenti skip silenzioso (REQ-008).
- **Assunzione:** `pwsh` presente per lo script (come per gli altri hook); assente → niente check
  automatico (la doc resta la via manuale).
- **`sertor-core` invariato:** la feature è host-facing (asset installer), additiva.

## 8. Rischi

- **R-1 — Bump di `/VERSION` raro:** se la versione non viene bumpata a ogni cambiamento di `master`,
  l'avviso **sotto-segnala** la staleness. *Accettato per decisione* (low-noise); l'alternativa
  commit-SHA è fuori ambito.
- **R-2 — Latenza/offline all'avvio:** una GET a ogni sessione rallenterebbe/romperebbe offline →
  mitigato da **cache ~1/giorno** + **non-fatale** (REQ-006/008).
- **R-3 — Copilot CLI senza script al SessionStart:** il SessionStart è un **prompt statico** (non può
  fare rete) → vedi **DA-1** (chi esegue il check su Copilot).
- **R-4 — Coesistenza con l'hook di freschezza (FEAT-011):** due segnali a inizio/fine sessione devono
  **coesistere** (entrambi non-fatali, asset/voci distinti).
- **R-5 — Cache stantia dopo un upgrade a metà giornata:** invalidare lo stato quando la versione
  installata cambia (REQ-017), per non avvisare a vuoto.
- **R-6 — Determinare la versione installata** in modo affidabile per ciascun pacchetto: dettaglio di
  design (metadati del pacchetto vs `/VERSION` locale).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-008, REQ-009, REQ-012, REQ-015, REQ-016.
- **Should:** REQ-006 (cache), REQ-007 (stato persistito), REQ-010 (3 dimensioni), REQ-013
  (distribuzione installer), REQ-014 (`.gitignore`), REQ-017 (chiusura loop).
- **Could:** REQ-011 (granularità per-dimensione), REQ-018 (re-check forzato).

## 10. Domande aperte

- **DA-1 — Chi esegue il check su Copilot CLI (e dove conviene su Claude):** il SessionStart di Copilot
  è un **prompt statico** (nessuno script → niente GET di rete). *Proposta (da confermare in design,
  raccomandata):* eseguire il **check in uno script** (sul modello del `SessionEnd` di FEAT-011, che è
  uno script su **entrambi** gli assistenti) che fa la GET, applica la cache e **scrive**
  `.sertor/.version-check.json`; il **SessionStart** (script su Claude, prompt su Copilot) si limita a
  **leggere lo stato e avvisare**. Così la parità regge e nessuno fa rete in un prompt statico.
- **DA-2 — Sorgente esatta del `/VERSION` «ultimo»:** URL raw su `master` (es.
  `raw.githubusercontent.com/<owner>/<repo>/master/VERSION`) — derivabile dalla config di
  distribuzione; come parametrizzarlo per ospiti che puntano a fork/branch diversi?
- **DA-3 — Sorgente della versione «installata»:** metadati del pacchetto (`sertor`/`sertor-flow`/
  `sertor-core`) vs un `/VERSION` locale copiato a install-time? (dettaglio di design).
- **DA-4 — Fusione vs separazione dall'hook di freschezza (FEAT-011):** asset/voce **separati**
  (gemello indipendente, come memory-capture ↔ rag-freshness) **oppure** estendere lo stesso script di
  fine sessione ad aggiornare anche `.version-check.json`? *Proposta:* separati per lifecycle granulare,
  ma valutare il piggyback sul SessionEnd per non duplicare la GET.
- **DA-5 — Confronto di versione:** semantica del confronto (`semver` vs confronto lessicale del
  contenuto di `/VERSION`) e cosa fare se l'installato risulta **più nuovo** del remoto (dev locale).
