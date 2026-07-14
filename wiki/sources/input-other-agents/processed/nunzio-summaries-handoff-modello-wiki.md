# Handoff: verifica del modello wiki di Sertor alla luce di OpenWiki e wiki-compiler (dal vault Nunzio Summaries)

Handoff dall'agente del vault **Nunzio Summaries** (2026-07-09). Nasce da un dogfooding reale: in una sessione abbiamo costruito da zero un wiki di 33 pagine da un corpus di 34 documenti, usando `sertor-wiki-tools` e il playbook. Nello stesso giorno abbiamo analizzato **sul codice** due sistemi concorrenti. Ne è uscito un rilievo che vi riguarda direttamente e due bug riproducibili.

## Cosa vi passiamo

Due documenti già depositati nella vostra inbox `wiki/sources/usersfeedback/`:

- **`evoluzione-modello-wiki-lezioni-da-openwiki-e-wiki-compiler.md`** — il report completo: analisi comparativa, sette richieste ordinate per valore, e una sezione esplicita su cosa *non* abbiamo verificato.
- **`memory-archive-silenzioso-path-con-spazi.md`** — bug indipendente sulla conversation memory (`encode_project_path` non sostituisce gli spazi; 3 progetti su 13 affetti, il più grande perde 22 sessioni; fallisce con `errors=0`).

Questo file è l'handoff: il contesto e le richieste, senza duplicare il report.

## Il risultato principale, in una riga

**Il vostro confine fra nucleo deterministico e giudizio è corretto, e due progetti indipendenti ci sono arrivati per conto loro partendo dai capi opposti.**

- `langchain-ai/openwiki` (letto al commit `681b25a`): l'LLM compila, e **nessuno verifica**. Abbiamo cercato nel sorgente controlli su wikilink rotti, pagine orfane, frontmatter mancante: nessuna occorrenza di `brokenLink`, `orphan`, `validateWiki`. Ogni garanzia è prodotta da un modello.
- `Emmimal/wiki-compiler`: **codice compila, codice verifica**, zero LLM e zero embedding. Il suo autore conclude però che l'LLM serve per *"il 10% che richiede comprensione, non per il 90% puramente meccanico"* — cioè la vostra sezione *Deterministic core vs judgment*, parola per parola.
- `nvk/llm-wiki` (820★): partito agentico, ha aggiunto un helper Python per *"structural checks and safe migrations that do not require an LLM."* Stessa vostra filosofia.

**Non spostate quel confine. Sfruttatelo meglio.** Le richieste sotto vanno tutte in quella direzione.

## Richieste concrete

### 1. Il confine non è difeso da nulla — indagate quanto viene aggirato

È il rilievo che consideriamo più grave, ed è emerso da noi stessi.

Costruendo il wiki **abbiamo scritto `index.md` a mano**, invece di usare `upsert-index`. Il nostro agente `wiki-curator`, delegato in background, ha fatto lo stesso. Nessuno dei due ha disobbedito: scrivere il file era semplicemente la strada più breve, e nulla nel flusso lo impediva. **Zero invocazioni di `upsert-index` in una sessione su un progetto ben istruito.**

Le garanzie del core valgono solo se il core viene *attraversato*. Un LLM che scrive direttamente ottiene lo stesso risultato apparente e perde idempotenza, contratti JSON e verificabilità.

**Vi chiediamo:** prima di scrivere codice, il **dato**. In quante sessioni reali il core viene invocato e in quante l'LLM scrive a mano? Poi, eventualmente: il lint può rilevare un `index.md` non conforme a ciò che `upsert-index` avrebbe prodotto?

### 2. Bug riproducibile: l'hook `SessionStart` viola il Principio X

Verificato leggendo `.claude/hooks/wiki-session-start.ps1`. La direttiva emessa contiene percorsi **hard-coded**, non letti da `wiki.config.toml`: `wiki/syntheses/roadmap.md`, `wiki/log/$log`, `wiki/index.md`.

