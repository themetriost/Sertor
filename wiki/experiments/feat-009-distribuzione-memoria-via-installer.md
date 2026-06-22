---
title: FEAT-009 — Distribuzione memoria via installer
type: experiment
tags: [FEAT-009, memoria, installer, lifecycle, hook, distribuzione, installable-feature]
created: 2026-06-22
updated: 2026-06-22
sources: ["requirements/memoria-conversazioni/distribuzione-installer/requirements.md", "packages/sertor/src/sertor_installer/install_rag.py", "packages/sertor/src/sertor_installer/compose_plan.py"]
---

# FEAT-009 — Distribuzione memoria via installer

Chiusura del **debito di completamento FEAT-035**: l'MVP della memoria conversazioni (cattura + ricerca episodica, live sul dogfood di Sertor) diventa **installabile su un ospite**. Finora la memoria era viva SOLO nel dogfooding; chi fa `sertor install rag` su un progetto terzo **non riceveva alcuna capacità di memoria** — violava il Principio X («una feature è completa solo se installabile»). Con questa feature, la memoria è un'**opzione opt-in** nella distribuzione standard del RAG, al pari dell'hook rag-usage e della struttura wiki.

## Soluzione & scope

**Pattern di riferimento:** riuso del meccanismo dell'hook `rag-usage` (FEAT-042):
- **Tipo artefatto:** FILE (`memory-capture.ps1`) + SETTINGS_MERGE (voce hook nei `settings.json` per-assistente)
- **Ciclo di vita:** install/upgrade/uninstall idempotenti; non-distruttivo per contenuto utente
- **Per-assistente:** hook depositato nel posto giusto per Claude e Copilot CLI (`.claude/` vs `.github/`)
- **NESSUN nuovo `ArtifactKind`:** riuso di quelli esistenti, pattern già validato in FEAT-042

**Due consegne (entrambe additive, sertor-core INVARIATO):**

1. **8 manopole di memoria nel template `.env`** (template environment che ospiti ricevono):
   - Nei due file (env.local.tmpl, env.azure.tmpl)
   - `SERTOR_MEMORY`, `SERTOR_MEMORY_ADAPTER`, `SERTOR_MEMORY_RETENTION_DAYS`, `SERTOR_MEMORY_SCRUB_PATTERNS`
   - Sezione commentata, OFF di default (privacy-by-default)
   - Chi fa `sertor configure` sceglie se attivarla

2. **Hook di cattura `memory-capture.ps1` nel plan installer:**
   - Asset depositato in `assets/rag/hooks/` (accanto ad altri asset)
   - Voce hook SessionEnd nel file di settings per-assistente (come rag-usage)
   - Uninstall rimuove hook + voce preservando il resto

**Cenno nei blocchi istruzioni:** il blocco `SERTOR:RAG-USAGE` (di FEAT-042) aggiunge una riga di condizione: «Se `SERTOR_MEMORY=true`, i comandi `sertor-rag memory search/archive/list/show` diventano disponibili» — nessun nuovo marker, non confonde l'architettura.

## Design & decisioni

### DA-a: Cenno nel blocco esistente, non nuovo marker

Soluzione: una sola riga nel blocco `SERTOR:RAG-USAGE` (il blocco istruzioni RAG), non un nuovo marker `SERTOR:MEMORY-INSTRUCTIONS`. Rimane tematico e non frammenta.

### DA-b: Corpo dello script invariato

Lo script `.ps1` della cattura è quello di FEAT-035 (identico), nessun parametro `-Assistant`. L'hook è già silenzioso (exit 0 sempre, no-op se SERTOR_MEMORY non è configurato). Riuso diretto, no modifiche.

### DA-c: Riuso tipi artefatto

Le primitive di FEAT-042 (FILE + SETTINGS_MERGE, routing per-assistente) bastano. Nessun nuovo `ArtifactKind`, no nuove strategie di merge. Minimo diff nei plan-builder.

### Refactor minore: _rag_hook_fragment art-aware

La funzione `_rag_hook_fragment(plan, art)` è resa **consapevole dell'artefatto** (accetta `art: Artifact`). Dispatch su `art.source`:
- Se memoria → body hook memoria
- Se rag-usage → body hook rag-usage

Così la stessa funzione serve per produrre il frammento giusto per il merge in settings, senza raddoppiare logica. Le funzioni ridondanti `_rag_settings_fragment` sono rimosse.

## Esiti & verifiche

**Test:** 952 test non-cloud verdi (sertor 323 (+30 nuovi), +10 su install_rag_memory.py, +20 su unit env_template), kit 131, sertor-flow 134; ruff pulito su src/packages (gli 87 errori residui sono nel prototype/ congelato).

**Constitution Check:** 12/12 PASS (pre e post-design), nessuna deviazione.

**Validazione:** ciclo di vita completo esercitato:
- `install` deposita hook + manopole env
- `upgrade` aggiorna idempotente
- `uninstall` rimuove hook + voce, preserva env (opzionale --purge)

**Non yet mergiato** (branch `071-distribuzione-memoria-installer`).

## Gap dichiarato (onestà, Principio XII)

1. **Su Copilot CLI:** lo script + wiring sono depositati, ma la cattura è **INERTE** finché una **FEAT-008 di corpo** non porta un adapter di cattura Copilot (oggi esiste solo `claude-code`). Su Copilot l'hook scatta (lo script non rifiuta), ma `uv run sertor-rag memory archive` dalla radice dipende dal lavoro di installazione/ambienti e dal fatto che il core sia raggiungibile dal contesto del bot.

2. **Invocazione ospite dell'hook:** l'hook sulla macchina dell'ospite fa `uv run sertor-rag ...` dalla radice del progetto — condivide il problema generale dell'accesso alla CLI dall'host (non specifico di questa feature, FEAT-003 sbloccherà).

3. **Principio X parziale:** memoria è feature completa quando gli ospiti la ricevono via installer (SÌ, qui). Ma il **fully functioning** richiede che gli ospiti configurino creds (per catturare in Copilot) e che la CLI sia accessibile nel loro ambiente (è una precondizione, documentata).

## Backlink & corpo della distill (riflessione)

Questa feature **chiude il principio X** per la memoria (installable = done), ma **non cambia la semantica della memoria stessa** (FEAT-001/035). Il corpo evergreen **[[memoria-conversazioni]]** rimane il luogo dove vivono i dettagli; qui registriamo che la **distribuzione** è ora completa. Le pagine-entità che calano specifiche sono:
- [[sertor-installer]] — aggiornata con il pattern (FILE + SETTINGS_MERGE, lifecycle)
- [[installer-lifecycle]] — il comportamento di install/upgrade/uninstall è qui
- [[memoria-conversazioni]] — segnare che la feature è ora **installable**

---

## Vedi anche

- [[feat-035-superficie-cli-memoria-hook-sessionend]] — MVP memoria (superficie CLI + hook).
- [[feat-001-memoria-cattura-archiviazione]] — cattura e storage episodico.
- [[feat-002-ricerca-episodica-fulltext]] — ricerca FTS5.
- [[sertor-installer]] — motore di installazione (cui questa feature si aggiunge).
- [[installer-lifecycle]] — ciclo di vita installer (install/upgrade/uninstall).
- [[assistant-targeting]] — routing per-assistente Claude/Copilot.
