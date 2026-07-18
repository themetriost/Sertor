# Feature Specification: L'installer descrive l'AZIONE + log ispezionabile

**Feature Branch**: `110-feat-018-installer-esito-azione-log`

**Created**: 2026-07-18

**Status**: Draft

**Input**: E2-FEAT-018 (epica sertor-cli), assorbe E10-FEAT-036. Requisiti: `requirements/sertor-cli/feat-018-installer-esito-azione-log/requirements.md`. 3° item della coda dell'analisi [[setup-dichiara-presunzione-non-azione]] (dopo FEAT-038, FEAT-033).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Il report distingue «identico» da «presente ma diverso» (Priority: P1)

Un utente ri-lancia `sertor install rag` (o `upgrade`) su un host dove un file di proprietà di Sertor è
stato **modificato** (dall'utente, o preesistente con contenuto diverso). Oggi il report dice `SKIPPED`
«already present» — identico a quando il file è **byte-identico**. Con la feature, l'installer **confronta
il contenuto** e riporta un esito **distinto** per «presente ma divergente» (non toccato) rispetto a
«presente e identico», così l'utente sa che c'è una divergenza lasciata sul posto.

**Why this priority**: è il cuore — l'esito che descrive l'azione. Chiude la conflazione di `SKIPPED` (il
buco di FEAT-031/032) e, con essa, assorbe E10-FEAT-036 (upgrade-crea-ex-novo diventa un fatto del report).

**Independent Test**: install su un path già occupato da contenuto diverso → l'esito è il nuovo membro
`present-divergent`; su contenuto identico → resta `SKIPPED`. Due esiti osservabili distinti.

**Acceptance Scenarios**:

1. **Given** un file di proprietà di Sertor con contenuto **diverso** da quello che l'installer
   depositerebbe, **When** si esegue install/upgrade, **Then** il report lo marca `present-divergent`
   (nuovo esito) e **non** lo sovrascrive, distinto da `SKIPPED`.
2. **Given** lo stesso file con contenuto **byte-identico**, **When** si esegue install, **Then** l'esito è
   `SKIPPED` (invariato, byte-backward-compat).
3. **Given** uno step dipendenze in cui `uv add` **viene eseguito** su una `.sertor/` preesistente, **When**
   si esegue install, **Then** l'esito riflette l'**esecuzione** del comando, non `SKIPPED` per «dir c'era».
4. **Given** un `upgrade` che deposita una capability **assente**, **When** si esegue, **Then** il report la
   esprime come **creazione** (leggibile), senza logica dedicata a 036.

### User Story 2 - Un log ispezionabile di ciò che è successo (Priority: P2)

Dopo un `install`/`upgrade`/`uninstall`, l'utente vuole sapere **cosa è successo davvero**. Trova
`.sertor/.install-log.jsonl`: una riga per artefatto/step con verbo reale, capability, comando eseguito,
esito col perché, revisione risolta. Il report a schermo è la sintesi; **il log è la verità**.

**Why this priority**: la richiesta esplicita («loggare cosa succede così non ci dobbiamo fidare alla
cieca»). Secondario rispetto a P1 perché l'esito onesto è il presupposto del log onesto.

**Acceptance Scenarios**:

1. **Given** un `install rag` completato, **When** l'utente apre `.sertor/.install-log.jsonl`, **Then**
   trova ≥1 riga JSON per artefatto con `op`, `capability`, `verb`, `outcome`, `reason`, `cmd` (se
   presente), `rev`, schema `install.event/1`.
2. **Given** un `--dry-run`, **When** lo si esegue, **Then** gli esiti proiettati coincidono con quelli che
   l'esecuzione reale scriverebbe (stesso codice; SC-005).
3. **Given** che la scrittura del log fallisca (es. FS read-only), **When** si esegue l'installer, **Then**
   l'installazione **non** aborta; il fallimento del log è segnalato, l'operazione primaria è preservata.

### Edge Cases

- **File di proprietà vs file utente a un path posseduto:** il confronto di contenuto tratta entrambi come
  «divergente → non tocco» (come già fa uninstall `lifecycle.py`).
- **CRLF vs LF:** il confronto normalizza i fine-riga (come `lifecycle.py:162`), per non falsare la divergenza su Windows.
- **Log con potenziali segreti:** i campi passano dallo scrub dell'osservabilità esistente.
- **Esiti esistenti (CREATED/SKIPPED-identico/MERGED/UPDATED/REMOVED):** invariati dove non c'è divergenza (REQ-006).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: L'installer MUST confrontare il contenuto di un artefatto già presente a un path posseduto con
  ciò che depositerebbe, e riportare `present-identical` e `present-divergent` come esiti **distinti** (nuovo
  membro `Outcome` additivo per il caso divergente; identico resta `SKIPPED`).
- **FR-002**: L'installer MUST riportare l'esito di un comando **eseguito** (es. `uv add`) come azione
  compiuta, non come `SKIPPED` perché una precondizione (dir presente) valeva.
- **FR-003**: When `upgrade` deposita una capability prima assente, il report MUST esprimerlo come creazione,
  distinguibile da un refresh (assorbe E10-FEAT-036) — **senza** `if` dedicato a 036.
- **FR-004**: L'installer MUST scrivere un log locale `.sertor/.install-log.jsonl` con, per step/artefatto:
  `op`, `capability`, `verb`, `outcome`, `reason`, `cmd` (se presente), `rev`; schema `install.event/1`;
  una riga JSON in append.
- **FR-005**: La proiezione `--dry-run` e l'esecuzione reale MUST derivare gli esiti dallo **stesso** codice
  (nessuna scorciatoia divergente).
- **FR-006**: Gli esiti **esistenti** MUST restare backward-compatible dove non c'è divergenza (no
  regressione del report per identical/created/merged).
