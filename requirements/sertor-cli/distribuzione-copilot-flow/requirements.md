# Requisiti — Distribuzione governance/SDLC su GitHub Copilot (`sertor-flow`)
<!-- Deriva da: FEAT-009 (epica sertor-cli) — gemella di distribuzione-copilot (FEAT-007) -->

## 1. Contesto e problema (perché)

Il pacchetto **`sertor-flow`** porta su un ospite l'apparato di **metodo di sviluppo (SDLC)**:
skill/agenti SpecKit (vendorati da spec-kit, MIT, pinnati), la skill `requirements` e l'agente
`requirements-analyst` (Sertor-authored), l'agente `configuration-manager`, il macchinario
`.specify/` (templates, scripts, extensions, workflows), una **costituzione-starter** neutra e un
blocco **rituale SDLC** nel `CLAUDE.md` dell'ospite (marker `SERTOR:SDLC-RITUAL`).

Tutto questo è oggi depositato in **forma specifica per Claude** (`.claude/skills/speckit-*`,
`.claude/agents/speckit-*`, blocco in `CLAUDE.md`). Un team che usa **GitHub Copilot** installa
`sertor-flow` ma **non può usarne le superfici**: ha il metodo nel pacchetto, non nel suo assistente.

Questa feature è la **gemella** di `distribuzione-copilot` (FEAT-007), che copre il pacchetto
`sertor` (RAG + wiki). Qui l'oggetto è il pacchetto `sertor-flow` (governance/SDLC). Le due feature
**condividono il meccanismo** di targeting per-assistente e la decisione di design "riuso vs
traduzione" (vedi §7, DA-1).

> **Leva chiave (grounding §7):** SpecKit è *agent-agnostic by design* e supporta **Copilot come
> target di prima classe** (`specify init --ai copilot` genera `.github/prompts/*.prompt.md` +
> `.github/agents/*.agent.md`). Il **motore** SpecKit (`.specify/`) è condiviso tra assistenti.
> Quindi la parte SpecKit del bundle si ottiene **ri-vendorando** l'output Copilot di spec-kit — lo
> *stesso* meccanismo di vendoring già usato per la variante Claude. Resta da tradurre solo la parte
> **Sertor-authored** (agenti, skill `requirements`, blocco rituale).

## 2. Obiettivi e criteri di successo

- **Obiettivo:** un ospite che usa Copilot installa `sertor-flow` e ottiene **lo stesso metodo SDLC**
  (SpecKit + requisiti + delega git + costituzione + rituale) che otterrebbe con Claude.
- **CS-1 (parità di superfici governance):** per la governance installata, ogni superficie
  disponibile sotto Claude ha un equivalente funzionante sotto Copilot (mappatura 1-a-1, niente
  omissioni silenziose).
- **CS-2 (SpecKit Copilot operativo):** i comandi `/speckit.*` sono invocabili da un client Copilot e
  producono gli stessi artefatti (spec/plan/tasks/…) della variante Claude.
- **CS-3 (selezione assistente):** l'utente sceglie l'assistente target di `sertor-flow install` tra
  almeno `claude` e `copilot`, ottenendo solo gli artefatti di quell'assistente.
- **CS-4 (motore condiviso):** il macchinario `.specify/` (script + template) è installato una sola
  volta, indipendente dall'assistente.
- **CS-5 (indipendenza dal core):** la feature **non** introduce alcuna dipendenza di `sertor-flow`
  da `sertor-core` (invariante del pacchetto preservata).
- **CS-6 (non distruttività, idempotenza, install ≠ run):** ereditati dall'epica (REQ-E2/E6) e da
  `sertor-flow`.
- **CS-7 (onestà sui gap):** ogni superficie priva di equivalente è dichiarata esplicitamente.

## 3. Stakeholder e attori

- **Owner/maintainer:** decide assistente target della governance su un repo.
- **Team che usa Copilot:** destinatario primario; oggi escluso dalla governance.
- **Pacchetto `sertor-flow` + `sertor-install-kit`:** motore di installazione e bundle.
- **Upstream spec-kit (MIT):** fornisce le varianti per-assistente di SpecKit (incl. Copilot).
- **Repository target:** progetto nuovo o esistente.

## 4. Ambito

### In ambito
- **Selezione assistente target** su `sertor-flow install` (almeno `claude`, `copilot`).
- **Parità su Copilot** delle superfici di `sertor-flow`:
  - comandi/agenti **SpecKit** (`/speckit.*`) nella variante Copilot;
  - agenti **Sertor-authored** `requirements-analyst` e `configuration-manager`;
  - skill **`requirements`** (Sertor-authored);
  - **blocco rituale SDLC** (oggi nel `CLAUDE.md`) nell'equivalente istruzioni Copilot;
  - **costituzione-starter** e macchinario `.specify/` (assistant-agnostic, una volta sola).
