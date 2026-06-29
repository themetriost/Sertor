<#
.SYNOPSIS
  Deterministic end-of-session version-update check — a thin HTTP+file wrapper.

.DESCRIPTION
  Host-specific trigger (SessionEnd) that checks whether the installed Sertor is older than the
  latest published version (E2-FEAT-013, FR-001..018). The twin of `rag-freshness.ps1`, but it
  consumes NO CLI vehicle and NO LLM (Principio XI / D<->N): it does a simple HTTP GET of the
  remote `/VERSION`, reads the install-time stamp, compares them, and persists the verdict. It
  NEVER imports `sertor_core` and NEVER runs Python (FR-014): the installed version comes from the
  stamp `.sertor/.sertor-version` written by the installer, not from `importlib.metadata` at runtime.

  Orchestration (data-model §3a, research D-5):
    1. read `.sertor/.version-check.json`; if `checked_at` is within ~24h and
       $env:SERTOR_VERSION_CHECK_FORCE is not set -> REUSE the result (no GET, FR-006) and
       re-confirm the verdict vs the CURRENT stamp (handles a mid-day upgrade, INV-4/R-5/FR-013).
    2. otherwise: GET $env:SERTOR_VERSION_CHECK_URL (default raw on `master`, research D-2),
       short timeout (~5s), `.Trim()` the body -> $latest.
    3. read the stamp `.sertor/.sertor-version` -> $installed; read `.sertor/.sertor-flow-version`
       if present -> the `dimensions` map (FR-011/012, Could).
    4. compare semantically by numeric segments + lexical fallback (research D-4): split on `.`,
       compare segments as integers; non-numeric segment -> lexical fallback. Verdict:
       installed < latest -> `behind`; == -> `up-to-date`; > -> `ahead`; parse failure -> `unknown`
       (FR-010, INV-2 — never a false `behind`).
    5. write `.sertor/.version-check.json` (schema `version.check/1`, contract version-check-state.md).
    6. exit 0 ALWAYS; GET/parse failure -> verdict `unknown`, no error (FR-009).

  Discipline (same as rag-freshness.ps1 / memory-capture.ps1):
    - Non-fatal: every step runs inside try/catch; the script ALWAYS exits 0 (FR-009, R-2).
    - Non-blocking: the host timeout in settings is the upper cap (RNF-2).
    - No LLM, no `sertor_core`, no Python in the hot path (FR-014, Principio XI).
    - Host-agnostic (RNF-3): no path hardcoded to a specific project; URL overridable via env.
    - Privacy (FR-015/INV-3): the only egress is the GET of the public `/VERSION`; no project
      content/secret is transmitted, and the state file holds only public version numbers.

  The hook input (JSON) arrives on stdin; the script tolerates its absence (manual invocation),
  falling back to '.' as the project root.

.NOTES
  Manual verification (quickstart):
    .\.claude\hooks\version-check.ps1; $LASTEXITCODE   # 0 (always); writes .sertor/.version-check.json
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

# --- default remote /VERSION (raw on master), overridable per-host via env (research D-2) ---
$DefaultUrl = 'https://raw.githubusercontent.com/themetriost/Sertor/master/VERSION'

# --- semantic version compare by numeric segments + lexical fallback (research D-4) ---
# Returns -1 if a<b, 0 if a==b, 1 if a>b. Empty/unparsable input -> $null (verdict `unknown`).
function Compare-Version([string]$a, [string]$b) {
    if (-not $a -or -not $b) { return $null }
    $sa = $a.Trim() -split '\.'
    $sb = $b.Trim() -split '\.'
    $n = [Math]::Max($sa.Length, $sb.Length)
    for ($i = 0; $i -lt $n; $i++) {
        $pa = if ($i -lt $sa.Length) { $sa[$i] } else { '0' }
        $pb = if ($i -lt $sb.Length) { $sb[$i] } else { '0' }
        $ia = 0; $ib = 0
        if ([int]::TryParse($pa, [ref]$ia) -and [int]::TryParse($pb, [ref]$ib)) {
            if ($ia -lt $ib) { return -1 }
            if ($ia -gt $ib) { return 1 }
        } else {
            # non-numeric segment -> deterministic lexical fallback for this segment
            $c = [string]::CompareOrdinal($pa, $pb)
            if ($c -lt 0) { return -1 }
            if ($c -gt 0) { return 1 }
        }
    }
    return 0
}

