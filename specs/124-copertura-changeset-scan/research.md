# Research — la registrazione copre un changeset, non una data

**Feature**: `124-copertura-changeset-scan` · **Date**: 2026-07-29

Le decisioni qui sotto sono tutte **verificate sul repo o misurate**, non scelte per plausibilità.
Dove una verifica ha cambiato il disegno, è detto.

---

## R1 — Su cosa si fonda la copertura: path, o `(path, contenuto)`?

**Decision**: **`(path, identità-di-contenuto)`**. La copertura è un insieme di coppie; un elemento è
coperto **se e solo se il suo contenuto attuale** compare nell'insieme.

**Rationale**: è la scelta che fa cadere gratis tre problemi che altrimenti richiederebbero macchinari
separati.

1. **Un elemento coperto e poi modificato di nuovo torna pendente** (FR-011, US3 scenario 3) —
   automatico: il contenuto nuovo non è nell'insieme.
2. **Le coperture vecchie non «sporcano» il presente.** Con i soli path, l'unione di tutte le coperture
   mai dichiarate coprirebbe per sempre; con il contenuto, una copertura vecchia porta un'identità
   vecchia che semplicemente **non combacia**. Questo elimina la necessità di stabilire *quali* voci
   sono «recenti» — e quindi elimina la data dalla logica per davvero, non solo a parole.
3. **Elimina il parsing delle voci** (vedi R3).

**Costo, misurato**: `git hash-object --stdin-paths` accetta N path in **un solo spawn**, e per un file
intatto restituisce **esattamente** ciò che restituisce `git rev-parse HEAD:<path>` (controprova
eseguita: `d33aa25…` su entrambi). Il costo è **+1 spawn** sul riferimento di 7, cioè ~1,5% — ben
dentro il budget del 15% (SC-008).

**Alternatives considered**:
- **Solo path** — più semplice da leggere, ma richiede di distinguere le coperture «attuali» dalle
  vecchie, il che reintroduce un criterio temporale: esattamente ciò che stiamo togliendo. Scartata.
- **`git diff --raw HEAD`** per ottenere le identità in un colpo — **verificata e scartata**:
  restituisce `0000000` sul lato albero-di-lavoro, perché il contenuto non consegnato non è
  nell'archivio degli oggetti. Non serve allo scopo.

---

## R2 — Dove vive la copertura

**Decision**: **dentro la voce di giornale**, come blocco delimitato in commento HTML
(`sertor-covers/1`), scritto da `append-log`.

**Rationale**: il Principio XIV chiede di non creare copie da riconciliare. Un file di stato accanto al
giornale sarebbe **una seconda fonte** che può divergere dal giornale (cancella una voce a mano e il
sidecar mente). Dentro la voce, invece, la copertura **non può separarsi** da ciò che descrive: si
sposta, si cancella e si consegna insieme ad essa. È anche ciò che rende una registrazione superficiale
**falsificabile**, che è il valore della Storia 3.

Il commento HTML è invisibile nel markdown reso ma **presente nel testo grezzo** — che è come questo
giornale viene letto davvero. Prosa pulita per chi legge, dato esatto per chi verifica.

**Alternatives considered**:
- **File sidecar** — seconda copia, scartata per il XIV.
- **`git notes`** — invisibile all'ospite, non viaggia col file, e richiede un repo: violerebbe
  l'host-agnosticità (progetti senza versionamento sono supportati *by design*).
- **Riga visibile in prosa** — leggibile, ma con identità di contenuto diventa rumore illeggibile, e
  il troncamento la renderebbe non più autorevole.

---

## R3 — Come si riconosce una registrazione ⚠️ *questa verifica ha cambiato il disegno*

**Decision**: **non si riconosce affatto.** Non serve rilevare «una voce è stata aggiunta»: si legge
l'**unione dei blocchi di copertura** presenti nel giornale.

