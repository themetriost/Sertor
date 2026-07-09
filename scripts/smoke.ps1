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
    [string]$Capability = "rag"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoUrl       = "https://github.com/themetriost/Sertor"
$SertorSource  = "git+$RepoUrl@$Ref#subdirectory=packages/sertor"
$FlowSource    = "git+$RepoUrl@$Ref#subdirectory=packages/sertor-flow"
$IsCopilot     = ($Assistant -eq "copilot-cli")

function Fail([string]$msg) {
    Write-Host "SMOKE_FAIL: $msg" -ForegroundColor Red
    exit 1
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

try {
    if ($createdHost) { New-SyntheticHost }

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
