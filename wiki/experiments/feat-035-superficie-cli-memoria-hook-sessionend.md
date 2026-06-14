---
title: FEAT-035 — Superficie CLI memoria + hook SessionEnd (MVP completo)
type: experiment
tags: [FEAT-035, memoria, superficie-cli, hook, sessionend, thin-consumer, speckit, MVP]
created: 2026-06-14
updated: 2026-06-14
sources: ["src/sertor_core/cli/__main__.py", "src/sertor_core/cli/output.py", ".claude/hooks/memory-capture.ps1", ".specify/memory/constitution.md"]
---

# FEAT-035 — Superficie CLI memoria + Hook SessionEnd

Completamento dell'MVP della memoria conversazioni (FEAT-001 + FEAT-002) con la **superficie d'uso** (CLI) e il **grilletto automatico** (hook SessionEnd). Con questa feature, la memoria episodica passa da componente bibliotecariana a strumento quotidiano: da terminale si cercano le conversazioni, e la cattura avviene automaticamente a fine sessione senza azione manuale.

## Feature completata (SpecKit full)

**Branch:** mergiata su master (PR oggi 2026-06-14). **SpecKit:** specify → plan → tasks → analyze → implement completo in giornata. **Validazione:** 12 nuovi test, 527 test non-cloud verdi, ruff clean, Constitution PASS 10/10.

### Componente 1: CLI thin-consumer memoria

**File:** `src/sertor_core/cli/__main__.py` (gruppo argparse `memory` con sub-sub-parser).

- **`sertor-rag memory archive`** — call `build_memory_archiver(settings).archive_all()`, report archived/skipped, idempotente. Se memoria è OFF (`SERTOR_MEMORY=false` o non configurato), comando esce 1 con messaggio azionabile.
- **`sertor-rag memory search "<query>"`** — call `build_episodic_search(settings).search(SearchQuery(...))`, filtri opzionali `--since`/`--until`/`-k`, output umano + `--json` per scripting. Integrazione: stesso stile di output di `sertor-rag search`.

**Principio:** [[thin-consumer]] — i comandi **non reimplementano** logica di archivio/ricerca, **importano** e **cablano** i servizi core da factory `build_*`, esattamente come [[mcp-server]].

**Output:** `src/sertor_core/cli/output.py` con funzioni pure `format_archive_report` e `format_memory_results` (stile `format_search_results` esistente).

### Componente 2: Hook SessionEnd (host-specifico)

**File:** `.claude/hooks/memory-capture.ps1` (PowerShell, hook del flusso Claude Code).

**Meccanismo:**
1. Pre-check: legge `SERTOR_MEMORY` (variabile d'ambiente o da .env).
   - Se OFF o assente → exit 0 subito (no-op, non-bloccante).
   - Se ON → procedi.
2. Launch `uv run sertor-rag memory archive` con stdout/stderr soppresso (non infastidire il flusso).
3. Try/catch generico: **exit 0 sempre** — anche se l'archivio fallisce, il flusso continua (nessun blocco).
4. Wiring: nel blocco `SessionEnd` di `.claude/settings.json` accanto all'hook wiki (già presente).

**Determinismo:** l'archiviazione è **idempotente** (sessione archiviata una sola volta per canonical key) e **non-fatale** (errori = warning, non eccezione) → adatta a un hook unattended.

**Privacy:** cattura disattivata per default; l'hook diventa no-op se `SERTOR_MEMORY` non è configurato.

### Comportamento end-to-end

1. Accendi `SERTOR_MEMORY=true` nel `.env`.
2. Parla con l'assistente (conversazioni catturate a fine sessione via hook, silenziosamente).
3. Qualunque momento: `sertor-rag memory search "argomento"` per cercare nelle conversazioni passate.
4. Oppure `sertor-rag memory archive` se vuoi forzare un'archiviazione manuale (es. prima di una pulizia).

### Requisiti soddisfatti

- **MVP memoria COMPLETO**: FEAT-001 (archivio) + FEAT-002 (ricerca) + FEAT-035 (superficie CLI + cattura auto).
- **Host-agnostico (Principio X):** comandi indipendenti dall'assistente; hook è host-specifico (come da FEAT-008 per wiki), ma il **core che archivia è generico** (porta + adapter).
- **Privacy-by-default:** memoria disattivata se non configurata; cattura silente, non interferisce col flusso principale.
- **Non-bloccante:** hook ha sempre exit 0, CLI ha validazione esplicita su memoria OFF (exit 1, messaggio chiaro).

## Nota: operazioni FUORI da questa feature

**Non** incluse (indicate nel brief come differite):
- Hook per assistenti diversi da Claude Code (FEAT-008 per wiki come precedente, resta il pattern).
- Distribuzione dell'hook su ospiti esterni via `sertor install` (FEAT-012 update).
- Refresh di sessioni parziali cresciute (degrada a no-op idempotente, OK così).
- Ricerca semantica (FEAT-004, può usare FTS5 di FEAT-002 come baseline).
- Distillazione da archivio (FEAT-003, farà query su episodico e pomperà nel wiki).
- Retention policy (FEAT-006, SQLite già ready, schema include `created_ts` per cleanup).
- Remember-this (FEAT-005, manuale, orthogonale).

## Pagine evergreen aggiornate (distill)

- **[[memoria-conversazioni]]** — segnare che MVP ha NOW superficie (CLI) e cattura (hook).
- **[[memoria-negli-agenti]]** explainer — linguaggio comune: «si usa da terminale e si salva da sola a fine sessione».

---

## Vedi anche

- [[feat-001-memoria-cattura-archiviazione]] — cattura & store.
- [[feat-002-ricerca-episodica-fulltext]] — ricerca.
- [[transcript-capture-adapter-e-storage]] — dettagli tecnici della porta.
- [[ricerca-episodica-fts5]] — motore FTS5.
- [[thin-consumer]] — il pattern architetturale.