**Come ci sono arrivato**: il piano iniziale era estrarre le intestazioni di voce **aggiunte** dal
changeset del giornale, riusando la regex `^## \[[^\]]*\]\s+(?P<op>\S+)` che vive in
`distill-floor.py:74`. Verificando prima di scrivere è emerso che **il formato dell'intestazione è
configurabile per ospite**: `registry.py:87` costruisce l'intestazione con
`profile.log_format.format(date=…, op=…, title=…)`, e `log_format` è un campo del profilo
(`profile.py:62`). Una regex cablata sul nostro formato avrebbe funzionato **solo sugli ospiti che
usano il nostro** — una violazione del Principio X, per giunta invisibile (nessun errore: semplicemente
zero voci riconosciute, quindi gate cieco).

Con la scelta R1 il problema **non si pone**: la presenza o assenza di un blocco di copertura è già la
risposta, e non richiede di sapere che forma abbia l'intestazione.

**Effetto collaterale sugli edge case**: una registrazione **vuota**, **priva di voci** o toccata da
sola normalizzazione del testo non porta alcun blocco di copertura → **non copre nulla**, che è
esattamente il comportamento richiesto (FR-002, edge case H/I/J) — ottenuto **senza** una regola
dedicata.

> **Finding adiacente, non in ambito qui:** l'hook `distill-floor.py` cabla la stessa regex e ha quindi
> lo **stesso difetto latente** su un ospite con `log_format` diverso — il pavimento del distill
> semplicemente non vedrebbe alcuna voce. Va tracciato a parte (non lo si corregge qui per non
> allargare lo scope: vedi *Out of scope* in fondo).

---

## R4 — La regola di transizione (Q1/C), ristretta a ciò che serve

**Decision**: una voce **priva** di blocco di copertura conta come copertura di tutto il lavoro in
perimetro **solo se la voce non è ancora consegnata**; le voci **già consegnate** non richiedono alcuna
regola. L'esito **dichiara** quante voci stanno valendo per compatibilità (`legacy_coverage`).

**Rationale**: la formulazione larga di Q1/C — *«una voce senza copertura copre tutto»* — combinata con
l'unione di R1 avrebbe reso il gate **cieco per sempre**: ogni giornale contiene decine di voci
storiche prive di copertura, e una sola di esse basterebbe a coprire tutto. Restringendo alle voci **non
consegnate** la regola fa esattamente il lavoro per cui esisteva — non far bloccare l'ospite al primo
aggiornamento su lavoro che considerava registrato — e si esaurisce da sé: appena quella voce viene
consegnata, l'àncora si sposta e il caso sparisce. **Durata reale della deroga: una sessione.**

Le voci storiche **consegnate** non hanno bisogno di nulla: il lavoro che descrivevano è anteriore
all'àncora, quindi non entra mai in `touched`.

**Alternatives considered**:
- **Q1/A o C non ristretti** — gate permanentemente cieco. Scartati *dopo* averne visto la
  conseguenza: è il difetto che stiamo chiudendo, reintrodotto dalla porta di servizio.
- **Q1/B (non copre nulla)** — corretto ma blocca ogni ospite al primo aggiornamento. Scartato in spec.

---

## R5 — Dichiarare una determinazione fallita senza reintrodurre il deadlock

**Decision**: `scan` espone un campo additivo `determination` (`ok` | `failed`) con `determination_reason`;
gli hook consumatori **non trattano `failed` come «pulito»**, ma **non bloccano**: scrivono il
breadcrumb ispezionabile già esistente (`hook.error/1`, meccanismo di E10-FEAT-019) e restano
fail-open.

**Rationale**: la lezione della FEAT-045 è che un gate che **impedisce di chiudere la sessione** è più
dannoso di un gate cieco. Se un `git` che non risponde bloccasse lo `Stop`, un problema d'ambiente
renderebbe la sessione non chiudibile — e la via d'uscita sarebbe aggirare il gate. Dichiarare senza
bloccare soddisfa il Principio XII (*la degradazione è ammessa solo se segnala*) senza creare una
condizione insoddisfacibile.