- **Dichiarazione esplicita** dei gap; **attribuzione/licenza** preservata sugli asset vendorati.
- **Riuso del meccanismo di targeting** condiviso con `distribuzione-copilot`.

### Fuori ambito
- **Superfici del pacchetto `sertor`** (server MCP, wiki, rituale wiki/RAG): coperte dalla feature
  gemella `distribuzione-copilot` (FEAT-007).
- **Codex** (AGENTS.md + variante SpecKit Codex): rinviato come **Could** (§9).
- **Il *come*** (layout file esatto, riuso `.claude` vs `.github/*`, versione spec-kit da vendorare):
  fase di **design**; §7 ne fissa solo il grounding.
- **Client Copilot diversi da VS Code agent mode** (assunzione DA-2).
- **PyPI**; modifiche al metodo SDLC in sé.

## 5. Requisiti funzionali (EARS)

### Selezione e instradamento per assistente
- **REQ-001 (Optional):** *Where the user runs `sertor-flow install`, the system shall let the user
  select the target assistant from at least `claude` and `copilot`.*
- **REQ-002 (Ubiquitous):** *The system shall apply a single, documented default target assistant
  when the user specifies none.*
- **REQ-003 (Event-driven):** *When the user selects a target assistant, the system shall install
  only the governance artifacts belonging to that assistant.*

### Variante SpecKit per Copilot
- **REQ-004 (Event-driven):** *When installing governance with the `copilot` target, the system shall
  provide the Copilot-targeted SpecKit command surfaces (prompt files and custom agents) functionally
  equivalent to the Claude-targeted ones.*
- **REQ-005 (Ubiquitous):** *The system shall install the shared SpecKit machinery (the `.specify/`
  scripts and templates) once, independently of the selected target assistant.*
- **REQ-006 (Ubiquitous):** *The system shall preserve license attribution for vendored SpecKit
  assets of every assistant variant it ships (pinned upstream version + NOTICE), inheriting
  `sertor-flow` REQ-025.*

### Superfici Sertor-authored (traduzione, come la feature gemella)
- **REQ-007 (Event-driven):** *When installing governance with the `copilot` target, the system shall
  provide Copilot custom-agent equivalents of the `requirements-analyst` and `configuration-manager`
  agents.*
- **REQ-008 (Event-driven):** *When installing governance with the `copilot` target, the system shall
  provide a Copilot equivalent of the `requirements` skill invokable from a Copilot client.*
- **REQ-009 (Event-driven):** *When installing governance with the `copilot` target, the system shall
  deposit the SDLC ritual instruction block into the Copilot repository-wide instruction surface,
  delimited by stable markers so re-installation updates it in place.*
- **REQ-010 (Ubiquitous):** *The system shall install the constitution-starter identically
  regardless of the target assistant (assistant-agnostic artifact).*

### Parità, onestà e invarianti
- **REQ-011 (Ubiquitous):** *The system shall expose a documented surface-by-surface mapping between
  the Claude governance artifacts and their Copilot equivalents.*
- **REQ-012 (Unwanted):** *If an in-scope Claude governance surface has no functional equivalent on
  the target assistant, then the system shall declare the gap explicitly rather than omit it
  silently.*
- **REQ-013 (Unwanted):** *If the setup runs against an existing repository, then the system shall not
  overwrite user-modified files without explicit confirmation (inherits REQ-E6).*
- **REQ-014 (Ubiquitous):** *The system shall be idempotent: re-running the install for the same
  target assistant shall not duplicate or corrupt installed artifacts.*
- **REQ-015 (Unwanted):** *If governance is installed or added for any target assistant, then the
  system shall not introduce a dependency of `sertor-flow` on `sertor-core` (preserves package
  independence).*
- **REQ-016 (Unwanted):** *If governance is installed for the `copilot` target, then the system shall
  not automatically run any SpecKit phase or other action (install ≠ run).*

### Meccanismo condiviso (anti-drift)
- **REQ-017 (Ubiquitous):** *The system shall implement assistant targeting through the shared
  install toolkit (`sertor-install-kit`) so that `sertor` and `sertor-flow` share one targeting
  mechanism rather than divergent copies.*
- **REQ-018 (Optional):** *Where the same surface content is shipped for more than one assistant, the
  system shall derive each assistant's artifacts from a single source of truth to prevent
  cross-assistant drift.*

### Codex (Could)
- **REQ-019 (Optional):** *Where the user selects `codex` as target, the system shall provide the
  Codex SpecKit variant and deposit an `AGENTS.md` instruction surface for the Sertor-authored
  governance.*

## 6. Requisiti non funzionali

- **NFR-1 (Assistant-agnostic / Principio X):** estende il Principio X all'assistente ospite; il
  metodo SDLC non cambia, cambia solo la sua veste per-assistente.
- **NFR-2 (Thin consumer + vendoring):** riusa il motore `sertor-install-kit` e il **vendoring**
  upstream di spec-kit; nessuna logica di installazione né di SpecKit reinventata.
