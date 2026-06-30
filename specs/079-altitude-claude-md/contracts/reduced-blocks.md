# Contract — substringhe stabili dei blocchi ridotti e del reference unico

Questo contratto fissa le **substringhe testuali stabili** che le guardie verificano. Sono ancore di
*presenza* (contenuto load-bearing conservato) e di *assenza* (dettaglio lookup estratto). Il testo
esatto è di `implement`; le substringhe qui sono il **contratto verificabile offline**.

## C1 — Blocco RAG ridotto (`rag/claude-md-block-rag-usage.md`) — REQ-015

**DEVE contenere (presenza, standing):**
- `sertor_core` + `vehicles` (CLI / MCP) → direttiva vehicle-only / no-import (es. «Do NOT import
  `sertor_core` directly»).
- `Search first` (o `search`… `before reading files`) → search-first, read-second.
- `uv run --project .sertor sertor-rag search` → esempio robusto conservato (mantiene
  `test_rag_usage_block_uv_run_replaces_bare_search` e `_ROBUST` presence).
- `error` + `signal` → «errore MCP = segnale, non rumore».
- `SERTOR_MEMORY` → gate privacy memoria conservato.
- `sertor-cli-reference.md` → **pointer per nome** al reference unico (REQ-002/015).

**NON DEVE contenere (assenza, lookup estratto — REQ-001/012):**
- l'heading `## How to invoke Sertor's commands`.
- `pywin32_bootstrap` (Windows note).
- `uvx --from` (livello installer — vive solo nel reference).
- `--directory` (spiegazione footgun — vive solo nel reference).

## C2 — Blocco wiki ridotto (`claude-md-block.md`) — REQ-014

**DEVE contenere (presenza, standing):**
- `Golden rule` → golden rule documentazione.
- `Step` + `Record` + `Distill` + `lint` → outline del rituale di step.
- `wiki-curator` + `main flow` → regole di delega (record→curator; distill/lint→main flow).
- `judgment` (D↔N) → confine meccanico vs giudizio.
- `wiki-playbook.md` → **riferimento per nome** al wiki playbook (REQ-014).

**NON DEVE contenere (assenza, lookup estratto):**
- l'enumerazione completa delle operazioni come sezione `### Wiki operations` con i bullet
  `ingest`/`query`/`reorg`/`generate`/`rag-sync`/`structure` (spostata al playbook).
- la sezione `### Conventions` con `YAML frontmatter`/`kebab-case`/formato voce di log (spostata).

*(Nota: golden rule, record/distill/lint e D↔N restano; ciò che esce è la reference enumerativa.)*

## C3 — Blocco SDLC (`claude-md-block-sdlc.md`) — REQ-016 (INVARIATO)

**DEVE contenere (tutto standing, invariato):**
- `The SpecKit flow` con le fasi `requirements`…`implement` in ordine.
- `Constitution Check` (gate).
- `Error discipline` (`fix, don't suppress`).
- `Version control discipline` (`Branch + PR`, `Conventional Commits`, `configuration-manager`).

**NON DEVE contenere:** `How to invoke`, `pywin32_bootstrap` (già assenti — DA-D-r3; guardia di
non-reintroduzione).

## C4 — Reference unico (`rag/sertor-cli-reference.md`) — REQ-005/006

**DEVE contenere (la sezione completa, UNICA sede):**
- l'heading `How to invoke Sertor's commands`.
- livello runtime: `uv run --project .sertor` + chiarimento `not on PATH` (≠ not installed) +
  `--project` NOT `--directory` + fallback al venv (`.sertor/.venv/Scripts/` / `bin/`).
- livello installer: `uvx --from "git+https://github.com/themetriost/Sertor` …
- Windows note: `pywin32_bootstrap` … `unaffected`.

**Invarianti (REQ-006, host-agnostico):**
- NON contiene `.claude/` (percorso assistente-specifico).
- NON contiene uno slash-command come invocazione (`/wiki`, `/requirements`).
- NON contiene nomi modello/prodotto Claude (`Claude`, `Opus`, `Haiku`, `CLAUDE.md`, `$ARGUMENTS`).
- NON contiene `uv run --directory .sertor` (footgun — solo il template MCP lo tiene).

## C5 — `guided-setup/SKILL.md` — REQ-008

**DEVE contenere:** `sertor-cli-reference.md` (pointer per nome) al posto della sezione inline.
**NON DEVE contenere:** l'heading `## How to invoke Sertor's commands` (sezione rimossa); conserva il
resto della logica (Step 0–6, consent gate, ecc.) e la forma robusta nei passi (`_ROBUST` presence).

## C6 — `wiki-playbook.md` — REQ-009 (closure-safe)

**DEVE contenere:** la forma minima di invocazione al §2 (`uv run --project .sertor sertor-wiki-tools`)
+ un chiarimento PATH (`not on `PATH``) + una frase condizionale **senza token di file** sul reference
RAG.
**NON DEVE contenere:** l'heading `### How to invoke the runtime CLIs`, la Windows note
(`pywin32_bootstrap`), né il token di file ``sertor-cli-reference.md`` (eviterebbe la closure sul piano
wiki). Resta host-agnostico: nessun `uvx --from`, nessun URL `github.com/themetriost/Sertor`.
