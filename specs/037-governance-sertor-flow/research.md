# Research — `sertor-flow` (installer di governance/SDLC)

Fase 0 del plan. Le 7 domande di scope (DA-a..g) erano già risolte in fase requisiti; qui si
risolvono le **decisioni di design** (il *come*), ancorate al codice reale di `packages/sertor`.

## D1 — Topologia dei pacchetti: estrarre un toolkit condiviso

**Decisione.** Introdurre un **terzo membro del workspace** `packages/sertor-install-kit` (dist
`sertor-install-kit`, modulo `sertor_install_kit`) che ospita il **motore di installazione**
riusabile, **senza dipendenza da `sertor-core`**. `sertor` (wiki/rag) e `sertor-flow` (governance)
dipendono entrambi dal kit; solo `sertor` continua a dipendere da `sertor-core` (per `wiki_tools`).

```
sertor-core ──────────────┐ (RAG: wiki_tools, retrieval)
                          ▼
packages/sertor (sertor) ─┴─► dipende da: sertor-install-kit + sertor-core
packages/sertor-install-kit (sertor-install-kit) ─► dipende da: NIENTE (stdlib)
packages/sertor-flow (sertor-flow) ─► dipende da: sertor-install-kit  (NON sertor-core)
```

**Razionale.** È l'unica topologia che soddisfa REQ-002/NFR-1 (sertor-flow senza core) **e** NFR-2
(no duplicazione del motore). Il secondo consumatore reale (sertor-flow) giustifica l'estrazione
(Principio III: non speculativo).

**Alternative scartate.**
- *sertor-flow dipende da `sertor` (packages/sertor):* tirerebbe `sertor-core` per transitività →
  viola REQ-002.
- *Duplicare il motore in sertor-flow:* viola NFR-2 (DRY).

## D2 — Cosa contiene il toolkit (`sertor_install_kit`) e cosa resta specifico

**Decisione.** Migrano nel kit i pezzi **generici e già core-agnostici nel comportamento**:
- `artifacts.py` — `Artifact`/`ArtifactKind`/`WriteStrategy`/`Outcome` + validazione path-traversal.
- `resources.py` — accesso agli asset via `importlib.resources` (invariato).
- `claude_md.py` — scrittore di blocco a marker (generalizzato, vedi D4).
- `report.py` — `InstallReport`/`ArtifactOutcome`.
- merge primitives: `settings_merge.py`, `env_merge.py`, `mcp_merge.py`, `gitignore_append.py`.
- `command_runner.py` — `CommandRunner` mockabile.
- `errors.py` — **nuova** eccezione base `InstallerError` (vedi D3).
- `observability.py` — **nuovo** helper `log_event` minimale (stdlib `logging`, vedi D3).
- `executor.py` — **generalizzazione** del loop `execute_plan` (vedi D5).
- `sync.py` — helper generico assets→`.claude`/`.specify` (parametrizzato per radici asset).

Restano **specifici di `sertor`** (NON migrano): `install_wiki.py` (usa `sertor_core.wiki_tools`),
`install_rag.py` (bootstrap dipendenze RAG), `config_gen.py` (genera `wiki.config.toml`),
`rag_profile.py`. Restano **nuovi e specifici di `sertor-flow`**: il plan-builder + apply-functions
del bundle governance + il generatore dei file init/integration.

**Razionale.** Il kit è il *meccanismo*; i bundle (wiki/rag/governance) sono le *politiche*. Confine
[[deterministic-vs-judgment]] meccanico: il kit è puro stdlib, testabile senza core.

## D3 — Spezzare la dipendenza da `sertor-core` (errori + logging)

**Contesto reale.** Oggi `sertor_installer` importa da `sertor-core` SOLO:
`ConfigError`/`SertorError` (`sertor_core.domain.errors`) e `log_event`
(`sertor_core.observability.logging`).

**Decisione.**
- Il kit definisce la propria base `InstallerError(Exception)` e `ConfigError(InstallerError)`.
- Il kit definisce un `log_event(level, operation, **fields)` minimale su `logging` stdlib
  (structured extra, nessun segreto), sufficiente a Principio IX senza importare il core.
