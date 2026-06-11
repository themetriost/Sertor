# Requisiti — CLI: installer `sertor install wiki`
<!-- Deriva da: FEAT-002 (Installazione selettiva delle capacità del core su un repo target) -->
<!-- STATO: elicitazione completata 2026-06-11; domande aperte DI-1..DI-5 RISOLTE con l'utente lo stesso giorno (vedi §10) -->
<!-- Revisione 2026-06-11: primo taglio — backbone `sertor` + sottocomando `sertor install wiki`;
     `sertor install rag` e `sertor install governance` citati come futuri (fuori ambito). -->

> **Nota di scope (DA-8 epica §9).** Il comando `sertor` è riservato all'installazione/setup
> dell'ospite con verbo esplicito: `sertor install <capacità>`. L'**esecuzione** vive nei
> console-script del core (`sertor-rag`, `sertor-wiki-tools`), già consegnati su master.
> Questa feature copre il **backbone del comando `sertor`** e il **primo sottocomando `sertor
> install wiki`**; i sottocomandi `install rag` e `install governance` sono tagli futuri.

---

## 1. Contesto e problema (perché)

Le capacità del core Sertor (indicizzazione, LLM Wiki, governance) sono oggi utilizzabili solo
sul repo Sertor stesso: i console-script `sertor-rag` e `sertor-wiki-tools` esistono, ma gli
**artefatti di configurazione** che li abilitano su un progetto qualunque — skill wiki, agente
wiki-curator, hook di sessione, rituale di step, `wiki.config.toml`, struttura wiki — devono
essere **copiati e adattati a mano**. Non esiste un comando che li installi sull'ospite in modo
riproducibile, idempotente e host-agnostico.

La mancanza di un installer crea tre problemi concreti:

1. **Proliferazione di copie accoppiante:** ogni progetto che vuole il wiki copia `.claude/` dal
   repo Sertor, con riferimenti interni a percorsi e dominio di Sertor (violazione del Principio X
   della costituzione).
