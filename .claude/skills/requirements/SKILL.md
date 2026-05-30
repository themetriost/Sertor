---
name: requirements
description: "Fase di gestione ed elicitazione dei requisiti, su due livelli. Livello epica: produce requirements/<epica>/epic.md con visione, ambito, criteri di successo e un backlog di feature (MoSCoW). Livello feature: produce requirements/<epica>/<feature>/requirements.md con requisiti funzionali in notazione EARS. Include la decomposizione dal backlog alle feature. È la fase a monte del design."
argument-hint: "Descrivi l'epica (requisito di alto livello) o la singola feature da mettere a requisiti"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

Considera SEMPRE l'input dell'utente prima di procedere (se non vuoto). Il testo dopo
`/requirements` **è** la descrizione dell'idea/esigenza. Se è vuoto, chiedi all'utente di descriverla.

## Scopo

Questa fase produce i **requisiti** — il "cosa serve e perché", *prima* di qualunque decisione di
design o stesura di specifica. Niente implementazione (no stack, API, schema dati, codice). Lavora
su **due livelli**, più un'azione di **decomposizione** che li collega.

```
Livello EPICA    →  requirements/<epica>/epic.md   (requisito di alto livello + backlog di feature)
        │  decomposizione (una per feature, i Must prima)
        ▼
Livello FEATURE  →  requirements/<epica>/<feature>/requirements.md   (requisiti EARS di dettaglio)
```

Un'**epica** è un requisito di alto livello (una grande capacità/obiettivo); le **feature** sono i
requisiti di dettaglio in cui l'epica si decompone.

## Passo 0 — Determina il livello

Dall'input capisci se stai mettendo a requisiti:
- **un'epica** (requisito di alto livello, più capacità, visione complessiva) → **A. Livello epica**;
- **una singola feature** (un'unica capacità ben delimitata) → **B. Livello feature**;
- **la decomposizione** di un'epica già esistente nelle sue feature → **C. Decomposizione**.
In caso di ambiguità, chiedilo all'utente.

---

## A. Livello epica

Obiettivo: `requirements/<epica>/epic.md` con il requisito di alto livello, il suo **perimetro** e il
**backlog di feature** (i requisiti di dettaglio da decomporre poi).

1. **Intake & short-name.** Estrai problema, attori, valore. Genera uno short-name dell'epica e crea
   la cartella `requirements/<epica>/`.
2. **Elicitazione** sulla *tassonomia di copertura* (vedi sotto), a grana di epica. Per le aree
   critiche *Missing/Partial* senza default, **poni domande all'utente** (raggruppate, prioritizzate:
   ambito > obiettivi > vincoli/sicurezza > resto). Il resto: assunzioni ragionevoli documentate.
