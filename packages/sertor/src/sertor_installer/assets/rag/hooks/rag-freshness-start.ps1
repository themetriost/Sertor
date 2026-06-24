<#
.SYNOPSIS
  Start-of-session RAG freshness signal — re-reads the persisted health state and INDUCES a fix.

.DESCRIPTION
  Host-specific trigger (SessionStart, Claude) that reads `.sertor/.rag-health.json` (written by
  `rag-freshness.ps1` at the previous SessionEnd) and, if the verdict is `degraded`, emits on stdout
  a directive that Claude receives as session-start context (E10-FEAT-011, FR-012..015).

  D<->N boundary (FR-014): this script does NOT run the correction (that would be judgement + a
  blocking cost at start). It ONLY induces — the agent decides and runs `sertor-rag index .` and/or
  reconnects the MCP server. No LLM is invoked (NFR-5).

  Logic:
    1. read `.sertor/.rag-health.json` (root from $env:CLAUDE_PROJECT_DIR -> '.').
    2. file absent OR verdict == "healthy" -> no-op (exit 0, no output): idempotency (NFR-6), no
       perpetual inducement (FR-015, INV-1).
    3. verdict == "degraded" -> emit the inducement directive (reason + the fix instruction).

  Always exits 0 (FR-017): the try/catch absorbs a missing file, malformed JSON, any read error.
  Host-agnostic (NFR-4): no path hardcoded to a specific project.

.PARAMETER Assistant
  The host assistant (expected: `claude`). Used to tailor the emitted message; extendable to future
  assistants without a breaking change.

.NOTES
  Manual verification (quickstart):
    .\.claude\hooks\rag-freshness-start.ps1 -Assistant claude; $LASTEXITCODE   # 0 (always)
#>
[CmdletBinding()]
param(
    [string]$Assistant = 'claude',
    # Absorbs anything sent via the PowerShell pipeline without binding errors.
    [Parameter(ValueFromPipeline = $true, ValueFromRemainingArguments = $true)]
    $PipelineInput
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

try {
    $root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }
    $statePath = Join-Path (Join-Path $root '.sertor') '.rag-health.json'

    if (-not (Test-Path $statePath)) { exit 0 }   # no state yet -> no-op (FR-015)

    $state = $null
    try { $state = Get-Content -Path $statePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $state = $null }
    if (-not $state) { exit 0 }   # malformed -> no-op (non-fatal, FR-017)

    if ($state.verdict -ne 'degraded') { exit 0 }   # healthy/unknown -> no-op (INV-1, NFR-6)

    $reason = if ($state.reason) { [string]$state.reason } else { 'unknown cause' }
    # Inducement directive (stdout = SessionStart context for the agent — FR-013, D<->N FR-014).
    Write-Output "RAG HEALTH DEGRADED ($reason). Before starting work: run ``sertor-rag index .`` and/or reconnect the MCP server to restore retrieval freshness. Do not proceed on potentially stale context."
} catch {
    # Any error -> no-op, non-fatal.
}

exit 0   # ALWAYS (FR-017)
