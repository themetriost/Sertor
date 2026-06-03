# Prompt per generare il PowerPoint di Sertor

> Copia tutto il blocco qui sotto e incollalo nello strumento che genera le slide.

---

Sei un esperto di presentazioni tecniche. Crea una **presentazione PowerPoint (.pptx) in italiano**,
formato 16:9, ~15 slide, per raccontare il progetto **Sertor** a un **team tecnico interno**
(sviluppatori e architetti che non conoscono il progetto). Tono: chiaro, concreto, professionale;
poche parole per slide, niente muri di testo; elenchi puntati brevi. Dove indicato, crea
**slide-diagramma** con shape native (non immagini esterne). Palette: blu `#2D6CDF`, verde
`#1E8E3E`, ambra `#B86E00`, grigio `#5F6B7A`, testo scuro `#1F2A44`, sfondi chiari. Ogni slide ha un
titolo. Restituisci un file `.pptx` scaricabile.

**Tema portante da far emergere in tutta la presentazione:** in un progetto **la verità vive in due
posti — i SORGENTI (come funziona) e la DOCUMENTAZIONE (il perché/le decisioni)** — storicamente
separati e divergenti. Sertor li fa **coesistere in un unico corpus interrogabile**; inoltre la
**documentazione nuova nasce e vive accanto ai sorgenti** grazie alla skill **LLM Wiki** (pagine
Markdown versionate col codice e indicizzate nello stesso RAG).

Struttura e contenuti (uno slide per blocco, salvo dove indicato):

**1. Cover** — Titolo "Sertor"; sottotitolo "Framework RAG enterprise — dal prototipo alla
produzione"; piè: "Repo-agnostico · local-first ↔ cloud · libreria + CLI + MCP · governance SpecKit".

