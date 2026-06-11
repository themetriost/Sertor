# Feature Specification: Installer `sertor` — backbone + `sertor install wiki`

**Feature Branch**: `012-sertor-install-wiki`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Installer `sertor`: backbone del comando di installazione (console-script, sottocomandi estensibili, help, exit code) + primo sottocomando `sertor install wiki` che installa sull'ospite l'intero sistema-wiki (skill wiki-author, /wiki, agente wiki-curator, hook di sessione con merge in settings.json, step-ritual nel CLAUDE.md via marker, wiki.config.toml con default inferiti, structure init). Artefatti come package-data nel wheel (DI-5). Vincoli: install ≠ run, non-distruttività per artefatto, idempotenza, fail-fast + report, artefatti host-agnostici. Fonte EARS: requirements/sertor-cli/installer/requirements.md (25 REQ + 7 NFR, DI-1..DI-5 risolte)."

> **Contesto di prodotto.** Per la decisione DA-8 (epica `sertor-cli`) il comando `sertor` è
> riservato all'**installazione** delle capacità sull'ospite (`sertor install <capacità>`);
> l'esecuzione vive nei console-script del core (`sertor-rag`, `sertor-wiki-tools`, già consegnati).
> Oggi portare il sistema-wiki su un altro repo richiede copia manuale da `.claude/` di Sertor, con
> tre problemi: copie accoppiate al dominio Sertor (viola il Principio X), nessuna idempotenza,
> nessuna garanzia install≠run. Requisiti EARS a monte:
> `requirements/sertor-cli/installer/requirements.md` (DI-1..DI-5 tutte risolte; DI-5 finale:
> artefatti come **package-data nel wheel**).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Installare il sistema-wiki su un repo nuovo (Priority: P1)

Un maintainer ha un progetto senza alcun artefatto Sertor e vuole dotarlo del sistema-wiki con un
solo comando: `sertor install wiki`. Al termine il repo ha tutto il necessario — skill wiki-author
(playbook + moduli operativi), comando `/wiki`, agente wiki-curator, hook di sessione registrati,
sezione step-ritual nel `CLAUDE.md`, `wiki.config.toml` con default sensati, struttura wiki
(cartelle, indice, log) — e un report che elenca ogni artefatto creato. Nessuna indicizzazione,
chiamata LLM o accesso di rete viene avviata.

