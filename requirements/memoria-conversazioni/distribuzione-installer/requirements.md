# Requisiti — Distribuzione della memoria via installer
<!-- Deriva da: FEAT-009 (epica memoria-conversazioni) -->

## 1. Contesto e problema (perché)

L'MVP della memoria conversazioni è **completo e acceso solo sul dogfood di Sertor**: la cattura
(FEAT-001), la ricerca episodica (FEAT-002), la superficie CLI + l'hook `SessionEnd` (feature 035) e
l'aggancio alla distillazione (FEAT-003) funzionano, ma **vivono dentro il repo di Sertor** —
le manopole sono nel `.env` di sviluppo, l'hook `memory-capture.ps1` e la voce `SessionEnd` stanno in
`.claude/` di Sertor, non negli **asset dell'installer**.

Conseguenza: **un ospite che fa `sertor install rag` non riceve la memoria**. Né le manopole
(`SERTOR_MEMORY` e compagne) compaiono nel template `.env` generato (`env.local.tmpl`/`env.azure.tmpl`
contengono RAG/osservabilità/eval ma **zero memoria**), né l'hook di cattura viene depositato, né
l'agente ospite viene informato che esistono i comandi `sertor-rag memory …`.

Questo viola il corollario **«una feature è completa solo se installabile su un ospite»** (CLAUDE.md,
Principio X): finché la memoria vive solo nel `.claude/`/`.env` di Sertor, è un prototipo, non una
capacità consegnata. La feature **recupera il rinvio A-009 di FEAT-035** (era tracciato solo in
`specs/035-…`, mai promosso a backlog durevole).

Le primitive d'installazione esistono già e sono riusabili: il `sertor-install-kit` e il plan-builder
`install_rag.py` depositano **già** un hook analogo — l'hook PreToolUse `sertor-rag-usage-check.ps1`
(feature 042/044/011) — come `FILE` (byte-copy, create-if-absent) + `SETTINGS_MERGE` (merge dedup che
preserva gli hook utente), instradato per-assistente (Claude `.claude/` ↔ Copilot CLI `.github/`), con
lifecycle inverso (upgrade/uninstall) e `sertor_owned_paths`. Questa feature **rispecchia quel pattern**
per l'hook di cattura memoria e le manopole `.env`.

## 2. Obiettivi e criteri di successo

- **CS-1 (manopole installate):** dopo `sertor install rag` su un ospite pulito, il `.sertor/.env`
  generato contiene **tutte** le manopole memoria di `Settings` (le 8 oggi esistenti), con commenti
  d'uso, e `SERTOR_MEMORY` **disattivata di default** (privacy-by-default).
- **CS-2 (cattura installata):** dopo l'installazione, l'ospite possiede lo script di cattura e la voce
  `SessionEnd` cablata nella configurazione hook dell'assistente scelto, **senza** sovrascrivere hook
  preesistenti dell'utente.
- **CS-3 (agente informato):** dopo l'installazione, le istruzioni host-facing dell'assistente
  menzionano i comandi `sertor-rag memory` (search/list/show/archive) e la loro condizione d'uso
  (`SERTOR_MEMORY` acceso).
- **CS-4 (privacy preservata end-to-end):** su un ospite appena installato e **non** opt-in
  (`SERTOR_MEMORY` non attivata), **nessun** contenuto di conversazione viene persistito e l'hook di
  cattura è un **no-op silenzioso** (exit 0).
- **CS-5 (ciclo di vita completo):** gli artefatti memoria introdotti sono coperti da
  `sertor upgrade` (riallineamento idempotente) e `sertor uninstall` (rimozione pulita), incluse le voci
  `SessionEnd` e lo script; il test invariante `plan ⊆ sertor_owned_paths` resta verde.
- **CS-6 (additività):** su un ospite che **non** opt-in, costo e comportamento del runtime restano
  identici a oggi; nessuna regressione delle capacità wiki/rag già installabili.

## 3. Stakeholder e attori

- **Owner/maintainer dell'ospite:** esegue `sertor install rag`; decide se accendere la memoria.
- **Agente LLM ospite (Claude Code / Copilot CLI):** consumatore dei comandi `sertor-rag memory`;
  sorgente delle conversazioni catturate dall'hook.
