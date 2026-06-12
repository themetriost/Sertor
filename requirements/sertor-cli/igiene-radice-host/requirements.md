# Requisiti — Igiene e collocazione degli artefatti sull'ospite
<!-- Deriva da: FEAT-002 (Installazione selettiva delle capacità del core su un repo target) -->
<!-- STATO: IN ELABORAZIONE — origine: feedback utente su Kaelen (2026-06-12). -->
<!-- ASSE: DOVE stanno i file (collocazione). ORTOGONALE al modello di ownership mono-utente vs
     enterprise/team, che vive in `installer-multiutente/requirements.md`. -->

> **Asse di questa feature: la COLLOCAZIONE.** Dove vive ogni artefatto dell'installer sull'ospite,
> per una **radice pulita** e **percorsi prevedibili**. È **ortogonale** a *chi* possiede il file
> (team-condiviso vs per-utente): quello è il modello mono/enterprise, feature
> [`installer-multiutente`](../installer-multiutente/requirements.md). Qui si decide solo il *posto*.

---

## 1. Contesto e problema (perché)

Installando le capacità Sertor su un repo ospite reale (Kaelen, 2026-06-12), alcuni artefatti
finiscono **sparsi nella radice** del progetto (`wiki.config.toml`, `.mcp.json`), che l'utente trova
disordinata. Serve una **collocazione decisa e coerente**: ciò che è infrastruttura di tool va
confinato, ciò che resta in radice deve esserci per un motivo (vincolo di client o documentazione).

*Ancora al codice reale (verificato in sessione):*
- **`.sertor/`** è già la dotfolder isolata del runtime RAG (feature 015): progetto Python, `.venv`,
  indice, `.env`.
- **`wiki.config.toml`** oggi è in root; `sertor-wiki-tools` lo trova via `--config` (default
  `./wiki.config.toml`), con path risolti relativi alla cartella del config (`wiki_tools/profile.py`,
  `config_dir = config_path.parent`, `--root` override).
- **`.mcp.json`** (server MCP project-scoped Claude Code): **DEVE** stare in radice (verificato su doc
  ufficiali — non spostabile in `.claude/`, nessun override di percorso). L'unica alternativa "fuori
  dal repo" è lo scope **`local`** (`claude mcp add --scope local` → `~/.claude.json`).
- **`.claude/`, `CLAUDE.md`, `wiki/`** sono **inevitabili a root**: i primi due li legge il client lì,
  `wiki/` è documentazione del progetto by design (DA-7).

## 2. Obiettivi e criteri di successo

- **OB-1 — Radice prevedibile e minima.** In radice host restano solo gli artefatti che *devono*
  starci; il resto è confinato.
  - *SC-1:* dopo l'install, la radice host contiene **solo** `.claude/`, `CLAUDE.md`, `wiki/`,
    `.gitignore` e la dotfolder `.sertor/` — **nessun** altro file di tool sparso.
- **OB-2 — Wiki autocontenuto.** Config e contenuto del wiki vivono nella stessa cartella.
  - *SC-2:* `wiki.config.toml` è in `wiki/` e **tutte** le invocazioni di `sertor-wiki-tools` negli
    asset installati funzionano senza intervento manuale.
- **OB-3 — `.mcp.json` confinabile.** Esiste un modo per non avere `.mcp.json` nella radice.
  - *SC-3:* con lo scope `local`, dopo l'install **non** esiste `<host>/.mcp.json` e il server
    `sertor-rag` è comunque raggiungibile dal client.

## 3. Stakeholder e attori
- **Owner/maintainer (utente):** vuole una radice ordinata sull'ospite.
- **Repository ospite:** il progetto su cui si installa (Python o non-Python).
- **Client MCP (Claude Code):** cerca `.mcp.json` in radice (project) o `~/.claude.json` (local).
- **`sertor-wiki-tools`:** consuma `wiki.config.toml` (via `--config`/`--root`).

## 4. Ambito

### In ambito
- **Collocazione di `wiki.config.toml`** dentro `wiki/` + adeguamento di ogni invocazione
  `sertor-wiki-tools` negli asset (skill, hook, agente) e nella config di Sertor stesso.
- **Conferma di `.sertor/`** come unica sede del runtime RAG (nulla del runtime in radice).
- **Meccanismo di scope MCP** (`--mcp-scope project|local`): *project* scrive/merge `.mcp.json` in
  radice; *local* registra in `~/.claude.json` senza file nel repo. *(Il valore di DEFAULT è deciso
  dal modello mono/enterprise — feature `installer-multiutente`.)*
