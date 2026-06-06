---
title: Mission, Vision e Principio X — Host-agnosticità come vincolo
type: concept
tags: [missione, visione, host-agnostico, principio-x, disaccoppiamento, costituzione]
created: 2026-06-05
updated: 2026-06-05
sources: ["README.md", ".specify/memory/constitution.md"]
---

# Mission, Vision e Principio X — Host-agnosticità come vincolo

## Cosa

Formalizzazione di Mission e Vision di Sertor nel nuovo [`README.md`](../../README.md) di radice,
accoppiata all'emendamento costituzionale che aggiunge il **Principio X** ("Capacità host-agnostiche")
come vincolo operativo. Questo documento lega i tre artefatti: il pitch pubblico (README) e il
vincolo architetturale (Principio X → [[costituzione-v1]]) che lo rende esecutivo.

## Vision: Il mondo che vogliamo

Estratto da [`README.md`](../../README.md):

> Ogni progetto software — che sia codice, documentazione, o entrambi — dovrebbe poter
> **conoscere e interrogare sé stesso**. La conoscenza di una codebase e dei suoi documenti smette
> di essere sparsa, volatile e ricostruita da zero a ogni sessione, e diventa un **asset vivo,
> persistente e auto-manutenuto**. E questo deve essere possibile **ovunque e senza lock-in**:
> portabile da un progetto all'altro, eseguibile in locale, neutrale rispetto al provider di LLM e
> di storage.

**Cosa significa:** la conoscenza non è un privilegi dei progetti grandi/enterprise; ogni progetto,
di qualsiasi forma (codice, doc, ibrido) deve poter *emergere a sé stesso* senza ricominciare ogni volta,
e senza dipendere da un fornitore specifico.

## Mission: Cosa costruiamo ora

Estratto da [`README.md`](../../README.md):

> Sertor è un **framework installabile** che dota **qualsiasi progetto** — *code+doc*, *solo-doc* o
> *solo-code* — di tre capacità componibili:
> 
> 1. **Indicizzazione repo-agnostica** dei contenuti (codice e documenti);
> 2. **Retrieval RAG** con più motori, da locale ad Azure;
> 3. un **LLM Wiki** cumulativo che cresce con il lavoro.
>
> Ogni capacità è **disaccoppiata dal dominio dell'ospite**: Sertor si aggancia a un progetto solo
> come *consumatore* — oggi a sé stesso, in modo strumentale, via **dogfooding**. È consegnato come
> **libreria importabile** (è quello il prodotto) — riproducibile e adatta a contesti di ogni scala,
> **enterprise inclusa** — mentre CLI e MCP ne sono veicoli sottili.

**Cosa significa:** Sertor non è un tool per un dominio specifico. È un'infrastruttura di
conoscenza *universale*, che si configura (non presume) sulla forma dell'ospite, e funziona in
egual misura su:
- un monorepo enterprise con decine di package
- un wiki standalone di conoscenza
- una libreria Python di poche cartelle
- il progetto Sertor stesso (dogfooding)

## Principio X: Il vincolo architetturale della portabilità

La Vision e la Mission richiedono un vincolo di design affinché non diventino aspirazioni pigre.
Il **Principio X** della Costituzione (`v1.1.0`, aggiunto il 2026-06-05) codifica questo:

### X. Capacità host-agnostiche (la portabilità è un vincolo, non un'aspirazione)

Estratto da [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md):

> Ogni capacità di Sertor — nucleo di retrieval, motori RAG, indicizzazione, skill LLM Wiki e gli
> strumenti che le orchestrano — MUST essere **disaccoppiata dal dominio e dalla struttura del progetto
> ospite**. L'ospite è un **consumatore**: si **configura**, non si **presume**. Il corpo di una
> capacità MUST NOT incorporare assunzioni specifiche di un progetto (percorsi fissi, nomi di dominio,
> struttura di cartelle dell'ospite); ciò che varia fra ospiti MUST vivere nella
> **configurazione/istanziazione**, non nel codice della capacità. Il **dogfooding** (Sertor applicato
> a sé stesso) è strumentale e MUST NOT essere usato come licenza per violare questo confine.
>
> **Test non-negoziabile:** una capacità MUST poter operare su un progetto-ospite diverso (code+doc,
> solo-doc, solo-code) senza modifiche al suo corpo — solo cambiando configurazione.

**Cosa significa in pratica:**
- Il motore RAG **non** conosce la cartella `src/` di Sertor; conosce il concetto universale di "documento".
- Una skill wiki **non** contiene riferimenti a `wiki/log.md` o `.claude/` come percorsi hardcoded;
  prende cartelle come parametri di istanziazione.
- Il playbook wiki [[sistema-wiki-fonte-unica]] (rules + operazioni) oggi è Sertor-coupled (parla di
  `wiki/`, `log.md`, agenti di Sertor); Principio X dice: "dovrà diventare parametrizzato all'ospite".

## Conseguenza operativa: Backlog di refactor

**Identificato il 2026-06-05:** le skill wiki, il playbook, e il rituale di step today violano il
Principio X (citano `wiki/`, `src/`, `log.md`, agenti nomati di Sertor).

**Azione differita (post-MVP):** quando la stack wiki sarà stabile (FEAT-003, FEAT-010 mergiate su `master`),
ri-parametrizzarla come una suite di skill *host-agnostiche*:

1. **Skill wiki (refactor):** invece di scrivere in `wiki/syntheses/`, leggere il percorso da brief/config.
2. **Playbook (refactor):** separare le regole universali (frontmatter, operazioni record/ingest/query)
   da quelle specific di Sertor (path `wiki/`, log `.md`, agenti).
3. **Rituale di step (refactor):** il "default fai" e la lint semantica restano principi universali;
   l'invocazione ("chi chiama le skill?") e la delega ("quale agente?") diventano parametri dell'ospite.

**Ispirazione:** le skill di Transcriptio (`C:\Workspace\Git\Transcriptio\.claude\skills/`) già
implementano pattern parametrizzati — si copia da lì.

**Non è un difetto:** è un aspetto naturale dell'evoluzione di uno strumento: MVP tight su
un'istanza (Sertor), follow-up di generalizzazione (Sertor come framework davvero portabile).
La testata nel Principio X ora impedisce che il dogfooding diventi lock-in silenzioso.

## Allineamento

- **[[costituzione-v1]]** — il nuovo Principio X e la versione v1.1.0 sono autorità di design.
- **[[rituale-step-e-allineamento-wiki]]** — il lint semantico di allineamento dovrà comprendere
  "questa skill/capacità contiene assunzioni hardcoded sull'ospite?" come nuova domanda.
- **README.md** — fonte di verità della Vision e della Mission; questa pagina sintesi rimanda.

## Riferimenti

- **Costituzione:** [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.1.0,
  Principio X, ratificato 2026-06-05.
- **README.md:** [`README.md`](../../README.md) (Vision/Mission, sezione "Disaccoppiamento").
- **Ispirazioni esterne:** skill di Transcriptio (pattern di parametrizzazione), Clean Code + Clean
  Architecture.
