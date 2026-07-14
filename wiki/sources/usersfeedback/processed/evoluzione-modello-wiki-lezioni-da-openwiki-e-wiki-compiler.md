---
title: "Richiesta di verifica approfondita — evolvere il modello wiki di Sertor imparando da OpenWiki e wiki-compiler"
type: source
tags: [usersfeedback, wiki, wiki-tools, determinismo, ingestione, roadmap-prodotto]
created: 2026-07-09
updated: 2026-07-09
source: utente vault "Nunzio Summaries" (richiesta di verifica, 2026-07-09)
status: da elaborare
---

# Richiesta: verifica approfondita del modello di creazione e manutenzione wiki

> **Fonte:** vault *Nunzio Summaries*, 2026-07-09. Nasce da un **dogfooding reale**: in una sessione
> abbiamo costruito da zero un wiki di 33 pagine a partire da un corpus di 34 documenti, usando
> `sertor-wiki-tools` e il playbook. Nello stesso giorno abbiamo analizzato **sul codice** due sistemi
> concorrenti. Questo documento riporta ciò che ne è emerso e chiede al team una verifica.
>
> **Natura del documento:** non è una lista di feature da implementare. È una richiesta di
> **indagine**, con ipotesi verificabili e metriche proposte. Dove non abbiamo prove lo diciamo.

## Executive summary

Sertor è già nel punto giusto dello spettro, e non se ne sta prendendo il merito.

