# Requisiti — FEAT-029: hook wiki SessionStart host-agnostico (no path hardcoded)

<!-- Deriva da: FEAT-029 dell'epica E10 `debito-tecnico`. BUG confermato (triage 2026-07-22 contro il
     codice a `ec9129c`). Gemella di FEAT-031/032 (correttezza host-facing degli hook wiki). -->

## 1. Contesto e problema (perché)

L'hook host-facing `wiki-session-start.py` (distribuito da `sertor install wiki`, byte-identico
asset↔dogfood) emette la direttiva di caricamento contesto con **path hardcoded**, **non** letti da
`wiki.config.toml`. Difetti confermati (verifica 2026-07-22):

1. **Path hardcoded → viola Principio X.** `wiki-session-start.py:37-47` compone la direttiva con i letterali
   `wiki/syntheses/roadmap.md`, `wiki/index.md`, `wiki/log/<partizione>`; `_latest_log` (`:19-26`) usa
   `root / "wiki" / "log"` hardcoded. Funziona sul dogfood **solo perché** la sua config coincide con i
   letterali; un ospite con `root`/tassonomia diversi (es. `root="docs"`, o senza `syntheses/`) punterebbe a
   path inesistenti → l'agente riceve l'ordine «Read <path che non esiste>».
2. **`structure init` non seeda la roadmap.** `structure.py:72-80` seeda solo `index`+`log`, **non**
   `syntheses/roadmap.md` → un wiki appena inizializzato, alla sessione successiva, apre con **letture
   fallite silenziose** (l'hook ordina «Read roadmap.md» che non esiste).
3. **Il prompt Copilot hardcoda gli stessi path.** `install_wiki.py` (`_copilot_wiki_hook_specs`, il
   `HookEntrySpec` SessionStart `type:"prompt"`) inserisce i letterali `wiki/syntheses/roadmap.md,
   wiki/index.md and the latest file in wiki/log/` → stesso difetto sul secondo assistente.
4. *(Minore)* fallback log: se manca `wiki/log/`, `_latest_log` compone `log.md` → path `wiki/log/log.md`
   invece del piatto pre-rotazione `wiki/log.md`. **Innocuo nel modello a rotazione** (default), ma incoerente.

**Fonte:** handoff Nunzio 2026-07-09 (§2), confermato dalla verifica agente 2026-07-14 e ri-verificato
2026-07-22. La migrazione A-09 (`.ps1`→`.py`) ha portato la logica **invariata** → i difetti sono
sopravvissuti al porting. Host-facing: ogni nuova install `wiki` lo eredita.

Ancoraggio: `requirements/debito-tecnico/epic.md` (FEAT-029). Il pattern config-driven **esiste già** nel
repo: `distill-floor.py` (E10-FEAT-039) legge `root`/`log_dir` da `wiki.config.toml` via `tomllib`
(`_load_wiki_layout`); il campo `[ritual].exec_page` (= `syntheses/roadmap.md` sul dogfood) è già in config
(usato da `ritual-check` FEAT-026). La roadmap **ha già una fonte di config**.

## 2. Obiettivi e criteri di successo

- **OB-1 — Host-agnostico (Principio X):** la direttiva SessionStart è costruita dai valori di
  `wiki.config.toml` (`root`, `index_file`, `log_dir`, `[ritual].exec_page`), non da letterali. *Criterio:*
  su un ospite con `root≠"wiki"` (e/o `exec_page` diverso/assente) la direttiva punta ai path reali di
  quell'ospite, senza letterali `wiki/...`.
- **OB-2 — Nessuna lettura fallita su wiki nuovo:** un wiki appena inizializzato apre senza ordinare
  «Read <file inesistente>». *Criterio:* o `structure init` seeda l'`exec_page` (roadmap), oppure la
  direttiva **degrada** omettendo i file assenti — nessun ordine di lettura verso un path che non esiste.
- **OB-3 — Parità Claude/Copilot:** il fix vale su entrambi gli assistenti (il prompt statico Copilot non
  hardcoda più i path). *Criterio:* nessun letterale `wiki/...` nel prompt Copilot generato quando la config
  dell'ospite differisce.
- **OB-4 — Coerenza fallback log:** il fallback punta al layout corretto per la config (rotazione vs
  single-file). *Criterio:* con `log_dir` configurato il fallback resta nella dir di rotazione; senza, punta
  al log single-file corretto.

## 3. Stakeholder e attori

- **L'agente frontier dell'ospite** (Claude/Copilot) — riceve la direttiva; oggi può ricevere path inesistenti.
- **L'utente/owner di un ospite non-dogfood** (root/tassonomia diversi) — vittima del path hardcoded.
- **Il team Sertor (dogfood)** — non vede il bug perché la sua config coincide coi letterali (teste contaminato).

## 4. Ambito

### In ambito
- **`wiki-session-start.py`** reso config-driven: legge `wiki.config.toml` (via `tomllib`, stdlib, come
  `distill-floor.py`) → `root`, `index_file`, `log_dir`, `[ritual].exec_page`; costruisce la direttiva coi
  path reali; **degrada** (omette una voce) se il file/campo è assente. Reso NATIVO per assistente invariato.
- **`structure.py`**: seed **opzionale** dell'`exec_page` (roadmap) all'`init` se configurato — oppure la
  degradazione dell'hook copre il caso; si sceglie in clarify/plan (vedi DA-1).
- **Prompt Copilot SessionStart** (`install_wiki.py`): costruito dai path della config dell'ospite (a
  install-time il `wiki.config.toml` è generato da `HostProfile`) invece dei letterali.
