# Audit degli strumenti Sertor — skill, agent, hook, CLAUDE.md

> **Oggetto:** analisi di buona-formazione e qualità degli asset *first-party* distribuiti da Sertor
> (skill, subagent, hook di lifecycle, blocchi iniettati in `CLAUDE.md`) e del meccanismo di parità
> host-agnostica.
> **Repo analizzato:** `C:\workspace\git\sertor`
> **Metro di giudizio:** spec ufficiale *Agent Skills* + guida `skill-creator` di Anthropic, incrociati
> con il vincolo di parità host-agnostica che Sertor si autoimpone (Definition of Done).
> **Metodo:** lettura integrale dei payload canonici (`packages/*/assets/`), non delle copie
> dogfooded sotto `.claude/`; ogni rilievo è ancorato a `file:riga`.
> **Stato:** documento di analisi + backlog di issue pronte da aprire. Nessun file di Sertor è stato modificato.

---

## 1. Verdetto generale

Sertor è **ben architettato**, sopra la media. In particolare:

- Il **parity guard host-agnostico esiste davvero ed è gated in CI** (su Windows *e* Ubuntu): niente
  `.claude/` letterali, niente slash-command, payload citati per nome, body condiviso con sola
  traduzione del frontmatter. Questo è nettamente migliore del fallimento tipico "parità dichiarata
  ma assente".
- `configuration-manager` (tool-scoping + safety gating) e `wiki-author` (progressive disclosure) sono
  **esemplari** e vanno usati come modello di riferimento interno.
- I 3 blocchi iniettati in `CLAUDE.md` sono **puliti** (0 leak host-specifici) e **idempotenti**
  (marker `START`/`END`, slice-swap in upgrade).

Le debolezze sono **concentrate e sistematiche**: ricorrono con lo stesso pattern, quindi sono
correggibili alla radice.

---

## 2. Temi trasversali (la radice dei problemi)

### ① Descrizioni povere di trigger → *undertriggering* — **impatto più alto**
La `description` è il meccanismo che decide se una skill/agent viene invocato. 4 skill su 5 mettono il
*what/how* ma lasciano il *when* (le frasi-trigger) **nel body**, dove non conta. `requirements` ha la
description **in italiano** e 2 agent (`configuration-manager`, `requirements-analyst`) sono
interamente IT → un main-flow che ragiona in EN li aggancia meno affidabilmente.
**`wiki-author` è l'unica fatta bene** (what + when con frasi-trigger concrete): è il modello.

### ② Fail-loud incoerente con la costituzione ("Fail Loud, Fix the Cause")
- Hook `memory-capture` e path catastrofico di `rag-freshness`: **silent-swallow** totale, zero
  segnale → una rottura dell'archiviazione resta invisibile per settimane.
- Agent (`concierge`, `wiki-curator`, `requirements-analyst`): istruzione "leggi la skill/playbook ed
  esegui" **senza fallback** "se l'asset non è risolvibile → STOP e segnala".

### ③ Portabilità OS e parità Copilot "di superficie"
- Tutti gli hook sono **solo PowerShell**: nessun gemello bash, `pwsh` assunto su mac/Linux **senza
  check né fallback** → off-Windows falliscono in silenzio (gli hook fanno sempre `exit 0`).
- Su Copilot diversi surface sono **inerti** (`memory-capture`, signal di SessionStart sono prompt
  statici, non script): "parity = wiring presente" ≠ feature-equivalente. Onesto nei commenti del
  codice, ma **non comunicato all'utente**.

### ④ Invocazione CLI incoerente — *bug di correttezza*
`wiki-pending-check` fa la cosa giusta (`uv run --project .sertor` + fallback al bare CLI). Ma
`memory-capture` e `rag-freshness` usano **bare `uv run`**, cwd-fragile e contrario al CLAUDE.md →
possono risolvere il progetto/venv sbagliato.

