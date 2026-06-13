# Research — Igiene e collocazione degli artefatti sull'ospite (feature 016)

**Data**: 2026-06-13 · **Branch**: `016-igiene-radice-host`

Risoluzione dei punti aperti tecnici della spec. Tutto ancorato al codice reale
(`packages/sertor/src/sertor_installer/`, `src/sertor_core/wiki_tools/profile.py`).

---

## D1 — Come gli strumenti trovano `wiki.config.toml` dopo lo spostamento in `wiki/`

**Problema (verificato a terra).** `WikiProfile` risolve **tutti** i path relativi rispetto a
`config_dir`, che di default è `config_path.parent` (`wiki_tools/profile.py:167`). Oggi
`wiki.config.toml` è in radice host → `config_dir` = radice → `root="wiki"` ⇒ `<host>/wiki`,
`source_dirs=["src"]` ⇒ `<host>/src`. **Corretto.**
Se si sposta il file in `wiki/` **senza altri accorgimenti**, `config_dir` diventa `<host>/wiki` →
`root="wiki"` ⇒ `<host>/wiki/wiki` e `source_dirs` ⇒ `<host>/wiki/src`. **Rotto.**

**Decisione: due meccanismi complementari.**

1. **Convenzione esplicita (forma canonica documentata)** — ogni invocazione negli asset usa
   `--config wiki/wiki.config.toml --root .`. Il `--root .` (parametro `root_override` di
   `load_profile`, già esistente, riga 151/167) forza la risoluzione dei path relativi dalla
   **radice host**, lasciando il file fisicamente in `wiki/`. Il valore `root="wiki"` del file
   **non cambia**: cambia solo la sua collocazione.

2. **Auto-discovery nel CLI `sertor-wiki-tools`** (`src/sertor_core/wiki_tools/__main__.py`) — quando
   `--config` è omesso, cerca in ordine: `./wiki.config.toml`, poi `./wiki/wiki.config.toml`. Se la
   config è trovata **sotto `wiki/`** e `--root` non è passato, imposta `root_override` alla CWD
   (radice host), così la risoluzione resta corretta senza flag aggiuntivi.

**Rationale.** (1) soddisfa REQ-302 alla lettera. (2) elimina la fragilità di dover modificare *ogni*
invocazione (decine di esempi in prosa negli asset) e fa funzionare le invocazioni **ad-hoc/umane**
(`sertor-wiki-tools <op>` da radice host) — è ciò che rende vero SC-2 ("senza intervento manuale") e
riduce drasticamente il rischio R-1 (drift di coerenza). L'ordine di ricerca è **generico**
(nessun path di dominio) → Principio X.

**Alternative scartate.**
- *Solo convenzione esplicita*: fragile; ogni esempio in prosa e ogni invocazione umana si rompe.
- *Config con `root="."` + `source_dirs` con `"../src"`*: la risoluzione `config_dir`-relativa
  renderebbe i sorgenti `<host>/wiki/../src`; funziona ma è fragile e illeggibile.
- *Cambiare il default di `root_override` a CWD sempre*: romperebbe la retro-compat del file-unico in
  radice e altri ospiti; troppo invasivo.

**Invariante da testare.** Il file generato resta valido per `load_profile` sia con
`--config wiki/wiki.config.toml --root .` sia via auto-discovery; `root="wiki"` invariato nel
template.

---

## D2 — `.sertor/` unica sede del runtime RAG (REQ-301)

**Stato.** Già realtà dalla feature 015: `install_rag._apply_deps/_apply_env` scrivono sotto
`.sertor/` (progetto uv + `.venv` + `.env`); solo `.mcp.json` e `.gitignore` toccano la radice
(`install_rag.py:102-112`). L'indice e lo store finiscono in `.sertor/` (runtime isolato).

**Decisione.** Nessun codice nuovo: si **conferma e si documenta**, aggiungendo una **guardia di
test** che dopo `build_rag_plan` nessun artefatto scrive in radice oltre `.mcp.json` (solo scope
project) e `.gitignore`. Serve a impedire regressioni future (un nuovo `ArtifactKind` che sbaglia
`target_rel`).

---

## D3 — Meccanismo `--mcp-scope project|local` (REQ-304/305)

**Decisione.** Nuova opzione `--mcp-scope {project,local}` su `install rag`, **default `project`**
(comportamento attuale; il default "vero" resta deciso da `installer-multiutente`).

- **`project`** — invariato: artefatto `MCP_MERGE` → `.mcp.json` in radice (merge additivo,
  `mcp_merge.merge_mcp`).
