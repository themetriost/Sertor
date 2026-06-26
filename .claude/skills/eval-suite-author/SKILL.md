---
name: eval-suite-author
description: "Assisted authoring of the evaluation suite (ground-truth). Use it whenever evaluation cases need to be created or grown. Triggers on 'create eval cases', 'build the ground-truth suite', 'add a retrieval test case', 'add a graph navigation case', or wanting to measure retrieval/graph quality on this corpus. Authors retrieval cases (query -> expected path) and code-graph navigation cases (relation + symbol -> expected set of refs): using the project's RAG/MCP tools over the indexed corpus, the agent DERIVES candidates, proposes them for approval, and persists ONLY the approved ones by invoking the CLI subcommands `eval add-case` / `graph-eval add-case`. It never runs the evaluation (that is deterministic and does not depend on this skill); it never imports the core library."
argument-hint: "Descrivi l'area/funzionalità del corpus per cui vuoi creare casi di valutazione (es. 'il retrieval sui simboli del dominio')"
user-invocable: true
disable-model-invocation: false
---

## User Input

Il testo che ha invocato questa capacità **è** l'area del corpus per cui derivare casi di valutazione
(es. «i simboli pubblici del core», «le query architetturali sulla composizione»). Se è vuoto, chiedi
all'utente di descrivere l'area o l'obiettivo della suite.

## Scopo

Questa skill aiuta a **costruire la suite di valutazione** (`eval/suite.toml`) — l'insieme di coppie
`query → path attesi` con cui si misura la pertinenza del retrieval (hit-rate@k / MRR). È **genesi
assistita**: l'agente *propone*, l'utente *approva*, e solo gli approvati vengono scritti. La misura
vera e propria (`eval run`) è **deterministica** e **non dipende da questa skill né da alcun LLM**:
qui si cura solo il *dato* (la suite), non l'esecuzione.

## Confine vincolante (D↔N)

- **Niente esecuzione, niente import della libreria.** Questa skill NON valuta e NON importa il core.
  Ogni scrittura passa **solo** dal vehicle CLI: `sertor-rag eval add-case`. Non accedere mai alla
  libreria direttamente né alle factory `build_*`. È il Principio XI: si accede a Sertor solo via
  vehicle (CLI o MCP).
- **Solo casi approvati.** Nessun candidato viene persistito senza un'approvazione esplicita
  dell'utente. L'agente propone; l'utente decide; l'agente scrive gli accettati.

## Prerequisito: il corpus dev'essere indicizzato

La derivazione legge il corpus tramite i tool RAG/MCP (ricerca codice/doc, ricerca simboli). Se il
corpus non è indicizzato, questi tool tornano vuoti o in errore: in tal caso **fermati con un
messaggio azionabile** —

> «Il corpus non risulta indicizzato. Indicizzalo prima con `sertor-rag index .`, poi rilancia.»

Per verificare in modo deterministico che un path candidato esista davvero nell'indice, usa il
vehicle: `sertor-rag eval validate-path <path> [...]` (esce sempre 0; riporta `missing`/`checked`).

## Procedura

1. **Inquadra l'area.** Dall'input individua l'area/funzionalità del corpus su cui creare casi
   (simboli specifici, file architetturali, comportamenti).

2. **Deriva candidati con i tool RAG/MCP.** Per ogni candidato formula una **query** realistica
   (come la scriverebbe un utente o un agente) e individua il **path atteso** — il file che *dovrebbe*
   comparire tra i risultati. Mescola due tipi (campo `kind`, opzionale ma consigliato):
   - `symbol` — query a simbolo esatto (nome di classe/funzione/errore). Usa la ricerca simboli del
     grafo per trovare dove è definito.
   - `nl` — query architetturale in linguaggio naturale (un concetto/comportamento). Usa la ricerca
     combinata codice+doc.

3. **Verifica i path candidati.** Per ciascun `expected`, controlla che sia presente nell'indice con
   `sertor-rag eval validate-path <path>`. Se manca, o correggi il path, o segnalalo all'utente (un
   path fuori indice non potrà mai essere un hit).

4. **Proponi all'utente.** Presenta i candidati come una lista chiara `query → expected (kind)` e
   chiedi quali approvare. Spiega brevemente il razionale di ciascuno (perché quel file è atteso).

