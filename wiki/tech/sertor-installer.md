---
title: sertor — l'installer (pacchetto e comando)
type: tech
tags: [installer, cli, wiki, package-data, host-agnostico, produzione]
created: 2026-06-11
updated: 2026-06-13 (+ igiene radice host, feature 016: config in `wiki/`, auto-discovery, `--mcp-scope`)
sources: ["packages/sertor/", "specs/012-sertor-install-wiki/", "specs/015-sertor-install-rag/", "specs/016-igiene-radice-host/", "requirements/sertor-cli/installer/requirements.md", "requirements/sertor-cli/install-rag/requirements.md", "requirements/sertor-cli/igiene-radice-host/requirements.md"]
---

# `sertor` — l'installer

Il **veicolo d'installazione** delle capacità Sertor su un repository ospite (DA-8: `sertor` è
riservato all'install con verbo esplicito; l'esecuzione vive in [[sertor-rag-cli]] e
[[wiki-tools]]). Consegnato con la feature 012 (`specs/012-sertor-install-wiki`, PR #22,
2026-06-11). È un **pacchetto distinto** da `sertor-core` — `packages/sertor/`, modulo
`sertor_installer`, in **uv workspace** col core — perché ha ciclo di release proprio e dipende dal
core senza esserne parte (Principio I).

## Cosa fa `sertor install wiki`

Porta sull'ospite l'intero sistema-wiki con un comando, **senza mai eseguire** indicizzazioni, LLM
o rete (install ≠ run):

| Artefatto | Strategia se esiste già |
|---|---|
| Skill wiki-author (14 file) + `/wiki` + agente wiki-curator + hook di sessione | skip **file-per-file** |
| Voci hook in `.claude/settings.json` | **merge con dedup per `command`** (hook utente preservati; JSON malformato → fail-fast, mai riscritto) |
| Rituale di step nel `CLAUDE.md` | blocco a marker `SERTOR:WIKI-RITUAL`, byte-identico fuori dai marker |
| `wiki/wiki.config.toml` (in `wiki/`, **non** in radice — feature 016) | generato (euristica `source_dirs` su cartelle standard, `language` default `en`, `--language`/`--source-dirs` per override); mai sovrascritto |
| Struttura `wiki/` | `structure init` del nucleo deterministico (idempotente) |

Report per artefatto (`created`/`skipped`/`merged`/`block`/`error`, anche `--json`,
schema `install.report/1`); exit 0/1/2; **fail-fast senza rollback** (il re-run completa i buchi);
idempotente per costruzione. Resta stub: `install governance` (`install rag` consegnato, vedi sotto).

## Cosa fa `sertor install rag` (feature 015, 2026-06-12)

Porta la **capacità RAG** su un ospite — anche **non-Python** (es. .NET) — con un comando, sempre
**install ≠ run** (nessuna indicizzazione automatica: `uv add` è ammesso, `index` no). Riusa il
backbone di `install wiki` (`Artifact`/`Outcome`/`InstallReport`, `build_plan`→`execute_plan`
fail-fast no-rollback) con **4 nuovi `ArtifactKind`** e una porta `CommandRunner` iniettabile che
isola `uv` (testabile senza rete). Decisione di collocazione: il **runtime vive isolato in
`<host>/.sertor/`**, solo `.mcp.json` e `.gitignore` toccano la radice host.

| Artefatto | Dove | Strategia |
|---|---|---|
| Progetto Python + dipendenze (`uv init --bare --name sertor-runtime` + `uv add sertor-core[azure,mcp,graph,rerank] @ git+url`) | `.sertor/` | idempotente (`uv add` no-op; `init` saltato se già fatto); `--no-deps` salta il passo |
| `.env` (template per backend, **segreti vuoti**, `SERTOR_EXCLUDE_PATTERNS` con `.sertor`) | `.sertor/.env` | merge additivo per-chiave (mai sovrascrive); `.sertor` garantito negli excludes |
| `.mcp.json` (server `sertor-rag` via `uv run --directory .sertor`) | **radice host** | merge additivo (preserva gli altri server MCP) |
| `.gitignore` (`.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env`) | **radice host** | append dedup |

Flag: `--backend azure|local`, `--corpus` (default = nome dir sanitizzato), `--no-graph`/`--no-rerank`
(opt-out, "metti tutto" di default), `--no-deps`, `--json`. I sorgenti dell'host **non vengono
"pythonizzati"**; disinstallare ≈ cancellare `.sertor/`. Lo stesso ambiente `.sertor/` fa girare
`sertor-rag` e `sertor-wiki-tools`. Il server/CLI girano con cwd `.sertor/` → caricano `.sertor/.env`
e tengono indice/grafo dentro `.sertor/`.

**Finding di distribuzione (lezione).** L'ipotesi dei requirements — che `sertor` standalone cercasse
`sertor-core` su PyPI e fallisse — era **errata**: `uvx --from "git+…#subdirectory=packages/sertor"`
**scopre il workspace dal checkout git** e costruisce `sertor-core` dallo stesso repo, nessun fix
necessario. Il fix ipotizzato (`[tool.uv.sources]` git nel member) è anzi **rifiutato** da uv
("Workspace members must be declared as workspace sources") e rompe il dev → **revocato**.
*Un'assunzione su un tool esterno va verificata empiricamente prima di scolpirla in un requisito.*

