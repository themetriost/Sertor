---
title: Mission, vision & Principle X (host-agnosticity)
type: concept
tags: [missione, visione, host-agnostico, principio-x, principio-xi, disaccoppiamento, costituzione]
created: 2026-06-05
updated: 2026-06-15 (allineato Costituzione v1.2.0 — Principio XI consumo via vehicles) · 2026-06-13 (+ sezione "Posizionamento: retrieval tool per agenti" — generate=agente, serve=MCP delegati per design; fronte competitivo = precisione/confidenza/freschezza; wiki = generazione precalcolata)
sources: ["README.md", ".specify/memory/constitution.md"]
---

# Mission, vision & Principle X (host-agnosticity)

La **missione** e la **visione** di Sertor — col **Principio X** (host-agnosticità) che ne discende come
vincolo non negoziabile — definiscono *cosa* costruisce il progetto e *perché*: un framework di retrieval
+ wiki **installabile su qualsiasi progetto**, senza lock-in sull'ospite.

## Cosa

Formalizzazione di Mission e Vision di Sertor nel nuovo [`README.md`](../../README.md) di radice,
accoppiata all'emendamento costituzionale che aggiunge il **Principio X** ("Capacità host-agnostiche")
come vincolo operativo. Questo documento lega i tre artefatti: il pitch pubblico (README) e il
vincolo architetturale (Principio X → [[constitution]]) che lo rende esecutivo.

## Vision: Il mondo che vogliamo

Estratto da [`README.md`](../../README.md):

> Ogni progetto software — che sia codice, documentazione, o entrambi — dovrebbe poter
> **conoscere e interrogare sé stesso**. La conoscenza di una codebase e dei suoi documenti smette
> di essere sparsa, volatile e ricostruita da zero a ogni sessione, e diventa un **asset vivo,
> persistente e auto-manutenuto**. E questo deve essere possibile **ovunque e senza lock-in**:
> portabile da un progetto all'altro, eseguibile in locale, neutrale rispetto al provider di LLM e
> di storage.

**Cosa significa:** la conoscenza non è un privilegio dei progetti grandi/enterprise; ogni progetto,
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
  legge il profilo dell'ospite (`wiki.config.toml`) come unica fonte di specificità.
- Il nucleo di retrieval si configura via `Settings` (corpus, backend, esclusioni): cambiare ospite è un
  atto di configurazione, non di codice.

## Come il principio è stato reso esecutivo

Il vincolo, identificato il 2026-06-05, è stato **chiuso a strati** invece che restare backlog:

1. **Skill e playbook wiki** — resi host-agnostici col **ponte D→N** (2026-06-05, PR #14): playbook,
   skill `wiki-author`, comando `/wiki` e agente `wiki-curator` leggono `wiki.config.toml`; il meccanico è
   delegato alla CLI `sertor-wiki-tools`. Vedi [[ponte-d-n-host-agnostico]] e [[architettura-wiki-llm]].
2. **Nucleo deterministico** — `wiki_tools` (FEAT-003-D) nasce host-agnostico per costruzione: zero path
   dell'ospite nel corpo, tutto dal profilo. Vedi [[wiki-tools]].
3. **Rituale di step** — il *principio* (registra/distilla/lint/…) è universale; l'**istanza** operativa
   vive in `CLAUDE.md` come fonte unica *deliberata* (vedi [[step-ritual]]): un'azione standing deve stare
   nell'unico asset garantito in contesto. La ri-esportazione come plugin portabile è il solo pezzo
   **differito** (quando il rituale sarà stabile).

Ogni nuova capacità passa dal **gate Principio X** del Constitution Check (es. la manopola
`extra_corpora` della query congiunta è *generica*, non "wiki": il caso dogfood vive solo nella config).

**Non è mai stato un difetto:** è l'evoluzione naturale di uno strumento — MVP tight su un'istanza
(Sertor), generalizzazione come vincolo costituzionale. Il Principio X impedisce che il dogfooding
diventi lock-in silenzioso.

## Posizionamento: retrieval tool per agenti, non app RAG end-to-end

Un equivoco ricorrente è leggere Sertor come *"un'app RAG a cui mancano due fasi"*. Il framing corretto
è un altro: Sertor è una **forma diversa** — un **retrieval tool per agenti** — in cui le fasi di una
pipeline RAG completa (`retrieve → generate → serve`) **esistono tutte**, ma due sono **delegate per
design**, non assenti.

- **GENERATE = l'agente.** La sintesi della risposta in linguaggio naturale (prompt → LLM → risposta
  citata, con grounding/abstention) la fa l'**agente frontier** che consuma Sertor via MCP. Cablare un
  LLM generativo dentro la libreria sarebbe **ridondante e peggiore**: duplicheremmo (male) ciò che
  l'agente già fa benissimo. È la scommessa del **RAG agentico composito** (FEAT-006 ✅ in forma
  composita): il miglior generatore è un agente esterno, non un LLM cablato.
