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

# --- delegate to the host-agnostic command; absorb any outcome, always exit 0 (FR-013) ---
try {
    Push-Location $root
    uv run sertor-rag memory archive 2>$null
    Pop-Location
} catch {
    try { Pop-Location } catch {}   # CLI unavailable / error: silent, non-fatal
}

exit 0   # ALWAYS — any failure of the command must never break the session close (SC-005)