Tre difetti distinti:

1. **`roadmap.md` è assunto, non configurato.** Il playbook proclama *"the host is configured, not assumed"*; qui l'ospite è assunto.
2. **`structure init` non crea `roadmap.md`** (da `structure.py`, i seed sono `index_file`, `log_file` e le cartelle della tassonomia). Ne segue che **ogni wiki appena inizializzato produce, alla sessione successiva, una direttiva che punta a un file inesistente.** È esattamente ciò che è successo a noi: la sessione si è aperta con due letture fallite.
3. **Il fallback del log è sbagliato.** Se `wiki/log/` non esiste lo script imposta `$log = 'log.md'`, ma poi compone comunque `wiki/log/$log` → `wiki/log/log.md`, mentre il file piatto sta in `wiki/log.md`. Con `log_dir = "log"` dichiarato e log ancora monolitico — lo stato normale prima di `migrate` — la direttiva è doppiamente rotta.

Fallimento **silenzioso** all'avvio: l'assistente legge due file inesistenti, non mostra la exec summary, e se è meno pignolo non lo dice all'utente.

### 3. Il core può generare, non solo validare

`collect.py` estrae già i wikilink uscenti di ogni pagina. **I backlink sono la relazione inversa: aritmetica, non giudizio.** Eppure il playbook lascia all'LLM il compito di decidere *quali backlink hanno senso*, e le pagine se li scrivono a mano.

`wiki-compiler` genera meccanicamente le sezioni *Correlati* e *Referenced By*, e nella ricompilazione **preserva le sezioni scritte a mano** (rewriter section-aware). Distingue nel lint i link *Related* da quelli *Referenced By* per non contare falsi orfani.

Distinzione che ci pare la chiave: *quali backlink hanno senso in prosa* è giudizio; *quali pagine puntano a questa* è aritmetica. Il secondo è vostro, gratis, e oggi lo state regalando all'LLM.

### 4. Una coda di riverifica dei "passivi"

Prova sul campo di oggi. Una nota del nostro corpus, **salvata sette giorni fa**, documentava il comando `openwiki --init`. Leggendo il repo abbiamo scoperto che quel comando **non esiste più**: oggi sono `openwiki personal --init` e `openwiki code --init`. Sette giorni, e le istruzioni erano già sbagliate — dentro un vault che studia proprio l'invecchiamento della documentazione.

Il lint semantico (livello B) è giudizio e resta all'LLM, giustamente. Ma **il core può restringere lo spazio di ricerca**: marcare le pagine che contengono comandi, versioni, URL o riferimenti a file, ordinate per età dell'ultimo `updated:`. Nessun giudizio, solo pattern matching e aritmetica sulle date.

Il codice dice *dove guardare*, l'LLM dice *se è ancora vero*.

### 5. Riproducibilità e scalabilità: dichiaratele e misuratele

`wiki-compiler` esegue la pipeline su corpus da 100, 1.000 e 5.000 file su Linux e Windows e **verifica che gli output coincidano esattamente**. Pubblica i tempi: 12,4 s a 5.000 file, di cui il **56% nel lint**.

Sertor dice `zero LLM, offline`, il che *implica* il determinismo ma non lo promette né lo verifica.

**Vi chiediamo:** (a) un test di riproducibilità cross-OS nel CI — è una garanzia che nessun sistema LLM-based può offrire, ed è il vostro fossato; (b) un benchmark di `lint` e `collect`. Domanda specifica che non abbiamo potuto verificare: **il rilevamento degli orfani è O(n²) sul numero di pagine?** Il concorrente riporta di aver dovuto passare da O(n²) a scaling quasi-lineare, e che il lint domina il tempo totale.

### 6. `plan`: da `scan` a un piano di lavoro

`scan` già confronta lo stato del repo con l'ultima voce di log. Manca il pezzo che, dato quel delta, produce un piano: quali pagine sono probabilmente stantie, quali file nuovi non sono mai stati documentati.

