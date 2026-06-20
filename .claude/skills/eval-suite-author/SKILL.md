---
name: eval-suite-author
description: "Genesi assistita della suite di valutazione del retrieval (ground-truth). L'agente, usando i tool RAG/MCP del corpus indicizzato, deriva candidati (query → path atteso), li propone all'utente per approvazione e persiste SOLO gli approvati invocando il sottocomando CLI `eval add-case`. Non esegue mai la valutazione (è deterministica e non dipende da questa skill); non importa mai la libreria del core."
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

## Cosa NON fare

- Non scrivere mai segreti nella suite (è dato versionato e diffabile a mano).
- Non inventare path: ogni `expected` dev'essere un file reale dell'indice (verificato con
  `validate-path`).
- Non eseguire la valutazione al posto dell'utente come se fosse parte della genesi: sono fasi
  separate (genesi = giudizio assistito; run = misura deterministica).
