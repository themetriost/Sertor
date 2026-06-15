# Requisiti — Distribuzione su GitHub Copilot (parità di assistente)
<!-- Deriva da: FEAT-007 (epica sertor-cli) -->

## 1. Contesto e problema (perché)

Tutto il consegnato di Sertor (server MCP `sertor-rag`, sistema-wiki, capacità RAG, rituale di
metodo) è oggi distribuito su un ospite in **forma specifica per Claude Code**: gli installer
(`sertor install wiki`, `sertor install rag`) depositano `.claude/skills`, `.claude/agents`,
`.claude/hooks`, `.claude/commands`, voci in `.claude/settings.json`, il `.mcp.json` e blocchi a
marker nel `CLAUDE.md`. Un team che lavora con **GitHub Copilot** non riceve nulla di questo: le
capacità *esistono* nel pacchetto ma non sono *raggiungibili* dal suo assistente.

Questo viola lo spirito del **Principio X (host-agnostico)** esteso all'**assistente ospite**: le
capacità non devono dipendere da un solo assistente. Le **CLI** di esecuzione (`sertor-rag`,
`sertor-wiki-tools`) sono già assistant-agnostic — il gap è tutto nelle **superfici agentiche** e
nel **cablaggio MCP**.

La ricognizione aggiornata (2026-06-15) mostra che GitHub Copilot dispone oggi delle superfici di
personalizzazione necessarie per la **parità funzionale**: hook con gli stessi 8 eventi di Claude,
custom agent (`.agent.md`), prompt file, istruzioni repo-wide, MCP di workspace — e legge
nativamente anche `.claude/settings.json`, `CLAUDE.md`, `AGENTS.md`. La parità è quindi tecnicamente
fattibile (vedi §7, Grounding).

> Distinzione netta da **DA-6** dell'epica: lì «GitHub Copilot» è un *provider LLM* da configurare;
> qui Copilot è l'**assistente consumatore** delle superfici installate. Sono assi diversi.

## 2. Obiettivi e criteri di successo

- **Obiettivo:** un ospite che usa Copilot può installare le capacità del pacchetto `sertor`
  (wiki + rag) e ottenerne **lo stesso comportamento** che otterrebbe con Claude.
- **CS-1 (parità di superfici):** per la capacità installata, **ogni** superficie agentica
  disponibile sotto Claude ha un equivalente funzionante sotto Copilot (mappatura 1-a-1
  verificabile, nessuna superficie silenziosamente omessa).
- **CS-2 (MCP raggiungibile):** dopo `install rag` con target Copilot, il server `sertor-rag`
  risulta collegato e interrogabile da un client Copilot, senza editing manuale della parte non
  segreta della configurazione.
- **CS-3 (selezione assistente):** l'utente può scegliere l'assistente target dell'installazione tra
  almeno `claude` e `copilot`, ottenendo **solo** gli artefatti di quell'assistente.
