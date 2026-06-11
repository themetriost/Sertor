# Research — Installer `sertor` + `sertor install wiki` (FEAT-012)

**Branch**: `012-sertor-install-wiki` | **Data**: 2026-06-11
**Spec**: [`spec.md`](spec.md) | **Requisiti EARS**: `requirements/sertor-cli/installer/requirements.md`

Phase 0 del workflow `plan`. Risolve gli ignoti del Technical Context e fissa le decisioni di design
chieste dalla spec (DI-1..DI-5 già risolte a monte; qui le decisioni *di design* D1..D8). Ogni
decisione: **Decisione / Razionale / Alternative scartate**, con ancore al repo (`path:lineno`).

> Le DI-* (decisioni di elicitazione) sono già chiuse nei requisiti §10. Questo documento NON le
> riapre: le **realizza** in scelte tecniche concrete e ne deriva ciò che restava marcato "dettaglio
> di design" (struttura del bundle, accesso, formato marker, criterio di dedup, lista cartelle,
> formato report).

---

## D1 — Struttura di packaging del comando `sertor`

**Decisione.** Un **secondo pacchetto Python `sertor`**, distinto da `sertor-core`, che lo dichiara
come dipendenza. Si materializza come **uv workspace a due membri** nello stesso repo:

```
pyproject.toml                 # root: workspace + membro sertor-core (invariato nei contenuti)
src/sertor_core/  src/sertor_mcp/
packages/sertor/
├── pyproject.toml             # pacchetto `sertor`: depends on sertor-core; console-script `sertor`
└── src/sertor_installer/      # codice dell'installer (modulo Python interno)
    └── assets/                # package-data: gli artefatti .claude/* e il template wiki.config
```

Il nome di distribuzione è `sertor`; il package importabile è `sertor_installer` (il nome del
console-script `sertor` ≠ nome del modulo, come già `sertor-rag` → `sertor_core.cli`). Il
console-script è `sertor = "sertor_installer.__main__:main"`.

**Razionale.**
- REQ-100 è esplicito e ripetuto (epica DA-8, spec FR-001, A-1): *"console-script of the `sertor`
  package, distinto da `sertor-core`"*. Rispettarlo alla lettera evita una deroga da giustificare e
  da promuovere in futuro.
