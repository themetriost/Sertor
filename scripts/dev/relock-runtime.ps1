#!/usr/bin/env pwsh
# Re-lock the dogfood runtime `.sertor/` to `origin/master` HEAD (E15-FEAT-008).
#
# WHY. The dogfood runtime (`.sertor/`, feature F1) installs `sertor-core` from `git=<repo>` HEAD, but
# `.sertor/uv.lock` pins the resolved commit. After a merge on `master`, HEAD advances and the runtime
# stays nailed to the old commit -> the RAG/hooks would serve STALE code relative to real `master`. This
# step re-aligns it mechanically (D<->N boundary: the "how" is deterministic; the "when" is the main-flow's
# post-merge ritual judgment).
#
# DOGFOOD-ONLY. This lives in `scripts/dev/` and is NEVER bundled by any installer. Hosts pin a version and
# get the auto-updater (E2-FEAT-013); they do NOT track HEAD. A guard test keeps this out of distributed
# assets / `rag-freshness.ps1`.
#
# CHECK-THEN-ACT. Cheap check first (compare the locked SHA vs remote HEAD); the costly `uv` re-sync runs
# ONLY when the runtime is behind. Fail-loud (Principio XII): missing `uv`/project or network failure exit
# non-zero with an actionable message, never leaving a partial runtime passed off as fresh.
#
# Usage:
#   ./scripts/dev/relock-runtime.ps1            # check-then-act
#   ./scripts/dev/relock-runtime.ps1 -WhatIf    # report the action without performing the re-lock
#
# Exit codes: 0 = up-to-date (no-op) or re-lock done; 2 = preflight (uv/project missing); 3 = op failed.
param([switch]$WhatIf)
$ErrorActionPreference = 'Stop'

function Fail([string]$msg, [int]$code) {
    Write-Host "relock-runtime: ERROR: $msg" -ForegroundColor Red
    exit $code
}
function Sha7([string]$sha) { if ($sha -and $sha.Length -ge 7) { return $sha.Substring(0, 7) } else { return $sha } }

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..' '..')).Path
Push-Location $RepoRoot
try {
    $SertorDir = Join-Path $RepoRoot '.sertor'
    $PyProject = Join-Path $SertorDir 'pyproject.toml'
    $LockPath = Join-Path $SertorDir 'uv.lock'

    # 1. Preflight (fail-loud): the runtime must exist (F1) and the `uv` vehicle must be available.
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Fail "'uv' not found on PATH. Install uv (the runtime vehicle) and retry." 2
    }
    if (-not (Test-Path $PyProject)) {
        Fail "'.sertor/pyproject.toml' not found: the dogfood runtime is not installed (run F1 setup first)." 2
    }

    # 2. Fetch the remote branch so the comparison reflects the true remote HEAD (the dogfood follows
    #    origin/master, not the local working tree).
    & git fetch origin master --quiet
    if ($LASTEXITCODE -ne 0) { Fail "'git fetch origin master' failed (network?). Runtime left at last lock." 3 }

    $remoteSha = (& git rev-parse origin/master).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $remoteSha) { Fail "cannot resolve origin/master." 3 }

    # 3. Check: extract the locked sertor-core commit from uv.lock (absent lock => treat as behind).
    $lockedSha = $null
    if (Test-Path $LockPath) {
        $m = Select-String -Path $LockPath -Pattern 'Sertor\.git#([0-9a-f]+)' | Select-Object -First 1
        if ($m) { $lockedSha = $m.Matches[0].Groups[1].Value }
    }

    if ($lockedSha -eq $remoteSha) {
        Write-Host "relock-runtime: runtime already at HEAD ($(Sha7 $remoteSha)): no-op." -ForegroundColor Green
        exit 0
    }

    $fromLabel = if ($lockedSha) { Sha7 $lockedSha } else { '(no lock)' }
    if ($WhatIf) {
        Write-Host "relock-runtime: WHATIF: would re-lock $fromLabel -> $(Sha7 $remoteSha)." -ForegroundColor Yellow
        exit 0
    }

    # 4. Re-lock (only when behind), via the `uv` vehicle only — never importing sertor_core (Principio XI).
    Write-Host "relock-runtime: runtime behind ($fromLabel -> $(Sha7 $remoteSha)); re-locking..." -ForegroundColor Yellow
    & uv lock --upgrade-package sertor-core --project $SertorDir
    if ($LASTEXITCODE -ne 0) { Fail "'uv lock --upgrade-package sertor-core' failed (network/resolution)." 3 }
    & uv sync --project $SertorDir
    if ($LASTEXITCODE -ne 0) { Fail "'uv sync' failed; the runtime may be partial — re-run to fix." 3 }

    # 5. Report the new locked commit.
    $newSha = $null
    $m2 = Select-String -Path $LockPath -Pattern 'Sertor\.git#([0-9a-f]+)' | Select-Object -First 1
    if ($m2) { $newSha = $m2.Matches[0].Groups[1].Value }
    Write-Host "relock-runtime: re-lock: $fromLabel -> $(Sha7 $newSha)." -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
