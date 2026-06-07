# Wiki Playbook — fonte unica del sistema wiki

> **Questo file è la fonte di verità del "sistema wiki".** La skill `wiki-author`, il comando `/wiki` e
> l'agente `wiki-curator` non duplicano queste regole: le **leggono qui** e le seguono. Se modifichi una
> convenzione o un'operazione, modificala **solo** in questo file (o nel modulo `ops/` dell'operazione).
>
> **Struttura (indice + moduli):** questo file è l'**indice** col **substrato condiviso** (host-agnosticità,
> identità, confine D↔N, tassonomia, convenzioni, voce di log, limiti). La **procedura di ogni operazione**
> sta in un modulo `ops/<operazione>.md` (stessa cartella), da `Read` **on-demand** — vedi §5. Così invocare
> una singola operazione non carica le procedure di tutte le altre (progressive disclosure), senza
> duplicare il substrato (DRY) e restando documenti `.md` portabili (Principio X — niente costrutti dell'host).
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
| `[[audit]]` | cosa sottoporre al lint e di che `kind` (wiki/requirements/spec/tracker) — vedi op. `lint` |
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

### Collocazione — scegliere l'area dalla natura della pagina

Un wiki è un **grafo, non un albero**: la cartella serve solo a dare a ogni pagina **una casa**, il valore
sta nei link. L'area si sceglie dalla **natura logica** del contenuto, **non** dalla fase/progetto (cartelle
per fase — `sprint-3/`, `fase-azure/` — invecchiano male). Ruoli delle aree (profilo Sertor; su un altro
ospite valgono i ruoli analoghi della sua `[[taxonomy]]`):

