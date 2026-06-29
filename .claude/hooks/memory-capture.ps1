<#
.SYNOPSIS
  Automatic (non-blocking, non-fatal) end-of-session capture — thin wrapper around the CLI.

.DESCRIPTION
  Host-specific trigger (Claude Code, SessionEnd) that adapts the host event to the host-agnostic
  command `sertor-rag memory archive` (feature 035, FR-010..018). Contains NO archiving logic
  (FR-011): all work is delegated to the core via the CLI.

  Discipline (same as wiki-pending-check.ps1):
    1. Privacy gate (D2): if $env:SERTOR_MEMORY is not enabled → exit 0, no output (FR-015).
    2. Non-fatal: the CLI is invoked inside try/catch, its exit code is ignored, output suppressed
       (2>$null); the script ALWAYS exits 0 (FR-013, SC-005). A failure in archiving (or a missing
       `uv`/`sertor-rag`) must never break the session close.
    3. Non-blocking: capture is local and light (SQLite + file reads, no network); the host timeout
       in settings.json is the upper cap (FR-012).

  The hook input (JSON) arrives on stdin; the script tolerates its absence (manual invocation),
  falling back to '.' as the project root (F5 analyze).

.NOTES
  Manual verification (quickstart §3):
    $env:SERTOR_MEMORY=$null;  .\.claude\hooks\memory-capture.ps1; $LASTEXITCODE   # 0, no output
    $env:SERTOR_MEMORY='true'; .\.claude\hooks\memory-capture.ps1; $LASTEXITCODE   # 0 (always)
#>
[CmdletBinding()]
param(
    # Absorbs anything sent via the PowerShell pipeline (manual `... | & script`) without binding
    # errors; the real hook payload is read from the process stdin below, not from here.
    [Parameter(ValueFromPipeline = $true, ValueFromRemainingArguments = $true)]
    $PipelineInput
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

function Write-HookBreadcrumb {
    <#
      Best-effort breadcrumb of the LAST hook failure (E10-FEAT-019), twin of `.rag-health.json`.
      Writes a single, OVERWRITTEN `.sertor/.last-hook-error` (schema `hook.error/1`) so a silently
      swallowed degradation leaves an inspectable trace. EVERYTHING runs inside try/catch: a write
      failure NEVER makes the hook fatal (it still exits 0). `Reason` is a FIXED hook-local string
      (secret-free): never `$_.Exception.Message` nor raw vehicle output (REQ-008).
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Hook,
        [Parameter(Mandatory = $true)][string]$Reason
    )
    try {
        $runtimeDir = Join-Path $Root '.sertor'
        if (-not (Test-Path $runtimeDir)) { New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null }
        $statePath = Join-Path $runtimeDir '.last-hook-error'
        $timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        $state = [ordered]@{
            schema = 'hook.error/1'
            hook   = $Hook
            ts     = $timestamp
            reason = $Reason
        }
        ($state | ConvertTo-Json -Depth 4) | Set-Content -Path $statePath -Encoding UTF8
        [Console]::Error.WriteLine("hook '$Hook' degraded: $Reason (see .sertor/.last-hook-error)")
    } catch { }
}

# --- privacy gate: no-op exit 0 unless memory is explicitly enabled (match _bool_env of the core) ---
$enabled = $false
if ($env:SERTOR_MEMORY) {
    $enabled = @('true', '1', 'yes', 'on') -contains $env:SERTOR_MEMORY.Trim().ToLowerInvariant()
}
if (-not $enabled) { exit 0 }   # memory off → silent no-op (FR-015)

# --- hook input (JSON on stdin); tolerant if absent (manual invocation, F5) ---
$raw = ''
try { $raw = [Console]::In.ReadToEnd() } catch {}
$hook = $null
if ($raw -and $raw.Trim()) { try { $hook = $raw | ConvertFrom-Json } catch { $hook = $null } }

# --- project root: harness env, then hook cwd, then current directory ---
$root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR }
        elseif ($hook -and $hook.cwd) { $hook.cwd }
        else { '.' }
# Resolve to an absolute path so `--project` is cwd-independent (audit ISSUE-03: a bare `uv run`
# resolves the project/venv from the CURRENT directory, which may NOT be the project root when the
# host fires the hook from elsewhere; pin the runtime explicitly below). Best-effort.
try { $root = (Resolve-Path -LiteralPath $root -ErrorAction Stop).Path } catch {}

# --- delegate to the host-agnostic command; absorb any outcome, always exit 0 (FR-013) ---
# E10-FEAT-017 (audit ISSUE-03): resolve the CLI robustly, never a cwd-fragile bare `uv run`.
# Once the RAG runtime is installed the CLI lives in `.sertor/.venv` and is NOT on PATH; prefer
# `uv run --project <root>/.sertor` (PATH- and cwd-independent: it pins the runtime regardless of the
# working directory), and fall back to the `sertor-rag` executable inside that venv only if `uv` is
# unavailable. Mirror of wiki-pending-check.ps1 / rag-freshness.ps1. Any failure → silent exit 0.
$reason = $null
try {
    Push-Location $root
    $runtimeDir = Join-Path $root '.sertor'
    if (Test-Path $runtimeDir) {
        uv run --project $runtimeDir sertor-rag memory archive 2>$null
    } else {
        # No `.sertor` runtime: try a global `sertor-rag` on PATH (e.g. a global install).
        sertor-rag memory archive 2>$null
    }
    # R-1: a non-zero exit of the vehicle does NOT throw in PowerShell — inspect $LASTEXITCODE so a
    # "ran but failed" archive is fail-loud too, not only a missing `uv` (caught below).
    if ($LASTEXITCODE -ne 0) { $reason = "sertor-rag memory archive exited $LASTEXITCODE" }
    Pop-Location
} catch {
    try { Pop-Location } catch {}
    # `uv` itself missing: fall back to the CLI executable inside the project venv (PATH-independent),
    # Windows (`Scripts/sertor-rag.exe`) or POSIX (`bin/sertor-rag`). Still non-fatal.
    try {
        $venvCli = Join-Path $root '.sertor/.venv/Scripts/sertor-rag.exe'   # Windows
        if (-not (Test-Path $venvCli)) {
            $venvCli = Join-Path $root '.sertor/.venv/bin/sertor-rag'       # POSIX
        }
        if (Test-Path $venvCli) {
            Push-Location $root
            & $venvCli memory archive 2>$null
            if ($LASTEXITCODE -ne 0) { $reason = "venv sertor-rag exited $LASTEXITCODE" }
            Pop-Location
        } else {
            $reason = "uv and venv sertor-rag both unavailable"
        }
    } catch {
        try { Pop-Location } catch {}   # CLI unavailable / error: non-fatal
        if (-not $reason) { $reason = "uv and venv sertor-rag both unavailable" }
    }
}

# E10-FEAT-019: a silently swallowed failure leaves an inspectable breadcrumb (never fatal).
if ($reason) { Write-HookBreadcrumb -Root $root -Hook 'memory-capture' -Reason $reason }

exit 0   # ALWAYS — any failure of the command must never break the session close (SC-005)
