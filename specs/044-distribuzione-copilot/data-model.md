# Data Model — Distribuzione su GitHub Copilot (FEAT-007)

Entità di dominio dell'installer toccate/aggiunte. Tutto stdlib, value object frozen (coerente con
`sertor_install_kit/artifacts.py`). Nessun import di SDK (Principio I).

## §1. `AssistantId` (nuovo — enum)

Identifica l'assistente target dell'installazione.

| Valore | Significato | Stato |
|---|---|---|
| `claude` | Claude Code (default) | supportato |
| `copilot` | GitHub Copilot (VS Code agent mode) | supportato (questa feature) |
| `codex` | OpenAI Codex | **non** in FEAT-007 (Could) |

Regole: valore sconosciuto → `ConfigError` esplicito e azionabile (Principio IV); il default applicato
quando assente è `claude` ed è documentato (FR-002).

## §2. `Surface` (nuovo — enum)

La categoria **logica** di artefatto distribuibile, indipendente dall'assistente. È il perno della
parità: ogni Surface ha una resa per ciascun `AssistantId`.

| Surface | Contenuto (fonte unica) | Capacità |
|---|---|---|
| `INSTRUCTION_BLOCK` | blocco rituale/uso (testo a marker) | wiki, rag |
| `MCP_SERVER` | entry del server `sertor-rag` | rag |
| `COMMAND` | corpo del comando/skill (es. `/wiki`, `wiki-author`) | wiki |
| `AGENT` | persona dell'agente (`wiki-curator`) | wiki |
| `HOOK` | wiring evento→script (script riusato) | wiki, rag |

## §3. `AssistantProfile` (nuovo — vive nel `sertor-install-kit`)

Risolve, per un dato `AssistantId`, come ogni `Surface` si materializza: il **contenitore** concreto
(path relativo) + la `WriteStrategy`/formato. È l'unico punto che conosce le convenzioni per-assistente
(Principio X: l'assistente si configura, non si presume nel corpo dei plan-builder).

Mappa concettuale (campi → `(target_rel, strategy/contenitore)`):

| Surface | `claude` | `copilot` |
|---|---|---|
| `INSTRUCTION_BLOCK` | `CLAUDE.md` · MARKER_BLOCK | `.github/copilot-instructions.md` · MARKER_BLOCK |
| `MCP_SERVER` | `.mcp.json` (`mcpServers`) · MCP_MERGE | `.vscode/mcp.json` (`servers`) · MCP_MERGE |
| `COMMAND` | `.claude/commands/*.md`,`.claude/skills/*` · FILE | `.github/prompts/*.prompt.md` · FILE(reso) |
| `AGENT` | `.claude/agents/*.md` · FILE | `.github/agents/*.agent.md` · FILE(reso) |
| `HOOK` | `.claude/settings.json` · SETTINGS_MERGE | `.github/hooks/sertor-*.json` · SETTINGS_MERGE |

Invarianti:
- Lo **script** dell'hook (`*.ps1`/`*.sh`) è lo **stesso** per i due assistenti (FILE, invariato); varia
  solo il wiring (dove/come è registrato).
- Il **contenuto** condiviso (testo blocco, entry MCP, corpo comando, persona agente) ha **una** fonte;
  la resa Copilot è derivata/guardata (anti-drift, REQ-021).
- I `target_rel` restano **relativi** e validati (no `..`, no assoluti) come da `Artifact.__post_init__`.

## §4. `Artifact` / `ArtifactKind` / `WriteStrategy` (esistenti — riuso + minima estensione)

- **Riuso senza modifica:** `FILE`/`CREATE_IF_ABSENT`, `MARKER_BLOCK`/`APPEND_BLOCK`,
  `SETTINGS_MERGE`/`MERGE_DEDUP` (vale anche su `.github/hooks/*.json`, è un file JSON arbitrario),
  `GITIGNORE_APPEND`, `DEPENDENCIES`.
- **Estensione minima:** `MCP_MERGE` resa parametrica sulla **root-key** (`mcpServers` ↔ `servers`) e
  sul **target** (`.mcp.json` ↔ `.vscode/mcp.json`). Nessuna nuova `ArtifactKind` necessaria.
- Il **plan-builder** non cabla più i path: li chiede all'`AssistantProfile`.

## §5. `InstallReport` / `ArtifactOutcome` (esistenti — invariati)

Outcome per artefatto invariati (`created`/`skipped`/`merged`/`block`/`error`). Si aggiunge in report il
campo informativo dell'**assistente target** (osservabilità, Principio IX) e, dove una Surface non ha
resa su un assistente, un outcome esplicito che **dichiara il gap** (FR-016) — mai un'omissione tacita.
