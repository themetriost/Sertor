# Contract — distribuzione dual-target & guardia di parità

Distribuisce **due** asset con **due** meccanismi, entrambi riusati dall'esistente:
- la **skill `guided-setup`** col pattern eval (065): bundle `assets/rag/skills/<name>/`,
  `ArtifactKind.FILE`/`CREATE_IF_ABSENT`, **byte identici** tra target (body host-agnostico, frontmatter
  nativo agent-skill su entrambi);
- l'**agente `concierge`** col pattern `sertor-flow`: bundle `assets/rag/agents/concierge.md`,
  `Surface.AGENT`/`render_path`/`render_custom_agent`, frontmatter **tradotto** per Copilot (`model:`
  omesso), body verbatim.

Niente nuova `ArtifactKind`/`Surface`/`WriteStrategy`; nessuna modifica al kit (`render_custom_agent`
già esportato e usato da `sertor-flow`); helper di render **locale** a `install_rag.py`.

## §1 — Deposito (FR-010, US8)

`sertor install rag --assistant <id>` deposita:

| Asset sorgente | Claude | Copilot CLI |
|----------------|--------|-------------|
| `assets/rag/skills/guided-setup/SKILL.md` | `.claude/skills/guided-setup/SKILL.md` | `.github/skills/guided-setup/SKILL.md` |
| `assets/rag/agents/concierge.md` | `.claude/agents/concierge.md` | `.github/agents/concierge.agent.md` |

- **skill**: byte identici tra target (`read_asset_text`); contenitore via
  `_CLAUDE_SKILLS_BASE`/`_COPILOT_SKILLS_BASE`;
- **agente**: contenitore via `AssistantProfile.render_path(Surface.AGENT, name)`; Claude byte-copy
  (**`model: sonnet` preservato**), Copilot `render_custom_agent` (**`model:` omesso**, frontmatter
  tradotto, body verbatim);
- `WriteStrategy.CREATE_IF_ABSENT`: non-distruttivo, idempotente;
- lifecycle: skill = `owned_dir`; agente = `owned_file` → uninstall rimuove, upgrade
  `update_file_if_changed` (render-aware).

## §2 — Guardia di parità offline (FR-011, CS-5)

File: `packages/sertor/tests/test_assets_copilot_parity.py` (+ `test_install_rag.py`). Niente rete,
`uv`, ospite reale.

### G1 (PUNTO CRITICO) — `_render_rag` allineato al render reale

Il renderer del test (`_render_rag`) oggi fa byte-copy pura. Va allineato al render del plan: **tradurre
gli `.agent.md`** (come fa `install_rag._render_rag_file`). Altrimenti il body Copilot dell'agente
testato non è quello realmente depositato e il **`model: sonnet`** del frontmatter Claude potrebbe
sfuggire ai check di leak. Allineato `_render_rag`, gli invarianti coprono anche l'agente.

### (a)(b)(c) — su skill E agente Copilot

- **(a)** nessun path-string `.claude/`;
- **(b)** nessuna slash-command invocata;
- **(c)** nessun nome assistente "Claude Code" / nome prodotto-modello Claude (`CLAUDE.md`/`Claude`/
  `Opus`/`Haiku`/`$ARGUMENTS`) — incluso il fatto che il frontmatter Copilot dell'agente **non** porti
  `model:` (omesso dal renderer).

### (d) — closure mirata

L'agente `concierge` cita **per nome** la skill `guided-setup` (riferimento per-nome-asset, non
file-`.md`). Closure mirata: ogni asset di usabilità citato per nome corrisponde a un asset **depositato
dal rag plan** su quel target (agente → skill `guided-setup` deve esistere).

### Test di deposito + frontmatter (`test_install_rag.py`)

- `test_guided_setup_skill_deposited_{claude,copilot}` + `test_guided_setup_body_byte_identical`;
- `test_concierge_agent_deposited_claude` (frontmatter contiene `model: sonnet`);
- `test_concierge_agent_deposited_copilot` (frontmatter **senza** `model:`, senza leak Claude);
- `test_concierge_routes_to_guided_setup` (un ramo, no FEAT-004/007);
- `test_no_wiki_artifacts_created` **ristretto**: il rag plan non deposita l'agente **wiki**
  (`wiki-curator`), ma SÌ l'agente `concierge`.

### Anti-corpo-a-mano

`test_no_hand_maintained_copilot_prompt_bodies` resta valido: nessun secondo corpo Copilot a mano per
skill/agente (resi da fonte unica).

## §3 — «Feature completa» (corollario installabile)

Done **solo** quando un ospite **Claude E uno Copilot** ricevono **skill E agente** via `sertor
install` (FR-010/011 — in ambito). Prova LIVE su ospite reale = follow-up, non done automatico (il done
automatico è deposito + parità verificati offline).