- **L'installer `sertor` (epica `sertor-cli`, owner di `sertor install`):** deposita gli artefatti.
- **Il `sertor-install-kit`:** fornisce le primitive riusate (FILE/SETTINGS_MERGE/MERGE_ENV, lifecycle).

## 4. Ambito

### In ambito
- **Manopole memoria nei template `.env`** dell'installer (`env.local.tmpl` **e** `env.azure.tmpl`):
  tutte le manopole memoria di `Settings`, con `SERTOR_MEMORY` off di default e commenti d'uso/privacy.
- **Deposito dello script di cattura** come asset dell'installer (oggi vive solo in `.claude/` di
  Sertor), byte-copy create-if-absent, **riuso identico** del corpo dello script.
- **Cablaggio della voce `SessionEnd`** nella configurazione hook dell'assistente scelto, additivo e
  dedup (preserva gli hook utente), instradato **per-assistente**: Claude (`.claude/settings.json`) e
  Copilot CLI (`.github/hooks/…`, formato nativo).
- **Cenno nel blocco istruzioni host-facing** (il `claude-md-block`/`copilot-instructions`): l'agente
  sa che esistono i comandi `sertor-rag memory` e quando valgono.
- **Copertura del ciclo di vita** (upgrade/uninstall) dei nuovi artefatti, con i rispettivi handler
  inversi e l'estensione di `sertor_owned_paths`.
- **La memoria cavalca `sertor install rag`** (decisione): condivide il runtime `.sertor/`, la CLI
  `sertor-rag` e il `.env`; nessun nuovo comando/capacità d'installazione.

### Fuori ambito
- **Adapter di cattura per assistenti diversi da Claude Code** (Copilot/Codex/…): è **FEAT-008**
  (cattura multi-assistente, Could). Qui l'hook viene **depositato anche su Copilot** per parità e
  forward-compat, ma resta **wiring inerte** finché FEAT-008 non fornisce un adapter che legga i
  transcript di quell'assistente (l'unico adapter oggi è `claude-code`).
- **Nuovo comando `sertor install memory`** (capacità separata): scartato — la memoria dipende dal
  runtime che solo `install rag` crea.
- **Modifiche a `sertor-core`** (porte/servizi/CLI memoria): la capacità esiste già; questa feature
  **distribuisce** ciò che c'è, non lo ridefinisce.
- **Enforcement della retention** (`SERTOR_MEMORY_RETENTION_DAYS` resta un hook non applicato): è
  FEAT-006.
- **Distribuzione della ricerca semantica** sull'archivio: dipende da FEAT-004 (non ancora costruita).

## 5. Requisiti funzionali (EARS)

### Manopole di configurazione (`.env`)
- **REQ-001 (Ubiquitous):** *The rag installer shall include every memory configuration knob defined
  in `Settings` (`SERTOR_MEMORY`, `SERTOR_MEMORY_ADAPTER`, `SERTOR_MEMORY_RETENTION_DAYS`,
  `SERTOR_MEMORY_SCRUB_PATTERNS`, `SERTOR_EPISODIC_LIMIT`, `SERTOR_EPISODIC_SNIPPET_TOKENS`,
  `SERTOR_MEMORY_LIST_LIMIT`, `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`) in the generated `.sertor/.env`.*
- **REQ-002 (Ubiquitous):** *The rag installer shall include the memory knobs in BOTH backend
  templates (`env.local.tmpl` and `env.azure.tmpl`), so they travel regardless of the chosen backend.*
- **REQ-003 (Unwanted, privacy-by-default):** *If the host does not opt in, then the generated `.env`
  shall leave conversation capture disabled (`SERTOR_MEMORY` off/commented), persisting no content.*
- **REQ-004 (Ubiquitous):** *The rag installer shall annotate each memory knob in the template with a
  short usage/privacy comment (purpose, default, and that capture is opt-in).*
- **REQ-005 (Event-driven, additive merge):** *When the target `.sertor/.env` already exists, the
  installer shall add only the missing memory keys without overwriting values the host already set.*

