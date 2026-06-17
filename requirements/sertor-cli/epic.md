# Epica — Sertor CLI (distribuzione e uso del core via command line)

> Livello: **epica SECONDARIA**. Veicola le capacità dell'epica primaria
> [`../sertor-core/epic.md`](../sertor-core/epic.md) (motori RAG + skill LLM Wiki) rendendole
> **installabili, configurabili ed eseguibili** su un repository qualunque. **Dipende dal core**:
> la CLI non *è* il prodotto, è il **modo per usarlo**. Le feature (§8) si decompongono in
> `requirements/sertor-cli/<feature>/requirements.md` (EARS).

## 1. Visione e problema (perché)

Le capacità del **core** (creare RAG vettoriale/ibrido/grafico/agentico, creare e gestire l'LLM Wiki)
devono poter essere **portate su un progetto qualsiasi** senza ricostruirle a mano. Serve un
**pacchetto installabile** `sertor` (via `uv` o `pip`) che espone una **command line** (comando
`sertor`) per **scegliere e installare** in modo selettivo le capacità del core su un repository —
**nuovo o esistente** — **configurarle** (provider LLM, vector DB) ed **eseguirle** su richiesta.

Principio cardine: **installazione ≠ esecuzione**. Installare o aggiungere una capacità **non** avvia
da solo la creazione/ingestione del RAG: serve sempre un **comando esplicito** separato.

## 2. Ambito

### In ambito
- **Pacchetto installabile** (`uv`/`pip`) con **CLI** `sertor` come punto d'ingresso unico.
- **Setup selettivo** sul repo target: l'utente sceglie *quali* capacità del core installare; nulla parte da solo.
- **Configurazione** delle capacità installate: provider **LLM** (obbligatorio, default cloud) e
  **vector DB** (condizionale, locale vs cloud).
- **Comando di creazione/esecuzione del RAG** (ingestione/indicizzazione), distinto dall'installazione.
- **Setup della configurazione di governance** (skill/agenti di fase + skill gestione requisiti) su un repo.
- **Agnosticità rispetto al repository** (progetto nuovo o già avviato) e **non distruttività**.
- **Distribuzione** del pacchetto (interim via `git+url`).

### Fuori ambito
- **Le capacità in sé** (come si crea/interroga il RAG, come funzionano le skill del wiki): sono
  l'epica **primaria** `sertor-core`. La CLI le **orchestra e installa**, non le definisce.
- **Pubblicazione pubblica su PyPI** e relativo hardening: rinviata (§8 Won't); il design non deve precluderla.
- Definizione del *come* (stack, API, schema, struttura del codice): fase di **design**.
- GUI/web: il deliverable è una **command line**.

## 3. Criteri di successo
<!-- misurabili e tech-agnostici -->
- **CS-1 (installabilità):** un utente installa il pacchetto con un singolo comando `uv`/`pip` e ha il
  comando `sertor` disponibile, su una macchina pulita, senza passi manuali aggiuntivi.
- **CS-2 (install ≠ run):** in **0** casi l'installazione/aggiunta di una capacità avvia automaticamente
  l'ingestione/creazione del RAG; serve sempre un comando esplicito separato.
- **CS-3 (selettività):** l'utente può installare un **qualsiasi sottoinsieme** delle capacità del core
  (motori RAG, skill wiki, governance) e ottenere solo quelle.
- **CS-4 (agnosticità & non distruttività):** lo stesso CLI completa il setup sia su un **repo nuovo**
  sia su uno **esistente** (≥2 scenari) senza sovrascrivere silenziosamente file dell'utente.
- **CS-5 (configurabilità LLM):** la configurazione supporta **≥1 provider cloud** (default) **e**
  un'opzione **locale (Ollama)**; senza un LLM configurato le operazioni RAG sono bloccate.
- **CS-6 (vector DB a scelta):** la configurazione consente di scegliere tra **≥2** opzioni di vector DB
  (locale vs cloud) oppure di **ometterlo** quando la modalità scelta non lo richiede.

## 4. Stakeholder e attori
- **Owner/maintainer (tu):** decide cosa installare/configurare sul repo target.
- **Team interno (futuro prossimo):** usa la CLI per portare il core su altri repository.
- **Utenti pubblici (futuro):** destinatari di una eventuale release PyPI (oggi Won't).
- **Epica `sertor-core` (dipendenza a monte):** fornisce le capacità che la CLI installa/esegue.
- **Repository target:** il progetto (nuovo o esistente) su cui la CLI opera.

## 5. Vincoli, assunzioni e dipendenze
- **Dipendenza dal core:** la CLI installa/configura/esegue le capacità di `sertor-core`; non le duplica.
- **Linguaggio/distribuzione:** Python ≥ 3.11; pacchetto e comando = **`sertor`**; installabile con
  **`uv`** (preferito) o **`pip`**. **Distribuzione interim (pre-PyPI): `git+url`**.
- **LLM obbligatorio:** target LLM configurato; **default = provider cloud**. Provider del primo taglio:
  **OpenAI, Anthropic, Azure OpenAI/Foundry, GitHub Copilot** e **Ollama** (locale, non-default);
  aggiuntivi proposti (max 3, da confermare): **Google Gemini/Vertex AI, AWS Bedrock, Mistral AI**.
- **Vector DB condizionale:** obbligatorio solo se la modalità RAG selezionata lo richiede; a scelta
  **Chroma** (locale) vs **PGVector/MongoDB su Azure** (cloud).
- **Segreti:** mai persistiti in file versionati.
- **Idempotenza/non distruttività** sul repo esistente; **local-first supportato** (non default).

## 6. Rischi
- **R-1 — Avvio non voluto:** un'installazione che fa partire ingestione costosa (viola CS-2).
- **R-2 — Sovrascrittura su repo esistente:** perdita di config utente (viola CS-4).
- **R-3 — Sicurezza segreti** in fase di configurazione.
- **R-4 — Conflitti di dipendenze** tra capacità del core installate insieme (es. motore grafico).
- **R-5 — Disallineamento col core:** se le capacità del core cambiano, la CLI deve restarvi allineata.
- **R-6 — Scope creep verso il pubblico** prima della maturità interna.

## 7. Requisiti trasversali (EARS)
<!-- solo i pochi requisiti davvero trasversali a tutta l'epica -->
- **REQ-E1 (Optional):** *Where the user runs the setup command, the system shall let the user select
  which core capabilities to install and install only the selected subset.*
- **REQ-E2 (Unwanted):** *If a capability is installed or added, then the system shall not automatically
  start RAG ingestion or index creation.*
- **REQ-E3 (Ubiquitous):** *The system shall require a configured LLM target before running any RAG operation.*
- **REQ-E4 (Optional):** *Where the user selects a local-only configuration, the system shall operate
  without requiring any cloud service.*
- **REQ-E5 (Unwanted):** *If a configuration value is a secret (e.g., an API key), then the system shall
  not persist it in a version-controlled file.*
- **REQ-E6 (Event-driven):** *When the setup runs against an existing repository, the system shall not
  overwrite user-modified files without explicit confirmation.*
- **REQ-E7 (Optional):** *Where a selected RAG modality requires a vector store, the system shall require
  a vector DB to be configured; otherwise it shall allow the setup to complete without one.*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **CLI installabile** (pacchetto `uv`/`pip`, entry-point `sertor`, struttura comandi, principio install≠run) | Spina dorsale: senza il CLI nessuna capacità è raggiungibile | **Must** | parz. (rev. DA-8): la parte **eseguibile** è **CONSEGNATA** come `sertor-rag` (feature `esecuzione`, PR #21, 2026-06-11), accanto a `sertor-wiki-tools`; `sertor` resta il veicolo di **install** (→ FEAT-002/005). **Parte packaging/distribuzione DECOMPOSTA (2026-06-16)** → [`packaging-distribuibile/requirements.md`](packaging-distribuibile/requirements.md) (ambito: formalizzare la distribuzione interim `git+url` — LICENSE MIT + metadati + validazione `uv build`/install pulito uv&pip; PyPI resta FEAT-006). Decisioni utente: MIT+file LICENSE, interim git+url non PyPI. **DA-P1..P4 risolte (2026-06-17)**: versione unica allineata · `uv` primario + `pip` best-effort documentato · `sertor-core`/`sertor-install-kit` solo dipendenze interne · install-kit build-validato ma esonerato dai metadati user-facing. → ✅ **CONSEGNATO su master (PR #68, 2026-06-17)**: pipeline SpecKit completa specify→implement (`specs/047-packaging-distribuibile/`), LICENSE MIT + versione `/VERSION` + metadati + suite `tests/integration/test_packaging.py` (build/install pulito `uv` validato live), Constitution 11/11. **Unico Must residuo dell'epica `sertor-cli` chiuso.** (PyPI pubblico resta FEAT-006/Won't.) |
| FEAT-002 | **Installazione selettiva delle capacità del core** (motori RAG + skill wiki) su un repo target | Portare il core su un progetto, a scelta, senza eseguirlo | **Must** | ✅ **CONSEGNATO**: backbone `sertor` + `sertor install wiki` (PR #22, 2026-06-11, pacchetto distinto in uv workspace, validato live su ospite reale); **`install rag` su master** (2026-06-12, validato live su Kaelen, `specs/015-sertor-install-rag/`); **`install governance` = puntatore** al pacchetto separato `sertor-flow` (FEAT-005, PR #56). **Tema lingua degli asset risolto** (asset EN canonico, PR #27/#28/#29/#31). **Packaging distribuibile ✅ FEAT-001 (PR #68, 2026-06-17) → nessun Must residuo nell'epica `sertor-cli`** |
| FEAT-003 | **Configurazione** (provider LLM obbligatorio default cloud + Ollama; vector DB condizionale a scelta Chroma vs PGVector/MongoDB Azure) | Adatta le capacità all'ambiente target senza toccare codice | **Should** | ✅ **CONSEGNATA (2026-06-17, PR #75)** — `sertor configure [rag]` (`specs/051-configurazione-wizard/`): risoluzione per-campo CI-safe, scrittura `.env` non-distruttiva, validazione statica da `validate_backend()`, report `--json` con anti-leak segreti; default coerente FEAT-009 (azure→store local). 293 test, Constitution 11/11. **Follow-up:** `--check`/US5 deferred → richiede `sertor-rag check` in `sertor-core` (Principio XI) |
| FEAT-004 | **Comando di creazione/esecuzione del RAG** (ingestione/indicizzazione, separato dall'install) | Costruire/aggiornare gli indici su richiesta esplicita | **Should** | ✅ **CONSEGNATA** via feature `esecuzione` (`sertor-rag index`/`search`, PR #21, 2026-06-11) |
| FEAT-005 | **Setup configurazione di governance** (skill/agenti di fase + skill gestione requisiti) | Replicare la configurazione di lavoro su altri repo | **Should** | ✅ **CONSEGNATA (2026-06-15, PR #56)** come **pacchetto separato `sertor-flow`** (distinto da `sertor`, ortogonale al RAG, no dipendenza da `sertor-core`; motore estratto in `sertor-install-kit`). SpecKit `specs/037-governance-sertor-flow/`; requisiti [`governance-sertor-flow/requirements.md`](governance-sertor-flow/requirements.md) |
| FEAT-006 | **Distribuzione pubblica su PyPI** (versioning pubblico, licenza, hardening supply-chain) | Apertura a utenti esterni | **Won't (per ora)** | rinviata |
| FEAT-008 | **Ciclo di vita dell'installer** — `upgrade` degli artefatti già installati su un ospite e `uninstall` (rimozione pulita), oltre al primo install | Oggi `sertor install` fa solo il primo install (install≠run); upgrade/uninstall rinviati da `specs/011`/`012`/`015` **senza una casa durevole** | **Could** | ✅ **CONSEGNATA (2026-06-17)** — `sertor upgrade`/`uninstall` e `sertor-flow upgrade`/`uninstall` (tutto-in-uno + per-capacità, `--dry-run`/`--json`/`--assistant`, `--purge-wiki`+`--yes` CI-safe). Primitive di ciclo di vita **una sola volta nel `sertor-install-kit`** (`LifecycleOp`, outcome `updated`/`removed`, funzioni inverse pure duali, `execute_lifecycle`, `sertor_owned_paths`); riuso dello stesso plan-builder col verbo; report `install.report/1` esteso (additivo); `sertor-flow` resta senza dipendenza da `sertor-core`/`sertor`. SpecKit `specs/048-lifecycle-installer/`, requisiti [`lifecycle-installer/requirements.md`](lifecycle-installer/requirements.md) (34 REQ EARS + 7 NFR). **Q1–Q4 risolte:** Q1 (a) wiki protetto (`--purge-wiki`+`--yes`) · Q2 (a) diff a posteriori, nessun manifest · Q3 (c) tutto-in-uno **e** per-capacità · Q4 (a) `sertor-flow` simmetrico |
| FEAT-007 | **Distribuzione multi-assistente: GitHub Copilot** (+ **Codex** come Could) — tutto il consegnato deve essere **utilizzabile anche da GitHub Copilot**: (a) il **server MCP** `sertor-rag` collegato ai client Copilot (VS Code agent mode / coding agent — MCP è supportato: da verificare e documentare la config, es. `.vscode/mcp.json`); (b) le **superfici agentiche** dell'installer tradotte per l'assistente ospite (`.claude/skills` + `/wiki` + agente + blocco rituale CLAUDE.md → equivalenti Copilot: `copilot-instructions.md`, prompt files `.github/prompts/`, da mappare in decomposizione) con **target assistant** nell'install; (c) le CLI (`sertor-rag`, `sertor-wiki-tools`) sono già assistant-agnostic. **Codex** (AGENTS.md + MCP) = Could. NB: distinto da DA-6 (lì Copilot è *provider LLM*; qui è l'*assistente consumatore* delle superfici). **Ambito ristretto al pacchetto `sertor` (wiki+rag)**; la governance/SpecKit (`sertor-flow`) è stata promossa a feature gemella → **FEAT-009** | Le capacità non devono dipendere da un solo assistente: estende lo spirito del Principio X (host-agnostico) all'**assistente ospite** | **Must** (Copilot) · **Could** (Codex) | ✅ **CONSEGNATA (2026-06-15, PR #64)** — parità Copilot per il pacchetto `sertor`: MCP `.vscode/mcp.json` + istruzioni `.github/copilot-instructions.md` + prompt-file/custom-agent resi + hook `.github/hooks/`; seam `AssistantProfile`/`Surface` nel `sertor-install-kit`, CLI `--assistant claude\|copilot`. **+ target `copilot-cli`** (PR #66, 2026-06-16, MCP in `.mcp.json`/`mcpServers`). Requisiti [`distribuzione-copilot/requirements.md`](distribuzione-copilot/requirements.md) (22 REQ EARS). **Codex resta Could (non avviato per scelta utente)**. ✅ **Conformità schema Copilot sanata da FEAT-011 (PR #73, 2026-06-17)** — hook/output/comandi/frontmatter nativi; resta da verificare sul campo il SessionStart VS Code (`[ASSUNTO-VSC]`) |
| FEAT-010 | **Ergonomia & portabilità dell'installer** — fallback **`pip`** (oltre `uv`), **avviso target non-Python**, **hook Linux** (varianti `sh`/Python per ospiti senza PowerShell), **install multi-target** (Claude + Copilot in un colpo). + **reviewer «clean-code» attivo** come superficie di governance (ricorre 3× senza casa) | Installer robusto su ospiti eterogenei (OS/runtime/assistente) | **Could** | da decomporre — **leak audit (2026-06-16)**, finora solo in spec |
| FEAT-009 | **Distribuzione governance/SpecKit multi-assistente: GitHub Copilot via `sertor-flow`** — gemella di FEAT-007 per il pacchetto `sertor-flow`: variante **SpecKit per Copilot** (vendorata da spec-kit `--ai copilot`: `.github/prompts/` + `.github/agents/`, macchinario `.specify/` condiviso) + traduzione Copilot delle superfici **Sertor-authored** (`requirements-analyst`, `configuration-manager`, skill `requirements`, blocco rituale SDLC). Meccanismo `--assistant` condiviso con FEAT-007 nel `sertor-install-kit`. **Codex** = Could | Un ospite Copilot riceve l'intero metodo SDLC, non solo RAG/wiki; estende il Principio X all'assistente ospite anche per la governance | **Must** (Copilot) · **Could** (Codex) | ✅ **CONSEGNATA (2026-06-15, PR #65)** — `sertor-flow install --assistant claude\|copilot`: **pivot vendoring→launch-installer** (SpecKit via `specify init --ai`, versione pinnata, fail-fast), superfici Sertor-authored tradotte per Copilot, renderer condiviso nel kit; nessuna dipendenza da `sertor-core`. SpecKit `specs/045-distribuzione-copilot-flow/`, requisiti [`distribuzione-copilot-flow/requirements.md`](distribuzione-copilot-flow/requirements.md) (19 REQ EARS). **Codex resta Could**. ✅ **Conformità schema Copilot sanata da FEAT-011 (PR #73, 2026-06-17)** |
| FEAT-011 | **Hardening compatibilità Copilot** — rendere le superfici depositate per Copilot conformi allo **schema reale** di Copilot (CLI 1.0.63 + VS Code): hook `version:1`/entry piatte/`powershell`+`bash`/`timeoutSec` (oggi formato Claude → file scartato); contratto di output degli `.ps1` per evento (`additionalContext`/`decision`, non `systemMessage`); comandi via **custom-agent** su Copilot CLI (i prompt-file non sono supportati dalla CLI); frontmatter agent (`model:` Claude → omesso); + **test di validità-schema-Copilot** anti-regressione | Le capacità distribuite su Copilot devono **davvero funzionare**, non solo essere installate (essenza dogfooding); corregge la falsa "parità piena" di FEAT-007/009 | **Must** | ✅ **CONSEGNATA (2026-06-17, PR #73)** — pipeline SpecKit completa `specs/049-compatibilita-copilot/`; `render_copilot_hooks`+`HookEntrySpec` nativi (rimossi gli asset Claude-format), output `.ps1` per-assistente via `-Assistant`, comandi per-target (VS Code prompt-file / CLI custom-agent), `model:` omesso, suite validità-schema offline. Constitution 11/11, 453 test verdi, `sertor-core` invariato. **Gap dichiarato** (mai "parità piena"): SessionStart VS Code `[ASSUNTO-VSC]` + MCP CLI da **verificare empiricamente** su ospite reale (follow-up in roadmap). Requisiti [`compatibilita-copilot/requirements.md`](compatibilita-copilot/requirements.md) |

> **Feature decomposta:** `esecuzione` (`requirements/sertor-cli/esecuzione/requirements.md`, rev.
> 2026-06-11) — taglio **run-centrico**: entry-point **`sertor-rag`** (console-script del core, DA-8)
> + comandi `index`/`search` + osservabilità a runtime + lettura della configurazione. Copre la parte
> eseguibile di FEAT-001, tutta FEAT-004 e la lettura config di FEAT-003. Il `wiki index` originario è
> stato rimosso (coperto da `sertor-wiki-tools index` + modello a corpus unico D-21/DA-7). Restano
> fuori: packaging/distribuzione, install selettivo su altri repo (FEAT-002), wizard di
> configurazione, governance (FEAT-005).

> **Nota sull'MVP della CLI:** il primo taglio (Must) rende il pacchetto **installabile** e capace di
> **installare selettivamente** le capacità del core su un repo. Configurazione (FEAT-003), esecuzione
> (FEAT-004) e governance (FEAT-005) completano il ciclo subito dopo (Should). La CLI è utile **solo
> insieme** al core: il suo MVP presuppone che il core esista (almeno baseline + creazione wiki).

## 9. Decisioni risolte (DA-1…DA-8)

Chiuse in elicitazione (2026-05-30, DA-7 il 2026-06-10, DA-8 il 2026-06-11); restano valide a livello di distribuzione/uso:

| # | Tema | Decisione |
|---|------|-----------|
| DA-1 | Naming | Pacchetto e comando = **`sertor`**. |
| DA-7 | **Wiki dentro l'ospite (by design)** | Quando si installa Sertor su un progetto, il **wiki si crea DENTRO il progetto ospite** (decisione utente, 2026-06-10). Conseguenza per il retrieval: il wiki è **parte del corpus primario** dell'ospite come documentazione (`doc_type=doc`) — il **modello standard è a corpus unico**, senza collezione separata né `SERTOR_EXTRA_CORPORA`. La query congiunta multi-collezione del core (feature `specs/010`) resta riservata a ospiti con corpora **davvero disgiunti** (es. doc-repo esterno), non al caso standard. L'install della CLI (FEAT-002) deve riflettere questo default. |
| DA-8 | **Split installer / esecuzione (2026-06-11)** | Il comando **`sertor` è riservato all'installazione/setup** sull'ospite, con verbo esplicito: **`sertor install <capacità>`** (es. `sertor install wiki`, poi `install rag`, `install governance`). L'**esecuzione** vive nei **console-script del pacchetto core**: **`sertor-rag`** (chiamate RAG: `index`/`search`, feature `esecuzione`) accanto a `sertor-wiki-tools` (wiki, già consegnato). Supera la DA-C1 della feature `esecuzione`. Contenuto confermato di `sertor install wiki` (input per la decomposizione di FEAT-002): skill wiki (wiki-author+playbook, `/wiki`, agente wiki-curator) + step ritual nel `CLAUDE.md` dell'ospite + `wiki.config.toml` + `structure init` + tooling di indicizzazione configurato; **nessuna indicizzazione automatica** (REQ-E2). |
| DA-2 | Confine install/config/run | **Confermato**: l'MVP della CLI installa; configurazione (FEAT-003) ed esecuzione (FEAT-004) restano **Should**. |
| DA-3 | Governance | **Resta Should** (FEAT-005 fuori dall'MVP della CLI). |
| DA-4 | Distribuzione interim | **`git+url`** prima dell'eventuale PyPI pubblico. |
| DA-5 | Vector DB | **Obbligatorio in modo condizionale**: solo se la modalità lo richiede; solo-graph può ometterlo (REQ-E7). |
| DA-6 | Provider LLM | Primo taglio: **OpenAI, Anthropic, Azure OpenAI/Foundry, GitHub Copilot, Ollama**; aggiuntivi (max 3, da confermare): **Gemini/Vertex AI, AWS Bedrock, Mistral AI**. |

> Nessuna domanda aperta residua a livello di questa epica. Le rifiniture di dettaglio si chiudono
> alla **decomposizione** delle feature.