3. **Scrivi `requirements/<epica>/epic.md`:**

   ```markdown
   # Epica — <Nome>

   ## 1. Visione e problema (perché)
   ## 2. Ambito
   ### In ambito
   ### Fuori ambito
   ## 3. Criteri di successo
   <!-- misurabili e tech-agnostici -->
   ## 4. Stakeholder e attori
   ## 5. Vincoli, assunzioni e dipendenze
   ## 6. Rischi
   ## 7. Requisiti trasversali (EARS, opzionale)
   <!-- solo i pochi requisiti davvero trasversali a tutta l'epica -->
   ## 8. Backlog di feature
   | ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
   |----|---------|--------------------|-------------------|-------|
   | FEAT-001 | ... | ... | Must | da decomporre |
   ## 9. Domande aperte
   <!-- ogni punto irrisolto resta [DA CHIARIRE: domanda] -->
   ```

   Il **backlog** è il cuore: ogni `FEAT-NNN` è una feature che diventerà una cartella di dettaglio.
   Prioritizza con **MoSCoW** (Must / Should / Could / Won't).

4. **Validazione:** ambito delimitato (in *e* fuori), criteri di successo misurabili, backlog con
   priorità esplicite, nessun dettaglio implementativo.

---

## B. Livello feature

Obiettivo: `requirements/<epica>/<feature>/requirements.md` con i requisiti funzionali **di dettaglio**
in EARS. (Se la feature è autonoma, fuori da un'epica, usa `requirements/<feature>/requirements.md`.)

1. **Short-name & cartella.** Genera lo short-name (2-4 parole) e crea il `requirements.md`. Se la
   feature deriva da un backlog, annota `Deriva da: FEAT-NNN`.
2. **Elicitazione** sulla tassonomia, a grana di feature.
3. **Scrivi `requirements.md`:**

   ```markdown
   # Requisiti — <Nome Feature>
   <!-- Deriva da: FEAT-NNN (se applicabile) -->

   ## 1. Contesto e problema (perché)
   ## 2. Obiettivi e criteri di successo
   ## 3. Stakeholder e attori
   ## 4. Ambito
   ### In ambito
   ### Fuori ambito
   ## 5. Requisiti funzionali (EARS)
   <!-- atomici, testabili, con ID REQ-NNN e pattern EARS -->
   ## 6. Requisiti non funzionali
   ## 7. Vincoli, assunzioni e dipendenze
   ## 8. Rischi
   ## 9. Prioritizzazione (MoSCoW)
   ## 10. Domande aperte
   ```

4. **Validazione:** ogni requisito funzionale **atomico, testabile, EARS-conforme**; criteri di
   successo misurabili; ambito delimitato; assunzioni esplicite.

---

## C. Decomposizione (dal backlog alle feature)

Dato un `requirements/<epica>/epic.md` esistente: per ogni `FEAT-NNN` (i **Must** prima), esegui il
**Livello feature (B)** producendo `requirements/<epica>/<feature>/requirements.md` con
`Deriva da: FEAT-NNN`. Aggiorna lo **Stato** nel backlog dell'epica (`da decomporre` → `decomposta`).
Le feature sono indipendenti: la decomposizione di più feature può essere **parallelizzata** (un
analista per feature).

---

## Notazione EARS (requisiti funzionali)

Ogni requisito funzionale usa un pattern (keyword fisse); soggetto = il sistema/componente; ID `REQ-NNN`.

- **Ubiquitous** (sempre attivo): *The <system> shall <response>.*
- **State-driven** (durante uno stato): *While <stato>, the <system> shall <response>.*
- **Event-driven** (a un evento): *When <trigger>, the <system> shall <response>.*
- **Optional feature** (se presente): *Where <feature>, the <system> shall <response>.*
- **Unwanted behaviour** (condizione indesiderata): *If <condizione>, then the <system> shall <response>.*
- **Complex**: combinazione. Ogni requisito deve risultare **verificabile** (deve poter generare un test).

## Tassonomia di copertura (elicitazione)

Problema/visione · stakeholder/attori · obiettivi e **criteri di successo misurabili** · ambito
(in/fuori) · capacità funzionali · dati/entità · qualità non-funzionali (performance, scalabilità,
affidabilità, osservabilità, sicurezza/privacy, costo, compliance) · integrazioni/dipendenze ·
vincoli/assunzioni · rischi/edge case · prioritizzazione **MoSCoW**.

## Regole del workspace (sempre attive)

- **Output e report in italiano.** Le formulazioni EARS possono restare in inglese (keyword standard).
- **Niente "come":** nessuno stack, libreria, API, schema DB o struttura del codice — è materia
  della fase di design a valle. Qui solo *cosa* e *perché*.
- **Git: mai eseguirlo direttamente** — delegato al `configuration-manager`. Al termine proponi un
  messaggio di commit (`docs(requirements): ...`).
- **Segreti/artefatti:** niente segreti; non toccare `.env`, `*.key`, `raw/`.
- **Dogfooding:** se l'esigenza tocca codice esistente, usa i tool di retrieval del repo per
  ancorare i requisiti a ciò che già esiste (cita i file).

## Done When

- [ ] Artefatto scritto e validato: `<epica>/epic.md` (epica) **o** `<feature>/requirements.md` (feature).
- [ ] Livello epica: backlog di feature con MoSCoW; ambito delimitato; criteri di successo misurabili.
- [ ] Livello feature: requisiti funzionali EARS atomici/testabili; `Deriva da: FEAT-NNN` se applicabile.
- [ ] Domande aperte elencate; commit proposto al `configuration-manager`.
