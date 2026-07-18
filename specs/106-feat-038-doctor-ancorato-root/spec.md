# Feature Specification: `doctor` ancorato alla radice del progetto

**Feature Branch**: `106-feat-038-doctor-ancorato-root`

**Created**: 2026-07-18

**Status**: Draft

**Input**: E10-FEAT-038 (epica debito-tecnico). Requisiti: `requirements/debito-tecnico/feat-038-doctor-ancorato-root/requirements.md`. Analisi radice: `wiki/syntheses/setup-dichiara-presunzione-non-azione.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verdetto stabile da qualunque sottocartella (Priority: P1)

Un utente sta lavorando in `src/` (o in una qualunque sottocartella del progetto) e lancia
`sertor-rag doctor` per sapere se il RAG è a posto. Oggi ottiene `index: warn (index_stale)` e
`mcp: registered=False` **anche se l'indice è appena stato ricostruito ed è sano** — perché `doctor`
risolve tutto rispetto al CWD invece che alla radice del progetto. Con la feature, `doctor` risolve la
radice in modo cwd-indipendente (la stessa che usano `index`/`search`), quindi restituisce lo **stesso
verdetto vero** che darebbe dalla radice.

**Why this priority**: è il bug stesso. Senza questo, `doctor` è inaffidabile come superficie di
fiducia, e l'hook `rag-freshness` — che costruisce il suo allarme sul verdetto di `doctor` (FEAT-034) —
eredita l'inaffidabilità. È il taglio MVP: se implementi solo questo, il bug è chiuso.

**Independent Test**: si esegue `doctor --json` dalla radice e da `src/` (stesso indice, stesso istante)
e si confrontano i verdetti di tutte le aree: devono essere identici.

**Acceptance Scenarios**:

1. **Given** un progetto con indice fresco e sano, **When** l'utente esegue `sertor-rag doctor` dalla
   radice e poi da `src/`, **Then** l'area `index` è `pass` in entrambi i casi (nessun `index_stale`
   spurio dovuto al cwd).
2. **Given** lo stesso progetto, **When** l'utente esegue `doctor` da una sottocartella annidata,
   **Then** l'area `mcp` riporta `registered=True` esattamente come dalla radice (nessun flip
   True→False dovuto al cwd).
3. **Given** `CLAUDE_PROJECT_DIR` impostato alla radice del progetto, **When** `doctor` è invocato da
   una directory qualsiasi, **Then** usa quella radice (parità con gli hook FEAT-031).

### User Story 2 - Fallimento onesto fuori da un progetto (Priority: P2)

Un utente lancia `doctor` da una directory che non appartiene ad alcun progetto Sertor risolvibile.
Invece di inventare un verdetto fuorviante basato sul CWD, `doctor` dichiara a voce alta che non riesce
a individuare la radice e come rimediare.

**Why this priority**: è il complemento fail-loud (Principio XII). Impedisce che il fix «nasconda» il
caso limite dietro un verdetto silenziosamente sbagliato. Secondario perché il caso primario è l'uso
dentro un progetto installato.

**Independent Test**: si esegue `doctor` da una directory temporanea senza layout Sertor e si verifica
exit non-zero + messaggio azionabile, senza tabella di verdetti.

**Acceptance Scenarios**:

1. **Given** un CWD fuori da qualunque progetto Sertor (nessun `.sertor/`, nessun `CLAUDE_PROJECT_DIR`),
   **When** l'utente esegue `doctor`, **Then** il comando fallisce con un messaggio azionabile ed
   exit non-zero, **e non** emette un verdetto di salute basato sul CWD.

### Edge Cases

- **Sottocartella profonda** (es. `src/sertor_core/cli/`): la radice deve risolversi comunque, non
  «la prima cartella con un `.git`» che potrebbe essere un submodule.
- **Profondità del venv diversa:** runtime installato (`.sertor/.venv`) vs dogfood (`.venv`) → la radice
  è a due profondità diverse rispetto a `sys.prefix`; entrambe devono risolversi (coerente con i tre
  rami di `settings._resolve_env_path`).
- **`CLAUDE_PROJECT_DIR` impostato ma inesistente/errato:** comportamento definito (fail-loud se non è
  una radice valida, non fallback silenzioso).
- **Invocazione dalla radice (caso oggi corretto):** deve restare identica — nessuna regressione.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `doctor` MUST determinare la radice del progetto in modo deterministico e indipendente dal
  current working directory del processo.
- **FR-002**: `doctor` MUST risolvere tutte le sorgenti indicizzate e gli artefatti runtime (manifest
  dell'indice, registrazione MCP) rispetto alla radice determinata, non rispetto al CWD.
- **FR-003**: `doctor` MUST produrre, a parità di stato dell'indice, lo **stesso** verdetto per ogni area
  quando invocato da qualunque sottocartella del progetto e quando invocato dalla radice.
- **FR-004**: `doctor` MUST riusare la **stessa** semantica di risoluzione della radice già usata dal
  runtime per `.env`/`.index` (self-localization via posizione del venv / layout `.sertor/`), senza
  introdurne una nuova.
- **FR-005**: Where `CLAUDE_PROJECT_DIR` è impostato a una radice valida, `doctor` MUST usarla come radice
  del progetto (parità con gli hook, FEAT-031).
- **FR-006**: If la radice del progetto non è risolvibile, then `doctor` MUST fallire a voce alta con un
  messaggio azionabile ed exit non-zero, e MUST NOT ripiegare sul CWD per emettere un verdetto.
- **FR-007**: `doctor` MUST restare in **sola lettura** durante la risoluzione della radice: non crea,
  sposta o scrive alcun file.
- **FR-008**: La risoluzione della radice MUST NOT contenere path host-specifici hardcodati, verificabile
  da un guard test (Principio X).

### Key Entities

- **Radice del progetto:** la directory che possiede il layout runtime (`.sertor/` con config `.env` e
  indice `.index`); unica risalendo dal punto d'ancoraggio (venv / `CLAUDE_PROJECT_DIR`).
- **Verdetto d'area (`AreaReport`):** l'esito pass/warn/fail di un'area di `doctor`; deve dipendere solo
  da stato reale + radice, non dal CWD.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `doctor` invocato da **≥2** directory distinte del progetto (radice + sottocartella
  annidata) produce verdetto e stato di **ogni** area identici a parità di indice → **0** divergenze.
- **SC-002**: l'area `mcp` (`registered`) non cambia `True`→`False` per il solo cambio di CWD → **0** flip
  dovuti alla directory.
- **SC-003**: da una directory fuori da un progetto Sertor risolvibile, `doctor` fallisce con exit
  non-zero e messaggio azionabile in **100%** dei casi, senza emettere verdetti.
- **SC-004**: `doctor` scrive **0** file (invariante di sola lettura preservato).
- **SC-005**: un guard test asserisce l'assenza di path host-specifici hardcodati nella risoluzione
  (Principio X) e passa.
- **SC-006**: **0** regressioni: schema `doctor.report/1`, exit-code gate, evento `doctor` metrics-only e
  comportamento dalla radice restano invariati (suite esistente verde).

## Assumptions

- Un «progetto Sertor» è individuabile da un marker deterministico presente sul layout reale
  (`.sertor/` per il runtime installato; il dogfood condivide lo stesso layout `.sertor/` per
  config+indice — FEAT-013).
- La radice è **unica** risalendo dal punto d'ancoraggio; non esistono due layout `.sertor/` annidati
  nello stesso albero.
- `doctor` è un vehicle: la correzione vive nel core dietro il CLI (Principio XI), non in un consumatore.
- `CLAUDE_PROJECT_DIR`, quando presente, è la fonte autorevole della radice (semantica ereditata dagli hook).
- Il canale esplicito `--root` **non** fa parte di questo taglio (rinviato, Could — vedi requirements §10).
