<#
.SYNOPSIS
  Start-of-session version-update signal — reads the persisted state and warns if behind.

.DESCRIPTION
  Host-specific trigger (SessionStart, Claude) that reads `.sertor/.version-check.json` (written by
  `version-check.ps1` at the previous SessionEnd) and, if the verdict is `behind`, emits on stdout
  an update notice that Claude receives as session-start context (E2-FEAT-013, FR-003).

  D<->N boundary (FR-014/W4): this script does NOT apply any update (that is the user's decision —
  FR-005/CS-4). It ONLY warns; the user runs `sertor upgrade` / `uvx --refresh`. No LLM, no
  `sertor_core`, ZERO network (the GET happened at SessionEnd — RNF-1/W6).

  Logic (data-model §3b):
    1. read `.sertor/.version-check.json` (root from $env:CLAUDE_PROJECT_DIR -> '.').
    2. file absent OR verdict != "behind" -> no-op (exit 0, no output): INV-1, no superfluous
       notice on up-to-date/ahead/unknown (FR-004/010).
    3. verdict == "behind" -> emit the notice (installed, latest, update command); if `dimensions`
       is present, name which dimension(s) are behind (FR-012/US6).

  Always exits 0 (FR-009): the try/catch absorbs a missing file, malformed JSON, any read error.
  Host-agnostic (RNF-3): no path hardcoded to a specific project.

.PARAMETER Assistant
  The host assistant (expected: `claude`). Used to tailor the emitted message; extendable to future
  assistants without a breaking change.

.NOTES
  Manual verification (quickstart):
    .\.claude\hooks\version-check-start.ps1 -Assistant claude; $LASTEXITCODE   # 0 (always)
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
    $statePath = Join-Path (Join-Path $root '.sertor') '.version-check.json'

    if (-not (Test-Path $statePath)) { exit 0 }   # no state yet -> no-op (INV-1)

    $state = $null
    try { $state = Get-Content -Path $statePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $state = $null }
    if (-not $state) { exit 0 }   # malformed -> no-op (non-fatal, FR-009)

    if ($state.verdict -ne 'behind') { exit 0 }   # up-to-date/ahead/unknown -> no-op (INV-1)

    $installed = if ($state.installed) { [string]$state.installed } else { 'unknown' }
    $latest = if ($state.latest) { [string]$state.latest } else { 'unknown' }

    # Name the behind dimension(s) if the per-dimension stamps are present (FR-012/US6).
    $dimText = ''
    if ($state.dimensions) {
        $behind = @()
        foreach ($p in $state.dimensions.PSObject.Properties) {
            $behind += "$($p.Name) $($p.Value)"
        }
        if ($behind.Count -gt 0) { $dimText = " Installed dimensions: $($behind -join ', ')." }
    }

    # Update notice (stdout = SessionStart context for the agent — FR-003, D<->N FR-014). The
    # script only WARNS; the user decides and runs the update command (FR-005/CS-4).
    Write-Output ("SERTOR UPDATE AVAILABLE: installed $installed, latest $latest.$dimText " +
        "To update, run ``sertor upgrade`` (or ``uvx --refresh sertor`` if installed via uvx). " +
        "This is only a notice — no update is applied automatically.")
} catch {
    # Any error -> no-op, non-fatal.
}

exit 0   # ALWAYS (FR-009)