### ⑤ Tool grant over-broad
`Bash` concesso ma **non usato** in `requirements-analyst`; **contraddittorio** in `concierge` (si
dichiara "thin dispatcher, non reimplementare" ma `Bash` gli permette di mutare l'host). Solo
`configuration-manager` fa scoping esemplare (nega `Edit`/`Write`).

### ⑥ Altitude / bloat del contesto always-on
I 3 blocchi `CLAUDE.md` pesano **~13 KB / ~205 righe sempre in contesto**. Il blocco "How to invoke /
Windows note" è **triplicato verbatim** (guided-setup + wiki-playbook + CLAUDE.md). ALL-CAPS pervasivo
e sezioni "What NOT to do" / "Hard boundary" che ripetono regole già dette inline.

### 🔥 Rischio sistemico singolo più grosso
**`rag-freshness.ps1` lancia un `sertor-rag index .` sincrono a OGNI SessionEnd con timeout 15s.** Su
repo non banali l'index non finisce in 15s → l'harness lo uccide a metà, `doctor` non gira, il verdetto
di salute resta stantio: il meccanismo di freshness **si auto-sabota** e costa comunque uno stallo a
ogni chiusura sessione.

---

## 3. Dettaglio per gruppo

### 3.1 Skill (5)

Ranking di buona-formazione (migliore → peggiore):

| # | Skill | Verdetto sintetico |
|---|-------|--------------------|
| 1 | `wiki-author` | **Gold standard.** Frontmatter minimale canonico, progressive disclosure esemplare (SKILL.md 39 righe → playbook → `ops/` on-demand → leaf craft), description con what+when. Nit: manca ToC al `wiki-playbook.md` (295 righe); wikilink orfano `[[assistant-targeting]]`. |
| 2 | `eval-suite-author` | Solida e lean; parità pulita. Description auto-descrittiva ma senza trigger espliciti; paragrafo "Hard boundary" duplicato (132–137 ↔ 24–29). |
| 3 | `guided-setup` | Corretta e disciplinata (consent gate, parità). Ma è la più lunga e ALL-CAPS-heavy; trigger nel body (riga 16) invece che nella description; "What NOT to do" (197–206) ridondante. |
| 4 | `eval-feedback` | Lean e corretta; description la più *mechanism-heavy* e trigger-cieca dei 3 procedurali. Typografia dash ASCII-mangled. |
| 5 | `requirements` | Body ben strutturato, ma description **in italiano** e **senza trigger** (il campo più importante) → ultima per *well-formedness* nonostante buon contenuto. |

**Parità:** tutte e 5 host-agnostic-clean (0 `.claude/` path, 0 slash-command). Gli unici match
`.github/`/`.claude` (guided-setup L98/L100) sono *segnali di host-detection*, simmetrici by design.

### 3.2 Agent (4)

| Agent | Verdetto sintetico |
|-------|--------------------|
| `configuration-manager` | **Standout.** Tool-scoping esemplare (`Bash,Read,Grep,Glob`; `Edit`/`Write` negati e ribaditi nel body), safety gating completo (invarianti su segreti, staging mirato, op distruttive gated). Fix: keyword EN nella description; invariante "mai push diretto su main/master". |
| `wiki-curator` | Ottima self-containment (legge `wiki-playbook.md` come prima azione). Manca fallback "playbook assente → STOP". Surfacing in description delle esclusioni (no lint/reorg/generate/rag-sync/git). |
| `concierge` | Dispatcher a branch singolo, parità esemplare (`--assistant`). `Bash` over-broad/contraddittorio col "thin dispatcher". Aggiungere scope negativo (non per search/index di routine). |
| `requirements-analyst` | Buona adattamento subagent (no Q&A live, ritorna domande aperte). `Bash` **granted-but-unused** → rimuovere. Description IT senza trigger EN. Manca fallback "skill `requirements` non risolvibile → usa la tassonomia inline". |

**Meccanismo di parità (confermato):** a install-time solo il frontmatter è tradotto nella shape
custom-agent di Copilot (`name`/`description`/`tools` preservati, `model` droppato); il **body è
riusato verbatim** (`render_custom_agent`, `surfaces.py:53-74`). Boundary git pulito e non
sovrapposto; layering persona↔skill coerente.

### 3.3 Hook (8) — PowerShell

| Hook | Evento | Note |
|------|--------|------|
| `wiki-session-start` | SessionStart | Più portabile (stdlib). Body **fuori da try/catch** (unico); `Get-ChildItem` senza `-LiteralPath`. |
| `wiki-pending-check` | Stop + SessionEnd | **Best practice CLI** (`uv run --project` + fallback). Ma subprocess sincrono a **ogni** Stop = tassa per-turno. |
| `memory-capture` | SessionEnd | **Bare `uv run`** (`:57`) ≠ `--project` → bug. Silent-swallow totale (zero segnale). |
| `rag-freshness` | SessionEnd | **Rischio sistemico:** `index .` sincrono, timeout 15s troppo basso. Bare `uv run` (`:65,:71`). |
| `rag-freshness-start` | SessionStart | Pulito, file-read only, nessun lavoro a start. |
| `version-check` | SessionEnd | Network egress (GET `/VERSION`) cache 24h, URL pubblico fisso, override env. OK. |
| `version-check-start` | SessionStart | Pulito, zero network a start. |
| `sertor-rag-usage-check` | PreToolUse | Fail-open, stderr-only (corretto per Copilot). Esclusione `\btests?\b` (`:62`) over-broad → falsi negativi (solo su reminder soft). |

**Wiring:** Claude usa `"shell":"powershell"`; Copilot hard-coda `pwsh -File` (`install_rag.py:123`).
**Nessun `.sh` esiste.** `CLAUDE_PROJECT_DIR` (Claude-only) → fallback `hook.cwd`/`.` su Copilot.

### 3.4 Blocchi CLAUDE.md + parità

| Blocco | Marker | Peso | Host-agnostic |
|--------|--------|------|---------------|
| RAG usage | `SERTOR:RAG-USAGE` | 71 righe / ~691 parole / 4,6 KB | Pulito (0 leak) |
| Wiki ritual | `SERTOR:WIKI-RITUAL` | 70 righe / ~712 parole / 4,9 KB | Pulito |
| SDLC | `SERTOR:SDLC-RITUAL` | 64 righe / ~492 parole / 3,4 KB | Pulito |

**Peso always-on combinato: ~205 righe / ~13 KB** (prima di `.specify`/skill).

**Parity guard (reale e in CI):**
- `test_assets_copilot_guard.py` — anti-drift (body Copilot == body Claude).
- `test_assets_copilot_parity.py` — no `.claude/`, no slash-command, no nomi prodotto/modello Claude,
  **reference-closure** (ogni asset citato è un target depositato), con test negativi anti-vacuità.
- `test_assets_cli_invocation.py` — ogni body agent usa `uv run --project .sertor`.
- Girano su windows-latest **e** ubuntu-latest + matrice e2e `{os} × {assistant}`.

**Finding chiave:** il tree `assets/copilot/` contiene **solo `.gitkeep`** (stub vuoti). I payload
Copilot sono **generati a runtime** da `assets/claude/**` via `surfaces.py`. È *by design*, ma lo stub
vuoto è **fuorviante** (implica un tree mantenuto a mano che non esiste).

**Promise vs Reality:** install multi-assistant ✅ reale; body unico host-agnostico ✅ enforced; ciclo
blocchi idempotente ✅; **ma** (a) altitude ~13 KB always-on, (b) stub `copilot/` fuorviante, (c)
"parity = surfaces presenti" sovrastima l'equivalenza funzionale runtime su Copilot (memory/signal
parzialmente inerti).

