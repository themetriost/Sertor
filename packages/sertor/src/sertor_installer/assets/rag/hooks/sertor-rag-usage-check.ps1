<#
.SYNOPSIS
  Sertor RAG usage check — non-blocking PreToolUse hook (Principle XI, host-facing).

.DESCRIPTION
  Detects direct use of the `sertor_core` library outside the supported vehicles (CLI / MCP) and
  outside tests, and emits a NON-BLOCKING warning reminding the agent to use `sertor-rag` (CLI) or
  the MCP tools instead.

  Mechanism (Claude Code PreToolUse): the hook input (JSON) arrives on stdin. We read the tool
  input (e.g. the shell command for Bash, or file content for Write/Edit), and if it contains
  `import sertor_core` / `from sertor_core` AND the context is not a test path, we warn on stderr.

  Default severity = `warn` → **exit 0 ALWAYS** (never blocks). Parse error / unknown context →
  FAIL-OPEN (exit 0, no signal). The hook's absence must not break anything (Principle X).

  FEAT-011: on Copilot the `preToolUse` event is FAIL-CLOSED (a non-zero exit / a `decision:"deny"`
  signal would BLOCK the tool call). This hook is a non-blocking reminder, so it MUST exit 0 in
  every case (even on a parse error) and emit NO stdout payload Copilot could read as a `deny`
  decision — the warning goes ONLY to stderr. `-Assistant` is accepted for wiring symmetry; the
  fail-open contract (exit 0, stderr-only) is already identical for both assistants.
#>
[CmdletBinding()]
param([ValidateSet('claude', 'copilot')][string]$Assistant = 'claude')

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

try {
    # --- hook input (JSON on stdin) ---
    $raw = ''
    try { $raw = [Console]::In.ReadToEnd() } catch {}
    if (-not $raw -or -not $raw.Trim()) { exit 0 }   # no input → fail-open

    $hook = $null
    try { $hook = $raw | ConvertFrom-Json } catch { exit 0 }   # parse error → fail-open
    if (-not $hook) { exit 0 }

    # --- collect candidate text + path from the tool input (best-effort, tool-agnostic) ---
    $toolInput = $hook.tool_input
    if (-not $toolInput) { exit 0 }   # unknown context → fail-open

    $text = ''
    $path = ''
    foreach ($field in @('command', 'content', 'new_string', 'new_str')) {
        if ($toolInput.PSObject.Properties.Name -contains $field -and $toolInput.$field) {
            $text += "`n" + [string]$toolInput.$field
        }
    }
    foreach ($field in @('file_path', 'path', 'notebook_path')) {
        if ($toolInput.PSObject.Properties.Name -contains $field -and $toolInput.$field) {
            $path = [string]$toolInput.$field
        }
    }
    if (-not $text -and -not $path) { exit 0 }   # nothing to inspect → fail-open

    # --- detection: direct import of the library ---
    $usesCore = $text -match 'import\s+sertor_core' -or $text -match 'from\s+sertor_core'
    if (-not $usesCore) { exit 0 }

    # --- exclusion: test paths/content are legitimate (Principle I/XI) ---
    $haystack = ($path + "`n" + $text)
    if ($haystack -match '(?i)\btests?\b') { exit 0 }

    # --- warn (non-blocking): default severity = warn, exit 0 ---
    $msg = 'Sertor RAG: direct use of `sertor_core` detected outside the vehicles/tests. ' +
           'Use the `sertor-rag` CLI or the MCP tools instead of importing the library (see CLAUDE.md, SERTOR:RAG-USAGE).'
    [Console]::Error.WriteLine($msg)
    exit 0
} catch {
    exit 0   # any failure → fail-open, non-fatal
}
