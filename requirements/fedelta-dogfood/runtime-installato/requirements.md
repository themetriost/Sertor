# Requisiti — Il dogfood gira sul runtime `.sertor/` installato (tracking HEAD) + repoint MCP

<!-- Deriva da: E15-FEAT-001 (self-install, scope A: core-runtime) + incorpora E15-FEAT-007 (repoint .mcp.json) -->

## 1. Contesto e problema (perché)

Direttiva utente (2026-07-03): il **runtime dell'agente** del dogfood deve girare **solo sulla versione
installata**, non sulla sorgente-repo. Oggi il server MCP + il core girano dal **`.venv` del workspace**
(editable), via `.mcp.json` = `command ".venv/Scripts/python.exe"`. Ambiguità: l'agente usa il codice locale
non-mergiato.

Lo spike ha mostrato la **forma reale** del runtime installato: un progetto `uv` `.sertor/` con
`pyproject.toml` (`dependencies=["sertor-core[graph,mcp,rerank]"]`, `[tool.uv.sources] sertor-core={git=<repo>}`)
+ `uv.lock`, e `.mcp.json` = `uv run --directory .sertor python -m sertor_mcp.server`.

Questa feature porta il dogfood su quel runtime **tracking HEAD**: il server MCP e il core girano
dall'**installato-da-HEAD** (ultimo master mergiato), non dal `.venv`. **Scope A (bounded):** solo il
**core-runtime + repoint MCP**; la process-fidelity degli **asset** `.claude/` (ri-eseguire `sertor install`,
con le sue riconciliazioni) è **fuori ambito** (feature separata) — gli asset restano su F2-sync.

## 2. Obiettivi e criteri di successo
- **O1.** Il server MCP `sertor-rag` del dogfood gira dal runtime `.sertor/` (sertor-core installato da
  `git=<repo>` HEAD), non dal `.venv` del workspace.
- **O2.** Nessuna ambiguità: il runtime dell'agente = versione **installata** da HEAD; i **test/sviluppo**
  restano sull'editable `.venv` (confine dev↔dogfood).

**Criteri di successo (misurabili):**
- **SC-1:** `.mcp.json` del dogfood usa la **runtime-form** `uv run --directory .sertor python -m
  sertor_mcp.server` (non `.venv`).
- **SC-2:** esiste un runtime `.sertor/` funzionante (`pyproject.toml` + `uv.lock`, `sertor-core` da git HEAD);
  `uv run --directory .sertor python -m sertor_mcp.server` **si avvia** (il server MCP risponde).
- **SC-3:** i **test** (`uv run pytest`) continuano a girare sull'editable workspace — invariati.
- **SC-4:** la machinery del runtime (`.sertor/pyproject.toml`, `.sertor/.venv`, `uv.lock`) è **rigenerabile**
  (gitignorata come il resto di `.sertor/`); un clone fresco la ottiene via lo step di setup (FEAT-008).
- **SC-5:** `sertor-core` invariato (nessun cambio di codice di libreria; è config runtime + wiring).

## 3. Stakeholder e attori
- **Agente del dogfood** — d'ora in poi consuma il core/MCP dall'installato-da-HEAD.
- **Manutentore** — deve poter (ri)creare il runtime `.sertor/` con un comando (setup); i test restano sul `.venv`.
- **Clone fresco / CI** — vedi FEAT-008 (setup step) + confine (i test non dipendono dal runtime `.sertor/`).

## 4. Ambito
### In ambito
- Creare/stabilire il runtime `.sertor/` del dogfood (uv project, `sertor-core[...]` da `git=<repo>` HEAD).
- **Repoint `.mcp.json`** (≡ FEAT-007) dalla forma-`.venv` alla runtime-form `.sertor/`.
- Documentare il setup (crea/aggiorna il runtime) — coordinato con FEAT-008 (re-lock post-merge).
### Fuori ambito
- **Ri-eseguire `sertor install rag/wiki`/`sertor-flow install`** sul dogfood (process-fidelity **asset**:
  duplicazione blocco CLAUDE.md, settings-merge, ecc.) → feature separata (F4/asset-install).
- Repoint degli **hook** al runtime `.sertor/` se oggi non usano `.venv` in modo ambiguo (valutare;
  altrimenti feature separata).
- Il **re-lock automatico** post-merge → FEAT-008.
- Cambi a `sertor-core`.

## 5. Requisiti funzionali (EARS)
- **REQ-001 (Ubiquitous).** The dogfood's `sertor-rag` MCP server shall run from the installed `.sertor/`
  runtime (`sertor-core` from `git=<repo>` at HEAD), not from the workspace `.venv`.