2. **Non idempotenza:** rieseguire il setup sovrascrive silenziosamente o duplica artefatti utente
   già presenti (violazione del Principio VI e di REQ-E6 dell'epica).
3. **Installazione ≠ esecuzione non garantita:** senza un punto d'ingresso esplicito, il setup può
   avviare operazioni costose (indicizzazione LLM) come effetto collaterale (violazione di REQ-E2).

*Ancora al repo (in `master`):*
- Artefatti da installare: `.claude/skills/wiki-author/` (SKILL.md + wiki-playbook.md + ops/*.md),
  `.claude/commands/wiki.md`, `.claude/agents/wiki-curator.md`,
  `.claude/hooks/wiki-pending-check.ps1`, `.claude/settings.json` (hook SessionStart/Stop/SessionEnd).
- Nucleo deterministico già installato con il pacchetto: `src/sertor_core/wiki_tools/` con
  `structure.init_structure()` (idempotente, `SC-006` documentato in `structure.py:6`).
- Modello di `wiki.config.toml` reale: radice del repo Sertor (`wiki.config.toml`).
- Sezione rituale di step e istruzioni wiki: `CLAUDE.md` (sezione *Rituale di step* e sezione
  *Wiki & documentazione*).

**Come viaggiano gli artefatti non-Python (DI-5, risolta 2026-06-11):** le skill, l'agente, gli
hook e il comando `/wiki` **non fanno parte di un modulo Python**: oggi vivono in `.claude/` del
repo Sertor. Decisione utente: l'installer li **scarica on-demand dal repository canonico**,
**pinnati al ref corrispondente alla versione del pacchetto installato** (riproducibilità:
artefatti sempre coerenti col codice); l'opzione **`--source <path>`** copia invece da un
clone/cartella locale, coprendo offline e sviluppo (REQ-115/116). Il *cosa* resta invariato: dopo
`sertor install wiki` quegli artefatti sono presenti e funzionanti sull'ospite, privi di
riferimenti a Sertor-il-progetto.

---

## 2. Obiettivi e criteri di successo

| ID | Criterio (misurabile, tech-agnostico) | Collegamento epica |
|----|----------------------------------------|--------------------|
| LSC-1 | `sertor install wiki` su un repo vuoto crea tutti gli artefatti wiki previsti senza errori e senza richiedere passi manuali aggiuntivi. | CS-1, FEAT-002 |
| LSC-2 | `sertor install wiki` su un repo che ha già un `CLAUDE.md`, un `wiki/`, o un `wiki.config.toml` **non sovrascrive** alcun contenuto utente preesistente; il comando termina con successo e riporta quali artefatti sono stati saltati. | CS-4, REQ-E6 |
| LSC-3 | Rieseguire `sertor install wiki` sullo stesso repo produce lo stesso stato degli artefatti; nessuna duplicazione né errore (idempotenza). | Principio VI |
| LSC-4 | Nessun artefatto installato contiene riferimenti a percorsi, domini o strutture specifiche del repo Sertor; ogni riferimento all'ospite proviene dalla configurazione (`wiki.config.toml`). | Principio X |
| LSC-5 | L'installazione non avvia alcuna operazione di indicizzazione né chiamata LLM; l'unico accesso di rete ammesso è il **download degli artefatti** (assente con `--source`). | CS-2, REQ-E2 |
| LSC-6 | Il test di accettazione dell'installer (install su un repo vuoto, re-run, install su repo con artefatti preesistenti) è eseguibile senza rete, senza LLM e senza cloud **usando il fallback `--source <path>`** (rev. DI-5c). | Principio V |
| LSC-7 | `sertor --help` e `sertor install --help` mostrano i sottocomandi disponibili e descrivono gli argomenti; sottocomandi non ancora implementati (`rag`, `governance`) sono elencati come pianificati ma non invocabili. | CS-1 |

---

## 3. Stakeholder e attori

| Attore | Ruolo |
|--------|-------|
| **Owner/maintainer** | Installa le capacità wiki su un repo target; è il principale utente del comando. |
| **Agente LLM (es. Claude Code)** | Potenziale consumatore automatizzato: deve poter interpretare exit code e output dell'installer. |
| **Repository target (ospite)** | Oggetto su cui l'installer opera; può essere nuovo o preesistente, con o senza artefatti Sertor. |
| **`sertor-core` (dipendenza a monte)** | Fornisce `sertor-wiki-tools` e le funzioni deterministiche (`structure.init_structure`) già presenti nel pacchetto installato. |
| **File system dell'ospite** | Destinazione fisica degli artefatti; il suo stato pre-esistente determina il comportamento dell'installer (skip/create). |

---

## 4. Ambito

### In ambito

- **Backbone del comando `sertor`**: entry-point installabile come console-script del pacchetto `sertor`
  (distinto da `sertor-core`), con struttura di sottocomandi estensibile; guida all'uso (`--help`).
- **Sottocomando `sertor install wiki`**: installa sull'ospite l'intero set di artefatti necessari per
  attivare il sistema wiki LLM:
  - **Skill wiki-author**: SKILL.md, wiki-playbook.md, tutti i moduli `ops/*.md`.
  - **Comando `/wiki`** (`.claude/commands/wiki.md`).
  - **Agente wiki-curator** (`.claude/agents/wiki-curator.md`).
  - **Hook di sessione** (`.claude/hooks/wiki-pending-check.ps1`).
  - **Configurazione hook** (`settings.json` — voci SessionStart/Stop/SessionEnd): scrittura
    additiva tramite marker, senza sovrascrivere configurazioni utente preesistenti.
  - **`wiki.config.toml`**: generato con valori di default derivati dall'ospite (nome,
    source_dirs ragionevoli, lingua, ecc.); mai sovrascrivere se già presente.
  - **Sezione rituale di step** nel `CLAUDE.md` dell'ospite: inserita tramite marker, in modo
    additivo; il `CLAUDE.md` esistente non viene toccato fuori dal blocco delimitato.
  - **Struttura wiki** (`structure init` del nucleo deterministico): crea cartelle di tassonomia,
    `index.md` e file di log; idempotente per costruzione (già garantito da `init_structure`
    in `structure.py:30-72`).
- **Non-distruttività per ciascun artefatto**: definizione precisa del comportamento in caso di
  artefatto preesistente (vedi §5, gruppo C).
- **Report dell'installazione**: riepilogo di artefatti creati, saltati (già esistenti) e di
  eventuali conflitti rilevati.
- **Idempotenza**: rieseguire il comando sullo stesso ospite produce lo stesso stato finale.
- **Testabilità senza rete/LLM**: l'intera operazione è su file; nessun provider esterno è richiesto.
- **Predisposizione struttura comandi `install`**: i sottocomandi `install rag` e `install
  governance` sono dichiarati come pianificati nell'help ma non implementati in questo taglio.

### Fuori ambito

- **`sertor install rag`**: configurazione del backend RAG, wizard LLM/vector-store sull'ospite.
  Rinviato (FEAT-002, taglio futuro).
- **`sertor install governance`**: skill SpecKit, agenti di fase, skill di gestione requisiti.
  Rinviato (FEAT-005).
- **Distribuzione pubblica (PyPI, git+url)**: packaging e hardening della supply-chain (FEAT-006).
  La feature presuppone che il pacchetto `sertor` sia disponibile (anche in editable install).
- **Wizard di configurazione interattivo**: la raccolta di parametri di configurazione LLM/RAG
  (provider, chiavi, endpoint) è FEAT-003; questa feature usa valori di default o parametri
  passati a riga di comando.
- **Esecuzione delle capacità installate**: l'installer non avvia indicizzazione, chiamate LLM o
  accessi di rete (REQ-E2). L'esecuzione è delegata a `sertor-rag` e `sertor-wiki-tools`.
- **Aggiornamento degli artefatti già installati** (upgrade): gestito in un taglio futuro; questo
  taglio installa o salta, non aggiorna.
- **Disinstallazione/rimozione degli artefatti**: fuori ambito.
- **GUI/web.**

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Backbone del comando `sertor`

**REQ-100 (Ubiquitous)** *The installer shall expose a single command-line entry-point named
`sertor` (installed as a console-script of the `sertor` package) that dispatches to the
`install` subcommand and to future subcommands (at minimum `install rag` and `install governance`
as declared-but-unimplemented stubs).*
> Il pacchetto `sertor` è distinto da `sertor-core`; il comando `sertor` è il veicolo
> di setup sull'ospite (DA-8 epica §9). La struttura a sottocomandi è estensibile senza
> rompere l'interfaccia esistente.

**REQ-101 (Ubiquitous)** *The `sertor` entry-point shall provide usage/help text for itself
and for each subcommand, describing available capabilities and their arguments.*

**REQ-102 (Unwanted behaviour)** *If an unknown subcommand or a required argument is missing,
then the installer shall print a readable error and exit with a non-zero status, without
performing any partial operation.*

**REQ-103 (Ubiquitous)** *The installer shall return exit code 0 on successful completion and
a non-zero exit code on any error, to support scripting and automation.*

**REQ-104 (Unwanted behaviour)** *If a subcommand is declared as planned but not yet
implemented (e.g. `install rag`, `install governance`), then the installer shall print a
human-readable "not yet available" message and exit non-zero, without performing any
partial operation.*

### Gruppo B — Sottocomando `sertor install wiki` — installazione complessiva

**REQ-110 (Event-driven)** *When the user runs `sertor install wiki [--target <path>]`, the
installer shall install all wiki-enabling artefacts on the target repository rooted at
`<path>` (defaulting to the current working directory) and shall print a report listing
each artefact as created, skipped (already present), or in conflict.*

**REQ-111 (Ubiquitous)** *The installer shall not invoke any LLM, embeddings provider, or
indexing operation during installation; its only permitted network access is fetching the
artefacts to install (REQ-115), and no network access shall occur when `--source` is used
(REQ-116). All writes are file-system operations on the target repository.*
> Fissa il confine install ≠ run (REQ-E2 epica) al livello di questa feature; riscritto con la
> risoluzione di DI-5 (2026-06-11): la rete serve SOLO al trasporto degli artefatti.

**REQ-115 (Ubiquitous)** *The installer shall obtain the non-Python artefacts (skills, command,
agent, hooks) by downloading them from the canonical Sertor repository URL, pinned to the ref
(tag/commit) corresponding to the installed `sertor` package version, so that installed artefacts
are always consistent with the installed code.*
> DI-5 + DI-5b risolte (2026-06-11): download on-demand, pinning alla versione installata
> (riproducibilità; un install oggi e uno fra un mese sulla stessa versione producono gli stessi
> artefatti). L'URL canonico e il meccanismo di fetch sono decisione di design.

**REQ-116 (Optional feature)** *Where the user passes a `--source <path>` option, the installer
shall copy the artefacts from the given local directory (e.g. a local clone of Sertor) instead of
downloading them, enabling fully offline installation and development workflows.*
> DI-5c risolta (2026-06-11): fallback locale che copre offline e sviluppo; è la base di LSC-6.

**REQ-117 (Unwanted behaviour)** *If the artefact download fails (network unavailable, ref not
found), then the installer shall print a readable error suggesting the `--source` fallback and
exit non-zero, leaving any already-written artefacts reported per REQ-125.*

**REQ-112 (Ubiquitous)** *The installer shall install the wiki skill artefacts
(`.claude/skills/wiki-author/SKILL.md`, `wiki-playbook.md`, and all `ops/*.md` modules),
the `/wiki` command (`.claude/commands/wiki.md`), the `wiki-curator` agent
(`.claude/agents/wiki-curator.md`), and the session hook
(`.claude/hooks/wiki-pending-check.ps1`) into the target repository.*

**REQ-113 (Ubiquitous)** *All artefacts installed by `sertor install wiki` shall be free of
references to the Sertor project's own paths, domain names, or repository-specific
assumptions; any host-specific value shall derive from the target repository's configuration.*
> Principio X della costituzione: gli artefatti installati devono essere host-agnostici.
> Questa è la distinzione tra "copiare Sertor" e "installare una capacità portabile".

**REQ-114 (Ubiquitous)** *The installer shall invoke the core's `structure init` operation
(via `sertor-wiki-tools structure init`) after writing `wiki.config.toml`, to create the
wiki directory structure (taxonomy folders, `index.md`, log file) on the target repository.*
> `init_structure` è già idempotente e non-distruttivo per costruzione
> (`src/sertor_core/wiki_tools/structure.py:30-72`): se la struttura esiste, salta.

### Gruppo C — Non-distruttività per artefatto

**REQ-120 (Event-driven)** *When `sertor install wiki` is run and some wiki-author skill files
already exist on the target, the installer shall check **file by file**: existing files are left
untouched and reported as skipped, missing files are created — so that partial installations are
repaired without overwriting user content.*
> DI-1 risolta (2026-06-11): granulare, coerente con `init_structure`; il report distingue
> creati da saltati.

**REQ-121 (Event-driven)** *When `sertor install wiki` is run and a `wiki.config.toml` file
already exists on the target, the installer shall not overwrite it and shall report it as
skipped.*

**REQ-122 (Event-driven)** *When `sertor install wiki` is run and a `CLAUDE.md` file already
exists on the target, the installer shall append the step-ritual section inside a dedicated
delimited block (using start/end markers); it shall not modify any content outside that block.*
> La scrittura additiva tramite marker garantisce la non-distruttività su CLAUDE.md preesistenti
> (REQ-E6 epica) e l'idempotenza (rieseguire il comando non duplica il blocco se già presente).

**REQ-123 (Event-driven)** *When `sertor install wiki` is run and a `.claude/settings.json` file
already exists on the target, the installer shall merge the required hook entries (SessionStart,
Stop, SessionEnd) into the existing configuration in an additive manner, without removing or
overwriting existing entries.*
> DI-2 risolta (2026-06-11): **merge con deduplicazione per `command`** — una voce hook si
> aggiunge solo se nessuna voce con lo stesso `command` è già presente; idempotente, preserva gli
> hook utente. Il criterio esatto di uguaglianza è dettaglio di design.

**REQ-124 (Event-driven)** *When `sertor install wiki` is run and a `wiki/` directory already
exists on the target, the installer shall invoke `structure init` (which is idempotent by
construction) and report existing directories and files as skipped.*

**REQ-125 (Unwanted behaviour)** *If any artefact installation step fails (e.g. due to
insufficient permissions), then the installer shall report the failure with the artefact path
and reason, and shall not leave a partial set of artefacts in an inconsistent state.*
> DI-3 risolta (2026-06-11): **fail-fast senza rollback** — l'installer si ferma al primo errore
> e il report elenca esattamente cosa è stato scritto e cosa manca; gli artefatti già scritti
> restano (nessuna cancellazione automatica sull'ospite) e il re-run idempotente completa i buchi.

### Gruppo D — Configurazione dell'ospite

**REQ-130 (Event-driven)** *When `wiki.config.toml` does not already exist on the target,
`sertor install wiki` shall generate it with host-specific defaults (at minimum: `root`,
`source_dirs` inferred from the target repository layout, `language`, taxonomy sections, and
`[roles]` entries referencing the installed agents by their installed names).*
> DI-4 risolta (2026-06-11): **euristica su cartelle standard riconosciute** (es. `src/`, `lib/`,
> `docs/`, `tests/`, `app/`: incluse quelle presenti; nessuna → `["."]`) con override esplicito
> via `--source-dirs` (REQ-133). La lista esatta delle cartelle riconosciute è decisione di design
> (documentata, NFR-I-07).

**REQ-131 (Ubiquitous)** *The installer shall not write secret values (API keys, credentials,
endpoints) to any file on the target repository.*
> Rafforza REQ-E5 dell'epica al livello di questa feature.

**REQ-132 (Optional feature)** *Where the user passes a `--language <lang>` option, the
installer shall use that value as the `language` field in the generated `wiki.config.toml`.*

**REQ-133 (Optional feature)** *Where the user passes a `--source-dirs <dir1,dir2,...>` option,
the installer shall use those directories as the `source_dirs` list in the generated
`wiki.config.toml` instead of the inferred defaults.*

### Gruppo E — Trasversali (install ≠ run, idempotenza, agnosticità)

**REQ-140 (Unwanted behaviour)** *If the installer is executed, imported, or installed as a
package, then it shall not automatically start any indexing, LLM call, or RAG operation;
every such operation requires an explicit subsequent command.*
> Fissa il principio install ≠ run (REQ-E2 epica) per questa feature.

**REQ-141 (Ubiquitous)** *The installer shall produce the same end state of artefacts on a
given target repository regardless of how many times it is run; repeated invocations shall
neither create duplicates nor raise errors for already-present artefacts (idempotency).*

**REQ-142 (Ubiquitous)** *The installer shall operate on any target repository provided as a
path, without hard-coded assumptions about its name, language distribution, existing structure,
or size.*

**REQ-143 (Ubiquitous)** *The installer shall report a summary of the installation outcome
(number of artefacts created, skipped, and any conflicts) on stdout, and shall exit with
code 0 if no artefact produced an error.*

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| NFR-I-01 | **Testabilità** | Ogni sottocomando è testabile in automatico su un repository temporaneo (fixture), senza cloud, senza rete e senza LLM attivo; gli esiti (artefatti creati/saltati, exit code, output) sono verificabili tramite asserzioni su file system. |
| NFR-I-02 | **Idempotenza / non-distruttività** | Nessuna invocazione dell'installer, qualunque sia lo stato del repo target, produce perdita di dati utente, duplicazione di artefatti o stato inconsistente (Principio VI). |
| NFR-I-03 | **Host-agnosticità** | Nessun artefatto installato contiene percorsi, variabili di dominio o assunzioni specifiche del repo Sertor; ogni specificità dell'ospite deriva dalla configurazione (Principio X). |
| NFR-I-04 | **Portabilità** | L'installer funziona su Linux e Windows senza modifiche. |
| NFR-I-05 | **Leggibilità degli errori** | I messaggi di errore sono comprensibili e indicano l'artefatto problematico, il percorso target e la causa; nessuno stack trace grezzo all'utente (salvo verbosità elevata). |
| NFR-I-06 | **Dipendenza verso l'interno** | Il comando `sertor` è un layer sottile: dipende da `sertor-core` per le operazioni deterministiche (`structure init`) e non duplica alcuna logica del core (Principio I). |
| NFR-I-07 | **Configurabilità centralizzata** | I default generati per `wiki.config.toml` derivano da un insieme documentato di euristiche sul layout del target; non sono hard-coded nel codice dell'installer (Principio VIII). |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **V-1**: Il comando `sertor` dipende da `sertor-core` (almeno `sertor-wiki-tools` disponibile);
  non funziona su un ambiente privo del core installato.
- **V-2**: Nessun segreto su file versionati (REQ-E5 epica; REQ-131).
- **V-3**: `install ≠ run` (REQ-E2 epica; REQ-140): nessuna operazione automatica all'installazione.
- **V-4**: Python ≥ 3.11 (vincolo d'epica).
- **V-5** *(rev. DI-5)*: Gli artefatti non-Python arrivano per **download dal repository canonico,
  pinnato al ref della versione installata** (REQ-115), con fallback locale `--source <path>`
  (REQ-116). URL canonico e meccanica di fetch sono dettaglio di design.

### Assunzioni

- **A-1**: Il pacchetto `sertor` è installato con `uv`/`pip` (anche editable) prima di invocare il
  comando; la distribuzione pubblica (PyPI/git+url) è fuori ambito (FEAT-006) ma il design non deve
  precluderla.
- **A-2**: `sertor-core` (e quindi `sertor-wiki-tools`) è installato come dipendenza del pacchetto
  `sertor` o è già disponibile nell'ambiente Python attivo.
- **A-3**: Il filesystem del repo target è accessibile in lettura/scrittura dall'utente che esegue
  il comando; l'installer non gestisce escalation di privilegi.
- **A-4**: La generazione di `wiki.config.toml` con default dall'ospite usa euristiche sul layout
  del filesystem (es. presenza di `src/`, `docs/`, `tests/`): se l'ospite ha un layout insolito,
  l'utente può passare `--source-dirs` (REQ-133) o modificare il file generato a mano.
- **A-5**: Il `CLAUDE.md` dell'ospite, se presente, è un file di testo UTF-8 in cui è sicuro
  inserire un blocco delimitato da marker (REQ-122). Il formato del blocco (marker, contenuto) è
  una decisione di design.

### Dipendenze

- **D-1**: `sertor-core` in `master` — in particolare `sertor_core.wiki_tools.structure.init_structure`
  (già idempotente e non-distruttivo, `structure.py:30-72`) e la CLI `sertor-wiki-tools structure init`.
- **D-2**: Artefatti sorgente da installare (oggi in `.claude/` del repo Sertor):
  `.claude/skills/wiki-author/` (10 file), `.claude/commands/wiki.md`,
  `.claude/agents/wiki-curator.md`, `.claude/hooks/wiki-pending-check.ps1`.
- **D-3**: Modello di `wiki.config.toml` (oggi: `wiki.config.toml` a radice del repo Sertor) come
  riferimento per i campi e le sezioni da generare sull'ospite.
- **D-4**: Feature `esecuzione` (già consegnata, PR #21): `sertor-rag` e `sertor-wiki-tools`
  sono i comandi che l'utente esegue **dopo** l'installazione; l'installer ne presuppone la
  disponibilità nel pacchetto core ma non li invoca.

---

## 8. Rischi

| ID | Rischio | Prob. | Impatto | Mitigazione |
|----|---------|-------|---------|-------------|
| R-I1 | **Sovrascrittura silenziosa di artefatti utente** (viola REQ-E6 / CS-4): l'installer sovrascrive CLAUDE.md, wiki.config.toml o settings.json senza avvisare. | Media | Alto | REQ-120..124: comportamento esplicito per ogni artefatto; test dedicati su repo con artefatti preesistenti. |
| R-I2 | **Artefatti Sertor-coupled** (viola Principio X): skill/agenti installati contengono percorsi o nomi di dominio di Sertor hard-coded, rendendoli inutili su un altro ospite. | Alta | Alto | REQ-113 + NFR-I-03: test di accettazione su un repo terzo senza conoscenza di Sertor. |
| R-I3 | **Stato parziale non segnalato** (viola REQ-125): un'installazione interrotta lascia l'ospite in uno stato inconsistente senza che l'utente lo sappia. | Bassa | Medio | REQ-125 + NFR-I-02: fail-fast con report esplicito; chiarire in design se serve rollback. |
| R-I4 | **Conflitto settings.json**: la strategia di merge delle voci hook in un `settings.json` preesistente produce duplicati o rompe configurazioni utente. | Media | Medio | REQ-123 + DA CHIARIRE DI-2: decidere la strategia di merge prima del design. |
| R-I5 | **Trasporto degli artefatti non-Python**: il download on-demand introduce dipendenza dalla rete e dal repository remoto al momento dell'install. | Media | Medio | DI-5 risolta: download **pinnato al ref della versione installata** (REQ-115, riproducibile) + fallback offline `--source` (REQ-116) + errore leggibile con suggerimento del fallback (REQ-117). |
| R-I6 | **Avvio non voluto** (viola REQ-E2): l'installer invoca `sertor-wiki-tools structure init` e questo potrebbe essere considerato "esecuzione" da un lettore frettoloso. | Bassa | Basso | REQ-111 chiarisce che `structure init` è un'operazione su file (crea directory/file seed), non un'indicizzazione o chiamata LLM: è parte dell'install per costruzione. |

---

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-100..104 (backbone), REQ-110..117 (install wiki + trasporto artefatti), REQ-120..125 (non-distruttività), REQ-130, REQ-131, REQ-140..143 (trasversali) | Ciclo minimo funzionante: il comando esiste, scarica/copia gli artefatti in modo riproducibile, installa tutto il set wiki, non distrugge nulla, è idempotente, non avvia esecuzioni. REQ-116 (`--source`) è Must perché è la base della testabilità offline (LSC-6). |
| **Should** | REQ-132, REQ-133 (opzioni `--language`, `--source-dirs`) | Migliorano l'usabilità del primo taglio senza essere bloccanti; il default inferito può bastare per il dogfooding. |
| **Could** | Verbosità estesa (`--verbose`), output JSON (`--json`) del report di install | Utili per consumatori automatizzati (agenti LLM); non bloccanti per il primo uso umano. |
| **Won't (questo taglio)** | `sertor install rag`, `sertor install governance`, upgrade degli artefatti, disinstallazione, wizard interattivo di config LLM | Tagli futuri (FEAT-002 residuo, FEAT-005); la struttura comandi li dichiara ma non li implementa. |

---

## 10. Domande aperte (RISOLTE il 2026-06-11)

Tutte le decisioni sono state chiuse con l'utente lo stesso giorno dell'elicitazione e codificate
nei requisiti sopra. Sintesi delle risoluzioni:

| # | Tema | Decisione | Codificata in |
|---|------|-----------|---------------|
| DI-5 | Trasporto artefatti non-Python | **Download on-demand dal repo canonico** (scartati package-data e path-locale-come-unico-meccanismo) | REQ-115, REQ-111 |
| DI-5b | Versione scaricata | **Ref pinnato alla versione del pacchetto installato** (riproducibilità) | REQ-115 |
| DI-5c | Offline | **Fallback `--source <path>`** (clone/cartella locale): copre offline e sviluppo; base della testabilità | REQ-116, REQ-117, LSC-5/6 |
| DI-1 | Skip artefatti esistenti | **Granulare, file-per-file** (ripara installazioni parziali, mai overwrite) | REQ-120 |
| DI-2 | Merge `settings.json` | **Merge con deduplicazione per `command`** (idempotente, preserva hook utente) | REQ-123 |
| DI-3 | Fallimento parziale | **Fail-fast + report, senza rollback** (nessuna cancellazione automatica; re-run completa i buchi) | REQ-125 |
| DI-4 | `source_dirs` inferito | **Euristica su cartelle standard** + override `--source-dirs` | REQ-130, REQ-133 |

Il dettaglio originale delle opzioni valutate resta sotto, per tracciabilità.

---

**DI-5 — Meccanismo di trasporto degli artefatti non-Python** (BLOCCANTE per il design)

*Contesto:* Le skill wiki-author (10 file `.md`), il comando `/wiki`, l'agente wiki-curator,
l'hook `.ps1` **non fanno parte di un modulo Python**: oggi vivono in `.claude/` del repo Sertor.
Per installarli sull'ospite tramite `sertor install wiki`, il pacchetto `sertor` deve averli
disponibili a runtime — ma come?

*Opzioni principali:*
- **Package-data nel wheel**: i file `.md` e `.ps1` vengono inclusi nel pacchetto Python come
  `package_data` (in `pyproject.toml`); `importlib.resources` o `pathlib` li localizza a runtime.
  Vantaggio: un solo `pip install sertor` basta. Svantaggio: i file `.md` diventano "statici"
  dentro il wheel (aggiornabili solo con una nuova release).
- **Directory `templates/` bundled** nel pacchetto Python (variante del precedente): stessa
  meccanica, ma con nomenclatura esplicita.
- **Download on-demand da URL** (es. release su GitHub): l'installer scarica i file al momento
  di `sertor install wiki`. Vantaggio: sempre aggiornati. Svantaggio: richiede rete (violazione
  di LSC-6 e NFR-I-04 se la rete non è disponibile); introduce una dipendenza esterna
  alla distribuzione.
- **Repo git clonato localmente** (per sviluppo/uso interno): un path fisso; fragile e non
  portabile.

*Raccomandazione (storica):* package-data nel wheel. **Decisione utente (2026-06-11): diversa
dalla raccomandazione — download on-demand da URL**, mitigata con pinning al ref della versione
installata (DI-5b → REQ-115) e fallback offline `--source` (DI-5c → REQ-116): artefatti
aggiornabili senza re-release del pacchetto, riproducibilità e offline preservati.

---

**DI-1 — Granularità dello skip degli artefatti già presenti** (impatta REQ-120, R-I1)

*Contesto:* REQ-120 specifica che se `.claude/skills/wiki-author/` esiste, i file della skill
vengono saltati. La domanda è: l'installer salta l'**intera directory** (tutto o niente) o
controlla **file per file** (salta solo i file già presenti, installa quelli mancanti)?

*Opzioni:*
- **Blocco (tutto-o-niente):** se la directory esiste, nessun file viene scritto. Semplice,
  prevedibile, ma non gestisce installazioni parziali pregresse.
- **Granulare (file per file):** ogni file viene controllato singolarmente; solo i file mancanti
  vengono creati. Gestisce meglio installazioni parziali, ma la logica è più complessa.

*Raccomandazione:* granulare (file per file), coerente con il comportamento di `init_structure`
(già granulare per directory/file) e con il principio di idempotenza. Il report deve distinguere
i file creati da quelli saltati.

---

**DI-2 — Strategia di merge di `settings.json`** (impatta REQ-123, R-I4)

*Contesto:* Il `settings.json` dell'ospite potrebbe già contenere voci di hook proprie dell'utente.
L'installer deve aggiungere le voci SessionStart/Stop/SessionEnd senza rompere le esistenti.

*Opzioni:*
- **Append nell'array:** le voci Sertor vengono aggiunte in coda all'array `hooks.<evento>`.
  Semplice, ma può produrre duplicati se `sertor install wiki` viene eseguito due volte.
- **Merge con deduplicazione per command:** prima di aggiungere, l'installer verifica se una
  voce con lo stesso `command` è già presente; in caso positivo, la salta.
- **Blocco delimitato da marker (come CLAUDE.md):** inserisce un blocco JSON identificato da
  marker all'interno del file. Fragile per JSON (il formato non ammette commenti/marker nativi).

*Raccomandazione:* merge con deduplicazione per `command` (seconda opzione): garantisce
idempotenza, è reversibile manualmente, non richiede marker nel JSON. Il design deve
specificare il criterio di uguaglianza ("stessa stringa `command`").

---

**DI-3 — Comportamento in caso di installazione parziale** (impatta REQ-125)

*Contesto:* REQ-125 dice che se un passo fallisce, l'installer non deve lasciare uno stato
inconsistente. Questo può significare due cose diverse in fase di design:
- **Fail-fast senza rollback**: l'installer si ferma al primo errore, riporta cosa è stato
  fatto e cosa no, e chiede all'utente di risolvere. Gli artefatti già scritti rimangono.
- **Rollback atomico**: se qualcosa fallisce, tutti gli artefatti scritti nel run corrente
  vengono rimossi, riportando il repo allo stato pre-install.

*Raccomandazione:* fail-fast senza rollback (prima opzione), più semplice e meno pericoloso
(il rollback potrebbe rimuovere file utente in edge case); il report esplicito dell'errore e
dello stato parziale è sufficiente per permettere all'utente di ripartire. I requisiti non
prescrivono il rollback.

---

**DI-4 — Euristica per `source_dirs` in `wiki.config.toml`** (impatta REQ-130)

*Contesto:* Quando `wiki.config.toml` non esiste, l'installer lo genera con valori di default
inferiti dall'ospite. Il campo `source_dirs` (cartelle sorgente da monitorare per il wiki) deve
essere ragionevole senza conoscere a priori il progetto.

*Opzioni per l'inferenza:*
- **Cartelle standard riconosciute**: l'installer controlla la presenza di cartelle comuni
  (`src/`, `docs/`, `tests/`, `lib/`, `app/`) e include quelle che esistono. Se nessuna è
  presente, usa `["."]` (radice).
- **Input obbligatorio**: l'installer richiede sempre `--source-dirs` e fallisce senza.
  Massima precisione, ma peggiore usabilità (non self-service per il primo taglio).
- **Usa radice come default**: sempre `source_dirs = ["."]`; l'utente corregge dopo.
  Semplice ma rumoroso (indicizza tutto).

*Raccomandazione:* cartelle standard riconosciute (prima opzione) come default, con
`--source-dirs` per override esplicito (REQ-133). Definire la lista esatta delle cartelle
riconosciute è una decisione di design.