**2. Cos'è Sertor** (slide chiave)
- In una frase: un **motore di ricerca semantica per il tuo progetto** (codice + documentazione), portabile e governato.
- **Una sola verità interrogabile**: unifica **codice** (com'è fatto) e **documentazione** (perché/decisioni) in un unico corpus, e **cita sempre la fonte** (file).
- Indicizza un repository e recupera i passaggi più pertinenti a una domanda in linguaggio naturale (RAG = Retrieval-Augmented Generation; Sertor copre la parte di **retrieval**).
- Tre capacità: nucleo di retrieval riusabile · motori RAG (baseline ora; ibrido/grafo/agentico) · **skill LLM Wiki** (la conoscenza distillata).
- Come si usa: **libreria Python · CLI `sertor` · strumento per agenti LLM (MCP)**.
- Cosa NON è: non è un chatbot né un LLM proprio; **non produce la risposta finale** — fornisce il contesto.

**3. Una sola verità: sorgenti + documentazione coesistono** (SLIDE-DIAGRAMMA — concetto chiave)
- Messaggio: la verità di un progetto è **doppia** — i **sorgenti** dicono *come funziona*, la **documentazione** dice *perché*. Di solito stanno separati e divergono.
- Sertor li indicizza **insieme** in **un unico corpus**, con **peso paritario** (nessuna fonte privilegiata) e citazione del file. Si interroga con `search_code` (codice), `search_docs` (documentazione/wiki), `search_combined` (entrambi).
- La **documentazione nuova vive accanto ai sorgenti** grazie alla **skill LLM Wiki**: crea/aggiorna pagine Markdown **dentro il repo** (versionate col codice) e le indicizza nello stesso RAG → niente knowledge base separata che diverge; il **"perché" è recuperabile insieme al "come"**.
- Diagramma suggerito: tre riquadri sorgente — **[Codice]**, **[Documentazione esistente]**, **[Wiki LLM — il "perché"]** — che convergono con frecce in un unico riquadro **[Corpus interrogabile]**, da cui escono i tre tool **search_code / search_docs / search_combined**.

**4. Il problema & la visione**
- La conoscenza del progetto (codice + decisioni) si disperde e si ricostruisce ogni volta; doc e codice divergono.
- Obiettivo: portare questa capacità su **qualunque** repository, riproducibile e production-grade.
- Local-first ↔ cloud via **configurazione** (no lock-in); testabile e **misurabile**.

**5. Atto 1 — L'esperimento (prototipo, ora congelato)**
- 4 modalità RAG su corpus FastAPI: **baseline vettoriale · ibrido (BM25+dense+reranking) · GraphRAG · agentico**.
- Local-first (Ollama+Chroma) + variante Azure (OpenAI + AI Search).
- ✅ Fattibilità dimostrata. ⚠️ Ma esplorativo, accoppiato al corpus, senza test, non riusabile.
- Lezione → rifarlo a qualità di produzione, repo-agnostico e testato.

**6. Atto 2 — La svolta: governance**
- **Costituzione di progetto (v1.0.0): 9 principi vincolanti** (core a dipendenze verso l'interno; errori espliciti; idempotenza; config centralizzata; osservabilità; …).
- **Pipeline SpecKit** per ogni feature: requirements (EARS) → spec → plan (Constitution Check) → tasks → analyze → implement.
- **Clean Architecture**: dominio puro ← servizi/adapter; provider intercambiabili dietro **porte**. Branch + PR + test.

**7. SLIDE-DIAGRAMMA — Architettura (Clean Architecture)**
- 5 strati impilati con freccia laterale "dipendenze → verso l'interno":
  1. **Consumatori**: CLI `sertor` · Server MCP
  2. **Composition root**: wiring da configurazione (.env)
  3. **Adapters**: Ollama/Azure (embeddings, LLM) · Chroma/Azure AI Search (vector store)
  4. **Services / Engines / Wiki**: ingestione · chunking · indexing · retrieval · baseline · **wiki**
  5. **Domain (cuore)**: entità · porte (EmbeddingProvider, VectorStore, LLMProvider) · errori — **nessun SDK esterno**
- Nota: "Il core non importa SDK di provider né la CLI; gli adapter dipendono dalle astrazioni; il wiring sta nel composition root."

**8. Atto 3 — Stato attuale: cosa funziona oggi**
- **MVP del core completo e in produzione** (`master`): Nucleo di retrieval · Motore RAG baseline · **Skill LLM Wiki (crea + indicizza)**.
- **CLI `sertor`**: `index` / `search` / **`wiki index`** + osservabilità (log strutturati, JSON, appender Splunk).
- **Server MCP** sul motore nuovo: un agente LLM (Claude) interroga Sertor — codice **e** documentazione/wiki — come strumento.
- **Dogfooding di produzione**: indicizzato **Sertor stesso** su Azure + Chroma; sorgenti, spec e **pagine wiki** nello stesso corpus.
- Il dogfooding reale ha **scovato 4 bug** invisibili ai test con mock → corretti con regressioni.

**9. SLIDE KPI** (griglia di 6 card, numero grande + etichetta)
- **3 / 3** Must del core completi · **108** test verdi (+2 xfail) · **9** PR mergiate · **147 / 1226** documenti / chunk (sorgenti **+** doc **+** wiki) · **9 / 9** principi di Costituzione · **4** bug trovati dal dogfooding.

**10. Atto 4 — SLIDE-DIAGRAMMA: Roadmap (3 colonne)**
- ✓ Fatto (verde): Nucleo (FEAT-001) · Baseline (FEAT-002) · **Skill LLM Wiki (FEAT-003)** · CLI `sertor` · Server MCP · Dogfooding Azure.
- ▶ Prossimo/Should (blu): RAG ibrido+reranking (FEAT-004) · RAG a grafo/GraphRAG (FEAT-005) · RAG agentico (FEAT-006) · **Manutenzione wiki (FEAT-007)** · CLI install selettivo.
- ◌ Dopo/Could-Won't (grigio): **Arricchimento bidirezionale Wiki↔RAG (FEAT-008)** · Refresh incrementale (FEAT-009) · CLI wizard config · Distribuzione PyPI.

**11. Questioni aperte & come contribuire**
- Aperte (per scelta): fissare le **soglie di pertinenza** su un ground-truth reale; promuovere **PowerShell / SQL** da chunking di fallback a sintattico.
- Uso (team): `uv pip install -e .` → comando `sertor`; oppure tool MCP `search_code/docs/combined` in Claude.
- Ogni nuova capacità segue la stessa pipeline SpecKit, sotto Costituzione.

**12. Chiusura / take-aways**
- **Una sola verità interrogabile**: codice + documentazione (+ wiki) coesistono nello stesso corpus; il **"perché" vive accanto al "come"**, versionato e indicizzato.
- MVP del core completo, in produzione e **dogfoodato su sé stesso**, esposto via CLI e MCP.
- Prossimo passo ad alto valore: **GraphRAG (FEAT-005)** o **ibrido+reranking (FEAT-004)**.

Linee guida finali:
- Coerenza visiva (stessi colori/famiglia font su tutte le slide); usa ✓ ▶ ◌ ⚠️ con parsimonia per gli stati.
- Le slide-diagramma (3, 7, 9, 10) devono essere **editabili** (shape, non immagini).
- Output: un file `.pptx` 16:9 scaricabile.
