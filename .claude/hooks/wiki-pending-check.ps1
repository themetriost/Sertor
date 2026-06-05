<#
.SYNOPSIS
  Trigger automatico (non bloccante) per la manutenzione del wiki — thin wrapper sulla CLI.

.DESCRIPTION
  Delega la logica al nucleo deterministico host-agnostico (FEAT-003-D): invoca
    sertor-wiki-tools scan --config <root>/wiki.config.toml --json
  e mappa il contratto `wiki.scan/1` (`pending`, `message`) al formato dell'hook. Nessuna
  euristica mtime duplicata qui: la fonte unica e' la CLI (Principio X, niente path hard-coded).
    - Mode Stop:       JSON con additionalContext (NON bloccante; rispetta stop_hook_active).
    - Mode SessionEnd: JSON con systemMessage di riepilogo verso il terminale.
  Se non c'e' lavoro pendente (o la CLI non e' disponibile): nessun output, exit 0.
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

$config = Join-Path $root 'wiki.config.toml'
if (-not (Test-Path $config)) { exit 0 }   # nessuna config host → niente da fare

# --- delega al nucleo deterministico: scan --json → contratto wiki.scan/1 ---
$scan = $null
try {
    Push-Location $root
    $out = uv run sertor-wiki-tools scan --config $config --json 2>$null
    Pop-Location
    if ($out) { $scan = ($out | Select-Object -Last 1 | ConvertFrom-Json) }
} catch {
    try { Pop-Location } catch {}
    exit 0   # CLI non disponibile / errore: hook silenzioso, niente rumore
}

if (-not $scan -or $scan.schema -ne 'wiki.scan/1' -or [int]$scan.pending -le 0) { exit 0 }

$pending = [int]$scan.pending

# --- output per evento (riusa il message localizzato del contratto) ---
if ($Mode -eq 'Stop') {
    $msg = "$($scan.message) Per la regola aurea (vedi CLAUDE.md, sezione Wiki): valuta di " +
           "delegare al wiki-keeper (operazione record) o eseguire /wiki."
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
