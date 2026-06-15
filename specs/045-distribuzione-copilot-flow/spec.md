# Feature Specification: Distribuzione governance/SDLC su GitHub Copilot (`sertor-flow`)

**Feature Branch**: `045-distribuzione-copilot-flow`

**Created**: 2026-06-15

**Status**: Draft

**Input**: FEAT-009 (epica sertor-cli) — requisiti in `requirements/sertor-cli/distribuzione-copilot-flow/requirements.md`. Gemella di FEAT-007 (consegnata, PR #64).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Il metodo SpecKit usabile da Copilot (Priority: P1) 🎯 MVP

Un team che usa **GitHub Copilot** installa la governance di Sertor su un repository scegliendo il
proprio assistente; al termine i comandi del metodo SpecKit (`/speckit.*`: specify, plan, tasks, …)
sono **invocabili dal client Copilot** e producono gli stessi artefatti che otterrebbe un utente Claude.

Per ottenere ciò, `sertor-flow` **non spedisce più copie congelate di SpecKit**: **lancia l'installer
di spec-kit** per l'assistente scelto, che deposita lui la variante corretta (Copilot →
`.github/prompts/` + `.github/agents/`; il macchinario `.specify/` è condiviso). Questo cambia anche il
percorso Claude (non più da copie vendorate).