---

## 4. Roadmap prioritizzata

### 🔴 P0 — alto impatto, subito
1. De-bloccare il re-index a SessionEnd (`rag-freshness`).
2. Trigger phrases in tutte le description + lingua EN (output IT resta regola nel body).
3. Standardizzare `uv run --project <root>/.sertor` con fallback bare-CLI.

### 🟠 P1 — robustezza e onestà
4. Guard `pwsh` / gemello bash / gap dichiarato + flag dei surface Copilot inerti.
5. Fail-loud con breadcrumb negli hook silenziosi + fallback "asset mancante → STOP" negli agent.
6. Tighten tools (`Bash` via da requirements-analyst; riconciliare concierge; invariante push su CM).
7. Tagliare l'altitude dei 3 blocchi + deduplicare il blocco "How to invoke" triplicato.

### 🟡 P2 — pulizia e guard-rail
8. Stile: via ALL-CAPS → imperativo + *why*; eliminare "What NOT to do"/"Hard boundary" ridondanti;
   ToC a `wiki-playbook.md`; risolvere wikilink orfano.
9. Rimuovere/documentare lo stub `assets/copilot/`.
10. Estendere il parity guard a `.ps1`/`.json` + test di budget altitude in CI.

---

## 5. Backlog issue (pronte da aprire)

