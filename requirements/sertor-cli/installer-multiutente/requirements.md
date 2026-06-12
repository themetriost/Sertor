# Requisiti — Installer per ospite multiutente / igiene della radice
<!-- Deriva da: FEAT-002 (Installazione selettiva delle capacità del core su un repo target) -->
<!-- STATO: IN ELABORAZIONE — origine: feedback utente su Kaelen (2026-06-12) + direzione strategica
     "Sertor enterprise e multiutente". Sorella di installer/ (wiki) e install-rag/. -->

> **Riformulazione.** È nata come "non mi piacciono `wiki.config.toml` e `.mcp.json` nella radice",
> ma la direzione **enterprise/multiutente** la trasforma: il problema vero non è estetico, è
> **stabilire quali artefatti dell'installer sono condivisi col team (versionati) e quali sono
> per-utente/per-macchina**, e dare le manopole coerenti. La "radice pulita" diventa un caso
> particolare (opt-in del singolo dev), non l'obiettivo primario.

---

## 1. Contesto e problema (perché)

Installando le capacità Sertor (`install wiki`, `install rag`) su un repo ospite reale (Kaelen,
.NET, 2026-06-12), gli artefatti si distribuiscono tra **radice host** e la dotfolder **`.sertor/`**.
Oggi (feature 012 + 015):
- **`.sertor/`** (isolato, per-utente/per-macchina): progetto Python, `.venv`, indice, `.env`.
- **radice host**: `.mcp.json` (rag), `.claude/` + `CLAUDE.md` + `wiki/` + `wiki.config.toml` (wiki),
  `.gitignore`.

L'utente non gradisce `wiki.config.toml` e `.mcp.json` nella radice. Ma il punto dirimente è un
altro: **Sertor punta a un uso enterprise e multiutente** (più sviluppatori sullo stesso repo). In
quello scenario la domanda "dove sta il file" è subordinata a **"chi possiede quel file: il team
(git) o il singolo dev (la sua macchina)?"**. Oggi quel confine è implicito e non dichiarato.

*Ancora al codice reale (verificato in sessione):*
- **`.mcp.json`** — la doc ufficiale di Claude Code è netta: i server MCP **project-scoped** stanno
  in **`.mcp.json` nella radice**, posizione **non configurabile** (no `.claude/`, nessuna chiave
  `mcpServers` in `settings.json`, nessun override di percorso). Esiste lo scope **`local`**
  (`claude mcp add --scope local`) che registra il server in `~/.claude.json` (home utente): **zero
  file nel repo**, ma config **per-utente** non condivisa. → Per un team, il project-scope versionato
  è la scelta che dà a tutti gli stessi tool; il local-scope è un opt-in del singolo.
- **`wiki.config.toml`** — `sertor-wiki-tools` lo carica via `--config` (default `./wiki.config.toml`)
  e risolve i path **relativi alla cartella del config** (`wiki_tools/profile.py:load_profile`,
  `config_dir = config_path.parent`, con `--root` override). Spostarlo in `wiki/` è fattibile ma
  cambia **ogni** invocazione negli asset dell'installer (skill `wiki-author`, hook, agente
  `wiki-curator`) e, per coerenza, la config di Sertor stesso.
- **`.claude/`, `CLAUDE.md`, `wiki/`** — inevitabili a root: i primi due li legge il client lì; `wiki/`
  è documentazione del progetto **by design** (DA-7), versionata col repo.

## 2. Obiettivi e criteri di successo

- **OB-1 — Confine ownership esplicito.** Ogni artefatto prodotto dall'installer è dichiaratamente
  **condiviso/versionato** o **per-utente/per-macchina**, e il `.gitignore` generato lo riflette.
  - *SC-1:* dopo l'install, eseguendo `git status`/`git check-ignore`, **0** artefatti per-utente
    (`.venv`, `.env`/segreti, indice) risultano tracciati, e gli artefatti condivisi
    (`.mcp.json`/`wiki.config.toml`/`wiki/` salvo scelte) **non** sono ignorati.
- **OB-2 — Onboarding del secondo dev.** Un secondo sviluppatore che clona il repo e ri-esegue
  l'install ricostruisce il **proprio** stato per-utente senza toccare il condiviso.
  - *SC-2:* su un clone con gli artefatti condivisi già presenti, il re-install produce solo
    `created` per il per-utente (`.venv`, `.env` template) e `skipped`/`merged` per il condiviso; **0**
    modifiche ai file versionati del team.