- **CS-4 (non distruttività & idempotenza):** l'installazione con target Copilot è non distruttiva su
  un repo esistente e idempotente su ri-esecuzione (eredita CS-4 dell'epica).
- **CS-5 (install ≠ run):** in 0 casi l'installazione su Copilot avvia automaticamente
  ingestione/indicizzazione (eredita CS-2 dell'epica / REQ-E2).
- **CS-6 (onestà sui gap):** ogni superficie priva di equivalente funzionale su Copilot è
  **dichiarata esplicitamente** all'utente, mai saltata in silenzio.

## 3. Stakeholder e attori

- **Owner/maintainer:** decide su quale assistente installare le capacità su un repo.
- **Team che usa Copilot:** destinatario primario; oggi escluso.
- **Repository target:** progetto nuovo o esistente su cui si installa.
- **Pacchetto `sertor` / `sertor-install-kit`:** fornisce il motore di installazione e gli asset.
- **Epica `sertor-core`:** fornisce il server MCP e le capacità sottostanti (invariate).

## 4. Ambito

### In ambito
- **Selezione dell'assistente target** nell'esperienza di installazione (almeno `claude`,
  `copilot`).
- **Parità funzionale su Copilot** delle superfici del pacchetto **`sertor`**:
  - server MCP `sertor-rag` cablato nei client Copilot;
  - blocco istruzioni/rituale (oggi nel `CLAUDE.md`) nell'equivalente Copilot;
  - skill/comandi del wiki (es. `/wiki`, `wiki-author`) nell'equivalente prompt-file Copilot;
  - agente `wiki-curator` nell'equivalente custom-agent Copilot;
  - hook del wiki (promemoria di registrazione) e hook anti-bypass del Principio XI
    (`sertor-rag-usage-check`) negli equivalenti hook Copilot.
- **Dichiarazione esplicita** di eventuali gap di parità.
- **Idempotenza, non distruttività, install ≠ run** sul target Copilot.

### Fuori ambito
- **Traduzione delle superfici di governance/SDLC** (pacchetto `sertor-flow`: skill/agenti SpecKit,
  `requirements`, `configuration-manager`, blocco SDLC): **feature successiva** dedicata.
- **Codex** (AGENTS.md + MCP): rinviato come **Could** (vedi §9), non nel taglio principale.
- **Copilot come provider LLM** (DA-6): asse diverso, non qui.
- **Il *come*** (formati file esatti, meccanismo del flag, riuso del formato `.claude`): è materia
  della fase di **design** (`/speckit-plan`); §7 ne registra solo il grounding verificato.
- **Pubblicazione PyPI** e modifiche alle capacità del core.

## 5. Requisiti funzionali (EARS)

### Selezione e instradamento per assistente
- **REQ-001 (Optional):** *Where the user runs a `sertor install` command, the system shall let the
  user select the target assistant from at least `claude` and `copilot`.*
- **REQ-002 (Ubiquitous):** *The system shall apply a single, documented default target assistant
  when the user specifies none.*
- **REQ-003 (Event-driven):** *When the user selects a target assistant, the system shall install
  only the artifacts belonging to that assistant for the selected capability.*
- **REQ-004 (Event-driven):** *When the user selects `copilot` as target for an in-scope capability,
  the system shall install a functional Copilot equivalent for every surface that the `claude`
  target installs for that same capability.*

### Server MCP su Copilot (capacità `rag`)
- **REQ-005 (Event-driven):** *When installing the `rag` capability with the `copilot` target, the
  system shall register the `sertor-rag` MCP server in the Copilot MCP configuration surface of the
  target repository.*
- **REQ-006 (Ubiquitous):** *The system shall produce the Copilot MCP configuration such that its
  non-secret parts require no manual editing for the server to be discoverable.*
- **REQ-007 (Unwanted):** *If the MCP configuration would contain a secret value, then the system
  shall not persist it in a version-controlled file (inherits REQ-E5).*
- **REQ-008 (Ubiquitous):** *The system shall document how to verify, from a Copilot client, that the
  `sertor-rag` server is connected and its tools are available.*

### Istruzioni / blocco rituale (capacità `wiki` e `rag`)
- **REQ-009 (Event-driven):** *When installing with the `copilot` target, the system shall deposit
  the Sertor instruction/ritual block(s) into the Copilot repository-wide instruction surface.*
- **REQ-010 (Ubiquitous):** *The system shall delimit each installed instruction block with stable
  markers so that re-installation updates the block in place without duplicating it.*

### Skill, comandi e agenti (capacità `wiki`)
- **REQ-011 (Event-driven):** *When installing the `wiki` capability with the `copilot` target, the
  system shall provide Copilot equivalents of the wiki authoring command surfaces (e.g. the `/wiki`
  consolidation command) invokable from a Copilot client.*
- **REQ-012 (Event-driven):** *When installing the `wiki` capability with the `copilot` target, the
  system shall provide a Copilot custom-agent equivalent of the `wiki-curator` agent (background
  bookkeeping persona).*

### Hook (capacità `wiki` e `rag`)
- **REQ-013 (Event-driven):** *When installing the `wiki` capability with the `copilot` target, the
  system shall provide Copilot hook equivalents of the session-lifecycle wiki reminders
  (record-pending checks at session start/stop).*
- **REQ-014 (Event-driven):** *When installing the `rag` capability with the `copilot` target, the
  system shall provide a Copilot hook equivalent of the Principle-XI usage check (warn on direct
  `sertor_core` use outside vehicles/tests), preserving its non-blocking, fail-open behavior.*
- **REQ-015 (Ubiquitous):** *The system shall keep installed hook scripts cross-platform
  (PowerShell and POSIX shell), consistent with the existing installer assets.*

### Parità, onestà e invarianti
- **REQ-016 (Ubiquitous):** *The system shall expose a documented surface-by-surface mapping between
  the Claude artifacts and their Copilot equivalents for each in-scope capability.*
- **REQ-017 (Unwanted):** *If an in-scope Claude surface has no functional equivalent on the target
  assistant, then the system shall declare the gap explicitly to the user rather than omit it
  silently.*
- **REQ-018 (Event-driven):** *When the setup runs against an existing repository with the `copilot`
  target, the system shall not overwrite user-modified files without explicit confirmation
  (inherits REQ-E6).*
- **REQ-019 (Unwanted):** *If a capability is installed or added for the `copilot` target, then the
  system shall not automatically start RAG ingestion or index creation (inherits REQ-E2).*
- **REQ-020 (Ubiquitous):** *The system shall keep the execution CLIs (`sertor-rag`,
  `sertor-wiki-tools`) assistant-agnostic, introducing no per-assistant CLI variant.*
- **REQ-021 (Optional):** *Where the same surface content is installed for more than one assistant,
  the system shall derive each assistant's artifacts from a single source of truth to prevent
  cross-assistant drift.*

### Codex (Could)
- **REQ-022 (Optional):** *Where the user selects `codex` as target, the system shall deposit an
  `AGENTS.md` instruction surface and register the `sertor-rag` MCP server for Codex.*

## 6. Requisiti non funzionali

- **NFR-1 (Host/assistant-agnostic):** estende il Principio X all'assistente; nessuna capacità del
  core duplicata o modificata — la feature agisce solo a livello di **distribuzione**.
- **NFR-2 (Thin consumer):** riusa il motore di installazione (`sertor-install-kit`); nessuna logica
  di installazione reinventata per Copilot.
- **NFR-3 (Idempotenza & non distruttività):** ogni operazione ripetibile senza danno, per artefatto.
- **NFR-4 (Manutenibilità / no drift):** la parità non deve creare due copie divergenti dello stesso
  contenuto (vedi REQ-021).
- **NFR-5 (Offline / install ≠ run):** l'installazione non richiede rete verso servizi a pagamento e
  non esegue ingestione.
- **NFR-6 (Robustezza alle Preview):** le superfici Copilot usate possono essere in *Preview* e
  cambiare; la feature deve degradare in modo onesto e isolare la dipendenza (vedi DA-3).

## 7. Vincoli, assunzioni e dipendenze

- **Dipendenza:** motore `sertor-install-kit` e asset esistenti del pacchetto `sertor`.
- **Ambito ai soli asset `sertor`** (wiki + rag); `sertor-flow` resta fuori (feature dedicata).

**Grounding verificato (ricognizione Copilot, 2026-06-15) — informa lo scope, NON è design:**
- Hook Copilot: `.github/hooks/*.json`, 8 eventi *con gli stessi nomi di Claude* (`SessionStart`,
  `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`,
  `Stop`); eseguono shell e possono bloccare (`permissionDecision`, exit code 2).
- Istruzioni repo-wide: `.github/copilot-instructions.md`; path-scoped:
  `.github/instructions/*.instructions.md` (`applyTo`).
- Prompt file (slash): `.github/prompts/*.prompt.md`. Custom agent (ex chat mode):
  `.github/agents/*.agent.md` (frontmatter `tools`/`model`/`description`/`hooks`).
- MCP: `.vscode/mcp.json` (chiave radice `servers`), workspace, committabile.
- **Compatibilità col formato Claude:** VS Code Copilot può caricare hook da `.claude/settings.json`
  e leggere `CLAUDE.md`/`AGENTS.md` → **possibile riuso diretto** di parte degli asset Claude
  (leva di design, da spike — vedi DA-2).
- **Assunzione:** il client target è **GitHub Copilot in VS Code** (agent mode). Il *Copilot coding
  agent* lato github.com usa una configurazione hook distinta (da decidere se in ambito — DA-1).

## 8. Rischi

- **R-1 — Superfici in Preview:** gli hook Copilot sono Preview; cambi upstream possono rompere gli
  asset installati (mitiga NFR-6).
- **R-2 — Drift tra assistenti:** mantenere due set di asset diverge col tempo (mitiga REQ-021).
- **R-3 — Parità illusoria:** un equivalente che *esiste* ma non *si comporta* come l'originale
  (mitiga CS-1/REQ-016: verifica comportamentale, non solo presenza del file).
- **R-4 — Frammentazione client Copilot:** VS Code vs coding agent cloud vs altri IDE hanno superfici
  diverse; ambito non chiaro genera scope creep (mitiga DA-1).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001…REQ-020 — selezione assistente, MCP su Copilot, blocco istruzioni, skill/comandi
  wiki, agente wiki-curator, hook wiki + anti-bypass, parità con mappatura, onestà sui gap,
  non distruttività/idempotenza/install≠run, CLI agnostiche. *(Decisione utente 2026-06-15: parità
  piena nel Must.)*
- **Should:** REQ-021 (single source of truth / anti-drift) — fortemente desiderato ma realizzabile
  in modo incrementale; istruzioni path-scoped; MCP a scope utente oltre che workspace.
- **Could:** REQ-022 (Codex); sfruttare la compatibilità nativa col formato `.claude` per ridurre la
  traduzione (DA-2).
- **Won't (per ora):** traduzione governance/SpecKit (`sertor-flow`); PyPI; client Copilot diversi da
  VS Code agent mode.

## 10. Domande aperte

- **DA-1 — Quali client Copilot?** Solo **VS Code agent mode** (assunzione corrente), oppure anche il
  *Copilot coding agent* su github.com (config hook diversa)? Restringe o allarga R-4. *(Raccomandato:
  VS Code agent mode nel primo taglio.)*
- **DA-2 — Riuso vs traduzione.** Spike di design: poiché VS Code Copilot legge `.claude/settings.json`
  e `CLAUDE.md`, conviene **riusare gli asset Claude così come sono** (parità "per compatibilità") o
  **autorizzare asset `.github/*` nativi** (parità "per traduzione")? Incide pesantemente su REQ-021 e
  sul costo. *(Da decidere in `/speckit-plan` con una prova.)*
- **DA-3 — Default e meccanismo di selezione.** `--assistant claude|copilot` con default `claude`?
  auto-detect? multi-target in un'unica esecuzione? È design, ma il *default* è una decisione di
  prodotto da confermare.
- **DA-4 — `/wiki` come prompt file vs custom agent.** Il comando `/wiki` lavora nel flusso
  principale; `wiki-curator` è un subagent. Mappano su prompt file e custom agent rispettivamente —
  da confermare in design che la semantica (background, non bloccante) regga su Copilot.