**Why this priority**: è il valore fondante della feature (portare la capacità su qualunque
progetto, CS-1/CS-3 dell'epica) e il percorso più semplice (nessun conflitto da gestire). Da solo
costituisce un MVP dimostrabile.

**Independent Test**: su un repository temporaneo vuoto, eseguire `sertor install wiki` e
verificare: exit 0, presenza di tutti gli artefatti attesi, report completo, nessun processo di
rete/LLM avviato, artefatti privi di riferimenti a Sertor-il-progetto.

**Acceptance Scenarios**:

1. **Given** un repo target privo di artefatti Sertor, **When** l'utente esegue
   `sertor install wiki`, **Then** vengono creati: skill wiki-author completa (SKILL.md,
   wiki-playbook.md, moduli ops), comando `/wiki`, agente wiki-curator, hook di sessione,
   voci hook in `.claude/settings.json`, blocco step-ritual nel `CLAUDE.md`, `wiki.config.toml`,
   struttura wiki — e il report li elenca come *created*, exit 0.
2. **Given** la stessa installazione, **When** si ispezionano gli artefatti installati, **Then**
   nessuno contiene percorsi, nomi o assunzioni del repo Sertor: ogni specificità dell'ospite
   deriva da `wiki.config.toml` (Principio X).
3. **Given** un ospite con cartelle standard (es. `src/`, `docs/`), **When** l'installer genera
   `wiki.config.toml`, **Then** `source_dirs` contiene le cartelle standard effettivamente
   presenti; se nessuna è presente, contiene la radice.
4. **Given** l'installazione completata, **When** si osserva il sistema, **Then** nessuna
   indicizzazione, chiamata LLM o accesso di rete è stata avviata (install ≠ run; gli artefatti
   provengono dal pacchetto stesso).

---

### User Story 2 - Install sicuro su un repo che ha già contenuti (Priority: P2)

Un maintainer lancia `sertor install wiki` su un progetto **esistente**, che può già avere un
`CLAUDE.md` curato, un proprio `.claude/settings.json` con hook personali, un `wiki.config.toml`,
o un'installazione parziale precedente. L'installer non sovrascrive nulla di suo: integra in modo
additivo dove è sicuro (blocco a marker nel `CLAUDE.md`, merge senza duplicati in `settings.json`),
salta file per file ciò che esiste già, e il report dice esattamente cosa è stato creato e cosa
saltato. Rieseguire il comando non cambia lo stato e non duplica nulla.

**Why this priority**: la non-distruttività (REQ-E6 epica) è il rischio più alto della feature
(R-I1: perdita di contenuti utente); senza questa garanzia l'installer non è usabile su progetti
reali. Dipende dagli stessi artefatti di US1.

**Independent Test**: su un repo temporaneo pre-popolato (CLAUDE.md con contenuto utente,
settings.json con un hook custom, wiki.config.toml esistente, skill parzialmente presente),
eseguire `sertor install wiki` due volte e verificare: contenuti utente intatti byte-per-byte fuori
dai blocchi gestiti, zero duplicati, secondo run = stesso stato del primo (idempotenza), report
coerente (created/skipped).

**Acceptance Scenarios**:

1. **Given** un `CLAUDE.md` esistente con contenuto utente, **When** l'installer scrive la sezione
   step-ritual, **Then** la inserisce in un blocco delimitato da marker senza toccare nulla fuori
   dal blocco; un re-run non duplica il blocco.
2. **Given** un `.claude/settings.json` con hook utente preesistenti, **When** l'installer
   registra gli hook di sessione, **Then** aggiunge solo le voci il cui comando non è già
   presente (merge con deduplicazione), preservando tutte le voci utente.
3. **Given** una `wiki.config.toml` già presente, **When** l'installer gira, **Then** il file non
   viene toccato e il report lo segnala come *skipped*.
4. **Given** una skill wiki-author parzialmente presente (alcuni file mancanti), **When**
   l'installer gira, **Then** crea solo i file mancanti e lascia intatti quelli esistenti
   (skip granulare file-per-file), riportando la distinzione.
5. **Given** un'installazione completata, **When** l'utente riesegue `sertor install wiki`,
   **Then** lo stato finale è identico e il report segnala tutto come *skipped* (idempotenza).
6. **Given** un fallimento a metà installazione (es. permessi), **When** l'installer si ferma,
   **Then** riporta esattamente quali artefatti sono stati scritti e quale passo è fallito
   (fail-fast, nessun rollback automatico); un re-run successivo completa i buchi.

---

### User Story 3 - Scoprire e governare l'installazione (Priority: P3)

Un utente esplora il comando: `sertor --help` mostra la struttura (`install wiki` disponibile;
`install rag` e `install governance` dichiarati come pianificati ma non invocabili). Può governare
l'install con le opzioni: `--target <path>` per installare su un repo diverso dalla directory
corrente, `--language <lang>` per la lingua del wiki generato, `--source-dirs <d1,d2>` per
sovrascrivere l'euristica delle cartelle sorgente. Gli errori d'uso producono messaggi leggibili
ed exit code distinti per lo scripting.

**Why this priority**: completa l'usabilità e la scriptabilità del backbone, ma l'install di base
(US1/US2) è già pienamente utile con i default.

**Independent Test**: invocare help, sottocomandi ignoti, stub non implementati e le tre opzioni su
repo temporanei; verificare messaggi, exit code e l'effetto delle opzioni sul `wiki.config.toml`
generato e sulla destinazione.

**Acceptance Scenarios**:

1. **Given** il pacchetto installato, **When** l'utente esegue `sertor --help` /
   `sertor install --help`, **Then** vede i sottocomandi disponibili e gli argomenti; `install rag`
   e `install governance` compaiono come pianificati.
2. **Given** un sottocomando ignoto o un argomento obbligatorio mancante, **When** viene invocato,
   **Then** errore leggibile + exit non-zero, nessuna operazione parziale.
3. **Given** `sertor install rag` (stub), **When** viene invocato, **Then** messaggio leggibile
   "non ancora disponibile" + exit non-zero, nessuna operazione.
4. **Given** `--target <path>` valido, **When** l'install gira, **Then** tutti gli artefatti
   finiscono sotto `<path>` e non nella directory corrente.
5. **Given** `--language it` e/o `--source-dirs src,docs`, **When** l'installer genera
   `wiki.config.toml`, **Then** i valori passati prevalgono su quelli inferiti.

---

### Edge Cases

- `--target` inesistente o non scrivibile → errore leggibile, exit non-zero, nessun artefatto.
- `.claude/settings.json` esistente ma **malformato** (JSON non valido) → l'installer non lo
  riscrive né lo corrompe: errore leggibile che indica il file, fail-fast con report (gli artefatti
  già scritti restano, REQ-125).
- `CLAUDE.md` che contiene già il blocco a marker (anche modificato dall'utente al suo interno) →
  il blocco non viene duplicato; il contenuto fuori dai marker non è mai toccato.
- Ospite senza alcuna cartella standard riconosciuta → `source_dirs = ["."]`.
- Ospite con `wiki/` già esistente (anche non creato da Sertor) → `structure init` idempotente:
  crea solo ciò che manca, non tocca l'esistente.
- Fallimento per permessi a metà run → report di stato parziale esplicito; re-run completa.
- Installazione del pacchetto / import del modulo → nessun effetto collaterale (install ≠ run).
- Doppia invocazione concorrente non è gestita (assunzione: uso single-user; documentato).

## Requirements *(mandatory)*

### Functional Requirements

**Backbone del comando `sertor`**

- **FR-001**: Il sistema MUST esporre un entry-point a riga di comando `sertor` (console-script del
  pacchetto installer) che smista al sottocomando `install` e dichiara i sottocomandi futuri.
  *(REQ-100)*
- **FR-002**: `sertor` MUST fornire help per sé e per ogni sottocomando, con capacità e argomenti.
  *(REQ-101)*
- **FR-003**: Sottocomando ignoto o argomento obbligatorio mancante → errore leggibile + exit
  non-zero, nessuna operazione parziale. *(REQ-102)*
- **FR-004**: Exit code 0 in successo, non-zero in errore, per scripting. *(REQ-103)*
- **FR-005**: I sottocomandi dichiarati ma non implementati (`install rag`, `install governance`)
  MUST produrre un messaggio leggibile "non ancora disponibile" + exit non-zero, senza operazioni.
  *(REQ-104)*

**`sertor install wiki` — installazione**

- **FR-006**: `sertor install wiki [--target <path>]` MUST installare tutti gli artefatti
  abilitanti del sistema-wiki sul repo target (default: directory corrente) e stampare un report
  che elenca ogni artefatto come created / skipped / in conflitto. *(REQ-110)*
- **FR-007**: L'installer MUST operare esclusivamente via file-system: nessuna chiamata LLM, nessun
  provider di embeddings, nessun servizio di rete, nessuna indicizzazione durante l'install.
  *(REQ-111)*
- **FR-008**: L'installer MUST installare: skill wiki-author (SKILL.md, wiki-playbook.md, moduli
  ops), comando `/wiki`, agente wiki-curator, hook di sessione. *(REQ-112)*
- **FR-009**: Tutti gli artefatti installati MUST essere privi di riferimenti a percorsi, domini o
  assunzioni del repo Sertor; ogni valore host-specifico deriva dalla configurazione dell'ospite.
  *(REQ-113, Principio X)*
- **FR-010**: Dopo aver scritto `wiki.config.toml`, l'installer MUST invocare l'operazione
  `structure init` del nucleo deterministico per creare la struttura wiki (idempotente per
  costruzione). *(REQ-114)*
- **FR-011**: Gli artefatti non-Python MUST provenire da dati inclusi nel pacchetto installato
  (package-data nel wheel): coerenza con la versione installata e nessun accesso di rete, per
  costruzione. *(REQ-115, DI-5)*

**Non-distruttività per artefatto**

- **FR-012**: File della skill già presenti sul target → controllo **file-per-file**: gli esistenti
  restano intatti e sono riportati come skipped, i mancanti vengono creati. *(REQ-120, DI-1)*
- **FR-013**: `wiki.config.toml` esistente → mai sovrascritto, riportato come skipped. *(REQ-121)*
- **FR-014**: `CLAUDE.md` esistente → la sezione step-ritual è inserita in un blocco delimitato da
  marker; nulla fuori dal blocco viene modificato; il blocco non si duplica al re-run. *(REQ-122)*
- **FR-015**: `.claude/settings.json` esistente → merge additivo delle voci hook con
  **deduplicazione per comando**: nessuna voce utente rimossa o sovrascritta, nessun duplicato.
  *(REQ-123, DI-2)*
- **FR-016**: `wiki/` esistente → `structure init` idempotente; directory e file esistenti
  riportati come skipped. *(REQ-124)*
- **FR-017**: Se un passo fallisce, l'installer MUST fermarsi riportando artefatto, percorso e
  causa; gli artefatti già scritti restano (nessun rollback automatico) e lo stato parziale è
  esplicito nel report; il re-run completa i mancanti. *(REQ-125, DI-3)*

**Configurazione dell'ospite**

- **FR-018**: `wiki.config.toml` assente → generato con default host-specifici: root, `source_dirs`
  inferiti dal layout (euristica su cartelle standard presenti; nessuna → radice), lingua, sezioni
  di tassonomia, ruoli riferiti agli agenti installati. *(REQ-130, DI-4)*
- **FR-019**: L'installer MUST NOT scrivere segreti (chiavi, credenziali, endpoint) su alcun file
  del repo target. *(REQ-131)*
- **FR-020**: Con `--language <lang>`, il valore MUST essere usato come lingua nel
  `wiki.config.toml` generato. *(REQ-132)*
- **FR-021**: Con `--source-dirs <d1,d2,…>`, le directory passate MUST sostituire i default
  inferiti. *(REQ-133)*

**Trasversali**

- **FR-022**: Esecuzione, import o installazione del pacchetto MUST NOT avviare indicizzazioni,
  chiamate LLM o operazioni RAG: ogni operazione richiede un comando esplicito. *(REQ-140)*
- **FR-023**: L'installer MUST produrre lo stesso stato finale qualunque sia il numero di
  invocazioni: nessun duplicato, nessun errore su artefatti già presenti (idempotenza). *(REQ-141)*
- **FR-024**: L'installer MUST operare su qualunque repo target passato come path, senza assunzioni
  hardcoded su nome, linguaggi, struttura o dimensione. *(REQ-142)*
- **FR-025**: Il report finale MUST riassumere su stdout creati/saltati/conflitti, con exit 0 se
  nessun artefatto ha prodotto errore. *(REQ-143)*

### Key Entities

- **Artefatto installabile**: unità che l'installer porta sull'ospite (file skill, comando, agente,
  hook, voce di settings, blocco CLAUDE.md, config, struttura wiki); ciascuno con la propria regola
  di non-distruttività (create / skip / merge additivo).
- **Report di installazione**: esito per artefatto (created / skipped / conflitto / errore) +
  riepilogo; è il contratto di osservabilità dell'operazione.
- **Blocco a marker**: regione delimitata dentro un file dell'utente (`CLAUDE.md`) che l'installer
  possiede e può riscrivere; tutto il resto del file è intoccabile.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Su un repo vuoto, **un solo comando** produce tutti gli artefatti del sistema-wiki
  senza passi manuali aggiuntivi né errori. *(LSC-1)*
- **SC-002**: Su un repo con `CLAUDE.md`, `wiki/`, `wiki.config.toml` o hook preesistenti, **zero
  byte di contenuto utente** vengono sovrascritti fuori dai blocchi gestiti; il comando completa e
  il report elenca gli skipped. *(LSC-2)*
- **SC-003**: Due esecuzioni consecutive producono **lo stesso stato** degli artefatti: zero
  duplicati, zero errori. *(LSC-3)*
- **SC-004**: **Zero riferimenti** a Sertor-il-progetto negli artefatti installati su un ospite
  terzo (verificabile con una scansione). *(LSC-4)*
- **SC-005**: **Zero** operazioni di indicizzazione, LLM o rete avviate dall'install. *(LSC-5)*
- **SC-006**: L'intero test di accettazione (repo vuoto, re-run, repo pre-popolato) gira **senza
  rete, senza LLM, senza cloud**. *(LSC-6)*
- **SC-007**: `sertor --help` e `sertor install --help` descrivono sottocomandi e argomenti; gli
  stub futuri sono elencati ma non invocabili. *(LSC-7)*
- **SC-008 (dogfood)**: Il sistema-wiki installato su un repo terzo di prova è **operativo**: la
  struttura wiki esiste, `sertor-wiki-tools` gira sulla config generata (scan/lint/validate ok).

## Assumptions

- Il pacchetto installer (`sertor`) è distinto da `sertor-core` e lo dichiara come dipendenza;
  come arrivi nell'ambiente (editable, git+url) è fuori da questa feature. *(A-1/A-2 requisiti)*
- Gli artefatti sorgente oggi vivono in `.claude/` del repo Sertor e vanno resi host-agnostici nel
  bundle del pacchetto; la struttura interna del bundle e la meccanica di accesso sono design.
- Filesystem del target accessibile in lettura/scrittura; nessuna escalation di privilegi. *(A-3)*
- Il `CLAUDE.md` dell'ospite, se presente, è testo UTF-8 in cui è sicuro inserire un blocco a
  marker; il formato esatto del blocco è design. *(A-5)*
- Upgrade degli artefatti già installati, disinstallazione, wizard di configurazione interattivo e
  implementazione di `install rag`/`install governance`: fuori ambito (tagli futuri).
- Invocazioni concorrenti dell'installer sullo stesso target non sono gestite (uso single-user).
