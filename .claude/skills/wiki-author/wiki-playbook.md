# Wiki Playbook — fonte unica del sistema wiki

> **Questo file è la fonte di verità del "sistema wiki".** La skill `wiki-author`, il comando `/wiki` e
> l'agente `wiki-curator` non duplicano queste regole: le **leggono qui** e le seguono. Se modifichi una
> convenzione o un'operazione, modificala **solo** in questo file.
>
> È **tooling**, non contenuto del wiki: vive in `.claude/`, non va indicizzato né registrato nel wiki.

## 0. Host-agnostico: l'ospite si configura, non si presume

La capacità wiki è **disaccoppiata dal progetto-ospite** (Principio X della costituzione). Tutto ciò che
varia tra progetti vive in **`wiki.config.toml`** alla radice dell'ospite — **unica fonte di specificità**:

| Chiave config | Cosa definisce |
|---|---|
| `root`, `index_file`, `log_file` | dove vive il wiki e i suoi due file speciali |
| `[[taxonomy]]` | le aree logiche (cartella → tipo frontmatter) |
| `frontmatter_required` / `_optional` | i campi di frontmatter attesi |
| `source_dirs`, `exclude` | da dove leggere il lavoro dell'ospite e cosa ignorare |
| `[roles]` | i nomi degli agenti: `curator` (questo wiki), `vcs` (git) |
| `[rag]`, `[strings]`, `language` | corpus RAG, messaggi localizzati, lingua |

**Non assumere `wiki/`, `src/`, nomi di cartelle o di agenti**: leggili dalla config. Gli esempi concreti
qui sotto (`wiki/`, `concepts/`, `src/`…) sono il **profilo Sertor** usato in dogfooding, **non** leggi
universali. Su un altro progetto cambia solo il file di config.

## 1. Identità & filosofia

Il wiki è un **LLM Wiki** in stile Karpathy: *Obsidian è l'IDE, l'LLM è il programmatore, il wiki è la
codebase*. La conoscenza si **compila una volta** e si tiene aggiornata, invece di ricostruirla a ogni
sessione.

- **Doppio ruolo (DA-W1):** il wiki è insieme **corpus** (interrogabile via RAG) e **superficie**
  (indice navigabile iniettato a inizio sessione). Vedi la pagina `ruolo-wiki-da-w1` del wiki.
- **Cumulativo:** cresce a ogni sessione; non si riparte da zero.
- **Idempotente:** se una pagina è già accurata, **non riscriverla**. Niente modifiche inutili.
- **Self-contained:** ogni pagina è scritta perché un agente la riprenda senza il contesto della chat.

## 2. Nucleo deterministico vs giudizio (il confine)

Il bookkeeping **meccanico** è codice host-agnostico già pronto: la CLI **`sertor-wiki-tools`**
(sottopacchetto `sertor_core.wiki_tools`, FEAT-003-D). **Usala invece di rifare il meccanico a mano.**

| Operazione CLI | Cosa fa (meccanico) | Contratto JSON |
|---|---|---|
| `scan` | conta i file più recenti dell'ultima voce di log (lavoro pendente) | `wiki.scan/1` |
| `structure init` | crea cartelle della tassonomia + index + log (idempotente) | `wiki.structure/1` |
| `validate` | frontmatter mancante + naming non kebab-case | `wiki.lint/1` |
| `lint` | wikilink rotti + pagine orfane + frontmatter mancante | `wiki.lint/1` |
| `collect` | enumera le pagine + metadati (path, area, type, title, tags, wikilink) | `wiki.collect/1` |
| `index` | re-indicizza il wiki nel RAG (corpus da `[rag]`) | `wiki.index/1` |

Invocazione: `uv run sertor-wiki-tools <op> --config wiki.config.toml [--json]` (o il console-script
`sertor-wiki-tools`). Con `--json` ottieni il contratto versionato; senza, un sommario umano.

**A te (LLM) resta il GIUDIZIO**, che la CLI non fa: *cosa* scrivere e il *perché*, se una pagina è nuova
o va aggiornata, *quali* backlink hanno senso, se due claim si **contraddicono**, se un claim è superato.
Il *dove/come* (percorsi, formati, rilevazione meccanica) lo dà il deterministico.