- **OB-3 — Radice più pulita (opt-in).** Esiste un modo per non scrivere `.mcp.json` nella radice.
  - *SC-3:* con l'opzione di scope `local`, dopo l'install **non** esiste `<host>/.mcp.json` e il
    server `sertor-rag` risulta comunque registrato (per quell'utente).
- **OB-4 — Coerenza di collocazione del wiki.** La config del wiki è collocata in modo deciso e
  coerente con la cartella `wiki/`.
  - *SC-4:* tutte le invocazioni di `sertor-wiki-tools` negli asset installati funzionano con la
    collocazione scelta, su un ospite, senza intervento manuale.

## 3. Stakeholder e attori
- **Owner/maintainer (utente):** installa e decide le manopole per il team.
- **Secondo+ sviluppatore del team:** clona il repo, ri-esegue l'install per il proprio ambiente.
- **Team/organizzazione enterprise:** vuole tool condivisi e riproducibili, segreti mai versionati.
- **Repository ospite condiviso (multiutente):** il progetto su cui più dev lavorano.
- **Client MCP (Claude Code):** consuma `.mcp.json` (project) o `~/.claude.json` (local).
- **`sertor-core` / installer (`packages/sertor/`):** dipendenze a monte.

## 4. Ambito

### In ambito
- **Confine versionato↔per-utente** dichiarato per ogni artefatto, riflesso nel `.gitignore` generato.
- **Collocazione di `wiki.config.toml`** (root vs dentro `wiki/`) — decisione + adeguamento degli
  asset che invocano `sertor-wiki-tools`.
- **Opzione di scope per `.mcp.json`** (`--mcp-scope project|local`, default da decidere).
- **Idempotenza/non-distruttività multiutente**: re-install di un secondo dev sicuro sul condiviso.
- **Documentazione** del modello ownership nella guida (`docs/install.md`).

### Fuori ambito
- **Implementazione di uno store remoto condiviso** (Azure AI Search): è capacità del **core** già
  esistente; al più qui se ne **abilita/documenta** l'uso via config (vedi DA-d), non si implementa.
- **Superfici multi-assistente** (Copilot/Codex): è la FEAT-007 dell'epica.
- **Gestione segreti centralizzata** (vault, SSO): fuori dall'MVP; qui i segreti restano nel `.env`
  per-utente, mai versionati.
- **Modifica del fatto che `.claude/`/`CLAUDE.md`/`wiki/` stiano in radice** (vincolo di client/by-design).

## 5. Requisiti funzionali (EARS)

### Gruppo A — Confine ownership (versionato vs per-utente)
- **REQ-301 (Ubiquitous):** *The installer shall classify every artifact it produces as either
  team-shared (version-controlled) or per-user/per-machine, and document the classification.*
- **REQ-302 (Ubiquitous):** *The generated `.gitignore` shall ignore all per-user/per-machine
  artifacts (`.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env`) and shall not ignore the
  team-shared ones that are meant to be committed.*
- **REQ-303 (Unwanted):** *If an artifact contains secrets, then it shall be per-user and never
  version-controlled (no secret value ever written).*

### Gruppo B — Collocazione di `wiki.config.toml`
- **REQ-310 (Optional):** *Where the chosen layout places `wiki.config.toml` inside `wiki/`, the
  installer shall generate it there and configure every installed `sertor-wiki-tools` invocation
  (skill, hooks, agent) to locate it (`--config wiki/wiki.config.toml --root .`).*  *(condizionale a DA-a)*
- **REQ-311 (Ubiquitous):** *The wiki configuration shall be treated as team-shared
  (version-controlled), co-located coherently with the `wiki/` it configures.*
- **REQ-312 (Event-driven):** *When the layout changes, the installed assets and Sertor's own
  configuration shall remain consistent (no invocation left pointing at the old location).*

### Gruppo C — Scope di `.mcp.json`
- **REQ-320 (Ubiquitous):** *The `install rag` command shall accept an option selecting the MCP
  server scope: `project` (writes/merges `<host>/.mcp.json`, team-shared) or `local` (registers the
  server in the user's `~/.claude.json`, no repo file).*
- **REQ-321 (Optional):** *Where scope `local` is selected, the installer shall not create or modify
  `<host>/.mcp.json`, and shall register the `sertor-rag` server for the current user (or emit the
  exact `claude mcp add` command if it cannot do so).*
- **REQ-322 (Ubiquitous):** *The default scope shall be the one chosen in DA-c (recommended:
  `project`, to give the whole team the same tools).*
- **REQ-323 (Unwanted):** *If scope `local` is requested but the Claude CLI / `~/.claude.json`
  mechanism is unavailable, then the installer shall fail-fast with a readable message (and/or print
  the manual command), without silently writing a root `.mcp.json`.*

### Gruppo D — Multiutente: onboarding del secondo dev
- **REQ-330 (Event-driven):** *When the installer runs on a clone that already has the team-shared
  artifacts, it shall (re)build only the per-user artifacts and report the shared ones as
  `skipped`/`merged`, never overwriting them.*
- **REQ-331 (Ubiquitous):** *Re-running the install on a multiuser host shall be idempotent and
  non-destructive on team-shared files (identical shared state, zero duplicates).*
- **REQ-332 (Ubiquitous):** *The per-user setup (env project, `.venv`, `.env` template) shall be
  reconstructable by each developer independently from the shared artifacts.*

## 6. Requisiti non funzionali
- **NFR-1 (host-agnostico, Principio X):** nessun riferimento a percorsi/dominio Sertor negli
  artefatti generati; le manopole stanno in flag/config.
- **NFR-2 (sicurezza):** nessun segreto versionato né loggato; i segreti vivono solo nel `.env`
  per-utente.
- **NFR-3 (coerenza di superficie):** stesse convenzioni di report/exit code di `install wiki`/`rag`.
- **NFR-4 (riproducibilità):** la scelta su `pyproject.toml`/`uv.lock` (DA-b) deve consentire, se
  versionati, un ambiente ricostruibile in modo deterministico dal team.
- **NFR-5 (retro-compatibilità):** gli ospiti già installati (root layout) non devono rompersi senza
  un percorso di migrazione esplicito.

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo (verificato):** `.mcp.json` project-scoped è fisso in radice (Claude Code); l'unica
  alternativa "no file nel repo" è il local-scope (`~/.claude.json`).
- **Vincolo:** `.claude/`, `CLAUDE.md`, `wiki/` restano in radice (client/by-design DA-7).
- **Assunzione:** lo store di default resta Chroma locale (per-utente) salvo scelta DA-d; il core
  supporta già Azure AI Search via config.
- **Dipendenza:** estende `packages/sertor/` (install_wiki.py, install_rag.py, config_gen.py) e gli
  asset; tocca le invocazioni `sertor-wiki-tools` se si sposta la config.

## 8. Rischi
- **R-1 — Drift di coerenza** se si sposta `wiki.config.toml` ma qualche invocazione resta al vecchio
  path (REQ-312).
- **R-2 — Local-scope dipende dalla CLI `claude`**: ambiente senza di essa (REQ-323).
- **R-3 — Indice per-utente costoso** in un team grande (ognuno ricostruisce/embedda): spinge verso
  DA-d (store condiviso) ma è fuori ambito implementativo.
- **R-4 — Migrazione** degli ospiti già installati al nuovo layout (NFR-5).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-301, REQ-302, REQ-303, REQ-330, REQ-331, REQ-332 (il confine ownership + onboarding
  multiutente sono il cuore).
- **Should:** REQ-320, REQ-321, REQ-322, REQ-323 (scope `.mcp.json`); REQ-311.
- **Could:** REQ-310/312 (spostamento `wiki.config.toml` in `wiki/` — dipende da DA-a); abilitazione
  documentata dello store condiviso (DA-d).
- **Won't (qui):** store remoto implementato; vault segreti; superfici multi-assistente.

## 10. Domande aperte (da portare all'utente — bivi veri)
- **[DA-a] Collocazione di `wiki.config.toml`.** Lasciarla in **root** (config standard accanto al
  `wiki/` che governa, come `pyproject.toml`/`tsconfig.json`) oppure spostarla **dentro `wiki/`**
  (cartella autocontenuta, ma cambia ogni invocazione negli asset + la config di Sertor stesso)?
  *Raccomandazione: valutare il rapporto costo/beneficio — il guadagno è 1 file in meno a root, il
  costo è il ripple sugli asset e la migrazione.*
- **[DA-b] `.sertor/pyproject.toml` + `uv.lock`: versionati o per-utente?** Versionarli dà al team un
  **ambiente riproducibile** (stesse versioni di `sertor-core`/extra); tenerli per-utente mantiene la
  radice/`.sertor` più "privata" ma ogni dev risolve da sé. *Raccomandazione (enterprise): versionare
  `pyproject.toml`+`uv.lock` (riproducibilità), gitignorare solo `.venv`/`.index`/`.env`.*
- **[DA-c] Default di `--mcp-scope`.** `project` (versionato, tutto il team ha i tool — coerente con
  enterprise/multiutente) o `local` (radice pulita ma per-utente)? *Raccomandazione: default
  `project`; `local` come opt-in.*
- **[DA-d] Store condiviso per team.** Per un team, l'installer dovrebbe **proporre/abilitare via
  config** uno store **condiviso remoto** (Azure AI Search) invece di Chroma locale per-utente (così
  l'indice si costruisce una volta e non per-dev)? *Raccomandazione: documentarlo come opzione ora,
  implementazione dedicata dopo (è capacità core già esistente).*

---

### Commit proposto (da delegare al configuration-manager)
`docs(requirements): elicita la feature installer-multiutente (ownership versionato↔per-utente, scope MCP, collocazione config)`
