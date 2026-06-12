# Feature Specification: `sertor install rag` — installer della capacità RAG

**Feature Branch**: `015-sertor-install-rag`

**Created**: 2026-06-12

**Status**: Draft

**Input**: Decomposizione di `requirements/sertor-cli/install-rag/requirements.md` (deriva da FEAT-002
dell'epica `sertor-cli`). Scope deciso dall'utente: **B — bootstrap completo** (scaffold config +
aggiunta dipendenze), con runtime isolato in `.sertor/`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un comando, RAG pronto sul progetto ospite (Priority: P1)

Un maintainer ha un repository (Python o anche non-Python, es. .NET) e vuole dare al proprio
assistente la capacità di interrogare quel codice via RAG. Da una macchina pulita lancia
`sertor install rag --backend azure` nella radice del repo. Al termine, il progetto ha tutto il
necessario per indicizzare: l'ambiente Python isolato con le dipendenze, il file di configurazione
con i segreti da riempire, e il collegamento al server MCP. L'utente non ha dovuto conoscere nessun
*internal* (uv, extra, subdirectory git).

**Why this priority**: è il cuore della feature e l'obiettivo dichiarato ("installare senza
preoccuparsi degli internals"). Senza questo nulla di valore viene consegnato.

**Independent Test**: su un repo target senza `pyproject.toml`, eseguire
`sertor install rag --backend azure` e verificare che (a) esista `<target>/.sertor/` con il progetto
Python e le dipendenze, (b) esista `<target>/.sertor/.env` col template Azure (segreti vuoti), (c)
esista `<target>/.mcp.json` con il server `sertor-rag`, (d) `.gitignore` ignori gli artefatti
rigenerabili, (e) il comando NON abbia creato alcun indice.

**Acceptance Scenarios**:

1. **Given** un repo target senza `pyproject.toml` e con `uv` disponibile, **When** l'utente esegue
   `sertor install rag --backend azure`, **Then** viene creato `<target>/.sertor/` con un progetto
   uv inizializzato e `sertor-core[azure,mcp,graph,rerank]` aggiunto, più `.sertor/.env`,
   `.mcp.json` (in radice) e le voci `.gitignore`, e il report elenca ogni artefatto come `created`.
2. **Given** l'install completato, **When** si ispeziona lo stato, **Then** nessun indice/collezione
   è stato creato (install ≠ run) e i valori segreti nel `.env` sono vuoti.
3. **Given** l'install completato, **When** l'utente riempie i segreti e lancia (separatamente)
   l'indicizzazione, **Then** il RAG indicizza i sorgenti dell'host escludendo `.sertor/`.

---

### User Story 2 - Idempotenza e non distruttività su repo esistente (Priority: P2)

Il maintainer riesegue `sertor install rag` su un repo che ha già una configurazione propria (un
`.gitignore`, magari un `.mcp.json` con altri server, un `.env` con valori già impostati). L'installer
non deve sovrascrivere nulla di suo: aggiunge solo ciò che manca e, se rieseguito, converge allo
stesso stato senza duplicati.

**Why this priority**: la fiducia nello strumento dipende dal non perdere mai configurazione utente
(REQ-E6 d'epica). È indipendentemente testabile e dà valore anche da solo.

**Independent Test**: predisporre un target con `.gitignore`/`.mcp.json`/`.env` preesistenti con
contenuti utente; eseguire l'install due volte; verificare che i contenuti utente siano preservati,
che le voci `sertor-rag` siano aggiunte una sola volta, e che la seconda passata produca solo esiti
`skipped`/`merged`.

**Acceptance Scenarios**:

1. **Given** un `.mcp.json` con un server `altro`, **When** si esegue l'install, **Then** il server
   `altro` è preservato e `sertor-rag` è aggiunto accanto (merge additivo).
2. **Given** un `.env` con `SERTOR_CORPUS=mio`, **When** si esegue l'install, **Then** il valore
   `mio` non viene sovrascritto e vengono aggiunte solo le chiavi mancanti.
3. **Given** un install già completato, **When** si riesegue lo stesso comando, **Then** lo stato
   finale è identico, senza duplicati, e tutti gli esiti sono `skipped`/`merged`.

---

### User Story 3 - Installer eseguibile standalone via `uvx` (fix di distribuzione) (Priority: P3)

Perché lo scenario P1 ("un comando da macchina pulita") sia reale, il pacchetto installer deve essere
eseguibile con `uvx --from "git+url" sertor install rag` senza che la risoluzione delle sue
dipendenze fallisca. Oggi fallisce perché `sertor` cerca `sertor-core` su PyPI (non pubblicato).

**Why this priority**: è il prerequisito tecnico di P1 dal punto di vista distribuzione; vale anche
per `install wiki`. Indipendentemente verificabile (risoluzione del pacchetto), separato dalla
logica di scaffold.

**Independent Test**: da una macchina/ambiente pulito, eseguire
`uvx --from "git+url#subdirectory=packages/sertor" sertor --help` e verificare exit `0`; in parallelo
verificare che la suite del workspace in sviluppo resti verde (la risoluzione locale non è rotta).

**Acceptance Scenarios**:

1. **Given** una macchina senza il repo Sertor clonato, **When** si esegue
   `uvx --from "git+url#subdirectory=packages/sertor" sertor --help`, **Then** il comando si risolve
   ed esce `0` (sertor-core preso dal git del monorepo, non da PyPI).
2. **Given** il repo Sertor in sviluppo, **When** si esegue la suite di test del workspace, **Then**
   la risoluzione di `sertor-core` continua a venire dal sorgente locale (workspace) e i test passano.

---

### User Story 4 - Backend locale e controllo fine via flag (Priority: P4)

Un utente che lavora local-first sceglie `--backend local` (embeddings via Ollama) e, se vuole un
install più leggero, esclude extra con `--no-graph`/`--no-rerank`, oppure si ferma allo scaffold con
`--no-deps`. Può anche nominare il corpus con `--corpus` e ottenere il report in JSON con `--json`.

**Why this priority**: completa la copertura (CS-5 d'epica: cloud default + opzione locale) e dà
controllo, ma non è necessario per l'MVP. Indipendente dalle altre storie.

**Independent Test**: eseguire `sertor install rag --backend local --no-rerank --json` su un target e
verificare che il `.env` contenga le chiavi `local` (Ollama, niente Azure), che `rerank` non sia tra
gli extra aggiunti, e che il report sia JSON valido.

**Acceptance Scenarios**:

1. **Given** `--backend local`, **When** si esegue l'install, **Then** il `.env` contiene
   `RAG_BACKEND=local`, `OLLAMA_HOST`, `SERTOR_CORPUS`, e l'extra `azure` NON viene aggiunto.
2. **Given** `--no-graph --no-rerank`, **When** si esegue l'install, **Then** gli extra `graph` e
   `rerank` non sono nelle dipendenze aggiunte (restano `mcp` + eventuale backend).
3. **Given** `--no-deps`, **When** si esegue l'install, **Then** vengono scritti solo gli artefatti di
   config e nessuna dipendenza viene aggiunta (nessun `uv add`).
4. **Given** `--corpus mio-corpus`, **When** si esegue l'install, **Then** `SERTOR_CORPUS=mio-corpus`
   compare nel `.env` e nell'env del server `.mcp.json`.

---

### Edge Cases

- **`uv` non installato sulla macchina**: l'install si ferma al passo dipendenze con un errore
  leggibile che indica il prerequisito, senza lasciare un `.sertor/` a metà dove evitabile (REQ-214).
- **`uv add` fallisce** (conflitto dipendenze / rete assente): fail-fast, il report indica il passo
  fallito e l'errore sottostante; gli artefatti già scritti restano (no rollback) (REQ-215/251).
- **Target inesistente o non directory** (`--target`): errore d'uso/dominio senza modificare nulla
  (REQ-203).
- **`.mcp.json` già con un server `sertor-rag`**: non duplicato né sovrascritto (esito
  `skipped`/`merged`) (REQ-232).
- **`pyproject.toml` già presente in `.sertor/`**: `uv init` non viene rieseguito; si procede con
  `uv add` (idempotente) (REQ-211).
- **Target non-Python (es. .NET)**: nessun problema — il runtime Python vive isolato in `.sertor/`,
  i sorgenti dell'host non vengono toccati (decisione di collocazione).
- **`--backend local` con `--no-...` che azzera gli extra**: resta sempre almeno `mcp` (il caso d'uso
  primario è l'assistente via MCP); il set di extra non diventa vuoto a meno di scelte esplicite.

## Requirements *(mandatory)*

### Functional Requirements

Tracciano 1:1 i REQ EARS di `requirements/sertor-cli/install-rag/requirements.md` (ID tra parentesi).

**Comando e superficie**
- **FR-001**: Il sistema MUST implementare il sottocomando `sertor install rag`, sostituendo lo stub
  che oggi solleva `CapabilityNotAvailableError` (REQ-201).
- **FR-002**: Il comando MUST accettare `--target` (default: cwd) come radice del repo ospite, e
  fermarsi con errore se il target non esiste o non è una directory, senza modificarlo (REQ-202/203).
- **FR-003**: Il comando MUST accettare `--backend {azure|local}` con default `azure` (REQ-204).
- **FR-004**: Il comando MUST accettare i flag opt-out `--no-graph`/`--no-rerank`, `--no-deps`, e le
  opzioni `--corpus` (default: nome sanitizzato della dir target) e `--json` (REQ-205/206/207/208).
- **FR-005**: Il comando MUST ritornare exit `0` (successo, incluso no-op idempotente), `1` (errore
  di dominio), `2` (errore d'uso) (REQ-209).

**Bootstrap dipendenze (runtime `.sertor/`)**
- **FR-006**: Il sistema MUST collocare l'intero runtime RAG (progetto Python, virtual env,
  indice/grafo, `.env`) sotto `<target>/.sertor/`, mai mescolato ai sorgenti dell'host (REQ-280).
- **FR-007**: Quando `.sertor/` non ha un `pyproject.toml` e `--no-deps` non è impostato, il sistema
  MUST inizializzare un progetto uv minimale (`uv init --bare`) dentro `<target>/.sertor/` prima di
  aggiungere dipendenze (REQ-211).
- **FR-008**: Il sistema MUST aggiungere `sertor-core` con gli extra derivati da backend e flag,
  dalla URL di distribuzione `git+url`, via `uv`, operando dentro `<target>/.sertor/` (REQ-212).
- **FR-009**: Di default gli extra MUST includere `mcp` + `graph` + `rerank` più l'extra del backend
  (`azure` per `--backend azure`; nulla in più per `local`); `--no-graph`/`--no-rerank` li rimuovono;
  `azure` non è mai forzato sul backend `local` (REQ-213).
- **FR-010**: Aggiungendo dipendenze il sistema MUST solo aggiungere (mai rimuovere o degradare) le
  voci di un `pyproject.toml` esistente (REQ-216).
- **FR-011**: Il sistema MUST NON avviare alcuna indicizzazione/ingestione come effetto collaterale
  (install ≠ run): `uv add` è ammesso, l'indicizzazione no (REQ-210).
- **FR-012**: Se `uv` non è disponibile, il sistema MUST fermare il passo dipendenze con errore
  leggibile sul prerequisito, evitando per quanto possibile uno stato `.sertor/` a metà (REQ-214).
- **FR-013**: Se `uv add` fallisce, il sistema MUST registrare il passo fallito e fermarsi
  (fail-fast), riportando l'errore sottostante (REQ-215).

**Scaffold `.env`**
- **FR-014**: Quando `<target>/.sertor/.env` è assente, il sistema MUST crearlo da un template con le
  chiavi richieste dal backend selezionato; per `azure`: `RAG_BACKEND=azure`,
  `SERTOR_STORE_BACKEND=local`, endpoint/key/embed-deployment Azure, `SERTOR_CORPUS`; per `local`:
  `RAG_BACKEND=local`, `OLLAMA_HOST`, `SERTOR_CORPUS` (REQ-220/223).
- **FR-015**: Il `.env` generato MUST lasciare i valori segreti (es. `*_API_KEY`) vuoti (REQ-221).
- **FR-016**: Quando il `.env` esiste già, il sistema MUST fondere solo le chiavi mancanti, senza mai
  sovrascrivere il valore di una chiave esistente (merge additivo) (REQ-222).

**Scaffold `.mcp.json`**
- **FR-017**: Il `.mcp.json` MUST essere scritto alla radice dell'host (dove i client MCP lo cercano)
  e MUST invocare il server dentro `.sertor/` (es. `uv run --directory .sertor`), con l'env del
  corpus (REQ-230/281).
- **FR-018**: Quando `.mcp.json` esiste già, il sistema MUST fondere additivamente la voce server
  `sertor-rag`, preservando gli altri server; se `sertor-rag` è già dichiarato, non duplicarlo né
  sovrascriverlo (REQ-231/232).

**Scaffold `.gitignore`**
- **FR-019**: Al completamento, il sistema MUST garantire che il `.gitignore` dell'host contenga le
  voci per gli artefatti rigenerabili (`.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env`),
  aggiungendo solo quelle mancanti e senza duplicati (REQ-240/241).

**Indicizzazione e collocazione**
- **FR-020**: L'indicizzazione RAG MUST puntare ai sorgenti dell'host (il parent di `.sertor/`)
  escludendo la cartella `.sertor/` stessa dal corpus (REQ-282).
- **FR-021**: Gli artefatti del wiki (`.claude/`, blocco rituale in `CLAUDE.md`, cartella `wiki/`)
  MUST restare alla radice dell'host e sono fuori ambito di questo comando (li gestisce
  `install wiki`); solo il runtime Python condiviso vive in `.sertor/` (REQ-283).

**Report e osservabilità**
- **FR-022**: Il sistema MUST produrre un report per-artefatto (`created`/`skipped`/`merged`/`error`)
  più un riepilogo, riusando il contratto `InstallReport` di `install wiki`, in forma umana e
  `--json`; ogni comando esterno `uv` invocato MUST essere riflesso nel report (REQ-250/252, NFR-2).
- **FR-023**: A un passo fallito il sistema MUST registrare il passo e fermarsi (fail-fast, no
  rollback), lasciando in posto gli artefatti già scritti (REQ-251).

**Distribuzione (fix `pyproject`)**
- **FR-024**: Il pacchetto `sertor` MUST risolvere la dipendenza `sertor-core` dalla distribuzione
  git del monorepo quando installato standalone (`uvx`/`pip install` da `git+url`), senza tentare
  PyPI (REQ-260/261).
- **FR-025**: Il fix MUST NON rompere la risoluzione workspace in sviluppo: il workspace uv in-repo
  continua a risolvere `sertor-core` dal sorgente locale (REQ-262).

**Trasversali**
- **FR-026**: Il sistema MUST completare sia su repo nuovo sia esistente (host-agnostico) senza
  sovrascrivere file modificati dall'utente, ed essere idempotente alla riesecuzione (REQ-270/271).

### Key Entities

- **Comando `install rag`**: il nuovo handler nel backbone CLI dell'installer; flag di input
  (`--target`, `--backend`, `--corpus`, `--no-graph`, `--no-rerank`, `--no-deps`, `--json`).
- **Piano di install RAG**: la sequenza ordinata di artefatti/azioni (init progetto, add dipendenze,
  scaffold `.env`/`.mcp.json`/`.gitignore`) — l'analogo del piano di `install wiki`, con nuovi tipi
  di artefatto (dipendenze, env-merge, mcp-merge, gitignore-append).
- **Profilo dell'ospite (RAG)**: backend scelto, set di extra risultante, nome corpus, percorsi
  (`<target>`, `<target>/.sertor/`).
- **Report di install**: esiti per artefatto + conteggi + exit code (riuso di `InstallReport`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Su un repo target senza `pyproject.toml`, **una sola** invocazione
  `sertor install rag --backend azure` lascia il progetto in uno stato in cui esistono e sono
  coerenti `<target>/.sertor/` (con dipendenze), `<target>/.sertor/.env`, `<target>/.mcp.json` e le
  voci `.gitignore` — senza passi manuali aggiuntivi (OB-1/SC-1).
- **SC-002**: In **0** esecuzioni dell'install viene creato o popolato un indice/collezione; l'unica
  attività di rete è il download dei pacchetti (OB-2/SC-2).
- **SC-003**: Due esecuzioni consecutive sullo stesso target producono lo **stesso** stato finale e
  **0** duplicati in `.env`/`.mcp.json`/`.gitignore`; la seconda passata ha solo esiti
  `skipped`/`merged` (OB-3/SC-3).
- **SC-004**: Il `.env` generato ha **tutte** le chiavi segrete (`*_API_KEY`) vuote, e `.gitignore`
  ignora `.sertor/.env` (segreti mai versionabili) (OB-4/SC-4).
- **SC-005**: `uvx --from "git+url#subdirectory=packages/sertor" sertor --help` esce `0` da ambiente
  pulito, **e** la suite del workspace in sviluppo resta verde (OB-5/SC-5).
- **SC-006**: `--backend azure` e `--backend local` generano ciascuno un `.env` con esattamente
  l'insieme di chiavi corretto per quel backend (OB-6/SC-6).
- **SC-007**: Su un target non-Python (es. con `.sln`/`.csproj`), dopo l'install i file sorgente
  dell'host risultano **immutati**; tutto il nuovo contenuto Python è confinato in `.sertor/` (+
  `.mcp.json`/`.gitignore` in radice).

## Assumptions

- **Gestore pacchetti = `uv`** (preferito dall'epica): nessun fallback `pip` nell'MVP; se `uv`
  manca, fail-fast con messaggio (DA-1 risolta).
- **Collocazione `.sertor/`**: il runtime vive isolato; i sorgenti host non vengono "pythonizzati"
  (DA-1 risolta) — risolve anche il caso target non-Python senza guardie esplicite.
- **Extra di default = tutti** (`mcp`+`graph`+`rerank`) + backend, opt-out via flag (DA-3 risolta).
- **Nessuna conferma interattiva** sul passo dipendenze: `uv add` è additivo (non rimuove nulla) →
  considerato conforme a REQ-E6; `--no-deps` è la valvola per chi vuole solo lo scaffold (DA-2).
- **Default corpus** = nome sanitizzato della cartella target quando `--corpus` è assente (DA-4).
- **Client MCP di riferimento = Claude Code** (formato `.mcp.json`); altri assistenti = FEAT-007.
- **Riuso del contratto `install wiki`**: `Artifact`/`Outcome`/`InstallReport`, fail-fast no-rollback,
  `--json`, exit 0/1/2; il subprocess `uv` è isolato dietro un confine mockabile (testabile senza
  rete, NFR-5).
- **Distribuzione interim = `git+url`** (DA-4 d'epica); il fix non preclude un futuro PyPI.
