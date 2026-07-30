---
title: Il rimedio ricade nel difetto che ripara
type: concept
tags: [qualita, verifica, design, principio-xiv, retrospettiva, anti-pattern, governance]
created: 2026-07-30
updated: 2026-07-30
sources: ["specs/126-ritual-check-perimetro/", "wiki/log/2026-07-30.md", ".specify/memory/constitution.md"]
---

# Il rimedio ricade nel difetto che ripara

**Chi ripara un difetto è, in quel momento, la persona più esposta a commetterlo di nuovo.** Non per
distrazione: per **fuoco**. Mentre si ripara si guarda l'*istanza* — questo file, questa riga, questo
comando sbagliato — e la **forma** del difetto, che è ciò che lo rende ripetibile, resta fuori campo
proprio mentre la si sta descrivendo a parole.

Il risultato ha una firma riconoscibile: **il rimedio contiene una copia del difetto**, e passa la
revisione perché chi rivede è la stessa persona che ha appena spiegato con precisione cos'era il
problema — e quella spiegazione fa da alibi.

## Tre istanze, due giorni

| Difetto riparato | Il rimedio conteneva | Colto da |
|---|---|---|
| **Un verde che non mostra cosa ha asserito** (una guardia poteva essere vacua) | Il primo rimedio rendeva la vacuità **visibile** (`-s` per leggere i log) invece che **impossibile** — cioè delegava l'onere a chi legge i log di un run *verde*, cioè a nessuno | una verifica successiva, applicando al gate la pagina appena distillata |
| **Un riferimento corretto nel nostro sistema e inutilizzabile nel loro** (E10-FEAT-064) | Le **note di rilascio di quella stessa correzione** contenevano comandi non eseguibili su un host ospite, pubblicati su tre canali | una **domanda dell'utente**, non una rilettura |
| **Due strumenti che misurano realtà diverse senza dichiararlo** (E10-FEAT-060) | Il piano prevedeva di aggiungere la struttura `perimeter` **accanto** alla stringa `scope`: due descrizioni dello stesso fatto, libere di divergere | il **Constitution Check** (Principio XIV), in fase di piano |

Tre difetti diversi, un solo movimento: *ho capito la malattia abbastanza bene da spiegarla, quindi non
la sto facendo*. È un non sequitur, e le tre righe qui sopra ne sono la prova.

## Perché è difficile da vedere dall'interno

- **La comprensione appena acquisita si traveste da immunità.** Aver nominato la forma del difetto in
  una spec o in un commit *sembra* garantire di non riprodurla. Non garantisce nulla: nominare è
  un'operazione di linguaggio, riconoscere è un'operazione di percezione, e la seconda avviene su un
  artefatto diverso — il proprio.
- **Il rimedio non viene guardato con la lente del difetto.** Si applica quella lente al codice
  *riparato*, mai al codice *della riparazione*, ai test scritti per l'occasione, alla nota che
  annuncia il fix.
- **Il difetto e il rimedio stanno in registri diversi.** Nel caso E10-FEAT-064 il difetto era in un
  asset distribuito e la sua ricaduta in una **nota di rilascio**: superfici così distanti che nessuna
  guardia le mette in relazione, e l'occhio nemmeno.
- **Chi rivede è chi ha riparato.** Ed è la condizione peggiore possibile: la revisione eredita
  esattamente il fuoco che ha causato l'errore.

## Cosa lo ha effettivamente colto

Nessuna delle tre è stata colta rileggendo con attenzione. Sono state colte da **qualcosa di esterno al
fuoco**:

1. **Un gate formale con una domanda propria.** Il Principio XIV non chiede «va bene?», chiede
   *«questo valore duplica una fonte di verità esistente?»* — una domanda che non dipende da quanto si
   crede di aver capito. È l'istanza in cui la cattura è avvenuta **prima** che il codice esistesse.
2. **Applicare al rimedio la regola appena scritta.** Prendere la pagina distillata cinque minuti prima
   e usarla come lente sul proprio lavoro — non come racconto di ciò che è successo.
3. **Una domanda esterna.** Quella dell'utente (*«quali comandi hai chiesto di installare?»*) ha fatto
   in una riga ciò che nessuna rilettura aveva fatto.

## La domanda che rende operativa questa pagina

Prima di chiudere una riparazione, una sola:

> **La forma del difetto che ho appena descritto — è presente in ciò che ho scritto per ripararlo?**

Non «ho riparato bene?», che si risponde riguardando il difetto. Questa si risponde riguardando **il
rimedio**, con la definizione del difetto in mano: il test appena scritto, la nota di rilascio, il campo
aggiunto, la regola nuova.

Corollario pratico: **conviene che il gate abbia una domanda che non è la tua.** Un check-list
costituzionale, una guardia deterministica, una persona che chiede. Le tre catture sopra vengono tutte
da lì, nessuna dall'introspezione.

## Relazioni

Parente di [[guardia-verde-non-e-una-misura]] (lì una verifica non può fallire; qui una riparazione
riproduce ciò che ripara) e di [[riuso-che-eredita-il-presupposto]] (lì un artefatto porta con sé i
presupposti della domanda per cui è nato). Il gate che l'ha colta la terza volta è il
[[constitution|Constitution Check]], nella forma del Principio XIV; la seconda istanza è la stessa
classe di [[host-agnostico-non-e-risolvibile]], ricomparsa nelle note del rilascio che la correggeva.
Vedi anche [[fail-loud-fix-cause]]: rimuovere la causa vale anche quando la causa è nel rimedio.