- **Documentazione** dei residenti inevitabili a root (`.claude/`, `CLAUDE.md`, `wiki/`).

### Fuori ambito
- **Chi possiede/versiona** ogni artefatto (team vs per-utente) e i **default** mono/enterprise →
  feature `installer-multiutente`.
- **Spostare `.mcp.json` in `.claude/`**: impossibile (vincolo Claude Code verificato).
- **Spostare `.claude/`/`CLAUDE.md`/`wiki/`** dalla radice: vincolo di client / by-design.

## 5. Requisiti funzionali (EARS)

- **REQ-301 (Ubiquitous):** *The installer shall keep the entire RAG runtime under `<host>/.sertor/`
  and place no RAG-runtime file in the host root.*
- **REQ-302 (Ubiquitous):** *The installer shall place `wiki.config.toml` inside `wiki/` and shall
  configure every installed `sertor-wiki-tools` invocation (skill, hooks, agent) to locate it
  (`--config wiki/wiki.config.toml --root .`).*
- **REQ-303 (Event-driven):** *When the wiki config location changes, the installed assets and
  Sertor's own configuration shall stay consistent — no invocation left pointing at the old path.*
- **REQ-304 (Optional):** *The `install rag` command shall offer an MCP-scope mechanism: `project`
  writes/merges `<host>/.mcp.json` (root), `local` registers the server in `~/.claude.json` and
  writes no repo file.*
- **REQ-305 (Unwanted):** *If `local` scope is requested but cannot be fulfilled (e.g., the `claude`
  CLI is unavailable), then the installer shall fail-fast with a readable message (and/or print the
  manual command), and shall not silently write a root `.mcp.json`.*
- **REQ-306 (Ubiquitous):** *The installer shall not place any artifact in the host root other than
  the unavoidable ones (`.claude/`, `CLAUDE.md`, `wiki/`, `.gitignore`) and the `.sertor/` dotfolder,
  documenting why each root resident must be there.*
- **REQ-307 (Ubiquitous):** *Generated artifacts shall be host-agnostic (Principle X): no hard-coded
  Sertor paths or domain references.*

## 6. Requisiti non funzionali
- **NFR-1 (coerenza):** stesse convenzioni di report/exit code di `install wiki`/`rag`.
- **NFR-2 (retro-compatibilità):** gli ospiti già installati con `wiki.config.toml` in root non si
  rompono senza un percorso di migrazione esplicito.
- **NFR-3 (testabilità):** la collocazione e l'adeguamento delle invocazioni verificabili senza rete.

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo (verificato):** `.mcp.json` project-scoped è fisso in radice; `.claude/`/`CLAUDE.md`/`wiki/`
  pure (client/by-design).
- **Dipendenza:** estende `packages/sertor/` (install_wiki.py, install_rag.py) e gli asset; tocca le
  invocazioni `sertor-wiki-tools`.
- **Relazione:** fornisce il **meccanismo** di scope MCP; il **default** lo fissa `installer-multiutente`.

## 8. Rischi
- **R-1 — Drift di coerenza** se qualche invocazione resta al vecchio path di `wiki.config.toml` (REQ-303).
- **R-2 — Migrazione** degli ospiti già installati al nuovo layout (NFR-2).
- **R-3 — Local-scope dipende dalla CLI `claude`** (REQ-305).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-301, REQ-302, REQ-303, REQ-306, REQ-307.
- **Should:** REQ-304, REQ-305 (meccanismo scope MCP).
- **Could:** —
- **Won't (qui):** ownership/versioning, default mono/enterprise (→ `installer-multiutente`).

## 10. Decisioni & domande aperte
- **[D1] ✅ `wiki.config.toml` → dentro `wiki/`** (decisione utente 2026-06-12).
- **[D2] ✅ `.sertor/` unica sede del runtime** (confermato, feature 015).
- **[D3] ✅ `.mcp.json`: solo root (project) o fuori-repo (local)** — il meccanismo `--mcp-scope`
  vive qui; il default è di `installer-multiutente`.
- Nessuna domanda aperta di collocazione residua.

---

### Commit proposto (da delegare al configuration-manager)
`docs(requirements): separa igiene-radice-host (collocazione) da installer-multiutente (ownership)`
