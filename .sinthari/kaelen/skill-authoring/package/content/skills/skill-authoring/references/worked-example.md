# Esempi lavorati

Due cicli completi, ridotti all'essenziale: una creazione e una modifica. I comandi sono quelli del runtime
(vedi `references/runtime.md` per come si invocano sul tuo ospite).

---

## Esempio 1 — `create`: una skill che scrive note di rilascio

**Richiesta dell'autore:** "Voglio una skill che, dato un intervallo di commit, scriva le note di rilascio
per gli utenti."

### 1. Intento

Prima di scrivere chiedi ciò che non si deduce, e riassumi per conferma:

- **Cosa fa:** dato un intervallo `A..B`, produce note di rilascio leggibili da utenti non tecnici.
- **Quando si attiva:** "scrivi le note di rilascio", "cosa è cambiato in questa versione", "changelog per
  gli utenti".
- **Output atteso:** un file Markdown con sezioni Novità, Correzioni e Da sapere.
- **Confine con le skill vicine:** non genera requisiti da un diff (è un'altra skill) e non tagga né
  pubblica la release.

L'autore conferma; solo allora si scrive.

### 2. Scrittura

Corpo snello. Il formato delle note va in `references/format.md` e un esempio di output in
`references/example-notes.md`. La regola "non inventare cambiamenti che non sono nei commit" porta il suo
perché: *una nota di rilascio sbagliata promette agli utenti qualcosa che il software non fa.*

```
skillauthor lint release-notes
```
Esito: `nessun bloccante`. Al primo giro c'era un R, perché il corpo citava `references/format.md` prima che
il file esistesse.

### 3. Confine

La regola "non inventare cambiamenti" si può garantire con un runtime? In parte sì: un comando potrebbe
estrarre l'elenco dei commit e la skill citerebbe solo quelli. L'autore decide di **non** scrivere il
runtime adesso, e lo registra fra le decisioni di scrittura: *regola di giudizio, perché scritto; candidata a
runtime (estrazione dei commit), rinviata dall'autore.*

### 4. Collaudo

`evals/evals.json`, con 3 casi e asserzioni etichettate:

```json
{"skill_name": "release-notes", "evals": [
  {"id": 1, "prompt": "Note di rilascio per v1.2..v1.3 di questo repo", "expectations": [
    {"text": "Ogni voce delle note corrisponde a un commit dell'intervallo", "kind": "merit"},
    {"text": "Le note hanno le sezioni Novità, Correzioni, Da sapere", "kind": "protocol"}]}
]}
```

```
skillauthor cost release-notes
```
Esito: 3 casi × 2 × 1 = 6 esecuzioni + 6 valutazioni. Lo dici all'autore, che conferma. Poi esegui ogni caso
con la skill e senza, ognuno in un sottoagente nuovo, e fai valutare ogni esecuzione dal valutatore
(`vendor/skill-creator/agents/grader.md`).

```
skillauthor verdict release-notes-workspace --evals release-notes/evals/evals.json
```
Esito: `validated`. L'asserzione di merito del caso 1 separa (1.00 contro 0.00): il baseline aveva
inventato una voce.

### 5. Revisione

Esegui `skill-review` sulla skill e trascrivi i finding in `review.json`:

```json
{"skill_name": "release-notes", "round": 1, "findings": [
  {"id": "B1", "severity": "blocking", "summary": "Non dice cosa fare se l'intervallo è vuoto", "status": "open"},
  {"id": "M1", "severity": "improvement", "summary": "Description poco distinta dalla skill di changelog tecnico", "status": "open"}]}
```

B1 è bloccante: aggiungi la gestione dell'intervallo vuoto alla sezione sui modi di guasto, e B1 diventa
`resolved` (lo conferma un secondo giro di revisione). M1 lo decide l'autore.

### 6. Chiusura

```
skillauthor ready release-notes --review review.json --verdict verdict.json
```
Esito: `ready`. Copi la skill nella cartella installata, controlli con `skillauthor parity` e consegni il
rapporto, con le decisioni di scrittura da registrare nel wiki del progetto.

---

## Esempio 2 — `modify`: applicare una revisione

**Ingresso:** una skill esistente e una revisione con un bloccante, *B1: "il comando `verify` è citato ma lo
schema del suo output non è allegato"*.

1. **Leggi tutto:** `SKILL.md` e ogni allegato, prima di proporre qualunque cosa.
2. **Proponi per finding:** "*B1 → allego `references/schemas/verify-output.schema.json` e lo cito nel
   passo 3.*" L'autore approva. Solo ora scrivi.
3. **Lint:** ora la citazione si risolve. Se avessi citato lo schema senza allegarlo, sarebbe uscito un R.
4. **Collaudo:** la modifica cambia l'impronta della skill, quindi il verdetto di prima non vale più. Il
   collaudo si ripete, anche ridotto, con l'accordo dell'autore sul costo. Se l'autore decide di non
   ripeterlo, il gate risponde `verdict-stale` e la skill non si può dichiarare pronta: lo dici.
5. **Secondo giro di revisione:** nuovo `review.json` con `round: 2`. B1 non c'è più.
6. **Chiusura:**
   ```
   skillauthor ready <skill> --review review-2.json --previous-review review-1.json --verdict verdict-2.json
   ```
   `verdict-2.json` è il verdetto del collaudo ripetuto al punto 4, che porta l'impronta della versione
   corretta.
   Se B1 fosse ricomparso, il motivo sarebbe `review-open-blocking` con "ricomparso".
