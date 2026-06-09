---
title: wiki-tools (nucleo deterministico del wiki)
type: tech
tags: [wiki-tools, cli, deterministico, host-agnostico, wiki, sertor-core, contracts]
created: 2026-06-08
updated: 2026-06-09
sources: ["src/sertor_core/wiki_tools/registry.py", "src/sertor_core/wiki_tools/**", "wiki.config.toml"]
---

# wiki-tools (nucleo deterministico del wiki)

**`wiki_tools`** (console-script **`sertor-wiki-tools`**, sottopacchetto `src/sertor_core/wiki_tools/`) è il
**nucleo meccanico** del sistema-wiki: orchestra **tutte le operazioni deterministiche** del wiki locale —
scan, lint strutturale, struttura, enumerazione, registri, indicizzazione — **senza LLM, senza rete**, con
sole dipendenze stdlib. È la metà **D** del confine [[deterministic-vs-judgment|deterministico↔giudizio]]: il
*giudizio* (cosa scrivere, è una contraddizione?) resta al layer LLM, che consuma questi mattoni.

## Host-agnostico: tutta la specificità in `wiki.config.toml`

Non assume nulla dell'ospite: legge un **`WikiProfile`** (dataclass `frozen`, caricato via `tomllib` stdlib)
da `wiki.config.toml` — radice del wiki, file indice/log, tassonomia, `source_dirs`/`exclude`, lingua,
profilo (`code+doc`/`solo-doc`/`solo-code`), frontmatter atteso, ruoli, config RAG. **Nessun default è
hard-coded nei moduli.** Conseguenza diretta del **Principio X** ([[constitution]], [[mission-vision]]): lo
**stesso codice immutato** gira su qualunque progetto cambiando solo il file di config.

## Le operazioni (e i contratti JSON)

La CLI è `sertor-wiki-tools <op> [--config <path>] [--root <override>] [--json]`; con `--json` ogni
operazione emette un **contratto versionato** (`contracts.py`, dataclass puri), pensato per essere consumato
da hook/skill/agente senza parsing fragile.

| Operazione | Cosa fa (meccanico) | Contratto |
|---|---|---|
| `scan` | conta i file delle `source_dirs` più recenti dell'ultima voce di log (lavoro pendente; anchor su **mtime**, non git → vale su ospiti senza git; in **rotazione** l'anchor è la **partizione più recente**) | `wiki.scan/1` |
| `structure init` | crea tassonomia + index + log (idempotente, non-distruttivo) | `wiki.structure/1` |
| `validate` | frontmatter mancante + naming non kebab-case | `wiki.lint/1` |
| `lint` | wikilink rotti + pagine orfane + frontmatter + stub | `wiki.lint/1` |
| `collect` | enumera le pagine + metadati (path, area, type, title, tags, wikilink) **senza corpo** | `wiki.collect/1` |
| `index` | re-indicizza il wiki nel RAG (collezione isolata) **riusando la facade del core** (`build_indexer`, import **lazy** → le altre op restano offline) | `wiki.index/1` |
| `append-log` | appende una voce di log nel file del giorno (**rotazione** a un file per data); accetta il **corpo curato** dall'LLM e ne fa solo il piazzamento (idempotente) | `wiki.append_log/1` |
| `migrate` | splitta retroattivamente il log monolitico in partizioni giornaliere (una-tantum, idempotente, non distruttivo) | `wiki.migrate/1` |

**Write-back del log curato + rotazione (FEAT-008).** L'op `append-log` riceve il **corpo curato** dall'LLM
(formato [[deterministic-vs-judgment|log-craft]]) e ne fa solo il **piazzamento** nella partizione della
data, rigenerando l'indice delle partizioni di log (`update_log_index`) — confine deterministico↔giudizio
netto. Con `log_dir` configurato la rotazione è **implicita** (la voce va nel file della sua data); senza,
vale la modalità a file unico (back-compat). Il modulo `registry.py` espone *anche* `upsert_index`
(inserimento idempotente della riga link+sommario nell'indice globale `index.md`), ma **non è cablato in
un'op della CLI**: per ora la riga di `index.md` resta **LLM-authored** (backlog in [[architettura-wiki-llm]]).

## Proprietà di fondo

- **Idempotente** — identità di pagina = **path relativo POSIX**; rieseguire su input invariato dà output
  identico, zero duplicati.
- **Offline per costruzione** — solo stdlib (`tomllib`, `pathlib`, `re`, `json`, `dataclasses`, `datetime`);
  l'unico tocco di SDK pesante (Chroma) è nell'op `index`, importato lazy.
- **Errori espliciti** — config assente/malformata → `ConfigError` azionabile, mai `None` silenzioso.

## Chi lo consuma

`wiki_tools` è a sua volta esercitato da [[thin-consumer|consumatori sottili]]: l'hook
`wiki-pending-check.ps1` è un thin wrapper su `scan`; la skill/agente del wiki lo chiamano per il meccanico,
tenendosi il giudizio. Realizzato in **FEAT-003-D** (record datato: [[nucleo-wiki-deterministico-feat003d]]).

## Vedi anche
- Il confine che incarna: [[deterministic-vs-judgment]].
- La libreria di cui fa parte: [[retrieval-core]] (l'op `index` riusa la facade).
- L'architettura del wiki LLM che ci poggia sopra: [[architettura-wiki-llm]].