## 3. Tassonomia (dalla config)

Le aree sono quelle in `[[taxonomy]]`. Nel profilo Sertor:

```
<root>/             (es. wiki/)
├─ <index_file>     catalogo globale (link + summary di una riga). LEGGILO PER PRIMO.
├─ <log_file>       registro append-only di tutto ciò che facciamo
├─ concepts/        concetti (RAG, chunking, embeddings, ...)
├─ tech/            tecnologie e strumenti
├─ experiments/     una pagina per attività/esperimento
├─ sources/         riassunti di fonti esterne ingerite
└─ syntheses/       confronti e sintesi trasversali
```

- Le **uniche** aree sono quelle della config. Le fonti esterne ingerite vanno in **`sources/`** (vedi
  `ingest`); non inventare cartelle non dichiarate.
- Le cartelle possono non esistere ancora: **creale on-demand** alla prima pagina della categoria (oppure
  in blocco con `sertor-wiki-tools structure init`). Non creare cartelle vuote o placeholder.
- Eventuali wiki **congelati/da non toccare** (su Sertor: `prototype/wiki/`) sono **fuori** dalla `root`
  ed esclusi via `exclude`: non si modificano, si consultano semmai via RAG.

## 4. Convenzioni

**Frontmatter YAML** in ogni pagina (eccetto i file append-only). I campi attesi sono in
`frontmatter_required`/`_optional`. Profilo Sertor:
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
  cross-reference aggiornati: una pagina nuova va linkata dall'indice e dalle pagine correlate.
- **Naming** file: kebab-case descrittivo (`azure-ai-search.md`). `validate` lo verifica per te.
- **Nuova vs aggiorna:** crea una pagina nuova per un concetto/entità nuovo; **aggiorna** quella
  esistente altrimenti. Una pagina per concetto reale, mai duplicati (usa `collect` per controllare).
- **Contraddizioni:** quando una fonte/codice contraddice una pagina, **segnalalo esplicitamente** — non
  scegliere in silenzio. Se tocca una decisione o una fonte autorevole umana, **chiedi all'utente**.
- **Niente over-doc:** non documentare il banale o le modifiche meccaniche. Calibra al valore.

**File append-only** (il log): **non** portano `updated` nel frontmatter (sarebbe sempre stale); il loro
stato è dato dall'ultima voce.

## 5. Operazioni

Ogni operazione = **input → passi → output** (pagine toccate + UNA voce di log). Le operazioni
documentali (`record`, `ingest`, `query`, `lint`) sono eseguibili anche dal `curator` in background;
`generate-from-diff` e `rag-sync` richiedono il **flusso principale** (vedi note).

> **Write-back log/indice:** oggi le scritture su indice e log sono **a cura dell'LLM** (formato curato:
> sezioni raggruppate, riga `- **[[slug]]** — summary`, voci di log multi-bullet). Il deterministico
> espone già `append_log`/`upsert_index` come funzioni, ma con identità/formato diversi (path POSIX, riga
> piatta) → non ancora cablati nella CLI. Per ora scrivi log/indice **a mano**, seguendo §6.

### `record` — registra lavoro/decisione svolti
1. Inventario meccanico: `uv run sertor-wiki-tools collect --json` (cosa esiste già) + leggi l'indice.
2. Crea/aggiorna la/e pagina/e rilevante/i (aree `concepts/ tech/ experiments/ syntheses/`). Sintetizza il
   *perché* oltre al *cosa*. **Giudizio:** nuova-vs-aggiorna, contenuto, quali backlink.
3. Aggiorna i backlink e l'indice (link + summary di una riga).
4. Appendi una voce di log `record`.

### `ingest` — acquisisci una fonte esterna
Input: un path locale (file/PDF) o un URL.
1. Acquisisci la fonte: `Read` per file/PDF locali; `WebFetch` per URL/PDF remoti. **Non modificare** la
   fonte originale.
