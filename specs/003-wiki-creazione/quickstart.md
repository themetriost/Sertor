# Quickstart — Skill LLM Wiki (creare/indicizzare)

Come usare la skill come libreria. Riflette il design ([plan.md](plan.md)); i percorsi sono il layout
target.

## 1. Inizializzare la struttura del wiki

```python
from sertor_core.wiki.structure import create_wiki

create_wiki("C:/path/al/repo/wiki")   # crea cartelle tematiche + index.md/log.md (se assenti)
```

Non sovrascrive un wiki esistente (i contenuti restano intatti). Reinvocabile senza effetti.

## 2. Documentare in continuo (record)

```python
from sertor_core.wiki.operations import record
from sertor_core.wiki.conventions import Brief

record("C:/path/al/repo/wiki", Brief(
    title="Decisione su X",
    kind="synthesis",                 # → wiki/syntheses/decisione-su-x.md
    body="Abbiamo scelto X perché ...",
    tags=["decisione", "architettura"],
    sources=["specs/003-.../spec.md"],
))
```

Crea/aggiorna la pagina, aggiunge il link in `index.md` e **una** voce in `log.md`. Reinvocato con lo
stesso input su wiki invariato → **no-op** (nessun duplicato, hash file invariato).

## 3. Ingerire una fonte esterna (ingest)

```python
from sertor_core.wiki.operations import ingest
from sertor_core.wiki.conventions import SourceBrief

ingest("…/wiki", SourceBrief(
    title="Paper su retrieval ibrido",
    summary="Il paper mostra che ...",
    reference="https://example.org/paper",
    related=["concepts/hybrid-search"],          # propaga il riferimento
    contradicts=[("concepts/baseline", "il paper contraddice Y")],  # marca la contraddizione
))
```

## 4. Distillare una conversazione (richiede LLM)

```python
from sertor_core.wiki.distill import distill
from sertor_core.composition import build_llm
from sertor_core.wiki.conventions import Brief

distill("…/wiki", Brief(title="Sessione design FEAT-003", kind="experiment", body="<brief condensato>",
                        tags=["sessione"], sources=[]), llm=build_llm())
```

Senza un LLM configurato → `LLMNotConfiguredError` esplicito. L'input è un brief **già condensato**
(non una trascrizione grezza).

## 5. Indicizzare il wiki nel RAG

```python
from sertor_core.wiki.indexing import index_wiki

report = index_wiki("C:/path/al/repo/wiki")     # full rebuild, riusa il nucleo
print(report.documents, report.chunks)
```

Le pagine del wiki entrano nel corpus documentale come **corpus paritario** (nessun boost). Poi sono
interrogabili come gli altri doc:

```python
from sertor_core import build_facade
build_facade().search_docs("cosa abbiamo deciso su X")   # restituisce anche pagine del wiki
```

RAG irraggiungibile → errore esplicito senza corrompere l'indice. Radice vuota → warning, indice
immutato.

## 6. Verifica rapida (accettazione)

| Verifica | Atteso | Criterio |
|----------|--------|----------|
| create su repo senza wiki | struttura completa in 1 invocazione | SC-001 |
| seconda invocazione invariata | file identici (hash), nessun duplicato | SC-002 |
| record/ingest | indice riflette le pagine, log ha la voce | SC-003 |
| index_wiki + query doc | la query trova pagine del wiki | SC-004 |
| 2 repository diversi | funziona senza modifiche | SC-005 |
| ogni operazione | log strutturato con esito | SC-006 |
