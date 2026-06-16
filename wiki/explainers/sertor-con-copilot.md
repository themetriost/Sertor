---
title: Sertor anche con GitHub Copilot
type: explainer
tags: [explainer, copilot, assistente, installazione, non-tecnico, feat-007]
created: 2026-06-15
updated: 2026-06-16 (Copilot esiste in due forme — editor e riga di comando — e Sertor le distingue)
sources: ["specs/044-distribuzione-copilot/spec.md", "requirements/sertor-cli/distribuzione-copilot/requirements.md"]
---

# Sertor anche con GitHub Copilot

**In una frase:** Sertor non funziona più solo con un assistente AI; ora puoi portarlo su un progetto
che usa **GitHub Copilot** e ottenere le stesse cose che otterresti con Claude.

## L'immagine quotidiana

Pensa a Sertor come a una **cassetta degli attrezzi** che si attacca all'assistente AI con cui lavori.
Finora la cassetta aveva un solo tipo di **attacco**: quello di Claude. Chi usava Copilot non poteva
agganciarla. Ora la cassetta ha **due attacchi**: scegli il tuo assistente e ricevi gli attrezzi nella
forma che lui capisce — gli stessi attrezzi, solo con la presa giusta.

## Cosa cambia in pratica

Quando installi Sertor su un progetto dici **per quale assistente** lo vuoi:

- *«installami il RAG, per Copilot»* → la ricerca intelligente sul codice compare già collegata dentro
  Copilot;
- *«installami il sistema-wiki, per Copilot»* → le istruzioni di lavoro, i comandi e i promemoria
  automatici arrivano nei posti che Copilot legge.

Se non dici niente, resta il comportamento di prima (Claude). Nessuna installazione fa partire da sola
lavori costosi, niente viene sovrascritto a sorpresa, e rifare l'installazione non crea doppioni.

## Copilot esiste in due forme

GitHub Copilot non è una cosa sola: c'è quello **dentro l'editor** (VS Code) e quello da **riga di
comando** (la "Copilot CLI", che si usa nel terminale). I due cercano le proprie istruzioni in
**posti diversi**, e per un periodo quello da terminale ha smesso di leggere il file che usava
l'editor. Sertor ora **distingue le due forme**: scegli *«per Copilot editor»* o *«per Copilot da
terminale»* e l'aggancio viene messo nel posto giusto per ciascuno — così la presa combacia davvero,
non solo in apparenza.

## Perché è importante

Le capacità di Sertor **non devono dipendere da un solo assistente**: è giusto che un team libero di
scegliere il proprio strumento riceva lo stesso valore. È la stessa idea per cui Sertor si installa su
*qualsiasi* progetto, estesa anche a *qualsiasi* assistente.

## Onestà sulle differenze

Dove un attrezzo non avesse un equivalente perfetto nell'altro assistente, Sertor **lo dice
apertamente** invece di far finta di niente: niente promesse vuote.

## Tutti gli attrezzi, anche su Copilot

Ora la cassetta è **completa** su Copilot: sia gli attrezzi di **ricerca e wiki**, sia quelli di
**metodo di sviluppo** (la parte "governance/SpecKit"). Per quest'ultima, Sertor non si porta dietro una
propria copia del metodo SpecKit: **chiede allo strumento ufficiale di installarsi** nella forma giusta
per il tuo assistente — come un mobile in kit che arriva con le istruzioni di montaggio del produttore
invece di una copia fotocopiata. (Serve quindi una connessione la prima volta che lo installi.)

---

*Dettaglio tecnico:* [[assistant-targeting]] (il meccanismo `AssistantProfile`/`Surface`), [[sertor-installer]],
e la panoramica [[collegamento-con-l-assistente]].
