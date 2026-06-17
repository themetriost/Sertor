# Requisiti — Ciclo di vita dell'installer (upgrade e uninstall)

<!-- Deriva da: FEAT-008 (epica sertor-cli) -->

> **Stato:** prima decomposizione — domande aperte §10 da girare all'utente prima di avanzare al
> design. Le assunzioni adottate in assenza di risposta sono marcate **[ASSUNTO]**.

---

## 1. Contesto e problema (perché)

L'installer Sertor (`sertor install wiki/rag`, `sertor-flow install`) copre oggi **solo il primo
install**: ogni artefatto viene creato se assente, o saltato se già presente (strategia
`CREATE_IF_ABSENT`), oppure unito in modo additivo (strategie `MERGE_*`). Questo design
garantisce idempotenza e non-distruttività al primo install, ma lascia due operazioni del ciclo di
vita senza un comando dedicato:

1. **Upgrade**: quando Sertor avanza su `master` — aggiungendo superfici, modificando artefatti
   standalone (`FILE`/`CREATE_IF_ABSENT`) o cambiando i blocchi a marker — ri-eseguire
   `sertor install` **non produce l'effetto atteso**:
   - i file già presenti vengono `SKIPPED` anche se il bundle ha una versione più recente;
   - gli artefatti obsoleti (es. il file `.vscode/mcp.json` di un assistente dismesso dopo il
     passaggio da `--assistant copilot` a `--assistant copilot-cli`) restano sul filesystem
     dell'ospite senza essere rimossi.
   - il blocco a marker (`MARKER_BLOCK`) è anch'esso `SKIPPED` se i marker sono presenti, anche se
     il contenuto del blocco è cambiato.

   Oggi il workaround documentato in `docs/install.md` §10.1 è `uvx --refresh … sertor install …`
   (forza il rebuild dell'installer) + re-run del plan idempotente. Funziona per i file assenti e
   per i merge additivi, ma **non rimuove gli obsoleti** né **aggiorna i file già presenti**.

2. **Uninstall**: non esiste ancora il comando `sertor uninstall`. La procedura di rimozione è
   documentata in `docs/install.md` §10.2 come procedura manuale in quattro categorie (A runtime
   isolato, B asset standalone, C file condivisi editati a marker, D registrazione client MCP) con
   uno script PowerShell helper. La produttivizzazione di questa procedura in un comando è
   necessaria per rendere Sertor rimovibile in modo affidabile e ripetibile, soprattutto su ospiti
   non-Windows dove lo script PowerShell non è l'opzione naturale.

**Riferimento architetturale.** Il `sertor-install-kit` (`packages/sertor-install-kit/`) espone
`ArtifactKind` / `WriteStrategy` / `Outcome` / `execute_plan` (callback-based) / `write_marker_block`
(idempotente su marker propri, `packages/sertor-install-kit/src/sertor_install_kit/claude_md.py`).
I plan-builder (`build_rag_plan`, `build_install_plan`, `build_governance_plan`) producono liste di
`Artifact` ordered; `execute_plan` le percorre con fail-fast no-rollback. Non esiste oggi nessun
meccanismo di rimozione inversa nel kit.

---

## 2. Obiettivi e criteri di successo

| ID | Criterio | Misura |
|----|----------|--------|
| CS-1 | **Rimozione completa** | Dopo `sertor uninstall <capacità>` (o equivalente), su un ospite di riferimento, la ricerca di ogni file/entry Sertor produce zero risultati (0 artefatti residui tracciabili). |
| CS-2 | **Non distruttività** | In **0** esecuzioni `uninstall` vengono eliminati o troncati file dell'utente che non sono **interamente** di proprietà Sertor (es. `CLAUDE.md`, `.gitignore`, `.mcp.json` con server non-Sertor). |
| CS-3 | **Upgrade esplicito** | Dopo `sertor upgrade <capacità>`, gli artefatti standalone (`FILE`/`CREATE_IF_ABSENT`) aggiornati nel bundle risultano **sovrascritti** sul filesystem dell'ospite; il conteggio `updated` nel report è > 0 se e solo se il bundle differisce dalla versione installata. |
| CS-4 | **Obsoleti rimossi** | Dopo `sertor upgrade` con cambio di assistente (es. `copilot` → `copilot-cli`), i file dell'assistente dismesso che non appartengono all'ospite vengono rimossi; in **0** casi vengono rimossi file dell'utente non creati da Sertor. |
| CS-5 | **Idempotenza** | Ri-eseguire `uninstall` su un ospite già pulito termina con exit code `0` e report `0 errori`; ri-eseguire `upgrade` su un ospite già aggiornato termina con exit code `0` e report `0 updated`. |
| CS-6 | **Dry-run** | Eseguire con `--dry-run` non modifica lo stato del filesystem; il report descrive ogni operazione che **sarebbe** stata eseguita. |
| CS-7 | **Osservabilità** | Il report di `upgrade`/`uninstall` riporta per ogni artefatto lo stato effettivo (updated / removed / skipped / error) e un conteggio sommario, nello stesso formato del report `install`. |
| CS-8 | **Multi-assistente** | `uninstall` rimuove correttamente gli artefatti per tutti e tre i target assistenti (`claude`, `copilot`, `copilot-cli`) supportati dall'installer attuale. |
| CS-9 | **Dati utente protetti** | Il `wiki/` non viene rimosso in assenza di consenso esplicito (`--purge-wiki` o equivalente [DA CHIARIRE: Q1]); un messaggio informativo specifica quante pagine/byte il wiki contiene. |

---

## 3. Stakeholder e attori

- **Maintainer del progetto ospite**: vuole aggiornare Sertor dopo un avanzamento su `master`, o
  rimuoverlo completamente da un ospite (es. per cambio di tecnologia, abbandono del progetto).
- **Team di sviluppo (utenti multipli)**: garantisce che ogni membro possa ripetere upgrade/uninstall
  senza conoscere la struttura interna degli artefatti.
- **CI/automazione (futuro)**: potrebbe invocare `upgrade` periodicamente; il report JSON è il
  contratto.
- **`sertor-install-kit`** (dipendenza interna): il kit deve esporre le primitivi necessarie a
  un'operazione inversa o a una sovrascrittura controllata.

---

## 4. Ambito

### In ambito

- Comando **`sertor upgrade <capacità>`** (con `--assistant`, `--dry-run`, `--json`): aggiorna
  artefatti standalone modificati, rimuove artefatti diventati obsoleti, aggiorna il contenuto dei
  blocchi a marker se il bundle è cambiato.
- Comando **`sertor uninstall <capacità>`** (con `--assistant`, `--dry-run`, `--json`, e un flag
  optin per la rimozione del wiki — Q1): rimozione completa e selettiva di tutti gli artefatti
  installati dalla capacità indicata, rispettando la tipologia A/B/C/D.
- Copertura delle **tre capacità installabili** tramite `sertor`: `wiki`, `rag`, e `governance`
  (puntatore a `sertor-flow`; per governance il comportamento è [DA CHIARIRE: Q4]).
- Supporto ai **tre assistenti** (`claude`, `copilot`, `copilot-cli`).
- Operazioni su **tipo C** (file condivisi): rimozione dei soli blocchi a marker Sertor
  (`SERTOR:WIKI-RITUAL`, `SERTOR:RAG-USAGE`, `SERTOR:SDLC-RITUAL`) e delle sole entry Sertor in
  `.claude/settings.json` / `.gitignore` / `.github/hooks/sertor-hooks.json`.
- Operazioni su **tipo D** (registrazione client MCP): de-registrazione via `claude mcp remove` per
  la registrazione in scope `local`; rimozione entry dai file MCP per scope `project`.
- Flag **`--dry-run`** valido sia per `upgrade` che per `uninstall`.
- Report in formato umano e `--json` (schema `install.report/1` esteso con nuovi outcome).

### Fuori ambito

- **Rollback automatico** a una versione precedente del bundle: gestione versioni è FEAT-006
  (distribuzione PyPI) o oltre.
- **Upgrade del runtime Python** (`.sertor/` venv e `uv`): oggi gestito con `uv add` idempotente
  ri-eseguito dal plan; non esteso da questa feature.
- **Upgrade/uninstall del corpus dati** (indice Chroma, SQLite observability/memory/cache):
  rimangono file dell'utente; la documentazione li cita ma il comando non li tocca
  **[ASSUNTO: la semantica è "togli Sertor dal progetto, non i dati del progetto"]**.
- **Distribuzione di `sertor upgrade`/`sertor uninstall` su ospiti via installer**: i nuovi
  comandi sono parte del pacchetto `sertor`; un ospite che ha già installato Sertor deve aggiornare
  il pacchetto `sertor` stesso per ottenerli (bootstrap del bootstrap) — fuori ambito qui.
- **Uninstall cross-utente o di sistema**: solo l'istanza nella `--target` corrente.
- **`sertor-flow upgrade`/`sertor-flow uninstall`**: comportamento simmetrico per il pacchetto
  `sertor-flow` — [DA CHIARIRE: Q4] se coperto da questo ticket o da uno separato.
- **GUI o wizard interattivo**: solo CLI non interattivo (flag espliciti).
- **Notifiche push / CI automatica**: upgrade su eventi è fuori ambito.

---

## 5. Requisiti funzionali (EARS)

### 5.1 Requisiti comuni (upgrade e uninstall)

**REQ-001 (Ubiquitous):** *The installer shall accept a `--dry-run` flag on both `upgrade` and
`uninstall` subcommands; when the flag is active, the installer shall not modify any file on the
filesystem and shall emit a report describing every operation that would have been performed.*

**REQ-002 (Ubiquitous):** *The installer shall accept a `--json` flag on both `upgrade` and
`uninstall` subcommands and emit a machine-readable report conforming to schema `install.report/1`
(extended with outcome values `updated` and `removed`).*

**REQ-003 (Ubiquitous):** *The installer shall accept `--assistant <id>` (`claude` | `copilot` |
`copilot-cli`) on both `upgrade` and `uninstall` subcommands, defaulting to `claude`, to select
which set of assistant-specific artifacts to operate on.*

**REQ-004 (Unwanted):** *If `upgrade` or `uninstall` encounters a domain error on a single artifact,
then the installer shall record the error outcome, name the failed artifact in the report, and stop
(fail-fast, no-rollback), leaving already-processed artifacts in their new state.*

**REQ-005 (Ubiquitous):** *The installer shall exit with code `0` when the operation completes with
zero errors (even if every artifact was `skipped`), `1` on a domain error, and `2` on wrong usage.*

**REQ-006 (Event-driven):** *When `upgrade` or `uninstall` completes, the installer shall print a
summary report with per-artifact outcome and aggregated counts (updated / removed / skipped /
created / errors).*

### 5.2 Requisiti di upgrade

**REQ-010 (Event-driven):** *When the user runs `sertor upgrade <capability>`, the installer shall
compare the content of each standalone asset (`FILE`/`CREATE_IF_ABSENT`) in the bundle against
the installed version; if they differ, the installer shall overwrite the installed file with the
bundle version and record outcome `updated`.*

**REQ-011 (Event-driven):** *When the user runs `sertor upgrade <capability>`, the installer shall
update the content of each marker block (`MARKER_BLOCK`) if the bundle content differs from the
content currently inside the markers; the content outside the markers shall not be modified.*

**REQ-012 (Event-driven):** *When the user runs `sertor upgrade <capability>` and an artifact
present in the previous bundle is no longer present in the current bundle (obsolete artifact), the
installer shall remove the obsolete artifact from the host filesystem and record outcome `removed`.*

**REQ-013 (Unwanted):** *If an artifact is marked as obsolete by `upgrade` but its path does not
match any Sertor-owned path, then the installer shall skip the removal, emit a warning, and
continue.*

**REQ-014 (Event-driven):** *When the user runs `sertor upgrade <capability>` and an artifact is
already up to date (bundle content equals installed content), the installer shall leave the artifact
unchanged and record outcome `skipped`.*

**REQ-015 (Unwanted):** *If `--dry-run` is active during `upgrade`, then the installer shall
compute the diff (updated / removed / skipped) without writing to disk and report the projected
outcome.*

**REQ-016 (Event-driven):** *When the user runs `sertor upgrade rag` and changes the `--assistant`
flag relative to the previously installed assistant, the installer shall add the new assistant's
artifacts and remove the old assistant's artifacts that are not shared, without affecting artifacts
common to both assistants.*

**REQ-017 (Ubiquitous — dipende da Q2):** *The installer shall maintain a record of which artifacts
have been installed for each capability and assistant, sufficient to determine which artifacts are
obsolete on a subsequent upgrade.* **[DA CHIARIRE: Q2 — manifest d'installazione vs re-install + diff
a posteriori; vedi §10]**

### 5.3 Requisiti di uninstall

**REQ-020 (Event-driven):** *When the user runs `sertor uninstall <capability>`, the installer
shall remove every standalone artifact (type B) installed by `sertor install <capability>` that is
entirely Sertor-owned (not a shared file like `CLAUDE.md` or `.gitignore`).*

**REQ-021 (Event-driven):** *When the user runs `sertor uninstall <capability>`, the installer
shall remove only the Sertor-owned marker blocks (identified by their start/end marker pair) from
each shared file (type C), leaving the remainder of the file intact byte-for-byte.*

**REQ-022 (Event-driven):** *When the user runs `sertor uninstall <capability>`, the installer
shall remove only the Sertor-owned entries from `.claude/settings.json` (hook entries whose command
references a Sertor script), leaving all other entries intact.*

**REQ-023 (Event-driven):** *When the user runs `sertor uninstall <capability>`, the installer
shall remove only the Sertor-owned lines from `.gitignore` (the lines appended by `install rag`:
`.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env`), leaving all other lines intact.*

**REQ-024 (Event-driven):** *When the user runs `sertor uninstall rag` and the RAG was installed
with `--mcp-scope local`, the installer shall de-register the `sertor-rag` MCP server from the
client (type D) via `claude mcp remove sertor-rag`.*

**REQ-025 (Event-driven):** *When the user runs `sertor uninstall rag` with `--assistant copilot`
or `--assistant copilot-cli`, the installer shall remove the MCP config file if and only if it
contains only the `sertor-rag` server entry; if the file contains other servers, the installer
shall remove only the `sertor-rag` entry and preserve the rest.*

**REQ-026 (Unwanted):** *If `sertor uninstall <capability>` is run and no artifact of that
capability is found on the target, then the installer shall complete successfully (exit `0`) and
report all artifacts as `skipped` (idempotency).*

**REQ-027 (Event-driven):** *When the user runs `sertor uninstall wiki`, the installer shall not
remove the `wiki/` directory unless an explicit opt-in flag is supplied
[DA CHIARIRE: Q1 — nome del flag e comportamento di default].*

**REQ-028 (Where — opt-in per Q1):** *Where the explicit wiki-removal opt-in flag is supplied to
`sertor uninstall wiki`, the installer shall display the number of pages and approximate size of
the `wiki/` directory and require either an interactive confirmation or a `--yes` flag before
deleting it.*

**REQ-029 (Unwanted):** *If `--dry-run` is active during `uninstall`, then the installer shall
report what would be removed without performing any deletion or modification.*

**REQ-030 (Event-driven):** *When the user runs `sertor uninstall rag`, the installer shall remove
the `.sertor/` directory (type A: isolated runtime with venv, `.env`, Chroma store, SQLite files,
code graph, `pyproject.toml`, `uv.lock`) in its entirety.*

**REQ-031 (Ubiquitous):** *The installer shall never remove any file or directory that Sertor did
not create and is not explicitly listed as owned by the installed capability.*

### 5.4 Requisiti di osservabilità e interazione

**REQ-040 (Ubiquitous):** *The installer shall emit a `log_event` (operation = `upgrade` or
`uninstall`) with counts and capability at the end of every operation, consistent with the existing
observability contract.*

**REQ-041 (Event-driven):** *When `--json` is active, the installer shall emit the report to stdout
as a single JSON object (schema `install.report/1` with added outcome values), suitable for
programmatic consumption.*

---

## 6. Requisiti non funzionali

**NFR-01 (Non-distruttività):** Nessuna operazione di `upgrade` o `uninstall` può rimuovere o
sovrascrivere contenuto utente al di fuori degli artefatti esplicitamente gestiti dal kit. Il
test di accettazione è: un file con contenuto non-Sertor in una posizione Sertor-owned (es.
`CLAUDE.md` con paragrafi utente) sopravvive invariato tranne per le porzioni a marker.

**NFR-02 (Idempotenza):** Ri-eseguire `upgrade` o `uninstall` N volte produce lo stesso stato
finale di una singola esecuzione. Il test: due run consecutivi producono lo stesso report salvo i
conteggi `skipped`/`0 updated`/`0 removed` al secondo run.

**NFR-03 (Host-agnosticità):** `upgrade` e `uninstall` devono funzionare su qualsiasi repo ospite
indipendentemente dal linguaggio/tecnologia; il meccanismo non presuppone che il progetto ospite
abbia Python, `uv` o altri prerequisiti oltre a `uv` per l'invocazione di Sertor stesso
(Principio X).

**NFR-04 (Performance):** Il tempo di esecuzione di `uninstall` su un ospite tipico
(< 100 artefatti) deve essere < 10 s su filesystem locale; non è un'operazione di rete.

**NFR-05 (Sicurezza — segreti):** `upgrade` non sovrascrive mai i valori di `.sertor/.env`
(solo le chiavi assenti nel file esistente vengono aggiunte, coerentemente con la strategia
`MERGE_ENV` attuale). `uninstall` rimuove `.sertor/` compreso `.sertor/.env`; il report non include
il contenuto dei file rimossi.

**NFR-06 (Osservabilità):** Il report di `upgrade`/`uninstall` usa lo stesso schema JSON
(`install.report/1`) già consumato dagli ospiti, esteso con i nuovi outcome `updated` e `removed`.
Non si introduce un secondo schema.

**NFR-07 (Stdlib-first nel kit):** Le operazioni di upgrade/uninstall non aggiungono dipendenze
esterne al `sertor-install-kit`; le primitive di diff file e rimozione usano solo la libreria
standard.

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli (invarianti dall'epica e dal kit)

- **install ≠ run**: `upgrade` e `uninstall` non avviano mai indicizzazione o operazioni RAG.
- **Fail-fast no-rollback**: coerente con `execute_plan` nel kit
  (`packages/sertor-install-kit/src/sertor_install_kit/executor.py`): in caso di errore su un
  artefatto, lo stato parziale rimane sul disco; re-eseguire completa l'operazione.
- **`sertor-install-kit` stdlib-only**: nessuna dipendenza aggiuntiva al kit.
- **Separazione `sertor` / `sertor-flow`**: `sertor` non ha dipendenza da `sertor-flow`; il
  comportamento di `sertor uninstall governance` è limitato al puntatore (come `sertor install
  governance`), a meno che [Q4] non indichi altrimenti.

### Assunzioni adottate

- **[ASSUNTO]** Gli artefatti di tipo A (`.sertor/`) sono interamente di proprietà Sertor e
  possono essere rimossi in blocco senza ulteriori conferme (il `.sertor/.env` non contiene dati
  utente non riproducibili).
- **[ASSUNTO]** Le operazioni su tipo C (rimozione marker blocks, linee `.gitignore`, entry
  settings) identificano gli artefatti Sertor tramite le marker string note
  (`SERTOR:WIKI-RITUAL`, `SERTOR:RAG-USAGE`, `SERTOR:SDLC-RITUAL`, prefisso linee gitignore
  `.sertor/`); non è necessaria un ulteriore store di tracciatura per questi.
- **[ASSUNTO Q2]** L'upgrade degli artefatti di tipo `FILE`/`CREATE_IF_ABSENT` può essere
  implementato come diff-e-overwrite a posteriori (confronto bundle vs disco), senza un manifest
  di installazione esplicito, **a meno che** la rimozione degli obsoleti non richieda sapere cosa
  era stato installato nella sessione precedente — questo è il punto critico della Q2.
- **[ASSUNTO]** `sertor-flow upgrade`/`sertor-flow uninstall` sono fuori ambito di questo ticket
  ma devono poter riusare le stesse primitive del kit una volta stabilite qui.

### Dipendenze

- `sertor-install-kit`: le nuove strategie di scrittura (`UPDATE_IF_CHANGED`, `REMOVE`, 
  `REMOVE_MARKER`, `REMOVE_LINES`, `DEREGISTER_CLI`) — o equivalenti — devono essere aggiunte
  al kit come `WriteStrategy` e/o come nuovi handler in `ArtifactKind`. Questo è design; il
  requisito è che il kit **esponga** le capacità inverse senza imporre uno schema specifico.
- `docs/install.md` §10.1–§10.2: la documentazione della procedura manuale deve essere aggiornata
  per puntare ai nuovi comandi automatici quando disponibili.
- `packages/sertor/src/sertor_installer/install_rag.py` e `install_wiki.py`: i plan-builder
  esistenti definiscono la lista canonica degli artefatti; i plan di `upgrade`/`uninstall` devono
  derivare dallo stesso sorgente di verità.

---

## 8. Rischi

| ID | Rischio | Probabilità | Impatto | Mitigazione |
|----|---------|-------------|---------|-------------|
| R-01 | Rimozione accidentale di contenuto utente in file shared (`CLAUDE.md`, `.gitignore`) | Media | Alto | Regex/parser per marker di rimozione testati su fixture con contenuto misto; dry-run obbligatorio nel test di accettazione |
| R-02 | Artefatti obsoleti non tracciabili senza manifest | Alta (per il problema upgrade) | Medio | Definire il meccanismo di tracciatura prima del design (Q2); in alternativa limitare il perimetro dell'upgrade agli artefatti noti a priori dal bundle corrente |
| R-03 | Rimozione del `wiki/` con documentazione reale accumulata | Media | Alto | Opt-in esplicito + warning con conteggio pagine (REQ-027/028); CS-9 misura il controllo |
| R-04 | De-registrazione MCP fallita (cliente non disponibile sul PATH) | Media | Basso | Fail-fast con messaggio actionable e comando manuale fallback (come oggi per `MCP_REGISTER`) |
| R-05 | Divergenza tra `sertor upgrade` e `sertor-flow upgrade` | Media (futuro) | Medio | Le primitive di rimozione nel kit devono essere progettate per essere riusabili da `sertor-flow` |
| R-06 | Complessità del manifest d'installazione (se adottato per Q2) | Bassa–Media | Medio | Valutare se il diff a posteriori copre i casi d'uso reali prima di introdurre un nuovo store persistente |

---

## 9. Prioritizzazione (MoSCoW)

| Gruppo | Requisiti | Priorità | Motivazione |
|--------|-----------|----------|-------------|
| **Uninstall — tipo A e B** | REQ-020, REQ-026, REQ-030, REQ-031 | **Must** | Rimuovere il runtime e gli asset standalone sono le operazioni più usate e più sicure; nessun rischio di contenuto utente perso |
| **Uninstall — tipo C (marker/settings/gitignore)** | REQ-021, REQ-022, REQ-023 | **Must** | Senza di esse l'uninstall lascia residui nei file shared; già documentata la regex come procedura manuale |
| **Uninstall — tipo D (de-registrazione MCP)** | REQ-024, REQ-025 | **Must** | Necessario per rimuovere il server MCP dal client |
| **Dry-run e report** | REQ-001, REQ-002, REQ-005, REQ-006, REQ-029 | **Must** | Invariante di sicurezza: nessuna operazione distruttiva senza visibilità |
| **Wiki opt-in + warning** | REQ-027, REQ-028 | **Must** | Protezione del contenuto utente (CS-9) |
| **Idempotenza uninstall** | REQ-026 | **Must** | Invariante dell'epica |
| **Upgrade artefatti standalone** | REQ-010, REQ-011, REQ-014, REQ-015 | **Should** | Priorità alta ma subordinata alla chiarifica Q2 sul meccanismo di tracciatura |
| **Upgrade artefatti obsoleti** | REQ-012, REQ-013, REQ-016 | **Should** | Dipende da Q2; può essere rinviato se il diff a posteriori non è sufficiente |
| **Manifest d'installazione (se necessario per Q2)** | REQ-017 | **Could** | Se il diff a posteriori non copre tutti i casi, introduce complessità; alternativa: limitare l'upgrade al bundle corrente |
| **Flag --assistant su uninstall** | REQ-003 (per uninstall) | **Should** | Necessario per ospiti multi-assistente |
| **Osservabilità log_event** | REQ-040, REQ-041 | **Should** | Coerenza con il contratto di osservabilità esistente |
| **`sertor-flow upgrade`/`uninstall`** | (fuori ambito) | **Won't (questo ticket)** | Fuori ambito; le primitive del kit devono però essere progettate per il riuso |

---

## 10. Domande aperte

Le domande sono prioritizzate: le prime due bloccano il design; le successive influenzano l'ambito
ma non bloccano.

---

**Q1 — Comportamento di `uninstall` rispetto al `wiki/` (critica — blocca REQ-027/028)**

Il `wiki/` è un asset di tipo B (standalone, interamente Sertor-owned a livello di struttura), ma
può contenere **documentazione reale prodotta dall'utente** dopo l'installazione. Ci sono tre
opzioni:

- **(a) Non rimuovere mai** il `wiki/` di default; richiedere `--purge-wiki` esplicito (con
  conferma o `--yes`). Raccomandato: massima protezione, comportamento prevedibile.
- **(b) Rimuovere solo la struttura Sertor** (cartelle di tassonomia vuote, `index.md`,
  `wiki.config.toml`) ma non le pagine utente. Complesso e fragile (come distinguere le pagine
  "Sertor" da quelle utente?).
- **(c) Chiedere conferma interattiva** sempre, con preview del contenuto. Rompe i flussi CI/non
  interattivi.

**Raccomandazione: opzione (a)** — `wiki/` non viene rimosso a meno di `--purge-wiki` (o
`--purge-data`); il flag richiede `--yes` o conferma interattiva, non combinabile con `--dry-run`.
Il nome `--purge-wiki` è più esplicito di `--purge-data` (circoscritto alla capacità).

---

**Q2 — Meccanismo di tracciatura per upgrade (critica — blocca REQ-012/017)**

L'upgrade degli artefatti **obsoleti** (quelli presenti nella versione precedente del bundle ma
non in quella corrente) richiede sapere cosa era installato. Due approcci:

- **(a) Diff a posteriori**: il bundle corrente dichiara la lista completa degli artefatti; se un
  file è su disco ma NON è nel bundle corrente E corrisponde a un path Sertor-owned, viene rimosso.
  Semplice, nessun store aggiuntivo, ma richiede una lista statica dei "path Sertor-owned" (da
  mantenere aggiornata).
- **(b) Manifest d'installazione**: un file `.sertor/sertor-manifest.json` (o simile) scritto
  all'install e aggiornato all'upgrade registra la lista degli artefatti installati per
  capacità+assistente. Preciso, ma introduce uno store persistente da mantenere e gestire
  (idempotenza, formato, conflitti multi-host).

**Raccomandazione: opzione (a) per il primo taglio** — la lista dei path Sertor-owned è già
implicita nei plan-builder ed è piccola; un dizionario `{capability: {assistant: [paths]}}` nel
codice è sufficiente. Il manifest (opzione b) è adeguato solo se la lista di path diventa
instabile o se si vuole supportare più versioni concorrenti installate sullo stesso host.

---

**Q3 — Granularità: uninstall per-capacità o tutto-in-uno? (media — influenza UX)**

Due possibilità:

- **(a) Per-capacità**: `sertor uninstall wiki`, `sertor uninstall rag`, `sertor uninstall
  governance`. Granularità massima; permette di rimuovere solo il RAG mantenendo il wiki.
- **(b) Tutto-in-uno**: `sertor uninstall` rimuove tutto. Più semplice; un ospite spesso rimuove
  Sertor interamente.
- **(c) Entrambi**: `sertor uninstall` equivale a `sertor uninstall wiki rag governance`.

**Raccomandazione: opzione (c)** — default all-in-one per il caso comune; la sintassi
per-capacità per gli ospiti che vogliono rimuovere solo una parte. Coerente con `sertor install
<capacità>`.

---

**Q4 — `sertor-flow upgrade`/`uninstall`: stesso ticket o ticket separato? (bassa — ambito)**

`sertor-flow` è un pacchetto separato senza dipendenza da `sertor-core`. Il suo ciclo di vita
(upgrade degli agenti, skill SpecKit, blocco SDLC, constitution starter) è simmetrico a quello di
`sertor`, ma operazionalizzato nel CLI `sertor-flow`, non in `sertor`.

- **(a) Stesso ticket**: definire i requisiti di `sertor-flow upgrade`/`uninstall` qui, con
  riferimento alle stesse primitive del kit.
- **(b) Ticket separato**: FEAT-008 copre solo il pacchetto `sertor`; `sertor-flow` ha una feature
  gemella nel suo backlog.

**Raccomandazione: opzione (b)** — il pacchetto è separato, il team che lo mantiene può avere
tempistiche diverse; le primitive del kit vengono progettate per essere riusabili da `sertor-flow`
senza che questo ticket le blocchi. Annotare come dipendenza nella roadmap.
