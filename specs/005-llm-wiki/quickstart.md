# Quickstart — LLM Wiki end-to-end (FEAT-010)

## 1. Setup (una volta per repo)
```bash
sertor wiki init .                         # struttura + binding del trigger al commit (+ ingest iniziale opz.)
sertor wiki init . --ingest docs/external  # con popolazione iniziale di ingested_sources/
```
Da qui in poi un **commit** innesca la generazione incrementale (binding installato).

## 2. Generazione al commit (automatica) / on-demand
```bash
# automatica: al commit, il configuration-manager invoca la generazione sul changeset (stesso commit)
sertor wiki generate .                     # on-demand (full o incrementale a seconda dello stato)
```
```python
from sertor_core.wiki.generation import generate
from sertor_core.composition import build_llm, build_facade
from sertor_core.adapters.git import SubprocessGitAdapter

rep = generate("wiki", build_llm(), sources=settings.wiki_sources,
               git=SubprocessGitAdapter("."), facade=build_facade())
print(rep.mode, rep.pages_written, rep.fallbacks)
```

## 3. Ingest di documentazione esterna (input non versionato)
```bash
sertor wiki ingest . docs/papers/retrieval.md   # importa in ingested_sources/ (import, NON compila)
```
La compilazione in concetti avviene poi in **generazione** (le pagine derivate citano la fonte; il
riferimento non è indicizzato).

## 4. Retrieval (query via RAG, collezioni separate)
```bash
sertor wiki index .                        # indicizza il wiki generato (collezione separata)
sertor search "perché abbiamo scelto le collezioni separate"   # ritorna wiki + codice
```
Gli input (`manual_edited/`, `ingested_sources/`) **non** compaiono: ricevi i **concetti compilati**.

## 5. Manutenzione + gate al commit
```bash
sertor wiki lint .                         # link rotti, orfani, copertura
sertor wiki gate . --threshold high        # incrementale: lint + freschezza; blocked → exit≠0
sertor wiki gate . --override --reason "hotfix"   # procede e REGISTRA l'override
```
Al commit, se ci sono problemi sopra soglia, il gate **blocca**, **avvisa** e **propone soluzioni**
(inclusa "ignora e committa").

## 6. Progetto senza codice
Tutto funziona con le sole fonti documentali (`manual_edited/`, `ingested_sources/`, log): generazione,
retrieval e manutenzione non assumono la presenza di codice.

## Verifica (accettazione)
| Verifica | Atteso | Criterio |
|----------|--------|----------|
| commit su N file | generazione limitata alle pagine del changeset | SC-001 |
| query | wiki generato + codice; input assenti | SC-002/003 |
| gate sopra soglia | blocca/avvisa/propone; override registrato | SC-004 |
| repo senza codice | funziona con fonti documentali | SC-005 |
| re-run invariato | esito identico | SC-006 |
| operazione on-demand | skill + CLI + MCP | SC-007 |
| post `wiki init` + commit | generazione scatta | SC-008 |
| pagina contraddetta dal codice/decisione | obsoleta | SC-009 |
| ingest | popola ingested_sources, no riassunti | SC-010 |