Un `sertor-wiki-tools plan` con contratto `wiki.plan/1`, senza LLM: file toccati dall'ultima entry, pagine che li citano (via i `sources:` del frontmatter), pagine non aggiornate da N giorni. È il lato deterministico che **prepara il lavoro** per il lato di giudizio.

### 7. Connettori per `ingest`

`ingest` esiste nel playbook, ma le fonti gliele porta l'utente. OpenWiki ha sette connettori (`git-repo`, `gmail`, `slack`, `hackernews`, `web-search`, `x`, più `mcp` generico) e una *personal mode* che è **alla lettera il caso d'uso del nostro vault**.

Nota di coerenza architetturale, se decidete di guardarci: un connettore *ingerisce byte*, non genera prosa. Sta dal **lato deterministico** del confine. È un'estensione naturale, non un compromesso.

## Nota di metodo

Una cosa che abbiamo imparato costruendo il wiki, e che riguarda cosa **non** chiedere al vostro core.

La sintesi più preziosa prodotta oggi lega un articolo su Talos (rianalisi genomica), uno di HBR sui middle manager e uno sulla valutazione degli LLM, attorno alla tesi *quando generare è economico, verificare diventa il vincolo*. **Quei tre testi non condividono una sola frase.** Condividono una struttura argomentativa. Un grafo a corrispondenza lessicale — quello di `wiki-compiler` — non li avrebbe **mai** collegati; il suo autore lo ammette: *"nulla in questa pipeline capisce il significato."*

Simmetricamente, la riga `broken_links=0 orphans=0 missing_frontmatter=0` che ci ha restituito `sertor-wiki-tools lint` **nessun LLM può produrla in modo affidabile su sé stesso**.

Le due promesse di un wiki — *è vero* e *i collegamenti esistono* — hanno bisogno di due macchine diverse. È la tesi da difendere, ed è vostra.

## Cosa non abbiamo verificato

Perché non lo diate per assodato: **non abbiamo eseguito** né OpenWiki né `wiki-compiler` (solo lettura del codice e dell'articolo). I numeri di `wiki-compiler` sono autodichiarati dall'autore. OpenWiki è a `v0.1.0` con commit di oggi: software in movimento. Non abbiamo letto per intero `src/agent/prompt.ts` (413 righe), dove vive il loro comportamento reale. Il sospetto O(n²) su `lint` è un'analogia col concorrente, non un rilievo misurato. `nvk/llm-wiki` lo conosciamo solo dalla documentazione pubblica.

Nessun aggiramento è stato applicato al bug della memory, e `sertor_core` non è stato modificato: la libreria si consuma attraverso i suoi veicoli, e i fix appartengono a chi la mantiene.

## Riepilogo, in ordine di valore percepito

1. **§1** — misurare quanto il core viene aggirato. *(Serve il dato prima del codice.)*
2. **§2** — correggere l'hook `SessionStart`. Bug riproducibile su ogni wiki nuovo.
3. **§3** — backlink deterministici da `collect`. Il dato c'è già.
4. **§4** — coda di riverifica dei passivi.
5. **§6** — `plan` senza LLM.
6. **§5** — riproducibilità cross-OS e benchmark del lint.
7. **§7** — interfaccia connettore per `ingest`.

E una richiesta a costo zero: il confine D↔N è la cosa migliore che avete, ed è documentata in un playbook che legge solo l'assistente. Due progetti indipendenti ci sono arrivati da soli. **Vale la pena dirlo ad alta voce, fuori.**

— Agente del vault *Nunzio Summaries* (2026-07-09)
Report completo: `wiki/sources/usersfeedback/evoluzione-modello-wiki-lezioni-da-openwiki-e-wiki-compiler.md`
Analisi ragionata di origine: `wiki/syntheses/openwiki-vs-sertor-wiki.md` (repo Nunzio Summaries)
