# Epica — Debito tecnico, igiene e portabilità interna

> Livello: **epica trasversale (interna).** Non aggiunge **capacità di prodotto**: paga il **debito** che
> rallenta o irrigidisce lo sviluppo e mette a rischio la promessa host-agnostica. Raccoglie le voci §7 del
> [backlog audit](../../wiki/syntheses/backlog-audit-2026-06-15.md) finora senza casa durevole. Si decompone
> in `requirements/debito-tecnico/<feature>/requirements.md` (EARS), ma molte voci sono interventi mirati,
> non feature da SpecKit pesante.

## 1. Visione e problema (perché)

Sertor è cresciuto in fretta e ha accumulato debiti che **non sono capacità mancanti** ma **frizioni**:

- **Asset Sertor-coupled:** alcune skill wiki / il playbook / il rituale di step sono ancora **legati a
  Sertor** invece di essere host-agnostici, contraddicendo la mission «framework installabile ovunque»
  (**Principio X**) — pezzi viaggiano sull'ospite ma assumono il contesto di Sertor.
- **Rituale non portabile:** la nota «riesportare il rituale/governance come **plugin portabile**
  repo-agnostico» è solo **parzialmente** assorbita da [[sertor-flow]].
- **Due venv divergenti** (`.venv` / `.venv-core`): footgun operativo, fonte di guasti silenziosi.
- **Igiene del wiki:** mancano hub/overview per-area, una tassonomia più fine, il distill della pagina
  osservabilità; alcune pagine sono gonfie ([[tree-sitter-language-pack]]); manca l'override dei seed
  `[strings]`; il `reconcile` periodico è solo documentato (nessun trigger).
- **Bundle governance rigido:** `sertor-flow` è all-or-nothing (selettività = Could) e senza hook harness (DA-g).
- **CI non Linux:** i test girano su Windows; manca il **test Linux nativo** (debito noto, rag-baseline DA-2).
- **Naming `--assistant` incoerente:** la distribuzione Copilot espone **due** valori (`copilot` = VS Code ·
  `copilot-cli` = Copilot CLI) per quello che l'utente percepisce come «un solo Copilot». Va **allineato a un
  solo `copilot`** (user-flagged 2026-06-16). Apre una decisione di design: come riconciliare i due
  contenitori MCP sotto un nome unico — `.vscode/mcp.json`/`servers` (VS Code) vs `.mcp.json`/`mcpServers`
  (CLI) — es. scriverli **entrambi**, oppure eleggere `.mcp.json` come canonico (GitHub sta convergendo lì).

Il valore: ridurre la frizione e **onorare il Principio X** anche sugli asset interni, così il prodotto
resta davvero portabile e lo sviluppo resta veloce.

> Il *come* (refactor, packaging del plugin, config CI) è materia di design/implementazione.

## 2. Ambito

### In ambito
- **Host-agnosticità degli asset Sertor-authored** residui (skill wiki, playbook, rituale) — chiudere il gap col Principio X.
- **Plugin portabile** del rituale/governance, repo-agnostico (oltre ciò che `sertor-flow` già copre).
- **Unificazione/igiene degli ambienti** (`.venv`/`.venv-core`).
- **Igiene del wiki** (hub per-area, tassonomia, distill mancanti, pagine gonfie, seed override, trigger `reconcile`).
- **Robustezza del bundle governance** (selettività, hook harness).
- **CI multipiattaforma** (Linux nativo).
- **Coerenza del naming dell'installer** (`--assistant`): un solo `copilot`, non `copilot`/`copilot-cli`.

### Fuori ambito
- Qualunque **nuova capacità di prodotto** (retrieval, ingestione, memoria, osservabilità): le rispettive epiche.
- Le **osservabilità minori** (export CSV/MD, bucket «hour», eviction cache): promosse nell'epica `osservabilita`.
- I leak di **enforcement Principio XI** (FR-007 export `__init__`, hook block-mode): vivono in
  `sertor-core/enforcement-principio-xi/` — non qui.

