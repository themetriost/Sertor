# Quickstart — enforcement deterministico della freschezza RAG (hook)

**Branch**: `076-enforcement-freschezza-rag` · verifica manuale (PowerShell, Windows).

> Premessa: l'hook **consuma** i vehicle `sertor-rag index` e `sertor-rag doctor` (su `master`).
> Tutti gli esempi sono offline; nessun LLM (NFR-5). Path assoluti per le operazioni, relativi nei
> riferimenti.

## 1. Hook a fine sessione — re-index + doctor + persistenza (US1/US2/US4)

```powershell
# corpus invariato → zero embedding (NFR-1): l'incrementale del core salta
& .\.claude\hooks\rag-freshness.ps1 ; $LASTEXITCODE          # 0 sempre
Get-Content .\.sertor\.rag-health.json | ConvertFrom-Json    # verdict/timestamp/areas/exit_code
```
Atteso: exit 0; `.sertor/.rag-health.json` scritto con `verdict` derivato da `doctor`. A corpus
invariato non si producono nuovi embedding (lo skip è del core, non dell'hook — FR-002/003).

## 2. Verdetto degradato → fail-loud (US4)

```powershell
# forza un degrado: indice assente o area doctor in fail
Remove-Item -Recurse -Force .\.sertor\.index* -ErrorAction SilentlyContinue
& .\.claude\hooks\rag-freshness.ps1 ; $LASTEXITCODE          # 0 (non-fatale)
(Get-Content .\.sertor\.rag-health.json | ConvertFrom-Json).verdict   # degraded
```
Atteso: `verdict=degraded`, `reason` nomina l'area, messaggio prominente emesso; exit 0 (FR-008/009/017).

## 3. Segnale a inizio sessione — induce se degradato (US3)

```powershell
& .\.claude\hooks\rag-freshness-start.ps1 -Assistant claude   # stato degradato → direttiva su stdout
& .\.claude\hooks\rag-freshness-start.ps1 -Assistant claude   # dopo guarigione (healthy) → no output (no-op)
$LASTEXITCODE                                                  # 0
```
Atteso: con stato `degraded`, la direttiva d'induzione (esegui `sertor-rag index .` / reconnect MCP)
è emessa; con `healthy`/assente, nessun output e nessuna induzione (FR-012/013/014, NFR-6).

## 4. Clear a guarigione — no loop (US4, R-1)

```powershell
& .\.claude\hooks\rag-freshness.ps1                           # con corpus sano → verdict=healthy
(Get-Content .\.sertor\.rag-health.json | ConvertFrom-Json).verdict   # healthy
& .\.claude\hooks\rag-freshness-start.ps1 -Assistant claude   # no output → niente inducement
```

## 5. Non-fatale e isolato (US6)

```powershell
$env:CLAUDE_PROJECT_DIR = 'C:\inesistente'                    # forza un errore interno
& .\.claude\hooks\rag-freshness.ps1 ; $LASTEXITCODE           # 0 (FR-017)
Remove-Item Env:\CLAUDE_PROJECT_DIR
& .\.claude\hooks\memory-capture.ps1 ; $LASTEXITCODE          # 0 — non disturbato (FR-018)
```

## 6. Distribuzione e parità (US8/US9)

```powershell
# Claude: deposita gli script + le voci SessionEnd/SessionStart
uvx --from "git+https://…#subdirectory=packages/sertor" sertor install rag --assistant claude
Test-Path .\.claude\hooks\rag-freshness.ps1                   # True
Test-Path .\.claude\hooks\rag-freshness-start.ps1             # True

# Copilot CLI: formato NATIVO (version:1, piatto); SessionStart = prompt statico (no script start)
uvx --from "git+…#subdirectory=packages/sertor" sertor install rag --assistant copilot-cli
Get-Content .\.github\hooks\sertor-hooks.json | ConvertFrom-Json   # version:1, entry piatte
Test-Path .\.github\hooks\rag-freshness.ps1                   # True (SessionEnd script)
# nessuno script rag-freshness-start.ps1 su Copilot (SessionStart = prompt)
```

## 7. Lifecycle granulare (US9)

```powershell
sertor uninstall rag --assistant claude                      # rimuove SOLO l'hook freschezza + voce
Test-Path .\.claude\hooks\rag-freshness.ps1                   # False
# memory-capture/wiki restano se altre capacità installate (isolamento)
```

## 8. Guardia di sync bundlato↔dogfood (US9, FR-024)

```powershell
uv run pytest tests/unit -k "rag_freshness and sync"         # asset bundlato == copia .claude/
uv run pytest packages/sertor/tests -k "freshness or install_rag"
```

## 9. Verifica D↔N (NFR-5)
Nessuno degli script invoca un LLM: cercano `sertor-rag`/file, mai un modello.

```powershell
Select-String -Path .\.claude\hooks\rag-freshness*.ps1 -Pattern 'sertor-rag|rag-health'  # match
Select-String -Path .\.claude\hooks\rag-freshness*.ps1 -Pattern 'openai|anthropic|llm'   # nessun match
```