> Formato pensato per GitHub: titolo *Conventional*, label, contesto, evidenza `file:riga`, modifica
> proposta, criteri di accettazione. Le issue sono indipendenti salvo dove indicato.

### 🔴 P0

#### ISSUE-01 — fix(rag): il re-index sincrono a SessionEnd viene ucciso dal timeout
- **Labels:** `bug`, `rag`, `hooks`, `P0`
- **Contesto:** `rag-freshness.ps1` esegue `sertor-rag index .` in modo sincrono a ogni SessionEnd con
  timeout di wiring 15s. Su repo non banali l'index non termina → process killed → `doctor` non gira →
  `.sertor/.rag-health.json` resta stantio o assente, vanificando il meccanismo di freshness e
  introducendo uno stallo a ogni chiusura sessione.
- **Evidenza:** `…/rag/hooks/rag-freshness.ps1:65` (`index .`), `:71-72` (`doctor`);
  `…/rag/settings.rag-freshness.json:9` (timeout 15s).
- **Fix proposto:** spostare l'indicizzazione in background/async (o gate su un change-check rapido —
  es. mtime/manifest diff) e separare il `doctor` dal re-index; in subordine, alzare il timeout a un
  valore realistico. Mantenere il messaggio fail-loud su `degraded` già presente (`:127`).
- **Accettazione:** una sessione che chiude su un repo grande non subisce stallo > ~1s; `health.json`
  riflette sempre l'ultimo stato anche quando l'index è lungo; nessun process killed nel log.

#### ISSUE-02 — refactor(skills,agents): description trigger-rich e in inglese
- **Labels:** `enhancement`, `skills`, `agents`, `P0`
- **Contesto:** la `description` è il meccanismo di triggering. 4 skill su 5 lasciano le frasi-trigger
  nel body; `requirements` ha la description in IT; `configuration-manager` e `requirements-analyst`
  sono interamente IT → undertriggering da un main-flow EN. `wiki-author` è il modello corretto.
- **Evidenza:** `guided-setup/SKILL.md:3` (trigger nel body a `:16`); `eval-feedback/SKILL.md:3`;
  `eval-suite-author/SKILL.md:3`; `requirements/SKILL.md:3` (IT); `configuration-manager.md:3` (IT);
  `requirements-analyst.md:3` (IT).
- **Fix proposto:** riscrivere ogni `description` in EN, in terza persona, con frasi-trigger concrete
  (what + when), leggermente "pushy". Regola: tutto il "when to use" nella description, non nel body.
  La lingua di **output** (IT) resta imposta dal body dove previsto. Vedi le riscritture proposte
  nell'audit per ciascun asset.
- **Accettazione:** ogni description contiene almeno 3 frasi-trigger; nessuna description in IT; un set
  di query EN realistiche aggancia la skill/agent attesa (verificabile con la description-optimization
  di `skill-creator`).

#### ISSUE-03 — fix(hooks): invocazione CLI standardizzata `uv run --project .sertor`
- **Labels:** `bug`, `hooks`, `rag`, `P0`
- **Contesto:** `memory-capture` e `rag-freshness` usano `uv run` *bare*, cwd-fragile e contrario al
  CLAUDE.md: se la cwd non è la project root con `.sertor` discoverable, risolvono il progetto/venv
  sbagliato o falliscono. `wiki-pending-check` mostra il pattern corretto (`--project` + fallback).
