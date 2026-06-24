<#
.SYNOPSIS
  Deterministic end-of-session RAG freshness enforcement — thin wrapper around the CLI vehicles.

.DESCRIPTION
  Host-specific trigger (SessionEnd) that adapts the host event to the host-agnostic vehicles
  `sertor-rag index` / `sertor-rag doctor` (E10-FEAT-011, FR-001..011). Contains NO change-detection
  logic (FR-002): the re-index is UNCONDITIONAL and the skip-when-nothing-changed is delegated to the
  core's incremental indexer (FEAT-009 manifest + FEAT-019 embedding cache). NEVER imports
  `sertor_core` (Principio XI): all work is done through the `sertor-rag` CLI.

  Orchestration (NOT change-detection — FR-002):
    1. `uv run sertor-rag index .`        — unconditional re-index (skip delegated to the core).
    2. `uv run sertor-rag doctor --json`  — health verdict per area + exit code.
    3. derive `verdict`: `degraded` if doctor exit code != 0 OR any area is `fail`/`warn`;
       otherwise `healthy` (FR-006).
    4. write `.sertor/.rag-health.json` (schema `rag.health/1`, contract rag-health-state.md):
       degraded → `verdict`/`timestamp`/`reason`/`areas`/`exit_code` + a prominent message (FR-009);
       healthy → REWRITTEN with `verdict: "healthy"` (NOT deleted — INV-1, so the start signal
       reads `healthy` and no-ops).

  Discipline (same as memory-capture.ps1):
    - Non-fatal: every step runs inside try/catch; the script ALWAYS exits 0 (FR-017, R-2). A failure
      of `index`/`doctor` (or a missing `uv`/`sertor-rag`) must never break the session close; on a
      catastrophic internal error the state file is NOT written (silence > corrupt data).
    - Non-blocking: the host timeout in settings is the upper cap (NFR-2).
    - No LLM is ever invoked (Principio D<->N, NFR-5): only the `sertor-rag` vehicles.
    - Host-agnostic (NFR-4): no path hardcoded to a specific project.
    - Privacy (NFR-3/INV-2): `reason`/`areas` come from `doctor --json` (already scrubbed by the
      vehicle); the hook never composes new text from `.sertor/.env`.

  The hook input (JSON) arrives on stdin; the script tolerates its absence (manual invocation),
  falling back to '.' as the project root.

.NOTES
  Manual verification (quickstart):
    .\.claude\hooks\rag-freshness.ps1; $LASTEXITCODE   # 0 (always); writes .sertor/.rag-health.json
#>
[CmdletBinding()]
param(
    # Absorbs anything sent via the PowerShell pipeline (manual `... | & script`) without binding
    # errors; the real hook payload is read from the process stdin below, not from here.
    [Parameter(ValueFromPipeline = $true, ValueFromRemainingArguments = $true)]
    $PipelineInput
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

# --- hook input (JSON on stdin); tolerant if absent (manual invocation) ---
$raw = ''
try { $raw = [Console]::In.ReadToEnd() } catch {}
$hook = $null
if ($raw -and $raw.Trim()) { try { $hook = $raw | ConvertFrom-Json } catch { $hook = $null } }

# --- project root: harness env, then hook cwd, then current directory ---
$root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR }
        elseif ($hook -and $hook.cwd) { $hook.cwd }
        else { '.' }

try {
    Push-Location $root
    try {
        # --- 1. unconditional re-index via the vehicle (skip-when-nothing-changed in the core) ---
        # Output suppressed; a failure here must not be fatal (the doctor below reports the truth).
        try { uv run sertor-rag index . 2>$null | Out-Null } catch {}

        # --- 2. health verdict via the vehicle (--json, stable schema doctor.report/1) ---
        $doctorOut = ''
        $doctorExit = 0
        try {
            $doctorOut = uv run sertor-rag doctor --json 2>$null | Out-String
            $doctorExit = $LASTEXITCODE
            if ($null -eq $doctorExit) { $doctorExit = 0 }
        } catch {
            $doctorOut = ''
            $doctorExit = 1
        }

        # --- 3. derive verdict + reason + per-area map from the doctor JSON ---
        $verdict = 'healthy'
        $reason = ''
        $areas = $null
        $report = $null
        if ($doctorOut -and $doctorOut.Trim()) {
            try { $report = $doctorOut | ConvertFrom-Json } catch { $report = $null }
        }
        if ($report -and $report.areas) {
            $areaMap = [ordered]@{}
            foreach ($a in $report.areas) {
                # `doctor --json` emits an area object with `name` + `status`; tolerate shapes.
                $name = if ($a.name) { [string]$a.name } elseif ($a.area) { [string]$a.area } else { $null }
                $status = if ($a.status) { [string]$a.status } else { $null }
                if ($name -and $status) {
                    $areaMap[$name] = $status
                    if ($status -eq 'fail' -or $status -eq 'warn') {
                        $verdict = 'degraded'
                        if (-not $reason) { $reason = "$name area: $status" }
                    }
                }
            }
            if ($areaMap.Count -gt 0) { $areas = $areaMap }
        }
        if ($doctorExit -ne 0) {
            $verdict = 'degraded'
            if (-not $reason) { $reason = "doctor reported failure (exit $doctorExit)" }
        }

        # --- 4. persist the state under .sertor/ (survives `index --full`, INV-4) ---
        $sertorDir = Join-Path $root '.sertor'
        if (-not (Test-Path $sertorDir)) { New-Item -ItemType Directory -Path $sertorDir -Force | Out-Null }
        $statePath = Join-Path $sertorDir '.rag-health.json'
        $timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

        $state = [ordered]@{
            schema    = 'rag.health/1'
            verdict   = $verdict
            timestamp = $timestamp
            reason    = $reason
            exit_code = $doctorExit
        }
        if ($areas) { $state['areas'] = $areas }

        ($state | ConvertTo-Json -Depth 6) | Set-Content -Path $statePath -Encoding UTF8

        if ($verdict -eq 'degraded') {
            # Prominent, fail-loud message at session close (FR-009).
            Write-Host "[sertor-rag] RAG health DEGRADED: $reason" -ForegroundColor Yellow
            Write-Host "[sertor-rag] At next session start you will be prompted to run 'sertor-rag index .' and/or reconnect the MCP server."
        }
    } finally {
        Pop-Location
    }
} catch {
    # Catastrophic internal error: silent, non-fatal; the state file is left untouched.
    try { Pop-Location } catch {}
}

exit 0   # ALWAYS — any failure of the vehicles must never break the session close (FR-017, R-2)
