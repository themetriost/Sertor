---
name: requirements
description: "Fase di gestione ed elicitazione dei requisiti. Trasforma un'idea/esigenza grezza in un documento di requisiti strutturato (requirements.md) con requisiti funzionali in notazione EARS, criteri di successo misurabili, ambito, vincoli, assunzioni, rischi e prioritizzazione MoSCoW. È la fase a monte del design."
argument-hint: "Descrivi l'idea o l'esigenza da trasformare in requisiti"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

Considera SEMPRE l'input dell'utente prima di procedere (se non vuoto). Il testo dopo
`/requirements` **è** la descrizione dell'idea/esigenza: assumi di averlo già disponibile in
conversazione. Se è vuoto, chiedi all'utente di descrivere l'idea.

## Scopo

Questa fase produce il **documento dei requisiti** — il "cosa serve e perché", *prima* di
qualunque decisione di design o stesura di specifica. Si concentra su **bisogni, obiettivi e
criteri di successo**, non sull'implementazione (niente stack, API, schema dati, codice).
L'output è un artefatto autonomo (`requirements.md`) che alimenta la fase di design a valle.

## Workflow

1. **Intake.** Acquisisci l'idea/esigenza grezza dall'input o dall'utente. Estrai i concetti
   chiave: problema, attori, obiettivo, valore atteso.

2. **Short-name & cartella.** Genera uno short-name (2-4 parole, formato azione-sostantivo,
   preserva acronimi/termini tecnici). Crea `requirements/<short-name>/` e l'artefatto
   `requirements/<short-name>/requirements.md`. (Se l'utente indica un percorso esplicito, usalo.)

3. **Elicitazione strutturata.** Scansiona l'idea contro la **tassonomia di copertura** qui sotto,
   marcando ciascuna area Clear / Partial / Missing. Per le aree critiche *Partial/Missing* senza
   default ragionevole, **poni domande mirate all'utente** (raggruppate, max ~5-7 alla volta,
   prioritizzate per impatto: problema/ambito > stakeholder > qualità non-funzionali > dettagli).
   Per il resto fai assunzioni ragionevoli e **documentale** nella sezione Assunzioni.

   **Tassonomia di copertura:**
   - **Problema & visione** — quale problema, per chi, perché ora, valore atteso.
   - **Stakeholder & attori** — chi usa/è impattato; ruoli e permessi distinti.
   - **Obiettivi & criteri di successo** — esiti **misurabili** e tecnologicamente agnostici.
   - **Ambito** — cosa è incluso e, esplicitamente, cosa è **fuori ambito**.
   - **Capacità funzionali** — cosa deve poter fare il sistema (→ requisiti EARS).
   - **Dati & entità** — entità principali, relazioni, regole di identità/ciclo di vita.
   - **Qualità non-funzionali** — performance, scalabilità, affidabilità, osservabilità,
     sicurezza/privacy, costo, compliance.
   - **Integrazioni & dipendenze** — sistemi esterni, formati, modalità di fallimento.
   - **Vincoli & assunzioni** — limiti tecnici/organizzativi, ipotesi su cui ci si appoggia.
   - **Rischi** — cosa può andare storto; edge case e scenari negativi.
   - **Prioritizzazione** — MoSCoW (Must / Should / Could / Won't).

4. **Scrivi `requirements.md`** con questa struttura:

   ```markdown
   # Requisiti — <Nome Feature>

   ## 1. Contesto e problema (perché)
   ## 2. Obiettivi e criteri di successo
   <!-- misurabili e tech-agnostici: "l'utente completa X in < N min", non "API < 200ms" -->
   ## 3. Stakeholder e attori
   ## 4. Ambito
   ### In ambito
   ### Fuori ambito
   ## 5. Requisiti funzionali (EARS)
   <!-- uno per riga, atomici, testabili, con ID REQ-NNN e pattern EARS -->
   ## 6. Requisiti non funzionali
   ## 7. Vincoli, assunzioni e dipendenze
   ## 8. Rischi
   ## 9. Prioritizzazione (MoSCoW)
   ## 10. Domande aperte
   <!-- ogni punto irrisolto resta marcato [DA CHIARIRE: domanda] -->
   ```

5. **Validazione di qualità.** Verifica che: ogni requisito funzionale sia **atomico, testabile e
   conforme EARS**; i criteri di successo siano **misurabili**; l'ambito sia delimitato (in *e*
   fuori); nessun dettaglio implementativo sia trapelato; le assunzioni siano esplicite. Itera
   finché passa o finché restano solo `[DA CHIARIRE]` legittimi.

## Notazione EARS (requisiti funzionali)

Scrivi ogni requisito funzionale con uno di questi pattern (keyword fisse). Soggetto = il sistema/
componente; ogni requisito ha un ID `REQ-NNN`.

- **Ubiquitous** (sempre attivo): *The <system> shall <response>.*
- **State-driven** (durante uno stato): *While <stato>, the <system> shall <response>.*
- **Event-driven** (a un evento): *When <trigger>, the <system> shall <response>.*
- **Optional feature** (se una feature è presente): *Where <feature>, the <system> shall <response>.*
- **Unwanted behaviour** (condizione indesiderata): *If <condizione>, then the <system> shall <response>.*
- **Complex**: combinazione dei precedenti (es. *While <stato>, when <trigger>, the <system> shall <response>*).

EARS serve a eliminare ambiguità, termini non definiti, trigger mancanti e logica incompleta:
ogni requisito deve risultare **verificabile** (deve poter generare un test). Puoi affiancare la
formulazione EARS in inglese a una glossa in italiano se aiuta la leggibilità.

## Regole del workspace (sempre attive)

- **Output e report in italiano.** Le formulazioni EARS possono restare in inglese (keyword standard).
- **Niente "come":** nessuno stack, libreria, API, schema DB o struttura del codice — quella è
  materia della fase di design a valle. Qui solo *cosa* e *perché*.
- **Git: mai eseguirlo direttamente.** Le operazioni git sono delegate all'agente
  `configuration-manager`. Al termine proponi un messaggio di commit (`docs(requirements): ...`).
- **Segreti/artefatti:** non includere segreti; non toccare `.env`, `*.key`, `raw/`.
- **Dogfooding:** se l'esigenza tocca codice esistente, usa i tool di retrieval del repo per
  ancorare i requisiti a ciò che già esiste (cita i file).

## Done When

- [ ] `requirements/<short-name>/requirements.md` scritto e validato.
- [ ] Requisiti funzionali in EARS, atomici e testabili; criteri di successo misurabili.
- [ ] Domande aperte elencate (o risolte con l'utente); commit proposto al `configuration-manager`.
