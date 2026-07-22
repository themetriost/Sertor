---
title: Roadmap & stato di prodotto (pagina viva)
type: synthesis
tags: [roadmap, piano, stato, produzione, backlog]
created: 2026-06-03
updated: 2026-07-21
sources: ["requirements/sertor-core/epic.md", "requirements/sertor-cli/epic.md", "specs/**", ".specify/memory/constitution.md", "requirements/memoria-conversazioni/epic.md"]
---

# Roadmap & stato — Sertor

> **Pagina viva.** Quadro d'insieme dello stato reale. Si aggiorna a mano (sezione *Nuove funzionalità da
> discutere*) e quando una feature avanza nella pipeline SpecKit. Quando un'idea matura: backlog epica →
> `requirements → spec → plan → tasks → implement`.

<!-- EXEC:START -->
## ⚡ Executive summary (stato al 2026-07-22)

### ✅ Capacità consegnate (feature su `master`)

| Capacità (feature) | Epica |
|---|---|
| Nucleo retrieval · motore baseline · Wiki LLM · server MCP | `sertor-core` |
| RAG ibrido+reranking (default) · code-graph · agentico & Wiki↔RAG (compositi) | `sertor-core` |
| **Refresh incrementale dell'indice** (FEAT-009, 2026-06-16) | `sertor-core` |
| Hardening retrieval (Must + Should gruppo C: retry · soglia · cache embeddings) | `sertor-core` |
| **Embedder locale local-first** (FEAT-011, 2026-06-21) — `glove` (GloVe 6B 300d PDDL, **nuovo default**) + `hash` (char-n-gram stdlib, pavimento airgapped/CI); **`RAG_BACKEND` rimosso** → `SERTOR_EMBED_PROVIDER` unico | `sertor-core` |
| CLI `sertor-rag` · installer `sertor install wiki`/`rag` | `sertor-cli` |
| **Packaging distribuibile** `git+url` (FEAT-001, LICENSE+metadati+build verificata, 2026-06-17) | `sertor-cli` |
| **Ciclo di vita installer** — `upgrade`/`uninstall` per `sertor` e `sertor-flow` (FEAT-008, 2026-06-17) | `sertor-cli` |
| Governance SDLC — pacchetto separato `sertor-flow` | `sertor-cli` |
| Distribuzione Copilot (VS Code + CLI) — FEAT-007+009 + **hardening nativo FEAT-011** ✅ *(verifica empirica VS Code/MCP CLI = follow-up)* | `sertor-cli` |
| Igiene radice host · tema lingua (tutto il prodotto in EN) | `sertor-cli` |
| MVP osservabilità F1–F4 (**accesa** sul dogfood) · **export OTel + visibilità RAG nella TUI** (FEAT-005/013/014/015, 2026-06-19) | `osservabilita` |
| MVP memoria: cattura→ricerca→CLI/hook→distillazione (**acceso**) | `memoria-conversazioni` |
| **Distribuzione della memoria via installer** (FEAT-009, merge `a36ba89`, 2026-06-22) — `sertor install rag` deposita manopole memoria `.env` (off di default) + hook cattura/`SessionEnd` per-assistente + cenno comandi `sertor-rag memory`; lifecycle completo | `memoria-conversazioni` |
| **Ricerca semantica opzionale sull'archivio** (FEAT-004, 2026-06-22) — `memory search --semantic` (full-text resta default) + `memory index-semantic` (backfill); store vettoriale **dedicato** che riusa le primitive del core (no nuovo motore); auto-index **incrementale** a fine sessione (append-only, marker via stato dello store + `contains_ids`); gate privacy `SERTOR_MEMORY_SEMANTIC`, on-machine col provider locale. *(Manopole `SERTOR_MEMORY_SEMANTIC*` ✅ nei template `.env` installer; guardia anti-drift resa auto-derivante da `Settings.load`.)* | `memoria-conversazioni` |
| **Cattura memoria su GitHub Copilot CLI** (FEAT-008, 2026-06-22) — secondo adapter `copilot-cli` dietro la porta `TranscriptCaptureAdapter`: legge `~/.copilot/session-state/<uuid>/events.jsonl` (Copilot CLI 1.0.63), estrae i soli turni `user.message`/`assistant.message`, associa la sessione al progetto via `cwd`/`gitRoot` del `session.start` (regola asimmetrica). **Rende vivo** l'hook `SessionEnd` già distribuito da FEAT-009; l'intero tier a valle (archivio · full-text · semantica · distillazione) opera su Copilot **senza modifiche**. Additivo a leva spenta. *(Cablaggio `SERTOR_MEMORY_ADAPTER=copilot-cli` nel template `.env` installer = debito → FEAT-009.)* | `memoria-conversazioni` |
| **Valutazione del retrieval & non-regressione** — `sertor-rag eval` (hit@k/MRR + gate baseline + `--by-kind` symbol→grafo) + skill genesi/feedback (FEAT-001, PR #92, 2026-06-20) | `retrieval-qualita` |
| **Valutazione set-based della navigazione del grafo** — `sertor-rag graph-eval` (precision/recall/F1, `who_calls`/`defines`, baseline separata) (FEAT-011, 2026-06-20) | `retrieval-qualita` |
| **Fusione code+doc misurata + `search_combined` strutturato** (FEAT-003 T1+T2, 2026-06-21) — set NL intent-typed + misura **per-superficie** + `eval run --fused`; **`search_combined` → tupla `(docs, code)`** (l'agente usa entrambi i flussi); metrica **OR/unione** *(la prima ipotesi «fusion coverage AND» = artefatto, corretta)* | `retrieval-qualita` |
| **`sertor-rag doctor` — verifica di salute deterministica** (FEAT-001, merge `171f43b`, 2026-06-23) — «ha funzionato?» in un comando: 4 aree (env/provider/indice/MCP), pass/warn/fail + causa/rimedio, `--json` schema `doctor.report/1`, exit-code gate, offline-safe (probe provider opt-in `--online`); chiude il `--check` *deferred* di E2/FEAT-003. Additivo, deterministico, zero LLM | `usabilità` |
| **Enforcement deterministico della freschezza RAG (hook)** (FEAT-011, merge `29dd30e`, 2026-06-25) — due hook host-facing via `sertor install rag` (parità Claude/Copilot): `rag-freshness.ps1` (SessionEnd: re-index incondizionato via vehicle + `doctor` + persiste `.sertor/.rag-health.json`) + `rag-freshness-start.ps1` (SessionStart: induce la correzione se `degraded`). Sposta i passi meccanici del rituale (re-index/smoke) dalla discrezione dell'agente a un harness deterministico (confine D↔N). `sertor-core` invariato | `debito-tecnico` |
| **Auto-update version check** (E2-FEAT-013, merge `8d951cd`, 2026-06-26) — avviso a inizio sessione: `version-check.ps1` (SessionEnd) confronta lo stamp `.sertor/.sertor-version` col `/VERSION` su master (GET cachata ~24h) → `.sertor/.version-check.json`; SessionStart avvisa se behind (script Claude / prompt statico Copilot). Solo avviso, **mai auto-upgrade**; non-fatale, no LLM. Gemello di E10-FEAT-011 | `sertor-cli` |
| **Guida d'install host-assistant-aware + NRT** (E12-FEAT-012, merge `030c695`, 2026-06-26) — `guided-setup`/`concierge` rilevano l'host e passano sempre `--assistant <host>` a rag/wiki/flow (prima default `claude` su host Copilot → layout sbagliato); + NRT anti-regressione per-PR. Fix di un bug reale emerso in dogfooding | `usabilità` |
| **Fail-loud breadcrumb negli hook + fallback «asset mancante → STOP» negli agent** (E10-FEAT-019, merge `629481b`/PR #125, 2026-06-29) — Principio XII reso reale sugli asset distribuiti: 4 hook (`memory-capture`/`rag-freshness`/`wiki-pending-check`/`version-check`) scrivono un breadcrumb ispezionabile `.sertor/.last-hook-error` (schema `hook.error/1`, sovrascritto, secret-free, `exit 0` sempre) sui path prima muti; 3 agent (`concierge`/`wiki-curator`/`requirements-analyst`) si fermano su asset mancante invece di procedere a vuoto. 4 guardie anti-regressione (incl. il buco sync dogfood D-5). Additivo, `sertor-core` invariato | `debito-tecnico` |
| **Portabilità OS degli hook (guardia pwsh) + onestà sui surface inerti** (E10-FEAT-018, merge `8257fd3`/PR #127, 2026-06-30) — Principio XII + X: gli hook `.ps1` cablati con `"shell": "powershell"` fallivano in silenzio su mac/Linux (`powershell` assente). Nuovo modulo puro `host_env.py` nel kit: su host non-Windows senza `pwsh` l'installer emette una **nota azionabile** (installa PowerShell Core) via `InstallReport.notes` (primo uso reale) invece del silent fail — **detect-only, wiring invariato**. + nota onestà `memory-capture` inerte su Copilot. Doc utente col limite tecnico dichiarato. Additivo, `sertor-core` invariato, schema `install.report/1` invariato | `debito-tecnico` |
| **Default model-policy subagent Copilot CLI** (E2-FEAT-015, merge `4e30d00`/PR #135, 2026-07-01) — i 5 agenti Sertor-authored su Copilot CLI ricevono un `model:` di default da una fonte unica versionata (`model_policy.py`), fail-loud install-time; meccanismo reale = frontmatter `.agent.md` (non un blocco settings, verificato vs doc ufficiale); path Claude byte-identico, core invariato | `sertor-cli` |
| **Self-host di SpecLift** (E14-FEAT-001, merge `bbfb74d`/PR #136, 2026-07-01) — `diff → requisiti EARS ancorati` (handoff da Sinthari) vendorato come `packages/speclift`; retrieval via **MCP** (Adapter B pluggable, esito della collaborazione agent-to-agent feedback CLI→MCP); dogfood e2e verde; core invariato, 122 test | `speclift` |
| **Doc utente MVP** (E13-FEAT-001+002, merge `6e40ccc`/PR #172, 2026-07-11, item A-18) — **`docs/getting-started.md`** (percorso unico host-agnostico «dal nulla al primo valore», varianti CLI Claude+Copilot affiancate, esempio finale di **fusione code+doc** via `search_combined`) + **README valore-first** (apre col differenziatore code+doc + esempio, fatti preservati, ingresso unico). Prima consegna di E13; authoring puro (core/CLI/installer invariati) | `documentazione-marketing` |
| **Doc utente Fase 1 COMPLETA** (E13-FEAT-003..008, merge `3bcb8b1`/PR #175, 2026-07-12) — batch: **`docs/why-sertor.md`** (cos'è e perché, non-tecnici) · **`docs/README.md`** (indice «dove andare per cosa») · **`docs/tutorial.md`** (end-to-end guidato) · **`docs/troubleshooting.md`** (symptom→cause→fix, complemento statico di `doctor`) · **`CHANGELOG.md`** (release notes utente, onesto sull'interim) · **`docs/reference.md`** (comandi+manopole, punta a install.md). Host-agnostici, comandi verbatim dagli asset reali, 0 link a `wiki/`/`specs/` (corretto anche 1 drift CS-5 in install.md). Chiude tutta la **Fase 1** di E13 | `documentazione-marketing` |
| **Ergonomia installer — multi-target · avviso non-Python · guida uv-assente** (E2-FEAT-010 residuo, merge `eb1f7a3`/PR #179, 2026-07-13) — `sertor install --assistant` accetta **CSV/`all`** → un comando installa più assistenti in **container disgiunti** (deps runtime `.sertor/` una volta, report aggregato + note propagate, fail-fast; single-value invariato) · nuovo `host_env.is_python_host` (kit) → **nota advisory** su host non-Python (sorgenti intatti) · messaggio **uv-assente onesto** (installa uv · `--no-deps` · pip non ancora disponibile). Pip fallback reale rinviato a **FEAT-006**/go-public. `sertor-core` invariato; kit 178 · sertor 523 · suite 1180 verdi | `sertor-cli` |
| **Fix cattura memoria — encoding path + fail-loud** (E4-FEAT-011, merge `5d30635`/PR #189, 2026-07-15) — `encode_project_path` collassava solo `:`/`\`/`/`, mentre Claude Code collassa **ogni** carattere non-alfanumerico (spazi **e** punti) → su path con spazi la cartella calcolata non esisteva → **0 sessioni archiviate in silenzio**. Regola derivata dai 15 nomi reali della macchina; validata dal vivo (**22 sessioni** recuperate su `VM-WorkingFolder`). + **fail-loud** host-agnostico: `source_available()` sul port + `ArchiveRunReport.source_absent` + WARNING visibile (human+JSON), exit 0 preservato (l'hook SessionEnd non si rompe). Adapter `copilot-cli` non affetto. Fonte: handoff Nunzio | `memoria-conversazioni` |
| **Hook wiring ancorato alla repo root** (E10-FEAT-031, merge `e3c2a97`/PR #190, 2026-07-15) — regressione di A-09: la migrazione `.ps1`→`.py` aveva perso l'ancoraggio `$env:CLAUDE_PROJECT_DIR`, e con CWD ≠ radice ogni hook falliva prima del comando (su `PreToolUse` **bloccando** Bash/Write/Edit). Fix **nativo** per assistente: `${CLAUDE_PROJECT_DIR}` nei 7 asset `settings*.json` (Claude) · campo `HookEntrySpec.cwd` → `cwd="."` sui 6 command entry (Copilot). Guardie anti-regressione; `sertor-core` invariato. **Consegna agli ospiti che aggiornano completata da E10-FEAT-032** (riga sotto) | `debito-tecnico` |
| **Identità di un hook = lo script (stem), non la stringa del comando** (E10-FEAT-032, merge `ddbfb27`/PR #192, 2026-07-17) — completa la consegna di FEAT-031 **agli ospiti che aggiornano**: il merge di `settings.json` identificava gli hook per stringa del comando, quindi un cambio di wiring **duplicava** (Claude, con la copia vecchia rotta ancora attiva) o **veniva scartato in silenzio** (Copilot, `cwd` aggiunto a command invariato). Identità per **stem** → le tre transizioni (`.ps1`→`.py`, relativo→ancorato, `cwd`) si chiudono insieme. Contratti espliciti: `install` non rimuove/non duplica e **nomina** la forma stantia nel report (prima taceva — Principio XII) · `upgrade` sostituisce in place e **collassa** le rese multiple. +10 guardie sull'**esito d'upgrade** (non sulla forma dell'asset). **Confermato da verifica indipendente (nodo Noetix)**; `sertor-core` invariato | `debito-tecnico` |
| **`doctor` ancorato alla radice del progetto** (E10-FEAT-038, merge `7075a0f`/PR #198, 2026-07-18) — `_cmd_doctor` usava `Path.cwd()` → stesso indice, `index: pass` dalla root e `warn` da `src/`; `registered` oscillava col cwd. Ora `Settings.project_root` risolve la radice con la **stessa self-localization** di `.env`/`.index` (parent di `.sertor/` via `sys.prefix`), onora `CLAUDE_PROJECT_DIR`, **fail-loud** se irrisolvibile (Principio XII) — una sola semantica di root nel CLI. Stesso difetto d'ancoraggio di FEAT-031, mai corretto per `doctor` (già sfiorato come E15-FEAT-009 «not-a-bug»). **Invarianza al cwd provata LIVE** (runtime installato) + 5 unit test; SpecKit completo; `sertor-core` engine invariato. **1° item della coda dell'analisi setup** | `debito-tecnico` |
| **`ritual-check` rileva il default branch** (E10-FEAT-033, merge `546cb22`/PR #200, 2026-07-18) — `_resolve_base` assumeva `master` hardcoded → `ritual-check` esplodeva su ogni ospite con default `main` (il **primo** tool toccato dalla forced declaration del rituale). Ora `_default_base_candidates` rileva il default a runtime (`origin/HEAD` → ref esistenti ordinati → primo con merge-base), `--base` e fail-loud invariati; dogfood `master` non regredisce (**verificato LIVE**). **Segnalato da Noetix**, verificato sul codice; 4 test; SpecKit completo. 2° item della coda dell'analisi setup | `debito-tecnico` |
| **L'installer descrive l'AZIONE + log ispezionabile** (E2-FEAT-018, merge `0b45c24`/PR #202, 2026-07-18) — il report dell'installer descriveva la *precondizione* («già presente») non l'*azione*: `SKIPPED` conflazionava identico/divergente (il buco di FEAT-031/032), le deps dicevano `SKIPPED` mentre `uv add` girava. Nuovo esito additivo **`Outcome.PRESENT_DIVERGENT`** (presente-ma-diverso → lasciato intatto, dichiarato) su sertor **e** flow, riusa `content_matches` da `lifecycle`; deps oneste (`UPDATED`); **assorbe E10-FEAT-036**. Log **`.sertor/.install-log.jsonl`** (`install.event/1`, best-effort, dry-run no-write) sul rag install — **provato LIVE** (present-divergent + log + file preservato). +10 test; doc utente. P2-log wiki/flow/lifecycle = follow-up E2-FEAT-020. 3° item della coda dell'analisi setup | `sertor-cli` |
| **`rag-freshness` misura post-riparazione + auto-heal del lock stantio** (E10-FEAT-034 **+ FEAT-035 fusa**, merge `5add90d`/PR #205, 2026-07-20) — **chiude l'ULTIMO item della coda «analisi setup»**. *(034)* l'hook `rag-freshness` misurava la salute con `doctor` e **scriveva** `.rag-health.json` **prima** di ri-indicizzare → verdetto pre-riparazione → il caso normale (stantio riparato) allarmava comunque al SessionStart, svalutando l'allarme. Ora: **re-index (ripara) → `doctor` (rimisura) → scrittura atomica del verdetto post-riparazione**; `reason` elenca **tutte** le aree degradate; re-index fallito ⇒ `degraded`. A valle di FEAT-038 (doctor ancorato). *(035)* `_IndexLock` (`sertor-core`) **auto-guarisce** il lock `.index.lock` con PID **confermato morto** (worker detached crashato → prima bloccava ogni re-index a mano, osservato PID 33516 il 2026-07-17): lo reclama e procede; PID vivo/lockfile ambiguo → `IndexLockedError` (conservativo); reclamo **osservabile** (`log_event` `index.lock.reclaimed`, Principio XII); helper `_pid_alive` cross-OS stdlib (mai `os.kill` su Windows). **Provato LIVE** via CLI reale (PID morto→procede / PID vivo→locked). SpecKit completo, Constitution 12/12; asset host-facing (guard esito-upgrade + byte-parity + doc utente `install.md`/CHANGELOG) | `debito-tecnico` |
| **Parità MCP per la lettura della memoria** (E4-FEAT-010, merge `427cf8e`/PR #208, 2026-07-20) — l'archivio memoria conversazioni era leggibile solo da CLI; il server MCP `sertor-rag` ora espone **3 tool read-only** (7→10): **`memory_search`** (full-text FTS5, «ne avevamo già parlato?»), **`memory_list`** (sessioni recenti), **`memory_show`** (turni di una sessione) — thin sopra gli stessi servizi core della CLI, gated da `SERTOR_MEMORY` (spenta → `{"status":"disabled"}` esplicito, non lista vuota). Porta la memoria episodica sul **vehicle nativo** dell'agente (Principio XI), non più via subprocess. Semantico via MCP = follow-up (doppio gate). **Provato LIVE** sull'archivio reale del dogfood (14MB): list/show/search ok, query hashata; 7 test; `sertor-core` **invariato** (solo `sertor_mcp`) | `memoria-conversazioni` |
| **Fix cattura-auto — il gate privacy legge la fonte reale** (E4-FEAT-012, merge `9921a34`/PR #210, 2026-07-21) — **chiude il 🐛 auto-capture** rimasto aperto. L'hook `memory-capture` (SessionEnd) gatava su `os.environ["SERTOR_MEMORY"]`, ma quel valore vive in **`.sertor/.env`** (letto solo da `Settings.load` **dentro la CLI**, non iniettato nell'ambiente hook) → gate sempre `None` → **no-op silenzioso** su ogni host che abilita la memoria via file → cattura mai eseguita. **Causa reale ≠ ipotesi EXEC precedente** (FEAT-031/032, path relativo): quello era un *secondo* difetto stacked (script non trovato), risolto; **sotto** c'era questo gate, mai toccato — regressione della migrazione A-09 (`.ps1`→`.py`, `69d527c`, 2026-07-09). **Fix:** helper `_hooklib.memory_enabled()` legge lo stesso `.env` della CLI (`./.env` poi `.sertor/.env` ancorato a `CLAUDE_PROJECT_DIR`; `.env` vince su `os.environ` come `Settings.load(override=True)`), stdlib-only, byte-copiato Claude/Copilot; +5 test regressione + whitelist `SERTOR_MEMORY` nella guardia host-agnostica. **Provato LIVE** (gate→True dal `.sertor/.env` reale; archive manuale ha colmato 10→20 lug); `sertor-core` **invariato** (solo asset hook) | `memoria-conversazioni` |
| **Ricerca semantica della memoria via MCP** (E4-FEAT-013, merge `727ab5b`/PR #212, 2026-07-21) — il tool MCP `memory_search` accetta ora **`semantic=true`**: ricerca per *significato* (non parola), mirror di `sertor-rag memory search --semantic`, sul **vehicle nativo** dell'agente. Dietro il **gate a due strati** `SERTOR_MEMORY` + `SERTOR_MEMORY_SEMANTIC` (consumato via `build_memory_semantic_index`, come la CLI): gate spento → `{"status":"disabled"}` che nomina il **knob giusto** + il backfill `index-semantic`, **mai** un fallback silenzioso al full-text. Hit shape condivisa col full-text; query hashata. Chiude il residuo «semantico via MCP» di FEAT-010. **Provato LIVE** sul core path (ricerca semantica reale → hit pertinenti); +6 test (colta e corretta una collisione `_hit_dict`↔SymbolHit dei graph tool); `sertor-core` **invariato** (solo `sertor_mcp`) | `memoria-conversazioni` |
| **Fix `memory search` punctuation-safe** (E4-FEAT-014, merge `beacd03`/PR #214, 2026-07-21) — **bug segnalato dal nodo Acta**: il testo grezzo andava nel `MATCH` FTS5, un token con punteggiatura (`0.1.1`, `a/b.py`, `tipo:esito`) → `fts5: syntax error`, catturato e **degradato a `(no results)`** (masking, anti-Fail-Loud). Colpiva CLI **e** tool MCP `memory_search`. **Fix:** funzione pura `_to_fts_match` (ogni token → string-literal FTS5 quotato, `"` interno raddoppiato; AND preservato) a monte di `_build_sql` → punteggiatura = contenuto; il masking sparisce **per prevenzione**. Help CLI corretto. **Provato LIVE** dal runtime installato 0.1.2 (RAW `0.1.1` crasha → `memory search "0.1.1"` ora torna 13 match reali prima mascherati); +7 test; `sertor-core` (solo `episodic_search.py` + help CLI). Verificato sul codice + risposto ad Acta | `memoria-conversazioni` |
| **Daily distill floor — merge-gate del distill** (E10-FEAT-039, merge `58c833a`/PR #216, v0.1.3, 2026-07-22) — dà al passo `distill` una **rete hard**: hook host-facing `distill-floor` (`PreToolUse`) che **BLOCCA il merge di consegna** (`git merge <feature>`/`gh pr merge`) finché la giornata non ha una voce `distill` nel log (distillazione reale o «no» motivato loggato). Gate = **sola presenza** (host-agnostico via `wiki.config.toml`), anti-deadlock, `git merge <mainline>` non bloccato, **fail-open** se indeterminabile. + tool `distill-audit` (`wiki.distill_audit/1`, cross-sessione: wikilink penzolanti + backtick composti) = **CONTESTO advisory** allegato al blocco, MAI gate (prosa rumore-dominata: 228 vs 9 wikilink sul dogfood). Confine D↔N; parità Claude/Copilot. **Prova LIVE del loop** (deny senza distill → allow dopo); +25 test; `sertor-core` engine invariato (solo `wiki_tools`+asset). Gemella lato-enforcement di E10-FEAT-026 | `debito-tecnico` |

*Dettaglio (PR, date, numeri) nella sezione ✅ DONE in fondo alla pagina.*

> 🚀 **Release `v0.1.3` (2026-07-22, tag su `58c833a`, GitHub Release *latest*)** — «daily distill floor»:
> il passo `distill` del rituale wiki ha ora una **rete hard** — l'hook `distill-floor` (`PreToolUse`)
> **blocca il merge di consegna** finché la giornata non ha una voce `distill` (E10-FEAT-039) + tool advisory
> `distill-audit`. Additivo (arriva con `sertor upgrade wiki`). Gate ATTIVATO sul dogfood. Annuncio Acta:
> in attesa di OK utente. Auto-updater: gli host su v0.1.2 vedranno *behind*.

> 🚀 **Release `v0.1.2` (2026-07-21, tag su `beacd03`, GitHub Release *latest*)** — «conversation memory»:
> lettura MCP (FEAT-010) · semantico MCP (FEAT-013) · fix cattura-auto (FEAT-012) · fix FTS5 punctuation
> (FEAT-014, da Acta). Annunciata su Acta (canale Releases) + risposta ad Acta sul fix. **E4 sostanzialmente
> completa** (residui = solo Could 005/006/007). Auto-updater: gli host su v0.1.1 vedranno *behind*.

> **Governance:** Costituzione **v1.4.0** — **Missione & stella polare (North Star)** (differenziatore = **fusione code+doc**; gate «Allineamento alla missione» nel Constitution Check) + **Principio XII «Fail Loud, Fix the Cause»** (v1.3.0: riparare la causa, non disattivare/silenziare per schivare un errore). Distribuita agli ospiti via `sertor-flow` (starter neutro + blocco SDLC).

### 📋 Le 15 epiche (per stato) — stato al 2026-07-22

> **⚠️ Nessuna epica è "finita" finché TUTTE le sue feature non sono consegnate.** Le 4 storiche hanno
> il **nucleo su `master`** ma residui aperti (tranne `sertor-core`, ormai completa); le altre sono
> **da fare** o appena avviate. Una *feature* (`FEAT-NNN`) vive **dentro** un'epica — le capacità già
> consegnate stanno nella tabella sopra, qui c'è il quadro a livello di epica.

| # | Epica | Stato | Residuo / 1° passo |
|---|---|---|---|
| **E1** | [`sertor-core`](../../requirements/sertor-core/epic.md) | ✅ completa (FEAT-011 ✅ merge `34b599a`) | **Nessun residuo Should aperto** — FEAT-011 embedder locale consegnata (2026-06-21). Resta solo il debito P2 **TASK-D04** (rinomina flag installer `--backend`→`--provider`). *(agenzia incorporata ❌ abbandonata by design)* |
| **E2** | [`sertor-cli`](../../requirements/sertor-cli/epic.md) | 🔄 nucleo su master | **residuo:** **FEAT-019 granularità bundle `sertor-flow` + blocco `CLAUDE.md` opzionale (Should P1, richiesta Noetix — attesa esterna)** · **FEAT-020 log `install.event/1` per wiki/flow/lifecycle (follow-up di FEAT-018)** · pip fallback reale (→FEAT-006) · multi-target `sertor-flow` (follow-up) · reviewer clean-code · Codex · PyPI · `configure --check` (deferred) *(packaging ✅ + lifecycle ✅ + hardening Copilot ✅ + wizard config ✅ + Copilot CLI-only ✅ + version-check FEAT-013 ✅ + **FEAT-010 multi-target/non-Python/uv ✅** `eb1f7a3`/#179 + **FEAT-016 ❌ Won't** spike 2026-07-13 + **FEAT-017 onestà auto-updater ✅** `00dcd62`/#180 + **FEAT-018 installer esito-azione + log ✅** `0b45c24`/#202)*. **PyPI/pip: gate CI caduto 2026-07-16 → eseguibile ora** |
| **E3** | [`osservabilita`](../../requirements/osservabilita/epic.md) | 🔄 MVP su master | **export OTel FEAT-005 ✅** + arricchimento span FEAT-013 ✅ + TUI tabella FEAT-014 ✅ + **visibilità RAG/dimostrabilità FEAT-015 ✅** (PR #88) · drift FEAT-012 · metriche aggregate · stima € (Should) · web · CSV/MD |
| **E4** | [`memoria-conversazioni`](../../requirements/memoria-conversazioni/epic.md) | 🔄 MVP acceso + **distribuibile** + **semantico** + **multi-assistente** · **🐛 cattura-auto ✅ FEAT-012** | **🐛 auto-capture ✅ CHIUSO (FEAT-012, merge `9921a34`/PR #210, 2026-07-21):** la cattura non popolava l'archivio (ultima sessione = **2026-07-09**). **Causa reale = gate privacy sull'ambiente sbagliato:** l'hook `memory-capture` gatava su `os.environ["SERTOR_MEMORY"]`, ma il valore vive in **`.sertor/.env`** (letto solo da `Settings` dentro la CLI) → gate sempre `None` → no-op silenzioso. **L'ipotesi 2026-07-16 (path relativo = stessa causa di FEAT-031/032) era errata:** quello era un *secondo* difetto stacked (script non trovato), risolto; sotto restava questo gate, regressione della migrazione A-09 (`.ps1`→`.py`). Fix: `_hooklib.memory_enabled()` legge la stessa fonte della CLI (provato LIVE). · **semantico via MCP ✅ FEAT-013** · residui: remember-this (FEAT-005) · retention (FEAT-006) · ponte second-brain (FEAT-007) — tutti Could *(**semantico via MCP FEAT-013 ✅** `727ab5b`/#212 — `memory_search(semantic=true)` doppio gate + **parità MCP lettura FEAT-010 ✅** `427cf8e`/#208 + cattura Copilot CLI FEAT-008 ✅ + ricerca semantica FEAT-004 ✅ + distribuzione installer FEAT-009 ✅)* |
| **E5** | 🆕 [`retrieval-qualita`](../../requirements/retrieval-qualita/epic.md) | 🔄 FEAT-001+011 ✅ · FEAT-003 T1+T2 ✅ su master | **eval IR ✅** (PR #92) + **graph-eval ✅** (FEAT-011) + skill live ✅ + **FEAT-003 misura fusione + `search_combined` strutturato (tupla, metrica OR) ✅** (merge `42aceaf`+`908bd92`). **Scoperta:** lo «0.17» era artefatto dell'AND; a OR union=1.00, il vero debole è **`search_docs` MRR 0.55** (leva futura). Restano FEAT-002/004/005-007 |
| **E6** | 🆕 [`backend-store-scala`](../../requirements/backend-store-scala/epic.md) | 📋 aperta | adapter PGVector (Should) |
| **E7** | 🆕 [`ingestione-estesa`](../../requirements/ingestione-estesa/epic.md) | 📋 aperta | chunking SQL → **sblocca** schema-SQL |
| **E8** | 🆕 [`conoscenza-schema-sql`](../../requirements/conoscenza-schema-sql/epic.md) | 📋 aperta | bloccata a monte da `ingestione-estesa` |
| **E9** | 🆕 [`second-brain`](../../requirements/second-brain/epic.md) | 📋 da espandere | decidere bivi §9 prima di decomporre |
| **E10** | 🆕 [`debito-tecnico`](../../requirements/debito-tecnico/epic.md) | 🔄 in progress | **FEAT-011 hook freschezza RAG ✅ (merge `29dd30e`, 2026-06-25)** + **FEAT-019 fail-loud breadcrumb hook + fallback STOP agent ✅ (merge `629481b`/PR #125, 2026-06-29)** + **FEAT-018 portabilità OS hook (guardia pwsh) + onestà surface ✅ (merge `8257fd3`/PR #127, 2026-06-30)**; + **FEAT-031 hook wiring ancorato ✅ (merge `e3c2a97`/PR #190, 2026-07-15)** + **FEAT-032 identità hook per script stem ✅ (merge `ddbfb27`/PR #192, 2026-07-17)** — confermata da verifica indipendente (nodo Noetix), chiude la consegna di FEAT-031 **agli ospiti che aggiornano**; + **FEAT-038 `doctor` ancorato alla radice ✅ (merge `7075a0f`/PR #198, 2026-07-18)** — invarianza al cwd provata LIVE, 1° item della coda analisi setup, sblocca FEAT-034; + **FEAT-033 `ritual-check` rileva il default branch ✅ (merge `546cb22`/PR #200, 2026-07-18)** — non assume più `master`, sblocca la forced declaration sugli ospiti `main` (da Noetix); + **FEAT-034 `rag-freshness` post-riparazione + FEAT-035 auto-heal del lock ✅ (merge `5add90d`/PR #205, 2026-07-20 — fuse)** — chiude l'**ULTIMO** item della coda «analisi setup»; **da feedback federazione 2026-07-17: FEAT-033** (`ritual-check` assume `master` → esplode su ospiti con default `main`, Principio X, da Noetix) ✅ · **FEAT-034** (✅ vedi sopra, da Acta) · **FEAT-035** (✅ vedi sopra, da dogfooding) · **FEAT-036** (`upgrade` installa una capability assente, da Noetix) · **FEAT-037** (investigazione: verdetto `index` di `doctor` non spiegabile da `last_index`, da Acta); resta Could (FEAT-014 stdin guard + **FEAT-015 refresh non disinstalla bene** + FEAT-004/005/006/007/008/021/022) + **FEAT-039 daily distill floor ✅ CONSEGNATA (merge `58c833a`/PR #216, v0.1.3, 2026-07-22 — vedi EXEC)** — merge-gate bloccante del distill (`PreToolUse` `distill-floor`) + tool advisory `distill-audit`; **NB: forma finale = merge-block, NON la vecchia idea «estendi wiki-pending-check per la dichiarazione»** (ricalibrata in sessione); Should aperti **FEAT-029** (hook wiki path hardcoded) / **FEAT-030** (emendamento costituzione Product-vs-Fixture Plane) *(**FEAT-009 distribuzione costituzione neutra ✅ 2026-06-19** — PR #82 · **FEAT-003 CI GitHub Actions ✅ 2026-06-23** — Windows + Linux verdi su PR #96, prima CI del progetto · **FEAT-013 allineamento config dogfood↔ospite ✅ 2026-06-23** — dogfood su `.sertor/.env`+`.sertor/.index`, resolver host-agnostico · **FEAT-012 governance nel corpus ✅ 2026-06-23** — costituzione+plan-template indicizzati · unif. venv ✅ · host-agnosticità asset **FEAT-001/009/010 ✅** · disciplina MCP-first agli ospiti ✅, 2026-06-19)* · **audit asset first-party 2026-06-26** ([[sertor-strumenti-audit]]) → FEAT-016..024 (P0 ✅ tutti mergiati; P1 FEAT-019 ✅) |
| **E11** | [`multiutente`](../../requirements/multiutente/epic.md) | 📋 differita | finché il caso d'uso team non è concreto |
| **E12** | 🆕 [`usabilità`](../../requirements/usabilita/epic.md) | 🔄 **MVP completo** (FEAT-001/002/010 ✅ su `master`) | **owner del layer UX** (skill agentiche + agente *concierge* + poche primitive deterministiche, D↔N). **FEAT-001 `doctor` ✅** (PR #100, fix freschezza #102) + **FEAT-002 guided-setup ✅** (skill + agente `concierge` model-pinned, PR #101) + **FEAT-010 discoverability CLI ✅** (`uv run --project .sertor`, PR #103/#104) + **FEAT-012 install host-aware ✅** (PR #115, fix dogfooding + NRT, 2026-06-26). MVP (doctor + guida + invocazione robusta) coperto. Restano Should: config-recommender (FEAT-004), explain (FEAT-005), search-diagnose (FEAT-007), concierge pieno (FEAT-009, **stub avviato**), progress GloVe (FEAT-003). Assorbe item UX-facing da E2/E3/E10 (cross-ref) · **FEAT-013 description trigger-rich EN** (da audit, P0) |
| **E13** | 🆕 [`documentazione-marketing`](../../requirements/documentazione-marketing/epic.md) | 🔄 **Fase 1 COMPLETA** (FEAT-001..008 ✅) | **owner della documentazione ESTERNA + marketing** (confine netto: E12 = UX in-product · `wiki/` = doc interna · meccanismi nelle epiche d'origine — E13 li *racconta*, cross-ref). **Fase 1 — doc utente ✅ TUTTA CONSEGNATA:** getting-started + README valore (A-18, PR #172) · why-sertor + indice docs + tutorial + troubleshooting + CHANGELOG + reference (batch 2026-07-12). **Fase 2 — marketing pubblico** (posizionamento, demo/screencast, landing/sito) **SBLOCCATA dal go-public** (repo pubblico dal 2026-07-13); non più bloccata dalla privacy del repo. Resta interim `git+url` (PyPI FEAT-006, espansione go-public/PyPI congelata utente 2026-07-17) ma è distribuzione, non blocco marketing → Fase 2 avviabile quando si vuole |
| **E14** | 🆕 [`speclift`](../../requirements/speclift/epic.md) | 🔄 FEAT-001 ✅ su master | **`diff → requisiti EARS ancorati`** (handoff da Sinthari, sandwich deterministico + moat). **FEAT-001 self-host ✅** (vendoring Adapter B/MCP, merge `bbfb74d`/PR #136, 2026-07-01). **FEAT-003 SpecAudit 🔄 self-host/dogfood vendorato ✅ (2026-07-02)** — verdetto per-requisito top-down; vendorato in `packages/specaudit` (stampo speclift, 59 test verdi 3.11+3.12, skill dogfood in `.claude/`); resta distribuzione esterna (gemella FEAT-002). Restano: **FEAT-002 distribuzione su ospiti** (casa **decisa 2026-07-14: `sertor-flow`**, fold) · **FEAT-004 Debrief / FEAT-005 Guida-al-test** (Could). Nato dalla collaborazione agent-to-agent (feedback CLI→MCP recepito upstream) |
| **E15** | 🆕 [`fedelta-dogfood`](../../requirements/fedelta-dogfood/epic.md) | 🔄 nuova (2026-07-03) · FEAT-027 ✅ · **FEAT-002 ✅** (sync+guardie RAG; assorbe F3-file, chiude E10-FEAT-025) · **⚠️ MODELLO RIORIENTATO (direttiva utente 2026-07-03):** dogfood = **real-install, traccia HEAD** (FEAT-001 self-install), NON sandbox; ospiti = versioni+auto-updater; sync/script (F2/FEAT-027) → **interim**. **FEAT-005 ✅** (installer preservante `plan-template`, sblocca la governance del self-install) · **FEAT-001/F1 ✅ + F7** (runtime `.sertor/` installato da git HEAD, #150; CI-fix guardia venv #151) · **FEAT-008/F8 ✅ MERGED (#152, b849a1f)** (re-lock runtime a HEAD dogfood-only; post-merge eseguito sul proprio merge 879b688→b849a1f) · **asset-install (FEAT-001 scope B) ✅ IMPLEMENTATA su branch `089` (2026-07-06)** — i 3 veri installer eseguiti sul dogfood: **process-fidelity raggiunta**. `.env`/costituzione/`.mcp.json`/`wiki.config` preservati, core invariato, idempotenza provata (2° giro `block:0`). **FEAT-010 ✅** (`.gitattributes` LF: dogfood+bundle+`sertor install rag` lo deposita create-if-absent → azzera churn CRLF su ogni host Windows). CLAUDE.md riconciliato via **ownership-note** (blocchi=contratto client-form · prosa IT=applicazione dogfood autoritativa; nessuna prosa dogfood persa). Sync/script retrocessi a **guardia-non-fonte**. `wiki/log.md` legacy scartato → **FEAT-006** (staleness template, promossa). Gate verde: root 1156·sertor 492·flow 142·kit 151·speclift 122·specaudit 59, ruff clean. [[asset-install-installer-dry-run-2026-07-04]] · **FEAT-009 ❌ CHIUSA not-a-bug** (`.mcp.json --directory` era misdiagnosi: `registered=False` = artefatto cwd del *doctor*, non del template; `Settings.load` self-localizing). [[feedback_dogfood_solo_via_install_versionbump]] | **Il dogfood prodotto e verificato dai veri installer** — fedeltà a **due livelli**: asset-fidelity (stessi file, oggi parziale via sync) + **process-fidelity** (prodotto dagli installer, oggi **assente ovunque**). Da audit 2026-07-03 ([[audit-fedelta-dogfood-2026-07-03]]): FEAT-001 harness process-fidelity (Must) · FEAT-002 sync completo+guardie (Must) · FEAT-003 artefatti RAG mancanti · FEAT-004 divergenze dev↔client · FEAT-005 installer preservante `plan-template` (≡E10-FEAT-028) · FEAT-006 staleness inversa template. **Correzione empirica:** `specify init --force` preserva la costituzione, clobbera solo `plan-template.md` |

*Legenda:* ✅ completa · 🔄 nucleo consegnato, residui aperti · 📋 da fare · 🆕 nuova. *Numerazione `E1`..`E15`: vista standing per epica (E1 nucleo `sertor-core`, E11 `multiutente` differita, E12 `usabilità`, E13 `documentazione-marketing`, E14 `speclift`, E15 `fedelta-dogfood` nuova 2026-07-03 da audit fedeltà); E1–E4 storiche, E5–E10 dal backlog audit 2026-06-16, E12 dall'esplorazione UX 2026-06-23, E13 dalla richiesta 2026-06-24, E15 dalla domanda «abbiamo fatto su tutto Sertor?».*

### 🔄 IN PROGRESS (dettaglio)

> **✅ CONSEGNATA (2026-06-25, merge `29dd30e` su `master`): E10-FEAT-011 enforcement freschezza RAG.**
> SpecKit completo specify→plan→tasks→implement, Constitution
> **12/12 + missione**, ruff clean; test: sertor **395** · kit **131** · root non-cloud **1128** (3 skip
> packaging noti); `sertor-core` **INVARIATO** (Principio XI). *Cosa:* due hook host-facing distribuiti via
> `sertor install rag`, parità Claude/Copilot — `rag-freshness.ps1` (SessionEnd: re-index incondizionato via
> vehicle + `doctor` + persiste `.sertor/.rag-health.json` `rag.health/1`; exit 0 sempre, no LLM) +
> `rag-freshness-start.ps1` (SessionStart Claude: ripesca lo stato e **induce** la correzione se `degraded`;
> Copilot = prompt statico). + reclass `CLAUDE.md` step 5/8 «enforced via hook» + `RUNTIME_IGNORES` esteso.
> *Dove:* branch `076`, commit spec `e89dcf6` · plan `abf507f` · tasks `f7b05ca` · impl `5f06cbd` · +FEAT-014
> `913a824`. *Test funzionale (dogfooding) ✅:* hook eseguito a mano → re-index reale (indice riscritto) +
> `rag-health.json` `verdict: healthy` 4/4 aree pass. *Prossimo passo concreto:* smoke MCP + `gh run list`
> (CI Win/Linux sul merge) + distill entità wiki. *Follow-up non-bloccante:* prova LIVE su ospite reale
> (quickstart §6); **FEAT-014 (Could, tracciata)** = fix stdin-hang dell'hook in invocazione manuale
> (`IsInputRedirected` guard) — emerso in dogfooding, non si manifesta in produzione.
>
> *(E12-FEAT-002 `guided-setup` ✅ e E12-FEAT-001 `doctor` ✅ già su `master` — vedi ✅ Capacità consegnate.)*
>
> **🔎 Verifica backlog 2026-06-25 (feature-per-feature, 13 epiche, via RAG+grafo+git).** Stato dichiarato
> accurato **~96%**, le ✅ tutte con evidenza concreta (file:symbol + commit/merge), le 📋 assenze pulite.
> Drift corretto nelle fonti durevoli: **E5-FEAT-008/009** (genesi/feedback eval) erano dati 📋 ma sono ✅
> skill bundlate (`eval-suite-author`/`eval-feedback`, vehicle presenti); **E12-FEAT-001/002/010**
> (doctor/guided-setup/discoverability) marcate in-corso negli `epic.md` ma ✅ su `master` (gli `epic.md`
> **lag** dietro l'EXEC); ripulito il residuo inerte `.venv-core/`. Sfumature: E11-FEAT-M01 ha bozza EARS
> congelata; E13-FEAT-001/002 parzialmente pre-coperte da README/`docs/` (delta = consolidamento). Finding
> collaterale (non roadmap): `.env` dogfood ha `SERTOR_OBSERVABILITY_OTEL` attivo senza collector su
> `localhost:4318` → rumore di connessione a ogni comando.

**🔄 In pipeline ora:** **Backlog dall'audit indipendente SWOT (2026-07-02).**

- **Audit SWOT + backlog azionabile — ✅ COMPLETO (2026-07-11).** 🎉 **Tutti i 20 item A-01..A-20 consegnati su `master`.**
  *Cosa:* audit completo del workspace (5 subagent paralleli: core · packages/CI · governance · backlog ·
  doc/wiki) → SWOT + **20 item prioritizzati P0–P2** (tabella sotto, dettaglio/evidenze in
  [[audit-swot-2026-07-02]]). Attaccati **in ordine da A-01 in giù**, con checkpoint a fine di ogni item.
  *Consegnato (su master):* **A-01 → A-20 ✅ TUTTI** (merge `e6096e4`/PR #174 chiude A-19, l'ultimo) → **🎉 backlog audit COMPLETO** — dettaglio nella tabella SWOT sotto. A-11 folded in E6
  FEAT-007; A-12/A-13 riconciliazione `epic.md`↔EXEC + `updated:`=data secca (PR #166); A-14 hardening
  `sertor-core` (parse guardato + scrub `detail` MCP, PR #167); A-15 policy `/VERSION` bump manuale a
  release (PR #168); **A-16** lifecycle robusto (content-guard uninstall + marker fail-loud, PR #169).
  **Finding auto-updater** (PR #170): inerte su **repo privato** (fetch `/VERSION` 404) → macchina validata
  live → **E2-FEAT-017** (gated sul go-public). **A-17 ✅** (merge `064c5eb`/PR #171) — sync/orfani
  installer: (1) `--check` **exit-code** sul `sync` (gate drift locale); (2) uninstall **senza orfani** —
  `settings.json` vuoto cancellato (`delete_if_empty` sul condiviso) + **dir vuote pruned**
  (`prune_empty_dirs`, i 3 consumer). **Chiude il bug tracciato «`.claude/` orfano».**
  - **A-18 — ✅ CONSEGNATA (merge `6e40ccc`/PR #172, 2026-07-11).** E13 Fase 1 Musts (doc utente MVP):
    **nuovo `docs/getting-started.md`** (percorso unico host-agnostico «dal nulla al primo valore»,
    entrambe le varianti CLI Claude+Copilot affiancate, esempio finale di fusione code+doc via
    `search_combined`) + **riscrittura `README.md`** valore-first (apre col differenziatore code+doc +
    esempio, fatti preservati, punta al getting-started come ingresso unico) + rimandi di convergenza in
    `install-claude`/`install-copilot`/`retrieval`. Pipeline SpecKit completa (requirements→specify→
    clarify→plan→tasks→implement); Constitution **12/12 + missione PASS** (authoring, `sertor-core`/CLI/
    installer **invariati**, D↔N); ruff clean + CI verde (1171 test). Post-merge: re-lock `064c5eb→6e40ccc`
    · re-index 1330doc/14536chunk (9+7) · smoke MCP verde (`getting-started.md` servito). **Chiude
    E13-FEAT-001+002.** *Prossimo:* **A-19** (o differirlo, vedi caveat YAGNI Codex).

- **E14-FEAT-001 — self-host di SpecLift (vendoring Adapter B) — ✅ CONSEGNATA (merge `bbfb74d`/PR #136, 2026-07-01) su `master`.**
  *Cosa:* SpecLift (capacità `diff → requisiti EARS ancorati`, **handoff da Sinthari**) vendorato come membro
  workspace `packages/speclift` per il dogfooding. **Storia collaborativa agent-to-agent:** handoff → nostro
  feedback «i consumatori esterni usano l'**MCP**, non la CLI» → Sinthari ha reso l'`EvidenceLocator` **pluggable**
  (Adapter B: agente+MCP) e mergiato su `master` (`5ee6fc1`) → noi **adottiamo l'Adapter B via vendoring puro**
  (zero fork, convergenza). Retrieval via MCP `search_code` (three-gear flow); Adapter A CLI dormiente;
  `sertor-core` INVARIATO. 2 divergenze di packaging (Python `>=3.11`, `jsonschema`→dev) + LICENSE MIT.
  *Test:* speclift **122** (su 3.11 e 3.12) · non-regressione sertor 487 / kit 151 / flow 140 / core-root 1064;
  Constitution **12/12 + missione**. **Dogfood e2e verde** (moat: anchor `verified`). Post-merge: re-index
  (1186 doc) + smoke MCP verde (code-graph auto-reload sui simboli nuovi). *Follow-up:* distribuzione su ospiti =
  **E14-FEAT-002** (casa **DECISA 2026-07-14: `sertor-flow` — fold**; speclift/specaudit zero-deps+MCP →
  nessun conflitto d'ortogonalità; esclusi dal publish PyPI; impl = feature media da decomporre);
  famiglia SpecAudit/Debrief = E14-FEAT-003/004/005.

- **E2-FEAT-015 — default model-policy subagent Copilot CLI — ✅ CONSEGNATA (merge `4e30d00`/PR #135, 2026-07-01) su `master`.**
  I 5 agenti Sertor-authored su Copilot CLI ricevono un `model:` di default da una fonte unica versionata
  (`sertor_install_kit/model_policy.py`), fail-loud install-time su profilo incompleto; path Claude byte-identico,
  `sertor-core` invariato. Meccanismo verificato = `model:` nel frontmatter `.agent.md` (non un blocco settings).
  Constitution 12/12 + missione; kit 151 · sertor 487 · flow 140 · root 1134/3-skip. *Scope out promosso:*
  modello per gli `speckit.*` → **E2-FEAT-016** (Could, previa spike).

- **E10-FEAT-019 ✅ CONSEGNATA (merge `629481b`/PR #125, 2026-06-29) su `master`.** SpecKit completo
  specify→plan→tasks→implement, Constitution **12/12 + missione**, ruff clean; test: sertor **443** ·
  sertor-flow **137** · kit **132** · root **1131 passed** (3 skip packaging `git+url`); `sertor-core`
  **INVARIATO** (Principio XI). Post-merge: re-index dogfood OK (1021 doc/11598 chunk, +17/~22) + smoke MCP
  verde (filtro `where` sano, indice fresco). *Follow-up non-bloccante:* prova LIVE su ospite Claude/Copilot
  reale (comportamento runtime del fallback agent = giudizio LLM, verificabile solo live — confine D↔N
  dichiarato). Dettaglio in ✅ Capacità consegnate sopra.
- **E10-FEAT-018 ✅ CONSEGNATA (merge `8257fd3`/PR #127, 2026-06-30) su `master`.** Portabilità OS degli
  hook (guardia `pwsh` + gap dichiarato, no gemello bash) + onestà sui surface inerti via `InstallReport.notes`;
  modulo puro `host_env.py` nel kit; detect-only (wiring invariato). Constitution **12/12 + missione**; test
  sertor **451** · kit **139** · root **1131 passed**; `sertor-core` invariato, schema `install.report/1`
  invariato. *Follow-up non-bloccante:* prova LIVE su ospite mac/Linux senza `pwsh`; fix wiring Claude portabile.
- **E10-FEAT-026 — rituale wiki anti-skip — ✅ CONSEGNATA (merge `e906e34`/PR #176, 2026-07-12).**
  MVP parte 1+3 (Should P1, dai 2 feedback ospiti convergenti). **Nuovo sottocomando `sertor-wiki-tools
  ritual-check`** (deterministico, zero-LLM, sola lettura): scope via git-diff-vs-base (fail-loud/`--pages`),
  elenca candidati **distill** (≥2 pagine changed con ≥2 nuovi backlink incrociati, 0 nuove `concepts/`/`tech/`)
  + **drift** (`stale-updated`/`neighbor-of-change`-non-hub/`capability-exec` config-driven) + **scaffold di
  dichiarazione**. + **dichiarazione forzata** a fine step nel blocco host-facing + playbook. Confine D↔N (tool
  trova, agente giudica); gemella lato-giudizio di FEAT-011. SpecKit completo; +9 test; suite 1180 verde, ruff
  clean; `sertor-core` engine invariato. **Fuori scope:** parte 2 (wiki-curator) + parte 4 (moduli derivati).
- **E2-FEAT-010 (residuo ergonomia installer) — ✅ CONSEGNATA (merge `eb1f7a3`/PR #179, 2026-07-13).**
  Scelta utente «procedi con tutte le rimanenti di sertor-cli a partire da 010». MVP: **multi-target**
  (`--assistant` CSV/`all` → un comando, container disgiunti, deps runtime una volta, report aggregato +
  note propagate, fail-fast; single-value invariato) · **avviso non-Python** (`host_env.is_python_host`
  nel kit → nota advisory, sorgenti intatti) · **guida uv-assente onesta** (installa uv · `--no-deps` ·
  pip non ancora disponibile). Pip fallback reale **rinviato a FEAT-006/go-public** (deps workspace non
  pubblicate — decisione utente). `sertor-core` invariato; kit 178 · sertor 523 · suite 1180 verdi, ruff
  clean; smoke CLI reale + smoke MCP fresco. Post-merge: re-lock `9b5b842→eb1f7a3` · re-index incrementale
  (1353doc/14778chunk, +4/~5) · smoke MCP verde (`find_symbol("is_python_host")`→`host_env.py:23`).
  *Fuori scope tracciato:* multi-target `sertor-flow` (follow-up) · reviewer clean-code (feature a sé).
- **E2-FEAT-016 (model policy speckit su Copilot CLI) — ❌ WON'T / non-applicabile (spike 2026-07-13).**
  La doc ufficiale Copilot CLI **non consuma i prompt-file** (`.github/prompts/*.prompt.md` = costrutto
  VS Code Chat); gli `speckit.*` sono prompt-file → sulla CLI **nessuna superficie li invoca**, quindi
  nessun meccanismo per `model:`. Sertor è copilot-cli-only (FEAT-012); la model-policy CLI utile è già
  FEAT-015. Chiusa; riaprire solo se la CLI aggiunge il consumo dei prompt-file. [Issue #1195].
- **E2-FEAT-017 (fetta onestà auto-updater) — ✅ CONSEGNATA (merge `00dcd62`/PR #180, 2026-07-13).** Il SessionStart
  emette un cenno **una-tantum** «SERTOR UPDATE CHECK UNAVAILABLE» quando `verdict=unknown` (GET `/VERSION`
  fallita — offline o repo privato), con flag persistente `unknown_notified` (no nag; reset a verdetto
  risolto); parità Copilot via prompt statico. Prima l'updater era **muto** su `unknown`. `sertor-core`
  invariato, +4 test parity. **Pezzo strutturale ora SBLOCCATO dal go-public** (repo pubblico → GET `/VERSION`
  = **200**, verificato 2026-07-13) — l'updater ora *può* verificare; rileverà `behind` alla prima release+bump.
- **🌐 GO-PUBLIC — DECISO ED ESEGUITO (2026-07-13).** Scelta utente «io andrei pubblico», sequenza «repo public
  ora, PyPI a CI verde». **✅ FATTO E VALIDATO:** audit segreti/history **CLEAN** (912 commit, 0 segreti, no
  rewrite) → **repo `themetriost/Sertor` PUBBLICO** · **prima release `v0.1.0`** (GitHub Release + tag su
  `00dcd62`, *latest*) · **auto-updater live** (3 scenari validati: up-to-date `/VERSION`=200 reale · behind ·
  unknown-una-tantum FEAT-017) · **install esterno provato** (`uvx` dal tag pubblico, fuori dal checkout, 85 pkg,
  `sertor --help` ok) · hardening `.gitignore` (`*.pem`/`*.pfx`/`*.p12`). **⏳ era GATED al 1° ago (CI ferma per
  billing) → 🔓 GATE CADUTO il 2026-07-16: la CI è tornata verde in anticipo (8/8 su PR #190), il residuo è
  eseguibile ORA:** **publish PyPI** dei 4 pacchetti (= **E2-FEAT-006**, Won't→planned; darà `pip install sertor`) +
  **pip fallback reale** (FEAT-010 residuo, possibile con deps pubblicate) + eventuale **bump `/VERSION`** che
  accende `behind` in produzione (la v0.1.0 è baseline, nessun bump). **🔓 Sbloccato ora:** **E13 Fase 2**
  (marketing). Casa del residuo: [`requirements/sertor-cli/go-public-pypi/`](../../requirements/sertor-cli/go-public-pypi/requirements.md).
- **✅ CI TORNATA VERDE (verificato 2026-07-16)** — il blocco per billing («CI ferma fino al 1° ago») **non è più
  vero**: la PR #190 ha girato con **8/8 check SUCCESS** (test Windows+Ubuntu py3.11/3.12, smoke Claude+Copilot).
  **Conseguenza:** il gate del residuo go-public **è caduto in anticipo** → PyPI publish + pip fallback sono
  eseguibili **ora**, non dal 1° agosto. Riprende anche l'auto-merge/uso normale della CI come gate pre-merge.
- **✅ E10-FEAT-032 — identità hook per script stem — CONSEGNATA (merge `ddbfb27`/PR #192, 2026-07-17).**
  **Confermata dalla verifica indipendente del nodo Noetix** (il dogfood era teste contaminato: bug prodotto
  sul nodo che ha scritto il fix), poi corretta. *Il bug:* `settings_merge.py` usava **la stringa del comando
  come identità** dell'hook → cambiare il wiring **non aggiornava, duplicava** (Claude: vecchia rotta + nuova,
  la vecchia **ancora attiva** → FEAT-031 non arrivava a chi aggiorna) oppure **non atterrava affatto**
  (Copilot: `cwd` aggiunto ma command invariato → dedup scartava la nuova, in silenzio). *Il fix:* l'identità
  è ora lo **stem dello script** (`rag-freshness` da `.py` o `.ps1`) — un solo cambio chiude **tutte e tre**
  le transizioni insieme (`.ps1`→`.py`, relativo→ancorato, `cwd` aggiunto) invece di rincorrerle una per una.
  I due contratti sono espliciti: `install` (`replace_stale=False`) non rimuove **e non duplica più** — lascia
  la forma stantia e la **nomina** nel report puntando a `upgrade` (Principio XII: prima taceva); `upgrade`
  (`replace_stale=True`) sostituisce in place e **collassa** le rese multiple (un hook = un wiring per evento).
  *Deliberatamente NON* si è delegato `install`→`upgrade`: romperebbe la non-distruttività che definisce
  `install`. **+10 guardie** (`test_settings_merge_identity.py`) che asseriscono l'**esito su un host che
  aggiorna**, non la forma dell'asset — il buco da cui era passato tutto. `sertor-core` invariato.
  **Prova sul campo:** il re-install sul dogfood ha collassato le voci duplicate → `.claude/settings.json` ora
  ha **9 hook, uno per stem, tutti ancorati** (lo stato «duplicato da non versionare» non esiste più).
- **Prossimo passo aperto — CODA (decisioni utente 2026-07-18, analisi [[setup-dichiara-presunzione-non-azione]]):**
  **✅ (1) FEAT-038 `doctor` ancorato — CONSEGNATA** (`7075a0f`/PR #198) + **✅ (2) FEAT-033 `ritual-check` rileva il default
  branch — CONSEGNATA** (`546cb22`/PR #200, 2026-07-18): `_resolve_base` non assume più `master` — rileva il default a
  runtime (`origin/HEAD` → candidati ordinati esistenti → fail-loud invariato); `--base` invariato; dogfood `master` non
  regredisce (verificato LIVE); 4 test (main/master/--base/orphan). Sblocca la forced declaration del rituale sugli ospiti `main`.
  + **✅ (3) E2-FEAT-018 — installer esito-azione + log — CONSEGNATA** (`0b45c24`/PR #202, 2026-07-18): nuovo esito additivo
  `Outcome.PRESENT_DIVERGENT` (presente-ma-diverso → non toccato, non più «skipped» muto) su sertor+flow, **assorbe
  E10-FEAT-036**; deps oneste; log `.sertor/.install-log.jsonl` (`install.event/1`) sul rag install — **provato LIVE**.
  P2-log per wiki/flow/lifecycle = follow-up **E2-FEAT-020**.
  + **✅ (4) E10-FEAT-034 (+ FEAT-035 fusa) — `rag-freshness` post-riparazione + auto-heal del lock — CONSEGNATA**
  (`5add90d`/PR #205, 2026-07-20): l'hook ora ripara-poi-misura (re-index → doctor → verdetto post-riparazione,
  `reason` completo); `_IndexLock` auto-guarisce il lock con PID morto (helper `_pid_alive` cross-OS, reclamo
  osservabile). **Provato LIVE** (PID morto→procede / PID vivo→locked); SpecKit completo, Constitution 12/12.
  → **🎉 La coda «analisi setup» è CHIUSA** (tutti e 4 gli item consegnati).
  *Tesi unificante:* «il setup dichiara ciò che presume, non ciò che è successo» (Principio XII).
  **Prossimi candidati (nessuno deciso — da scegliere con l'utente):** E13 Fase 2 (marketing, gated go-public) ·
  E5-FEAT-003 (`search_docs`) · E2-FEAT-020 (P2-log wiki/flow/lifecycle) · verifica empirica E4 cattura-auto (sotto).
  (2-bis) **go-public/PyPI: FERMO — decisione utente 2026-07-17 «non ancora»**.
  È *tecnicamente* sbloccato (CI verde, gate 1° ago caduto) ma **non si procede**: il repo resta pubblico con
  `v0.1.0`, niente `pip install sertor`, gli ospiti installano via `uvx` dal tag, l'auto-updater resta dormiente
  fino al primo bump di `/VERSION`. Casa del residuo:
  [`go-public-pypi`](../../requirements/sertor-cli/go-public-pypi/requirements.md). **Non riproporlo come
  «prossimo passo» finché l'utente non lo riapre.** (3) 🐛 **E4 cattura-auto memoria — ✅ CHIUSO (FEAT-012, 2026-07-21):**
  il controllo empirico ha **smentito** l'ipotesi «chiusa da sé»: `memory list` mostrava ancora `2026-07-09` come ultima
  sessione **nonostante** FEAT-031/032 installate → il wiring ancorato NON bastava. **Causa reale = gate su `os.environ`**
  invece che su `.sertor/.env` (fonte del valore, letta solo dalla CLI) → no-op silenzioso; corretto in FEAT-012
  (`_hooklib.memory_enabled()`). (4) **E13 Fase 2** (marketing) · E5-FEAT-003 `search_docs`.
  (5) **Noetix — bundle governance divisibile = `E2-FEAT-019`** (Should P1, già a backlog: *«granularità
  bundle `sertor-flow`, blocco `CLAUDE.md` opzionale»*, da decomporre). Richiesta **presa in carico** (risposta
  affissa su Acta, `2026-07-17-sertor-presa-in-carico-bundle-governance-divisibile`); **dobbiamo ancora
  l'analisi nel merito** delle 5 domande (divisibilità, blocco opzionale, superficie del
  `configuration-manager`, parti neutre della costituzione, se un nodo che si ferma sopra gli EARS è in
  bersaglio). **Debito verso un altro nodo**, non verso noi stessi — è l'unico item con un'attesa esterna.

**Candidati a valore = Should aperti:**

- **FEAT-003 → dedup dei risultati near-duplicate ✅ (2026-07-07, merge `67b4177`)** — la leva `search_docs`
  è stata affrontata: la causa misurata era la **duplicazione di contenuto** (blocchi `CLAUDE.md` ↔ copie
  bundle `assets/**`) che saturava il top-k. Dedup fuzzy (shingle+containment) a query-time → `search_docs`
  @5 0.75→0.88, union solida, `search_code` intatto; baseline eval ri-registrato al corpus 1302 (dedup on).
  **Leva profonda residua tracciata (nuova):** **competizione tra doc *correlati* (non duplicati)** al
  confine k=3 — il `search_docs` hit@3 oscilla con la crescita del corpus perché contenuto *diverso* ma
  affine (spec/log della stessa feature) compete con la pagina-concetto attesa. Il dedup non lo tocca (non
  sono duplicati); serve una leva distinta (contextual retrieval / re-ranking di diversità / gestione query),
  **solo se** mostra lift misurato. *(HyDE escluso: niente LLM nel run, RNF-3.)*

*(Le capacità già consegnate stanno in ✅ Capacità consegnate sopra e in ✅ DONE in fondo.)*

### 📋 PLANNED (per priorità)

> **Riorganizzato il 2026-06-16 dal [backlog audit](backlog-audit-2026-06-15.md):** tutto il non-fatto è
> ora raggruppato in epiche con casa durevole. Sei **nuove epiche** danno casa al materiale orfano; le
> epiche esistenti restano sotto.

**Nuove epiche (aperte, da decomporre quando prioritarie):**
- **Qualità del retrieval** (`retrieval-qualita`) — *primo passo a valore:* ground-truth + metriche
  (Must). Poi search_code architetturale, calibrazione soglie, eval `cloud` (Should); tecniche avanzate
  HyDE/filtro-metadata/contextual-retrieval (Could, ex `hardening-produzione` H7/H8/H11).
- **Backend store & scala** (`backend-store-scala`) — *primo passo:* adapter PGVector (Should). Poi
  Mongo/Atlas, indici multi-provider, fan-out su >2 corpora, scala del code-graph (Could).
- **Ingestione estesa** (`ingestione-estesa`) — repo remoti via URL, formati non-testo (PDF/DOCX/notebook),
  chunking PS/T-SQL/PL-SQL/Bash, no-code-first (Could). **Sblocca** la conoscenza-schema SQL.
- **Conoscenza-schema SQL** (`conoscenza-schema-sql`) — schema nel corpus (Should) + schema-graph + fusione
  col codice applicativo (Could). **Bloccata a monte** dal chunking SQL di `ingestione-estesa`.
- **Second-brain / Meta-Sertor** (`second-brain`) — **da espandere:** MVP = catalogo flotta + query
  federata (quasi solo wiring); poi harvest/promote, trust, asset-registry. Bivi §9 (solo/team, meta-corpus
  vs fan-out, meta-grafo, nome) **da decidere prima di decomporre**.
- **Debito tecnico & igiene** (`debito-tecnico`, interna) — host-agnosticità asset residui, unif. venv,
  CI Linux (Should); plugin rituale portabile, igiene wiki, selettività bundle `sertor-flow` (Could).

**Epiche esistenti, in attesa:**
- **Sertor-core — ✅ nessun residuo aperto** — l'**agenzia incorporata** è **❌ abbandonata by design**
  (2026-06-16, «non ci serve»; l'agentic RAG è già ✅ composito via MCP+agente). *(FEAT-009 ✅ DONE merge
  `3ec47f1`; FEAT-008 Wiki↔RAG ✅ composita.)* L'epica primaria del prodotto è sostanzialmente **completa**.
- **Memoria — Should/Could** — FEAT-004 (ricerca semantica opt-in), FEAT-005 (remember-this), FEAT-006
  (retention), FEAT-007 (ponte second-brain), **FEAT-009 distribuzione via installer (Must/debito)**,
  FEAT-008 (cattura multi-assistente), FEAT-010 (parità MCP `show`/`list`). *(FEAT-003 ✅ DONE.)*
- **Osservabilità 2 — Should/Could** — export OTel (FEAT-005), metriche aggregate (FEAT-006), **stima €
  (FEAT-007, Should, non fatto)**, web mode, trend qualità, metriche graph/wiki, export CSV/MD (FEAT-011).
- **Distribuzione/CLI — Could (Must chiuso)** — *packaging del pacchetto ✅ FEAT-001 DONE (PR #68) e
  lifecycle upgrade/uninstall ✅ FEAT-008 DONE (PR #71), entrambi 2026-06-17*;
  restano: wizard config (FEAT-003, Should), ergonomia installer (FEAT-010), **Codex** (FEAT-007/009
  Could, non avviato per scelta utente), PyPI (Won't) — gating sulla **licenza MIT scelta** per i
  pacchetti (PyPI pubblico resta da aprire).
- **Multiutente** — epica differita finché il caso d'uso team non è concreto.
- **Agenzia RAG incorporata** — ❌ **abbandonata by design (2026-06-16, decisione utente)**: l'agentic RAG
  è già ✅ composito (MCP+agente) e un agente nel core con modello minore non lo migliorerebbe; i 36 REQ in
  `sertor-core/motore-agentico/` restano **elicitazione storica**, non pianificata.

<!-- EXEC:END -->

### ✅ DONE (su `master`, le rilevanti)

- **🚢 Cattura memoria su GitHub Copilot CLI (FEAT-008 `memoria-conversazioni`, feature 073, 2026-06-22)** —
  chiude il rischio **R-1 dell'epica** (cattura host-specifica) per il secondo assistente: l'MVP memoria
  era host-agnostico **tranne la cattura**, che aveva un solo adapter `claude-code`. Nuovo adapter
  **`copilot-cli`** dietro la 8ª porta `TranscriptCaptureAdapter` (nessuna porta/entità nuova, **Principio
  X/I/III**): legge `~/.copilot/session-state/<uuid>/events.jsonl` (Copilot CLI **1.0.63**), mappa i soli
  turni `user.message`/`assistant.message` (testo = `data.content`, niente tool/diff — REQ-008), associa la
  sessione al progetto via `cwd`/`gitRoot` del `session.start` con **regola asimmetrica** (`cwd` dentro il
  progetto / `gitRoot` lo contiene → niente misattribuzione, R-CM-3). **Rende vivo** l'hook `SessionEnd`
  già depositato da FEAT-009 (prima inerte): l'intero tier a valle — archivio · full-text (FEAT-002) ·
  semantica (FEAT-004) · distillazione (FEAT-003) — opera su Copilot **senza modifiche**. Additivo a leva
  spenta (gate `SERTOR_MEMORY`, default adapter `claude-code` invariato, import lazy); stdlib-only,
  best-effort non-fatale (parità Claude); fixture offline. **Design risolto empiricamente** (dogfooding su
  sessioni Copilot reali della macchina) — le 7 forche di scope chiuse senza indovinare. SpecKit completo
  specify→implement, **Constitution 12/12 + missione** (pre e post), **1039 test non-cloud verdi** (32+8
  nuovi), ruff pulito, `sertor-core` invariato fuori dai 4 punti. **Debito tracciato:** `SERTOR_MEMORY_ADAPTER=copilot-cli`
  nel template `.env` dell'installer → FEAT-009 (backlog epica). Pagina [[feat-008-cattura-copilot-cli]].

- **🚢 Valutazione del retrieval & non-regressione (FEAT-001 `retrieval-qualita`, feature 065, PR #92, 2026-06-20)** —
  prima feature dell'epica E5: trasforma «funziona» in «**misurato e presidiato**» (Principio V), host-side
  su qualunque progetto. Promuove l'harness `evaluate` (sepolto nei test) a capacità di prima classe:
  sottocomando **`sertor-rag eval`** — `run` (hit-rate@k/MRR sulla suite TOML versionata `eval/suite.toml`
  + dettaglio per-query + **gate di non-regressione** baseline+tolleranza, exit 1 sotto soglia),
  `add-case`/`validate-path`, `--compare`, **`--by-kind`** (instrada symbol→code-graph). Servizio puro
  `services/eval/`; riusa `evaluate` con estensione non-breaking (`EvalReport.per_query`); accesso al
  retrieval **solo via vehicle** (Principio XI) — il core/CLI **non chiama mai un LLM**. Skill
  `eval-suite-author`/`eval-feedback` (genesi assistita + feedback = giudizio dell'agente, vehicle-only)
  cablate nell'installer **dual-target** (Claude + Copilot). **Scoperta dal vivo:** il run nudo dava
  hit@1=0.18/MRR=0.38 — la diagnosi via MCP ha mostrato che misuravamo *un solo motore* (i casi symbol sono
  domande da grafo); con `--by-kind` → hit@1 **0.64**, hit@10 **1.00**, MRR **0.75**: il sistema composito è
  **sano**, era la misura a essere parziale. SpecKit completo (Constitution **11/11**), **718 test non-cloud
  verdi**, ruff clean, `sertor-core` invariato fuori dai punti citati. Pagina [[valutazione-e-non-regressione]].
  Promosse FEAT-008 (genesi)/FEAT-009 (feedback)/FEAT-010 (pavimento assoluto) nel backlog; resta FEAT-003
  (qualità ibrido su NL, **ora misurabile**). Re-index dogfood post-merge OK (813 doc/8557 chunk), smoke MCP verde.

- **🛠️ Robustezza staleness del server MCP — fix gemelli + disciplina (PR #89/#90, 2026-06-19)** — il
  server MCP, tenendo client/artefatti a vita lunga, serviva risultati **stantii** dopo un re-index
  (scoperto via **dogfooding**: `search_code`/`search_docs` in `InternalError` sul filtro `where` mentre
  `search_combined` reggeva; `find_symbol` a righe vecchie). Un client fresco sul disco funzionava →
  difetto nel **processo**, non nei dati. Due fix di **auto-guarigione**: **ChromaStore** ricrea il
  client posseduto (`clear_system_cache` + retry una volta) su errore di query (PR #89);
  **NetworkxCodeGraph** ricarica l'artefatto su cambio `(mtime_ns, size)` (PR #90) — nessun riavvio.
  + **rituale**: regola **MCP-first** (apertura dello step) + **smoke test del RAG** (punto 8, chiusura),
  e la disciplina MCP-first **propagata agli ospiti** nel blocco host `SERTOR:RAG-USAGE` (corollario
  installabile). core 600 · sertor 293 verdi, ruff pulito; validato live (Chroma auto-heal confermato
  senza reconnect; code-graph fresco dopo reconnect, auto-reload coperto dai test). Robustezza **E1** +
  governance/host **E10**.

- **🔧 Fix uninstall: file hook Copilot dedicato cancellato se vuoto (PR #77, 2026-06-17)** — `sertor
  uninstall` lasciava `.github/hooks/sertor-hooks.json` come guscio `{"version":1}` dopo aver rimosso
  le entry Sertor. `remove_settings_entries(delete_if_empty=)` ora cancella il file **dedicato** quando
  resta senza contenuto; il file **condiviso** `.claude/settings.json` è sempre preservato (cancella
  solo quando non resta nulla — un hook utente residuo mantiene il file). 3 test; kit 131 · sertor 282.
  *Emerso dalla verifica empirica su Spike. Chiude l'item 4 del programma utente (1·2·4 completo).*

- **🚢 Consolidamento Copilot CLI-only (FEAT-012 `sertor-cli`, feature 052, PR #76, 2026-06-17)** —
  la distribuzione Copilot ha **un solo target = la CLI**. Rimosso `AssistantId.COPILOT` (VS Code) dal
  `sertor-install-kit` + profilo + rami di resa (`.vscode/mcp.json`, prompt-file come veicolo comandi);
  **`--assistant copilot` ora è un errore esplicito** che nomina `copilot-cli`. **Naming uniforme**
  `claude|copilot-cli` su `sertor` e `sertor-flow` (rinomina diretta). Skill **`requirements`** resa
  come **custom-agent** su CLI (non più prompt-file). **Mapping** `copilot-cli → --ai copilot` (upstream
  spec-kit) in un punto unico (`_SPECKIT_AI_FLAG`) + `_EXPECTED_LAYOUT` per l'idempotenza. Docs allineate
  + nota di migrazione VS Code. Elimina il footgun VS Code↔CLI e l'incoerenza di naming emersi dalla
  verifica empirica. **530 test verdi** (kit 128 · sertor 282 · sertor-flow 120), Constitution 11/11,
  **`sertor-core` invariato**, non-regressione Claude verde. *Chiude l'item 2 del programma utente.*

- **🚢 Wizard di configurazione `sertor configure [rag]` (FEAT-003 `sertor-cli`, feature 051, PR #75, 2026-06-17)** —
  chiude la **causa-radice UX** del RAG non configurato (il `-32000` su Copilot CLI quando mancano le chiavi):
  un comando guidato porta `.sertor/.env` da segreti vuoti a pronto **senza editor**. Risoluzione per-campo
  CI-safe (flag→env/esistente→prompt-se-TTY→default; campo mancante senza TTY → errore che lo nomina, niente
  scrittura parziale); campi richiesti da **fonte unica** `Settings.validate_backend()` (test di copertura
  catalogo↔validatore, no drift); scrittura **additiva non-distruttiva** (`merge_env`, overwrite gated);
  **segreti** via `getpass`, mascherati ovunque da `mask_secret` (anti-leak su entità/umano/JSON/stdout);
  validazione statica; report umano + `--json`. Default coerente col **decoupling FEAT-009** (backend azure
  → store `local`/Chroma, embeddings Azure + Chroma locale — confermato dall'utente; "azure ovunque" scartato).
  install≠run; install/upgrade/uninstall invariati. Pipeline SpecKit completa; **293 test**, Constitution
  11/11. **Follow-up:** `--check` (probe live, US5) **deferred** → richiede un nuovo `sertor-rag check` in
  `sertor-core` (Principio XI: il wizard usa il vehicle, non importa `build_embedder`); oggi il flag c'è e
  degrada onestamente.

- **🔧 Fix runtime Copilot + verifica empirica LIVE (PR #74, branch 050, 2026-06-17)** — la **verifica
  empirica** della distribuzione Copilot su un **ospite reale** (Copilot CLI 1.0.63) ha chiuso il loop
  «installato≠funzionante» e scoperto **3 difetti** che i test offline di FEAT-011 non coprivano (uno li
  *codificava*): (1) il server MCP crashava `-32000 Connection closed` su config incompleta → warm-up
  protetto, ora parte e l'errore è azionabile al tool-call; (2) SessionStart usava `command` invece di
  `prompt` (Copilot lo ignorava) → campo corretto + dedup/idempotenza/uninstall sul payload `prompt`;
  (3) `description` del custom-agent non quotata → un `:` rompeva lo YAML e `wiki-author` non si caricava
  → quoting `_yaml_scalar`. **Confermato LIVE:** `.mcp.json` auto-caricato in sessione interattiva,
  `sertor-rag` connesso (7 tool), 3 agent caricati; con creds mancanti il server resta connesso con
  errore azionabile (niente `-32000`). Test che pinnano i fix (+ guard sugli asset veri). Suite verde
  (kit 127 · sertor 221 · root 583 · packaging 2). **Lezione:** i test offline non bastano per superfici
  di un tool esterno → la verifica sul client reale è parte del «done». *Decisioni: distribuzione
  Copilot CLI-only + naming `copilot-cli` + governance prompt→custom-agent → da decomporre.*

- **🚢 Hardening compatibilità Copilot — schema nativo (FEAT-011 `sertor-cli`, feature 049, PR #73, 2026-06-17)** —
  corregge la falsa "parità piena" di FEAT-007/009 emersa da un **audit dogfooding** su Copilot CLI
  1.0.63 (hook in formato Claude → file scartato; comandi prompt-file ignorati dalla CLI). Principio
  **nativo, niente hack** (principio standing «supporto nativo, niente compat-hack»): nuovo `render_copilot_hooks` + `HookEntrySpec`
  generano hook in **formato Copilot** (`version:1`, entry piatte, `powershell`/`bash`, `timeoutSec`)
  al posto degli asset Claude-format **rimossi**; gli script `.ps1` condivisi emettono il **contratto
  nativo per assistente** via `-Assistant` (sessionStart→`additionalContext`, agentStop→`decision:allow`
  non-bloccante, preToolUse **fail-open**); comandi **per-target** (VS Code prompt-file `agent:`, Copilot
  CLI **custom-agent**); `model:` omesso; **suite di validità-schema offline** che fallisce se un bug
  dell'audit rientra. Estensione **mirata** del seam `AssistantProfile`/`Surface` (non revisione profonda,
  YAGNI). Pipeline SpecKit completa; **Constitution 11/11**; **453 test verdi** (kit 126 · sertor 219 ·
  sertor-flow 108); `sertor-core` invariato, `sertor-flow` senza dipendenza dal core. **Gap dichiarato
  (mai parità piena):** SessionStart VS Code `[ASSUNTO-VSC]` + target MCP CLI da **verificare
  empiricamente** su ospite reale (follow-up). [[assistant-targeting]] aggiornato.

- **🚢 Ciclo di vita installer — `upgrade`/`uninstall` (FEAT-008 `sertor-cli`, feature 048, PR #71, 2026-06-17)** —
  l'installer acquista i verbi di **ciclo di vita** oltre al primo install: `sertor upgrade`/`uninstall`
  (tutto-in-uno **e** per-capacità, Q3) e i simmetrici `sertor-flow upgrade`/`uninstall` (Q4 — governance
  in ambito). Le **primitive di ciclo di vita vivono una volta sola nel `sertor-install-kit`**: verbo
  ortogonale `LifecycleOp{INSTALL/UPGRADE/UNINSTALL}` + outcome `UPDATED`/`REMOVED` + **funzioni inverse
  pure** duali 1:1 delle additive (D1 — scartato il raddoppio di `WriteStrategy`/`ArtifactKind`), riuso
  degli **stessi plan-builder** percorsi col verbo (D2 — nessun secondo plan-builder), tracciatura degli
  obsoleti via **diff a posteriori** `sertor_owned_paths` + **test invariante `plan ⊆ owned`** al posto
  di un manifest (Q2). `--purge-wiki` opt-in **CI-safe** (D4 — senza TTY né `--yes` il `wiki/` è
  preservato; `--purge-wiki --dry-run` = usage error). Report `install.report/1` **esteso in modo
  additivo** (no secondo schema). Invariante duro preservato: **`sertor-flow` senza dipendenza da
  `sertor-core`/`sertor`** (verificato via AST + guard di simmetria a 0 divergenze). Pipeline SpecKit
  completa specify→implement; **Constitution 11/11** pre/post senza deroghe; **393 test verdi**
  (kit 108 · sertor 180 · sertor-flow 105), ruff pulito. `docs/install.md §10` produttivizzato
  (comandi automatici via primaria, script manuale → fallback). **Chiude l'ultima Could rilevante
  dell'epica `sertor-cli`** (restano wizard config Should + ergonomia FEAT-010 + Codex + PyPI).

- **🚢 Packaging distribuibile `git+url` (FEAT-001 `sertor-cli`, feature 047, PR #68, 2026-06-17)** —
  chiude l'**unica casella Must rimasta** dell'epica `sertor-cli`: la distribuzione interim `git+url`
  diventa un percorso di prima classe, coerente e **verificato**. File **`LICENSE` MIT** in radice + ogni
  pacchetto (incluso nelle wheel via PEP 639); **versione unica** da `/VERSION` (dynamic hatchling) sui 4
  pyproject; **metadati di distribuzione** (urls/classifiers/keywords) su `sertor`/`sertor-flow`
  (install-kit esonerato, DA-P4); suite **`tests/integration/test_packaging.py`** (stdlib+subprocess, no
  import `sertor_core`, marker `integration`) che prova licenza→metadati→build→**install pulito reale**.
  Decisioni DA-P1..P4: versione allineata · `uv` primario+gate / `pip` best-effort documentato (→FEAT-010)
  · `sertor-core`/`install-kit` = dipendenze interne. Pipeline SpecKit completa; install pulito `uv`
  validato live (2 passed), `pip` xfail documentato; **Constitution 11/11**. PyPI resta FEAT-006 (Won't).
- **🛠️ Robustezza chunking — tetto del chunk al budget token dell'embedder (PR #69 + #70, 2026-06-17)** —
  bug emerso dal **dogfooding** del re-index post-merge: i chunker strutturali (markdown per heading,
  codice per simbolo) potevano emettere un chunk oltre il limite dell'embedder (`CLAUDE.md` 8357 tok >
  8192 di text-embedding-3-large → `http 400`), bloccando ogni re-index. Fix in due passi: #69 cap
  iniziale, #70 **cap in TOKEN** (`SERTOR_MAX_CHUNK_TOKENS`, default 8191 — usa la finestra piena del
  large invece di frammentare le sezioni coerenti), conteggio preciso con **tiktoken** dietro l'extra
  opzionale `tokenizer` (lazy) + **fallback per carattere** offline-safe; `_logic_version` aggiornato
  (FR-013). Corpus re-indicizzato pulito (max chunk 8191 tok, 0 oversized). *L'indicizzazione incrementale
  FEAT-009 si è confermata corretta end-to-end nello stesso giro.*

- **🚢 Refresh incrementale dell'indice (FEAT-009, feature 046, merge `3ec47f1`, 2026-06-16)** — chiude
  l'**ultimo residuo reale di `sertor-core`** (resta solo l'agenzia incorporata, Could differita).
  `index()` è ora **incrementale di default**: un **manifest SQLite** namespaced `(corpus, provider)`
  ricorda `mtime+content_hash+logic_version` e conserva le unità derivate (Document/Chunk); i file cambiati
  sono riprocessati con **upsert/delete mirati** sul vector store (`VectorStore.delete` già esistente) e
  **BM25+code-graph ricostruiti dal manifest** (decisione utente F1 — niente re-chunk/re-read degli
  invariati). Safeguard: **fallback automatico al full** su manifest assente/incompatibile, `--full` reset
  sicuro, invalidazione su cambio-logica, **lock single-writer** (`IndexLockedError`), riconciliazione
  off-default (`SERTOR_INDEX_RECONCILE_EVERY`, decisione F2/clarify), conteggi delta osservabili. Manifest =
  store concreto **senza nuova porta** (come EmbeddingCache). Pipeline SpecKit completa specify→implement,
  guidata da **ricerca prior-art** (CocoIndex/LlamaIndex/LangChain); **gate di equivalenza** incrementale≡full
  (byte-identico) verde; **596 test** non-cloud verdi, ruff pulito, **Constitution PASS 11/11 senza deroghe**.
  Genera la feature osservabilità **FEAT-012 drift-detection** (il segnale per il trigger della riconciliazione).

- **🚢 Distribuzione Copilot della governance/SDLC — `sertor-flow` (FEAT-009, feature 045, PR #65, 2026-06-15)** —
  **chiude la distribuzione multi-assistente Copilot end-to-end** (con FEAT-007). `sertor-flow install
  --assistant claude|copilot` porta il metodo SDLC anche su Copilot. **Pivot vendoring→launch-installer**
  ([[sertor-flow]]): SpecKit non più vendorato — `sertor-flow` lancia `specify init --ai <assistant>`
  (versione pinnata, via `CommandRunner`, fail-fast se assente), asset `speckit-*`/`specify/**` rimossi
  dal bundle; refactor del path **anche per Claude** (non-regressione verificata, `specify` mockato).
  Superfici Sertor-authored (`requirements-analyst`/`configuration-manager`/skill `requirements`/blocco
  SDLC) tradotte per Copilot via [[assistant-targeting]]; **renderer spostato nel `sertor-install-kit`**
  (condiviso `sertor`↔`sertor-flow`, anti-drift; `sertor` reimporta via shim). Costituzione
  assistant-agnostica. Invariante dura preservata: **nessuna dipendenza `sertor-flow`→`sertor-core`**.
  Constitution **11/11** con **1 deroga tracciata** (II: fetch install-time spec-kit, governance≠RAG);
  kit 49 · sertor 132 · sertor-flow 87 verdi, ruff pulito.
- **🚢 Distribuzione su GitHub Copilot — pacchetto `sertor` (FEAT-007, feature 044, PR #64, 2026-06-15)** —
  prima realizzazione della **parità di assistente** ([[assistant-targeting]]): l'installer `sertor`
  porta le superfici del pacchetto `sertor` (server MCP + sistema-wiki) anche su **GitHub Copilot** con
  `sertor install <cap> --assistant claude|copilot` (default `claude`, non-regressione verificata).
  Estende il **Principio X** all'assistente ospite. Design DA-2 = **ibrido (riuso contenuto + traduzione
  contenitore)**: nuovo seam `AssistantId`/`Surface`/`AssistantProfile` nel **`sertor-install-kit`** (lo
  riuserà FEAT-009), plan-builder parametrici, `merge_mcp` con `root_key` retro-compatibile. Copilot →
  MCP `.vscode/mcp.json`, istruzioni `.github/copilot-instructions.md`, prompt-file/custom-agent **resi
  da fonte unica** (+ guardia anti-drift), hook `.github/hooks/sertor-hooks.json` con **script riusati
  identici**. Invarianti: install≠run, non distruttivo, idempotente, CLI assistant-agnostic, segreti non
  versionati, gap dichiarati. Constitution **11/11**; kit 49 · sertor 132 verdi, ruff pulito. *Ambito
  solo `sertor`; governance `sertor-flow` = FEAT-009 (planned).*
- **🚢 Principio XI realizzato end-to-end (enforcement A-D, PRs #61/#62/#63, specs/041-043, 2026-06-15)** —
  il **Principio XI — Consumo via vehicles (CLI/MCP), non la libreria a runtime** è implementato in
  profondità (difesa in 4 livelli) e cablato sui sistemi ospiti. (A) **Auto-wire nel composition root:**
  helper `_wire_runtime` nelle 5 factory consumer-entry cabla config/osservabilità/error-handling
  uniformemente, chiudendo il gap del re-index via libreria non tracciato (658 eventi su 6163 in
  telemetria). (B+C) **Lato ospite:** blocco CLAUDE.md istruzione + hook PreToolUse rileva l'uso diretto
  della libreria → warning fail-open. (D) **Coerenza bundle:** `sertor-flow` usa plan-template generico
  upstream (intenzione non-drift, a differenza degli script gated del dogfood). Constitution PASS 11/11;
  suite verde (root 564 · kit 37 · sertor 104 · sertor-flow 107).

- **🚢 Governance/SDLC come pacchetto `sertor-flow` (FEAT-005, feature 037, PR #56, 2026-06-15)** —
  l'apparato di metodo di sviluppo (SpecKit + requisiti + delega git + costituzione + rituale) è ora
  **installabile su qualunque ospite** come pacchetto separato, ortogonale al RAG e **senza dipendenza
  da `sertor-core`**. Tre pezzi: (1) **`sertor-install-kit`** — motore di installazione **estratto** in
  un toolkit condiviso stdlib-only (artifacts/resources/report/claude_md/merge/executor/sync +
  errors/observability), riusato anche da `sertor`; (2) **`sertor`** repointato sul kit (re-export shim,
  non-regressione mantenuta); (3) **`sertor-flow`** — CLI `sertor-flow install`, thin consumer, bundle 68
  asset (SpecKit vendored MIT 0.8.18 + requirements/configuration-manager + costituzione-starter neutra +
  blocco SDLC a marker distinti + NOTICE). `sertor install governance` → puntatore. install≠run,
  idempotente, non-distruttivo, offline. SpecKit completo; Constitution PASS 10/10; full-suite verde
  (root 560 · kit 37 · sertor 86 · sertor-flow 106). 7 DA risolte in sessione. *Distill entità +
  re-index in corso.*

- **🚢 Memoria conversazioni — FEAT-003 aggancio distillazione all'archivio (feature 036, PR #51,
  2026-06-14)** — chiude il loop **cattura→distillazione** dell'epica: l'archivio episodico diventa
  una **fonte recuperabile** per la modalità «from conversation» di `distill` (finora solo teorica,
  pretendeva un brief a mano). Comandi *thin consumer* `sertor-rag memory show <key>` (transcript
  intero, umano/`--json`, non troncato) e `memory list` (sessioni recenti). Core additivo: riuso di
  `MemoryArchive.get` + nuovo `list_recent`, **nessuna nuova porta** (factory `build_memory_reader`
  gated). `distill.md` aggiornato. **Vincolo cardine FR-013:** distillazione dall'archivio sempre su
  sessione mirata, su invocazione esplicita — mai sull'intero archivio, mai automatica (cattura
  economica e distillazione costosa restano disaccoppiate; l'archivio è BACKUP, non RAM). Constitution
  PASS 10/10, 558 test non-cloud verdi (31 nuovi), additivo puro. *Provato live* sul dogfood. Nuova
  pagina [[feat-036-aggancio-distillazione]].
- **🚢 Memoria conversazioni — superficie CLI + hook SessionEnd (feature 035, PR #49, 2026-06-14)** —
  rende l'MVP memoria **usabile dal terminale e automatico**: comandi *thin consumer*
  `sertor-rag memory archive` (idempotente) e `memory search "..."` (filtri temporali, umano/`--json`)
  + **hook Claude Code `SessionEnd`** (`.claude/hooks/memory-capture.ps1`) che cattura a fine sessione,
  **non-bloccante/non-fatale**, **gated** su `SERTOR_MEMORY` (off → comando con errore azionabile, hook
  no-op). Comandi host-agnostici, hook host-specifico (Principio X). Core FEAT-001/002 invariato.
  Constitution PASS 10/10, 12 test, 527 non-cloud verdi. *Provato live* (`memory search "GraphRAG"` →
  turni reali). *Resta:* accendere `SERTOR_MEMORY` per attivarla.
- **🚢 Memoria conversazioni — FEAT-002 ricerca episodica full-text (feature 033, PR #47, 2026-06-14)** —
  chiude l'**MVP memoria** ([[ricerca-episodica-fts5]]): l'archivio di FEAT-001 è ora **interrogabile**
  («ne avevamo già parlato?»). Componente concreto `EpisodicSearch` (no porta) su **SQLite FTS5 nativo**
  (`bm25()`+`snippet()`, tabella virtuale `turns_fts` mantenuta da trigger di sync), ricerca a grana di
  **turno** con citazione (sessione, ruolo, snippet, score) + filtro temporale; **sola lettura** sui dati
  (indice FTS derivato/ricostruibile), stdlib-only, **zero cloud** nel percorso query (privacy by design),
  query **hashata** nei log. Constitution PASS 10/10, 27 test, 515 non-cloud verdi. *Provato live* sul
  dogfood (5062 turni). *Resta:* superficie CLI (PLANNED) + ricerca semantica FEAT-004 (Should).
- **🚢 Memoria conversazioni — FEAT-001 cattura & archiviazione (feature 031, PR #45, 2026-06-14)** —
  il **tier grezzo episodico** che mancava ([[memoria-conversazioni]]): 8ª porta
  `TranscriptCaptureAdapter` + adapter Claude-Code (legge i JSONL di sessione `~/.claude/projects/…`),
  store concreto `MemoryArchive` (SQLite `<index_dir>/memory.sqlite`, conservato, idempotente,
  granularità **ibrida** sessione+turni per FEAT-002), `scrub_text` (segreti rimossi dal contenuto),
  servizio orchestrante, 5 manopole, wiring lazy/gated. **Privacy-by-default** (`SERTOR_MEMORY` off).
  SpecKit completo, Constitution PASS 10/10, 29/29 task, 488 test non-cloud verdi. *Manca:* superficie
  d'avvio (PLANNED) + ricerca FEAT-002 (PLANNED). NB: nuove pagine [[transcript-capture-adapter-e-storage]],
  [[scrub-segreti-in-contenuto]], explainer [[memoria-negli-agenti]].
- **🚢 Osservabilità accesa + errori MCP segnalati (PR #40/#43, 2026-06-14)** — `enable_observability`
  cablato nei consumatori CLI/MCP e **acceso sul dogfood** (`SERTOR_OBSERVABILITY=true`, 11 eventi
  catturati); ogni errore del server MCP ora persiste come evento `mcp.<tool>.error` + self-test
  end-to-end allo startup (sarebbe emerso subito il 401/`rank_bm25` di oggi). Governance anti-fallback
  silenzioso negli agenti che usano `sertor-rag`.
- **🚢 MVP Osservabilità e pannello di controllo (epica `osservabilita`, F1→F4, PR #34/#35/#36/#38,
  2026-06-14)** — Sertor è ora **trasparente su sé stesso** ([[il-pannello-di-controllo]]): **F1** strato
  persistente (store SQLite `observability.sqlite` + 7ª porta `ObservabilityStore`, cattura via
  `logging.Handler`, `SERTOR_OBSERVABILITY` default off) → **F2** servizio `ObservabilityReports` (5
  report cache/costo/salute/latenze/affidabilità da `query_events`, funzioni pure) → **F3** pannello TUI
  vista live (`sertor-rag observe`, auto-aggiornante, extra `[tui]` Textual isolato) → **F4** report
  sfogliabili a schede (Live/Cache/Cost/Corpus, tasto `t` intervallo all/7g/24h, freschezza). Privacy-by-
  default (solo metriche, mai testo). Architettura: modello/aggregazione **puri** nel core + guscio
  Textual sottile; sola lettura; degradazione onesta. Constitution PASS 10/10 ×4; ~470+85 test verdi.
  *Restano Should/Could:* export OTel · metriche aggregate · stima € · web mode. Più: **fix `wiki/wiki/`**
  (PR #37) — resolver wiki reso cwd-indipendente.
- **🚢 Cache embeddings + token nei log (hardening gruppo C, feature 019, PR #33, 2026-06-14)** — chiude
  i due Should del costo d'indicizzazione ([[indexing-and-retrieval]]): `CachingEmbedder` (decoratore
  della porta `EmbeddingProvider`, servizi invariati) + `EmbeddingCache` (store SQLite
  `<index_dir>/embed_cache.sqlite`, chiave `(model, sha256)`, vettori float64 esatti → indice
  byte-equivalente, degrado non-fatale); wiring solo sul percorso d'indicizzazione, manopola
  `SERTOR_EMBED_CACHE` (default off). + token nei log (`embeddings` con `usage.total_tokens`/
  `prompt_eval_count`, omesso se assente) e fix redazione segreti per-parola. SpecKit completo, 395+85
  test verdi, Constitution 10/10. Cache **attivata sul dogfood**. NB: nuova **area wiki `explainers/`**
  (descrizioni per non tecnici) consegnata nella stessa PR.
- **🚢 Manutenzione wiki deterministica (FEAT-007, feature 017, PR #30, 2026-06-13)** — chiude
  l'ultimo Should del core ([[wiki-tools]]): `sertor-wiki-tools move` (sposta/rinomina una pagina e
  riscrive i link entranti — wikilink form-preserving + relativi, `--dry-run`, recovery,
  `wiki.move/1`), `reconcile` (detection read-only delle pagine `status: superseded` +
  `superseded_by`, `wiki.reconcile/1`), `collect`+campo `status`; trigger periodico = doc (scheduler
  ospite). stdlib-only, offline, non-distruttivo; 434 test verdi, Constitution 10/10 senza deroghe.
  I gruppi della dote FEAT-007 sono tutti chiusi: A (probe) Won't · E (seed)/F (asset EN) consegnati
  a parte (PR #27/#28/#29) · B/C/D qui. Primo uso reale: riconciliata `pulizia-pycache-e-diagnosi-mcp`.
- **🚢 Igiene radice host (feature 016, PR #26, 2026-06-13)** — radice ospite pulita e prevedibile
  ([[sertor-installer]]): `wiki.config.toml` spostato in `wiki/` con **auto-discovery** nel CLI
  (`./wiki.config.toml` poi `./wiki/wiki.config.toml`, root=CWD) così le invocazioni ad-hoc non si
  rompono; `sertor install rag --mcp-scope project|local` (5° `ArtifactKind` `MCP_REGISTER` via
  `claude mcp add-json --scope local` dietro `CommandRunner`, idempotente, fail-fast); `.sertor/`
  confermata unica sede runtime + doc dei residenti inevitabili (`docs/install.md §7`). Fix Sertor
  one-shot (config + asset ri-sync); retrocompat ospiti esterni fuori ambito (D4). 410 test verdi,
  Constitution 10/10 senza deroghe; SpecKit completo specify→implement in giornata.
- **🧩 Agentic RAG in forma composita (FEAT-006, 2026-06-13)** — la quarta modalità RAG **esiste
  senza codice nuovo da scrivere**: il sistema [server MCP a 7 tool] + [agente client frontier]
  pianifica, seleziona i tool, itera e cita — *è* agentic RAG. Decisione utente: nessun motore
  incorporato da costruire (un loop con un modello minore non migliorerebbe l'orchestratore
  frontier). I «4 motori» dell'epica si chiudono così: vettoriale + ibrido + code-graph +
  agentico (composito). L'**agenzia incorporata** nel core resta dote differita (vedi PLANNED).
- **🚢 Installer `sertor install rag` (feature 015, 2026-06-12, su master)** — la **capacità RAG su un
  ospite con UN comando** ([[sertor-installer]]): scaffold config (`.env`/`.mcp.json`/`.gitignore`) +
  bootstrap dipendenze via `uv` in un **runtime isolato `<host>/.sertor/`** (i sorgenti host, anche
  non-Python come .NET, non vengono "pythonizzati"); riusa il backbone di `install wiki` (4 nuovi
  ArtifactKind, `CommandRunner` mockabile). install ≠ run, idempotente, segreti vuoti. **Validato live
  su un repo reale** (`uvx … sertor install rag` su Kaelen → `sertor-rag index` 150 doc/1755 chunk,
  Azure `text-embedding-3-large`). **Finding chiave:** il "bug" di distribuzione `uvx` era una
  **diagnosi errata** — `uv` risolve `sertor-core` scoprendo il workspace dal git, nessun fix
  necessario (FR-024 ✅); il fix ipotizzato avrebbe rotto il dev (revocato). Bug reale trovato live e
  fixato (`uv init --name`, `.sertor` non è un package name valido). Lavorato su `master` (bugfix
  autorizzato); 76 (pacchetto) + 321 (root) test verdi. SpecKit completo requirements→implement.
- **🚢 Motore a grafo / code-graph strutturale (FEAT-005, feature 014, PR #25, 2026-06-12 sera)**
  — terza capacità RAG, ortogonale ai motori ([[code-graph]]): porta `CodeGraph` (sesta), build
  integrato in `index()` (mai grafo stantio), artefatto JSON per corpus, copertura per-linguaggio
  DICHIARATA e verificata sui 10 linguaggi; **i 4 tool MCP storici sono tornati**
  (find_symbol/who_calls/related_docs/get_context, superficie a 7 tool). Misure: recall 1.00 sul
  ground-truth reale, precisione 1.00 sul mini-corpus; dogfood live 1.180 nodi/1.202 calls,
  query <0.1ms. SpecKit completo in serata; 321+38 test.
- **🚢 Motore RAG ibrido + reranking (FEAT-004, feature 013, PR #24, 2026-06-12)** — seconda
  modalità RAG e **nuovo default** ([[hybrid-retrieval]]): BM25 (porta `LexicalIndex`, sidecar
  atomico) + denso fusi con RRF; degradazione onesta sui corpora pre-ibrido (REQ-034); reranking
  FlashRank come extra `rerank` lazy; consumatori MCP/CLI invariati (strategia iniettata).
  **Chiusi i 2 xfail storici** (strict: simboli hit@5 0.00→1.00; +rerank MRR 0.939). SpecKit
  completo in giornata; 273+38 test; dogfood live validato (ibrido in 666ms).
- **Hotfix server MCP (PR #23, 2026-06-12)** — risolto l'hang della prima query di sessione su
  Windows (init pigro di Chroma parcheggiava il task fino al prossimo evento stdin): warm-up eager
  della facade in `main()`; prima chiamata da 51+ min appesa → 0.6s; metodo di troubleshooting
  documentato in [[mcp-server]]. 222 test verdi.
- **Installer `sertor install wiki` (feature 012, PR #22, 2026-06-11 sera)** — il pacchetto
  **`sertor` distinto** (uv workspace) che porta il sistema-wiki su qualunque ospite
  ([[sertor-installer]]): non distruttivo per artefatto, idempotente, install≠run, assets
  package-data come fonte canonica (`.claude/` = derivato + test di guardia). **Validato live su un
  repo ospite reale** (hook utente preservati, wiki operativo, re-run idempotente). 221+38 test.
  Guida: `docs/install.md`. Aperto: tema lingua (PLANNED).
- **CLI di esecuzione RAG `sertor-rag` (feature 011, PR #21, 2026-06-11)** — terza superficie del
  core ([[sertor-rag-cli]]): `index`/`search` dal terminale, osservabilità a runtime, validazione
  statica del backend. SpecKit completo in giornata (specify→plan→tasks→analyze→implement); suite
  **204 passed + 2 xfail**; SC-008: risultati CLI ≡ server MCP. DA-8: `sertor` resta riservato
  all'installer (PLANNED).
- Nucleo retrieval (FEAT-001) · motore baseline (FEAT-002) · server MCP (FEAT-MCP).
- **Wiki LLM (FEAT-003) COMPLETATA (2026-06-10)** — l'ultimo Must dell'epica: nucleo deterministico
  `wiki_tools` + operazioni-giudizio come skills/playbook. Nella giornata di chiusura: N1 riconciliata,
  N2 (`distill` a 3 ingressi → [[diary-vs-graph]]), N3 (`generate` a 2 ingressi + preset profondità,
  esercitata leggera+media su spec-kit), N4 (`ingest` → prime pagine `sources/`: gist Karpathy + v2),
  N6 (gerarchia di verità + supersession nel playbook §4, SC-009 su pagina pycache); N5/N9 → FEAT-007.
- **Query congiunta multi-collezione + `upsert-index` in CLI** (feature 010, `specs/010`, PR #20 mergiata il
  2026-06-10): capacità di fan-out su più corpora (`SERTOR_EXTRA_CORPORA`, fail-fast su provider eterogenei) +
  write-back dell'indice cablato. I pezzi D di FEAT-003 sono chiusi. **D-21 (stesso giorno):** modello
  standard = **corpus unico** (il wiki vive dentro l'ospite by design → già nel corpus primario); il fan-out
  resta per ospiti con corpora disgiunti.
- Lavori abilitanti: decoupling store↔embeddings (`specs/009`) · meccanica log (`specs/008`) · indice dogfood
  `sertor` vivo via MCP · **regola standing di re-index dei corpora** a fine step (2026-06-10, mitiga la
  FEAT-009 d'epica).
- **Startup di sessione**: hook SessionStart **sottile** (direttiva-`Read`, ~630 B) che fa caricare roadmap/index/log
  al flusso principale e mostrare l'executive summary — supera il cap ~10K del canale-hook (verificato in sessione 2026-06-09).

## Visione

Portare capacità **RAG** (ricerca semantica su codice + documentazione) su **qualunque repository**, in modo
riproducibile e production-grade. **Una sola verità interrogabile**: sorgenti (il *come*) e doc/wiki (il
*perché*) coesistono nello stesso corpus; la doc nuova vive **accanto ai sorgenti** via LLM Wiki. Local-first
↔ cloud per configurazione; riusabile come **libreria**, esposta via **CLI** e **MCP**.

## ⚠️ Due numerazioni (da non confondere)

- **`FEAT-NNN` (epica)** = capacità di prodotto nel backlog (`requirements/sertor-core/epic.md`).
- **`specs/NNN`** = ordine **sequenziale** di implementazione. NON coincide con l'epica: `specs/008`
  (meccanica del log) e `specs/009` (decoupling store) sono **lavori abilitanti** sul nucleo/wiki-tools,
  **non** le FEAT-008/009 dell'epica (arricchimento Wiki↔RAG / refresh incrementale, ancora da decomporre).

## 🔍 Backlog dall'audit indipendente (SWOT 2026-07-02)

> Esito dell'audit richiesto dall'utente (prompt in `wiki/sources/Human/`). Dettaglio, evidenze
> (file:riga) e criteri d'accettazione in **[[audit-swot-2026-07-02]]**. Si affronta **in ordine, da A-01
> in giù**, con **checkpoint a fine di ogni item** (decisione utente 2026-07-02). Stato: 📋 da attaccare ·
> 🔄 in corso · ✅ fatto. La promozione a `FEAT-NNN` d'epica si decide item-per-item.

| ID | Tipo | P | Titolo | Casa d'epica candidata | Stato |
|---|---|---|---|---|---|
| A-01 | FIX | P0 | `upgrade` safety: assistente esplicito/rilevato, no capability creep | `sertor-cli` (E2) | ✅ merge `a9e84e3`/PR #141 (auto-detect · no creep · switch consentito) |
| A-02 | FIX | P0 | Licenza speclift: provenienza onesta (titolarità comune) + LICENSE upstream + re-pin | `speclift` (E14) | ✅ **CHIUSO su entrambi i lati**: in-repo (merge `9a7e3b7`/PR #142) + **Sinthari ha aggiunto e pushato la `LICENSE` MIT** (© themetriost, PR #12/merge `1245355`) → speclift+specaudit ereditano la licenza alla sorgente |
| A-03 | FIX | P0 | BM25 staleness auto-heal (terza gamba MCP) | `sertor-core` (E1) | ✅ merge `ddac060`/PR #144 (reload su token `(mtime_ns,size)`, gemello code-graph; 1054 unit + 2 staleness verdi). **Dogfood SpecLift→SpecAudit** sul changeset: 6/6 àncore verificate; audit 2 SODDISFATTO + 2 NON_DOCUMENTATO (vanish-case) |
| A-04 | FIX | P0 | Session-open 55k→~10k token (EXEC-only + potatura CLAUDE.md) | `debito-tecnico` (E10) | ✅ merge `e83c6de`/PR #145 (EXEC:END spostato prima del changelog DONE + `index.md` on-demand al SessionStart + potatura CLAUDE.md); redesign profondo della rappresentazione EXEC rinviato a cross-team |
| A-05 | FIX | P0 | 9 skill speckit fantasma → **promosso a debito** (E10-FEAT-027) | `debito-tecnico` (E10) | ✅ **E10-FEAT-027 MERGE `2f2ea70`/PR #146** (dogfood = client SpecKit fedele); tema poi assorbito e superato dall'epica **E15 fedelta-dogfood** (asset-install mergiato 2026-07-06 → il `materialize-speckit.ps1` è retrocesso a dev-tool, la fonte è il vero install). *Storia:* **diagnosi fatta, primo fix ritirato** Il primo tentativo (de-reference dei 9 agenti + guardia di root) **incistava** lo special case: la guardia *benediva* la divergenza dal client invece di eliminarla. Causa reale = **il dogfood non è un client Sertor fedele** (gli mancano skill/script SpecKit che ogni ospite riceve da `specify init`; porta 9 agenti orfani che nessun client ha, `test_no_vendored_speckit_agents`). Conversione fedele-al-client → **E10-FEAT-027 IMPLEMENTATA** (branch `087-a05-dogfood-client-debt`): script `scripts/dev/materialize-speckit.ps1` (materializza via `specify init` isolato + copia selettiva + overlay UTF-8 + fail-loud se cambiano gli artefatti Sertor) · gitignore del rigenerabile · 9 agenti orfani rimossi · guardia `test_dogfood_speckit_fidelity` (3 verdi). Accettazione OK: 9 skill+5 script gitignorati, artefatti Sertor byte-identici, 1057 unit verdi, `sertor-core` invariato |
| A-06 | FIX | P0 | Doc: `configure` documentato + quick-start Claude su GloVe | `documentazione-marketing` (E13) | ✅ (2026-07-07) — `docs/install.md`: sezione **`sertor configure`** (flag, resolution, `--check`) + fix framing «local=Ollama»→**glove default zero-config** (prerequisiti, commento install, variante `--backend local`); `docs/install-claude.md`: quick-start su glove + step `configure`. README pulito |
| A-07 | EVO | P1 | `search_docs` MRR 0.55 (leva missione) | `retrieval-qualita` E5-FEAT-003 | ✅ **E5-FEAT-003 dedup consegnata su branch `090` (2026-07-07)** — `search_docs` degradava perché lo stesso contenuto (blocchi `CLAUDE.md` ↔ copie bundle `assets/**`) saturava il top-k. **Misura-prima:** l'MVP dedup *esatto* (content-hash) è risultato **insufficiente** (i chunk dello stesso blocco da file diversi hanno confini diversi → non byte-identici); il **fuzzy** (shingle 5-word + containment ≥0.8) ha consegnato il lift: **`search_docs` hit@3 0.62→0.75** (baseline ristabilito), MRR 0.55→0.57, `search_code` intatto, **gate `--fused` PASS**. Funzione pura `dedup_results` a query-time nei 5 siti di retrieval (pool>k), manopola `SERTOR_DEDUP` default-on, host-agnostico. 1 residuo union (competizione doc-fratelli, NON dedup) chiuso con calibrazione GT legittima. **Follow-up tracciato:** near-dup a scala (MinHash) + leva «doc-fratelli». *(dettaglio: `wiki/log/2026-07-07.md`, spec `090`)* |
| A-08 | FIX | P1 | Security review installer (merge settings.json + hook auto-eseguiti) | `debito-tecnico` (E10) | ✅ **review + 3 fix su branch `093` (2026-07-08)** — **Bottom line: superficie difensivamente ben costruita** (hook injection-safe by construction, merge non-distruttivi/`json.loads`-only, breadcrumb secret-free, no RCE dalla version-check). Fix: **#1** `--corpus` non sanitizzato → **injection in `.env`/`.mcp.json`** (newline clobberava la key) → `resolved_corpus()` ora sanitizza anche l'esplicito (+test); **#2** re-index incondizionato a ogni SessionEnd → costo Azure → **`SERTOR_EMBED_CACHE` default ON** + nota costo in `docs/install.md`; **#3** version-check honora l'URL override **solo su https** (no MITM del notice). **#4 (`.env` non gitignorato) = FALSO POSITIVO** colto in verifica (`RUNTIME_IGNORES` include già `.sertor/.env`). `sertor-core` toccato solo per il default cache |
| A-09 | FIX | P1 | Hook POSIX story (promuovere E2-FEAT-010 da Could) | `sertor-cli` E2-FEAT-010 | ✅ **DONE (merge `0ffe904`/PR #161 + hotfix smoke `9e85f70`/PR #162)** — 8 hook riscritti in **Python portabile** (`uv run --no-project python`, zero dip `pwsh`); parità coi `.ps1` provata (gate) + smoke CI matrice ubuntu+windows (test **e** smoke E2E verdi); `.ps1` **ritirati** (single-impl DA-1); `upgrade` migra host legacy (file+wiring, helper `remove_hook_entries_by_command_substring`); **E10-FEAT-018 superata** (`host_env.py`/nota pwsh rimossi — fix, non mitigazione); doc utente aggiornata. `sertor-core` invariato. **Migrazione live del dogfood eseguita** via `sertor upgrade` (8 `.ps1` rimossi, `settings.json` riwirato a `.py`, 0 residui) — valida T022 dal vivo. Dettaglio [[feat-010-hook-portabili]] |
| A-10 | FIX | P1 | CI: smoke E2E su PR + job 3.11 + (opz.) leg cloud | `debito-tecnico` (E10) | ✅ **DONE (merge `c9e5140`/PR #164)** — lo smoke E2E ora è un **gate pre-merge**: job `changes` (`dorny/paths-filter`, permesso `pull-requests:read`) lo attiva sui PR che toccano la superficie install/smoke, e `SERTOR_SMOKE_REF=github.head_ref` fa installare dal **branch del PR** (testa il diff, non master) → avrebbe colto la regressione di #161. + leg **Python 3.11** (ubuntu, via `include`). Leg `cloud` opzionale non fatto. Il PR #164 si è auto-validato (tocca `ci.yml`). |
| ~~A-11~~ | — | — | Azure Search experimental/test → **spostata in E6** `backend-store-scala` **FEAT-007** (store cloud online); riferimento A ritirato | `backend-store-scala` (E6) | ➡️ promossa a E6-FEAT-007 (2026-07-10) |
| A-12 | FIX | P1 | Riconciliazione epic.md↔EXEC enforced + pulizia fondo-roadmap zombie | `debito-tecnico` (E10) | 🔄 **implementata, pre-merge (2026-07-10)** — *enforcement per costruzione* (opzione A): EXEC = fonte unica, `epic.md` puntano. Fatto: blocco fossile «Mappa delle feature» eliminato (~85 righe) · 6 righe `epic.md` allineate (sertor-cli/fedelta-dogfood×3/debito-tecnico/speclift + osservabilità) · idee promosse/consegnate rimosse dalle *Nuove funzionalità* · licenza «DA APRIRE»→MIT · «riavvio MCP»→auto-heal · regola fonte-unica nel rituale (CLAUDE.md item 4) + «Come mantenere» |
| A-13 | FIX | P1 | `updated:` = data secca; storia solo nel log | `debito-tecnico` (E10) | 🔄 **implementata, pre-merge (2026-07-10)** — regola «`updated:`/`created:` = data secca, storia nel log» nel playbook (dogfood+bundle, parità verde) + CLAUDE.md convenzioni; **25 pagine** ripulite (changelog nel frontmatter → data secca; `roadmap.md` da ~13KB → `2026-07-10`) |
| A-14 | FIX | P1 | Settings: parsing numerico guardato + scrub `detail` MCP | `sertor-core` (E1) | ✅ **(merge `c859a19`/PR #167)** — `Settings.load`: 24 parse `int/float(os.getenv)` → helper guardati `_int_env`/`_float_env` (+ `_*_or_none` guardati); valore non-numerico → `ConfigError(key=…)` invece di `ValueError` crudo (Principio XII). `server.py`: `detail=scrub_text(str(exc))` ai 3 siti d'errore (`_guard`/`_self_test`/`warmup`) → no leak segreti nello store. +5 test; ruff clean |
| A-15 | FIX | P2 | VERSION policy (E2-FEAT-014): decidere il bump o version-check resta morto | `sertor-cli` E2-FEAT-014 | ✅ **decisa (merge `192c629`/PR #168)** — scelta utente: **bump MANUALE a ogni release user-facing** (`/VERSION` SemVer, non a ogni merge — il per-merge è il dogfood via HEAD). Zero codice; bump automatico scartato (YAGNI). Regola in CLAUDE.md §Git & versionamento + E2-FEAT-014 risolta. **Caveat (finding 2026-07-10):** l'avvisatore è inerte anche per un 2° motivo — il fetch di `/VERSION` **404** su repo **privato** → `verdict:"unknown"`; macchina **validata live** (override → `behind` → avviso). Entrambi sciolti al **go-public** → **E2-FEAT-017** |
| A-16 | FIX | P2 | Lifecycle edge: uninstall di file pre-esistenti + trappola marker corrotto | `sertor-cli` (E2) | ✅ **(merge `87ac1da`/PR #169)** — scelta utente **content-guard** (no manifest, rispetta D3): (1) `remove_file_if_owned` nel kit — un FILE owned si cancella solo se combacia con l'asset deposto, altrimenti **preserva+warn**; wirato nei 3 consumer (rag/wiki/gov, split FILE/CONFIG). (2) `MarkerBlockCorruptError` + `_assert_not_corrupt` in `claude_md.py` — START-xor-END → **fail-loud** (non più SKIPPED silenzioso) su write/remove/update. Solo installer package (no `sertor-core`); +8 test; kit 157·sertor 510·flow 142 verdi, ruff clean |
| A-17 | FIX | P2 | Sync asset: copertura `rag/hooks` 5/5 + `--check` exit code + delete orfani | `debito-tecnico` (E10) | ✅ **(merge `064c5eb`/PR #171)** — scelta utente **completo**: (1) **copertura** già risolta (il `sync` enumera il subtree → tutti i 7 hook; guardia auto-derivante E15-FEAT-002); (2) **`--check`** su `sync.py` → exit 1 sul drift (gate locale); (3) **delete orfani** — `delete_if_empty=True` sul `settings.json` **condiviso** (il key-check preserva il contenuto utente) + nuova primitiva kit **`prune_empty_dirs`** (rimuove le dir vuote bottom-up) wirata in `execute_lifecycle` (`uninstall_prune_empty`) nei 3 consumer → **chiude il bug «`.claude/` orfano vuoto»**. Solo installer package; +8 test; kit 162·sertor 513·flow 142 verdi, ruff clean |
| A-18 | EVO | P2 | E13 Fase 1 Musts (getting-started, README di valore) | `documentazione-marketing` E13 | ✅ **(merge `6e40ccc`/PR #172)** — **nuovo `docs/getting-started.md`** (percorso unico host-agnostico «dal nulla al primo valore»: prerequisiti→install→index→prima query; entrambe le varianti CLI Claude+Copilot affiancate; esempio finale di **fusione code+doc** via `search_combined`) + **riscrittura `README.md`** valore-first (apre col differenziatore code+doc + esempio; fatti preservati; punta al getting-started come ingresso unico) + rimandi di convergenza in `install-claude`/`install-copilot`/`retrieval`. Pipeline SpecKit completa; Constitution 12/12 + missione PASS; **authoring** (`sertor-core`/CLI/installer invariati, D↔N), 0 codice; ruff clean. Chiude E13-FEAT-001+FEAT-002 |
| A-19 | EVO | P2 | Refactor seam assistenti (surface-iteration, no ternari binari) pre-Codex | `sertor-cli` (E2) | ✅ **(merge `e6096e4`/PR #174)** — refactor iso-funzionale: nuovo helper **`select_for(assistant, {AssistantId: valore})`** n-ario + fail-loud (`AssistantProfile.select`) sostituisce i **ternari binari** `X if CLAUDE else Y` in ~5 siti (`_SERTOR_AUTHORED` governance da colonne→`dict[AssistantId,str]`; concierge rag; legacy `.ps1`+`owned_dirs` wiki) + enum-iteration in `__main__`. Chiave mancante→`ConfigError` (Principio IV/XII) invece di `else` silenzioso → aggiungere Codex = aggiungere una chiave. **Fuori scope motivato** (YAGNI): i guard `if COPILOT_CLI:` strutturali. Parità byte-identica (per costruzione); +3 test; suite 1173 verdi, ruff clean; `sertor-core` invariato. Distill in [[assistant-targeting]] |
| A-20 | FIX | P2 | Igiene: gitignore `.last-hook-error`, triage `sources/Human/`, 6 wikilink rotti, collisione `specs/077`, OTel senza collector | `debito-tecnico` (E10) | ✅ **(merge `6032cab`/PR #173)** — sondaggio: **3/5 già risolti** (`.gitignore:88` ha `.last-hook-error`; `.sertor/.env:54` ha `SERTOR_OBSERVABILITY_OTEL=false` con commento; lint `broken_links=0` — i 6 wikilink già sistemati). **Fatto ora:** (#2) `Fable SWOT.md` normalizzato → `fable-swot-audit-prompt.md` (kebab + frontmatter, fonte del backlog A-01..A-20), citazioni aggiornate → azzera `naming_violations`; (#4) collisione `specs/077` **accettata come artefatto storico** (due branch `077` paralleli offline, merged; `077-version-update-check` senza ref vivi; rename = churn su storia; allocatore max+1 già previene ricorrenze same-repo) — **no rename, documentata**; **bonus** sweep frontmatter su 9 file-fonte tracciati → lint corpus committato pulito. Restano fuori i 2 input **non processati** (workflow separato) |

---

## 🧭 Nuove funzionalità da discutere (sezione a mano)

> Idee **prima** che diventino feature formali. Stati: 💡 idea · 🗣️ in discussione · 👍 approvata (→ decomporre) · ❌ scartata.
>
> **Quando un'idea è promossa a epica o consegnata, esce da qui:** vive nel backlog dell'epica
> (`requirements/<epica>/epic.md`) + nell'**EXEC** (fonte unica dello stato «consegnato»). Qui restano
> solo le idee **ancora aperte** — non si duplica lo stato delle feature (regola A-12, 2026-07-10).

| Idea | Valore / perché | Note / vincoli | Stato |
|------|-----------------|----------------|-------|
| **Rilevamento attivo dei gap di documentazione** (codice→wiki generativo) | Il residuo *genuino* di FEAT-008: oggi il legame codice↔doc è **passivo** (lo interroghi con `get_context`/`related_docs`), manca il **generativo** — il RAG/code-graph che rileva **entità di codice senza pagina wiki** e le **propone** al `wiki-author` | Scorporato dalla chiusura di FEAT-008 (✅ composita, verificata live 2026-06-16). Casa candidata: feature wiki dedicata o `debito-tecnico` FEAT-005 (igiene-wiki). Riusa il [[code-graph]] (`find_symbol`/`related_docs`) + lint C | 💡 **idea, scorporata da FEAT-008** (2026-06-16) |
| **Misurare nella TUI *quando si usa il grafo* vs *il vettoriale/ibrido*** (epica `osservabilita`, estende FEAT-015) | Vedere a runtime **quale metodo di retrieval** serve ogni risposta: quando si scende sul code-graph (`find_symbol`/`who_calls`) e quando si resta sulla ricerca densa/ibrida. Oggi la scheda RAG (FEAT-015) mostra query/verdetto/op-MCP ma **non distingue grafo vs ricerca** | Gli eventi distinti **già esistono** (`hybrid_query`/`retrieve` vs i tool grafo via `mcp.<tool>`): serve **aggregarli/etichettarli per metodo** nella TUI. Si lega al fatto che il "routing" del metodo vive **nell'agente** (nessun router nel core, vedi A/B del 2026-06-20) → la TUI lo renderebbe **visibile** | 💡 **idea (utente, 2026-06-20)** |
| **Timeout espliciti su embed/query (server MCP e adapter)** | L'hang della prima query MCP è stato diagnosticato e **risolto** (causa vera: init pigro di Chroma nella prima tool call parcheggiava il task su Windows → warm-up eager in `main()`, **hotfix PR #23**, vedi [[mcp-server]]); i timeout generici restano una rifinitura di robustezza | Timeout configurabile in `Settings` + eccezione di dominio | 💡 idea ridimensionata (hang risolto 2026-06-12) |
| **Misurare quanto il core D↔N viene *aggirato*** (dato-prima-del-codice) | Rilievo più grave dell'handoff Nunzio: in una sessione reale `index.md` è stato scritto **a mano** invece che via `upsert-index` (0 invocazioni del core). Le garanzie valgono solo se il core è *attraversato*. Prima il **dato** (quante sessioni bypassano il core), poi eventualmente un lint che rileva un `index.md` non-conforme a `upsert-index` | **Fonte: handoff Nunzio 2026-07-09 (§1).** Gemella di E10-FEAT-026 (anti-skip): stesso pattern di skip silenzioso del confine D↔N | 💡 idea esterna (alto valore) |
| **Backlink deterministici da `collect`** (wiki-tooling) | I wikilink uscenti sono già estratti da `collect.py`; i **backlink = relazione inversa = aritmetica, non giudizio** — oggi li scrive l'LLM a mano. Generarli/validarli nel core (à la wiki-compiler «Referenced By», **preservando le sezioni scritte a mano**) libera l'LLM dal 90% meccanico | **Fonte: Nunzio (§3).** Confine D↔N: aritmetica→core. Riusa `collect.py` | 💡 idea esterna |
| **`sertor-wiki-tools plan` (`wiki.plan/1`) + coda dei «passivi»** (no LLM) | Da `scan` a un **piano di lavoro** deterministico (file toccati dall'ultima entry · pagine che li citano via `sources:` · pagine non aggiornate da N giorni); + marcare pagine con **comandi/versioni/URL** ordinate per età `updated:` — il codice dice *dove guardare*, l'LLM *se è ancora vero* | **Fonte: Nunzio (§4+§6).** **Estende `ritual-check`** (E10-FEAT-026): stessa filosofia D↔N | 💡 idea esterna |
| **Riproducibilità cross-OS + benchmark del `lint`** (il fossato, misurato) | «zero-LLM, offline» *implica* il determinismo ma non lo **promette né verifica**: (a) test di riproducibilità cross-OS in CI (output identici — garanzia che nessun sistema LLM-based può dare); (b) benchmark `lint`/`collect`; sospetto **O(n²)** sul rilevamento orfani | **Fonte: Nunzio (§5).** Rende *misurato* il differenziatore, non solo dichiarato | 💡 idea esterna |
| **Connettori per `ingest`** (git/slack/web/…, personal mode) | `ingest` esiste ma le fonti le porta l'utente; un connettore *ingerisce byte* (lato deterministico), non genera prosa → estensione naturale del confine | **Fonte: Nunzio (§7).** **→ mappa su E7 `ingestione-estesa`** (repo remoti/formati) — cita epica esistente, non voce nuova | 💡 idea esterna → E7 |
---

## Questioni aperte (tenute così, per ora)

- **Soglie di pertinenza**: non fissate a priori; da misurare su ground-truth reale (DA-003 / DA-1·3).
- **Numerazione**: epica FEAT-NNN ≠ `specs/NNN` (vedi banner sopra) — non riconciliarle a forza, documentare.
- **Server MCP & codice nuovo**: il server **auto-guarisce** da indice/dati *stantii* dopo un re-index (ChromaStore auto-refresh + code-graph auto-reload, PR #89/#90 — **nessun riavvio**). Resta necessario un **riavvio** del subprocess MCP solo per servire **codice nuovo del server** (`sertor_mcp`).
- **Processo: `requirements.md` ↔ `spec.md` si sovrappongono?** (riflessione di metodo, 2026-06-20) — la fase
  `requirements` (skill, EARS) e la `specify` SpecKit (user-story + accettazione) coprono entrambe il
  *cosa/perché* e in FEAT-001 si sono sovrapposte parecchio. **Da fare:** confrontare i due artefatti di
  `specs/065-ground-truth-valutazione/` e decidere — per le prossime feature conviene sempre entrambe, o a
  volte saltarne una (es. `requirements`→`plan` diretto come feature 064)? **Nota emersa:** la skill
  `speckit-specify` e il template `spec-template.md` **non sono nel repo** (l'agente ha proceduto per
  convenzione) → eventuale debito di tooling. Casa possibile dell'esito: epica `debito-tecnico` o questa nota.

## Come mantenere questa pagina

- Brainstorming → a mano in *Nuove funzionalità da discutere*; l'idea **promossa o consegnata esce di lì** (vive nell'epica + EXEC).
- Avanzamento feature → aggiorna **solo** il blocco **EXEC** in cima (`<!-- EXEC:START/END -->`): è la **fonte unica** dello stato «consegnato». Gli `epic.md` vi **puntano**, non lo duplicano (regola A-12). È giudizio del flusso principale, non del `wiki-curator`.
- Idea matura → backlog epica + `/requirements` → `/speckit-*`.

## Riferimenti

Sintesi per feature: [[hybrid-retrieval]] · [[implementazione-nucleo-retrieval]] · [[motore-baseline-feat002]] ·
[[nucleo-wiki-deterministico-feat003d]] · [[server-mcp-produzione-feat-mcp]] · [[meccanica-log-feat008]] ·
[[store-backend-disaccoppiato-feat009]] · [[spec-010-query-congiunta-e-upsert-index]] ·
[[sertor-rag-cli]] · [[architettura-wiki-llm]] · [[constitution]] · [[corpus-index-naming]].