## 3. Criteri di successo
- **CS-1 (host-agnostico):** gli asset interni residui non contengono assunzioni hardcoded su Sertor; un
  ospite li riceve e li usa senza patch manuali (test di guardia, come per `sertor-installer`).
- **CS-2 (plugin):** il rituale/governance è installabile come plugin portabile su un repo terzo senza riferimenti a Sertor.
- **CS-3 (un solo env):** lo sviluppo usa un ambiente coerente; non esistono due venv che divergono silenziosamente.
- **CS-4 (wiki igienico):** il lint organizzativo (livello C) non segnala hub mancanti/pagine fuori posto/seed non-overridabili sui casi noti.
- **CS-5 (CI Linux):** la suite passa in CI su Linux **oltre** che su Windows, in **0** regressioni di piattaforma.

## 4. Stakeholder e attori
- **Owner/maintainer (tu):** paga meno frizione, sviluppa più veloce.
- **Ospite terzo:** riceve asset davvero portabili (Principio X mantenuto).
- **Il sistema-wiki & `sertor-flow`:** oggetti del refactor di igiene/portabilità.

## 5. Vincoli, assunzioni e dipendenze
- **Non-regressione:** ogni intervento mantiene verdi le suite esistenti (root/kit/sertor/sertor-flow).
- **Principio X come bussola:** il refactor host-agnostico riusa la metodologia già applicata (config
  esternalizzata, marker, package-data canonico + derivato + guard test).
- **Calibra al valore:** molte voci sono interventi mirati; non tutte richiedono un flusso SpecKit completo.
- **Coordinamento con `sertor-flow`:** la selettività bundle e gli hook harness toccano quel pacchetto.

## 6. Rischi
- **R-1 — Debito invisibile rimandato all'infinito:** senza casa durevole queste voci si perdono; l'epica
  è proprio la loro casa.
- **R-2 — Refactor host-agnostico che rompe il dogfood:** mitigare con guard test e modifiche incrementali.
- **R-3 — Unificazione venv che rompe ambienti cloud/extra:** procedere con cautela, isolare gli extra pesanti.
- **R-4 — Scope creep dell'igiene wiki:** tenere gli interventi atomici, guidati dal lint C.

## 7. Requisiti trasversali (EARS)
- **REQ-E1 (Ubiquitous):** *The internal Sertor-authored assets shall be host-agnostic: no hardcoded
  assumptions about Sertor, verifiable by guard tests (Principio X).*
- **REQ-E2 (Unwanted):** *If two divergent virtual environments can drift silently, then the development
  setup shall be consolidated to a single coherent environment.*
- **REQ-E3 (Optional):** *Where the governance/ritual is exported as a portable plugin, it shall install on
  a third-party repo without references to Sertor.*
- **REQ-E4 (Ubiquitous):** *The test suite shall pass on Linux in CI in addition to Windows.*

## 8. Backlog di feature

