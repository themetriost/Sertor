<#
.SYNOPSIS
  Deterministic end-of-session RAG freshness enforcement — thin wrapper around the CLI vehicles.

.DESCRIPTION
  Host-specific trigger (SessionEnd) that adapts the host event to the host-agnostic vehicles
  `sertor-rag doctor` / `sertor-rag index` (E10-FEAT-011, refined by E10-FEAT-016). Contains NO
  change-detection logic (FR-002): the re-index is UNCONDITIONAL and the skip-when-nothing-changed is
  delegated to the core's incremental indexer (FEAT-009 manifest + FEAT-019 embedding cache). NEVER
  imports `sertor_core` (Principio XI): all work is done through the `sertor-rag` CLI.

  NON-BLOCKING ORDER (E10-FEAT-016, doctor-first + background re-index):
    1. `sertor-rag doctor --json`  — health verdict per area + exit code (fast, deterministic).
    2. derive `verdict`: `degraded` if doctor exit code != 0 OR any area is `fail`/`warn`;
       otherwise `healthy` (FR-006).
    3. write `.sertor/.rag-health.json` ALWAYS, BEFORE any index (schema `rag.health/1`, contract
       rag-health-state.md) — so the persisted health is NEVER stale/absent even on a large repo
       where the re-index is long (FEAT-016 REQ-004/REQ-005, DA-6):
         degraded → `verdict`/`timestamp`/`reason`/`areas`/`exit_code` + a prominent message (FR-009);
         healthy → REWRITTEN with `verdict: "healthy"` (NOT deleted — INV-1, so the start signal
         reads `healthy` and no-ops).
    4. `sertor-rag index .` — launched DETACHED / fire-and-forget (Start-Process), so the session
       close returns immediately (FEAT-016 REQ-001/002/003). Concurrency is handled by the core's
       single-writer lock (`IndexLockedError`, FEAT-009): an overlapping re-index no-ops harmlessly.
       The verdict above reflects the CURRENT on-disk state (pre-index); the background re-index
       freshens the corpus for the NEXT session (DA-2 accepted).

  Discipline (same as memory-capture.ps1):
    - Non-fatal: every step runs inside try/catch; the script ALWAYS exits 0 (FR-017, R-2). A failure
      of `doctor`/`index` (or a missing `uv`/`sertor-rag`) must never break the session close; on a
      catastrophic internal error the state file is NOT written (silence > corrupt data).
    - Non-blocking: the host timeout in settings only needs to cover `doctor` + the spawn of the
      detached index — NOT the re-index itself (FEAT-016 REQ-015, NFR non-blocking).
    - No LLM is ever invoked (Principio D<->N, NFR-5): only the `sertor-rag` vehicles.
    - Host-agnostic (NFR-4): no path hardcoded to a specific project.
    - Privacy (NFR-3/INV-2): `reason`/`areas` come from `doctor --json` (already scrubbed by the
      vehicle); the hook never composes new text from `.sertor/.env`.
    - The CLI lives in the `.sertor/.venv` and is NOT on PATH: invoked via
      `uv run --project <root>/.sertor` (PATH-independent; keeps the working directory so `index .`
      resolves from the project root).

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
        $runtimeDir = Join-Path $root '.sertor'

        # --- 1. health verdict via the vehicle (--json, stable schema doctor.report/1) ---
        # FEAT-016 (doctor-first): the verdict is computed and persisted BEFORE the re-index, so the
        # health state is never stale/absent even if the re-index is long-running or deferred.
        $doctorOut = ''
        $doctorExit = 0
        try {
            $doctorOut = uv run --project $runtimeDir sertor-rag doctor --json 2>$null | Out-String
            $doctorExit = $LASTEXITCODE
            if ($null -eq $doctorExit) { $doctorExit = 0 }
        } catch {
            $doctorOut = ''
            $doctorExit = 1
        }

        # --- 2. derive verdict + reason + per-area map from the doctor JSON ---
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

        # --- 3. persist the state under .sertor/ ALWAYS, before any index (survives `index --full`,
        #        INV-4; FEAT-016 REQ-004 freshness, REQ-006 atomic write avoids torn state) ---
        $sertorDir = $runtimeDir
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

        # Atomic write (REQ-006, no partial/torn state): write to a temp file then replace.
        $tmpPath = "$statePath.tmp"
        ($state | ConvertTo-Json -Depth 6) | Set-Content -Path $tmpPath -Encoding UTF8
        Move-Item -LiteralPath $tmpPath -Destination $statePath -Force

        if ($verdict -eq 'degraded') {
            # Prominent, fail-loud message at session close (FR-009).
            Write-Host "[sertor-rag] RAG health DEGRADED: $reason" -ForegroundColor Yellow
            Write-Host "[sertor-rag] At next session start you will be prompted to run 'sertor-rag index .' and/or reconnect the MCP server."
        }

        # --- 4. unconditional re-index via the vehicle, DETACHED / fire-and-forget ---
        # FEAT-016 (non-blocking): the re-index runs in a separate, detached process so the session
        # close returns immediately, regardless of how long the index takes on a large repo
        # (REQ-001/002/003). Skip-when-nothing-changed is delegated to the core's incremental indexer
        # (FR-002); overlapping runs are serialized by the core's single-writer lock (REQ-006/R-2).
        # Start-Process is portable across pwsh on Windows and POSIX (REQ-016).
        try {
            Start-Process -FilePath 'uv' `
                -ArgumentList @('run', '--project', $runtimeDir, 'sertor-rag', 'index', '.') `
                -WorkingDirectory $root `
                -WindowStyle Hidden `
                -ErrorAction Stop | Out-Null
        } catch {
            # No usable detached-process facility (REQ-016, honest degrade): the verdict is already
            # written above, so freshness of the STATE is preserved; we simply skip the re-index this
            # time rather than block the session close. Never fatal.
        }
    } finally {
        Pop-Location
    }
} catch {
    # Catastrophic internal error: silent, non-fatal; the state file is left untouched.
    try { Pop-Location } catch {}
}

exit 0   # ALWAYS — any failure of the vehicles must never break the session close (FR-017, R-2)
