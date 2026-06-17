<#
.SYNOPSIS
  SessionStart directive — loads the wiki/roadmap context at the start of a session.

.DESCRIPTION
  Single source (FEAT-011, anti-drift): the directive that was inline in the Copilot/Claude hook
  wiring (`wiki.hooks.json`) is extracted here so BOTH families share ONE body. It computes the
  name of the latest log partition and emits the "load roadmap/index/log + show the EXEC summary"
  directive.

  The OUTPUT is rendered NATIVELY per assistant (contract hook-output-contract.md):
    - claude (default): the directive on stdout (the harness uses it as the SessionStart context) —
      non-regression with the historical inline behavior.
    - copilot (VS Code, `type:"command"`): `{ additionalContext = "<directive>" }` as VALID JSON,
      never a bare string ([ASSUNTO-VSC]: the `additionalContext` mechanism is NOT verified on a
      real VS Code client — declared as a gap, not "full parity").
  The Copilot CLI does NOT invoke this script: it uses a `type:"prompt"` wiring entry with the
  directive as a static prompt.

  Exit 0 always; stdlib PowerShell only, no external dependency.
#>
[CmdletBinding()]
param([ValidateSet('claude', 'copilot')][string]$Assistant = 'claude')

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

# --- project root: harness env (Claude), then current directory (host-agnostic) ---
$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }
$logDir = Join-Path $d 'wiki/log'
$log = if (Test-Path $logDir) {
    Get-ChildItem $logDir -Filter '*.md' |
        Where-Object { $_.Name -ne 'index.md' } |
        Sort-Object Name | Select-Object -Last 1 -ExpandProperty Name
} else { 'log.md' }

# --- the shared directive (single source — same words for every assistant) ---
$lines = @(
    'SESSION START - load the project context BEFORE replying to the user.',
    'Do this NOW, on your own initiative:',
    "1. Read (the outputs enter the context in full): wiki/syntheses/roadmap.md ; wiki/index.md (the wiki catalog) ; wiki/log/$log (the tail of the journal).",
    '2. Then show the user the executive summary of the roadmap: the block between the markers <!-- EXEC:START --> and <!-- EXEC:END --> of wiki/syntheses/roadmap.md.',
    'Reminder: during project work delegate the wiki update to the wiki-curator agent (see the instructions, Wiki and documentation section).'
)
$directive = $lines -join "`n"

# --- render the output NATIVELY per assistant (FEAT-011) ---
if ($Assistant -eq 'copilot') {
    # VS Code: additionalContext as VALID JSON [ASSUNTO-VSC]. O4 / FR-006.
    $out = @{ additionalContext = $directive }
    $out | ConvertTo-Json -Compress -Depth 5
    exit 0
}

# claude (default): the directive on stdout (the harness uses it as SessionStart context).
$directive
exit 0
