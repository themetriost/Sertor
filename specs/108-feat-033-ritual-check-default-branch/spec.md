# Feature Specification: `ritual-check` rileva il default branch (non assume `master`)

**Feature Branch**: `108-feat-033-ritual-check-default-branch`

**Created**: 2026-07-18

**Status**: Draft

**Input**: E10-FEAT-033 (epica debito-tecnico). Requisiti: `requirements/debito-tecnico/feat-033-ritual-check-default-branch/requirements.md`. Segnalato da Noetix (Acta), verificato sul codice. 2° item consegnato della coda dell'analisi setup (dopo FEAT-038).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un ospite con default `main` chiude uno step (Priority: P1)

Un ospite ha installato Sertor; il suo repo ha branch di default `main` (nessun `master`). A fine step,
la *forced declaration* del rituale (E10-FEAT-026) lo porta a lanciare `sertor-wiki-tools ritual-check`
per scoprire i candidati distill/drift. Oggi il comando esplode con
`cannot determine a git diff base (no merge-base with 'master')`. Con la feature, `ritual-check` rileva
che il default è `main`, risolve la base, e restituisce i candidati — **senza flag**.

**Why this priority**: è il bug. `ritual-check` è il primo tool che l'ospite tocca con la nostra
governance; su un repo `main` (default moderno diffuso) fallisce al primo colpo. È il taglio MVP: chiuso
questo, la forced declaration è usabile ovunque.

**Independent Test**: in un repo git con default `main` (senza `master`), un commit di feature + una
modifica, `ritual-check` senza `--base` risolve la base e produce l'output senza errore.

**Acceptance Scenarios**:

1. **Given** un repo con default `main` (nessun `master`) e un branch di feature con modifiche, **When**
   l'utente esegue `ritual-check` senza `--base`, **Then** il comando risolve la base (merge-base con
   `main`) ed emette il risultato, **senza** fail-loud.
2. **Given** il repo dogfood con default `master`, **When** l'utente esegue `ritual-check` senza `--base`,
   **Then** il comportamento è **invariato** (base = merge-base con `master`).
3. **Given** un qualsiasi repo, **When** l'utente passa `--base <ref>`, **Then** quel ref è usato e il
   rilevamento del default è saltato.

### User Story 2 - Nessun default risolvibile → fallimento onesto (Priority: P2)

In un contesto senza mainline risolvibile (nessun `origin/HEAD`, nessun `main`/`master`, o HEAD staccato
senza antenato comune), `ritual-check` non inventa uno scope: dichiara che non riesce a determinare la
base e come rimediare.

**Why this priority**: complemento fail-loud (Principio XII), invariato rispetto a oggi — un tool di
scoperta che produce uno scope silenziosamente vuoto/sbagliato è peggio di un errore.

**Acceptance Scenarios**:

1. **Given** un repo senza default rilevabile né candidato con merge-base, **When** l'utente esegue
   `ritual-check` senza `--base`, **Then** fallisce con messaggio azionabile (`--base`/`--pages`) ed
   exit non-zero, senza emettere candidati.

### Edge Cases

- **`origin/HEAD` non impostato** (alcuni cloni): il rilevamento primario manca → fallback ai candidati.
- **Repo con *sia* `main` sia `master`**: `origin/HEAD` (se presente) decide autorevolmente; se assente,
  l'ordine `main`→`master` è deterministico e documentato.
- **Repo senza remote** (locale): niente `origin/…` → fallback ai rami locali `main`/`master`.
- **HEAD staccato / CI shallow**: nessun merge-base → fail-loud onesto (US2).
- **Default `master` (dogfood):** deve restare identico — nessuna regressione.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `ritual-check` MUST risolvere la base del diff contro il **branch di default rilevato a
  runtime**, non contro un nome hardcodato.
- **FR-002**: Where `--base <ref>` è fornito, `ritual-check` MUST usarlo e saltare il rilevamento.
- **FR-003**: `ritual-check` MUST rilevare il default via `git symbolic-ref refs/remotes/origin/HEAD`
  quando disponibile (fonte autorevole del remote).
- **FR-004**: When `origin/HEAD` non è disponibile, `ritual-check` MUST provare un insieme ordinato di
  candidati esistenti (`origin/main`, `origin/master`, `main`, `master`) e usare il primo con un
  merge-base con HEAD.
- **FR-005**: If nessun default né candidato risolve una base, then `ritual-check` MUST fallire a voce
  alta con un messaggio azionabile (`--base`/`--pages`) ed exit non-zero, senza produrre candidati.
- **FR-006**: Il percorso di risoluzione MUST NOT contenere nomi di branch hardcodati come **unica**
  strategia; deve funzionare su un repo `main`-default senza `--base` (verificabile da guard test, Principio X).
- **FR-007**: Il contratto pubblico (`--base`/`--pages`, forma del messaggio fail-loud, output JSON
  `wiki.ritual_check/1`) MUST restare backward-compatible (nessuna regressione `master`-default).

### Key Entities

- **Base del diff:** il commit/ref rispetto a cui si calcola `base...HEAD`; deve derivare dal default
  reale del repo, non da un nome assunto.
- **Branch di default:** il ramo mainline del repo, rilevato (remote `origin/HEAD`) o dedotto (candidati).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: su un repo con default `main` (senza `master`), `ritual-check` senza flag → **0** fail-loud
  spurii, output prodotto.
- **SC-002**: su un repo `master`-default (dogfood), **0** differenze di comportamento (base risolta come prima).
- **SC-003**: `--base <ref>` esplicito onorato in **100%** dei casi (rilevamento saltato).
- **SC-004**: repo senza default/candidato risolvibile → fail-loud con messaggio azionabile, exit non-zero,
  **0** candidati emessi.
- **SC-005**: guard test verde su un repo `main`-default (Principio X: nessun assunto `master` blocca).
- **SC-006**: suite `test_ritual_check.py` esistente verde (nessuna regressione del contratto).

## Assumptions

- Il branch di default è determinabile via `origin/HEAD` sui repo con remote; i repo senza remote hanno un
  ramo mainline fra `main`/`master`.
- `ritual-check` continua a essere **sola lettura** e **zero-LLM** (trova; l'agente giudica — D↔N).
- L'override del default via `wiki.config.toml` NON fa parte di questo taglio (Could, rinviato).
- Nessuna nuova dipendenza: si usa `git` via `subprocess`, già in `ritual_check.py`.