2. Scrivi un riassunto in `sources/<slug>.md` con frontmatter (`sources:` = path/URL d'origine).
3. Integra/linka i concetti collegati nelle pagine `concepts/`/`tech/`; **segnala contraddizioni** con le
   pagine esistenti (giudizio).
4. Aggiorna l'indice e appendi una voce di log `ingest`.

### `query` — rispondi a una domanda sul wiki
1. Rispondi citando le pagine pertinenti (`collect` per orientarti; `index`/RAG se serve ricerca).
2. Se l'esplorazione è preziosa e riusabile, **archiviala** come nuova pagina (le query si cumulano in
   conoscenza) e aggiorna l'indice + voce di log `query`. Altrimenti nessuna scrittura.

### `lint` — verifica di coerenza
Il **meccanico è 100% della CLI**: esegui
`uv run sertor-wiki-tools lint --json` **e** `uv run sertor-wiki-tools validate --json` e interpreta i
contratti `wiki.lint/1` (wikilink rotti, orfani, frontmatter mancante, naming). **Non** rifare Glob/Grep a
mano. Produci un **report** + (opzionale) voce di log `lint`. **Non auto-correggere** di default: proponi e
correggi solo su conferma o se il brief lo richiede.

> Il **lint semantico** (contraddizioni, claim superati, coverage di senso) è **giudizio**, non meccanico:
> resta all'LLM e di norma al flusso principale (ha il contesto dello step). Non è coperto dalla CLI.

### `generate-from-diff` — aggiorna dalle modifiche recenti (flusso principale)
Evita di rileggere l'intero repo: aggiorna solo ciò che è cambiato.
1. Ancora il punto di partenza con `uv run sertor-wiki-tools scan --json` (file pendenti via mtime) e/o
   **delega al ruolo VCS** (`[roles].vcs`) un brief di sola lettura «`git log` + `git diff` dal punto X».
   X = data dell'ultima voce di log (o l'ultimo commit che tocca il wiki). *(Le operazioni git si delegano.)*
2. Col diff ricevuto, aggiorna **solo** le pagine impattate (giudizio).
3. Aggiorna l'indice e appendi una voce di log `generate-from-diff` che cita il range di commit.

### `rag-sync` — re-indicizza il wiki nel RAG (flusso principale; NON il curator)
Rende il wiki interrogabile via RAG (ruolo "corpus" di DA-W1).
1. Esegui `uv run sertor-wiki-tools index --config wiki.config.toml`. La CLI legge `[rag]` (corpus isolato,
   default `wiki`) e fa rebuild-from-scratch idempotente; il backend (Chroma locale / Azure AI Search)
   dipende da `RAG_BACKEND` nel `.env`. **Non** lanciare interpreti Python a mano.
2. Se la CLI segnala provider di embeddings non configurato (es. `RAG_BACKEND=azure` senza credenziali),
   **fermati e segnala** (non fallire in silenzio).
3. Appendi una voce di log `rag-sync` con `documents`/`collection` dal contratto `wiki.index/1`.
4. **Costo:** con backend azure gli embeddings sono a pagamento.

### `structure` — bootstrap della struttura (idempotente)
Su un ospite nuovo (o per riparare cartelle/file speciali mancanti): `uv run sertor-wiki-tools structure
init`. Crea le cartelle della tassonomia + index + log con seed minimo; **non sovrascrive** ciò che esiste
(contratto `wiki.structure/1`: `created` / `skipped_existing`). Nessun giudizio: puro meccanico.

## 6. Voce di log

Append al log (nome-file da config), una voce per operazione, con la **data odierna**:
```
## [YYYY-MM-DD] <operazione> | <titolo>
- <bullet sintetici: pagine create/aggiornate, decisioni, esiti, commit se noti>
```
`<operazione>` ∈ `setup` · `record` · `ingest` · `query` · `lint` · `generate-from-diff` · `rag-sync`.

## 7. Limiti & deleghe

- **Git:** mai eseguirlo direttamente. Tutte le operazioni git (incluse le letture per
  `generate-from-diff`) si **delegano al ruolo VCS** (`[roles].vcs`). Il `curator` non esegue git.
- **Fonti & wiki congelati:** non toccare mai le fonti originali date a `ingest`, né i wiki esclusi via
  `exclude` (su Sertor: `prototype/`).
- **Quando NON documentare:** modifiche puramente meccaniche o di poco conto non meritano una voce.
- **Versionamento:** quando l'utente vuole versionare, delega al ruolo VCS un commit `docs(wiki):
  <sommario>` con staging selettivo della radice del wiki.