# --- project root: harness env, then hook cwd, then current directory ---
$raw = ''
try { $raw = [Console]::In.ReadToEnd() } catch {}
$hook = $null
if ($raw -and $raw.Trim()) { try { $hook = $raw | ConvertFrom-Json } catch { $hook = $null } }
$root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR }
        elseif ($hook -and $hook.cwd) { $hook.cwd }
        else { '.' }

try {
    $sertorDir = Join-Path $root '.sertor'
    $statePath = Join-Path $sertorDir '.version-check.json'

    # --- read the installed stamp(s) (no Python — FR-014/D-3) ---
    $installed = ''
    $stampPath = Join-Path $sertorDir '.sertor-version'
    if (Test-Path $stampPath) {
        try { $installed = (Get-Content -Path $stampPath -Raw -Encoding UTF8).Trim() } catch { $installed = '' }
    }
    $dimensions = [ordered]@{}
    if ($installed) { $dimensions['sertor'] = $installed }
    $flowStampPath = Join-Path $sertorDir '.sertor-flow-version'
    if (Test-Path $flowStampPath) {
        try {
            $flowVer = (Get-Content -Path $flowStampPath -Raw -Encoding UTF8).Trim()
            if ($flowVer) { $dimensions['sertor-flow'] = $flowVer }
        } catch {}
    }

    # --- decide whether the cache is fresh (~24h) and not forced (FR-006/008) ---
    $latest = ''
    $cacheFresh = $false
    if ((Test-Path $statePath) -and (-not $env:SERTOR_VERSION_CHECK_FORCE)) {
        try {
            $prev = Get-Content -Path $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($prev -and $prev.checked_at) {
                $checkedAt = [datetime]::Parse(
                    $prev.checked_at, $null,
                    [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor
                    [System.Globalization.DateTimeStyles]::AssumeUniversal
                )
                $ageHours = ((Get-Date).ToUniversalTime() - $checkedAt).TotalHours
                if ($ageHours -ge 0 -and $ageHours -lt 24) {
                    $cacheFresh = $true
                    if ($prev.latest) { $latest = [string]$prev.latest }
                }
            }
        } catch { $cacheFresh = $false }
    }

    # --- fetch the remote /VERSION if cache stale/absent/forced (FR-002/008) ---
    if (-not $cacheFresh) {
        $url = if ($env:SERTOR_VERSION_CHECK_URL) { $env:SERTOR_VERSION_CHECK_URL } else { $DefaultUrl }
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
            $body = $resp.Content
            # `-UseBasicParsing` may yield Content as a byte[] in some hosts: decode to UTF-8 text.
            if ($body -is [byte[]]) { $body = [System.Text.Encoding]::UTF8.GetString($body) }
            $latest = ([string]$body).Trim()
        } catch {
            $latest = ''   # offline / GET failed -> inconclusive (FR-009), verdict `unknown`
        }
    }

    # --- compute the verdict (D-4); installed >= latest => no warning (FR-004) ---
    $verdict = 'unknown'
    if ($installed -and $latest) {
        $cmp = Compare-Version $installed $latest
        if ($null -eq $cmp) { $verdict = 'unknown' }
        elseif ($cmp -lt 0) { $verdict = 'behind' }
        elseif ($cmp -eq 0) { $verdict = 'up-to-date' }
        else { $verdict = 'ahead' }
    }

    # --- persist the state under .sertor/ (INV-1: written canonically, never deleted) ---
    if (-not (Test-Path $sertorDir)) { New-Item -ItemType Directory -Path $sertorDir -Force | Out-Null }
    $timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $state = [ordered]@{
        schema     = 'version.check/1'
        verdict    = $verdict
        installed  = $installed
        latest     = $latest
        checked_at = $timestamp
    }
    if ($dimensions.Count -gt 0) { $state['dimensions'] = $dimensions }
    ($state | ConvertTo-Json -Depth 6) | Set-Content -Path $statePath -Encoding UTF8
} catch {
    # E10-FEAT-019: catastrophic internal error — this also covers a BLIND read of our own runtime
    # state (`.version-check.json` / stamp corrupt that hides a problem, REQ-006). The verdict was
    # NOT persisted, so leave an inspectable breadcrumb (fixed string, no `$_` — R-3) then exit 0.
    Write-HookBreadcrumb -Root $root -Hook 'version-check' -Reason "version-check internal error"
}

exit 0   # ALWAYS — any failure must never break the session close (FR-009, R-2)
