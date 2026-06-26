<#
.SYNOPSIS
  Deterministic end-of-session RAG freshness enforcement — thin wrapper around the CLI vehicles.

.DESCRIPTION
  Host-specific trigger (SessionEnd) that adapts the host event to the host-agnostic vehicles
  `sertor-rag doctor` / `sertor-rag index` (E10-FEAT-011, refined by E10-FEAT-016). Contains NO
  change-detection logic (FR-002): the re-index is UNCONDITIONAL and the skip-when-nothing-changed is
  delegated to the core's incremental indexer (FEAT-009 manifest + FEAT-019 embedding cache). NEVER
  imports `sertor_core` (Principio XI): all work is done through the `sertor-rag` CLI.

  FULLY NON-BLOCKING ORDER (E10-FEAT-016 refinement — EVERYTHING in the background):
    The hook has TWO modes, selected by the `-Worker` switch on this same script:

    FOREGROUND (normal SessionEnd invocation, no `-Worker`):
      1. resolve the project root (harness env / hook cwd / '.').
      2. RELAUNCH THIS SAME SCRIPT DETACHED via `Start-Process pwsh -WindowStyle Hidden`
         with `-Worker -Root <root>` — fire-and-forget — then return IMMEDIATELY (exit 0, < 1-2s).
         Passing `-Root` avoids re-reading stdin in the worker.
      The foreground does NO doctor, NO state write, NO index: it only spawns the worker. So the
      session close cost is just the spawn (FEAT-016 refinement: the ~13s `doctor` is now off the
      critical path too, not only the re-index).

    WORKER (`-Worker -Root <root>`, the detached process):
      1. `sertor-rag doctor --json`  — health verdict per area + exit code (deterministic).
      2. derive `verdict`: `degraded` if doctor exit code != 0 OR any area is `fail`/`warn`;
         otherwise `healthy` (FR-006).
      3. write `.sertor/.rag-health.json` ATOMICALLY (temp + Move-Item -Force) with schema
         `rag.health/1` (contract rag-health-state.md):
           degraded → `verdict`/`timestamp`/`reason`/`areas`/`exit_code` + a prominent message
           emitted on stderr/log (FR-009); never blocks (it is already off the session path);
           healthy → REWRITTEN with `verdict: "healthy"` (NOT deleted — INV-1, so the start signal
           reads `healthy` and no-ops).
      4. `sertor-rag index .` — unconditional re-index. Synchronous INSIDE the worker is fine: the
         worker is already detached, so it never blocks the session close.

  Accepted semantics (DA-2): the health state is written by the worker AFTER the foreground hook has
  returned, so it may lag by at most one session; the SessionStart signal reads the most recent
  `.rag-health.json` available. The fail-loud `degraded` message is emitted by the worker.

  Discipline (same as memory-capture.ps1):
    - Non-fatal: every step runs inside try/catch; the script ALWAYS exits 0 (FR-017, R-2). A failure
      of the spawn (foreground) or of `doctor`/`index` (worker) must never break the session close;
      on a catastrophic internal error the state file is NOT written (silence > corrupt data).
    - Non-blocking: the host timeout in settings only needs to cover the foreground SPAWN — not the
      doctor, not the re-index (both run in the detached worker; FEAT-016 refinement).
    - No LLM is ever invoked (Principio D<->N, NFR-5): only the `sertor-rag` vehicles.
    - Host-agnostic (NFR-4): no path hardcoded to a specific project.
    - Privacy (NFR-3/INV-2): `reason`/`areas` come from `doctor --json` (already scrubbed by the
      vehicle); the hook never composes new text from `.sertor/.env`.
    - Concurrency: the worker's `index` is covered by the core's single-writer lock
      (`IndexLockedError`, FEAT-009); an overlapping re-index no-ops harmlessly.
    - The CLI lives in the `.sertor/.venv` and is NOT on PATH: invoked via
      `uv run --project <root>/.sertor` (PATH-independent; keeps the working directory so `index .`
      resolves from the project root).

  The hook input (JSON) arrives on stdin in foreground mode; the script tolerates its absence
  (manual invocation), falling back to '.' as the project root.