- NFR-I-06 (dipendenza verso l'interno) e Principio I: l'installer è un **layer sottile** che
  dipende da `sertor-core` (per `wiki_tools.init_structure`/`load_profile`), mai il contrario. Un
  pacchetto separato rende la dipendenza **fisica**, non solo logica.
- La distribuzione interim (epica DA-4: `uv add git+url`) resta servibile: un uv workspace con due
  membri permette `uv add "git+<url>#subdirectory=packages/sertor"` (o l'editable
  `uv pip install -e packages/sertor`) — la dipendenza `sertor-core` si risolve dal workspace in
  sviluppo e da PyPI/git in futuro. Il design **non preclude** PyPI (A-1).
- Coerenza con la struttura monorepo esistente: i due pacchetti del core (`sertor_core`,
  `sertor_mcp`) sono già nello **stesso** wheel via `[tool.hatch.build.targets.wheel] packages`
  (`pyproject.toml:41-42`). `sertor` è invece un **wheel diverso** perché ha dipendenze e ciclo di
  release propri: tenerlo nel root-wheel di `sertor-core` confonderebbe i due prodotti.

**Alternative scartate.**
- **(b) Modulo `src/sertor_installer/` dentro il wheel `sertor-core`** con console-script `sertor`
  aggiunto a `[project.scripts]` del root. Più semplice (un solo `pyproject`, un solo `uv sync`), ed
  è la via più rapida per il dogfood (`uv add git+url` sul root installa già tutto). **Scartata
  come default** perché contraddice REQ-100 ("pacchetto distinto"): il "pacchetto distinto"
  diventerebbe solo logico, e l'installer (consumatore) finirebbe *dentro* il prodotto-libreria,
  invertendo la direzione della dipendenza dichiarata. *Se* l'effort del workspace risultasse
  sproporzionato in fase `tasks`, (b) resta il fallback documentato — ma con una deroga esplicita a
  REQ-100 da tracciare in Complexity Tracking, e la promozione a pacchetto reale richiederebbe poi
  uno spostamento di modulo + nuovo `pyproject` + ripubblicazione. Si preferisce pagare il costo
  della separazione ora, quando il modulo è piccolo.
- **Pacchetto separato fuori dal monorepo** (repo proprio): scartato — i due prodotti evolvono
  insieme e condividono test di integrazione (SC-008 dogfood); separare i repo aumenterebbe l'attrito
  senza valore in questa fase (la distribuzione pubblica è FEAT-006).

**Conseguenza per `tasks`.** Verificare che `uv` (versione del repo, c'è `uv.lock`) supporti la
sezione `[tool.uv.workspace]`; in caso contrario, i due pacchetti coesistono comunque come progetti
hatchling fratelli e si installano singolarmente in editable. Il `pyproject.toml` di root resta
invariato per `sertor-core`; si **aggiunge** `[tool.uv.workspace] members = ["packages/sertor"]`.

---

## D2 — Bundle degli artefatti (package-data) e sincronia con `.claude/`

**Decisione.** Gli artefatti non-Python (skill, comando, agente, hook, template di config) vivono
come **package-data dentro `packages/sertor/src/sertor_installer/assets/`**, accessibili a runtime
via **`importlib.resources`** (`importlib.resources.files("sertor_installer") / "assets"`). Layout:

```
sertor_installer/assets/
├── claude/
│   ├── skills/wiki-author/{SKILL.md, wiki-playbook.md, *-craft.md, ops/*.md}
│   ├── commands/wiki.md
│   ├── agents/wiki-curator.md
│   └── hooks/wiki-pending-check.ps1
├── settings.hooks.json          # frammento: SOLO le 3 voci hook da mergiare (non un settings completo)
├── claude-md-block.md           # contenuto della sezione step-ritual host-agnostica (dentro i marker)
└── wiki.config.toml.tmpl        # template del profilo, con segnaposti per i valori inferiti
```

**Sincronia con i sorgenti in `.claude/` del repo (rischio drift).** Fonte unica = **gli assets nel
pacchetto**; gli artefatti vivi del repo Sertor in `.claude/` sono **derivati** (generati/copiati
dagli assets), non viceversa. Meccanismo a due livelli:

1. **Script di sync deterministico** (`packages/sertor/scripts/sync-assets.*` o un comando
   `python -m sertor_installer.sync`) che, *in sviluppo*, copia/diffa
   `assets/claude/**` ⇄ `.claude/**` del repo Sertor. Direzione canonica: **assets → .claude**.
2. **Test di guardia** (`tests/unit/test_assets_sync.py`, nella root suite): confronta byte-per-byte ogni file in
   `assets/claude/` con il corrispettivo in `.claude/` (escludendo le parti host-specifiche che il
   repo Sertor aggiunge — vedi D3). Il test **fallisce** se divergono: il drift diventa un errore di
   CI, non una sorpresa al runtime di un ospite.

In questo modo: una correzione a una skill si fa **negli assets**, il sync la propaga al `.claude/`
di Sertor (così il dogfood gira sulla versione installabile), e il test impedisce che le due copie
si separino. Coerente con DI-5 (R-I5): aggiornare gli artefatti = nuova release del pacchetto; in
sviluppo l'editable install legge gli assets dal source tree senza rebuild del wheel.

**Razionale.**
- REQ-115/FR-011 impone package-data nel wheel: offline e coerenza versione-artefatti *by
  construction*. `importlib.resources` è l'API stdlib stabile (≥3.11) per leggere package-data senza
  assunzioni sul layout su disco (funziona sia da editable sia da wheel installato/zipped).
- Il rischio architetturale nuovo è il **drift** tra le due copie degli artefatti (assets nel
  pacchetto vs `.claude/` vivo del repo). Renderlo un **test** (Principio V, F.I.R.S.T.) lo elimina
  alla radice senza introdurre un build-step fragile in fase di packaging.
- Tenere `settings.hooks.json` come **frammento delle sole 3 voci** (non un `settings.json`
  completo) serve il merge additivo di D5: l'installer non possiede l'intero `settings.json`
  dell'ospite, possiede solo le proprie voci.

**Alternative scartate.**
- **Sorgente unica in `.claude/` + symlink verso gli assets.** I symlink non sopravvivono al
  packaging del wheel (sdist/wheel non preservano i link in modo portabile) e rompono su Windows
  senza privilegi (NFR-I-04). Scartata.
- **Copia in fase di build (hatchling build hook) da `.claude/` agli assets.** Inverte la direzione
  canonica (renderebbe `.claude/` la fonte e gli assets un derivato di build), ma `.claude/` di
  Sertor contiene le note "profilo Sertor" (D3) che NON devono finire nel bundle: servirebbe
  comunque una trasformazione, non una copia. Meglio una fonte pulita (assets) + derivato annotato
  (.claude). Scartata come direzione canonica; il sync resta uno script, non un build hook.
- **`pathlib`/`__file__` per localizzare gli assets.** Fragile da wheel zip-safe e in editable;
  `importlib.resources` è l'astrazione corretta. Scartata.

---

## D3 — Host-agnosticità degli artefatti bundlati (FR-009 / Principio X / SC-004)

**Decisione.** Gli assets bundlati sono una **variante ripulita** degli artefatti del repo Sertor:
**zero menzioni di "Sertor", "prototype", percorsi del repo**. Le note didattiche "profilo Sertor"
presenti oggi nei sorgenti del repo (vedi sotto) sono **rimosse o riformulate in modo generico**
negli assets. Non si fa templating al momento dell'install (gli artefatti restano statici): tutta la
specificità dell'ospite passa già da `wiki.config.toml`, che gli artefatti leggono — il bundle è
*già* pulito.

**Stato verificato dei sorgenti (ground truth).** Scansione `Grep` su `.claude/skills/wiki-author/`:
28 occorrenze di `Sertor|prototype|sertor_core|FastAPI|src/sertor` in 6 file. **Tutte** sono
**esempi esplicitamente etichettati "profilo Sertor"** o note di dogfooding, *non* assunzioni
hard-coded nel comportamento:
- `wiki-playbook.md` (12): es. `:31` «sono il **profilo Sertor** usato in dogfooding, **non** leggi
  universali»; `:95` «su Sertor: `prototype/wiki/`»; `:255` «su Sertor: `prototype/`».
- `wiki-craft.md` (9), `page-craft.md` (4), `log-craft.md` (1), `ops/distill.md` (1): idem, sempre
  marcate "(profilo Sertor)".
- `ops/rag-sync.md`: nessuna occorrenza Sertor-coupled (il match veniva da `sertor-wiki-tools`, che
  è il **nome del comando del prodotto**, host-agnostico per costruzione — non un riferimento al
  repo).

Quindi il comportamento è **già** host-agnostico (legge da `wiki.config.toml`, vedi
`SKILL.md:15-17`, `wiki-curator.md:20-23`, `commands/wiki.md:13-15`). Ma SC-004 chiede **zero
riferimenti** verificabili con una scansione: gli **esempi** "profilo Sertor" sono comunque stringhe
"Sertor" che la scansione di accettazione troverebbe.

**Trattamento per file negli assets:**
- **Skill/playbook/craft/ops**: sostituire le note "(profilo Sertor: …)" con formulazioni generiche
  («nel profilo dell'ospite»/«esempio») o rimuoverle dove sono pura aneddotica di dogfooding. La
  procedura resta identica; cambia solo la *resa* degli esempi (lo dice già `page-craft.md:14`:
  «su un altro progetto cambia solo la resa, non i principi»).
- **`wiki-curator.md` / `commands/wiki.md`**: già puliti (i match erano `sertor-wiki-tools`). Resta
  da decidere `uv run` (vedi sotto).
- **`wiki-pending-check.ps1`**: già host-agnostico — usa `$env:CLAUDE_PROJECT_DIR` e
  `wiki.config.toml`, nessun path Sertor (`wiki-pending-check.ps1:30-35`). Da bundlare invariato.
- **`uv run sertor-wiki-tools`**: gli artefatti invocano `uv run sertor-wiki-tools …`. `uv run`
  presume `uv` sull'ospite. **Decisione**: bundlare con `sertor-wiki-tools` **senza** `uv run`
  (assume il console-script installato nell'ambiente attivo, che è garantito da V-1/A-2: il core è
  una dipendenza). Su Sertor il `.claude/` derivato può mantenere `uv run` (il sync lo aggiunge come
  trasformazione del repo, oppure lo si normalizza anche lì). Questo è un punto che il sync (D2)
  tratta come differenza ammessa tra assets e `.claude/` di Sertor.

**Verifica (SC-004).** Test di accettazione: scansione `grep -ri "sertor\b" <ospite>` sugli
artefatti installati (escludendo il **nome del comando** `sertor-wiki-tools`/`sertor-rag`, che è
prodotto, non dominio) → zero match a "Sertor-il-progetto". Il criterio esatto della whitelist (nomi
dei comandi del prodotto) è definito nel contratto del test.

**Razionale.** Principio X non-negoziabile + SC-004 misurabile. Il lavoro è **piccolo** (riformulare
~28 note in 6 file) e va fatto una volta, sugli assets; il test di sync (D2) lo mantiene.

**Alternative scartate.**
- **Templating al momento dell'install** (sostituire segnaposti nelle skill): inutile e rischioso —
  le skill non hanno valori host-specifici da iniettare (tutto passa da `wiki.config.toml` a
  runtime); il templating introdurrebbe un punto di rottura senza beneficio. Scartato. (Il
  templating si applica **solo** a `wiki.config.toml.tmpl`, vedi D7.)
- **Lasciare gli esempi "profilo Sertor" nel bundle**: viola SC-004 alla lettera. Scartato.

---

## D4 — Blocco a marker nel `CLAUDE.md` (FR-014 / REQ-122)

**Decisione.** Formato marker su riga propria, idempotente, posseduto dall'installer:

```
<!-- SERTOR:WIKI-RITUAL START -->
…contenuto della sezione step-ritual host-agnostica (da assets/claude-md-block.md)…
<!-- SERTOR:WIKI-RITUAL END -->
```

Algoritmo di scrittura (idempotente, non-distruttivo):
1. `CLAUDE.md` assente → crealo con il solo blocco (marker + contenuto). Report: *created*.
2. `CLAUDE.md` presente **senza** i marker → **appendi** il blocco in coda (dopo una riga vuota di
   separazione). Tutto il resto del file è intoccato byte-per-byte. Report: *created (block)*.
3. `CLAUDE.md` presente **con** i marker → **non toccare nulla** (anche se l'utente ha modificato il
   contenuto *dentro* i marker). Report: *skipped*. Il re-run non duplica e non sovrascrive.

> Nota: la regola 3 è **conservativa** (skip, non "rewrite del blocco") perché in questo taglio
> l'**upgrade** degli artefatti è fuori ambito (spec Assumptions; requisiti §4 Fuori ambito). Un
> futuro `sertor install wiki --upgrade` potrà riscrivere il *contenuto* dentro i marker lasciando
> intatto l'esterno: il marker è già progettato per consentirlo. La spec FR-014 dice «il blocco non
> si duplica al re-run», non «si aggiorna»: skip soddisfa il requisito.

**Razionale.** I marker su commento HTML/Markdown sono il pattern già usato dal repo
(`<!-- SPECKIT START/END -->` in `CLAUDE.md`, `<!-- EXEC:START/END -->` in roadmap): coerenza e
familiarità. Lo skip-on-present garantisce idempotenza (SC-003) e non-distruttività (SC-002) senza
bisogno di diffare il contenuto interno. Il contenuto del blocco vive negli assets
(`claude-md-block.md`), host-agnostico (nessun path Sertor — punta a `wiki-curator`, `/wiki`,
`wiki.config.toml`, tutti nomi standard).

**Alternative scartate.**
- **Rewrite del contenuto dentro i marker a ogni run** (preservando l'esterno): è il comportamento
  di upgrade, fuori ambito ora; rischia di sovrascrivere modifiche utente *dentro* il blocco.
  Differito a `--upgrade`. Scartata per questo taglio.
- **Marker per-prodotto generico senza namespace** (`<!-- WIKI START -->`): rischio collisione con
  blocchi utente omonimi. Il prefisso `SERTOR:` qualifica la proprietà del blocco; non è un
  riferimento *host-specifico* (è il nome del prodotto che installa), quindi non viola X.

---

## D5 — Merge di `.claude/settings.json` (FR-015 / REQ-122 / DI-2)

**Decisione.** Merge **additivo con deduplicazione per `command`**:
1. Leggi `settings.json` se presente; **assente** → crealo con le 3 voci hook
   (SessionStart/Stop/SessionEnd) dal frammento `assets/settings.hooks.json`.
2. **Presente e JSON valido** → per ciascun evento (`hooks.SessionStart|Stop|SessionEnd`), per
   ciascuna voce hook del frammento: aggiungila **solo se** nessuna voce esistente in
   quell'evento ha lo **stesso `command`** (uguaglianza = stringa `command` identica, criterio DI-2).
   Tutte le voci utente preesistenti restano. Scrittura con `json.dump(indent=2,
   ensure_ascii=False)` preservando le chiavi esistenti (incluso `$schema`).
3. **Presente ma JSON malformato** → **fail-fast**: `ConfigError` con il path del file e la causa;
   **non** riscrivere né toccare il file (edge case spec; REQ-125). Gli artefatti già scritti
   restano (no rollback), report di stato parziale.

**Struttura delle voci hook** (dal frammento, deve combaciare con il formato Claude Code reale —
`.claude/settings.json:3-42`): array `hooks.<evento>` di oggetti `{ "hooks": [ { "type":"command",
"shell":"powershell", … , "command":"…" } ] }`. La dedup confronta il `command` della voce
*innermost*.

**Razionale.** DI-2 risolta = dedup per command (idempotenza SC-003, preserva hook utente SC-002).
JSON non ha marker nativi (DI-2 scarta l'opzione marker), quindi il merge è strutturale. Il
fail-fast su JSON malformato è prescritto dall'edge case della spec e da REQ-125: mai corrompere un
file utente.

**Sfumatura (preservazione formattazione).** `json.load`/`json.dump` **normalizza** la formattazione
(indentazione, ordine non garantito su versioni vecchie — ma 3.11 preserva l'ordine di inserimento).
Questo tecnicamente "tocca" il file anche fuori dalle voci hook (reindenta). **Decisione**: è
accettabile perché (a) `settings.json` è un file di **configurazione strutturata**, non prosa utente
(diverso da `CLAUDE.md`, dove SC-002 "zero byte" è critico); (b) il contenuto **semantico** è
preservato al 100% (nessuna chiave persa/sovrascritta). SC-002 parla di "contenuto utente fuori dai
blocchi gestiti": per un JSON il "blocco gestito" è l'intero documento strutturato, e la garanzia è
*semantica* (nessuna voce persa), non *byte-per-byte*. Documentato nel contratto e nel quickstart.

**Alternative scartate.**
- **Append cieco nell'array** (DI-2 opzione 1): produce duplicati al re-run → viola SC-003. Scartata.
- **Blocco a marker nel JSON** (DI-2 opzione 3): JSON non ammette commenti/marker nativi; fragile.
  Scartata (già in DI-2).
- **Merge byte-preserving con libreria di patch JSON**: over-engineering (YAGNI/Principio III) per
  un guadagno (formattazione byte-identica) non richiesto da alcun requisito. Scartata.

---

## D6 — Portabilità dell'hook PowerShell (NFR-I-04)

**Decisione.** **Bundlare l'hook `.ps1` invariato** e documentare il requisito **PowerShell**
(`pwsh`/`powershell`) come prerequisito dell'esperienza-wiki sull'ospite. **Non** si produce una
variante `sh` in questo taglio.

**Razionale.**
- NFR-I-04 («funziona su Linux e Windows senza modifiche») riguarda **l'installer** (l'operazione di
  copia/merge/struttura su filesystem), che è Python puro e gira ovunque. L'hook `.ps1` è un
  **artefatto installato**, eseguito poi dall'harness Claude Code, non dall'installer: l'installer
  lo **copia** in modo portabile su qualunque OS.
- L'hook è un **thin wrapper** (`wiki-pending-check.ps1:1-12`): delega tutta la logica a
  `sertor-wiki-tools scan --json` (Python, host-agnostico). Riscriverlo in `sh` duplicherebbe il
  wrapper senza valore di prodotto, e Claude Code su Linux supporta comunque `pwsh` come shell di
  hook. La spec/requisiti non chiedono una variante shell.
- Coerenza con il `.claude/settings.json` esistente, che usa `"shell":"powershell"` per tutti gli
  hook (`.claude/settings.json:8,24,36`): le voci mergiate (D5) e l'hook bundlato sono allineati.

**Conseguenza documentata (R residuo).** Su un ospite Linux **senza** `pwsh`, gli hook di sessione
non scattano (il sistema-wiki resta usabile a mano e via `/wiki`; solo i promemoria automatici non
partono). Lo si documenta nel quickstart come prerequisito. Una **variante `sh`/Python** dell'hook è
un **taglio futuro** (annotato come rischio residuo, non blocca SC-1..SC-8: nessun SC dipende
dall'esecuzione dell'hook).

**Alternative scartate.**
- **Variante `sh` dell'hook**: lavoro extra per parità di piattaforma su un artefatto secondario;
  YAGNI finché non c'è un ospite Linux reale che lo richiede. Differita.
- **Hook in Python invocato da settings.json**: cambierebbe il formato delle voci hook e divergerebbe
  dal `.claude/settings.json` di Sertor (drift); rinviato a un futuro consolidamento cross-OS degli
  hook. Differita.

---

## D7 — Euristica `source_dirs` e generazione di `wiki.config.toml` (FR-018/020/021, DI-4)

**Decisione — lista cartelle standard riconosciute** (ordine di controllo, NFR-I-07 documentato):

```
src, lib, app, pkg, packages, docs, doc, tests, test, requirements, specs
```

Algoritmo:
1. `--source-dirs <d1,d2,…>` passato (FR-021) → usa **quelle** (override esplicito), nessuna
   inferenza.
2. Altrimenti, includi le cartelle della lista **effettivamente presenti** come sottocartelle dirette
   del target, nell'ordine sopra.
3. Se **nessuna** è presente → `source_dirs = ["."]` (radice; edge case spec).

**Generazione del file** (`wiki.config.toml.tmpl` + valori inferiti):
- `profile = "code+doc"` (default generico).
- `language` = valore di `--language` (FR-020) altrimenti default **`"en"`** (host-agnostico: non si
  presume l'italiano di Sertor; l'utente lo cambia con `--language`).
- `root = "wiki"`, `index_file = "index.md"`, `log_file = "log.md"`, `log_dir = "log"`.
- `source_dirs` = inferiti/override (sopra).
- `exclude` = lista generica (`.git`, `.venv*`, `venv`, `__pycache__`, cache vari, `node_modules`,
  `.index*`) — **senza** `prototype/` (specifico di Sertor).
- `[[taxonomy]]` = le 5 aree standard (`concepts`, `tech`, `experiments`, `sources`, `syntheses`),
  identiche al profilo di riferimento (`wiki.config.toml:23-46`) — sono **archetipi generali**, non
  specificità Sertor (lo dice `wiki-craft.md:42`).
- `[roles] curator = "wiki-curator"`, `vcs = "configuration-manager"` — riferiscono gli **agenti
  installati per nome installato** (REQ-130). `configuration-manager` è installato? **No** in questo
  taglio (solo `wiki-curator`). **Decisione**: includere `curator = "wiki-curator"`; **omettere**
  `vcs` (o lasciarlo commentato) perché l'installer non porta il `configuration-manager` (fuori
  ambito). Il playbook degenera con grazia se `[roles].vcs` manca (la delega VCS è opzionale,
  `SKILL.md:35-37`).
- `[rag] enabled = false`, `corpus = "wiki"` — **disabilitato di default**: install ≠ run, nessun
  RAG presunto (FR-007/022). L'utente lo abilita con `sertor install rag` (futuro) o a mano.
- `[strings]` = messaggi di default localizzati nella `language` scelta — **decisione**: bundlare
  solo le stringhe **in inglese** nel template, dato che la `language` di default è `en`; se l'utente
  passa `--language it` le stringhe restano in inglese (il *contenuto* localizzato delle stringhe è
  fuori ambito — l'utente le adatta). Documentato.

I valori NON sono hard-coded nel codice dell'installer: stanno nel **template** negli assets
(NFR-I-07, Principio VIII); il codice inietta solo `language` e `source_dirs`.

**Validità (vincolo dal core).** `load_profile` richiede `language` e `root` non vuoti e tassonomia
con ≥1 voce (`profile.py:169-173, 131-132`); `source_dirs` può essere vuoto ma noi garantiamo ≥1
elemento (`["."]` come floor). Il file generato deve quindi **passare `load_profile`** — verificabile
da un test (carica il file generato → nessun `ConfigError`).

**Razionale.** DI-4 = euristica + override. La lista è documentata (NFR-I-07) e generica (Principio
X): nessuna voce è specifica di Sertor (`prototype/` escluso, `.claude/` non incluso di default —
sull'ospite lo aggiunge l'utente se vuole documentare la propria governance). `language` default `en`
evita di sedimentare l'italiano di Sertor.

**Alternative scartate.**
- **`language` default `it`**: copierebbe la specificità di Sertor → viola X. Scartata.
- **Includere `.claude` in `source_dirs`** (come fa Sertor, `wiki.config.toml:14`): è una scelta di
  *dogfooding* (documentare la propria governance), non un default sensato per un ospite generico.
  Scartata dal default; resta possibile via `--source-dirs`.
- **Inferenza più aggressiva** (scan ricorsivo per linguaggio): over-engineering; la lista piatta +
  override copre i casi reali (DI-4). Scartata.

---

## D8 — Contratto del report ed exit code (FR-006/025, REQ-143)

**Decisione.** Report **umano su stdout** (default), una riga per artefatto + riepilogo finale:

```
sertor install wiki — target: /path/to/host
  created  .claude/skills/wiki-author/SKILL.md
  skipped  .claude/skills/wiki-author/wiki-playbook.md (già presente)
  created  .claude/commands/wiki.md
  merged   .claude/settings.json (+3 voci hook)
  block    CLAUDE.md (sezione step-ritual inserita)
  skipped  wiki.config.toml (già presente)
  created  wiki/ (struttura: 6 cartelle, 2 file)
Riepilogo: 12 creati · 3 saltati · 0 conflitti · 0 errori
```

Esiti per artefatto: `created` · `skipped` · `merged` · `block` · `error`. Exit code:
- **0** = nessun artefatto ha prodotto errore (anche se tutto è `skipped` — idempotenza, REQ-143).
- **1** = errore di dominio durante l'install (`SertorError`/`ConfigError`: permessi, JSON malformato,
  target non scrivibile) — fail-fast con report di stato parziale (REQ-125); messaggio su stderr.
- **2** = errore d'uso (argparse: sottocomando ignoto, argomento mancante) — REQ-102.

Allineato al pattern del core (`cli/__main__.py:130-145`, `wiki_tools/__main__.py:169-192`): UTF-8
forzato, `SertorError → stderr + return 1`, argparse → 2. Stub `install rag|governance`: messaggio
«non ancora disponibile» + exit **non-zero** (REQ-104; uso exit 1 via `SertorError` dedicata, es.
`NotImplementedError` di dominio mappata a messaggio).

**`--json` (Could).** Output JSON del report previsto come **Could** (requisiti §9): un array di
`{artifact, path, outcome, detail}` + sommario. Si **predispone** il contratto (data-model lo
definisce) ma l'implementazione `--json` è marcata Should/Could in `tasks`, non bloccante per l'MVP
(US1/US2 funzionano con l'output umano). SC-007 (help) non lo richiede.

**Razionale.** REQ-143/FR-025 chiede un riepilogo su stdout + exit 0 se nessun errore. Il formato
umano è sufficiente per US1/US2/US3; `--json` serve i consumatori automatizzati (agente LLM,
stakeholder §3) ma è Could. Exit code a 3 valori (0/1/2) replica l'esatta convenzione già consegnata
nel core (coerenza, NFR-I-06).

**Alternative scartate.**
- **Solo JSON**: peggiora l'esperienza umana del primo uso (US3 enfatizza messaggi leggibili).
  Scartata come default.
- **Exit code binario (0/1)**: perderebbe la distinzione errore-d'uso vs errore-di-dominio già
  stabilita nel core (`cli/__main__.py` docstring). Scartata.

---

## Sintesi delle decisioni

| ID | Tema | Decisione |
|----|------|-----------|
| D1 | Packaging | Pacchetto `sertor` distinto in uv workspace (`packages/sertor/`, modulo `sertor_installer`), dipende da `sertor-core` |
| D2 | Bundle/sync | Package-data in `sertor_installer/assets/`, accesso `importlib.resources`; fonte = assets, `.claude/` derivato; **test di sync** anti-drift |
| D3 | Host-agnosticità | Assets ripuliti dalle note "profilo Sertor"; nessun templating delle skill; test di scansione SC-004 |
| D4 | Marker CLAUDE.md | `<!-- SERTOR:WIKI-RITUAL START/END -->`; skip-on-present (idempotente, non-distruttivo) |
| D5 | Merge settings.json | Dedup per `command`; JSON malformato → fail-fast; preservazione semantica (non byte) |
| D6 | Hook portabilità | Bundle `.ps1` invariato; `pwsh` prerequisito documentato; variante `sh` = taglio futuro |
| D7 | Config gen | Euristica `source_dirs` su lista documentata; `language` default `en`; template negli assets; passa `load_profile` |
| D8 | Report/exit | Report umano (riga per artefatto + riepilogo); exit 0/1/2; `--json` Could |

**Nessun NEEDS CLARIFICATION residuo.** Le DI-* erano già chiuse; D1..D8 risolvono i punti marcati
"dettaglio di design" nei requisiti. Rischi residui (variante hook Linux, byte-preservation di
settings.json, fallback packaging (b)) sono documentati e non bloccano i Success Criteria.