- **REQ-002 (Ubiquitous).** `.mcp.json` shall use the runtime form `uv run --directory .sertor python -m
  sertor_mcp.server` (host/client form), not `.venv/Scripts/python.exe`.
- **REQ-003 (Event-driven).** When the runtime setup runs, it shall produce a working `.sertor/` uv project
  (`pyproject.toml` + `uv.lock`) whose `sertor_mcp.server` starts.
- **REQ-004 (Ubiquitous).** The workspace editable environment (`.venv`) shall remain the target for
  **tests/development** (`uv run pytest`) — unchanged (confine dev↔dogfood).
- **REQ-005 (Ubiquitous).** The `.sertor/` runtime machinery (`pyproject.toml`, `uv.lock`, `.venv`) shall be
  **git-ignored** (regenerable; obtained via the setup step, coherent with FEAT-008).
- **REQ-006 (Unwanted behaviour).** If the `.sertor/` runtime is absent (fresh clone before setup), then the
  failure shall be **honest/actionable** (the MCP server error names the missing runtime + the setup command),
  never a silent wrong-runtime.
- **REQ-007 (Ubiquitous).** The change shall leave `sertor-core` unmodified (it is runtime config + wiring).

## 6. Requisiti non funzionali
- **NFR-1 (no ambiguità):** dopo il repoint, non deve esistere un percorso in cui l'agente-runtime usa il
  `.venv` editable (solo i test lo usano).
- **NFR-2 (setup ripetibile):** creare/aggiornare il runtime è un comando documentato (come `uv sync`), idempotente.
- **NFR-3 (rete):** il setup del runtime richiede rete (`uv` risolve `sertor-core` da git); dichiarato.

## 7. Vincoli, assunzioni e dipendenze
- **Dipendenza:** FEAT-005 ✅ (installer preservante `plan-template`) — non strettamente necessaria per lo
  scope A (che non ri-esegue `sertor-flow install`), ma lo è per il full-install futuro.
- **Assunzione (spike):** `.sertor/pyproject.toml` prodotto dall'installer pinna `requires-python >=3.12`
  mentre il core è 3.11+ → allineare a `>=3.11` (finding minore, incluso o feature adiacente).
- **Vincolo:** `.mcp.json` è **committato** (root). Repointarlo alla runtime-form significa che il dogfood
  **richiede** il runtime `.sertor/` per far partire l'MCP → il setup (FEAT-008) diventa un passo necessario
  a inizio-lavoro (dichiarato in doc).
- **Attenzione:** il runtime `.sertor/` installa `sertor-core` dal **remote git HEAD** → riflette l'ultimo
  master **pushato/mergiato**, non il working tree locale (è precisamente l'intento: niente ambiguità).

## 8. Rischi
- **R-1 (disruptivo sul runtime vivo):** repointare `.mcp.json` rompe l'MCP se il runtime `.sertor/` non è
  pronto. *Mitigazione:* creare/validare il runtime **prima** del repoint; REQ-006 (fallimento onesto);
  implement gated (con l'utente).
- **R-2 (clone fresco/CI):** senza runtime `.sertor/`, l'MCP non parte. *Mitigazione:* setup step documentato
  (FEAT-008) + i test non dipendono dal runtime (girano su `.venv`).
- **R-3 (lag remote):** il runtime tira HEAD dal **remote**; se una modifica non è pushata, il dogfood non la
  vede. *Voluto* (no ambiguità), ma da dichiarare (per testare codice locale si usa il `.venv`, non l'MCP).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-003, REQ-004, REQ-007.
- **Should:** REQ-005, REQ-006, NFR-2.

## 10. Domande aperte
- **Q1 [design→plan]:** come **creare** il runtime `.sertor/` del dogfood — (a) eseguire il pezzo di
  `sertor install rag` che genera `.sertor/` (DEPENDENCIES + `.mcp.json`), scoping-out il resto; (b) uno
  **script di setup dedicato** (come `materialize-speckit.ps1`) che scrive `.sertor/pyproject.toml` (pin
  `requires-python>=3.11`, `sertor-core` da git HEAD) + `uv lock`; (c) `sertor install rag` pieno (ma tocca
  asset → scope B). *Raccomandazione: (b)* o (a)-scoped, coerente con «core-runtime bounded».
- **Q2 [scope]:** gli **hook** del dogfood usano `.venv` o `uv run --project .sertor`? Se già coerenti, fuori
  ambito; altrimenti valutare il repoint qui o in feature adiacente.

---

**Commit proposto:** `docs(requirements): E15-FEAT-001(+007) requisiti — dogfood runtime installato tracking HEAD`
