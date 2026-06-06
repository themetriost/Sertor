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

## 5. Operazioni

Ogni operazione = **input → passi → output** (pagine toccate + UNA voce di log). Le operazioni
documentali (`record`, `ingest`, `query`, e il lint **strutturale**) sono eseguibili anche dal `curator` in
background; il lint **semantico/organizzativo**, `reorg`, `generate-from-diff` e `rag-sync` richiedono il
**flusso principale** (vedi note).

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
Il lint ha **tre livelli**: **A** strutturale (meccanico, CLI: igiene), **B** semantico (giudizio, LLM:
*claim ↔ realtà del repo*) e **C** organizzativo (giudizio, LLM: *collocazione/atomicità/link*). A è la
baseline; B e C sono ortogonali (puoi lanciarli insieme o separati). **Non auto-correggere** di default:
produci un **report con severità** e correggi **solo su conferma** (o se il brief lo richiede); l'applicazione
del refactoring organizzativo è l'operazione `reorg`. Voce di log `lint` (opzionale ma consigliata se correggi).

**Ambito: cosa lintare (`[[audit]]`).** Il lint **non** è solo sul wiki: copre i target dichiarati in
`[[audit]]` (config). Ogni target = `paths` (glob dell'ospite) + `kind` (profilo universale qui sotto).
**Prima regola che matcha vince** (i `paths` più specifici vanno prima): così `TODO.md`/`tasks.md`/
`checklists` ricadono in `tracker` anche se stanno sotto `requirements/`/`specs/`. Il `kind` determina
**quali livelli** si applicano e **cosa conta come deriva** — è ciò che evita i falsi positivi (non trattare
l'*intento* come *stato*; gerarchia di autorità: codice/test = comportamento, requisiti/spec = perché).

| `kind` | Liv. A (strutturale) | Liv. B (semantico) — cos'è "deriva" | Azione default |
|---|---|---|---|
| `wiki` | **sì** (CLI: wikilink/frontmatter/orfani/naming) | claim descrittivo contraddetto da codice/test · contraddizioni tra pagine · coverage · sommario stantio | report |
| `requirements` | no (niente wikilink/frontmatter) | **solo claim di STATO** (implementato/mergiato/conteggi/ID); un «*shall X*» non ancora in codice = **backlog, NON deriva** | report |
| `spec` | no | come `requirements` + coerenza col codice **se** lo stato dichiara "implementato" | report |
| `tracker` | no | **tabelle/checkbox di stato** ("FATTO/da fare", `[x]`/`[ ]`) contraddette dalla realtà = **deriva diretta** | report |

**A) Lint strutturale — 100% meccanico (CLI).** Esegui `uv run sertor-wiki-tools lint --json` **e**
`… validate --json`; interpreta i contratti `wiki.lint/1` (wikilink rotti, orfani, frontmatter mancante,
naming). **Non** rifare Glob/Grep a mano. È autorevole sui link: se la CLI dice 0 broken, i link sono a posto.

**B) Lint semantico — giudizio (LLM, flusso principale).** Verifica che gli **artefatti dichiarati in
`[[audit]]`** (non solo il wiki: anche `requirements`/`spec`/`tracker`) **non siano derivati** dalla realtà
del progetto, applicando il **profilo del `kind`** (tabella sopra). È **giudizio**: resta all'LLM e **di
norma al flusso principale (Opus)**, che ha il
contesto; **non si delega al `curator` (Haiku)** la parte di giudizio (vedi §7 e il rituale in `CLAUDE.md`).
Procedura ripetibile:

1. **Baseline** = il report di (A).
2. **Estrai i claim verificabili** dalle pagine (usa `collect` per l'inventario): conteggi (test, moduli,
   lingue…), stati (`mergiata`, `in progress`, branch/PR/commit), versioni, date, percorsi/simboli citati come
   esistenti, nomi di entità. *(Per fan-out su molte pagine puoi delegare l'ESTRAZIONE a reader; il giudizio resta tuo.)*
3. **Recupera la ground truth dal repo** — appòggiati agli strumenti **già disponibili**, non reinventarli:
   - **git** (stato/PR/branch/commit) → **delega al ruolo VCS** (`[roles].vcs`); le operazioni git non si eseguono qui.
   - **esistenza file/simboli, valori nel codice** → il **RAG dell'ospite** se configurato (server MCP del corpus
     codice: `search_code`/`find_symbol`/`search_docs`); **altrimenti** ispezione diretta (`Read`/`Grep`).
   - **conteggi build/test** → il tool dell'ospite (es. `uv run pytest --collect-only -q`).
4. **Confronta claim ↔ ground truth → giudica.** Un claim è una **deriva** se il repo lo contraddice. Tassonomia
   dei controlli: *stato git/PR/branch superato* · *numeri incoerenti col codice* · *file/simboli citati ma assenti*
   · *date/versioni vecchie* · *contraddizioni tra pagine* · *claim più vecchi delle `sources`* · *coverage* (cose
   reali del progetto non ancora documentate).
5. **Report con severità** (Alto/Medio/Basso/Info) + proposta di correzione per ciascun finding. **Scarta i falsi
   positivi** (es. un reader che segnala link "inesistenti" già smentiti dalla CLI).
6. **Correggi su conferma.** Aggiorna **solo le pagine attive** (stato corrente); **non riscrivere** il registro
   storico (`log.md`) né gli artefatti datati. Appendi una voce di log `lint`.

