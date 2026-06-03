# Phase 0 — Research: Skill LLM Wiki (creare/indicizzare)

Decisioni tecniche per FEAT-003. Formato: **Decisione / Razionale / Alternative**. Ancoraggio:
`prototype/wiki/`, `.claude/agents/wiki-keeper.md`, `prototype/shared/loaders.py` (load_docs su wiki),
e l'interfaccia di FEAT-001/002 (in `master`).

---

## R1 — La skill come insieme di operazioni su file; l'indicizzazione riusa il nucleo (DRY)

**Decisione.** Sottopacchetto `sertor_core/wiki/` con operazioni pure sul filesystem (create, record,
ingest, distill) e una `index_wiki()` che **delega** a `IndexingService(rebuild=True)` del nucleo
puntandolo sulla radice del wiki. Nessuna logica di ingestione/chunking/embeddings/store viene
riscritta.

**Razionale.** REQ-040/041: indicizzare il wiki = indicizzare un corpus di Markdown → è esattamente
ciò che il nucleo fa già (discover → chunk markdown → embed → upsert). Il dogfooding del prototipo
(`load_docs` include `wiki/`) conferma il pattern. DRY (Principio III): la skill è un consumatore.

**Alternative.** (a) Reimplementare l'indicizzazione nella skill: viola §4/DRY → respinta. (b) Pacchetto
separato: le skill wiki sono core per costituzione → dentro `sertor_core`.

---

## R2 — Porta `LLMProvider` per la distillazione (nuovo boundary, solo Gruppo D)

**Decisione.** Aggiungere una porta `LLMProvider` (Protocol) con `generate(prompt, system=None) -> str`
e adapter `adapters/llm/{ollama,azure}.py` (chat via `httpx`, come gli embeddings). `build_llm(settings)`
nel composition root. La **distillazione** riceve un `LLMProvider`; se assente solleva
`LLMNotConfiguredError` (REQ-031). Tutte le altre operazioni sono **LLM-free**.

**Razionale.** REQ-030/031: la distillazione richiede generazione. Principio II: l'LLM è una dipendenza
esterna → dietro un'astrazione di Sertor. È il primo uso di un LLM nel core (FEAT-001/002 non ne avevano
bisogno); la porta è minimale (un solo metodo) per non over-ingegnerizzare (Principio III). Mockabile
con `FakeLLM` nei test.

**Alternative.** (a) Chiamare direttamente un SDK LLM nella skill: viola Principio I/II → respinta.
(b) Porta ricca (streaming, tool-calling): YAGNI per la distillazione MVP → respinta, estendibile poi
(FEAT-006 agentico la amplierà).

---

## R3 — Idempotenza strutturale: scrivere solo se il contenuto cambia (REQ-050/013, SC-002)

**Decisione.** Le operazioni sono **idempotenti per struttura**: prima di scrivere una pagina si
calcola il contenuto atteso e lo si confronta con quello su disco; se identico → **no-op** (nessuna
riscrittura, nessuna voce di log, nessun aggiornamento indice). `index.md` e `log.md` si aggiornano
**solo** quando una pagina è effettivamente creata/cambiata. Il `created` nel frontmatter è preservato
sulle pagine esistenti; `updated` cambia solo a contenuto modificato. La data è un parametro
(`today`, default = data odierna) per rendere deterministico il test nello stesso giorno.