> **Cross-ref `usabilità` (E12):** l'aspetto *user-facing* della freschezza RAG («indice stantio →
> fai X», reconnect MCP) è ownership dell'epica [`usabilità`](../usabilita/epic.md); qui resta il
> **meccanismo** d'enforcement deterministico (hook `SessionEnd`, FEAT-011).

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Host-agnosticità degli asset residui** (skill wiki / playbook / rituale ancora Sertor-coupled) | Onora il Principio X anche sugli asset interni | **Should** | ✅ **DONE (2026-06-19)** — feature 056, PR #80 (`97c91f5`): parità wiki Copilot CLI via **agent-skills NATIVE** (`.github/skills/wiki-author/`, SKILL.md dispatcher che assorbe `/wiki` + payload byte-copiato co-locato), body host-agnostici, guardia di parità con closure; verificata LIVE su Copilot CLI reale (Spike). *(Eventuali altri asset host-coupled scoperti in futuro → nuove voci.)* |
| FEAT-002 | **Unificazione degli ambienti** (`.venv` / `.venv-core` → uno coerente) | Elimina un footgun operativo | **Should** | ✅ **DONE (2026-06-18)** — un solo `.venv` (default workspace `uv`); `dev` superset (incl. `mcp`+`graph`), `azure` opt-in; `.mcp.json` ripuntato; `.venv-core` eliminato; guard test CS-3 |
| FEAT-003 | **CI Linux nativo** (suite verde su Linux oltre Windows; debito rag-baseline DA-2) | Portabilità reale verificata in CI | **Should** | ✅ **DONE 2026-06-23** — `.github/workflows/ci.yml` (matrix os=windows-latest+ubuntu-latest, `fail-fast: false`, ruff `extend-exclude=["prototype"]`); **Windows + Linux verdi** su PR #96 (run `28015943729`). Prima CI del progetto. La prima esecuzione ha scoperto un test non-ermetico (`test_engine_selection` dipendeva dalla cache GloVe) → reso ermetico col provider `hash`. |
| FEAT-004 | **Rituale/governance come plugin portabile** repo-agnostico (oltre ciò che `sertor-flow` copre) | Riuso del metodo su repo terzi senza Sertor | **Could** | da decomporre |
| FEAT-005 | **Igiene del wiki** — hub/overview per-area, tassonomia più fine, distill pagina osservabilità, ripasso [[tree-sitter-language-pack]], override seed `[strings]`, trigger periodico `reconcile` | Wiki navigabile e senza deriva organizzativa | **Could** | da decomporre — guidata dal lint C |
| FEAT-006 | **Robustezza del bundle `sertor-flow`** — selettività (vs all-or-nothing) + hook harness governance (DA-g) | Install governance più flessibile | **Could** | da decomporre |
| FEAT-007 | **Allineamento naming `--assistant`** — unificare i due valori Copilot (`copilot` VS Code + `copilot-cli`) in **un solo `copilot`** | Coerenza dell'API installer, meno confusione utente | **Could** | da decomporre — *user-flagged 2026-06-16*; decisione di design aperta: due contenitori MCP (`.vscode/mcp.json`/`servers` vs `.mcp.json`/`mcpServers`) sotto un nome unico (scrivere entrambi? `.mcp.json` canonico?) |
| FEAT-008 | **Visibilità del context-load SessionStart su Copilot CLI** — investigare se si può **ridurre/eliminare la visibilità** del prompt di SessionStart all'avvio | UX d'avvio meno rumorosa senza perdere il context-load del rituale wiki | **Could** | da investigare — *user-flagged 2026-06-19*. Su Copilot CLI l'hook SessionStart è `type:"prompt"` → il client **mostra all'utente** la direttiva «SESSION START - load the project context…» a ogni avvio; su Claude è **silenzioso** (`additionalContext`). Verificare se Copilot CLI offre un canale d'iniezione contesto meno visibile (o, in alternativa, accettare/accorciare il prompt). Sorgente: `install_wiki._copilot_wiki_hook_specs` (SessionStart) |
| FEAT-010 | **Host-agnosticità degli asset governance (asse Sertor↔ospite)** — gli asset distribuiti da `sertor-flow` avevano **project-coupling**: `requirements-analyst` hardcodava i tool `mcp__sertor-rag__*` nel frontmatter (esistono solo se l'ospite installa *anche* il pacchetto RAG — viola l'indipendenza `sertor-flow`↛RAG); `configuration-manager` si descriveva come gestore di un "workspace RAG" e usava le cartelle-prototipo Sertor (`01-baseline`/`03-graphrag`…) come scope-esempi. Neutralizzati → generici/RAG-opzionale-via-discovery; pin di regressione | Asset governance davvero portabili (Principio X sull'asse progetto, non solo assistente) | **Should** | ✅ **DONE (2026-06-19)** — feature 059: la guardia di parità 056 copriva l'asse Claude↔Copilot, non il project-coupling; scoperto chiedendo «distribuiamo configuration-manager?» |
| FEAT-011 | **Enforcement deterministico della freschezza RAG (hook)** — i passi **MECCANICI** del rituale (re-index incrementale + smoke MCP) NON devono dipendere dalla memoria dell'agente: spostarli in un **hook `SessionEnd`** (`.claude/hooks/rag-freshness.*`) che re-indicizza incrementale + esegue lo smoke MCP e **fallisce loud** se stantio o un tool erra. Include la **reclassificazione nel `CLAUDE.md`** degli step 5/8 da «standing» a «enforced via hook» (confine D↔N: meccanico→harness, giudizio→agente). Host-facing → cablato nell'installer. Complementa la rilevazione del drift (`osservabilita` FEAT-012). | Rende deterministici gli step che oggi si **saltano** (lezione 2026-06-20: discrezionale+condizionato+auto-eseguito = skippabile; il commit sopravvive perché cheap+delegato+incondizionato) | **Should** | ✅ **DONE (2026-06-25, merge `29dd30e`)** — branch `076-enforcement-freschezza-rag`: due hook host-facing (`rag-freshness.ps1` SessionEnd: re-index incondizionato via vehicle + `doctor` + persiste `.sertor/.rag-health.json`; `rag-freshness-start.ps1` SessionStart: induce correzione se `degraded`) + reclass `CLAUDE.md` step 5/8 + `RUNTIME_IGNORES` esteso; Constitution 12/12 + missione, sertor 395/kit 131/root 1128 verdi, `sertor-core` invariato; test funzionale dogfooding ✅ (re-index reale + health 4/4). 4 decisioni scope risolte (re-index incondizionato · fail-loud a 2 tempi · smoke = solo `doctor` · hook separato/non-fatale; buco filtro-metadata `where` promosso a E12-FEAT-011). Follow-up: prova LIVE su ospite + **FEAT-014** (stdin guard) — *user-flagged 2026-06-20* |
| FEAT-012 | **Governance interrogabile via RAG** — includere `.specify/memory/constitution.md` (e valutare `plan-template`) nel **corpus indicizzato**: oggi la **costituzione NON è nel corpus** (verificato con `validate-path`, 2026-06-20) → principi e North Star **non recuperabili** via `search_docs`. | I principi/mission sono interrogabili dall'agente via RAG, non solo letti a mano | **Should** | ✅ **DONE (2026-06-23)** — fix dogfood: rimosso `.specify` dagli exclude del `.env` (host-agnostico default già corretto; template installer già ok). Verifica: `validate-path` conferma `.specify/constitution.md` + `plan-template.md` in indice. Nota latente: template esclude `.git/.hg/.svn`. |
| FEAT-009 | **Distribuzione corretta della costituzione neutra + rifinitura principi** — lo starter neutro **non arriva** sull'ospite: `specify init` (launch-installer FEAT-045) scaffolda un `.specify/memory/constitution.md` **placeholder** (`[PROJECT_NAME]`/`[PRINCIPLE_1_NAME]`) e il nostro CONFIG `create-if-absent` fa **skip** → l'ospite riceve il template vuoto di spec-kit, non la nostra costituzione curata. Fix **replace-if-placeholder** (sovrascrivi il placeholder, preserva una costituzione reale) + rifinitura dei principi neutri (XI/II generalizzati, allineamento VII) | L'ospite riceve una costituzione neutra **sensata e completa**, non il placeholder `[PROJECT_NAME]` | **Should** | ✅ **DONE (2026-06-19)** — feature `058-distribuzione-costituzione`, PR #82 (`b16c4a1`, merge `78f51b8`): replace-if-placeholder in `sertor-flow` (placeholder spec-kit sovrascritto con lo starter neutro, costituzione reale preservata) + rifinitura principi (starter v0.1.0→0.2.0) + mock `FakeSpecifyRunner` reso fedele (depositava il placeholder, era il blind-spot). *(bug scoperto 2026-06-19 via verifica empirica su Spike + install pulito)* |
| FEAT-013 | **Allineamento del layout di config dogfood↔ospite** — il dogfood di Sertor legge la config dal **`.env` a ROOT del repo** (non esiste `.sertor/`), mentre l'installer provvede agli ospiti **`.sertor/.env`** (+ `.sertor/.index`). `_resolve_env_path` onora entrambi (cwd `./.env` → poi `<venv-parent>/.env`), quindi funziona, **ma il dogfood non esercita il layout `.sertor/` che spedisce** → blind-spot di fedeltà del dogfooding (caso 2026-06-22: assunto erroneamente `.sertor/.env` per il dogfood). Decisione di plan: **(a)** migrare la config del dogfood sotto `.sertor/` (mangiare il proprio dog-food anche sul layout) **oppure (b)** documentare esplicitamente la convenzione dev(`./.env`)↔ospite(`.sertor/.env`) e renderla verificabile. | Il dogfood riflette il layout di config reale degli ospiti; niente assunzioni divergenti dev↔host | **Should** | ✅ **DONE (2026-06-23)** — scelta (a): migrato dogfood sotto `.sertor/`. (1) Esteso `_resolve_env_path` per cercare `./.sertor/.env` (additivo, host-agnostico). (2) Spostato `.env` dogfood → `.sertor/.env`, rimosso override `SERTOR_INDEX_DIR` → indice ora `.sertor/.index` per convenzione. Test `test_cwd_sertor_dotenv_resolved_when_venv_not_nested` aggiunto (6/6 verdi). Re-index: 935 doc / 10268 chunk. Finding: server MCP serve ancora da vecchia `.index-sertor` (config all'avvio) → richiede reconnect (segnalato smoke-test standing). |
| FEAT-014 | **Robustezza invocazione manuale dell'hook freschezza (stdin non-bloccante)** — lo script `rag-freshness.ps1` (FEAT-011) blocca su `[Console]::In.ReadToEnd()` quando stdin **non** è rediretto: il docstring dichiara «tolerant if absent (manual invocation)» ma è **falso**, e gli esempi del quickstart (`& .\.claude\hooks\rag-freshness.ps1` senza pipe) si **appendono a tempo indefinito**. In **produzione non si manifesta** (il client agente passa il payload JSON e poi chiude stdin → EOF). Fix proposto: guardia `if ([Console]::IsInputRedirected) { … ReadToEnd … }` (salta la lettura in console interattiva), + correzione degli esempi del quickstart. Scoperto in **dogfooding 2026-06-24** testando FEAT-011 (l'hook è rimasto appeso ~1h al primo run manuale). | L'hook è invocabile a mano/in test senza appendersi; il docstring dice il vero | **Could** | da decomporre (fix mirato; tocca asset bundlato + copia dogfood → sync + `test_assets_sync`) — *dogfooding 2026-06-24* |
| FEAT-015 | **Il refresh/upgrade non disinstalla bene gli artefatti obsoleti** — il percorso di **refresh** (re-install via `uvx --refresh` e/o `sertor upgrade`) **non rimuove in modo pulito** gli artefatti già installati che una nuova versione ha cambiato o tolto dal bundle: sull'ospite restano file/voci **obsoleti** (residui non pruned). Da **riprodurre e isolare** quale percorso cede (re-install idempotente — che by-design non *rimuove* mai — vs `upgrade`, che dovrebbe prunare via diff a posteriori `sertor_owned_paths`), poi correggere. | Un host aggiornato non deve accumulare artefatti stantii/duplicati: il refresh deve lasciare lo stato **pulito** (no residui) | **Could** | 📋 da investigare/decomporre — *user-flagged 2026-06-25*. Verificare contro il lifecycle **FEAT-008** ([[installer-lifecycle]]): `upgrade` dovrebbe già fare prune (diff `sertor_owned_paths` + `LifecycleOp`); capire se il refresh osservato non pulisce per **bug** o per **gap di copertura** (es. l'utente fa `uvx --refresh … install` invece di `upgrade` → il re-install non prune by-design). Possibile esito: documentare «usa `upgrade` per pulire» e/o estendere il prune al percorso di refresh |

> **Nota:** non c'è un «MVP» nel senso di prodotto: è debito. La priorità reale è **FEAT-001/002/003**
> (Should): host-agnosticità, un solo env, CI Linux — le tre frizioni che incidono di più su qualità e
> portabilità. Il resto (Could) si paga quando tocca quelle aree.
