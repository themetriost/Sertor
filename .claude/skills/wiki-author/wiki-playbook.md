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
| `root`, `index_file`, `log_file`, `log_dir` | dove vive il wiki e i suoi file speciali (`log_dir` ⇒ rotazione del log a un file per giorno) |
| `[[taxonomy]]` | le aree logiche (cartella → tipo frontmatter) |
| `frontmatter_required` / `_optional` | i campi di frontmatter attesi |
| `source_dirs`, `exclude` | da dove leggere il lavoro dell'ospite e cosa ignorare |
| `[[audit]]` | cosa sottoporre al lint e di che `kind` (wiki/requirements/spec/tracker) — vedi op. `lint` |
| `[roles]` | i nomi degli agenti: `curator` (questo wiki), `vcs` (git) |
| `[rag]`, `[strings]`, `language` | corpus RAG, messaggi localizzati, lingua |

**Non assumere `wiki/`, `src/`, nomi di cartelle o di agenti**: leggili dalla config. Gli esempi concreti
qui sotto (`wiki/`, `concepts/`, `src/`…) sono **esempi del profilo dell'ospite**, **non** leggi
universali. Su un altro progetto cambia solo il file di config.

## 1. Identità & filosofia

Il wiki è un **LLM Wiki** in stile Karpathy: *Obsidian è l'IDE, l'LLM è il programmatore, il wiki è la
codebase*. La conoscenza si **compila una volta** e si tiene aggiornata, invece di ricostruirla a ogni
sessione.

- **Doppio ruolo:** il wiki è insieme **corpus** (interrogabile via RAG) e **superficie**
  (indice navigabile iniettato a inizio sessione).