- **Evidenza:** `memory-capture.ps1:57`; `rag-freshness.ps1:65,:71`; pattern corretto in
  `wiki-pending-check.ps1:63-67`.
- **Fix proposto:** usare `uv run --project (Join-Path $root '.sertor') …` con fallback al CLI nel
  venv (`.sertor/.venv/Scripts|bin`) come in `wiki-pending-check`. Non dipendere da `Push-Location` +
  `.`.
- **Accettazione:** gli hook funzionano da una cwd arbitraria; un test verifica l'assenza di `uv run`
  bare negli asset hook.

### 🟠 P1

#### ISSUE-04 — feat(hooks): portabilità OS (`pwsh` guard / gemello bash) + onestà sui surface Copilot inerti
- **Labels:** `enhancement`, `portability`, `hooks`, `copilot`, `P1`
- **Contesto:** tutti gli hook sono `.ps1`; `pwsh` è assunto su mac/Linux senza check né fallback → off-
  Windows falliscono in silenzio (exit 0). Inoltre su Copilot `memory-capture` e i signal SessionStart
  sono inerti, ma "parity" lo nasconde all'utente.
- **Evidenza:** wiring `"shell":"powershell"` (`settings.hooks.json:8`), `_PWSH="pwsh -File"`
  (`install_rag.py:123`); inert: `install_rag.py:142-148, 203-218, 261-278`.
- **Fix proposto:** (a) l'installer verifica `pwsh` su non-Windows e — se assente — emette un gap
  onesto (o si ship un gemello `.sh`); (b) il report d'install / il parity test marca i surface Copilot
  come "wired, runtime-inert (no Copilot adapter)".
- **Accettazione:** install su Linux senza `pwsh` produce un warning esplicito; il report distingue
  surface attivi da inerti.

#### ISSUE-05 — fix(hooks,agents): fail-loud con breadcrumb + fallback "asset mancante → STOP"
- **Labels:** `enhancement`, `reliability`, `hooks`, `agents`, `P1`
- **Contesto:** la costituzione impone "Fail Loud, Fix the Cause", ma `memory-capture` e il path
  catastrofico di `rag-freshness` fanno silent-swallow (zero segnale); 3 agent dicono "leggi la
  skill/playbook ed esegui" senza fallback se l'asset manca.
