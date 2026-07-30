<#
.SYNOPSIS
  End-to-end smoke test of a Sertor capability on a host, against the real distribution (git+url@master).

.DESCRIPTION
  Installs a Sertor capability into a host directory exactly as a third-party project would
  (`uvx --from git+url#subdirectory=packages/<pkg> <verb> ...`) for a chosen assistant, then asserts
  the deposited artifacts (and, for `rag`, drives the runtime CLI end-to-end: index -> doctor ->
  search). It catches integration bugs the offline test-suite cannot (CLI discoverability, cwd/index
  anchoring, per-assistant asset routing), because it drives the real installed entry-points from a
  clean host, not the in-repo source.

  MATRIX: {claude, copilot-cli} x {rag, wiki, flow}.
    * rag   — `sertor install rag`   : .sertor/ + .mcp.json + UX assets, then index/doctor/search.
    * wiki  — `sertor install wiki`  : wiki-author skill, wiki-curator agent, hooks, wiki.config.toml,
              wiki/ scaffold, the SERTOR:WIKI-RITUAL block (deposit-only, no runtime).
    * flow  — `sertor-flow install`  : SpecKit (via `specify init`, NETWORK), constitution starter,
              requirements/configuration-manager surfaces, the SERTOR:SDLC-RITUAL block (deposit-only).

  ISOLATION (no "Sertor on Sertor"): the smoke runs in a host directory OUTSIDE the Sertor checkout
  and with an environment scrubbed of inherited SERTOR_* variables, and it launches `uvx` with
  cwd = the host dir plus UV_NO_WORKSPACE=1 so `uv` cannot discover the local workspace. For `rag`
  this also guarantees `sertor-core` is BUILT FROM GIT (asserted against .sertor/uv.lock). `wiki`/
  `flow` do not create `.sertor`, so their isolation is host-outside-the-checkout + install-from-git.

  FIXTURE vs REAL TARGET: by DEFAULT (no -Target) the smoke creates a NEUTRAL synthetic project
  (README.md + src/app.py + src/utils.ts — a generic project, never Sertor files) in a temp dir and
  cleans it up. With -Target the smoke runs on THAT existing repo (and does NOT delete it). -Target
  is used by CI for `rag` (the real C#/.NET repo `themetriost/PgnToFen`); `wiki`/`flow` use the
  synthetic fixture.

  Provider (rag) = `hash` (zero-credentials, zero-download, deterministic): the install writes
  SERTOR_EMBED_PROVIDER=glove (which would download ~822 MB) into .sertor/.env, so the script
  rewrites that line to `hash` before any runtime command. `--no-rerank --no-graph` keep the
  isolated venv slim (no torch/networkx).

  On success the script prints a single machine-checkable marker line:
      SMOKE_OK assistant=<a> capability=<c> ...<capability fields>...
  and exits 0. On any failed assertion it prints `SMOKE_FAIL: <reason>` and exits non-zero.

.PARAMETER Ref
  Git ref to install from (default: master — the real distribution channel).

.PARAMETER Target
  Existing repo to run against. When omitted a neutral synthetic project is created in a temp dir.

.PARAMETER Assistant
  Target assistant: claude (default) | copilot-cli.

.PARAMETER Capability
  Capability to smoke: rag (default) | wiki | flow.
#>
[CmdletBinding()]
param(
    [string]$Ref = "master",
    [string]$Target = "",
    [ValidateSet("claude", "copilot-cli")]
    [string]$Assistant = "claude",
    [ValidateSet("rag", "wiki", "flow")]
    [string]$Capability = "rag",
    # E15-FEAT-012: ref the host STARTS from. Empty = install-only (behaviour unchanged).
    # Set = install that release, then `upgrade` to -Ref, then assert the outcomes on the host.
    [string]$FromRef = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoUrl        = "https://github.com/themetriost/Sertor"
$SertorSource   = "git+$RepoUrl@$Ref#subdirectory=packages/sertor"
$FlowSource     = "git+$RepoUrl@$Ref#subdirectory=packages/sertor-flow"
$IsUpgrade      = -not [string]::IsNullOrWhiteSpace($FromRef)
$FromSertorSrc  = if ($IsUpgrade) { "git+$RepoUrl@$FromRef#subdirectory=packages/sertor" } else { "" }
$FromFlowSrc    = if ($IsUpgrade) { "git+$RepoUrl@$FromRef#subdirectory=packages/sertor-flow" } else { "" }
$IsCopilot      = ($Assistant -eq "copilot-cli")
$script:UpgradeOut = ""   # the upgrade report, read by the no-stale-divergence outcome

function Fail([string]$msg) {
    Write-Host "SMOKE_FAIL: $msg" -ForegroundColor Red
    exit 1
}

# An environment impediment is NOT a product defect, and collapsing the two teaches people to ignore
# the gate — the exact dynamic that made v0.3.3 necessary (a guard that cries wolf stops being read).
# Distinct marker AND distinct exit code so a consumer can tell them apart without parsing prose.
function Fail-Env([string]$msg) {
    Write-Host "SMOKE_ENV: $msg" -ForegroundColor Yellow
    exit 2
}

# Every asserted outcome goes through here, so a failure NAMES the outcome and the context instead of
# leaving the reader to reproduce the run (FR-008). The outcome list lives in ONE place: see
# `Assert-UpgradeOutcomes`.
function Assert-Outcome([string]$outcome, [bool]$ok, [string]$detail) {
    if ($ok) {
        Write-Host "[upgrade] OK   $outcome"
        return
    }
    Fail ("upgrade outcome '$outcome' diverged — $detail " +
          "[assistant=$Assistant capability=$Capability from=$FromRef to=$Ref]")
}

function Require-Tool([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Fail "required tool not found in PATH: $name"
    }
}

function Assert-Path([string]$rel) {
    if (-not (Test-Path (Join-Path $HostDir $rel))) { Fail "expected artifact missing: $rel" }
}

function Assert-MarkerInFile([string]$rel, [string]$marker) {
    $p = Join-Path $HostDir $rel
    if (-not (Test-Path $p)) { Fail "instruction file missing: $rel" }
    if ((Get-Content $p -Raw) -notmatch [regex]::Escape($marker)) {
        Fail "marker '$marker' not found in $rel"
    }
}

Require-Tool "uvx"
Require-Tool "uv"

# --- Resolve the host: real target OR neutral synthetic fixture in system temp --------------------
$createdHost = $false
if ([string]::IsNullOrWhiteSpace($Target)) {
    # System temp is outside the Sertor checkout — required for isolation.
    $HostDir = Join-Path ([System.IO.Path]::GetTempPath()) ("sertor-smoke-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
    New-Item -ItemType Directory -Path $HostDir -Force | Out-Null
    $createdHost = $true
} else {
    if (-not (Test-Path $Target -PathType Container)) { Fail "target is not a directory: $Target" }
    $HostDir = (Resolve-Path $Target).Path
}
$HostDir = (Resolve-Path $HostDir).Path

# Guard: never run inside the Sertor checkout (would let uv resolve sertor-core from the workspace).
$repoCheckout = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($HostDir.StartsWith($repoCheckout, [StringComparison]::OrdinalIgnoreCase)) {
    Fail "host '$HostDir' is inside the Sertor checkout '$repoCheckout' — isolation requires a host OUTSIDE the checkout"
}

Write-Host "[smoke] assistant = $Assistant | capability = $Capability"
Write-Host "[smoke] host = $HostDir"

# Scrub inherited SERTOR_* (and UV workspace) vars for this process so the dogfood env of the
# developer machine does not leak into the host install/runtime. We set only what we need.
Get-ChildItem Env: | Where-Object { $_.Name -like "SERTOR_*" } | ForEach-Object {
    Remove-Item "Env:$($_.Name)" -ErrorAction SilentlyContinue
}
# Also drop an inherited active venv (e.g. CI's `uv sync` sets VIRTUAL_ENV=<checkout>\.venv); `uv run
# --project .sertor` would warn it is ignored. Unset it so the smoke env stays clean (parity with .sh).
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
$env:UV_NO_WORKSPACE = "1"   # prevent uv from discovering the local Sertor workspace

function New-SyntheticHost {
    # Neutral synthetic project (generic — never Sertor files). Used as host for all capabilities.
    $readme = @"
# Acme Widgets

A small sample project used to exercise the Sertor smoke test. It ships a documented helper function
and a TypeScript utility so the index has real code and documentation to retrieve.
"@
    Set-Content -Path (Join-Path $HostDir "README.md") -Value $readme -Encoding utf8

    New-Item -ItemType Directory -Path (Join-Path $HostDir "src") -Force | Out-Null
    $app = @"
def add(a: int, b: int) -> int:
    """Return the sum of two integers (sample function for the smoke test)."""
    return a + b


def greet(name: str) -> str:
    """Build a friendly greeting for the given name."""
    return f"Hello, {name}!"
"@
    Set-Content -Path (Join-Path $HostDir "src/app.py") -Value $app -Encoding utf8

    $utils = @"
// Format a label for display in the Acme Widgets UI.
export function formatLabel(text: string): string {
    return text.trim().toUpperCase();
}
"@
    Set-Content -Path (Join-Path $HostDir "src/utils.ts") -Value $utils -Encoding utf8
}

# =================================================================================================
# Capability: RAG — install (assets) + runtime (index -> doctor -> search)
# =================================================================================================
function Invoke-RagSmoke {
    Write-Host "[smoke] installing rag capability ($Assistant) ..."
    Push-Location $HostDir
    try {
        $installOut = & uvx --refresh --from $SertorSource sertor install rag --assistant $Assistant --backend local --no-rerank --no-graph --corpus smoke --target $HostDir 2>&1 | Out-String
    } finally {
        Pop-Location
    }
    Write-Host $installOut.TrimEnd()
    if ($LASTEXITCODE -ne 0) { Fail "install rag exited $LASTEXITCODE" }

    $sertorDir = Join-Path $HostDir ".sertor"
    if (-not (Test-Path $sertorDir)) { Fail ".sertor/ not deposited" }

    # Proof of isolation: the runtime lock must resolve sertor-core FROM GIT, never from the local
    # workspace path — otherwise the smoke would test the working tree, not the distribution.
    $lockFile = Join-Path $sertorDir "uv.lock"
    if (Test-Path $lockFile) {
        $lockText = Get-Content $lockFile -Raw
        if ($lockText -match 'name = "sertor-core"[\s\S]*?source = \{ git = "https://github.com/themetriost/Sertor') {
            Write-Host "[smoke] isolation OK (sertor-core resolved from git in .sertor/uv.lock)"
        } else {
            Fail "sertor-core is NOT resolved from git in .sertor/uv.lock (local-path leak — isolation broken)"
        }
    } else {
        Write-Host "[smoke] note: .sertor/uv.lock absent (--no-deps?); cannot prove git isolation"
    }
    Assert-Path ".mcp.json"
    # UX assets (guided-setup skill + concierge agent), routed per-assistant.
    if ($IsCopilot) {
        Assert-Path ".github/skills/guided-setup/SKILL.md"
        Assert-Path ".github/agents/concierge.agent.md"
    } else {
        Assert-Path ".claude/skills/guided-setup/SKILL.md"
        Assert-Path ".claude/agents/concierge.md"
    }
    Write-Host "[smoke] install OK (.sertor/, .mcp.json, UX assets present)"

    # Provider -> hash (zero-download, deterministic). The .env is loaded with override=True,
    # so editing the file is the robust way to force the provider for runtime commands.
    $envFile = Join-Path $sertorDir ".env"
    if (-not (Test-Path $envFile)) { Fail ".sertor/.env not found after install" }
    $envText = Get-Content -Path $envFile -Raw
    $envText = $envText -replace "(?m)^SERTOR_EMBED_PROVIDER=.*$", "SERTOR_EMBED_PROVIDER=hash"
    if ($envText -notmatch "(?m)^SERTOR_EMBED_PROVIDER=hash$") {
        $envText = $envText.TrimEnd() + "`nSERTOR_EMBED_PROVIDER=hash`n"
    }
    Set-Content -Path $envFile -Value $envText -Encoding utf8
    Write-Host "[smoke] provider forced to hash"

    Push-Location $HostDir
    try {
        # Index (the heart — catches the cwd/anchor bug) ----------------------------------------
        Write-Host "[smoke] indexing ..."
        $indexOut = & uv run --project .sertor sertor-rag index . 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { Write-Host $indexOut; Fail "index exited $LASTEXITCODE" }
        Write-Host $indexOut.TrimEnd()

        $m = [regex]::Match($indexOut, "documents=(\d+)")
        if (-not $m.Success) { Fail "index output has no documents=N marker" }
        $documents = [int]$m.Groups[1].Value
        if ($documents -le 0) { Fail "documents=$documents (expected > 0; cwd/anchor bug would give 0)" }
        Write-Host "[smoke] indexed documents=$documents"

        # Anchoring: index lives under .sertor/.index, NOT at host root --------------------------
        if (-not (Test-Path (Join-Path $sertorDir ".index"))) { Fail ".sertor/.index does not exist (index anchored wrong)" }
        if (Test-Path (Join-Path $HostDir ".index"))          { Fail "host-root .index exists (cwd/anchor regression)" }
        Write-Host "[smoke] anchoring OK (.sertor/.index present, root .index absent)"

        # Doctor --------------------------------------------------------------------------------
        #    Parse stdout only: the provider emits a 'lexical-only' warning to stderr that would
        #    otherwise pollute the JSON, so stderr is captured to a temp file (shown only on error).
        Write-Host "[smoke] running doctor ..."
        $doctorErr = New-TemporaryFile
        $doctorOut = (& uv run --project .sertor sertor-rag doctor --json 2>$doctorErr.FullName | Out-String)
        if ($LASTEXITCODE -ne 0) { Write-Host $doctorOut; Write-Host (Get-Content $doctorErr.FullName -Raw); Remove-Item $doctorErr.FullName -ErrorAction SilentlyContinue; Fail "doctor exited $LASTEXITCODE (a critical area failed)" }
        Remove-Item $doctorErr.FullName -ErrorAction SilentlyContinue
        $doctor = $doctorOut | ConvertFrom-Json
        $overall = $doctor.overall
        if ($overall -notin @("pass", "warn")) { Fail "doctor overall=$overall (expected pass|warn)" }
        $areaStatus = @{}
        foreach ($a in $doctor.areas) { $areaStatus[$a.name] = $a.status }
        if ($areaStatus["index"]    -ne "pass") { Fail "doctor index area=$($areaStatus['index']) (expected pass)" }
        if ($areaStatus["config"]   -ne "pass") { Fail "doctor config area=$($areaStatus['config']) (expected pass)" }
        if ($areaStatus["provider"] -ne "pass") { Fail "doctor provider area=$($areaStatus['provider']) (expected pass)" }
        Write-Host "[smoke] doctor OK (overall=$overall, index/config/provider=pass)"

        # Search --------------------------------------------------------------------------------
        #    Parse stdout only (same stderr-warning reason as doctor).
        Write-Host "[smoke] searching ..."
        $searchErr = New-TemporaryFile
        $searchOut = (& uv run --project .sertor sertor-rag search "greeting function" --json 2>$searchErr.FullName | Out-String)
        if ($LASTEXITCODE -ne 0) { Write-Host $searchOut; Write-Host (Get-Content $searchErr.FullName -Raw); Remove-Item $searchErr.FullName -ErrorAction SilentlyContinue; Fail "search exited $LASTEXITCODE" }
        Remove-Item $searchErr.FullName -ErrorAction SilentlyContinue
        # search --type both prints {"docs":[...],"code":[...]}; mono-type prints an array.
        $search = $searchOut | ConvertFrom-Json
        $results = @()
        if ($search.PSObject.Properties.Name -contains "docs" -or $search.PSObject.Properties.Name -contains "code") {
            if ($search.docs) { $results += $search.docs }
            if ($search.code) { $results += $search.code }
        } else {
            $results = @($search)
        }
        $resultCount = $results.Count
        if ($resultCount -le 0) { Fail "search returned no results" }
        Write-Host "[smoke] search OK (results=$resultCount)"
    }
    finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "SMOKE_OK assistant=$Assistant capability=rag doctor=$overall documents=$documents results=$resultCount" -ForegroundColor Green
}

# =================================================================================================
# Capability: WIKI — install (deposit-only, no runtime; no .sertor/, no sertor-core install)
# =================================================================================================
function Invoke-WikiSmoke {
    Write-Host "[smoke] installing wiki capability ($Assistant) ..."
    Push-Location $HostDir
    try {
        $installOut = & uvx --refresh --from $SertorSource sertor install wiki --assistant $Assistant --target $HostDir 2>&1 | Out-String
    } finally {
        Pop-Location
    }
    Write-Host $installOut.TrimEnd()
    if ($LASTEXITCODE -ne 0) { Fail "install wiki exited $LASTEXITCODE" }

    # Wiki scaffold + config (assistant-agnostic).
    Assert-Path "wiki/wiki.config.toml"
    Assert-Path "wiki/index.md"
    # Per-assistant asset routing.
    if ($IsCopilot) {
        Assert-Path ".github/skills/wiki-author/SKILL.md"
        Assert-Path ".github/agents/wiki-curator.agent.md"
        Assert-Path ".github/hooks/wiki-pending-check.py"
        Assert-Path ".github/hooks/_hooklib.py"
        Assert-Path ".github/hooks/sertor-hooks.json"
        Assert-MarkerInFile ".github/copilot-instructions.md" "SERTOR:WIKI-RITUAL"
    } else {
        Assert-Path ".claude/skills/wiki-author/SKILL.md"
        Assert-Path ".claude/commands/wiki.md"
        Assert-Path ".claude/agents/wiki-curator.md"
        Assert-Path ".claude/hooks/wiki-pending-check.py"
        Assert-Path ".claude/hooks/_hooklib.py"
        Assert-Path ".claude/settings.json"
        Assert-MarkerInFile "CLAUDE.md" "SERTOR:WIKI-RITUAL"
    }
    Write-Host "[smoke] wiki deposit OK (skill, agent, hooks, config, scaffold, ritual block)"

    Write-Host ""
    Write-Host "SMOKE_OK assistant=$Assistant capability=wiki deposit=ok" -ForegroundColor Green
}

# =================================================================================================
# Capability: FLOW (governance) — install (deposit-only; launches `specify init`, NETWORK)
# =================================================================================================
function Invoke-FlowSmoke {
    Write-Host "[smoke] installing governance (flow) capability ($Assistant) ..."
    Push-Location $HostDir
    try {
        $installOut = & uvx --refresh --from $FlowSource sertor-flow install --assistant $Assistant --target $HostDir 2>&1 | Out-String
    } finally {
        Pop-Location
    }
    Write-Host $installOut.TrimEnd()
    if ($LASTEXITCODE -ne 0) { Fail "sertor-flow install exited $LASTEXITCODE" }

    # SpecKit machinery (from `specify init`) — assistant-agnostic `.specify/` + constitution starter.
    Assert-Path ".specify/templates/plan-template.md"
    Assert-Path ".specify/memory/constitution.md"
    # Per-assistant SpecKit surface + Sertor-authored surfaces + SDLC block.
    if ($IsCopilot) {
        Assert-Path ".github/prompts/speckit.specify.prompt.md"
        Assert-Path ".github/agents/requirements-analyst.agent.md"
        Assert-Path ".github/agents/configuration-manager.agent.md"
        Assert-Path ".github/agents/requirements.agent.md"
        Assert-MarkerInFile ".github/copilot-instructions.md" "SERTOR:SDLC-RITUAL"
    } else {
        Assert-Path ".claude/skills/speckit-specify/SKILL.md"
        Assert-Path ".claude/agents/requirements-analyst.md"
        Assert-Path ".claude/agents/configuration-manager.md"
        Assert-Path ".claude/skills/requirements/SKILL.md"
        Assert-MarkerInFile "CLAUDE.md" "SERTOR:SDLC-RITUAL"
    }
    Write-Host "[smoke] governance deposit OK (speckit, constitution, authored surfaces, SDLC block)"

    Write-Host ""
    Write-Host "SMOKE_OK assistant=$Assistant capability=flow deposit=ok" -ForegroundColor Green
}

# =================================================================================================
# E15-FEAT-012 — upgrade flow: install the PREVIOUS release, upgrade, assert outcomes on the HOST
# =================================================================================================

# THE outcome list (FR-015). Every entry exists because a defect really happened: adding one after a
# new field report must be one more line here, never a restructuring — otherwise the list ages and the
# guard only protects the past.
function Assert-UpgradeOutcomes([string]$cap) {
    $sertorDir = Join-Path $HostDir ".sertor"

    # 1. The pin moved. Defect: the recorded source stayed at the old version after `upgrade` —
    #    reported by THREE independent nodes, and the reason v0.3.1 existed.
    $pinFile = Join-Path $sertorDir "pyproject.toml"
    if (Test-Path $pinFile) {
        $pin = Get-Content $pinFile -Raw
        Assert-Outcome "pin-moved" (-not ($pin -match [regex]::Escape($FromRef))) `
            "the runtime source still references '$FromRef' in .sertor/pyproject.toml"
    } else {
        Write-Host "[upgrade] n/a  pin-moved (capability '$cap' creates no runtime)"
    }

    # 2. Exactly ONE session automation, and it is the current one. Defect: identity by command string
    #    made a re-wire look new, so the hook was duplicated (E10-FEAT-032) with the broken copy live.
    $settingsRel = if ($IsCopilot) { ".github/hooks/sertor-hooks.json" } else { ".claude/settings.json" }
    $settings = Join-Path $HostDir $settingsRel
    if (Test-Path $settings) {
        $raw = Get-Content $settings -Raw
        foreach ($stem in @("rag-freshness", "wiki-guard", "memory-capture")) {
            $count = ([regex]::Matches($raw, [regex]::Escape($stem))).Count
            if ($count -gt 0) {
                Assert-Outcome "hook-single:$stem" ($count -le 2) `
                    "hook '$stem' appears $count times in $settingsRel (duplicated wiring)"
            }
        }
    }

    # 3. Host-owned configuration preserved. Defect: fixing E2-FEAT-022 nearly zeroed the corpus on
    #    every upgrade — caught by a MANUAL run, not by the tests. The upgrade rewrites OUR invocation
    #    and preserves THEIR configuration.
    $envFile = Join-Path $sertorDir ".env"
    if (Test-Path $envFile) {
        $envRaw = Get-Content $envFile -Raw
        Assert-Outcome "host-config-preserved" ($envRaw -match "SERTOR_CORPUS\s*=\s*smoke") `
            "SERTOR_CORPUS=smoke is gone from .sertor/.env after the upgrade"
    }

    # 4. The recorded invocation has the current shape. Defect: `--directory` kept because it "was
    #    already there" — the RAG resolved the index in the wrong folder for a month.
    $mcp = Join-Path $HostDir ".mcp.json"
    if (Test-Path $mcp) {
        $mcpRaw = Get-Content $mcp -Raw
        Assert-Outcome "mcp-invocation-shape" (-not ($mcpRaw -match "--directory")) `
            "the MCP registration still uses --directory instead of --project"
    }

    # 5. Nothing was left stale. Defect: `install` is non-destructive and leaves a divergent file in
    #    place (PRESENT_DIVERGENT) — correct for install, WRONG for upgrade, whose contract is to
    #    replace our own artefacts. It blocked hook fixes that had already been released (E2-FEAT-023
    #    family). The signal is in the upgrade's own report, so it costs nothing to read.
    Assert-Outcome "no-stale-divergence" (-not ($script:UpgradeOut -match "PRESENT_DIVERGENT")) `
        "the upgrade left an artefact divergent instead of replacing it (PRESENT_DIVERGENT in report)"

    # 6. The version the host reports as INSTALLED is DERIVED from the runtime, not read from the
    #    install-time stamp. Defect E2-FEAT-021 — already FIXED, which is precisely why the assertion
    #    is worth its lines: being fixed and ARRIVING at a host that upgrades are different facts, and
    #    only the second is what the host experiences. The stamp records the version of the *installer
    #    that ran*; a host whose runtime was current but whose stamp lagged reported a permanent false
    #    `behind`, with a suggested remedy that was not even executable there.
    #
    #    Discriminating BY CONSTRUCTION, not by luck: we plant a stamp that LAGS the runtime — the
    #    field condition itself. Reading the stamp yields `behind`; deriving from the lock yields
    #    up-to-date. Without the planted stamp the two sources agree on this fixture and the assertion
    #    would pass while measuring nothing. `latest` is seeded into the cache so the check stays
    #    offline: the network is not what is under test here.
    $vcHook = if ($IsCopilot) { Join-Path $HostDir ".github/hooks/version-check.py" }
              else            { Join-Path $HostDir ".claude/hooks/version-check.py" }
    if ((Test-Path $sertorDir) -and (Test-Path $vcHook)) {
        $lockPath = Join-Path $sertorDir "uv.lock"
        $runtimeVer = ""
        if (Test-Path $lockPath) {
            $mv = [regex]::Match((Get-Content $lockPath -Raw),
                '(?s)name\s*=\s*"sertor-core".*?version\s*=\s*"([^"]+)"')
            if ($mv.Success) { $runtimeVer = $mv.Groups[1].Value }
        }
        # Fail, not skip: an unreadable lock on a host that just upgraded is the very state this
        # outcome exists to observe. A silent `n/a` here would be the gate disabling itself.
        if (-not $runtimeVer) { Fail "version-derived: no sertor-core version in .sertor/uv.lock" }

        Set-Content -Path (Join-Path $sertorDir ".sertor-version") -Value "0.0.1" -Encoding utf8
        $seed = [ordered]@{
            schema     = "version.check/1"
            verdict    = "unknown"
            installed  = ""
            latest     = $runtimeVer
            checked_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        } | ConvertTo-Json
        Set-Content -Path (Join-Path $sertorDir ".version-check.json") -Value $seed -Encoding utf8

        # CLAUDE_PROJECT_DIR is pinned to the throwaway host ON PURPOSE: the hook honours it over the
        # event's cwd, so a run started from inside a real session would otherwise write its state
        # into THAT project instead of the fixture.
        $prevProjectDir = $env:CLAUDE_PROJECT_DIR
        $env:CLAUDE_PROJECT_DIR = $HostDir
        try {
            '{}' | & uv run --no-project python $vcHook 2>&1 | Out-String | Write-Host
        } finally {
            $env:CLAUDE_PROJECT_DIR = $prevProjectDir
        }

        $vc = Get-Content (Join-Path $sertorDir ".version-check.json") -Raw | ConvertFrom-Json
        Assert-Outcome "version-derived-from-runtime" `
            (($vc.installed_source -eq "runtime-lock") -and ($vc.verdict -ne "behind")) `
            ("the host reports installed='$($vc.installed)' source='$($vc.installed_source)' " +
             "verdict='$($vc.verdict)' while the runtime resolves sertor-core $runtimeVer — " +
             "the planted stale stamp won over the lock")
    } else {
        Write-Host "[upgrade] n/a  version-derived-from-runtime (capability '$cap' deposits no version-check hook)"
    }

    # 7. Health is green — the catch-all for what the six above do not name.
    if (Test-Path $sertorDir) {
        $doctor = & uv run --project $sertorDir sertor-rag doctor 2>&1 | Out-String
        Assert-Outcome "health-green" ($LASTEXITCODE -eq 0) `
            "doctor exited $LASTEXITCODE after the upgrade: $($doctor.Trim())"
    }
}

