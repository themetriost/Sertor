---
title: Ponte D→N — layer agentico host-agnostico sul nucleo deterministico
type: experiment
tags: [wiki, host-agnostico, principio-x, feat-003-n, tooling, confine-deterministico-giudizio]
created: 2026-06-05
updated: 2026-06-05
sources: [".claude/skills/wiki-author/wiki-playbook.md", ".claude/skills/wiki-author/SKILL.md", ".claude/commands/wiki.md", ".claude/agents/wiki-curator.md", "wiki.config.toml", "src/sertor_core/wiki_tools/", "requirements/sertor-core/wiki-llm/TODO.md", "CLAUDE.md"]
---

# Ponte D→N — il layer agentico poggia sul deterministico, host-agnostico

Primo step della traccia collaborativa **FEAT-003-N** (la metà *di giudizio* del Wiki LLM). Trasforma —
non ricrea — il layer agentico del wiki perché: (1) poggi sul **nucleo deterministico** `wiki_tools`
(FEAT-003-D) per il meccanico, (2) sia **host-agnostico** (Principio X), (3) abbia **nomi coerenti**.
Scope deciso con l'utente: **leggero** (solo prosa/config/glue, zero codice in `sertor_core`). Vedi
[[nucleo-wiki-deterministico-feat003d]], [[sistema-wiki-fonte-unica]], [[costituzione-v1]], [[deterministic-vs-judgment]].

## Il confine D ↔ N (la clarity, esito di questo step)

Ogni operazione del playbook ora separa **meccanico** (chiamata CLI `sertor-wiki-tools`) da **giudizio**
(resta all'LLM):

| Operazione | D — meccanico (CLI) | N — giudizio (LLM) |
|---|---|---|
| `record` | `collect` (inventario) | il **perché**, il **corpo** pagina, nuova-vs-aggiorna, **quali** backlink |
| `ingest` | `collect`, `lint` (l'import file non ha ancora un tool D) | riassumere la fonte, integrarla, **segnalare contraddizioni** |
| `query` | `collect`, `index` (RAG) | rispondere, decidere se archiviare |
| `lint` | `lint`+`validate` = **100% meccanico** | **lint semantico** (contraddizioni, claim superati) = N5, futuro |
| `generate-from-diff` | `scan` (anchor mtime); git → ruolo `[roles].vcs` | decidere pagine impattate, scrivere update |
| `rag-sync` | `index` = **100% meccanico** | — |
| `structure` | `structure init` = bootstrap idempotente | — |

Principio: il *dove/come* (percorsi, formati, rilevazione) è del deterministico; il *cosa/perché* è dell'LLM.

## Host-agnosticità (Principio X)

L'**unica fonte di specificità dell'ospite** è `wiki.config.toml` (root, tassonomia, frontmatter,
`source_dirs`/`exclude`, `[roles]`, `[rag]`, `language`, `[strings]`). Il playbook e le superfici non
assumono più `wiki/`, `src/`, né i nomi-agente: li leggono dalla config. I nomi-agente nel testo sono
ora **ruoli** (`[roles].curator`, `[roles].vcs`), non letterali. Portare la capacità su un altro
progetto = cambiare il file di config, non il corpo delle istruzioni.

## Rename coerente delle 4 entità (author/curator)

| Entità | Tipo | Prima | Dopo |
|---|---|---|---|
| skill | auto-invocata | `genera-wiki` | **`wiki-author`** |
| playbook | doc fonte | `playbook.md` | **`wiki-playbook.md`** |
| comando | manuale | `/wiki` | `/wiki` (invariato, entry ergonomica) |
| agente | background | `wiki-keeper` | **`wiki-curator`** (+ tool `Bash`) |

L'agente `wiki-curator` ha ora **`Bash`** così può chiamare la CLI (prima, con soli Read/Write/Glob/Grep,
non poteva). Author = scrive le pagine; Curator = mantiene in background: ruoli LLM distinti.

## Quattro scoperte (perché alcune cose restano LLM-authored)

1. **La CLI espone solo lettura/validazione** (`scan, structure, validate, lint, collect, index`) — **non**
   i write-back: `registry.append_log`/`upsert_index` sono funzioni Python, non comandi CLI.
2. **Disallineamento identità/formato:** `upsert_index` usa `rel_path` POSIX e scrive una riga piatta col
   path (es. `area/file.md`) tra doppie graffe; l'`index.md` curato usa invece lo slug nudo (es. `foo`)
   tra doppie graffe, in sezioni `### …` con `**bold**`. `append_log` scrive solo l'header, non i bullet di giudizio.
3. Conseguenza: **log/indice restano scritti dall'LLM a mano** in questo step (il ponte è "leggero").
4. **Gli hook** hanno ancora root/index/log e il nome curatore come *stringhe*; parametrizzarli da config
   richiede estendere il contratto `scan` (= codice) → **deferito**.

## Fuori scope (prossimi step FEAT-003-N)

- **Scope "completo":** esporre i write-back in CLI + riconciliare identità/formato dell'index curato →
  sblocca l'offload totale di `record`.
- **FR-004** (trigger esatto del popolamento: hook `Stop`/`SessionEnd` vs `/wiki` vs entrambi).
- Operazioni di contenuto N1/N2/N5… (giudizio vero: distillazione, lint semantico).

## Verifica

CLI invariata e funzionante col config rinominato: `scan` (6 pending = le modifiche `.claude/`),
`lint`/`validate` puliti (0 broken/orphans), `collect` = 16 pagine. Nessun nome vecchio residuo nei file
tooling (`grep genera-wiki|wiki-keeper` → solo registro storico e artefatti SpecKit datati).
