<#
.SYNOPSIS
  Trigger automatico (non bloccante) per la manutenzione del wiki.
  Logica CONDIVISA tra l'hook Stop e l'hook SessionEnd — fonte unica anche per gli hook.

.DESCRIPTION
  Euristica mtime-based (niente git → policy-neutra): se esiste almeno un file sorgente sotto
  src/ specs/ requirements/ .claude/ con LastWriteTime piu' recente dell'ultima scrittura di
  wiki/log.md, c'e' "lavoro non ancora registrato" nel wiki.
    - Mode Stop:       stampa JSON con additionalContext (NON bloccante: nessun decision:block).
                       Rispetta la guardia anti-loop stop_hook_active.
    - Mode SessionEnd: stampa JSON con systemMessage di riepilogo verso il terminale.
  Se non c'e' lavoro pendente: nessun output, exit 0 (niente rumore a ogni turno).
  L'input dell'hook (JSON) arriva su stdin; lo script e' tollerante se assente (test manuali).
#>
[CmdletBinding()]
param([ValidateSet('Stop', 'SessionEnd')][string]$Mode = 'Stop')

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

# --- input hook (JSON su stdin) ---
$raw = ''
try { $raw = [Console]::In.ReadToEnd() } catch {}
$hook = $null
if ($raw -and $raw.Trim()) { try { $hook = $raw | ConvertFrom-Json } catch { $hook = $null } }

# --- guardia anti-loop: se Claude e' gia' in un ciclo di Stop hook, lascialo terminare ---
if ($Mode -eq 'Stop' -and $hook -and $hook.stop_hook_active) { exit 0 }

# --- radice progetto: env dell'harness, poi cwd dell'hook, poi cartella corrente ---
$root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR }
        elseif ($hook -and $hook.cwd) { $hook.cwd }
        else { '.' }

# --- ancora temporale: ultima scrittura di wiki/log.md (assente => tutto e' pendente) ---
$log = Join-Path $root 'wiki/log.md'
$anchor = if (Test-Path $log) { (Get-Item $log).LastWriteTime } else { [DateTime]::MinValue }

# --- scansione sorgenti, con esclusione di artefatti/ambienti rigenerabili ---
$dirs = @('src', 'specs', 'requirements', '.claude')
$exclude = '[\\/](\.git|\.venv[^\\/]*|venv|__pycache__|\.ruff_cache|\.pytest_cache|\.mypy_cache|node_modules|\.index[^\\/]*)([\\/]|$)'

$pending = 0
foreach ($d in $dirs) {
    $p = Join-Path $root $d
    if (-not (Test-Path $p)) { continue }
    $hits = Get-ChildItem -Path $p -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch $exclude -and $_.LastWriteTime -gt $anchor }
    $pending += @($hits).Count
}

if ($pending -eq 0) { exit 0 }

# --- output per evento ---
if ($Mode -eq 'Stop') {
    $msg = "Lavoro non ancora registrato nel wiki: $pending file sotto src/specs/requirements/.claude " +
           "risultano piu' recenti dell'ultima voce di wiki/log.md. Per la regola aurea (vedi CLAUDE.md, " +
           "sezione Wiki): valuta di delegare al wiki-keeper (operazione record) o eseguire /wiki."
    $out = @{ hookSpecificOutput = @{ hookEventName = 'Stop'; additionalContext = $msg } }
    $out | ConvertTo-Json -Compress -Depth 5
    exit 0
}
else {
    $msg = "Wiki: $pending file modificati non risultano ancora registrati. " +
           "Alla prossima sessione esegui /wiki record (o delega al wiki-keeper)."
    $out = @{ systemMessage = $msg }
    $out | ConvertTo-Json -Compress -Depth 5
    exit 0
}