- **Compatibilità con `sertor` (packages/sertor):** dove `install_wiki` chiama
  `sertor_core.wiki_tools` (che può sollevare `sertor_core.SertorError`), il bridge **avvolge** gli
  errori del core in `InstallerError` al boundary (Principio IV: wrap di terze parti al confine — per
  il kit, `sertor-core` È una terza parte). Così `executor.execute_plan` cattura solo `InstallerError`.

**Razionale.** Mantiene il kit puro e non rompe `sertor`: il wrapping è localizzato nel solo punto
che attraversa il confine kit↔core. Niente duplicazione concettuale rilevante (l'helper di logging è
minimale, non logica di dominio).

**Alternative scartate.** *Lasciare `log_event` nel core e farlo importare dal kit:* re-introdurrebbe
la dipendenza vietata. *Executor generico sul tipo d'eccezione:* over-engineering (YAGNI).

## D4 — Due blocchi `CLAUDE.md` a marker distinti

**Contesto reale.** `claude_md.write_ritual_block` oggi **inchioda** i marker wiki
(`<!-- SERTOR:WIKI-RITUAL START/END -->`), 3 casi (assente→crea / presente-senza-marker→append /
presente-con-marker→skip), preservazione byte-per-byte fuori dai marker.

**Decisione.** Generalizzare la firma a `write_marker_block(path, content, marker_start, marker_end)`.
- `sertor` (wiki) passa i marker WIKI esistenti (comportamento invariato, retro-compatibile).
- `sertor-flow` passa marker **SDLC distinti**: `<!-- SERTOR:SDLC-RITUAL START -->` /
  `<!-- SERTOR:SDLC-RITUAL END -->`.
- I due blocchi coesistono: l'append aggiunge il blocco SDLC dopo l'eventuale blocco wiki, ognuno
  idempotente sui propri marker (DA-b).

**Razionale.** Marker distinti ⇒ idempotenza indipendente, zero collisione. Il blocco SDLC è **owner**
della disciplina git/commit; il blocco wiki vi rimanda (micro-ridondanza accettata, DA-b).

## D5 — Esecutore di piano generalizzato

**Decisione.** Il kit espone `execute_plan(plan, apply) -> InstallReport` dove `apply: Artifact ->
ArtifactOutcome` è fornita dal pacchetto consumatore (chiude su `target_root`/profilo/runner). Loop
**fail-fast no-rollback** invariato: al primo `InstallerError` registra l'esito `ERROR`, imposta il
passo fallito, si ferma; gli artefatti già scritti restano.

**Razionale.** Il loop è identico tra wiki/rag/governance; cambia solo il dispatch per `kind`.
Generalizzare con una callback elimina la duplicazione (NFR-2) senza un framework.

## D6 — Bundle assets di `sertor-flow`

**Decisione.** Layout asset (package-data, letti via `resources.iter_asset_dir`):
```
packages/sertor-flow/src/sertor_flow/assets/
├── claude/
│   ├── skills/speckit-*/…           # VENDOR spec-kit (pinned 0.8.18)
│   ├── skills/speckit-git-*/…       # VENDOR spec-kit
│   ├── skills/requirements/…        # Sertor-authored
│   ├── agents/speckit-*.md          # VENDOR spec-kit
│   ├── agents/requirements-analyst.md     # Sertor-authored
│   └── agents/configuration-manager.md    # Sertor-authored
├── specify/
│   ├── templates/…                  # VENDOR (spec/plan/tasks/checklist/constitution-template)
│   ├── scripts/{bash,powershell}/…  # VENDOR (entrambe le shell, cross-platform)
│   ├── extensions/git/…             # VENDOR
│   └── workflows/…                  # VENDOR
├── init-options.json.tmpl           # generato per-host (D7)
├── integration.json.tmpl            # generato per-host (D7)
├── integrations/*.manifest.json.tmpl
├── constitution-starter.md          # Sertor-authored (D8)
├── claude-md-block-sdlc.md          # Sertor-authored (blocco rituale SDLC, EN)
└── NOTICE / LICENSES/spec-kit-MIT.txt   # attribuzione MIT (REQ-022)
```
Mappatura sull'ospite: `assets/claude/**` → `.claude/**`, `assets/specify/**` → `.specify/**` (entrambi
CREATE_IF_ABSENT per-file), starter costituzione → `.specify/memory/constitution.md` (skip se esiste),
blocco SDLC → `CLAUDE.md` (marker), file init/integration → generati, `NOTICE` → `.specify/NOTICE`.

