---
title: Audit del codice morto — quattro lenti e i loro punti ciechi
type: concept
tags: [audit, codice-morto, entry-point, copertura, metodo, e10]
created: 2026-07-27
updated: 2026-07-27
sources: ["src/sertor_core/", "packages/", "requirements/debito-tecnico/epic.md", "wiki/log/2026-07-27.md"]
---

# Audit del codice morto — quattro lenti e i loro punti ciechi

«Questo codice serve ancora?» non ha **una** risposta meccanica. Ogni strumento che la dà guarda da
un'angolazione sola, e le angolazioni hanno punti ciechi **diversi e prevedibili**: usarne una fa
concludere troppo, usarle tutte lascia da giudicare solo ciò che va giudicato davvero.

Metodo validato su **~30.000 righe** (2026-07-27), che ha prodotto 5 righe di backlog e — cosa che
conta uguale — **8 falsi positivi riconosciuti prima di proporre cancellazioni**.

## La definizione, che viene prima del metodo

> **Un test che referenzia codice morto è a sua volta codice morto.**

Non è pignoleria: un test che esercita codice **irraggiungibile** misura sé stesso. Dà la sensazione
di copertura senza coprire nulla di ciò che gira, e — peggio — **tiene in vita** il codice morto
davanti a qualunque strumento che conti i riferimenti. Senza questa regola, ogni funzione con un test
è viva per definizione, e l'audit non può concludere niente.

## Le quattro lenti

| Lente | Cosa trova | Cosa NON vede |
|---|---|---|
| **Raggiungibilità dagli entry point** (import-graph) | **moduli interi** che nessun percorso raggiunge | tutto ciò che è *dentro* un modulo raggiunto |
| **Livello-definizione** (`vulture`) | funzioni/classi/metodi senza riferimenti | registrazione per decoratore, callback di framework, dispatch per stringa |
| **Superficie degli entry point** (sottocomandi, tool MCP) | comandi che esistono ma nessuno invoca | codice interno |
| **Copertura** (`pytest --cov`) | righe **mai eseguite** in nessuno scenario | *non-coperto ≠ morto*: i percorsi d'errore difensivi sono vivi e giustamente non esercitati |

**Nessuna lente da sola conclude.** L'incrocio sì: ciò che è **irraggiungibile** *e* **senza
riferimenti in produzione** *e* **non coperto** è morto con tre conferme indipendenti.

## I falsi positivi hanno classi ricorrenti

Riconoscerle **prima** evita di proporre la cancellazione di codice vivo — che è il modo più veloce
per far perdere fiducia in un audit:

- **Registrazione per decoratore.** I tool MCP (`@mcp.tool()`) non sono chiamati da nessuno nel
  sorgente: li chiama il protocollo. Un'analisi statica li dà per morti.
- **Callback di framework.** `compose`, `on_mount` sono invocati dal ciclo di vita di Textual.
- **Dispatch per stringa.** `BINDINGS = [("r", "refresh", …)]` lega il tasto al metodo
  `action_refresh` **per nome**: nessun riferimento simbolico esiste.
- **Riferimenti in prosa distribuita.** Un comando invocato solo da una **skill** o da un **agente**
  (`… validate --json`) è vivissimo, ma vive in un `.md`, non in un `.py`.
- **Entry point `python -m`.** Uno strumento di sviluppo (`sertor_installer.sync`) non è importato da
  nessuno *per costruzione*.

> **Corollario pagato sul campo:** il primo pattern di ricerca ha dichiarato morte tre operazioni
> (`validate`, `upsert-index`, `migrate`) perché cercava `sertor-wiki-tools <op>`, mentre la doc le
> scrive nella forma abbreviata `… <op> --json`. **Due erano vive.** Quando una lente dice «morto»,
> la domanda successiva è *«in quale forma verrebbe scritto, se fosse vivo?»*.

## Verificare anche lo strumento, non solo il codice

La prima versione dell'analisi di raggiungibilità saltava gli **import relativi** (`from .domain
import …`) e dichiarava irraggiungibile **un pacchetto intero** che aveva un entry point regolare.
L'errore era plausibile e l'output sembrava un finding grosso. È la stessa disciplina di
[[esito-sull-host-vs-forma-dell-asset]] applicata all'auditor: *una lente che non trova nulla e una
lente rotta si assomigliano*, e vale anche al contrario.

## Distinguere «morto» da «obsoleto»

Non sono la stessa cosa e il rimedio è diverso:

- **Morto** — nessun percorso lo raggiunge. Si cancella (con i suoi test).
- **Obsoleto** — raggiungibile e documentato, ma la sua **finestra si è chiusa**: `migrate` è la
  migrazione una-tantum al log partizionato, e ogni ospite installato da allora nasce già migrato.
  Va **deciso**: mantenerlo dichiarandolo storico, o ritirarlo con la sua riga di catalogo.
- **Mai cablato** — una API sensata che nessun consumatore ha mai usato. Qui la domanda giusta non è
  *«cancellare?»* ma **«perché il consumatore previsto non è mai arrivato?»**: la risposta è spesso
  una capacità dimenticata, non codice di troppo.

## Vedi anche
- [[deterministic-vs-judgment]] — le lenti sono la metà **deterministica**; classificare i falsi
  positivi e decidere fra morto/obsoleto/mai-cablato è **giudizio**.
- [[esito-sull-host-vs-forma-dell-asset]] — una guardia (o una lente) può essere verde e cieca.