- **Evidenza:** `memory-capture.ps1:13-16,57-60`; `rag-freshness.ps1:134`; `concierge.md` (read
  `guided-setup`), `wiki-curator.md:12-18` (read playbook), `requirements-analyst.md:13` ("Leggila ed
  eseguila").
- **Fix proposto:** gli hook degradano *e* lasciano una traccia (`.sertor/.last-hook-error` o nota
  stderr); ogni agent aggiunge "se l'asset non è risolvibile → STOP e segnala" (requirements-analyst
  può auto-reggersi sulla tassonomia inline).
- **Accettazione:** una rottura silenziosa lascia una traccia ispezionabile; gli agent non procedono a
  vuoto quando manca la skill/playbook.

#### ISSUE-06 — refactor(agents): tool grant minimi + invariante push allineata alla costituzione
- **Labels:** `enhancement`, `agents`, `security`, `P1`
- **Contesto:** `Bash` è granted-but-unused in `requirements-analyst` e contraddittorio in `concierge`
  (thin dispatcher che però può mutare l'host). `configuration-manager` lista `push` come op di routine
  mentre la costituzione vieta push diretti su default branch.
- **Evidenza:** `requirements-analyst.md` frontmatter `tools`; `concierge.md:4,8-9,27-28`;
  `configuration-manager.md:14`.
- **Fix proposto:** rimuovere `Bash` da `requirements-analyst`; in `concierge` togliere `Bash` (host-
  detection read-only basta) o riconciliare il framing; aggiungere a `configuration-manager`
  l'invariante "mai push diretto su `main`/`master`, branch-first".
- **Accettazione:** ogni tool grant è giustificato da un uso documentato; `configuration-manager` si
  rifiuta di pushare sul default branch senza istruzione esplicita.

#### ISSUE-07 — refactor(claude-md): ridurre l'altitude dei blocchi e deduplicare il blocco "How to invoke"
- **Labels:** `enhancement`, `claude-md`, `docs`, `P1`
- **Contesto:** i 3 blocchi iniettati pesano ~13 KB always-on; il blocco "How to invoke / Windows note"
  è triplicato verbatim (guided-setup, wiki-playbook, CLAUDE.md).
- **Evidenza:** `claude-md-block-rag-usage.md` (71 righe), `claude-md-block.md` (70),
  `claude-md-block-sdlc.md` (64); duplicazione in `guided-setup/SKILL.md:50-75` e nel wiki-playbook.
- **Fix proposto:** ridurre ogni blocco a direttiva breve (~15–20 righe) + pointer a un doc nel repo;
  estrarre il blocco "How to invoke" in un reference condiviso citato per nome.
- **Accettazione:** peso always-on ridotto sensibilmente; nessuna tripla duplicazione; i pointer
  risolvono.

### 🟡 P2

#### ISSUE-08 — chore(skills): pulizia stile (ALL-CAPS, duplicazioni, ToC, wikilink orfano)
- **Labels:** `chore`, `skills`, `docs`, `P2`
- **Contesto:** ALL-CAPS pervasivo dove il rubric preferisce imperativo + *why*; sezioni "What NOT to
  do"/"Hard boundary" che ripetono regole inline; `wiki-playbook.md` (295 righe) senza ToC; wikilink
  orfano `[[assistant-targeting]]`.
- **Evidenza:** `guided-setup/SKILL.md:197-206`; `eval-suite-author/SKILL.md:132-137`;
  `wiki-playbook.md` (no ToC), `wiki-playbook.md:52` (`[[assistant-targeting]]`).
- **Fix proposto:** sostituire ALL-CAPS con imperativo + breve motivazione; convertire i blocchi
  ridondanti in pointer; aggiungere ToC al playbook; risolvere/annotare il wikilink come pagina-wiki
  host, non file bundled.
- **Accettazione:** nessuna sezione duplica regole già date; playbook con ToC; nessun wikilink dangling
  nel bundle.

#### ISSUE-09 — chore(assets): rimuovere o documentare lo stub vuoto `assets/copilot/`
- **Labels:** `chore`, `copilot`, `docs`, `P2`
- **Contesto:** `assets/copilot/**` contiene solo `.gitkeep`; i payload Copilot sono generati a runtime
  da `assets/claude/**`. Lo stub implica un tree mantenuto a mano che non esiste.
- **Evidenza:** `packages/sertor/src/sertor_installer/assets/copilot/{agents,hooks,instructions,prompts}/.gitkeep`;
  generazione in `surfaces.py`.
- **Fix proposto:** rimuovere il tree stub, oppure aggiungere un `README` che dichiari "generato a
  runtime da `surfaces.py`".
- **Accettazione:** nessuna ambiguità sull'origine dei payload Copilot.

#### ISSUE-10 — test(ci): estendere il parity guard a `.ps1`/`.json` + budget di altitude
- **Labels:** `test`, `ci`, `parity`, `P2`
- **Contesto:** il parity guard esclude deliberatamente script/JSON, ma il wiring Copilot ha già avuto
  drift silenzioso; inoltre non c'è un freno alla crescita dei blocchi always-on.
- **Evidenza:** `test_assets_copilot_parity.py:46-58` (scope esclude script); nota drift in
  `surfaces.py:144-184`.
- **Fix proposto:** assert sullo shape del wiring Copilot reso (version/flat-list/`timeoutSec`); test
  di budget che fallisce se un `claude-md-block*.md` supera N righe.
- **Accettazione:** un drift di shape del wiring fallisce in CI; un blocco oltre budget fallisce in CI.

---

## 6. Note di consegna a Sertor

- Questo report è autonomo e spostabile (nessuna dipendenza dal progetto Sinthari).
- Possibili canali verso Sertor: (a) `docs/` nel repo Sertor via PR; (b) apertura delle ISSUE-01..10
  con `gh issue create`; (c) una pagina wiki di Sertor.
- Le issue sono già in forma fileabile: titolo, label, evidenza `file:riga`, fix, accettazione.