**Why this priority**: è il cuore del valore — il metodo di sviluppo disponibile nel proprio
assistente — e introduce il cambio di meccanismo (vendoring → lancio dell'installer) su cui tutto il
resto poggia. È un incremento dimostrabile da solo.

**Independent Test**: su un repo pulito, installare la governance scegliendo Copilot; verificare che i
comandi `/speckit.*` siano presenti e invocabili dal client Copilot e che il macchinario condiviso
`.specify/` sia installato una sola volta. Ripetere con Claude e verificare la **non-regressione** (gli
stessi comandi nella forma Claude).

**Acceptance Scenarios**:

1. **Given** un repo senza governance, **When** l'utente installa la governance con target Copilot,
   **Then** le superfici comando/agente di SpecKit per Copilot risultano presenti e invocabili dal
   client, e il macchinario `.specify/` è installato una volta sola.
2. **Given** la stessa installazione con target Claude, **When** completa, **Then** produce le superfici
   SpecKit nella forma Claude **equivalenti a oggi** (non-regressione), pur ottenute lanciando
   l'installer di spec-kit invece che da copie vendorate.
3. **Given** che l'installer di spec-kit non è disponibile o non raggiungibile, **When** si tenta
   l'installazione, **Then** il sistema **fallisce in modo esplicito e azionabile**, senza lasciare le
   superfici SpecKit a metà né omettendole in silenzio.
4. **Given** governance installata, **When** l'utente non avvia alcun comando, **Then** nessuna fase
   SpecKit o altra azione parte automaticamente (install ≠ run).

---

### User Story 2 - Le superfici Sertor-authored su Copilot (Priority: P2)

Oltre a SpecKit, l'utente Copilot riceve le superfici **scritte da Sertor** che SpecKit non genera: gli
agenti `requirements-analyst` e `configuration-manager`, la skill `requirements`, e il **blocco rituale
SDLC** (oggi nel `CLAUDE.md`), nelle forme native di Copilot. La costituzione-starter è installata
identica per ogni assistente.

**Why this priority**: completa la **parità** della governance portando ciò che non viene da spec-kit;
poggia sul targeting già introdotto e sul meccanismo di US1.

**Independent Test**: installare la governance con target Copilot; verificare che esistano i custom-agent
Copilot per `requirements-analyst`/`configuration-manager`, la skill `requirements` come prompt-file, e
il blocco rituale SDLC nella superficie di istruzioni di Copilot; la costituzione-starter presente e
identica.

**Acceptance Scenarios**:

1. **Given** l'installazione con target Copilot, **When** completa, **Then** gli agenti Sertor-authored
   e la skill `requirements` esistono come custom-agent/prompt-file Copilot.
2. **Given** l'installazione con target Copilot, **When** completa, **Then** il blocco rituale SDLC è
   presente, a marker, nella superficie di istruzioni di Copilot (idempotente su re-run).
3. **Given** target Claude o Copilot, **When** completa, **Then** la costituzione-starter è installata
   identica (assistant-agnostic).
4. **Given** una superficie Claude priva di equivalente funzionale su Copilot, **When** si installa,
   **Then** il gap è **dichiarato esplicitamente**, mai omesso in silenzio.

---

### Edge Cases

- **Refactor che cambia il path Claude**: passando da vendoring a lancio dell'installer, anche
  l'installazione Claude cambia meccanismo; deve restare **funzionalmente equivalente** (non-regressione).
- **Installer spec-kit assente/non raggiungibile / versione incompatibile**: fail-fast esplicito; non
  lasciare stato parziale.
- **Coesistenza claude + copilot** sullo stesso repo: le due configurazioni di governance coesistono
  senza conflitti né doppio-trigger.
- **Repo esistente con file utente**: nessuna sovrascrittura silenziosa.
- **Invariante dura**: l'operazione non deve introdurre alcuna dipendenza di `sertor-flow` da
  `sertor-core`.
- **Ospiti con SpecKit già vendorato** da un'installazione precedente: la migrazione di quegli ospiti è
  fuori ambito (annotato).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST consentire di scegliere l'assistente target di `sertor-flow install` tra
  almeno `claude` e `copilot`, installando solo gli artefatti di governance di quell'assistente.
- **FR-002**: Il sistema MUST applicare un assistente target predefinito documentato (allineato a
  FEAT-007) quando l'utente non ne specifica alcuno.
- **FR-003**: Il sistema MUST ottenere le superfici SpecKit **lanciando l'installer di spec-kit** per
  l'assistente target (a versione fissata), **anziché** spedire copie vendorate.
- **FR-004**: Se l'installer di spec-kit non è disponibile o non può essere ottenuto/eseguito, allora il
  sistema MUST fallire in modo esplicito e azionabile, senza superfici SpecKit parziali o silenziosamente
  omesse.
- **FR-005**: Il sistema MUST installare il macchinario condiviso di SpecKit (`.specify/`) una sola
  volta, indipendentemente dall'assistente target.
- **FR-006**: Quando il target è Copilot, il sistema MUST fornire equivalenti funzionali Copilot delle
  superfici SpecKit (comandi/agenti) corrispondenti a quelle prodotte per Claude.
- **FR-007**: Quando il target è Copilot, il sistema MUST fornire equivalenti Copilot delle superfici
  **Sertor-authored**: agenti `requirements-analyst` e `configuration-manager`, skill `requirements`.
- **FR-008**: Quando il target è Copilot, il sistema MUST depositare il blocco rituale SDLC nella
  superficie di istruzioni repo-wide di Copilot, delimitato da marcatori stabili (idempotente).
- **FR-009**: Il sistema MUST installare la costituzione-starter identica indipendentemente
  dall'assistente target (artefatto assistant-agnostic).
- **FR-010**: Il sistema MUST esporre una mappatura documentata superficie-per-superficie tra gli
  artefatti di governance Claude e i loro equivalenti Copilot.
- **FR-011**: Se una superficie di governance Claude in ambito non ha equivalente funzionale
  sull'assistente target, allora il sistema MUST dichiarare il gap esplicitamente, mai ometterlo.
- **FR-012**: Il sistema MUST preservare l'equivalenza funzionale dell'installazione **Claude** dopo il
  passaggio a lancio-installer (non-regressione rispetto al comportamento vendorato odierno).
- **FR-013**: Se la governance è installata per qualunque assistente, allora il sistema MUST NOT avviare
  automaticamente alcuna fase SpecKit o altra azione (install ≠ run).
- **FR-014**: Quando il setup gira su un repo esistente, il sistema MUST NOT sovrascrivere file
  modificati dall'utente senza conferma esplicita.
- **FR-015**: La ri-esecuzione dell'installazione per lo stesso assistente MUST essere idempotente.
- **FR-016**: Il sistema MUST NOT introdurre alcuna dipendenza di `sertor-flow` da `sertor-core`
  (invariante dura del pacchetto).
- **FR-017**: Il sistema MUST implementare il targeting per-assistente **riusando il meccanismo
  condiviso** introdotto da FEAT-007 (un solo meccanismo `--assistant` tra `sertor install` e
  `sertor-flow install`), senza duplicarlo.
- **FR-018**: Il sistema MUST preservare l'attribuzione di licenza richiesta da spec-kit (MIT) per il
  contenuto che ne deriva, coerente con il nuovo meccanismo di ottenimento.

### Key Entities

- **Assistente target**: l'assistente per cui si installa la governance (almeno `claude`, `copilot`);
  riusa il concetto introdotto da FEAT-007.
- **Superficie di governance**: categoria di artefatto (comando/agente SpecKit, agente Sertor-authored,
  skill `requirements`, blocco rituale SDLC, costituzione-starter, macchinario `.specify/`).
- **Fonte SpecKit**: l'installer di spec-kit a versione fissata, da cui le superfici SpecKit sono
  **ottenute a install-time** (non più copie vendorate).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un utente Copilot completa l'installazione della governance scegliendo l'assistente e usa
  i comandi `/speckit.*` dal proprio client, senza editing manuale.
- **SC-002**: Per la governance installata, il **100%** delle superfici disponibili sotto Claude ha
  sotto Copilot un equivalente funzionante **oppure** un gap dichiarato; **0** superfici omesse in
  silenzio.
- **SC-003**: L'installazione **Claude** dopo il refactor produce una governance **funzionalmente
  equivalente** a quella odierna (non-regressione verificata).
- **SC-004**: In **0** casi l'installazione avvia automaticamente una fase SpecKit o altra azione.
- **SC-005**: La ri-esecuzione produce **0** duplicazioni e **0** file corrotti; su repo esistente **0**
  sovrascritture silenziose.
- **SC-006**: **0** dipendenze di `sertor-flow` da `sertor-core` (verificato).
- **SC-007**: Con installer di spec-kit assente/non raggiungibile, l'installazione **fallisce
  esplicitamente** in **100%** dei casi (nessuno stato parziale).

## Assumptions

- **Client target = GitHub Copilot in VS Code (agent mode)**; altri client Copilot fuori dal primo
  taglio.
- **Meccanismo di selezione assistente = quello di FEAT-007** (`--assistant claude|copilot`, default
  `claude`), riusato dal `sertor-install-kit`.
- **Lancio dell'installer di spec-kit**: il *come* (comando esatto, versione pinnata, gestione offline)
  è design (fase plan); la versione di spec-kit usata deve emettere il layout Copilot atteso (da
  verificare nel plan, DA-4).
- **Riuso vs traduzione** per le superfici Sertor-authored: stessa leva di design di FEAT-007 (DA-2),
  sciolta nel plan; non cambia il *cosa* di questa spec.
- **Migrazione di ospiti con SpecKit già vendorato**: fuori ambito.
- **Ambito ai soli asset del pacchetto `sertor-flow`**; il pacchetto `sertor` (wiki+rag) è FEAT-007 (già
  consegnata).
- **Codex** fuori taglio (Could d'epica).
