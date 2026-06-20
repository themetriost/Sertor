---
name: eval-feedback
description: "Feedback esplicito di pertinenza: l'agente osserva i risultati di una ricerca, riceve dall'utente il giudizio (pertinente / non pertinente) e raffina la suite di valutazione di conseguenza, aggiornando gli `expected` del caso corrispondente — sempre tramite il vehicle CLI `sertor-rag eval add-case`. Nessun giudizio viene mai inferito o persistito senza azione esplicita dell'utente. Non importa mai la libreria del core."
argument-hint: "La query di cui stai valutando i risultati (o lascia vuoto e parti da una ricerca appena fatta)"
user-invocable: true
disable-model-invocation: false
---

## User Input

Il testo che ha invocato questa capacità è la **query** di cui si sta valutando la pertinenza dei
risultati. Se è vuoto, parti dall'ultima ricerca fatta o chiedi all'utente quale query considerare.

## Scopo

Questa skill cattura il **feedback esplicito** dell'utente su quanto un retrieval è pertinente, e lo
traduce in un raffinamento della **suite di valutazione** (`eval/suite.toml`): se l'utente indica che
un certo file *era* il risultato giusto per una query (o che quello restituito *non* lo era), la suite
viene aggiornata così che la misura futura (`eval run`) catturi quel giudizio. È il ciclo di
miglioramento del ground-truth a partire dall'uso reale.

## Confine vincolante (nessun giudizio implicito)

- **Mai inferire, mai persistire senza azione esplicita** (REQ-051): ogni modifica alla suite richiede
  una conferma esplicita dell'utente. Non esiste una modalità «automatica»: l'agente non deduce la
  pertinenza dai punteggi né scrive da solo. Propone; l'utente conferma; l'agente scrive.
- **Solo via vehicle** (Principio XI): ogni scrittura passa dal sottocomando CLI
  `sertor-rag eval add-case`. Non accedere mai alla libreria del core direttamente.

## Procedura

1. **Osserva i risultati.** Considera la query e i risultati che il retrieval ha restituito (es. da
   `sertor-rag search`). Mostrali all'utente in modo leggibile (path + perché potrebbe essere
   pertinente o no).

2. **Raccogli il giudizio esplicito.** Chiedi all'utente, per la query, quale/i file è *davvero* il
   risultato atteso (pertinente). Il giudizio è dell'utente, non tuo: non assegnarlo da solo.

3. **Verifica i path.** Controlla che i path indicati esistano nell'indice con
   `sertor-rag eval validate-path <path>` (esce sempre 0; segnala `missing`). Un atteso fuori indice
   non potrà mai essere un hit: segnalalo.

4. **Aggiorna la suite, su conferma.**
   - **Caso già nella suite** — se esiste un caso per quella query, proponi di aggiornarne gli
     `expected` con i path che l'utente ha confermato pertinenti; applica solo dopo conferma.
   - **Caso assente** (REQ-052) — se non c'è un caso per quella query, **offri di crearne uno nuovo**
     con i path approvati; crea solo dopo conferma.

   In entrambi i casi la scrittura passa dal vehicle:

   ```powershell
   sertor-rag eval add-case --query "<la query>" `
       --expected "<path approvato>[,<altro>]" --kind nl
   ```

   `add-case` è idempotente (una query già presente non viene duplicata) e non-distruttivo; se un path
   non è nell'indice il comando richiede `--confirm` — inoltra la richiesta all'utente, non forzarla.

5. **Chiudi.** Riepiloga cosa è stato aggiornato e ricorda che la suite è **dato versionato** (va
   committata) e che la misura (`sertor-rag eval run`) resta **deterministica e indipendente** da
   questa skill.

## Cosa NON fare

- Non dedurre la pertinenza dai punteggi di similarità e scriverla in autonomia.
- Non avere/usare una modalità automatica: ogni azione di scrittura passa dalla conferma dell'utente e
  dal CLI.
- Non scrivere segreti nella suite.
