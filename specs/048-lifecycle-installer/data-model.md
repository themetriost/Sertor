# Data Model — Ciclo di vita dell'installer

**Feature**: `048-lifecycle-installer` (FEAT-008) | **Date**: 2026-06-17

Le entità vivono nei **pacchetti installer** (`sertor-install-kit` stdlib-only + consumer `sertor`,
`sertor-flow`), **non** in `sertor-core`. Questa feature **estende** le entità d'install esistenti
(`Artifact`, `Outcome`, `InstallReport`) e ne aggiunge poche, tutte value object frozen stdlib-only.
"NUOVO" = introdotto da questa feature; "ESTESO" = campo/membro aggiunto a un'entità esistente.

---

## §1 — `LifecycleOp` (NUOVO, enum nel kit `artifacts.py`)

Il **verbo** dell'operazione, ortogonale agli `ArtifactKind`. È la chiave del design D1 (B): un solo
plan-builder, eseguito con verbi diversi.

| Membro | Valore | Significato |
|--------|--------|-------------|
| `INSTALL` | `"install"` | comportamento odierno (default → retrocompatibile) |
| `UPGRADE` | `"upgrade"` | aggiorna asset/blocchi cambiati, rimuove obsoleti |
| `UNINSTALL` | `"uninstall"` | rimuove gli artefatti della capacità |

**Regola di validità**: `INSTALL` è il default in `execute_plan` (nessun call-site esistente cambia
comportamento, NFR-3 non-regressione).

---

## §2 — `Outcome` (ESTESO, enum nel kit `artifacts.py`)

Aggiunge due membri agli esistenti (`CREATED`, `SKIPPED`, `MERGED`, `BLOCK`, `ERROR`):

| Membro | Valore | Quando |
|--------|--------|--------|
| `UPDATED` | `"updated"` (NUOVO) | un asset standalone o un blocco a marker è stato sovrascritto perché il bundle differiva (upgrade) |
| `REMOVED` | `"removed"` (NUOVO) | un artefatto è stato rimosso dal filesystem o de-registrato (uninstall / obsoleto in upgrade) |

I membri esistenti restano invariati. La spec (§Key Entities → "Esito d'operazione") richiede
esplicitamente questi due.

---

## §3 — `Artifact` (INVARIATO)

`Artifact(kind, source, target_rel, strategy)` **non cambia**: niente nuovi `ArtifactKind` né
`WriteStrategy` inversi (decisione D1-B). Lo stesso oggetto è percorso dai tre verbi; l'operazione
inversa è scelta dall'`apply(artifact, op)` del consumer in base a `kind` + `op`.

**Mappa `ArtifactKind` → funzione inversa del kit** (per `op != INSTALL`):

| `ArtifactKind` | Tipo (A/B/C/D) | UPGRADE | UNINSTALL |
|----------------|----------------|---------|-----------|
| `FILE` | B (standalone) | `update_file_if_changed` | `remove_path` |
| `MARKER_BLOCK` | C (condiviso) | `update_marker_block` | `remove_marker_block` |
| `SETTINGS_MERGE` | C (condiviso) | additivo idempotente (no-op se presente) | `remove_settings_entries` |
| `GITIGNORE_APPEND` | C (condiviso) | additivo idempotente | `remove_gitignore_lines` |
| `MCP_MERGE` | C/D (condiviso) | additivo idempotente | `remove_mcp_server` |
| `MCP_REGISTER` | D (client) | additivo idempotente (skip se registrato) | `deregister_mcp_client` |
| `ENV_MERGE` | A (in `.sertor/`) | additivo, mai sovrascrive valori (NFR-05) | coperto da rimozione blocco `.sertor/` |
| `DEPENDENCIES` | A (in `.sertor/`) | `uv add` idempotente | coperto da rimozione blocco `.sertor/` |
| `CONFIG`/`GENERATE_CONFIG` | B | `update_file_if_changed` (o skip se preserva config utente) | `remove_path` |
| `STRUCTURE` (wiki scaffold) | B | no-op (idempotente) | dir wiki preservata salvo `--purge-wiki` |

> Tipo A (`.sertor/`) è rimosso **in blocco** da `remove_path(".sertor")` (FR-030), non per singolo
> sotto-artefatto: il diff dei path Sertor-owned (§5) marca `.sertor` come `owned_dir`.

---

## §4 — `SertorOwnedPaths` + `SharedEdit` (NUOVO, value object per consumer)

La **dichiarazione statica** dei path Sertor-owned (decisione D3, FR-017). Funzione pura
`sertor_owned_paths(capability, assistant) -> SertorOwnedPaths` co-localizzata col plan-builder.

```text
SharedEdit(frozen):
    target_rel: str                  # file condiviso (es. "CLAUDE.md", ".gitignore")
    kind:       SharedEditKind        # MARKER | SETTINGS | GITIGNORE | MCP_ENTRY
    key:        str                   # il "selettore" della porzione Sertor:
                                      #   MARKER     → coppia marker (es. "SERTOR:RAG-USAGE")
                                      #   SETTINGS   → asset fragment (comandi hook Sertor)
                                      #   GITIGNORE  → RUNTIME_IGNORES
                                      #   MCP_ENTRY  → "sertor-rag" + root_key

SertorOwnedPaths(frozen):
    owned_dirs:   tuple[str, ...]     # alberi interamente Sertor (rimovibili in blocco)
    owned_files:  tuple[str, ...]     # singoli file standalone Sertor-owned
    shared_edits: tuple[SharedEdit, ...]
```