.NOTES
  Manual verification (quickstart):
    .\.claude\hooks\rag-freshness.ps1; $LASTEXITCODE   # 0 (always); spawns the detached worker
                                                       # which then writes .sertor/.rag-health.json
#>
[CmdletBinding()]
param(
    # When set, this process IS the detached background worker: run doctor + write health + index.
    [switch]$Worker,
    # Project root passed to the worker so it does NOT need to re-read stdin (FEAT-016 refinement).
    [string]$Root,
    # Absorbs anything sent via the PowerShell pipeline (manual `... | & script`) without binding
    # errors; the real hook payload is read from the process stdin below, not from here.
    [Parameter(ValueFromPipeline = $true, ValueFromRemainingArguments = $true)]
    $PipelineInput
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}


function Invoke-RagFreshnessWorker {
    <#
      Detached worker body: doctor -> derive verdict -> atomic state write -> unconditional re-index.
      Runs INSIDE the background process, so synchronous work here never blocks the session close.
    #>
    param([Parameter(Mandatory = $true)][string]$Root)

    try {
        Push-Location $Root
        try {
            $runtimeDir = Join-Path $Root '.sertor'

            # --- 1. health verdict via the vehicle (--json, stable schema doctor.report/1) ---
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

            # --- 3. persist the state under .sertor/ ATOMICALLY (survives `index --full`, INV-4;
            #        FEAT-016 REQ-004 freshness, REQ-006 atomic write avoids torn state) ---
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
                # Fail-loud message (FR-009). Emitted on stderr from the detached worker so it never
                # interferes with the host's consumption of the SessionEnd hook output.
                [Console]::Error.WriteLine("[sertor-rag] RAG health DEGRADED: $reason")
                [Console]::Error.WriteLine("[sertor-rag] At next session start you will be prompted to run 'sertor-rag index .' and/or reconnect the MCP server.")
            }

            # --- 4. unconditional re-index via the vehicle (synchronous inside the worker) ---
            # FR-002: skip-when-nothing-changed is delegated to the core's incremental indexer.
            # Overlapping runs are serialized by the core's single-writer lock (REQ-006/R-2).
            try {
                uv run --project $runtimeDir sertor-rag index . 2>$null | Out-Null
            } catch {
                # Non-fatal: the state verdict is already written; skip the re-index this time.
            }
        } finally {
            Pop-Location
        }
    } catch {
        # Catastrophic internal error in the worker: silent, non-fatal.
        try { Pop-Location } catch {}
    }
}


if ($Worker) {
    # --- WORKER MODE: we ARE the detached background process. Do the real work, then exit 0. ---
    $workerRoot = if ($Root) { $Root } else { '.' }
    Invoke-RagFreshnessWorker -Root $workerRoot
    exit 0
}

# --- FOREGROUND MODE: spawn the detached worker, return immediately. ---

# hook input (JSON on stdin); tolerant if absent (manual invocation)
$raw = ''
try { $raw = [Console]::In.ReadToEnd() } catch {}
$hook = $null
if ($raw -and $raw.Trim()) { try { $hook = $raw | ConvertFrom-Json } catch { $hook = $null } }

# project root: harness env, then hook cwd, then current directory
$root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR }
        elseif ($hook -and $hook.cwd) { $hook.cwd }
        else { '.' }

# Relaunch THIS SAME SCRIPT detached, in worker mode, so doctor + state write + re-index all run
# off the session-close critical path (FEAT-016 refinement). The foreground returns in < 1-2s.
# Start-Process is portable across pwsh on Windows and POSIX (REQ-016).
try {
    $self = $PSCommandPath
    Start-Process -FilePath 'pwsh' `
        -ArgumentList @('-NoProfile', '-File', $self, '-Worker', '-Root', $root) `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -ErrorAction Stop | Out-Null
} catch {
    # No usable detached-process facility (REQ-016, honest degrade): rather than block the session
    # close with a synchronous doctor + index, we skip the freshness work this time. Never fatal.
}

exit 0   # ALWAYS — any failure must never break the session close (FR-017, R-2)
