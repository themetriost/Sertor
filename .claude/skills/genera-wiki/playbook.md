# Wiki Playbook — fonte unica del sistema wiki

> **Questo file è la fonte di verità del "sistema wiki".** Skill `genera-wiki`, comando `/wiki` e
> agente `wiki-keeper` non duplicano queste regole: le **leggono qui** e le seguono. Se modifichi una
> convenzione o un'operazione, modificala **solo** in questo file.
>
> È **tooling**, non contenuto del wiki: vive in `.claude/`, non va indicizzato né registrato nel wiki.

## 1. Identità & filosofia

Il wiki in `wiki/` è un **LLM Wiki** in stile Karpathy: *Obsidian è l'IDE, l'LLM è il programmatore,
il wiki è la codebase*. La conoscenza si **compila una volta** e si tiene aggiornata, invece di
ricostruirla a ogni sessione.

- **Doppio ruolo (DA-W1):** il wiki è insieme **corpus** (interrogabile via RAG) e **superficie**
  (indice navigabile iniettato a inizio sessione). Vedi `wiki/syntheses/ruolo-wiki-da-w1.md`.
- **Cumulativo:** cresce a ogni sessione; non si riparte da zero.
- **Idempotente:** se una pagina è già accurata, **non riscriverla**. Niente modifiche inutili.
- **Self-contained:** ogni pagina è scritta perché un agente la riprenda senza il contesto della chat.

## 2. Tassonomia (UNICA)

```
wiki/
├─ index.md        catalogo globale (link + summary di una riga). LEGGILO PER PRIMO.
├─ log.md          registro append-only di tutto ciò che facciamo
├─ concepts/       concetti (RAG, chunking, embeddings, ...)
├─ tech/           tecnologie e strumenti
├─ experiments/    una pagina per attività/esperimento di produzione
├─ sources/        riassunti di fonti esterne ingerite
└─ syntheses/      confronti e sintesi trasversali
```

- Queste sono le **uniche** cartelle. Non esistono `manual_edited/` né `ingested_sources/`: le fonti
  esterne ingerite vanno in **`sources/`** (vedi operazione `ingest`).
- `concepts/`, `experiments/`, `sources/` possono non esistere ancora: **creale on-demand** alla prima
  pagina della categoria. Non creare cartelle vuote o placeholder.
- Il **wiki del prototipo** (`prototype/wiki/`) è **congelato**: non si tocca, si consulta solo via MCP
  `sertor-rag`. Questo playbook riguarda solo `wiki/` di produzione.

## 3. Convenzioni

**Frontmatter YAML** in ogni pagina (eccetto i file append-only, vedi sotto):
```yaml
---
title: <titolo leggibile>
type: <concept|tech|experiment|source|synthesis|index>
tags: [<tag>, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["<path o URL>", ...]
---
```

- **Wikilink** `[[nome-pagina]]` (senza `.md`); alias con `[[nome-pagina|testo mostrato]]`. Mantieni i
  cross-reference aggiornati: una pagina nuova va linkata da `index.md` e dalle pagine correlate.
- **Naming** file: kebab-case descrittivo (`azure-ai-search.md`, `hybrid-search.md`).
- **Nuova vs aggiorna:** crea una pagina nuova per un concetto/entità nuovo; **aggiorna** quella
  esistente altrimenti. Una pagina per concetto reale, mai duplicati.
- **Contraddizioni:** quando una fonte/codice contraddice una pagina, **segnalalo esplicitamente** —
  non scegliere in silenzio. Se la contraddizione tocca una decisione o una fonte autorevole umana,
  **chiedi all'utente** invece di decidere.
- **Niente over-doc:** non documentare il banale o le modifiche meccaniche. Calibra al valore.

**File append-only** (`log.md`): **non** portano `updated` nel frontmatter (sarebbe sempre stale); il
loro stato è dato dall'ultima voce.

## 4. Operazioni

Ogni operazione = **input → passi → output** (pagine toccate + UNA voce di `log.md`). Le operazioni di
sola lettura/scrittura documentale (`record`, `ingest`, `query`, `lint`) sono eseguibili anche dal
`wiki-keeper` in background; `generate-from-diff` e `rag-sync` richiedono il **flusso principale** (vedi note).

### `record` — registra lavoro/decisione svolti
1. Leggi `index.md` e la coda di `log.md` per lo stato attuale.
2. Crea/aggiorna la/e pagina/e rilevante/i (`concepts/ tech/ experiments/ syntheses/`). Sintetizza il
   *perché* oltre al *cosa*.
3. Aggiorna i backlink e `index.md` (link + summary di una riga).
4. Appendi una voce di log `record`.