- **Fallback log** coerente col layout (rotazione/single-file).
- **Guardia** anti-regressione (asset non hardcoda i path; degradazione su file assenti).

### Fuori ambito
- Ridisegno del formato della direttiva SessionStart (resta lo stesso contenuto: roadmap EXEC + index + log).
- Il contenuto della roadmap/EXEC (è responsabilità del flusso principale, non dell'hook).
- Altri hook (già coperti da FEAT-031/032/039).

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous):** *The wiki SessionStart hook shall build its context-load directive from
  `wiki.config.toml` (`root`, `index_file`, `log_dir`, `[ritual].exec_page`), not from hardcoded literals.*
- **REQ-002 (Unwanted):** *If a referenced file/field is absent (no `exec_page` configured, missing
  partition), then the directive shall omit that item rather than order the agent to read a non-existent
  path.*
- **REQ-003 (Ubiquitous):** *On a freshly initialised wiki, the SessionStart directive shall not order a
  read of a file that `structure init` did not create — either by seeding the `exec_page` at init or by the
  degradation of REQ-002.*
- **REQ-004 (Ubiquitous):** *The Copilot SessionStart prompt shall be built from the host's configured paths
  (at install time from the generated `wiki.config.toml`), not from hardcoded `wiki/...` literals — parity
  with Claude.*
- **REQ-005 (Ubiquitous):** *The log fallback shall resolve to the layout implied by the config (rotation
  dir when `log_dir` is set; the single-file log otherwise), not `wiki/log/log.md`.*
- **REQ-006 (Ubiquitous):** *The hook shall remain host-agnostic (no assumption on a specific host's
  structure), stdlib-only, non-blocking (exit 0), consistent with the other portable hooks.*
- **REQ-007 (Ubiquitous):** *A regression guard shall assert the asset builds the directive from config (no
  hardcoded `wiki/...` literals in the emitted directive when the config differs).*

## 6. Requisiti non funzionali

- **NFR-1 (Host-agnostico, Principio X):** nessun path fisso; tutto da config. Test: gira su un ospite con
  `root≠"wiki"` senza modifiche al corpo.
- **NFR-2 (stdlib-only / portabile):** `tomllib` stdlib; nessuna nuova dipendenza; parità Claude/Copilot.
- **NFR-3 (fail-safe):** exit 0 sempre; su config illeggibile, degrada (breadcrumb come gli altri hook),
  non blocca la sessione.
- **NFR-4 (`sertor-core` invariato dove possibile):** il fix è negli **asset** (`packages/sertor`) +
  eventualmente `structure.py` (`sertor_core.wiki_tools`) per il seed roadmap — nessun tocco al motore RAG.

## 7. Vincoli, assunzioni e dipendenze

- **Riuso:** il pattern `_load_wiki_layout` (tomllib) di `distill-floor.py` è il modello; `[ritual].exec_page`
  è la fonte config della roadmap (già presente).
- **Dipendenza — installer & bundle:** asset host-facing (`wiki-session-start.py`) + wiring Copilot in
  `install_wiki.py` → sync bundle (`sertor_installer.sync` + `test_assets_sync`), parità Claude/Copilot.
- **Assunzione:** l'`exec_page` (roadmap) è la pagina da caricare per prima; se non configurata, la direttiva
  la omette (degradazione), non fallisce.

## 8. Rischi

- **R-1 — Copilot prompt statico non può leggere config a runtime.** Mitigazione: costruirlo a **install-time**
  dai path della config generata (`HostProfile`), non a runtime.
- **R-2 — Seed roadmap invasivo.** Un seed automatico di `roadmap.md` potrebbe non essere voluto da ogni
  ospite. Mitigazione: seed **minimale/opzionale**, oppure preferire la degradazione (REQ-002) e lasciare che
  il flusso principale crei la roadmap (come già fa il fallback del rituale). Deciso in clarify (DA-1).
- **R-3 — Drift dogfood↔bundle.** Asset host-facing. Mitigazione: guardia sync + parità.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-006 (config-driven + degradazione + host-agnostico stdlib).
- **Should:** REQ-003 (no lettura fallita su wiki nuovo), REQ-004 (parità Copilot), REQ-007 (guardia).
- **Could:** REQ-005 (coerenza fallback log — minore, innocuo in rotazione).

## 10. Domande aperte

- **DA-1 — Seed roadmap vs degradazione.** [DA CHIARIRE: `structure init` seeda un `roadmap.md` minimale
  (evita la lettura fallita ma impone un file), **oppure** la sola degradazione (REQ-002) + il flusso
  principale/fallback crea la roadmap quando serve? Raccomandazione iniziale: **degradazione** (meno
  invasiva) + seed opzionale solo se `[ritual].seed_exec_page=true`.]
- **DA-2 — Prompt Copilot: install-time build vs generico.** [DA CHIARIRE: costruire il prompt Copilot dai
  path reali a install-time (preciso ma lega il prompt alla config d'install), oppure renderlo generico
  («la roadmap/index/log del wiki») senza path? Un agente preferisce path concreti → install-time build.]
