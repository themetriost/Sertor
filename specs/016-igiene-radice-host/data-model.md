# Data Model — Igiene e collocazione (feature 016)

**Data**: 2026-06-13 · **Branch**: `016-igiene-radice-host`

Estende il modello dell'installer (feature 012/015). Solo le **delta** rispetto all'esistente.

---

## 1. `ArtifactKind` / `WriteStrategy` — nuova voce per la registrazione MCP via CLI

`artifacts.py` (enum esistenti) acquisisce un kind e una strategy per lo scope MCP *local*:

| Kind | Strategy | Significato |
|------|----------|-------------|
| `MCP_REGISTER` | `REGISTER_CLI` | Registra il server `sertor-rag` nel client via `claude mcp add-json … --scope local`; **non** scrive file nel repo. Alternativa a `MCP_MERGE` quando `--mcp-scope local`. |

Invarianti: `MCP_REGISTER` ha `source = "rag/mcp.server.json.tmpl"` (stessa entry di `MCP_MERGE`) e
`target_rel` simbolico (`"<client mcp registry>"`, non un path di repo — non viene scritto su disco;
la validazione path-traversal di `Artifact.__post_init__` resta soddisfatta da una stringa relativa
senza `..`).

`MCP_MERGE` resta invariato per lo scope `project`.

---

## 2. `RagInstallOptions` — nuovo campo `mcp_scope`

`rag_profile.py`:

```
mcp_scope: str = "project"     # {"project", "local"}; default project (comportamento attuale)
```

Validazione in `__post_init__`: valore non in `{"project","local"}` → `ConfigError` (Principio IV,
come `backend`). Il **default** è materia di `installer-multiutente`; qui resta `project`.

`RagHostProfile` non cambia (lo scope guida la *costruzione del piano*, non la specificità
dell'ospite); in alternativa `mcp_scope` può essere passato a `build_rag_plan(profile, with_deps,
mcp_scope)`. Decisione: parametro di `build_rag_plan` (lo scope è una scelta di piano, non un dato di
profilo).

---

## 3. Errore di dominio

`McpRegistrationError(SertorError)` (in `install_rag.py`, accanto a `DependencyError`): sollevato
quando lo scope `local` è richiesto ma non realizzabile (`claude` assente o `claude mcp add` fallito).
Messaggio leggibile + comando manuale equivalente. Mappa a exit code 1 (via `main`).

---

## 4. Collocazione della config wiki — regola (non un'entità)

- **Asset/installer**: `install_wiki._CONFIG_TARGET = "wiki/wiki.config.toml"` (era
  `"wiki.config.toml"`). Il valore `root="wiki"` **dentro** il file generato resta invariato.
- **Risoluzione path**: la correttezza dipende dal `root_override`:
  - via `--root .` esplicito (forma canonica), oppure
  - via auto-discovery del CLI (root = CWD quando la config è sotto `wiki/`).
- `_apply_config`: `dest.parent.mkdir(parents=True, exist_ok=True)` prima di scrivere.
- `_apply_structure`: `load_profile(config_path, root_override=target_root)`.

---

## 5. Auto-discovery della config (CLI `sertor-wiki-tools`)

Regola in `wiki_tools/__main__.py` (risoluzione del `--config` default):

```
se --config assente:
    se ./wiki.config.toml esiste            → config = ./wiki.config.toml ; root_override = (default)
    altrimenti se ./wiki/wiki.config.toml   → config = ./wiki/wiki.config.toml ; root_override = CWD (se --root assente)
    altrimenti                              → ConfigError "config non trovata" (Principio IV)
```

Host-agnostico: ordine di ricerca generico, nessun nome di dominio. Non altera il comportamento
quando `--config` è esplicito.