- **SERVE = MCP.** Il protocollo **MCP è il livello di serving** — il modo standard con cui un agente
  invoca lo strumento. Non è un endpoint HTTP pubblico multi-tenant perché il "client" non è internet
  ma **l'agente sulla stessa sessione/macchina**: auth/rate-limit/multi-tenant risolverebbero un
  problema che non abbiamo.

**Quindi non fare generate/serve NON è un limite:** è la scelta di essere *il miglior retriever per
agenti* invece di *un'app RAG mediocre ma completa*. Il fronte competitivo reale — dove il prodotto
vince o perde — **non** è generate/serve, ma la **qualità di ciò che si restituisce all'agente**:

1. **Precisione/recall dei chunk** — il pezzo giusto fa brillare l'agente, il rumore lo fa allucinare.
   È il perché di chunking-AST ([[chunking-dispatch]]), ibrido+reranking ([[hybrid-retrieval]]),
   code-graph ([[code-graph]]).
2. **Segnale di confidenza** — oggi si restituisce top-k *sempre*: l'agente non sa *quando* il
   retrieval è debole, quindi non sa quando astenersi. È l'unico buco che indebolisce il grounding
   *dentro* il modello composito → Must in `requirements/sertor-core/hardening-produzione/`.
3. **Freschezza** — un indice stantio serve all'agente contesto non reale: è letteralmente l'essenza
   *"contesto dell'agente sempre reale"* (retry, cache, refresh incrementale; vedi [[dogfooding]]).

Questi tre — non generate/serve — sono il terreno di gioco. I gap reali sono tracciati e prioritizzati
in `requirements/sertor-core/hardening-produzione/` (dal RAG audit 2026-06-13).

### Dove si colloca il wiki

Il wiki è **generazione precalcolata**: la distillazione che un'app e2e farebbe *a query-time* (pagando
token a ogni richiesta), Sertor la fa **offline e una volta sola** e la persiste come documentazione
indicizzabile (`doc_type=doc`). In termini di retrieval è **contesto ad altissimo segnale/rumore** — il
codice dice *cosa fa*, il wiki dice *perché* ed espone l'astrazione giusta — ed è **memoria cumulativa
tra sessioni**. Non è una fase a parte: è una sorgente di **prima classe dentro il corpus** e il
**moltiplicatore di precisione** del retriever. Dettaglio in [[wiki-role-da-w1]].

## Allineamento

- **[[constitution]]** — il nuovo Principio X e la versione v1.1.0 sono autorità di design.
- **[[step-ritual]]** — il lint semantico di allineamento dovrà comprendere
  "questa skill/capacità contiene assunzioni hardcoded sull'ospite?" come nuova domanda.
- **README.md** — fonte di verità della Vision e della Mission; questa pagina sintesi rimanda.

## Riferimenti

- **Costituzione:** [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.2.0,
  Principio X (host-agnostico, 2026-06-05), Principio VII chiarito su nesting/SESE (2026-06-14),
  Principio XI (consumo via vehicles, 2026-06-15).
- **README.md:** [`README.md`](../../README.md) (Vision/Mission, sezione "Disaccoppiamento").
- **Ispirazioni esterne:** skill di Transcriptio (pattern di parametrizzazione), Clean Code + Clean
  Architecture.