**Razionale.** Riusa la meccanica `iter_asset_dir`+`CREATE_IF_ABSENT` già provata per il wiki; il
confine vendor/genera/escludi è quello fissato in DA-e.

**Provenienza degli asset (sync/anti-drift).** Gli asset di metodo sono la **copia canonica**; la
dogfood `.claude/`+`.specify/` del repo Sertor è derivata, mantenuta allineata da un guard test
(`sync.py`, modello di `test_assets_sync.py`), **limitato al sottoinsieme governance** (NON gli asset
wiki di `sertor`, NON la costituzione RAG di Sertor). Lo starter costituzione e i `.tmpl` init non hanno
mirror dogfood (sono asset autorati una volta) → esclusi dal guard.

## D7 — File init/integration generati per-host

**Decisione.** `init-options.json`, `integration.json`, `integrations/*.manifest.json` sono **generati**
da template iniettando i valori host-inferiti, come `config_gen.generate_wiki_config` fa per
`wiki.config.toml`. Valori MVP: `ai/integration = claude` (unico assistente supportato ora);
`script = ps|bash` inferito dall'OS (default `ps` su Windows, `bash` altrove), con entrambe le varianti
comunque spedite (D6). `speckit_version` pinnato (0.8.18).

**Razionale.** Coerente con il pattern di generazione già in `config_gen` (Principio VIII: niente
default hardcoded nel corpo, stanno nei template). Host-agnostico (Principio X).

## D8 — Costituzione-starter neutra

**Decisione.** Un asset `constitution-starter.md` Sertor-authored, derivato dalla costituzione di Sertor
v1.1.1 **de-RAGizzata**: include III (YAGNI), IV (errori espliciti), VI (idempotenza/non-distruttività),
VII (leggibilità) + i kernel generali di I (dipendi-verso-le-astrazioni), V (test F.I.R.S.T.),
VIII (config centralizzata), IX (log strutturati) + sezioni Sicurezza/segreti e Governance (branch+PR,
Constitution Check, emendamenti semver); **esclusi II e X** (RAG/mission). Deployato CREATE_IF_ABSENT;
l'ospite lo personalizza con `speckit-constitution`. Base testuale: `constitution-template.md` di
spec-kit (vendored) come scheletro, riempito coi principi generali.

**Razionale.** DA-a: lo starter non è vuoto (vera disciplina ingegneristica) ma non impone il dominio
RAG. Lasciato editabile dall'ospite.

## D9 — Puntatore `sertor install governance`

**Decisione.** In `packages/sertor/src/sertor_installer/__main__.py`, il dispatch del sotto-comando
`governance` (oggi `raise CapabilityNotAvailableError`) emette un **messaggio-puntatore**: la governance
è fornita dal pacchetto separato `sertor-flow`, con l'istruzione d'installazione. Exit code dedicato.
**Nessuna** dipendenza di `sertor` da `sertor-flow` (DA-f).

**Razionale.** Preserva la storia `sertor install <x>` come indizio, senza accoppiare i pacchetti.

## D10 — Console-script e superficie CLI di `sertor-flow`

**Decisione.** `[project.scripts] sertor-flow = "sertor_flow.__main__:main"`. Sotto-comando
`sertor-flow install [--target PATH] [--json]` che deposita l'intero bundle governance (completo,
all-or-nothing — DA-d). Verbi futuri (upgrade/uninstall, selettività) fuori MVP. Install≠run: nessuna
fase SDLC/git/index avviata.

**Razionale.** Specchio del modello `sertor install wiki` (thin consumer del kit), pronto a estendersi.

## Constitution Check (pre-design) — sintesi

Tutti i gate rilevanti PASS (dettaglio in `plan.md`). Niente provider/retrieval (II/V-misure/VIII-param
RAG/IX-embeddings = N/A per questa feature); I soddisfatto perché il *motore* è il kit puro e l'installer
è thin; X è il cuore (host-agnostico). **Nessuna deroga**, Complexity Tracking vuoto.