### Trigger di cattura (script + wiring `SessionEnd`)
- **REQ-010 (Ubiquitous):** *The rag installer shall deposit the conversation-capture hook script on
  the host as an installer asset (no longer living only in Sertor's `.claude/`).*
- **REQ-011 (Event-driven, non-destructive):** *When the hook script already exists on the host, the
  installer shall leave it unchanged (create-if-absent).*
- **REQ-012 (Ubiquitous):** *The rag installer shall wire a `SessionEnd` entry that invokes the
  capture hook into the chosen assistant's hook configuration.*
- **REQ-013 (Event-driven, dedup):** *When the assistant's hook configuration already contains other
  user/Sertor hooks, the installer shall add the capture entry additively without removing or
  duplicating existing entries.*
- **REQ-014 (Optional feature, per-assistant routing):** *Where the target assistant is the Copilot
  CLI, the installer shall deposit the capture script and the `SessionEnd` wiring in that assistant's
  native containers and format (`.github/**`), mirroring the existing rag-usage hook routing.*
- **REQ-015 (Ubiquitous, body reuse):** *The rag installer shall reuse the capture script body
  identically across assistants (single source), translating only the container/wiring per assistant.*

### Consapevolezza dell'agente
- **REQ-020 (Ubiquitous):** *The rag installer shall add, to the assistant's host-facing instruction
  surface, a mention of the `sertor-rag memory` read commands (search/list/show) and capture (archive).*
- **REQ-021 (State-driven):** *While conversation capture is disabled, the instruction surface shall
  make clear that the memory commands require enabling `SERTOR_MEMORY`.*

### Privacy & sicurezza
- **REQ-030 (Unwanted):** *If conversation capture is not enabled, then the deposited `SessionEnd`
  hook shall be a silent no-op and shall exit successfully (it must never break session close).*
- **REQ-031 (Ubiquitous):** *The installer shall write no conversation content and no secrets into any
  versioned or deposited artifact (only knob names and comments in the template).*
- **REQ-032 (Ubiquitous):** *The installer shall ensure the memory archive location stays excluded
  from version control (covered by the existing runtime ignores under `.sertor/`).*

### Ciclo di vita (upgrade/uninstall)
- **REQ-040 (Event-driven):** *When `sertor uninstall` runs, the installer shall remove the deposited
  capture script and the `SessionEnd` capture entry it added, preserving any user hooks.*
- **REQ-041 (Event-driven):** *When `sertor upgrade` runs, the installer shall realign the capture
  script and wiring idempotently (no duplicate entries, no overwrite of host `.env` values).*
- **REQ-042 (Ubiquitous):** *The installer shall declare the new memory artifacts in
  `sertor_owned_paths` so the lifecycle obsolete-detection and the `plan ⊆ owned` invariant cover
  them.*
- **REQ-043 (Optional feature):** *Where the host previously installed a different assistant, the
  upgrade obsolete-scan shall remove the other assistant's memory wiring (same cross-assistant rule as
  the rag-usage hook).*

### Host-agnosticità & parità
- **REQ-050 (Ubiquitous):** *The deposited memory knobs and archive shall operate on any host without
  changes to their body; only the capture trigger is assistant-specific (Principio X).*
- **REQ-051 (Ubiquitous):** *The rag installer shall keep the existing wiki/rag installable surfaces
  unchanged (non-regression): the memory artifacts are additive to the rag plan.*

## 6. Requisiti non funzionali

- **RNF-1 (riuso, no nuove dipendenze):** la feature riusa il `sertor-install-kit` e i tipi artefatto
  esistenti (`FILE`/`SETTINGS_MERGE`/`MERGE_ENV`, lifecycle inverso); nessuna nuova dipendenza, nessun
  nuovo `ArtifactKind` se evitabile.
- **RNF-2 (`sertor-core` invariato):** nessuna modifica a `src/sertor_core/` — le modifiche vivono nei
  pacchetti installer (`sertor`/`sertor-install-kit`) e negli asset.
- **RNF-3 (additività):** su ospiti che non opt-in, nessun cambiamento di comportamento/costo del
  runtime; le manopole sono inerti finché `SERTOR_MEMORY` resta off.
- **RNF-4 (idempotenza & non-distruttività):** re-install/upgrade non duplicano voci né sovrascrivono
  valori dell'host; uninstall non tocca artefatti non-Sertor.
- **RNF-5 (verificabilità offline):** install/upgrade/uninstall degli artefatti memoria verificabili
  con i runner mock esistenti, senza rete, su host temporanei (stile suite `test_install_rag_*`).
