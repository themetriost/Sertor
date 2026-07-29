---
title: Identità per presenza o per contenuto
type: concept
tags: [idempotenza, installer, guardie, difetti, pattern-diagnostico, principio-vi, e10]
created: 2026-07-24
updated: 2026-07-29
sources: ["src/sertor_core/composition.py", "src/sertor_core/observability/capture.py", "src/sertor_core/wiki_tools/scan.py", "packages/sertor-install-kit/src/sertor_install_kit/", "wiki/log/2026-07-24.md"]
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

## La quarta istanza, con il segno invertito: **rilevare un cambiamento** (2026-07-27)

Le tre sopra riguardano l'**idempotenza** — decidere se *rifare* qualcosa. La stessa distinzione
governa la domanda opposta, *«è cambiato qualcosa?»*, e lì l'errore ha il **segno invertito**: non un
no-op che sembra successo, ma **lavoro dichiarato dove non ce n'è**.

Git offre due risposte, e non sono la stessa:

| Comando | Risponde a | `.claude/settings.json` |
|---|---|---|
| `git status --porcelain` | «il file risulta **modificato**?» (presenza di una differenza, **fine-riga inclusi**) | **`M`** |
| `git diff --name-only HEAD` | «il **contenuto** è cambiato?» (content-aware, normalizzazione esclusa) | **assente** |

Il file aveva **zero righe aggiunte e zero rimosse**: differiva solo per i fine-riga, cioè per come
git normalizza — **nessuno aveva scritto nulla**. Costruendo `scan` sull'ancora derivata avevo preso
`status`, e il gate ha **bloccato la chiusura di sessione su un file che nessuno aveva toccato**.
Trovato al **primo uso reale del gate appena consegnato**, contro il suo stesso autore.

> Quando decidi se **c'è lavoro**, la domanda è sul **contenuto**, non sulla presenza di una
> differenza. «Modificato» ha due significati, e uno dei due include cose che nessuno ha scritto.

*Nota di metodo:* per tutta la sessione avevo chiamato quel file «rumore CRLF» **senza verificarlo**,
escludendolo dai commit per abitudine. Era vero — ma lo sapevo per assunzione, non per misura, e
finché resta un'assunzione non può diventare una **regola nel codice**. La verifica è costata un
comando.

## La quinta istanza, la peggiore: **un via libera che sembra pulizia** (2026-07-29)

Il gate della freschezza del wiki (`scan` → hook `wiki-guard`) chiede *«c'è lavoro non registrato?»*.
La decisione **A-2** voleva che una voce di giornale **non committata** valesse — giusto: il gate chiede
se hai *registrato*, non se hai *committato*. È stata implementata così:

```python
recorded_today = today is not None and today in worktree   # identità: data + PRESENZA del file
pending_paths = ([] if recorded_today else [...])          # azzeramento GLOBALE
```

Verifica la **presenza di una registrazione**, non la **copertura del lavoro**. Conseguenza misurata:
**otto scenari distinti** di lavoro non registrato riportano `pending: 0`, con **una sola causa**. Il
gate non richiede nemmeno una *voce* — un file **vuoto**, o una **riga vuota** appesa, lo soddisfano.

> **Chi soddisfa la regola la disattiva.** Il rituale prescrive di scrivere la voce di giornale; nel
> momento in cui la scrivi, il gate smette di vedere tutto il lavoro successivo — nella finestra esatta
> in cui lo `Stop` lo interroga.

**Perché è la peggiore delle cinque:** le prime tre producono un no-op che *sembra* un successo, la
quarta lavoro dichiarato dove non ce n'è. Questa produce **un via libera che sembra pulizia** — e come
lo formula il nodo *Acta*, che l'ha segnalata: *«un gate che non blocca mai è indistinguibile da un
gate disinstallato»*.

**E il test la certifica.** `test_todays_uncommitted_entry_satisfies_the_gate_without_a_commit` verifica
che la voce **ci sia**, non che **copra**: guardia e test condividono la stessa assunzione di identità,
per questo nessuno dei due ha visto il difetto. È lo stesso schema dell'istanza 2, dove un test
certificava `--directory`. **Un test scritto dalla stessa mente della guardia ne eredita il confine di
identità** — non è una verifica indipendente, è la stessa affermazione detta due volte.

*Rimedio in requisito:* la voce dichiara l'**insieme di path che copre**, derivato al momento della
scrittura; `pending = lavoro − copertura`. La **data sparisce dalla logica** (E10-FEAT-062).

> **Nota che attraversa le istanze:** la 2 e la 5 sono state trovate **da nodi a valle**, non da noi.
> Il dogfood è **una** configurazione, e la più favorevole per costruzione — vedi il terzo limite in
> [[dogfood-fidelity]].

## Perché è insidioso

**Il criterio sbagliato non fallisce mai.** Un'operazione che non fa nulla non solleva eccezioni, non
degrada, non lascia tracce: riporta successo, e la verifica che chiede *«ha funzionato?»* risponde sì.
Il difetto si vede solo chiedendo **«cosa c'è adesso?»**, che è una domanda diversa.

**Colpisce esattamente ciò che dovrebbe ripararsi.** Nelle istanze di idempotenza il meccanismo
esisteva per **aggiornare** qualcosa — un hook, una configurazione, un sink — ed è il meccanismo
d'aggiornamento a diventare il custode della versione vecchia. Nella variante a segno invertito vale
il gemello: è il **presidio** a produrre l'allarme falso, e a pagarlo è la fiducia nel presidio.

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
