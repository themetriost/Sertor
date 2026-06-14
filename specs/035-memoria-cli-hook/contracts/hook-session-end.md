# Contratto Hook — cattura automatica a fine sessione (Claude Code)

**Feature**: 035 | **Schema**: `hook.memory-capture/1` | **Host**: Claude Code (primo adattatore).

Hook **host-specifico** (FR-018, A-005): adatta il *trigger* di fine sessione dell'assistente ospite
all'invocazione del comando **host-agnostico** `sertor-rag memory archive`. Non contiene logica di
archiviazione (FR-011). Non-bloccante (FR-012) e non-fatale (FR-013).

## Wiring

- **Script**: `.claude/hooks/memory-capture.ps1` (PowerShell, versionato — dogfood di Sertor).
- **Configurazione**: voce aggiunta al blocco `SessionEnd` di `.claude/settings.json` (versionato),
  accanto alla voce esistente del wiki (additivo, non la sostituisce):

```jsonc
"SessionEnd": [
  { "hooks": [
      { "type": "command", "shell": "powershell", "timeout": 10,
        "command": "...wiki-pending-check.ps1 -Mode SessionEnd" },     // esistente, invariato
      { "type": "command", "shell": "powershell", "timeout": 15,
        "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/memory-capture.ps1')" }
  ] }
]
```

## Comportamento dello script

```
1. Pre-check gate privacy:
     se $env:SERTOR_MEMORY NON ∈ {true,1,yes,on} (case-insensitive)  →  exit 0  (no-op silenzioso)
2. Risolvi la root di progetto: $env:CLAUDE_PROJECT_DIR  →  hook.cwd (stdin JSON)  →  '.'
3. Invoca il comando host-agnostico, assorbendo qualunque esito:
     try { (push-location root) ; <runner> sertor-rag memory archive 2>$null ; (pop-location) }
     catch { }                          # mai propagare
   <runner> = 'uv run' in dev (rilevato se presente pyproject + uv), altrimenti 'sertor-rag' diretto.
4. exit 0    SEMPRE   (qualunque cosa accada al comando)
```

## Garanzie (mappate ai requisiti)

| Garanzia | Meccanismo | Req |
|----------|-----------|-----|
| No-op silenzioso a memoria spenta | pre-check env → `exit 0`, nessun output | FR-015, SC-006 |
| Non contiene logica di archiviazione | invoca solo il comando CLI | FR-011 |
| Non-fatale | `try/catch`, esce sempre 0, ignora l'exit del comando | FR-013, SC-005 |
| Non-bloccante | cattura locale e leggera (no rete); `timeout` host come cap | FR-012, SC-005 |
| Trigger automatico | evento `SessionEnd` dell'host (transcript completo, A-004) | FR-010, SC-004 |
| Host-specifico, comando host-agnostico | adattatore del trigger → CLI portabile | FR-018 |

## Edge cases coperti

- **Host diverso / fuori sessione**: lo script non è invocato (è cablato solo in Claude Code); se
  invocato a mano senza stdin, tollera l'assenza di JSON e usa `.` come root.
- **Memoria abilitata ma archiviazione che fallisce**: il guasto è assorbito dal `try/catch`, la
  chiusura sessione procede (FR-013).
- **`uv`/`sertor-rag` non disponibile**: il `try/catch` assorbe; `exit 0`, nessun rumore.

## Fuori ambito (estensioni)

- Distribuzione su ospiti esterni via `sertor install` (qui solo dogfood Sertor).
- Hook per assistenti diversi da Claude Code (adattatori futuri del medesimo trigger → stesso comando).
- Avvio in background (`Start-Process`): via di fuga documentata se la cattura diventasse costosa;
  oggi YAGNI.