- **concepts/** — astrazioni, pattern, idee (un concetto RAG, una tecnica). Evergreen.
- **tech/** — una tecnologia/strumento/infra concreta (una libreria, un servizio). Evergreen.
- **experiments/** — il **record datato** di un'attività/step/feature svolta (l'implementazione di FEAT-X,
  uno spike, una sessione). È il diario di un lavoro, non un'astrazione.
- **sources/** — il riassunto di una **fonte esterna** ingerita (paper, blog, PR, doc di terzi).
- **syntheses/** — un **confronto trasversale** fra più concetti/esperimenti (A-vs-B, una sintesi che
  attraversa pagine). È la categoria **più rara**, **non** il default.

**Regola anti-discarica:** se non sai dove mettere una pagina, di solito è perché **non è atomica** (parla
di troppe cose) o perché **manca una categoria** — è un *segnale*, non un buco da tappare con `syntheses/`.
Nessuna area va usata come `misc/`. In dubbio fra due aree, scegli la più specifica alla natura; una pagina
è `syntheses/` **solo** se è davvero un confronto fra più concetti, altrimenti quasi mai.

**`type` riflette la natura, non solo la cartella.** Il `type` del frontmatter deve descrivere **cos'è
davvero** la pagina e coincidere con l'area che la ospita. Attenzione: cartella e `type` possono essere
*coerenti tra loro ma entrambi falsi* rispetto al contenuto (es. un record in `syntheses/` con
`type: synthesis`). Questo disallineamento **natura↔collocazione** è invisibile al lint meccanico (vede solo
la stringa) ed è il bersaglio del **lint livello C** (§5).

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

**Atomicità — una pagina, un concetto.** È la regola più importante per un LLM Wiki: pagine atomiche si
linkano meglio, si riusano in più contesti e si **chunkano puliti** per il RAG (una pagina che parla di tre
cose produce chunk ambigui e link generici). Criterio di **split**: se sviluppando una pagina emergono **due
focus distinti** (due "cos'è"), crea **due pagine** collegate da wikilink reciproci invece di accatastare.
Sotto la pressione dell'append è qui che si cede — sezioni duplicate ("Note di processo" ×2, due blocchi di
stato) sono il sintomo: *ricuci o splitta*, non appendere.

**Auto-contenimento — la prima frase definisce.** Il RAG recupera una pagina **fuori dal suo contesto**: la
**prima frase** deve dire *cos'è* il soggetto senza presupporre nulla ("**X è …**"), prima dei dettagli — il
primo chunk dev'essere autosufficiente. Evita aperture che rimandano ("Questo concetto è stato approfondito
in…").

**Link densi, inline e bidirezionali.** Quasi tutto il valore di un wiki sta nei **link**, non nelle
cartelle. Linka **al punto di menzione** (inline), non in una sezione "vedi anche" in fondo: il link
contestuale dice *perché* due pagine sono connesse. Preferisci link **specifici** alla pagina giusta
piuttosto che a pagine-contenitore (densità ≠ qualità). I `[[wikilink]]` danno i **backlink** gratis
(segnale di rilevanza per umano e RAG); una pagina **orfana** (zero link entranti) è invisibile alla
navigazione — è uno *smell*, falla linkare. Linkare in avanti una pagina **non ancora esistente** è una
*feature* (marca un nodo da creare), non un errore.

**File append-only** (il log): **non** portano `updated` nel frontmatter (sarebbe sempre stale); il loro
stato è dato dall'ultima voce.

## 5. Operazioni — indice (caricamento on-demand)

Ogni operazione = **input → passi → output** (pagine toccate + UNA voce di log) e segue il **substrato
condiviso** di questo file (confine D↔N §2, tassonomia §3, convenzioni §4, voce di log §6, limiti §7).
La **procedura specifica** di ciascuna operazione vive in un **modulo `ops/<operazione>.md`** (stessa
cartella di questo file): **`Read` solo il modulo dell'operazione che ti serve** — non caricarli tutti
(progressive disclosure). Le operazioni documentali (`record`, `ingest`, `query`, lint **A**) sono
eseguibili anche dal `curator` in background; il lint **B/C**, `reorg`, `generate-from-diff` e `rag-sync`
richiedono il **flusso principale** (Opus).

| Operazione | Modulo (`Read` on-demand) | Cosa fa | Esecutore |
|---|---|---|---|
| `record` | [`ops/record.md`](ops/record.md) | registra lavoro/decisione svolti | curator OK |
| `ingest` | [`ops/ingest.md`](ops/ingest.md) | acquisisci una fonte esterna → `sources/` | curator OK |
| `query` | [`ops/query.md`](ops/query.md) | rispondi a una domanda sul wiki (archivia se prezioso) | curator OK |
| `lint` | [`ops/lint.md`](ops/lint.md) | coerenza a 3 livelli: A strutturale · B semantico · C organizzativo | A: curator · B/C: solo Opus |
| `reorg` | [`ops/reorg.md`](ops/reorg.md) | applica il refactoring organizzativo del lint C (su conferma) | solo Opus |
| `generate-from-diff` | [`ops/generate-from-diff.md`](ops/generate-from-diff.md) | aggiorna solo le pagine impattate dalle modifiche recenti | solo Opus |
| `rag-sync` | [`ops/rag-sync.md`](ops/rag-sync.md) | re-indicizza il wiki nel RAG (ruolo "corpus" di DA-W1) | solo Opus |
| `structure` | [`ops/structure.md`](ops/structure.md) | bootstrap idempotente della struttura | curator/CLI |

> **Write-back log/indice:** oggi le scritture su indice e log sono **a cura dell'LLM** (formato curato:
> sezioni raggruppate, riga `- **[[slug]]** — summary`, voci di log multi-bullet). Il deterministico
> espone già `append_log`/`upsert_index` come funzioni, ma con identità/formato diversi (path POSIX, riga
> piatta) → non ancora cablati nella CLI. Per ora scrivi log/indice **a mano**, seguendo §6.

## 6. Voce di log

Append al log (nome-file da config), una voce per operazione, con la **data odierna**:
```
## [YYYY-MM-DD] <operazione> | <titolo>
- <bullet sintetici: pagine create/aggiornate, decisioni, esiti, commit se noti>
```
`<operazione>` ∈ `setup` · `record` · `ingest` · `query` · `lint` · `reorg` · `generate-from-diff` · `rag-sync`.

## 7. Limiti & deleghe

- **Git:** mai eseguirlo direttamente. Tutte le operazioni git (incluse le letture per
  `generate-from-diff`) si **delegano al ruolo VCS** (`[roles].vcs`). Il `curator` non esegue git.
- **Fonti & wiki congelati:** non toccare mai le fonti originali date a `ingest`, né i wiki esclusi via
  `exclude` (su Sertor: `prototype/`).
- **Quando NON documentare:** modifiche puramente meccaniche o di poco conto non meritano una voce.
- **Versionamento:** quando l'utente vuole versionare, delega al ruolo VCS un commit `docs(wiki):
  <sommario>` con staging selettivo della radice del wiki.