"Fare una wiki" sono **due lavori separabili**: qualcuno la **compila** (decide cosa scrivere, come
collegarlo, cosa significa) e qualcuno la **verifica** (i link esistono, le pagine non sono orfane, il
frontmatter c'è). Il primo lavoro richiede di capire il significato; il secondo si fa contando.

| Sistema | Compila | Verifica |
|---|---|---|
| `langchain-ai/openwiki` | LLM | **nessuno** |
| **Sertor** · `nvk/llm-wiki` | LLM | codice |
| `Emmimal/wiki-compiler` | codice | codice |

**Il dato più interessante: i due estremi convergono verso il centro da soli.** L'autore del
compilatore puramente deterministico conclude il proprio articolo dicendo che l'LLM serve per *"il 10%
che richiede comprensione, non per il 90% puramente meccanico"* — che è, parola per parola, il confine
formalizzato nella sezione *Deterministic core vs judgment* del playbook di Sertor. E `nvk/llm-wiki`,
partito dall'agente, ha finito per aggiungere un helper Python descritto come *"structural checks and
safe migrations that do not require an LLM."*

Due progetti indipendenti, partiti dai capi opposti, arrivati dove Sertor era già.

**La richiesta di fondo è quindi: non spostare quel confine. Sfruttarlo meglio.** Le sezioni seguenti
propongono come, prendendo da ciascun concorrente ciò in cui è oggettivamente più avanti.

---

## Parte 1 — Cosa prendere da `wiki-compiler` (il lato deterministico)

**Riferimento:** Emmimal P Alexander, *"LLM Wikis Are Over-Engineered: I Replaced Mine With a Pure
Python Compiler"*, Towards Data Science, 2026-07-03. Repo `Emmimal/wiki-compiler`. Quattro fasi
(estrattore regex, costruttore di grafo, riscrittore section-aware, linter), *zero LLM calls, zero
embeddings, no external APIs, standard library only*.

### 1.1 Il core può **generare**, non solo validare

**Osservazione.** `collect.py` estrae già, per ogni pagina, i **wikilink uscenti**
(`"wikilinks": extract_wikilinks(text)`). Da quell'informazione i **backlink** sono derivabili in modo
puramente deterministico: sono la relazione inversa. Eppure oggi il core non li genera, e il playbook
lascia all'LLM il compito di decidere *"quali backlink hanno senso"*.

**Cosa fa il concorrente.** `wiki-compiler` genera meccanicamente le sezioni *Metadati*, *Correlati*,
*Referenced By* e *Body*, e nella ricompilazione **preserva le sezioni scritte a mano** (rewriter
section-aware). Il suo linter distingue i link in *Related* da quelli in *Referenced By* proprio per
non contare falsi positivi fra gli orfani.

**Domanda al team.** Quanta parte delle pagine è *struttura derivabile* e non *prosa*? Una sezione
`## Referenced by` rigenerata da `collect` a ogni run sarebbe:

- sempre corretta per costruzione (mai un backlink stantio);
- gratis in token;
- e toglierebbe all'LLM un compito in cui non porta valore.

Attenzione a una distinzione che ci pare importante: *quali backlink hanno senso in prosa* è giudizio
(e resta all'LLM); *quali pagine puntano a questa* è aritmetica.

**Come misurarlo.** Su un wiki reale, contare quante righe delle pagine sono generabili da `collect`
senza LLM. Nel wiki che abbiamo costruito oggi la sezione `## Collegamenti` di ogni pagina è, nella
sostanza, un backlink set curato a mano.

### 1.2 Riproducibilità dichiarata, e misurata

**Osservazione.** Sertor dice `zero LLM, offline` nel proprio `--help`, il che *implica* il
determinismo ma non lo **promette** né lo **verifica**.

**Cosa fa il concorrente.** `wiki-compiler` esegue la pipeline su corpus da 100, 1.000 e 5.000 file, su
Linux e su Windows, e **verifica che gli output coincidano esattamente**. Pubblica i tempi: 12,4 secondi
a 5.000 file, di cui il **56% speso nel lint**.

**Richiesta.** Due cose concrete:

1. Un test di **riproducibilità cross-OS** nel CI: stesso corpus, due sistemi, output identico byte per
   byte. È una garanzia che nessun sistema LLM-based può offrire, ed è il vostro fossato.
2. Un **benchmark di scalabilità** di `lint` e `collect`. Domanda specifica, che non abbiamo potuto
   verificare: il rilevamento degli orfani è O(n²) sul numero di pagine? Il concorrente riporta di aver
   dovuto passare da O(n²) a scaling quasi-lineare, e che il lint domina il tempo totale. Se Sertor ha
   lo stesso profilo, il problema si manifesterà su un wiki grande, non su quelli attuali.

### 1.3 I limiti del deterministico, da non ignorare

Per onestà verso il team: il modello puro **fallisce producendo struttura corretta e vuota**. Il suo
autore ammette che il grafo usa corrispondenza esatta — *"se una nota dice 'gradient descent' e l'altra
'optimization step' senza la frase letterale, non si collegano"* — e che *"nulla in questa pipeline
capisce il significato."*

**Non chiedete al core di scrivere prosa.** La prova, dal nostro dogfooding: la sintesi più preziosa
prodotta oggi lega un articolo su Talos (rianalisi genomica), uno di HBR sui middle manager e uno sulla
valutazione degli LLM. **Quei tre testi non condividono una sola frase.** Condividono una struttura
argomentativa. Un grafo lessicale non li avrebbe mai collegati. Simmetricamente, la riga
`broken_links=0 orphans=0 missing_frontmatter=0` che ci ha dato `sertor-wiki-tools lint` nessun LLM
può produrla in modo affidabile su sé stesso.

Le due promesse di un wiki — *è vero* e *i collegamenti esistono* — hanno bisogno di due macchine
diverse. Questa è la tesi da difendere.

---

## Parte 2 — Cosa prendere da OpenWiki (il lato agentico)

**Riferimento:** `langchain-ai/openwiki`, commit `681b25a` del 2026-07-09, MIT, `v0.1.0`. TypeScript,
~11.600 righe su 36 file, costruito su DeepAgents e LangGraph. Clonato e letto; **non eseguito**.

### 2.1 Ingestione: `ingest` esiste, i connettori no

**Osservazione.** Il playbook elenca `ingest` fra le operazioni, ma le fonti gliele porta l'utente.

**Cosa fa il concorrente.** Sette connettori in `src/connectors/sources/`: `git-repo`, `gmail`, `slack`,
`hackernews`, `web-search`, `x`, più un connettore `mcp` generico. Espone all'agente i tool
`openwiki_list_connectors`, `openwiki_ingest_connector`, `openwiki_ingest_all_connectors`,
`openwiki_list_raw_items`, `openwiki_read_raw_item`. Ha due modalità: `code` (documenta una codebase) e
`personal` (costruisce un cervello locale da fonti eterogenee in `~/.openwiki/wiki`).

**Perché ci riguarda.** La *personal mode* è **alla lettera il caso d'uso del nostro vault**: ingerire
fonti eterogenee e sintetizzarle in una wiki locale. Noi lo facciamo con un agente esterno che produce
riassunti e un `git pull`.

**Richiesta.** Valutare un'**interfaccia connettore** nel core, con `git-repo` come primo caso. Nota di
coerenza architetturale: un connettore *ingerisce byte*, non genera prosa — sta quindi **dal lato
deterministico del confine**, e non minaccia la separazione. È un'estensione naturale, non un
compromesso.

### 2.2 Manutenzione: oggi solo session-driven

**Osservazione.** L'hook `wiki-pending-check` invoca `sertor-wiki-tools scan`, che conta i file più
recenti dell'ultima voce di log e restituisce `wiki.scan/1` con il numero di `pending`. Il wiki ti
ricorda di aggiornarlo **quando hai lavorato**.

**Cosa fa il concorrente.** OpenWiki è **guidato dal tempo**: installa una GitHub Action (cron di
default `0 8 * * *`) o un job GitLab CI, conserva il `gitHead` dell'ultimo run in
`openwiki/.last-update.json` e da lì calcola il diff. La documentazione si aggiorna anche se nessuno
apre una sessione.

**Osservazione strategica.** `scan` è **a un passo** dall'update diff-driven: già confronta lo stato del
repo con l'ultima voce di log. Manca il pezzo che, dato quel delta, produce un *piano di lavoro* per il
curatore — quali pagine sono probabilmente stantie, quali file nuovi non sono mai stati documentati.

**Domanda al team.** Ha senso un `sertor-wiki-tools plan` che, senza LLM, emetta un contratto
`wiki.plan/1` con: file toccati dall'ultima entry, pagine che li citano, pagine mai aggiornate da N
giorni? Sarebbe il lato deterministico che *prepara il lavoro* per il lato di giudizio. Nessuna prosa,
solo aritmetica sui timestamp e sui `sources:` del frontmatter.

### 2.3 Cosa NON prendere da OpenWiki

Nel sorgente di OpenWiki **non esiste alcuna validazione deterministica**: abbiamo cercato controlli su
wikilink rotti, pagine orfane, frontmatter mancante e non ne abbiamo trovato nessuno. Ogni garanzia
sulla correttezza del wiki è prodotta da un modello linguistico, e il revisore della PR aperta dal cron
non ha in mano alcun rapporto di verifica.

È una scelta coerente col loro obiettivo (girare headless in CI, dove non c'è nessuno a cui riportare
un lint fallito). **Non è una scelta da imitare.**

---

## Parte 3 — Difetti trovati durante il dogfooding

Fatti osservati oggi, non ipotesi. Sono la parte più azionabile del documento.

### 3.1 Le ergonomie spingono l'LLM ad aggirare il core deterministico

**Questo è il rilievo che consideriamo più importante di tutto il documento.**

Costruendo il wiki, **abbiamo scritto `index.md` a mano** invece di usare `upsert-index`. L'agente
`wiki-curator`, delegato in background, ha fatto lo stesso. Nessuno dei due ha disobbedito: semplicemente
scrivere il file era la strada più breve, e nulla nel flusso ce lo impediva.

**La conseguenza è sistemica.** Le garanzie del core deterministico valgono solo se il core viene
*attraversato*. Un LLM che scrive direttamente i file ottiene lo stesso risultato apparente e perde
l'idempotenza, i contratti JSON e la verificabilità. **Il confine D↔N non è difeso da nulla se non
dalla buona volontà dell'assistente.**

Domande al team:

- Il lint potrebbe rilevare una `index.md` **non conforme** a ciò che `upsert-index` avrebbe prodotto?
- Vale la pena rendere `upsert-index` la via *più comoda*, non solo la via corretta?
- Andrebbe misurato: in quante sessioni reali il core viene effettivamente invocato, e in quante l'LLM
  scrive a mano? Il dato di oggi, su un progetto ben istruito, è **zero invocazioni di `upsert-index`**.

### 3.2 L'hook `SessionStart` viola il Principio X (host-agnosticismo)

**Verificato leggendo `.claude/hooks/wiki-session-start.ps1`.** La direttiva emessa contiene percorsi
**hard-coded**, non letti da `wiki.config.toml`:

```powershell
"1. Read (...): wiki/syntheses/roadmap.md ; wiki/log/$log (...). Read wiki/index.md (...)"
"2. Then show (...) the block between the markers <!-- EXEC:START --> and <!-- EXEC:END --> of wiki/syntheses/roadmap.md."
```

Tre problemi distinti:

1. **`wiki/syntheses/roadmap.md` è un'assunzione, non una configurazione.** Il nome `syntheses` viene
   dalla tassonomia del config; `roadmap.md` non esiste in nessun config. Il playbook proclama *"the
   host is configured, not assumed"*, e qui l'ospite è assunto.

2. **`structure init` non crea `roadmap.md`.** Da `structure.py`, i seed creati sono `index_file` e
   `log_file` più le cartelle della tassonomia. Ne segue che **ogni wiki appena inizializzato produce,
   alla sessione successiva, una direttiva che punta a un file inesistente.** È esattamente ciò che è
   accaduto nel nostro progetto: la sessione si è aperta con due letture fallite.

3. **Il fallback sul log è sbagliato.** Se `wiki/log/` non esiste, lo script imposta `$log = 'log.md'`,
   ma poi compone comunque `wiki/log/$log`, cioè `wiki/log/log.md` — che non esiste. Il file piatto sta
   in `wiki/log.md`. Con `log_dir = "log"` dichiarato nel config e un log ancora monolitico (stato
   normale prima di `migrate`), la direttiva è **doppiamente rotta**.

**Impatto.** Fallimento silenzioso all'avvio di ogni sessione su un wiki nuovo. L'assistente legge due
file inesistenti, non mostra la exec summary e, se è meno pignolo di così, non lo dice all'utente.

**Richiesta.** Rendere i percorsi funzione del profilo; far creare a `structure init` uno `roadmap.md`
seed con i marker `EXEC:START`/`EXEC:END` già dentro (oppure rendere la direttiva tollerante alla sua
assenza, dichiarandolo); correggere il fallback del log.

### 3.3 Il lint semantico non ha supporto dal core, e potrebbe averne

**Osservazione.** Il livello B (verificare che il wiki non sia andato alla deriva rispetto alla realtà)
è giudizio puro, e giustamente resta all'LLM. Ma **il core può restringere lo spazio di ricerca.**

**Prova sul campo, di oggi.** Una nota del nostro corpus, salvata **sette giorni fa**, documentava il
comando `openwiki --init`. Leggendo il repo abbiamo scoperto che quel comando **non esiste più**: oggi
sono `openwiki personal --init` e `openwiki code --init`. Sette giorni, e le istruzioni erano già
sbagliate — dentro un vault che studia proprio il problema della documentazione che invecchia.

**Proposta.** Un'operazione deterministica che marchi i **passivi**: pagine che contengono comandi,
numeri di versione, URL o riferimenti a file, ordinate per età dell'ultimo `updated:`. Nessun giudizio,
solo pattern matching e aritmetica sulle date. L'output è una **coda di riverifica** che l'LLM lavora.

È la stessa divisione del lavoro di sempre: il codice dice *dove guardare*, l'LLM dice *se è ancora
vero*.

---

## Parte 4 — Cosa NON abbiamo verificato

Dichiarato perché il team non lo dia per assodato:

- **Non abbiamo eseguito OpenWiki né `wiki-compiler`.** Nessun `npm install`, nessuna generazione. La
  qualità reale delle wiki che producono ci è ignota; conosciamo solo la loro architettura.
- I dati su `wiki-compiler` vengono **dall'articolo dell'autore**, non da una nostra esecuzione dei
  benchmark. Sono numeri autodichiarati.
- OpenWiki è a `v0.1.0` con commit di oggi: **software in movimento**. Qualunque affermazione qui
  invecchierà.
- Non abbiamo letto per intero le 413 righe di `src/agent/prompt.ts`, dove vive il comportamento reale
  del loro agente. Le nostre conclusioni sull'assenza di validazione derivano da ricerca nel sorgente
  (`brokenLink`, `orphan`, `validateWiki`: nessuna occorrenza), non da una lettura riga per riga.
- Non abbiamo misurato la complessità asintotica di `lint`: la domanda in §1.2 è un sospetto per
  analogia col concorrente, non un rilievo.
- `nvk/llm-wiki` (820★, MIT, `v0.15.0`) lo conosciamo solo dalla documentazione pubblica, non dal codice.

## Riepilogo delle richieste, in ordine di valore percepito

1. **§3.1** — Indagare quanto spesso il core deterministico viene *aggirato* dall'LLM. Se il confine non
   è difeso, le garanzie sono nominali. *(Nessuna riga di codice nuova richiesta: prima serve il dato.)*
2. **§3.2** — Correggere l'hook `SessionStart`: percorsi dal profilo, seed di `roadmap.md`, fallback del
   log. Bug riproducibile su ogni wiki nuovo.
3. **§1.1** — Valutare la generazione deterministica dei backlink da `collect`. Il dato c'è già.
4. **§3.3** — Coda di riverifica dei "passivi" (comandi, versioni, URL) ordinata per età.
5. **§2.2** — `plan`: dal `scan` a un piano di lavoro per il curatore, senza LLM.
6. **§1.2** — Test di riproducibilità cross-OS nel CI e benchmark di scalabilità del lint.
7. **§2.1** — Interfaccia connettore per `ingest`, partendo da `git-repo`.

**E una richiesta a costo zero:** il confine fra nucleo deterministico e giudizio è la cosa migliore che
Sertor ha, ed è *documentata in un playbook che nessuno legge se non l'assistente*. Due progetti
indipendenti ci sono arrivati per conto loro. Vale la pena dirlo ad alta voce, fuori.

---

## Materiale di riferimento

- Analisi completa e ragionata: `wiki/syntheses/openwiki-vs-sertor-wiki.md` nel vault *Nunzio Summaries*.
- OpenWiki: <https://github.com/langchain-ai/openwiki> — clonato in `C:\Workspace\Git\ExternalRepos\openwiki`.
- `wiki-compiler`: <https://github.com/Emmimal/wiki-compiler> — articolo su Towards Data Science, 2026-07-03.
- `nvk/llm-wiki`: <https://github.com/nvk/llm-wiki>.
- Segnalazione correlata, stessa cartella: `memory-archive-silenzioso-path-con-spazi.md`.