- **`local`** — **nessun file nel repo**: si registra il server via la CLI del client
  (`claude mcp add-json sertor-rag '<entry>' --scope local`) attraverso il `CommandRunner` già
  iniettabile. A build-time il piano seleziona un nuovo artefatto `MCP_REGISTER` (strategy
  `REGISTER_CLI`) **al posto** di `MCP_MERGE`, così in scope local `.mcp.json` non è nemmeno nel piano.

**Fail-fast (REQ-305).** Prima di registrare: `runner.is_available("claude")`. Se assente, o se il
comando fallisce → `McpRegistrationError` (sottoclasse `SertorError`) con messaggio leggibile **e**
stampa del **comando manuale equivalente**; **nessun** `.mcp.json` scritto in radice (l'artefatto
file non è nel piano). Stesso pattern di `_apply_deps` per `uv`.

**Idempotenza (Principio VI).** In scope local, prima dell'add si interroga
`claude mcp get sertor-rag` (o `list`): presente ⇒ `SKIPPED`; assente ⇒ `add` → `CREATED`. In scope
project l'idempotenza è già garantita da `merge_mcp` (server presente ⇒ skip).

**Rationale.** Riuso del `CommandRunner` → test senza `claude` reale (`FakeCommandRunner`);
delega al client ufficiale invece di editare a mano `~/.claude.json` (formato non contrattualizzato).

**Dettaglio da confermare a runtime.** Il nome esatto dello scope CLI del client: mappiamo "local"
del nostro flag su `--scope local` di Claude Code (voce in `~/.claude.json`, nessun file nel repo).
Il **meccanismo** è indipendente dal nome; verificabile live (come la validazione uvx della 015).

**Alternative scartate.** Scrivere noi `~/.claude.json`: fragile, fuori dal nostro contratto, rischio
di corrompere config personale dell'utente.

---

## D4 — Fix one-shot di Sertor stesso (FR-008)

**Decisione.** Nello **stesso** cambiamento, senza alcun meccanismo di migrazione riusabile:

1. **Asset canonici (fonte di verità)**: `install_wiki._CONFIG_TARGET` → `wiki/wiki.config.toml`;
   `_apply_config` fa `mkdir(parents=True)` del genitore; `_apply_structure` passa
   `root_override=target_root` a `load_profile`. Ordine del piano invariato (CONFIG prima di
   STRUCTURE: il `mkdir` crea `wiki/`).
2. **Asset testuali**: `assets/claude/**`, `claude-md-block.md`, hook `wiki-pending-check.ps1`
   aggiornati alla nuova convenzione (`--config wiki/wiki.config.toml --root .` nelle invocazioni
   reali; prosa "config in `wiki/`"). L'unica invocazione **eseguibile** hard-coded è il hook
   (`$config = Join-Path $root 'wiki/wiki.config.toml'`).
3. **Repo Sertor (dogfood)**: `git mv wiki.config.toml wiki/wiki.config.toml`; ri-sincronizzazione di
   `.claude/` dagli asset (`sync.py` / guardia `test_host_agnostic`); aggiornamento di `CLAUDE.md`
   di radice (esempi `append-log`, blocco rituale) e degli esempi nel playbook in `.claude/`.

**Rationale.** Gli asset package-data sono la **fonte canonica**; `.claude/` è derivato con test di
guardia → toccare entrambi nello stesso commit tiene il guard verde (Principio VI, niente deriva).
L'auto-discovery (D1) copre comunque le invocazioni ad-hoc rimaste senza flag.

**Nota operativa.** Dopo lo spostamento, le invocazioni `sertor-wiki-tools append-log` del rituale
(incluse quelle del flusso principale) funzionano per auto-discovery; la forma esplicita resta quella
documentata.

---

## D5 — Documentazione dei residenti inevitabili a root (REQ-306, mossa #4)

**Decisione.** Sezione in `docs/install.md`: "Cosa resta in radice host e perché" — `.claude/` e
`CLAUDE.md` (letti dal client lì), `wiki/` (documentazione del progetto, by-design), `.gitignore`,
`.sertor/` (runtime isolato) e `.mcp.json` **solo** in scope project (vincolo del client: il
project-scope deve stare in radice). Nessun codice; soddisfa la parte documentale di REQ-306.

---

## Vincoli verificati (dalla spec, ribaditi)

- `.mcp.json` project-scope **deve** stare in radice (vincolo Claude Code) → in scope project resta un
  residente legittimo e documentato; lo scope local è l'unico modo per non averlo nel repo.
- `.claude/`, `CLAUDE.md`, `wiki/` sono residenti inevitabili (client/by-design).
- Retro-compat ospiti esterni **fuori ambito** (D4 requirements): nessun comando di migrazione; un
  file legacy in radice su un vecchio ospite non viene rimosso.