- **NFR-3 (No dipendenza dal core):** invariante dura di `sertor-flow` (vedi REQ-015).
- **NFR-4 (Idempotenza & non distruttività):** per artefatto.
- **NFR-5 (Offline / install ≠ run):** nessuna rete a pagamento, nessuna esecuzione.
- **NFR-6 (Manutenibilità / no drift):** vendorare *due* varianti (Claude + Copilot) raddoppia la
  superficie da tenere pinnata/attribuita → governare il drift (REQ-006/018).
- **NFR-7 (Robustezza alle Preview):** alcune superfici Copilot sono Preview; degradare in modo
  onesto, isolare la dipendenza.

## 7. Vincoli, assunzioni e dipendenze

- **Dipendenza:** `sertor-install-kit`, asset attuali di `sertor-flow`, upstream spec-kit (MIT).
- **Coordinamento con la feature gemella:** `distribuzione-copilot` (FEAT-007) definisce il
  meccanismo `--assistant` e scioglie la DA comune sul riuso/traduzione; questa feature lo **eredita**
  (idealmente implementata dopo, riusando il pattern).

**Grounding verificato (2026-06-15) — informa lo scope, NON è design:**
- **spec-kit** supporta Copilot di prima classe: `specify init --ai copilot` genera
  `.github/prompts/*.prompt.md` + `.github/agents/*.agent.md` per ogni `/speckit.*`; il macchinario
  `.specify/` è **agent-agnostic** (condiviso). Supporta 24+ agenti (incl. Claude, Copilot, Codex).
- Superfici Copilot (come nella feature gemella): hook `.github/hooks/*.json` (8 eventi = Claude),
  custom agent `.github/agents/*.agent.md`, prompt file `.github/prompts/*.prompt.md`, istruzioni
  `.github/copilot-instructions.md`, e lettura nativa di `.claude/settings.json`/`CLAUDE.md`.
- **Assunzione:** il bundle `sertor-flow` oggi è **Claude-only** (asset `.claude/skills|agents/
  speckit-*` + blocco SDLC); va aggiunta la variante Copilot.
- **Assunzione (da verificare in design):** la versione di spec-kit attualmente vendorata
  (pinnata 0.8.18) emette la variante Copilot nel layout atteso; altrimenti decidere se aggiornare il
  pin.
- **Assunzione:** client target = **GitHub Copilot in VS Code (agent mode)**.

## 8. Rischi

- **R-1 — Doppio vendoring:** mantenere due varianti SpecKit pinnate/attribuite aumenta il carico di
  manutenzione e il rischio di disallineamento di versione (mitiga REQ-006/NFR-6).
- **R-2 — Superfici Copilot in Preview:** cambi upstream (mitiga NFR-7).
- **R-3 — Parità illusoria:** un comando Copilot che esiste ma non si comporta come l'originale
  (mitiga CS-1/REQ-011: verifica comportamentale).
- **R-4 — Deriva dal pin upstream:** la variante Copilot di spec-kit evolve diversamente dalla Claude
  tra versioni (mitiga pin unico + ri-vendoring atomico delle due varianti).
- **R-5 — Accoppiamento con la feature gemella:** se il meccanismo `--assistant` non è davvero
  condiviso nel kit, le due CLI divergono (mitiga REQ-017).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001…REQ-016 — targeting assistente su `sertor-flow install`, variante SpecKit
  Copilot, traduzione delle superfici Sertor-authored (agenti, skill `requirements`, blocco SDLC),
  parità con mappatura, onestà sui gap, idempotenza/non distruttività/install≠run, **no dipendenza
  dal core**.
- **Should:** REQ-017 (targeting condiviso nel kit), REQ-018 (single source of truth / anti-drift).
- **Could:** REQ-019 (Codex).
- **Won't (per ora):** superfici del pacchetto `sertor` (→ feature gemella); PyPI; client Copilot
  diversi da VS Code agent mode.

## 10. Domande aperte

- **DA-1 (condivisa con FEAT-007) — Riuso vs traduzione.** Per la parte **Sertor-authored** vale lo
  stesso bivio: riusare gli asset `.claude` (Copilot li legge) o autorizzare asset `.github/*`
  nativi? Per la parte **SpecKit** la risposta è più netta: vendorare l'output `--ai copilot` di
  spec-kit (nativo `.github`). Da confermare con lo spike unico in `/speckit-plan`.
- **DA-2 (condivisa) — Quale client Copilot?** VS Code agent mode (assunzione corrente) o anche il
  Copilot coding agent cloud? *(Raccomandato: VS Code agent mode nel primo taglio.)*
- **DA-3 (condivisa) — Default e meccanismo di selezione.** `--assistant claude|copilot`, default
  `claude`? Da allineare 1-a-1 con la feature gemella (stesso flag, stesso default).
- **DA-4 — Versione spec-kit per la variante Copilot.** Il pin 0.8.18 emette il layout Copilot
  atteso? Se no, bump del pin o `--ai generic`? Da verificare in design.