`SharedEditKind` (NUOVO enum): `MARKER`, `SETTINGS`, `GITIGNORE`, `MCP_ENTRY`.

**Regole di validità**:
- ogni `target_rel` è relativo e non ascendente (stessa guard di `Artifact.__post_init__`);
- **invariante di copertura** (testata): per ogni capacità+assistente, l'insieme dei `target_rel`
  prodotti dal plan-builder ⊆ (`owned_dirs` ∪ `owned_files` ∪ `{e.target_rel for e in shared_edits}`).
  Questo guard-rail sostituisce il manifest (R-02/R-06).
- `owned_dirs`/`owned_files` non duplicano valori hardcoded: derivano dalle costanti già presenti
  (`_RAG_HOOK_TARGET`, `RUNTIME_IGNORES`, target risolti dall'`AssistantProfile`, ecc.).

**Esempi (illustrativi, non vincolanti per `/speckit-tasks`)**:
- `rag` / `claude`: `owned_dirs=(".sertor",)`; `owned_files=(".claude/hooks/sertor-rag-usage-check.ps1",)`;
  `shared_edits=(MARKER "CLAUDE.md"/"SERTOR:RAG-USAGE", SETTINGS ".claude/settings.json", GITIGNORE
  ".gitignore", MCP_ENTRY ".mcp.json"/"mcpServers")`.
- `wiki` / `claude`: `owned_dirs=("wiki", ".claude/skills/wiki-author")` (wiki rimosso solo con
  `--purge-wiki`); `owned_files=(".claude/commands/wiki.md", ".claude/agents/wiki-curator.md",
  ".claude/hooks/wiki-pending-check.ps1", "wiki/wiki.config.toml")`; `shared_edits=(MARKER "CLAUDE.md"
  /"SERTOR:WIKI-RITUAL", SETTINGS ".claude/settings.json")`.
- `governance` / `claude` (in `sertor-flow`): `owned_dirs=(".specify",)` (vedi nota SpecKit launch
  sotto); `owned_files=(".claude/agents/requirements-analyst.md", ...)`; `shared_edits=(MARKER
  "CLAUDE.md"/"SERTOR:SDLC-RITUAL",)`.

> **Nota SpecKit launch (FR-040, governance).** Gli artefatti `.specify/**` arrivano da `specify init`
> (feature 045, launch-installer), non dal plan-builder Sertor. Il loro uninstall/upgrade è dichiarato
> in `sertor_owned_paths("governance", ...)` come `owned_dirs=(".specify",)` con la cautela che la
> *constitution* (`CREATE_IF_ABSENT`, dell'ospite) e i template neutri non vanno sovrascritti in
> upgrade — sono trattati come asset che l'upgrade lascia invariati salvo cambio bundle Sertor-authored.

---

## §5 — `InstallReport` (ESTESO, kit `report.py`)

Aggiunge i contatori `updated` e `removed` agli esistenti (`created`/`skipped`/`merged`/`block`/
`errors`). `add(outcome)` incrementa il nuovo contatore corretto per `Outcome.UPDATED`/`REMOVED`.

- `render_human()`: il titolo riflette il verbo (`sertor upgrade rag — target: …` /
  `sertor uninstall wiki — …`); la riga di summary include `… · N updated · M removed · …`.
- `render_json()`: stesso schema `install.report/1` (NFR-06); `summary` guadagna le chiavi `updated` e
  `removed`; gli `outcome` per-artefatto possono valere i nuovi `"updated"`/`"removed"`. **Nessun nuovo
  schema** (la versione resta `install.report/1`, additiva e retrocompatibile: i consumer esistenti
  ignorano le chiavi nuove).
- `exit_code()`: invariato — `1` se ci sono errori, altrimenti `0` (anche se tutto `skipped`/`removed`).

**Aggregato (US8/FR-032).** `sertor uninstall` senza argomento esegue le capacità installate in sequenza
e produce **un report aggregato** (le `outcomes` concatenate, i conteggi sommati, `capability` =
`"all"` o l'elenco). Il dettaglio di forma è in `contracts/cli-lifecycle.md`.

---

## §6 — Relazioni e flusso (sintesi)

```text
build_<cap>_plan(profile, assistant)  ──┐  (UNICA fonte di verità degli artefatti, INVARIATA)
                                         │
sertor_owned_paths(cap, assistant)  ─────┤  (vista statica derivata, D3)
                                         │
                                         ▼
   execute_lifecycle(plan, owned, apply, op=UPGRADE|UNINSTALL, dry_run, ...)
                                         │
              per ogni Artifact ─────────┤── apply(artifact, op) → funzione inversa del kit
                                         │
              fase obsoleti (UPGRADE) ───┘── scan disco ∩ owned − plan_corrente → remove_*
                                         │
                                         ▼
                                  InstallReport (esteso) → human | JSON | log_event
```

Le funzioni inverse (`remove_marker_block`, `update_marker_block`, `remove_settings_entries`,
`remove_gitignore_lines`, `remove_mcp_server`, `deregister_mcp_client`, `update_file_if_changed`,
`remove_path`) sono **nel kit** (FR-053) e duali 1:1 delle primitive additive esistenti.