**Host-agnostico (degradazione per profilo).** I probe disponibili dipendono dall'ospite: su un host **solo-doc**
non ci sono test/simboli di codice → salta i probe di codice e tieni i controlli su date/contraddizioni/coverage;
su **solo-code** salta i controlli doc-specifici. git è quasi sempre disponibile; il RAG è un **acceleratore se
c'è**, mai un prerequisito (fallback su `Read`/`Grep`). Non assumere `pytest`/`src/`: derivali da `source_dirs`/profilo.

**Al commit (comportamento-obiettivo: A + B incrementale).** Al commit gira il livello **A** (strutturale, sui
target `wiki`) **e** il livello **B** **solo sugli artefatti del changeset** (incrementale, mai l'intero repo),
per ogni `kind`; esito = **report + warning NON bloccante** (mai blocco, mai auto-fix — lezione: il valore sta
nella rilevazione, non nella correzione automatica). **Caveat di automazione:** A al commit è meccanico
(hook/CLI); **B al commit è un giudizio LLM** → la sua esecuzione automatica dipende dall'orchestrazione/trigger
(lato deterministico, cfr. `generate-from-diff` e il contratto-trigger, oggi non cablato). Finché non è cablata:
il warning al commit copre A e **ricorda di lanciare B incrementale** (`/wiki lint` sul changeset).

**C) Lint organizzativo — giudizio (LLM, flusso principale).** Verifica che il wiki sia un **grafo ben
organizzato**, non solo igienicamente sano. È **tutto giudizio**: collocazione e natura di una pagina **non
sono deterministiche** — cartella e `type` possono concordare tra loro e **mentire entrambi** sul contenuto,
quindi nessun controllo meccanico le coglie. Resta al flusso principale (Opus), **non** al `curator`. Si
applica al solo `kind` `wiki`, **on-demand** (non al commit). Inventario di partenza: `collect`
(rel_path/area/`type`/tags/wikilink); i **backlink non sono esposti** dalla CLI → **calcolali invertendo** i
`wikilinks` di `collect`. Controlli:

1. **Collocazione vs natura** — la natura reale della pagina non corrisponde all'area che la ospita (es. un
   record di feature in `syntheses/`). Riferimento: l'euristica di collocazione in §3.
2. **`type` semanticamente falso** — `type` coerente con la cartella ma non col contenuto (deriva
   natura↔collocazione).
3. **Tassonomia collassata** — un'area usata come discarica (quota sproporzionata di pagine, specie in
   un'area "rara" come `syntheses/`) mentre altre aree dichiarate restano vuote pur esistendo contenuto che
   le riempirebbe.
4. **Atomicità** — pagine con più focus o sezioni duplicate (candidate a split; vedi §4).
5. **Disciplina dei link** — link relegati a "vedi anche" invece che inline; pagine centrali ma debolmente
   connesse (pochi backlink).

Esito = **report con severità + proposta** per finding (sposta a `<area>` · correggi `type` · splitta ·
aggiungi link inline), **nessun auto-fix**. L'applicazione su conferma è l'operazione `reorg`.

### `reorg` — applica il refactoring organizzativo (flusso principale; NON il curator)
Applica, **su conferma esplicita** dell'utente, le proposte del **lint livello C**. È **più distruttivo**
della correzione-claim (sposta file, riscrive link) → **mai automatico, mai bloccante, un incremento per
volta**. È **giudizio** (cosa spostare/dove/se splittare) + meccanica via `Read`/`Edit`: **non si delega al
`curator`**.
1. Parti dal report del lint livello C e **concorda con l'utente** le pagine da trattare.
2. Per ogni pagina: **spostala** nell'area corretta (nuovo path), **correggi il `type`** nel frontmatter, e
   **aggiorna tutti i wikilink entranti** (dai backlink calcolati a §5-C) perché area/slug cambiano; aggiorna
   l'indice (riga `- **[[slug]]** — summary` nella sezione giusta).
3. **Verifica l'igiene post-move:** `uv run sertor-wiki-tools lint --json` **e** `… validate --json` →
   attesi **0 link rotti / 0 orfani / 0 naming**. Se no, ripara prima di proseguire.
4. Appendi una voce di log `reorg` (pagine spostate da→a, `type` corretti).

> **Backlog (meccanica deterministica):** un comando `move`-con-aggiornamento-link sicuro in `wiki_tools`
> (FEAT-003-D) renderebbe il passo 2 meno fragile dell'`Edit` a mano — da fare **solo se** l'approccio manuale
> si rivela rumoroso. La **rilevazione** (livello C) resta comunque giudizio, non deterministica.

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
`<operazione>` ∈ `setup` · `record` · `ingest` · `query` · `lint` · `reorg` · `generate-from-diff` · `rag-sync`.

## 7. Limiti & deleghe

- **Git:** mai eseguirlo direttamente. Tutte le operazioni git (incluse le letture per
  `generate-from-diff`) si **delegano al ruolo VCS** (`[roles].vcs`). Il `curator` non esegue git.
- **Fonti & wiki congelati:** non toccare mai le fonti originali date a `ingest`, né i wiki esclusi via
  `exclude` (su Sertor: `prototype/`).
- **Quando NON documentare:** modifiche puramente meccaniche o di poco conto non meritano una voce.
- **Versionamento:** quando l'utente vuole versionare, delega al ruolo VCS un commit `docs(wiki):
  <sommario>` con staging selettivo della radice del wiki.