function Invoke-UpgradeFlow([string]$cap) {
    $fromSrc = if ($cap -eq "flow") { $FromFlowSrc } else { $FromSertorSrc }
    $toSrc   = if ($cap -eq "flow") { $FlowSource }  else { $SertorSource }
    $exe     = if ($cap -eq "flow") { "sertor-flow" } else { "sertor" }

    Write-Host "[upgrade] installing PREVIOUS release $FromRef ($cap / $Assistant) ..."
    Push-Location $HostDir
    try {
        if ($cap -eq "rag") {
            & uvx --refresh --from $fromSrc $exe install $cap --assistant $Assistant `
                --backend local --no-rerank --no-graph --corpus smoke --target $HostDir 2>&1 | Out-String | Write-Host
        } else {
            & uvx --refresh --from $fromSrc $exe install $cap --assistant $Assistant --target $HostDir 2>&1 | Out-String | Write-Host
        }
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) {
        # Could not even reach the starting line: the previous release is not installable here.
        Fail-Env "install of previous release '$FromRef' exited $LASTEXITCODE (ref reachable? network?)"
    }

    # Same fixture policy the install flow already applies: the install writes
    # SERTOR_EMBED_PROVIDER=glove, whose vectors are a ~822 MB download the runner must not make. It
    # is a FIXTURE choice, not a product one — and the product question it could hide was checked:
    # `host-config-preserved` passes, so the upgrade preserves .env; the provider stays `glove`
    # because that is the install default, not because the upgrade touched it.
    $envFile = Join-Path $HostDir ".sertor/.env"
    if (Test-Path $envFile) {
        $envRaw = Get-Content $envFile -Raw
        if ($envRaw -match "(?m)^SERTOR_EMBED_PROVIDER=") {
            ($envRaw -replace "(?m)^SERTOR_EMBED_PROVIDER=.*", "SERTOR_EMBED_PROVIDER=hash") |
                Set-Content -Path $envFile -Encoding utf8
        } else {
            Add-Content -Path $envFile -Value "`nSERTOR_EMBED_PROVIDER=hash" -Encoding utf8
        }
        Write-Host "[upgrade] provider forced to hash (fixture: no 822 MB download on the runner)"
    }

    # A host that upgrades HAS an index, and it was built by the OLD version. Skipping this step is
    # what made the first run report `health-green` as diverged: `doctor` said `index_absent`, which
    # was true of the fixture and of no real host. It is not only fixture, though — indexing HERE,
    # with the previous release, is what turns `health-green` into a question the install-only smoke
    # cannot ask at all: does the new version still READ the index the previous one wrote? A manifest
    # that stopped being readable would otherwise cost the host its index in silence.
    if ($cap -eq "rag" -and (Test-Path (Join-Path $HostDir ".sertor"))) {
        Write-Host "[upgrade] indexing with the PREVIOUS release ..."
        Push-Location $HostDir
        try {
            $idxOut = & uv run --project .sertor sertor-rag index . 2>&1 | Out-String
        } finally {
            Pop-Location
        }
        # Fail-Env, not Fail: a previous release that cannot index is a starting line we never
        # reached — it says nothing about $Ref, which is the thing under test.
        if ($LASTEXITCODE -ne 0) {
            Write-Host $idxOut
            Fail-Env "index with the previous release '$FromRef' exited $LASTEXITCODE"
        }
        Write-Host $idxOut.TrimEnd()
    }

    Write-Host "[upgrade] upgrading $FromRef -> $Ref ..."
    Push-Location $HostDir
    try {
        $script:UpgradeOut = & uvx --refresh --from $toSrc $exe upgrade $cap --assistant $Assistant --target $HostDir 2>&1 | Out-String
        Write-Host $script:UpgradeOut.TrimEnd()
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) { Fail "upgrade $cap exited $LASTEXITCODE" }

    # Exit code 0 is NOT an outcome: `upgrade` used to succeed while moving nothing (SC-004).
    Assert-UpgradeOutcomes $cap

    Write-Host ""
    Write-Host "SMOKE_OK assistant=$Assistant capability=$cap upgrade=$FromRef->$Ref" -ForegroundColor Green
}

try {
    if ($createdHost) { New-SyntheticHost }

    if ($IsUpgrade) {
        Invoke-UpgradeFlow $Capability
        exit 0
    }

    switch ($Capability) {
        "rag"  { Invoke-RagSmoke }
        "wiki" { Invoke-WikiSmoke }
        "flow" { Invoke-FlowSmoke }
    }
    exit 0
}
finally {
    if ($createdHost -and (Test-Path $HostDir)) {
        Write-Host "[smoke] cleaning up $HostDir"
        Remove-Item -Path $HostDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