- **Cumulativo:** cresce a ogni sessione; non si riparte da zero.
- **Idempotente:** se una pagina è già accurata, **non riscriverla**. Niente modifiche inutili.
- **Self-contained:** ogni pagina è scritta perché un agente la riprenda senza il contesto della chat.
- **Coerente per costruzione (anti-deriva auto-inflitta):** quando una modifica (al codice, alle regole o
  a un'altra pagina) rende **stale** una pagina, riallinearla **fa parte dello stesso lavoro** — non è
  un'operazione separata da chiedere. La deriva che *tu* introduci si corregge **nello stesso step**, di
  default e senza richiesta esplicita; quella *preesistente* che soltanto scopri può diventare worklist del
  `lint`. *(L'ospite può codificarlo nel proprio rituale, es. nel `CLAUDE.md`.)*

## 2. Nucleo deterministico vs giudizio (il confine)

Il bookkeeping **meccanico** è codice host-agnostico già pronto: la CLI **`sertor-wiki-tools`**.
**Usala invece di rifare il meccanico a mano.**

| Operazione CLI | Cosa fa (meccanico) | Contratto JSON |
|---|---|---|
| `scan` | conta i file più recenti dell'ultima voce di log (lavoro pendente) | `wiki.scan/1` |
| `structure init` | crea cartelle della tassonomia + index + log (idempotente) | `wiki.structure/1` |
| `validate` | frontmatter mancante + naming non kebab-case | `wiki.lint/1` |
| `lint` | wikilink rotti + pagine orfane + frontmatter mancante | `wiki.lint/1` |
| `collect` | enumera le pagine + metadati (path, area, type, title, tags, wikilink) | `wiki.collect/1` |
| `index` | re-indicizza il wiki nel RAG (corpus da `[rag]`) | `wiki.index/1` |
| `append-log` | piazza una voce di log (corpo curato dall'LLM) nel file del giorno, idempotente | `wiki.append_log/1` |
| `migrate` | splitta retroattivamente il log monolitico in partizioni giornaliere | `wiki.migrate/1` |
| `upsert-index` | inserisce/aggiorna la riga `- [[page]] — summary` nell'indice (sommario LLM-authored) | `wiki.upsert_index/1` |

Invocazione: `sertor-wiki-tools <op> --config wiki.config.toml [--json]` (o il console-script
`sertor-wiki-tools`). Con `--json` ottieni il contratto versionato; senza, un sommario umano.

**A te (LLM) resta il GIUDIZIO**, che la CLI non fa: *cosa* scrivere e il *perché*, se una pagina è nuova
o va aggiornata, *quali* backlink hanno senso, se due claim si **contraddicono**, se un claim è superato.
Il *dove/come* (percorsi, formati, rilevazione meccanica) lo dà il deterministico.

## 3. Tassonomia (dalla config)

Le aree sono quelle in `[[taxonomy]]`. Esempio di profilo:

```
<root>/             (es. wiki/)
├─ <index_file>     catalogo globale (link + summary di una riga). LEGGILO PER PRIMO.
├─ <log_dir>/       registro append-only, un file per giorno (rotazione; o <log_file> unico se off)
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
- Eventuali wiki **congelati/da non toccare** (es. un wiki storico archiviato) sono **fuori** dalla `root`
  ed esclusi via `exclude`: non si modificano, si consultano semmai via RAG.

### Collocazione — scegliere l'area dalla natura della pagina

L'area si sceglie dalla **natura logica** del contenuto, **non** dalla fase/progetto (cartelle
per fase — `sprint-3/`, `fase-azure/` — invecchiano male): la cartella dà solo **una casa**, il valore sta nei
link. Il *perché* — «un wiki è un grafo, non un albero» e i due assi di navigazione — sta in
[`wiki-craft.md`](wiki-craft.md) §4. Ruoli delle aree (su ogni
ospite valgono i ruoli analoghi della sua `[[taxonomy]]`):

- **concepts/** — astrazioni, pattern, idee (un concetto RAG, una tecnica). Evergreen.
- **tech/** — una tecnologia/strumento/infra concreta (una libreria, un servizio). Evergreen.
- **experiments/** — il **record datato** di un'attività/step/feature svolta (l'implementazione di una
  feature, uno spike, una sessione). È il diario di un lavoro, non un'astrazione.
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
la stringa) ed è il bersaglio del **lint livello C** (modulo [`ops/lint.md`](ops/lint.md)).

**Livello-grafo → [`page-craft.md`](page-craft.md) (la singola pagina) e [`wiki-craft.md`](wiki-craft.md)
(l'insieme).** *Quando* una cosa merita una pagina (test del link/nome), gli **archetipi** di pagina, le
pagine di struttura (home/hub/overview) e i due assi di navigazione stanno in `wiki-craft.md` — la guida di
livello-grafo, gemella di `page-craft.md`.

## 4. Convenzioni

**Frontmatter YAML** in ogni pagina (eccetto i file append-only). I campi attesi sono in
`frontmatter_required`/`_optional`. Esempio:
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

- **Stub (nodo da creare):** un forward-link a una pagina non ancora scritta si realizza come **stub**, non
  come `[[…]]` a vuoto (che il lint A segnala `broken`). Meccanismo e regole in [`page-craft.md`](page-craft.md) §4.
- **Wikilink** `[[nome-pagina]]` (senza `.md`); alias con `[[nome-pagina|testo mostrato]]`. Mantieni i
  cross-reference aggiornati: una pagina nuova va linkata dall'indice e dalle pagine correlate.
- **Naming** file: kebab-case descrittivo (`azure-ai-search.md`). `validate` lo verifica per te.
  - **Lingua del nome (esempio di convenzione):** le pagine-**entità/concetto** (`concepts/`, `tech/`) hanno
    **slug e titolo in inglese** (`retrieval-core`, `thin-consumer`), mentre il **corpo discorsivo resta in
    italiano**. I **record** (`experiments/`) restano in italiano descrittivo (sono eventi, non entità). Le
    pagine esistenti con slug italiano si rinominano **opportunisticamente** (quando le si tocca), non in
    blocco.
- **Nuova vs aggiorna:** crea una pagina nuova per un concetto/entità nuovo; **aggiorna** quella
  esistente altrimenti. Una pagina per concetto reale, mai duplicati (usa `collect` per controllare).
- **Contraddizioni:** quando una fonte/codice contraddice una pagina, **segnalalo esplicitamente** — non
  scegliere in silenzio. Se tocca una decisione o una fonte autorevole umana, **chiedi all'utente**.
- **Niente over-doc:** non documentare il banale o le modifiche meccaniche. Calibra al valore.

**Com'è fatta *dentro* una pagina → [`page-craft.md`](page-craft.md).** Le regole qui sopra sono
il *formato* (frontmatter, naming, wikilink, quando creare/aggiornare). Il **page-craft** — atomicità,
auto-contenimento, disciplina dei link e soprattutto il **livello di significato** (*cosa* scrivere, non solo
come) — vive nella pagina di riferimento `page-craft.md`, **linkata dalle operazioni** che creano o
riscrivono pagine (`record`, `ingest`, lint **C**, `reorg`). È una foglia: le operazioni la referenziano
senza che questo file dipenda da loro.

### Verità, autorità e obsolescenza

**Non esiste una singola fonte di verità**: l'autorità dipende dall'**asse** del claim —
sul **comportamento** vincono **codice + test**; sul **perché** vincono le **decisioni registrate**
(log, requirements, decisioni di processo). Il wiki è **derivato**: in conflitto si applica la gerarchia
di default (comportamento → codice/test · perché → decisione registrata); una gerarchia configurata
dall'ospite può sostituirla (opzionale).

**Una pagina è stale quando contraddice la sua autorità.** La risposta NON è correggere in
silenzio, né cancellare: è la **supersession esplicita** —

1. **frontmatter**: `status: superseded` (il campo `status` è tra gli opzionali della config);
2. **banner in testa** con data, *cosa* supera la pagina e il **link** alla verità corrente
   (`> ⚠️ **Superata (YYYY-MM-DD):** <claim> è contraddetto da <autorità> → vedi [[pagina-corrente]]`);
3. il **contenuto resta** (testimonianza; gli errori cancellati si ripetono): la pagina si pota o si
   fonde nel successore solo in un `reorg` confermato, mai d'ufficio.

Per il **diario** (log, record datati) la supersession è naturale: la correzione è una **nuova voce**,
mai un edit. Per il **grafo** la convenzione qui sopra è l'equivalente. **Niente punteggi di confidenza
numerici**: l'evidenza è la catena di link/prove del claim ancorato (vedi le critiche in
la falsa precisione dei punteggi numerici). Chi *rileva* la contraddizione è
il lint B (o chiunque, lavorando); chi *decide* la marcatura è il flusso principale **su conferma**
quando il caso tocca decisioni/fonti autorevoli umane (convenzione "Contraddizioni" qui sopra).

**File append-only** (il log): **non** portano `updated` nel frontmatter (sarebbe sempre stale); il loro
stato è dato dall'ultima voce.

## 5. Operazioni — indice (caricamento on-demand)

Ogni operazione = **input → passi → output** (pagine toccate + UNA voce di log) e segue il **substrato
condiviso** di questo file (confine D↔N §2, tassonomia §3, convenzioni §4, voce di log §6, limiti §7);
chi crea o riscrive pagine segue inoltre il page-craft in [`page-craft.md`](page-craft.md).
La **procedura specifica** di ciascuna operazione vive in un **modulo `ops/<operazione>.md`** (stessa
cartella di questo file): **`Read` solo il modulo dell'operazione che ti serve** — non caricarli tutti
(progressive disclosure). Le operazioni documentali (`record`, `ingest`, `query`, lint **A**) sono
eseguibili anche dal `curator` in background; il lint **B/C**, `distill`, `reorg`, `generate` e
`rag-sync` richiedono il **flusso principale** (Opus).

| Operazione | Modulo (`Read` on-demand) | Cosa fa | Esecutore |
|---|---|---|---|
| `record` | [`ops/record.md`](ops/record.md) | registra lavoro/decisione svolti | curator OK |
| `distill` | [`ops/distill.md`](ops/distill.md) | estrae le entità/concetti durevoli in pagine proprie (ingressi: step appena svolto · record grasso dal backlog · brief di una conversazione intera, anche vecchia); assottiglia i record datati | solo Opus |
| `ingest` | [`ops/ingest.md`](ops/ingest.md) | acquisisci una fonte esterna → `sources/` | curator OK |
| `query` | [`ops/query.md`](ops/query.md) | rispondi a una domanda sul wiki (archivia se prezioso) | curator OK |
| `lint` | [`ops/lint.md`](ops/lint.md) | coerenza a 3 livelli: A strutturale · B semantico · C organizzativo | A: curator · B/C: solo Opus |
| `reorg` | [`ops/reorg.md`](ops/reorg.md) | applica il refactoring organizzativo del lint C (su conferma) | solo Opus |
| `generate` | [`ops/generate.md`](ops/generate.md) | genera il wiki dal repo: **da-zero** (bootstrap su ospite privo di wiki) o **da-diff** (incrementale: solo le pagine impattate dalle modifiche recenti); profondità di ricognizione a preset (`leggera`/`media`/`massiva`, default leggera) | solo Opus |
| `rag-sync` | [`ops/rag-sync.md`](ops/rag-sync.md) | re-indicizza il wiki nel RAG (il ruolo di "corpus") | solo Opus |
| `structure` | [`ops/structure.md`](ops/structure.md) | bootstrap idempotente della struttura | curator/CLI |

> **Write-back log/indice.** Entrambi **cablati in CLI**: il **log** con `append-log` (l'LLM
> compone il **corpo curato** §6, la CLI lo piazza nel file del giorno) e la riga d'**indice** con
> `upsert-index` (`--page` + `--summary` o stdin; insert/update/noop idempotente, sommario
> **sempre LLM-authored**, vuoto/multilinea rifiutati). Sfumatura sull'indice: la CLI scrive la riga
> **piatta** `- [[page]] — summary`; se l'indice dell'ospite è *curato* (grassetti, sezioni),
> decidere se adottare il formato piatto o continuare ad autorare la riga a mano è **giudizio**.

## 6. Voce di log

Append al log, una voce per operazione, con la **data odierna**. Con la **rotazione** (`log_dir`) la voce va
nel **file del giorno** (`<log_dir>/YYYY-MM-DD.md`) e il **piazzamento** lo fa `append-log` (CLI) a
cui passi il **corpo curato**; senza `log_dir`, un unico file di log (back-compat). Formato:
```
## [YYYY-MM-DD] <operazione> | <titolo>
<lead: 1–2 frasi col perché/trigger dello step>
- **<etichetta>:** <fatto saliente o puntatore [[pagina]], una riga>
```
`<operazione>` ∈ `setup` · `structure` · `record` · `distill` · `ingest` · `query` · `lint` · `reorg` ·
`generate` · `rag-sync` — l'insieme delle operazioni di §5 più `setup` (bootstrap generico di
sessione/governance, distinto da `structure` che è il bootstrap della *struttura* del wiki). `structure`
lascia una voce **solo se ha creato qualcosa** (`created` non vuoto); se è tutto `skipped_existing`,
niente voce (idempotente + regola anti-banale). *Retro-compatibilità:* le voci storiche
`generate-from-diff` nei log restano valide (il log è append-only, non si riscrive); dal 2026-06-10 il
vocabolario corrente usa `generate`.

**Com'è fatta una buona voce → [`log-craft.md`](log-craft.md).** Le regole qui sopra sono la *convenzione*
(grammatica dell'heading, vocabolario delle operazioni, regola anti-banale). Il **log-craft** — il confine
log↔pagina (cosa va nel log datato vs nella pagina evergreen), l'anatomia della voce (lead + bullet piatti +
riga d'esito), la **granularità** e l'**anti-deriva** (no dump del contenuto, no liste-file, no aggettivi) —
vive nella pagina-foglia gemella di [`page-craft.md`](page-craft.md), linkata dalle operazioni che appendono
una voce (`record`, `ingest`, `lint`, `reorg`, …).

## 7. Limiti & deleghe

- **Git:** mai eseguirlo direttamente. Tutte le operazioni git (incluse le letture per il `generate`
  da-diff) si **delegano al ruolo VCS** (`[roles].vcs`). Il `curator` non esegue git.
- **Fonti & wiki congelati:** non toccare mai le fonti originali date a `ingest`, né i wiki esclusi via
  `exclude`.
- **Quando NON documentare:** modifiche puramente meccaniche o di poco conto non meritano una voce.
- **Versionamento:** quando l'utente vuole versionare, delega al ruolo VCS un commit `docs(wiki):
  <sommario>` con staging selettivo della radice del wiki.
