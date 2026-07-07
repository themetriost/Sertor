# Quickstart — RUNBOOK asset-install (Phase 1)

Procedura **ripetibile, reversibile e ispezionabile** per portare il dogfood alla process-fidelity: gli
asset host-facing prodotti dai **veri** installer. Operazione **distruttiva sul repo vivo** → si esegue su
branch (`089-asset-install`), si ispeziona il diff, poi si committa (mai su master diretto).

> **Prerequisiti:** rete (per `uvx`/`specify init`); `.venv` di sviluppo intatto per i test; branch pulito.
> **Confine:** i test/sviluppo restano su `.venv` (invariato); questa procedura tocca lo **stato del
> dogfood**, non il ciclo di sviluppo (NFR-4).

## 0. Prepara la policy EOL (fatta UNA volta, prima degli installer)

Evita il churn CRLF che renderebbe illeggibile il diff dell'install (D1).

```powershell
# .gitattributes alla radice del dogfood
Set-Content -Path .gitattributes -Value "* text=auto eol=lf`n" -NoNewline -Encoding utf8
git add .gitattributes
git add --renormalize .          # allinea l'index a LF
git ls-files --eol | Select-String "crlf"   # atteso: nessun match testuale spurio
```

Poi rinormalizza il **bundle** `assets/` dei package (guardia byte LF↔LF) e aggiungi il `.gitattributes`
al **template installer** wiki/rag (host-facing — vedi tasks). Commit separato «policy EOL».

## 1. Esegui i 3 installer sul dogfood (ordine: flow → rag → wiki)

Come farebbe un ospite reale, dal `git+url@<HEAD>` (o dall'editable per il dry-run). Su branch usa-e-getta
per il **primo** giro di scoperta; poi sul branch di feature per l'esito committabile.

```powershell
# 1. governance (machinery SpecKit + blocco SDLC; preservante su costituzione/plan-template via FEAT-005)
sertor-flow install --assistant claude

# 2. RAG (hook/skill/agenti RAG + wiring settings.json PreToolUse + blocco RAG-USAGE + cli-reference)
sertor install rag --assistant claude

# 3. wiki (struttura wiki + blocco WIKI-RITUAL)
sertor install wiki --assistant claude
```

> **Osserva l'esito (NFR-2):** ogni comando stampa un `InstallReport` (skipped/updated/created/preserved).
> Atteso dal dry-run: ~tutti gli asset `skipped (already present)`; residuo = ~174 righe in `CLAUDE.md`
> (3 blocchi) + hook in `settings.json` + `.sertor/sertor-cli-reference.md` creato.

## 2. Ispeziona il diff (il gate di reversibilità — FR-009/R-1)

```powershell
git status --porcelain
git diff -- CLAUDE.md settings.json .claude/ .specify/ wiki/
git diff --stat src/sertor_core/    # DEVE essere vuoto (Principio XI)
```

- **Cerca clobber non mappati (R-1):** qualunque artefatto curato (`.env`, costituzione, `.mcp.json`,
  `wiki.config`, prosa `CLAUDE.md`) che risulti **cambiato** → **STOP**, valuta se estendere la
  preservazione dell'installer (come FEAT-005 per `plan-template`) prima di procedere.
- **Il diff DEVE essere solo contenuto reale**, 0 righe da EOL (grazie allo step 0).

## 3. Riconcilia `CLAUDE.md` (ibrido per-blocco — D3)

- **`SERTOR:RAG-USAGE`** → tieni il blocco; sfronda dalla prosa i duplicati puri.
- **`SERTOR:WIKI-RITUAL`** → la prosa dogfood vince; valuta di rimuovere/minimizzare il blocco (evita la
  ridondanza — la prosa IT è più ricca).
- **`SERTOR:SDLC-RITUAL`** → ibrido: tieni il blocco (7 fasi SpecKit in forma-client) + togli dalla prosa i
  duplicati puri, lasciando solo ciò che il blocco non dice.
- **Invariante (SC-3):** ogni tema coperto una sola volta. `CLAUDE.md` resta **bilingue** (blocchi EN + prosa IT).

## 4. Risolvi il `wiki/log.md` legacy (D9 / FR-008)

```powershell
# il template crea wiki/log.md monolitico; il dogfood usa la rotazione wiki/log/<data>.md
Remove-Item wiki/log.md -ErrorAction SilentlyContinue   # scarta lo spurio; la conoscenza resta in wiki/log/
```

Allinea il template installer alla rotazione (slice) **o** dichiara `wiki/log/` come forma-client super-set
preservata; il resto → E15-FEAT-006.

## 5. Retrocedi sync/script a guardia (D8 / FR-006)

Aggiorna la documentazione perché **non** indichi più `sertor_installer.sync` / `materialize-speckit.ps1`
come modo di *ottenere* gli asset (la fonte è il vero install):
- header dei moduli `sync.py` (kit, sertor, sertor-flow) + `scripts/dev/materialize-speckit.ps1`;
- rituale post-merge in `CLAUDE.md` (se cita il sync come via).
Le **guardie byte** restano attive e verdi.

## 6. Verifica (i contratti — vedi `contracts/verification.md`)

```powershell
# idempotenza: ri-esegui i 3 installer → 0 diff distruttivo
sertor-flow install --assistant claude; sertor install rag --assistant claude; sertor install wiki --assistant claude
git status --porcelain     # atteso: vuoto (o superset dichiarato)

# guardie byte + suite completa + lint (gate pre-merge FEAT-008)
uv run pytest -m "not cloud"
uv run ruff check .
git ls-files --eol | Select-String "crlf"   # repo EOL-consistente
```

## 7. Doc utente (FEAT-010, host-facing — regola CLAUDE.md §Feature completa 3)

Aggiorna `docs/install.md` (+ quick-start `install-claude.md`, `README.md` dove pertinente) con la nota
sulla policy `.gitattributes`/EOL depositata dal template: perché c'è, cosa fa su host Windows.

## 8. Commit + rituale post-merge

Delega a `configuration-manager` (branch+PR, mai master diretto). Dopo il merge: re-lock runtime
(`scripts/dev/relock-runtime.ps1`) → re-index (`sertor-rag index .`) → smoke MCP → mostra EXEC roadmap.

---

## Reversibilità (se qualcosa va storto)

Tutto è su branch, non committato finché lo step 2 non è verde:

```powershell
git checkout -- .        # scarta le modifiche dell'install non ancora committate
git clean -fd .claude .specify wiki   # rimuovi file nuovi indesiderati (ATTENZIONE: ispeziona prima)
```

Nessuno stato curato è perso irreversibilmente (FR-012 / NFR-5).
