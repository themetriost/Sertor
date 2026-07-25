---
title: Identità per presenza o per contenuto
type: concept
tags: [idempotenza, installer, guardie, difetti, pattern-diagnostico, principio-vi, e10]
created: 2026-07-24
updated: 2026-07-25
sources: ["src/sertor_core/composition.py", "src/sertor_core/observability/capture.py", "packages/sertor-install-kit/src/sertor_install_kit/", "wiki/log/2026-07-24.md"]
---

# Identità per presenza o per contenuto

Ogni operazione idempotente deve rispondere a una domanda prima di decidere se ha già lavorato:
**«questa cosa c'è già?»**. La risposta dipende da cosa si conta come *«questa cosa»* — e sbagliare
quel confine produce un difetto con una firma costante:

> **L'operazione non fa nulla, riporta successo, e lascia in piedi la versione sbagliata.**

Non è un fallimento: è un **no-op che sembra un successo**. Nessun errore, nessun warning, nessuna
traccia — e la cosa sbagliata continua a funzionare abbastanza da non farsi notare.

## La distinzione

| Criterio | La domanda che pone | Cosa non vede |
|---|---|---|
| **Per presenza** | «esiste qualcosa di questo tipo?» | che quel qualcosa sia **la cosa giusta** |
| **Per contenuto** | «esiste qualcosa che punta al target giusto?» | — |

Il criterio per presenza è quasi sempre il più facile da scrivere, ed è per questo che si ripresenta.

## Tre istanze, tre domini

**1. L'identità di un hook nel merge** (E10-FEAT-032). L'`upgrade` identificava un hook per la
**stringa del comando**. Un ri-cablaggio cambia quella stringa, quindi l'hook sembrava *nuovo*: su un
assistente veniva **duplicato** (con la copia vecchia rotta ancora attiva), su un altro **scartato**.
Identità corretta: lo **stem dello script**. Dettaglio in [[identita-hook-nel-merge]].

**2. La registrazione del server MCP** (segnalazione del nodo *Kaelen*, 2026-07-24). L'installer saltava
`.mcp.json` quando il server era **già registrato**. Su quell'host la registrazione conteneva
`--directory` invece di `--project`: il RAG risolveva l'indice nella cartella sbagliata e **ogni query
tornava `[]`** — per **un mese**, indistinguibile da un corpus povero. La configurazione rotta era
quindi **immune a tutti gli upgrade successivi**, proprio perché «c'era».

> **Chiusa il 2026-07-25 (E2-FEAT-022) — e la radice era peggio della diagnosi.** Correggendo si è
> scoperto che `--directory` non era un residuo di installazioni vecchie: era **la forma che il
> template spediva**, mai cambiata dal primo commit, mentre cinque punti della nostra documentazione
> dicevano di non usarla — con un test che la **certificava** giusta (vedi
> [[esito-sull-host-vs-forma-dell-asset]]). Il fix è su tre livelli: il template passa a `--project`;
> `upgrade` riconcilia l'entry **per contenuto** (`update_mcp_server`) mentre `install` resta
> non-distruttivo ma **dichiara** la divergenza (`PRESENT_DIVERGENT`); `doctor` verifica la **forma
> dell'invocazione** e non solo la presenza. Con una separazione che il primo tentativo non aveva:
> l'upgrade riscrive **l'invocazione** (nostra) e **preserva la configurazione dell'ospite**
> (`SERTOR_CORPUS`) — riscrivere tutto azzerava il corpus e riproduceva il RAG cieco.

**3. L'idempotenza dell'osservabilità** (trovata il 2026-07-24). `enable_observability` chiedeva
*«c'è già un `EventPersistenceHandler` attaccato?»*. Con uno puntato a un altro store non faceva
nulla, e ogni evento continuava a finire nello store **precedente**. Nella suite di test si
manifestava come **4 fallimenti apparentemente scorrelati**: bastava che un test qualsiasi costruisse
un componente via factory perché si attaccasse un handler puntato allo store reale del progetto, e da
lì in poi nessun test riusciva più a catturare i propri eventi.

## Perché è insidioso

**Il criterio sbagliato non fallisce mai.** Un'operazione che non fa nulla non solleva eccezioni, non
degrada, non lascia tracce: riporta successo, e la verifica che chiede *«ha funzionato?»* risponde sì.
Il difetto si vede solo chiedendo **«cosa c'è adesso?»**, che è una domanda diversa.

**Colpisce esattamente ciò che dovrebbe ripararsi.** In tutti e tre i casi il meccanismo esisteva per
**aggiornare** qualcosa — un hook, una configurazione, un sink — ed è il meccanismo d'aggiornamento a
diventare il custode della versione vecchia.

**Si nota tardi e altrove.** L'hook duplicato si è visto su un host che aggiornava, la `.mcp.json`
rotta dopo un mese di risposte vuote, l'handler stantio come fallimenti in un file di test che non
c'entrava nulla.

## La regola

> Quando un'operazione decide di **non fare nulla perché «c'è già»**, l'identità che usa dev'essere
> quella che rende la cosa **la cosa giusta**, non quella che la rende *una cosa di quel tipo*.
> Se le due divergono, il no-op conserva l'errore.

In pratica, per ogni guardia di idempotenza chiedersi: **due oggetti che superano questo test possono
comportarsi in modo diverso?** Se sì, il test è per presenza e va stretto.

E l'identità dev'essere **interrogabile**, non dedotta: nel fix dell'osservabilità sono state aggiunte
due property (`EventPersistenceHandler.store`, `SqliteObservabilityStore.path`) proprio perché chi
decide deve poter *chiedere* il target, non inferirlo.

## Parentele

- [[esito-sull-host-vs-forma-dell-asset]] — il parente stretto, e la distinzione vale: là si osserva
  nel **punto sbagliato** (la forma spedita invece dell'esito sull'host); qui si osserva nel punto
  giusto ma con il **criterio sbagliato**. Questo pattern è spesso *la causa* di quello.
- [[default-masked-defect]] — un'altra famiglia di difetti che non si manifestano: là è una manopola
  spenta a chiudere il percorso, qui è un no-op che si autodichiara riuscito. In entrambi il segnale
  manca **per costruzione**, non per distrazione.
- [[identita-hook-nel-merge]] — l'istanza 1 in dettaglio.
- [[constitution]] — Principio VI (idempotenza) dice *cosa* deve valere; questa pagina dice **su quale
  identità** si verifica.