### `ingest` — acquisisci una fonte esterna
Input: un path locale (file/PDF) o un URL.
1. Acquisisci la fonte: `Read` per file/PDF locali; `WebFetch` per URL/PDF remoti. **Non modificare**
   la fonte originale.
2. Scrivi un riassunto in `sources/<slug>.md` con frontmatter (`sources:` = path/URL d'origine).
3. Integra/linka i concetti collegati nelle pagine `concepts/`/`tech/`; **segnala contraddizioni** con
   le pagine esistenti.
4. Aggiorna `index.md` e appendi una voce di log `ingest`.

### `query` — rispondi a una domanda sul wiki
1. Rispondi citando le pagine pertinenti.
2. Se l'esplorazione è preziosa e riusabile, **archiviala** come nuova pagina (le query si cumulano in
   conoscenza) e aggiorna `index.md` + voce di log `query`. Altrimenti nessuna scrittura.

### `lint` — verifica di coerenza (preferibilmente nel flusso principale: serve visione globale)
1. Inventario con `Glob` di `wiki/**/*.md`.
2. Segnala con `Grep`/lettura:
   - **frontmatter** mancante o incompleto;
   - **wikilink `[[x]]` non risolti** (cross-ref rotti: nessun file corrispondente);
   - **pagine orfane** (file non linkati da `index.md` né da altre pagine);
   - **claim potenzialmente superati/contraddittori** (es. `updated` vecchio rispetto alle `sources`, o
     affermazioni in conflitto tra pagine).
3. Produci un **report** + (opzionale) voce di log `lint`. **Non auto-correggere** di default: proponi
   e correggi solo su conferma dell'utente o se il brief lo richiede esplicitamente.

### `generate-from-diff` — aggiorna dalle modifiche recenti (flusso principale)
Evita di rileggere l'intero repo: aggiorna solo ciò che è cambiato.
1. **Delega al `configuration-manager`** un brief di sola lettura: «fornisci `git log` + `git diff`
   dal punto X». Ancora X = data dell'ultima voce di `log.md` (o l'ultimo commit che tocca `wiki/`).
   *(Anche `git log`/`diff` passano dall'agente: tutte le operazioni git sono delegate.)*
2. Col diff testuale ricevuto, aggiorna **solo** le pagine impattate dai cambiamenti.
3. Aggiorna `index.md` e appendi una voce di log `generate-from-diff` che cita il range di commit.

### `rag-sync` — re-indicizza il wiki nel RAG (flusso principale; NON il keeper)
Rende il wiki interrogabile via RAG (ruolo "corpus" di DA-W1). Richiede `sertor_core` importabile.
1. Esegui l'indexer su `wiki/` con corpus **isolato**, senza toccare il `.env` di produzione:
   ```powershell
   $env:SERTOR_CORPUS='wiki'   # isola dal corpus 'production'; RAG_BACKEND ereditato da .env (azure)
   # usa un interprete dove `import sertor_core` funziona (.venv-core oppure PYTHONPATH=src)
   .venv-core/Scripts/python.exe -c "from sertor_core import build_indexer; r=build_indexer().index('wiki', rebuild=True); print(r.documents, r.chunks)"
   ```
   `rebuild=True` = rebuild-from-scratch idempotente. Con `RAG_BACKEND=azure` il vector store è Azure
   AI Search e l'isolamento è la collezione `wiki__<provider>` (nessun indice Chroma locale).
2. Se `import sertor_core` non è disponibile, **fermati e segnala** (non fallire in silenzio).
3. Appendi una voce di log `rag-sync` con `documents`/`chunks` indicizzati.
4. **Costo:** con backend azure gli embeddings sono a pagamento. **Follow-up noto:** l'MCP
   `sertor-rag` punta oggi al prototipo (corpus `sertor`); interrogare il corpus `wiki` via MCP
   richiede un server dedicato — fuori da questo playbook.

## 5. Voce di log

Append a `wiki/log.md`, una voce per operazione, con la **data odierna**:
```
## [YYYY-MM-DD] <operazione> | <titolo>
- <bullet sintetici: pagine create/aggiornate, decisioni, esiti, commit se noti>
```
`<operazione>` ∈ `setup` · `record` · `ingest` · `query` · `lint` · `generate-from-diff` · `rag-sync`.

## 6. Limiti & deleghe

- **Git:** mai eseguirlo direttamente. Tutte le operazioni git (incluse le letture per
  `generate-from-diff`) si **delegano al `configuration-manager`**. Il `wiki-keeper` non esegue git.
- **Prototipo:** non toccare mai `prototype/` né le fonti originali date in input a `ingest`.
- **Quando NON documentare:** modifiche puramente meccaniche o di poco conto non meritano una voce.
- **Versionamento:** quando l'utente vuole versionare, delega al `configuration-manager` un commit
  `docs(wiki): <sommario>` con staging selettivo di `wiki/`.