**Il difetto rimosso alla radice**: oggi `_committed_since` e `_worktree_changes` fanno
`return … if rc == 0 else []`, cioè **degradano verso l'insieme vuoto** — e `pending == 0` significa
«pulito». La correzione non è aggiungere un campo sopra il comportamento vecchio: è **non fabbricare
più un insieme vuoto** quando non si è potuto guardare.

---

## R6 — Come `append-log` deriva la copertura senza ricorsione

**Decision**: `append_log` calcola la copertura **prima** di scrivere la voce, chiamando la stessa
funzione di determinazione che usa `scan`, e vi include **il lavoro attualmente pendente**.

**Rationale**: l'ordine risolve da sé il caso di più voci nello stesso giorno. La prima voce copre ciò
che è pendente in quel momento; quando si scrive la seconda, la prima copertura è già in vigore, quindi
la seconda copre **solo il delta**. L'unione è corretta per costruzione, senza una regola di
composizione (US3 scenario 2).

Nessuna ricorsione: la copertura si calcola sul giornale **com'è prima** dell'append.

**Nota di confine (Principio XI)**: `append_log` e `scan` sono due funzioni della **stessa libreria**;
comporle in-process non è «bypassare un vehicle» — il vehicle è il comando CLI che le espone. Nessun
subprocess, nessun import da fuori.

---

## R7 — Non bumpare la stringa di schema

**Decision**: `wiki.scan/1` **invariata**; le informazioni nuove viaggiano su campi **additivi**
(`determination`, `determination_reason`, `legacy_coverage`). Guardia dedicata che asserisce la stringa.

**Rationale**: verificato sul codice — `wiki-guard.py:105` fa
`scan.get("schema") != "wiki.scan/1" → return` (fail-open). Un bump **non** romperebbe il gate: lo
farebbe **sparire in silenzio** su ogni ospite non ancora aggiornato, che è il modo peggiore di
rompere una guardia. Il vincolo è già presidiato da una guardia scritta in FEAT-045: va **estesa**, non
sostituita.

---

## R8 — Superfici host-facing toccate

**Decision**: oltre alla libreria, il changeset tocca **tre** superfici distribuite, e ciascuna ha la
sua regola di completamento.

| Superficie | Perché | Regola |
|---|---|---|
| `wiki-guard.py` · `wiki-pending-check.py` | devono capire `determination` | asset distribuiti → parità Claude/Copilot |
| `wiki-playbook.md` (§ formato della voce) | il formato della voce **cambia**: acquisisce un blocco | asset distribuito → va aggiornato, non solo il nostro |
| `docs/` | regola 3: doc utente nello stesso step | verificare cosa diventa falso, e correggerlo |

**Rationale**: la regola 1 dice che una feature non è completa finché un ospite non può ottenerla; la
regola 3 dice che non è completa finché la doc utente non riflette il cambiamento. Entrambe scattano
qui perché `append-log` **cambia ciò che scrive** e gli hook **cambiano ciò che leggono**.

---

## Out of scope (promossi, non sepolti)

- **`distill-floor.py` cabla il formato dell'intestazione** (finding di R3): stesso difetto latente di
  Principio X, su un altro hook. Da tracciare come riga di backlog propria — **non** si corregge qui,
  perché è un secondo difetto su una seconda superficie e allargarlo renderebbe questo changeset
  difficile da verificare.
- **Perimetro di `scan`** (`packages/`, file di radice fuori da `source_dirs`): già **E10-FEAT-063**.
- **Divergenza `ritual-check` ↔ `wiki-guard`**: già **E10-FEAT-060**. Questa feature non la chiude ma
  la rende più visibile, perché i due strumenti misureranno realtà ancora più diverse.
