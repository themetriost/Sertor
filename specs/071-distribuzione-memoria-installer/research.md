# Research — Distribuzione della memoria via installer (FEAT-009)

Fase 0. Decisioni di *come*, ancorate all'esistente (MCP-first/dogfooding). Nessuna cambia lo scope.

## Fatti di terra (verificati)
- **8 manopole memoria** in `src/sertor_core/config/settings.py:132-149`: `SERTOR_MEMORY`,
  `SERTOR_MEMORY_ADAPTER`, `SERTOR_MEMORY_RETENTION_DAYS`, `SERTOR_MEMORY_SCRUB_PATTERNS`,
  `SERTOR_EPISODIC_LIMIT`, `SERTOR_EPISODIC_SNIPPET_TOKENS`, `SERTOR_MEMORY_LIST_LIMIT`,
  `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`. Privacy-by-default: `memory_enabled=False`.
- I template `.env` dell'installer (`assets/rag/env.{local,azure}.tmpl`) **non** contengono manopole
  memoria (gap).
- L'hook `.claude/hooks/memory-capture.ps1` + la voce `SessionEnd` (`.claude/settings.json`) vivono
  **solo** nel `.claude/` di Sertor (gap). L'hook è un wrapper sottile, privacy-gated, non-fatale, exit 0.
- **Pattern gemello = hook rag-usage** (`install_rag.py`, feature 042/044/011): `FILE` (CREATE_IF_ABSENT)
  + `SETTINGS_MERGE` (MERGE_DEDUP), routing per-assistente via `AssistantProfile`, wiring Copilot
  **generato** via `render_copilot_hooks` in `.github/hooks/sertor-hooks.json`, lifecycle inverso +
  `sertor_owned_paths` + guardia `plan ⊆ owned`.
- Gemello ancora più vicino per la forma `SessionEnd`: `assets/settings.hooks.json` (wiki) ha già una
  voce `SessionEnd` annidata Claude; `render_copilot_hooks` supporta l'evento `SessionEnd`
  (`surfaces.py`, mappa nativa `sessionEnd`).

## Forche risolte
- **DA-a (cenno istruzioni):** righe nel blocco `SERTOR:RAG-USAGE` esistente — *Alternative scartata:*
  nuovo marker `SERTOR:MEMORY-USAGE` (più superficie, nuovo `shared_edit`, nessun valore aggiunto ora).
- **DA-b (`-Assistant` sullo script):** non serve — l'hook è già silenzioso/exit-0; corpo unico
  cross-assistente (FR-015). *Alternative scartata:* parametro nuovo (complessità senza beneficio).
- **DA-c (tipo artefatto):** riuso `FILE`+`SETTINGS_MERGE`. *Alternative scartata:* nuovo `ArtifactKind`
  (viola YAGNI; il gemello rag-usage dimostra che bastano i tipi esistenti).

## Gap dichiarato (onestà, Princ. XII)
- Su **Copilot CLI** lo script + wiring sono depositati ma la **cattura è inerte**: l'unico adapter è
  `claude-code` (legge `~/.claude/projects`). Cattura Copilot reale = **FEAT-008** (già nel backlog).
- **Invocazione su host** dell'hook (`uv run sertor-rag memory archive` dalla radice host) condivide la
  questione generale «come si invoca `sertor-rag` su un host» col resto della CLI; l'hook è **non-fatale**
  (degrada in silenzio se il runtime non risolve). Non risolto qui (corpo invariato, FR-015) →
  **follow-up tracciato** (vedi tasks/roadmap), non un blocco di questa feature.
