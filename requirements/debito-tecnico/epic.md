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

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Host-agnosticità degli asset residui** (skill wiki / playbook / rituale ancora Sertor-coupled) | Onora il Principio X anche sugli asset interni | **Should** | da decomporre |
| FEAT-002 | **Unificazione degli ambienti** (`.venv` / `.venv-core` → uno coerente) | Elimina un footgun operativo | **Should** | ✅ **DONE (2026-06-18)** — un solo `.venv` (default workspace `uv`); `dev` superset (incl. `mcp`+`graph`), `azure` opt-in; `.mcp.json` ripuntato; `.venv-core` eliminato; guard test CS-3 |
| FEAT-003 | **CI Linux nativo** (suite verde su Linux oltre Windows; debito rag-baseline DA-2) | Portabilità reale verificata in CI | **Should** | da decomporre |
| FEAT-004 | **Rituale/governance come plugin portabile** repo-agnostico (oltre ciò che `sertor-flow` copre) | Riuso del metodo su repo terzi senza Sertor | **Could** | da decomporre |
| FEAT-005 | **Igiene del wiki** — hub/overview per-area, tassonomia più fine, distill pagina osservabilità, ripasso [[tree-sitter-language-pack]], override seed `[strings]`, trigger periodico `reconcile` | Wiki navigabile e senza deriva organizzativa | **Could** | da decomporre — guidata dal lint C |
| FEAT-006 | **Robustezza del bundle `sertor-flow`** — selettività (vs all-or-nothing) + hook harness governance (DA-g) | Install governance più flessibile | **Could** | da decomporre |
| FEAT-007 | **Allineamento naming `--assistant`** — unificare i due valori Copilot (`copilot` VS Code + `copilot-cli`) in **un solo `copilot`** | Coerenza dell'API installer, meno confusione utente | **Could** | da decomporre — *user-flagged 2026-06-16*; decisione di design aperta: due contenitori MCP (`.vscode/mcp.json`/`servers` vs `.mcp.json`/`mcpServers`) sotto un nome unico (scrivere entrambi? `.mcp.json` canonico?) |

> **Nota:** non c'è un «MVP» nel senso di prodotto: è debito. La priorità reale è **FEAT-001/002/003**
> (Should): host-agnosticità, un solo env, CI Linux — le tre frizioni che incidono di più su qualità e
> portabilità. Il resto (Could) si paga quando tocca quelle aree.