- **RNF-6 (parità di schema per-assistente):** il wiring Copilot rispetta il formato nativo
  (la guardia di validità-schema offline esistente non deve regredire).

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo — la memoria cavalca `rag`:** gli artefatti memoria sono **appesi al piano di
  `sertor install rag`** (decisione utente); nessun comando d'installazione nuovo. La memoria richiede
  il runtime `.sertor/` e la CLI `sertor-rag` che solo `install rag` crea.
- **Assunzione — gitignore già coperto:** l'archivio `memory.sqlite` vive sotto `<index_dir>` dentro
  `.sertor/` → già escluso dai `RUNTIME_IGNORES` esistenti; nessuna nuova voce `.gitignore`.
- **Assunzione — adapter unico oggi:** l'unico adapter di cattura è `claude-code`; su Copilot il
  wiring depositato è **inerte** finché FEAT-008 non porta un adapter che legga quei transcript.
- **Dipendenza — epica `sertor-cli`:** è l'owner di `sertor install`; i tipi artefatto/lifecycle del
  kit sono il punto d'aggancio.
- **Dipendenza — feature 035/048/042-044-011:** riusa lo stesso meccanismo di deposito hook
  (FILE+SETTINGS_MERGE), lifecycle (048) e routing per-assistente (044/011).

## 8. Rischi

- **R-1 — Wiring Copilot inerte percepito come rotto:** la voce `SessionEnd` su Copilot non cattura
  nulla finché manca l'adapter (FEAT-008). Mitigazione: dichiararlo esplicitamente (gap onesto, mai
  parità non-verificata) nelle note d'installazione e nei commenti.
- **R-2 — Privacy:** depositare cattura su un ospite alza la posta sulla privacy-by-default.
  Mitigazione: `SERTOR_MEMORY` off di default + hook no-op + scrub già nel core + REQ-030/031.
- **R-3 — Collisione hook `SessionEnd`:** un ospite con un proprio `SessionEnd` non deve perderlo.
  Mitigazione: merge dedup additivo (REQ-013), come l'hook rag-usage.
- **R-4 — Drift template ↔ Settings:** nuove manopole memoria in `Settings` non riflesse nei template.
  Mitigazione: nota di completamento/test di copertura knob↔template (come `configure`).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001..005 (manopole `.env`), REQ-010..013 (script + wiring Claude), REQ-020..021
  (consapevolezza agente), REQ-030..032 (privacy), REQ-040..042 (lifecycle), REQ-050..051
  (host-agnostico/non-regressione).
- **Should:** REQ-014..015 (deposito + routing Copilot CLI — deciso in ambito), REQ-043 (obsolete
  cross-assistente), RNF-6 (parità schema Copilot).
- **Could:** test di copertura knob↔template anti-drift (R-4) come guardia esplicita.
- **Won't (qui):** adapter di cattura Copilot/Codex (FEAT-008); enforcement retention (FEAT-006);
  distribuzione ricerca semantica (FEAT-004); comando `sertor install memory` separato.

## 10. Domande aperte

- **DA-a — Forma del cenno nelle istruzioni:** il cenno ai comandi `sertor-rag memory` (REQ-020) va
  in un **blocco a marker dedicato** (`SERTOR:MEMORY-USAGE`) o come **poche righe nel blocco
  `SERTOR:RAG-USAGE` esistente**? Default proposto (design): righe nel blocco RAG-usage (un solo
  marker, meno superficie), salvo che il contenuto cresca. [DA CHIARIRE in design]
- **DA-b — Parametro `-Assistant` sull'hook di cattura:** l'hook rag-usage usa `-Assistant copilot`
  per rendere il contratto nativo; l'hook di cattura oggi esce sempre 0 senza output. Serve un
  parametro analogo per il `SessionEnd` Copilot, o lo stesso corpo basta su entrambi? [DA CHIARIRE in
  design]
- **DA-c — Nuovo `ArtifactKind` o riuso `FILE`/`SETTINGS_MERGE`:** verificare in design che il
  deposito dell'hook memoria riusi i tipi esistenti senza introdurne di nuovi (RNF-1). [DA CHIARIRE in
  design]