- **FR-007**: If la scrittura del log fallisce, then l'installer MUST NON abortire; MUST segnalare il
  fallimento del log preservando l'operazione primaria e l'exit code.
- **FR-008**: Il log MUST NOT contenere segreti (scrub coerente con l'osservabilità esistente).
- **FR-009**: La capacità (esiti onesti + log) MUST essere installabile via l'installer e riflessa nella
  **documentazione utente** (host-facing completo).

### Key Entities

- **`Outcome` (+1 membro):** l'esito di un artefatto; nuovo membro per «presente ma divergente» (oggi
  collassato in `SKIPPED`).
- **Evento di install (`install.event/1`):** riga di log per artefatto/step — op, capability, verb, outcome,
  reason, cmd, rev.
- **Log-writer (nel kit):** utility accanto a `log_event` che serializza gli eventi in `.install-log.jsonl`,
  riusata dai tre installer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: per un artefatto presente-ma-divergente, il report emette il nuovo esito distinto da `SKIPPED`
  (≥2 esiti osservabili) — verificabile su un caso costruito.
- **SC-002**: lo step dipendenze non emette `SKIPPED` quando `uv add` è stato eseguito (CS-2).
- **SC-003**: un `upgrade` su capability assente è leggibile come creazione (CS-3), senza codice 036-dedicato.
- **SC-004**: dopo install/upgrade/uninstall esiste `.sertor/.install-log.jsonl` con righe `install.event/1`
  complete e ben formate.
- **SC-005**: per gli stessi input, gli esiti di `--dry-run` == quelli scritti dall'esecuzione reale (0 divergenze).
- **SC-006**: **0** regressioni sulle suite installer/kit/flow (esiti esistenti byte-compat).
- **SC-007**: la doc utente (`docs/…` + tabella capability) menziona il log e gli esiti onesti; il bundle
  installer è sincronizzato (guardia sync verde).

## Assumptions

- Il confronto di contenuto di `lifecycle.py:159-164` (read + normalizza CRLF + compara) è riusabile per
  install; `log_event`/l'osservabilità del kit sono la base del log-writer (non un canale nuovo slegato).
- Il nuovo membro `Outcome` è **additivo**: gli esiti esistenti mantengono valore (report byte-identico dove non diverge).
- La scrittura del log è best-effort non-fatale (parità con la filosofia fail-safe degli hook, E4-011).
- P3 (lettore unico / `doctor` che aggrega i segnali) e E2-FEAT-017 (auto-updater) sono **fuori** — item successivi della coda.
- Nessuna rotazione del log al primo taglio (append semplice).