5. **Persisti SOLO gli approvati.** Per ogni caso approvato invoca il vehicle:

   ```powershell
   sertor-rag eval add-case --query "<la query>" `
       --expected "<percorso/atteso.ext>" --kind symbol
   ```

   Se un path atteso non è nell'indice, il comando avvisa e richiede `--confirm` prima di scrivere
   (REQ-012): inoltralo all'utente, non forzare il `--confirm` di tua iniziativa. `add-case` è
   idempotente (una query già presente non viene duplicata) e non-distruttivo.

6. **Chiudi.** Riepiloga quali casi sono stati aggiunti e ricorda che la suite è **dato versionato**:
   va committata. La valutazione si lancia con `sertor-rag eval run` (deterministica, indipendente).

## Genesi di casi di navigazione del grafo (`[[graph_case]]`)

Oltre ai casi di retrieval, la suite può contenere casi di **navigazione del grafo del codice**: un
caso = **relazione + simbolo target → insieme atteso di `ref`** (`path#qualname`). La metrica è a
**insiemi** (precision/recall/F1), non a rank. Relazioni MVP supportate: `who_calls` (chi chiama il
simbolo) e `defines` (dove è definito). Anche qui la genesi è assistita: l'agente propone uno
**snapshot deterministico**, l'utente approva, e solo gli approvati vengono scritti.

1. **Naviga lo stato corrente del grafo (snapshot deterministico).** Per la relazione+simbolo
   richiesti, ottieni l'insieme candidato di `ref` invocando il vehicle deterministico:

   ```powershell
   sertor-rag graph-eval validate-ref --relation who_calls --target build_facade --json
   ```

   L'output JSON riporta `checked`/`unverifiable`/`graph_available`. Per *scoprire* l'insieme
   corrente (snapshot), passa l'insieme che ti aspetti e leggi quali risultano `unverifiable`, oppure
   ricava i `ref` reali dai tool RAG/MCP (ricerca simboli / chi-chiama) e confrontali. L'insieme
   candidato è **ciò che il grafo restituisce ora**, non un giudizio autonomo dell'agente.

2. **Proponi l'insieme all'utente.** Presenta l'insieme candidato di `ref` come **proposta da
   approvare** (è uno snapshot: «oggi questi sono i chiamanti di `X`»). Spiega che l'insieme diventerà
   il valore atteso del caso e che il gate ne misurerà la non-regressione.

3. **Persisti SOLO dopo approvazione esplicita.** Per ogni caso approvato:

   ```powershell
   sertor-rag graph-eval add-case --relation who_calls --target build_facade `
       --expected "src/.../a.py#A,src/.../b.py#B" --confirm
   ```

   - Mai scrittura implicita o automatica: l'utente deve **approvare** l'insieme prima.
   - Se la verifica riporta `ref` **non verificabili** (`unverifiable` non vuoto): **nominali**
     all'utente e offri di escluderli o di procedere comunque con `--confirm`. Non forzare `--confirm`
     di tua iniziativa.
   - `add-case` è **idempotente** su `(relation, target)` e non-distruttivo (preserva i casi di
     retrieval `[[case]]` e gli altri `[[graph_case]]`).
   - Un caso con insieme atteso **vuoto** è legittimo (atteso «nessun chiamante»): usa
     `--expected ""`.

4. **Ri-authoring di uno snapshot esistente.** Se l'insieme corretto è cambiato e l'utente lo
   approva, aggiorna il caso con `sertor-rag graph-eval amend-case --relation R --target T
   --expected "..."`. È il percorso deterministico di re-congelamento dello snapshot; la decisione
   resta dell'utente.

5. **Se il grafo non è costruito** (`graph_available=false`): **fermati con un messaggio azionabile**
   — «Il grafo del codice non risulta costruito. Indicizza prima il progetto con `sertor-rag index
   .`, poi rilancia.»

**Confine D↔N (vincolante anche qui).** Il run deterministico (`sertor-rag graph-eval run`) **non
dipende** da questa skill né da alcun LLM: la skill è la superficie di *giudizio* (proporre/approvare
gli insiemi), il run è la *misura* deterministica nel core. Ogni accesso al grafo passa **solo** dai
sottocomandi `graph-eval validate-ref`/`add-case`/`amend-case` (vehicle, Principio XI): la skill non
importa mai la libreria del core.

## Cosa NON fare

- Non scrivere mai segreti nella suite (è dato versionato e diffabile a mano).
- Non inventare path/ref: ogni `expected` dev'essere reale (verificato con `validate-path` per i
  casi di retrieval, con `graph-eval validate-ref` per i casi di navigazione).
- Non eseguire la valutazione al posto dell'utente come se fosse parte della genesi: sono fasi
  separate (genesi = giudizio assistito; run = misura deterministica).
