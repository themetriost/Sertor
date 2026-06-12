# Requisiti — Modello mono-utente vs enterprise/team (ownership degli artefatti)
<!-- Deriva da: FEAT-002 (sertor-cli) MA ASSORBITA come FEAT-M01 dell'epica `multiutente`. -->
<!-- STATO: ❄️ CONGELATA — è la "fetta-installer" di un tema più ampio (workflow collaborativo). -->

> **⚠️ ASSORBITA NELL'EPICA `multiutente` (2026-06-12).** L'utente ha chiarito che il multiutente è un
> **tema di workflow** (cosa/quando condividere, collaborazione su RAG+wiki), **non** solo
> dell'installer. Questa bozza resta come **input** ed è ora **FEAT-M01** dell'epica
> [`requirements/multiutente/epic.md`](../../multiutente/epic.md). **Non procedere a specify da qui**
> finché l'epica non viene affrontata e decomposta (decisione: in seguito). L'asse **collocazione**
> resta invece pronto e indipendente in [`igiene-radice-host`](../igiene-radice-host/requirements.md).

> **Asse di questa (futura) feature: l'OWNERSHIP.** Chi possiede ogni artefatto prodotto dall'installer — il
> **team** (versionato in git, condiviso) o il **singolo dev** (per-utente/per-macchina). È
> **ortogonale** a *dove* sta il file (collocazione → feature
> [`igiene-radice-host`](../igiene-radice-host/requirements.md)). Il driver è una **modalità**:
> **mono-utente** (default) vs **enterprise/team**, che imposta i *default* di ownership.

---

## 1. Contesto e problema (perché)

Sertor punta a un uso **enterprise e multiutente**: più sviluppatori sullo stesso repo. In quello
scenario la domanda dirimente non è *dove* sta un file, ma **chi lo possiede**: il team (lo versiona
in git, così tutti hanno la stessa cosa) o il singolo dev (sta sulla sua macchina, mai versionato).
Oggi quel confine è **implicito**. Serve renderlo esplicito e governabile da una **modalità**, perché
le scelte giuste cambiano tra un uso **mono-utente** (un dev, tutto privato, massima pulizia) e un uso
**team** (condivisione e riproducibilità).

*Distinzioni ancorate (verificate in sessione):*
- **`.mcp.json`**: scope **project** = file versionato in radice (tutto il team ha lo stesso server);
  scope **local** = `~/.claude.json`, per-utente, niente nel repo. *(Il meccanismo è in
  `igiene-radice-host`; qui si decide il DEFAULT in base alla modalità.)*
- **`.sertor/`** (runtime RAG): contiene cose intrinsecamente **per-macchina** (`.venv`) e
  **per-utente** (`.env`/segreti, indice locale), più `pyproject.toml`+`uv.lock` (potenzialmente
  condivisibili per riproducibilità).
- **`wiki/`** (con la sua config) e **`.claude/`/`CLAUDE.md`**: naturalmente **team-condivisi**
  (versionati col repo).

## 2. Obiettivi e criteri di successo

