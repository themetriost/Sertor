<#
.SYNOPSIS
  Automatic (non-blocking) trigger for wiki maintenance — thin wrapper around the CLI.

.DESCRIPTION
  Delegates logic to the host-agnostic deterministic core: invokes
    sertor-wiki-tools scan --config <root>/wiki/wiki.config.toml --root <root> --json
  and maps the `wiki.scan/1` contract (`pending`, `message`) to the hook format. No
  duplicate mtime heuristics here: the single source of truth is the CLI (Principle X, no hard-coded paths).

  The logical BODY (delegation to the CLI, computing the pending count) is ONE source; only the
  OUTPUT shape is rendered NATIVELY per assistant (FEAT-011, no dual-field — contract
  hook-output-contract.md):
    - claude (default, non-regression): top-level `{ systemMessage }` for both Stop and SessionEnd.
    - copilot + Stop (→ agentStop event): `{ decision = "allow"; reason }` — NON-blocking (never
      `block` for a reminder).
    - copilot + SessionEnd (→ sessionEnd event): NO stdout consumed by Copilot; message → stderr.
  If there is no pending work (or the CLI is unavailable): no output, exit 0.
  The hook input (JSON) arrives on stdin; the script is tolerant if absent (manual tests).
#>
[CmdletBinding()]
param(
    [ValidateSet('Stop', 'SessionEnd')][string]$Mode = 'Stop',
    [ValidateSet('claude', 'copilot')][string]$Assistant = 'claude'
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

# --- hook input (JSON on stdin) ---
$raw = ''
try { $raw = [Console]::In.ReadToEnd() } catch {}
$hook = $null
if ($raw -and $raw.Trim()) { try { $hook = $raw | ConvertFrom-Json } catch { $hook = $null } }

# --- anti-loop guard: if Claude is already in a Stop hook cycle, let it finish ---
if ($Mode -eq 'Stop' -and $hook -and $hook.stop_hook_active) { exit 0 }

# --- project root: harness env, then hook cwd, then current directory ---
$root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR }
        elseif ($hook -and $hook.cwd) { $hook.cwd }
        else { '.' }
# Resolve to an absolute path so `--config`/`--root` are cwd-independent. FEAT-010: the CLI is
# invoked via `uv run --project .sertor` below (PATH-independent; keeps the working directory).
try { $root = (Resolve-Path -LiteralPath $root -ErrorAction Stop).Path } catch {}

# feature 016: config lives in wiki/; fallback to the old root path for hosts in transition.
$config = Join-Path $root 'wiki/wiki.config.toml'
if (-not (Test-Path $config)) {
    $legacy = Join-Path $root 'wiki.config.toml'
    if (Test-Path $legacy) { $config = $legacy } else { exit 0 }  # no host config → nothing to do
}

# --- delegate to the deterministic core: scan --json → wiki.scan/1 contract ---
# FEAT-010: resolve the CLI robustly. Once the RAG runtime is installed it lives in `.sertor/.venv`
# and is NOT on PATH; prefer `uv run --project .sertor` (PATH-independent; keeps the working
# directory, so relative paths resolve from the project root), and fall back to a bare
# `sertor-wiki-tools` only if there is no `.sertor` (e.g. a global install). Any failure → silent
# exit 0 (below): the hook never breaks the session.
$scan = $null
try {
    Push-Location $root
    $runtimeDir = Join-Path $root '.sertor'
    if (Test-Path $runtimeDir) {
        $out = uv run --project $runtimeDir sertor-wiki-tools scan --config $config --root $root --json 2>$null
    } else {
        $out = sertor-wiki-tools scan --config $config --root $root --json 2>$null
    }
    Pop-Location
    if ($out) { $scan = ($out | Select-Object -Last 1 | ConvertFrom-Json) }
} catch {
    try { Pop-Location } catch {}
    # E10-FEAT-019: `sertor-wiki-tools scan` not resolvable or in error → a path that was silently
    # swallowed; leave an inspectable breadcrumb (fixed string, no `$_` — R-3) then exit 0 (non-fatal).
    # NB: a no-config or `pending <= 0` outcome is a DEFINED no-op (handled above/below), not a
    # failure → no breadcrumb there.
    Write-HookBreadcrumb -Root $root -Hook 'wiki-pending-check' -Reason "sertor-wiki-tools scan unavailable or failed"
    exit 0   # CLI unavailable / error: non-fatal hook, breadcrumb left, no noise
}

if (-not $scan -or $scan.schema -ne 'wiki.scan/1' -or [int]$scan.pending -le 0) { exit 0 }

$pending = [int]$scan.pending

# --- build the localized message (shared body — same for every assistant) ---
if ($Mode -eq 'Stop') {
    $msg = "$($scan.message) Per the golden rule: consider delegating to the wiki-curator " +
           "agent (record operation) or triggering a wiki consolidation."
}
else {
    $msg = "Wiki: $pending modified files are not yet recorded. At the next session, delegate " +
           "to the wiki-curator agent (record) or trigger a wiki consolidation."
}

# --- render the output NATIVELY per assistant (FEAT-011, no dual-field) ---
if ($Assistant -eq 'copilot') {
    if ($Mode -eq 'Stop') {
        # agentStop event: NON-blocking decision (never `block` for a reminder). FR-007 / O3.
        $out = @{ decision = "allow"; reason = $msg }
        $out | ConvertTo-Json -Compress -Depth 5
        exit 0
    }
    else {
        # sessionEnd event: Copilot does NOT consume stdout here; surface the message on stderr. O5.
        [Console]::Error.WriteLine($msg)
        exit 0
    }
}

# claude (default): top-level systemMessage for both Stop and SessionEnd (non-regression). O6.
# NB: for the Stop event the Claude harness does NOT support hookSpecificOutput.additionalContext
# (valid only for UserPromptSubmit/PostToolUse/PostToolBatch); the non-blocking message goes in
# systemMessage (top-level), as the SessionEnd branch does. See the Claude Code hook schema.
$out = @{ systemMessage = $msg }
$out | ConvertTo-Json -Compress -Depth 5
exit 0