**Razionale.** REQ-050 ("nessun file nuovo, nessuna voce duplicata, nessun timestamp modificato su file
invariati") e SC-002 (hash invariato). Confrontare il contenuto prima di scrivere è il modo robusto per
garantirlo senza dipendere dai timestamp del filesystem. La distillazione fa eccezione (R-W2): è
idempotente sulla *struttura* (no pagina/voce duplicata), non sul *contenuto generato* dall'LLM.

**Alternative.** (a) Riscrivere sempre e deduplicare il log a posteriori: fragile, cambia i timestamp →
respinta. (b) Hash di contenuto come id: il path relativo è già id stabile (REQ-051) → non serve.

---

## R4 — `create_wiki` non distruttivo (REQ-001/002)

**Decisione.** `create_wiki(root)` crea cartelle tematiche (`concepts/`, `tech/`, `experiments/`,
`sources/`, `syntheses/`) e `index.md`/`log.md` con contenuto minimo valido **solo se assenti**. Se
`index.md`/`log.md` esistono → lasciati intatti (non sovrascritti né troncati). Le cartelle mancanti
vengono create comunque (idempotente: `mkdir` se assente). Struttura **fissa** (DA-W6).

**Razionale.** REQ-002 (non sovrascrivere) + REQ-001 (creare se assente). La struttura è quella del
prototipo/`CLAUDE.md` (DA-W6 risolta: fissa nell'MVP).

**Alternative.** Template configurabile: post-MVP, solo se un 2° repo lo richiede (DA-W6) → respinta ora.

---

## R5 — record / ingest: brief strutturato dall'agente (DA-W2)

**Decisione.** `record(root, brief)` e `ingest(root, source)` accettano un **brief già strutturato**
(non linguaggio naturale grezzo): `Brief(title, kind, body, tags, sources)` dove `kind` ∈ aree
tematiche. `record` crea/aggiorna la pagina del tema (dedup per path derivato dal titolo+kind),
aggiorna `index.md` (link + sommario) e appende **una** voce a `log.md`. `ingest` crea/aggiorna una
pagina in `sources/`, **propaga** un riferimento nelle pagine correlate esistenti indicate dal brief, e
**marca le contraddizioni** esplicitamente segnalate dal chiamante (REQ-023).

**Razionale.** DA-W2: l'attore primario è l'agente LLM, che fornisce un brief condensato; la skill non
interpreta NL grezzo. La rilevazione di contraddizioni spetta all'agente (che conosce il contesto): la
skill le *marca* quando il brief le dichiara (`contradicts=[(page, nota)]`).

**Alternative.** (a) Auto-detect contraddizioni: richiederebbe LLM/semantica e non è nell'MVP → respinta.
(b) Parsing NL grezzo: fuori ambito (DA-W2/DA-W3) → respinta.

---

## R6 — Indicizzazione: full rebuild, abort su RAG non raggiungibile, identità = path (REQ-040..045/051)

**Decisione.** `index_wiki(wiki_root, settings)` costruisce embedder+store dal nucleo e chiama
`IndexingService(...).index(wiki_root, rebuild=True)` → full rebuild idempotente (DA-W4). I chunk del
wiki hanno `doc_type=doc`, `chunker=markdown` (già dal nucleo) e id = path relativo (REQ-051, già nel
nucleo). Radice vuota/senza Markdown → warning + indice immutato (REQ-045). Store irraggiungibile →
`VectorStoreError` propagato (abort senza corrompere, REQ-043). Peso paritario: nessun boost (REQ-044,
il nucleo non applica boost di default).

**Razionale.** Riuso diretto del nucleo (R1). Le proprietà richieste (rebuild idempotente, id stabile,
errore esplicito, peso paritario) sono già garantite da FEAT-001/002 — la skill le eredita.

**Alternative.** Incrementale: post-MVP (DA-W4) → respinta. Collezione/metadati "wiki" dedicati: l'MVP
indicizza il wiki come corpus doc paritario; un marcatore `wiki` è additivo e opzionale.

---

## R7 — Sandbox dei test (RNF-002, R-W5)

**Decisione.** Tutti i test operano su un **wiki temporaneo** (`tmp_path`), mai sul `wiki/` di
produzione. Fixture `wiki_sandbox` che crea una radice vuota in temp. Distillazione con `FakeLLM`
deterministico; indicizzazione con `FakeEmbedder`+`InMemoryStore`/`ChromaStore` su temp.

**Razionale.** R-W5: eseguire test di idempotenza sul wiki reale lo altererebbe. RNF-002: isolamento.

---

## Sintesi NEEDS CLARIFICATION risolti

| Tema | Risolto in | Esito |
|------|-----------|-------|
| Indicizzazione del wiki | R1/R6 | riuso `IndexingService(rebuild=True)` sul wiki root |
| Generazione per distill | R2 | porta `LLMProvider` + adapter (solo distill) |
| Idempotenza strutturale | R3 | scrivere solo se il contenuto cambia; data parametrica |
| create non distruttivo | R4 | crea se assente, non sovrascrive index/log |
| record/ingest input | R5 | brief strutturato; contraddizioni marcate dal chiamante |
| abort/peso/identità RAG | R6 | ereditati dal nucleo (errore esplicito, id=path, no boost) |
| isolamento test | R7 | wiki sandbox in temp, FakeLLM |

Tutti i NEEDS CLARIFICATION tecnici sono risolti → si procede alla Phase 1.
