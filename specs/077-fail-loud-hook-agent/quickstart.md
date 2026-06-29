# Quickstart — Fail-loud breadcrumb + fallback agent (E10-FEAT-019)

Verifiche manuali/offline (PowerShell; nessuna rete, nessun `uv` necessario per le guardie).

## 1. Breadcrumb su rottura silenziosa (US1/US2)
```powershell
# Simula un memory-capture degradato (memoria ON, CLI non risolvibile):
$env:SERTOR_MEMORY = 'true'
.\.claude\hooks\memory-capture.ps1; $LASTEXITCODE      # → 0 SEMPRE
Get-Content .\.sertor\.last-hook-error                  # → JSON hook.error/1 (hook/ts/reason)
# stderr ha la nota: [sertor] hook 'memory-capture' degraded: …
```

## 2. No-op gated NON lascia traccia (US3)
```powershell
Remove-Item .\.sertor\.last-hook-error -ErrorAction SilentlyContinue
$env:SERTOR_MEMORY = $null
.\.claude\hooks\memory-capture.ps1; $LASTEXITCODE      # → 0, no-op
Test-Path .\.sertor\.last-hook-error                    # → False (nessun breadcrumb)
```

## 3. Persistenza + scrittura best-effort (US2)
```powershell
# Il file persiste tra sessioni (è su disco, non solo stderr).
# Best-effort: se .sertor/ non è scrivibile, l'hook esce comunque 0 (nessun nuovo path fatale).
```

## 4. Fallback negli agent (US6/US7) — verifica statica
```powershell
Select-String -Path packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md -Pattern 'STOP','guided-setup'
Select-String -Path packages/sertor/src/sertor_installer/assets/claude/agents/wiki-curator.md -Pattern 'STOP','wiki-playbook'
Select-String -Path packages/sertor-flow/src/sertor_flow/assets/claude/agents/requirements-analyst.md -Pattern 'STOP','requirements'
# Nessun `.claude/`, slash-command o nome Claude nella frase di fallback (host-agnostico).
```

## 5. Guardie (US8/US9)
```powershell
# lint breadcrumb + assert fallback + sync rag dogfood + RUNTIME_IGNORES
uv run pytest packages/sertor/tests/test_assets_hook_breadcrumb.py `
              packages/sertor/tests/test_assets_agent_fallback.py `
              tests/unit/test_assets_rag_dogfood_sync.py -q
# parità Copilot (riuso) + sync esistente restano verdi
uv run pytest packages/sertor/tests/test_assets_copilot_parity.py tests/unit/test_assets_sync.py -q
```

## 6. Sync dogfood dopo l'edit del canonico
```powershell
# wiki-pending-check + wiki-curator (assets/claude) → sync automatico:
uv run python -m sertor_installer.sync
# i 3 hook rag dogfood (.claude/hooks/) vanno ri-allineati a mano (poi la Guardia C verifica):
#   copy assets/rag/hooks/{memory-capture,rag-freshness,version-check}.ps1 → .claude/hooks/
```

## 7. `.gitignore` (US9)
```powershell
Select-String -Path .gitignore -Pattern '.last-hook-error'   # presente dopo install rag
git check-ignore .sertor/.last-hook-error                     # ignorato (runtime, non versionato)
```