**Validazione live (2026-06-12).** `uvx … sertor install rag --backend azure` su un repo reale
(Kaelen, .NET) → poi `sertor-rag index ..` ha indicizzato **150 doc / 1755 chunk** con Azure
`text-embedding-3-large`. Bug reale trovato live e fixato (`uv init` rifiuta `.sertor` come package
name → `--name sertor-runtime`). 76 test del pacchetto (38 nuovi) + 321 root verdi; **zero modifiche
al core**. Lavorato su `master` (bugfix autorizzato), non via PR.

## Igiene radice host (feature 016, 2026-06-13)

L'asse **DOVE**: radice ospite **minima e prevedibile**. Tre mosse + doc, distinte dall'asse CHI
(ownership/multiutente, differito).

- **`wiki.config.toml` → `wiki/`.** Non più sparso in radice: vive accanto al contenuto del wiki.
  `install_wiki._CONFIG_TARGET = "wiki/wiki.config.toml"` (mkdir del genitore; `_apply_structure`
  passa `root_override=target_root`). Il valore `root="wiki"` del file **non cambia**: resta relativo
  alla radice ospite.
- **Auto-discovery del `--config`** nel CLI [[wiki-tools|`sertor-wiki-tools`]] (`wiki_tools/__main__`):
  se `--config` è omesso cerca `./wiki.config.toml` poi `./wiki/wiki.config.toml` (in quest'ultimo
  caso `root`=CWD). Così le invocazioni *ad-hoc* e gli esempi non si rompono dopo lo spostamento —
  è ciò che rende vero "le invocazioni funzionano senza intervento manuale" e abbatte il rischio di
  drift. Forma canonica esplicita equivalente: `--config wiki/wiki.config.toml --root .`.
- **`--mcp-scope project|local`** su `install rag` (5° `ArtifactKind`: `MCP_REGISTER`). `project`
  (default) = `.mcp.json` in radice (comportamento attuale); `local` = registra il server nel client
  via `claude mcp add-json … --scope local` (dietro lo stesso `CommandRunner` di `uv`), **nessun file
  nel repo**. Idempotente (`claude mcp get` → skip se già presente), **fail-fast** `McpRegistrationError`
  + comando manuale se `claude` manca: mai un `.mcp.json` scritto silenziosamente. Il *default* dello
  scope resta materia dell'epica multiutente.
- **Residenti inevitabili a root documentati** (`docs/install.md §7`): `.claude/`, `CLAUDE.md`,
  `wiki/`, `.gitignore`, `.sertor/` e `.mcp.json` (solo scope project). Stesso principio del workspace
  Sertor: `pyproject.toml`+`uv.lock` stanno in radice perché `uv` lo richiede — **`uv.lock` sta sempre
  accanto al suo `pyproject.toml`** (su un ospite: in `.sertor/`; nel repo Sertor: in radice).

**Runtime auto-localizzante (follow-up 2026-06-13).** `Settings.load` risolve il `.env` in modo
robusto: cwd `.env` → poi `.env` accanto al venv del runtime (`Path(sys.prefix).parent`, cioè
`.sertor/` per un install, radice repo in dev) → altrimenti default con **warning** (niente fallback
silenzioso a `local`). L'indice è ancorato alla stessa home. Conseguenza: `sertor-rag` indicizza con
backend Azure e tiene l'indice in `.sertor/.index` **da qualsiasi cwd**, non solo lanciato da dentro
`.sertor/` (lezione dalla validazione live su Kaelen: l'exe chiamato da radice host caricava il `.env`
sbagliato → fallback a Ollama).

**Retrocompat ospiti esterni: fuori ambito** (decisione D4) — nessun comando di migrazione; un
`wiki.config.toml` legacy in radice su un vecchio ospite non viene rimosso. **Eccezione: Sertor
stesso**, spostato **one-shot** (config in `wiki/`, asset `.claude/` ri-sync, auto-discovery
verificata dal vivo: `sertor-wiki-tools scan`/`append-log` senza flag dalla radice repo). Consegnata
con SpecKit completo (`specs/016`, PR #26): 410 test verdi (84 pacchetto + 326 root), Constitution
10/10 senza deroghe.

## L'architettura che conta: assets come fonte

Gli artefatti non-Python viaggiano come **package-data nel wheel** (DI-5, dopo ripensamento
documentato nei requisiti §10): offline e coerenza versione-artefatti *by construction*; in
sviluppo l'install editable legge dal source tree. **Inversione di fonte (D2):**
`sertor_installer/assets/` è la **fonte canonica** e la `.claude/` del repo Sertor ne è il
**derivato** — `python -m sertor_installer.sync` propaga, e il test di guardia
(`tests/unit/test_assets_sync.py`, 17 casi) rende il drift un errore di CI. Gli assets sono
**host-agnostici** (Principio X): zero riferimenti a Sertor-il-progetto fuori dalla whitelist
(`sertor-wiki-tools`, `sertor-rag`, marker `SERTOR:WIKI-RITUAL`), verificato da test di scansione.

## Validazione (2026-06-11)

35/35 task SpecKit; root suite **221 passed + 2 xfail** (baseline intatta) + 38 test del pacchetto;
**install live su un repo ospite reale** con contenuti utente preesistenti: 19 created · 1 merged
(hook utente preservato) · 1 block · 0 errori; wiki operativo (`scan`/`validate`/`lint` sulla
config generata); re-run idempotente. Guida utente: `docs/install.md`.

## Aperto: il tema della lingua

Gli **asset testuali sono in italiano fisso** (blocco rituale, skill) anche con `language=en` nella
config generata; lo stesso vale per il seed di `structure init` ([[wiki-tools]]). Decisione utente
(2026-06-11): **da gestire** — tracciato in roadmap e nelle epiche (dote FEAT-007 / evoluzione
installer).
