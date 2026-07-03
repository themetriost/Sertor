#!/usr/bin/env pwsh
# Materialize the SpecKit machinery into the Sertor dogfood — as a faithful Sertor client (E10-FEAT-027).
#
# WHY. A project that installs Sertor gets the SpecKit machinery from the install path
# (`sertor-flow install --assistant claude` -> `specify init`, feature 045). The dogfood must obtain it
# THE SAME WAY, so the workspace exercises the real client path instead of diverging (audit A-05). The
# machinery is regenerable and git-ignored (like `.venv`): this script is the setup step that produces it.
#
# HOW (safe by construction). `specify init --force` at the repo root clobbers the customized
# `plan-template.md` (verified empirically); the constitution is create-if-absent and survives, but we do
# not rely on that — we run init in an ISOLATED temp dir and copy back ONLY the regenerable machinery, so
# ALL Sertor-authored artifacts (constitution.md, plan-template.md, feature.json) are never touched, and
# re-checked afterwards (fail loud if they changed). UTF-8 is forced (spec-kit's rich banner aborts on cp1252).
#
# Idempotent: re-running replaces the regenerable machinery and leaves the Sertor-authored artifacts intact.
param([switch]$Quiet)
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..' '..')).Path

# Pinned spec-kit version — SINGLE SOURCE (Principle VIII): read the literal from the authoritative
# profile, never duplicate it here.
$ProfilePy = Join-Path $RepoRoot 'packages/sertor-flow/src/sertor_flow/profile.py'
$verMatch = Select-String -Path $ProfilePy -Pattern 'SPECKIT_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
if (-not $verMatch) { throw "SPECKIT_VERSION not found in $ProfilePy (single-source read failed)." }
$Version = $verMatch.Matches[0].Groups[1].Value

# Sertor-authored artifacts that MUST stay byte-identical (never copied over; verified after).
$Protected = @(
    '.specify/memory/constitution.md',
    '.specify/templates/plan-template.md',
    '.specify/feature.json'
)
function Get-Sha([string]$rel) {
    $fp = Join-Path $RepoRoot $rel
    if (Test-Path $fp) { return (Get-FileHash $fp -Algorithm SHA256).Hash } else { return $null }
}
$before = @{}; foreach ($p in $Protected) { $before[$p] = Get-Sha $p }

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("sertor-speckit-" + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$prevUtf8 = $env:PYTHONUTF8; $prevIoEnc = $env:PYTHONIOENCODING
try {
    Push-Location $tmp
    try {
        # Force UTF-8 so spec-kit's rich banner does not abort on a legacy cp1252 console.
        $env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'
        & uvx --from "git+https://github.com/github/spec-kit.git@v$Version" `
            specify init . --here --ai claude --script ps --no-git --force --ignore-agent-tools
        if ($LASTEXITCODE -ne 0) { throw "specify init failed (exit $LASTEXITCODE)." }
    }
    finally { Pop-Location }

    # Copy ONLY regenerable machinery back into the repo (never the protected artifacts).
    # 1) native speckit-* skills
    Get-ChildItem (Join-Path $tmp '.claude/skills') -Directory -Filter 'speckit-*' | ForEach-Object {
        $dest = Join-Path $RepoRoot ".claude/skills/$($_.Name)"
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item $_.FullName $dest -Recurse
    }
    # 2) whole regenerable subtrees
    foreach ($d in @('.specify/scripts', '.specify/workflows', '.specify/integrations')) {
        $src = Join-Path $tmp $d
        if (Test-Path $src) {
            $dest = Join-Path $RepoRoot $d
            if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
            Copy-Item $src $dest -Recurse
        }
    }
    # 3) loose regenerable files
    foreach ($f in @('.specify/init-options.json', '.specify/integration.json')) {
        $src = Join-Path $tmp $f
        if (Test-Path $src) { Copy-Item $src (Join-Path $RepoRoot $f) -Force }
    }
    # 4) non-custom templates (plan-template.md is Sertor-authored -> excluded)
    foreach ($t in @('checklist-template.md', 'constitution-template.md', 'spec-template.md', 'tasks-template.md')) {
        $src = Join-Path $tmp ".specify/templates/$t"
        if (Test-Path $src) { Copy-Item $src (Join-Path $RepoRoot ".specify/templates/$t") -Force }
    }
}
finally {
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    $env:PYTHONUTF8 = $prevUtf8; $env:PYTHONIOENCODING = $prevIoEnc
}

# Fail loud if any Sertor-authored artifact changed (they must be byte-identical).
$violations = @()
foreach ($p in $Protected) { if ($before[$p] -ne (Get-Sha $p)) { $violations += $p } }
if ($violations.Count -gt 0) {
    throw "Sertor-authored artifact(s) changed during materialization: $($violations -join ', '). Aborting."
}

if (-not $Quiet) {
    Write-Host "SpecKit machinery materialized (spec-kit v$Version) into the dogfood."
    Write-Host "Regenerable and git-ignored; Sertor-authored artifacts unchanged."
}