- **OB-1 — Ownership esplicito e governato da una modalità.** Ogni artefatto è dichiaratamente
  *team-condiviso* o *per-utente*, e la modalità (mono/team) ne imposta i default coerenti.
  - *SC-1:* in modalità **mono**, dopo l'install **0** artefatti del runtime RAG sono tracciati
    (l'intera `.sertor/` è ignorata) e nessun `.mcp.json` è scritto nel repo; in modalità **team**,
    gli artefatti condivisi designati (es. config, eventualmente lockfile) **non** sono ignorati.
- **OB-2 — Onboarding del secondo dev.** Un dev che clona il repo ricostruisce il **proprio** stato
  per-utente senza toccare il condiviso.
  - *SC-2:* su un clone con i condivisi presenti, il re-install produce `created` solo per il
    per-utente e `skipped`/`merged` per il condiviso; **0** modifiche ai file versionati del team.
- **OB-3 — Segreti mai versionati.** Indipendentemente dalla modalità.
  - *SC-3:* nessun valore segreto compare in un file versionato.

## 3. Stakeholder e attori
- **Owner/maintainer (utente):** sceglie la modalità per il progetto/team.
- **Secondo+ sviluppatore:** clona ed esegue l'install per il proprio ambiente.
- **Team/organizzazione enterprise:** vuole tool condivisi, riproducibili, segreti mai versionati.
- **Singolo dev (mono-utente):** vuole massima pulizia, tutto privato.

## 4. Ambito

### In ambito
- **Modalità di installazione** (mono-utente *default* / enterprise-team) che imposta i **default di
  ownership** degli artefatti.
- **Classificazione ownership** (team-condiviso vs per-utente) di ogni artefatto, riflessa nel
  `.gitignore` generato.
- **Default mono-utente**: runtime `.sertor/` interamente per-utente (gitignorato), MCP scope
  `local`, nessun lockfile condiviso.
- **Default team**: artefatti riproducibili/condivisi versionati (config wiki; *opz.*
  `.sertor/pyproject.toml`+`uv.lock`), MCP scope `project`.
- **Onboarding multiutente**: re-install di un secondo dev sicuro e non distruttivo sul condiviso.

### Fuori ambito
- **DOVE** stanno i file (collocazione, radice pulita) → feature `igiene-radice-host`.
- **Implementazione** di uno store remoto condiviso (vedi DA-d) — capacità core, feature dedicata.
- **Vault/SSO** per i segreti: restano nel `.env` per-utente, mai versionati.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Modalità e classificazione
- **REQ-401 (Ubiquitous):** *The installer shall expose an installation mode — mono-user (default) or
  enterprise/team — that sets the ownership defaults of the produced artifacts.*
- **REQ-402 (Ubiquitous):** *The installer shall classify every artifact as team-shared
  (version-controlled) or per-user/per-machine, and the generated `.gitignore` shall reflect that
  classification.*
- **REQ-403 (Unwanted):** *If an artifact contains secrets, then it shall be per-user and never
  version-controlled, in any mode.*

### Gruppo B — Default mono-utente
- **REQ-410 (State-driven):** *While in mono-user mode, the installer shall treat the entire
  `.sertor/` runtime as per-user (the generated `.gitignore` ignores all of `.sertor/`, including
  `pyproject.toml`/`uv.lock`), default the MCP scope to `local`, and share no lockfile.*

### Gruppo C — Default enterprise/team
- **REQ-420 (State-driven):** *While in enterprise/team mode, the installer shall mark the
  reproducible/shared artifacts as team-shared (wiki config; optionally `.sertor/pyproject.toml`
  + `uv.lock` for deterministic environments) and default the MCP scope to `project`.*
- **REQ-421 (Optional):** *Where team mode targets a shared index, the installer shall document (and,
  if enabled, configure) a shared remote vector store instead of per-user local Chroma; the likely
  stores are MongoDB / PGVector on Azure (full enablement is a dedicated feature).*

### Gruppo D — Multiutente: onboarding del secondo dev
- **REQ-430 (Event-driven):** *When the installer runs on a clone that already has the team-shared
  artifacts, it shall (re)build only the per-user artifacts and report the shared ones as
  `skipped`/`merged`, never overwriting them.*
- **REQ-431 (Ubiquitous):** *Re-running the install on a multiuser host shall be idempotent and
  non-destructive on team-shared files (identical shared state, zero duplicates).*
- **REQ-432 (Ubiquitous):** *The per-user setup (env project, `.venv`, `.env` template) shall be
  reconstructable by each developer independently from the shared artifacts.*

## 6. Requisiti non funzionali
- **NFR-1 (sicurezza):** nessun segreto versionato né loggato (qualunque modalità).
- **NFR-2 (riproducibilità):** in team mode, se versionati `pyproject.toml`+`uv.lock`, l'ambiente è
  ricostruibile deterministicamente; in mono mode si accetta la deriva di versioni (mitigata dallo
  stesso `git+url`).
- **NFR-3 (coerenza di superficie):** stesse convenzioni di report/exit code di `install wiki`/`rag`.
- **NFR-4 (host-agnostico, Principio X):** la modalità è una manopola; nessun default hardcoded nel corpo.

## 7. Vincoli, assunzioni e dipendenze
- **Dipendenza:** consuma il **meccanismo** di scope MCP e la **collocazione** definiti in
  `igiene-radice-host`; qui se ne fissano i **default** per modalità.
- **Assunzione:** lo store di default resta Chroma locale per-utente salvo team mode con store condiviso (DA-d).
- **Dipendenza:** estende `packages/sertor/` (install_rag.py, install_wiki.py, config_gen.py).

## 8. Rischi
- **R-1 — Complessità della modalità:** due set di default da mantenere coerenti (test su entrambe).
- **R-2 — Indice per-utente costoso** in team grandi → spinge verso store condiviso (DA-d, fuori ambito impl.).
- **R-3 — Deriva di versioni** in mono mode (NFR-2, accettata).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-401, REQ-402, REQ-403, REQ-410 (mono default = lo scenario attuale dell'utente),
  REQ-430, REQ-431, REQ-432.
- **Should:** REQ-420 (default team).
- **Could:** REQ-421 (store condiviso documentato/abilitato — MongoDB/PGVector).
- **Won't (qui):** implementazione store remoto; vault segreti; collocazione (→ `igiene-radice-host`).

## 10. Decisioni & domande aperte
- **[DA-b] ✅ Default mono-utente = `.sertor/` interamente per-utente/gitignorata** (decisione utente):
  `pyproject.toml`+`uv.lock` privati, nessun lockfile condiviso. Trade-off deriva versioni accettato.
- **[DA-c] ✅ Default MCP scope (mono) = `local`** (decisione utente): radice pulita, registrazione
  per-utente; `project` è il default in **team mode**.
- **[DA-d] ✅ Store condiviso = documentato ora, implementato dopo; candidati MongoDB/PGVector** (non
  Azure AI Search) — feature dedicata legata all'idea roadmap "Adapter VectorStore PGVector/MongoDB".
- **[DA-e] APERTA (design):** forma/nome della modalità (flag `--mode mono|team`? profilo in config?)
  e se la **modalità è per-install o per-progetto** (registrata nella config condivisa così ogni dev
  eredita lo stesso modo). *Da chiarire in specify/clarify.*

---

### Commit proposto (da delegare al configuration-manager)
`docs(requirements): installer-multiutente diventa il puro modello ownership mono↔enterprise (ortogonale alla collocazione)`
