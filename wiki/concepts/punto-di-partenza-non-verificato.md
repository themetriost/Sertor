---
title: Un salto si misura dal punto in cui si è davvero
type: concept
tags: [guardie, misura, aggiornamento, fixture, dipendenze, e10, e15]
created: 2026-09-13
updated: 2026-09-13
sources: ["scripts/smoke.ps1", "scripts/smoke_plant_mcp.py", "tests/integration/test_host_smoke.py", "requirements/debito-tecnico/epic.md", "wiki/log/2026-09-13.md"]
---

# Un salto si misura dal punto in cui si è davvero

Una verifica di aggiornamento dichiara un salto: *«dalla release precedente a questa»*. La parte che
nessuno controlla è la **prima metà** della frase. Se il punto di partenza non è quello dichiarato, il
gate non misura un salto più piccolo: **non misura un salto**, e resta verde dicendolo.

> **La regola:** in una misura fra due stati, il punto di partenza è un'**asserzione**, non un
> presupposto. Va verificato con la stessa cura dell'arrivo — perché è quello che nessuno guarda.

## La misura che ha prodotto la pagina

Il 2026-09-13, aggiungendo al gate d'aggiornamento un esito che verifica se un ospite colpito guarisce
(**E10-FEAT-070**), la condizione da riprodurre non si lasciava piantare: `uv` rifiutava la
risoluzione nominando **un vincolo che esiste soltanto sul ramo di default**. Da lì il fatto:

```
install «della release v0.4.1»  →  created .sertor (sertor-core 0.4.1 (de31fe6))
                                                                     ↑
                                                  un commit di master, non il tag
```

L'installer scrive la sorgente del runtime come **riferimento git nudo** — `{ git = "…" }`, senza
`rev` né `tag` — quindi il runtime **segue il ramo di default**, non la release da cui l'installer
proviene. Lo smoke installava «la versione vecchia» dell'**installer** e otteneva il **codice nuovo**
del core: partenza e arrivo coincidevano.

Ne segue una seconda cosa, peggiore, perché è un presidio che si autoconferma: l'esito `pin-moved`
asserisce che dopo l'aggiornamento il manifest **non citi più** il ref di partenza. Un manifest a git
nudo **non l'ha mai citato**. L'asserzione passa per costruzione — la *forma 2* di
[[guardia-verde-non-e-una-misura]], le due fonti che concordano perché non possono divergere. Tracciato
come **E10-FEAT-077**.

## Perché sfugge, e perché sfugge proprio a chi ha costruito il gate

Il gate d'aggiornamento è nato da una misura onesta e severa: dei difetti arrivati dal campo, tredici su
quattordici stavano nella superficie di consegna, e sette richiedevano **un'installazione preesistente
più vecchia** per manifestarsi ([[esito-sull-host-vs-forma-dell-asset]]). La conclusione — «serve un host
che aggiorna davvero» — era giusta. La sua **implementazione** ha ereditato un'assunzione mai scritta: che
installare l'installer di una versione producesse un host *a* quella versione.

È un'assunzione ragionevole e falsa, e nessun errore la segnala: entrambe le installazioni riescono,
tutti gli esiti diventano verdi, il report dice `upgrade=v0.4.1->master`. La stringa è vera dell'installer
e falsa del runtime, che è la parte che gli ospiti eseguono.

## Cosa ne segue

- **Chiedi allo stato, non al comando.** «Ho installato la v0.4.1» è la storia di ciò che si è
  *eseguito*; «il runtime risolve `de31fe6`» è lo **stato**. Solo il secondo è una misura, e nel nostro
  caso lo ha rivelato **lo strumento** (un rifiuto di risoluzione), non una rilettura del codice — che è
  il modo normale in cui questi difetti si scoprono, quando si scoprono.
- **Un presidio che non può fallire in un percorso va nominato, non lasciato verde.** `pin-moved` regge
  dove il manifest è pinnato e passa gratis dove è nudo: lo stesso nome, due significati. Era invisibile
  perché *l'esito c'era*.
- **La forma della domanda che avrebbe trovato il difetto prima:** non «il gate è verde?» ma **«se il
  punto di partenza fosse sbagliato, questo gate diventerebbe rosso?»**. Qui la risposta era no, e si
  poteva dare senza eseguire nulla.
- **Non tutte le istanze sono difetti.** Un ospite che *vuole* seguire il ramo di default è legittimo —
  ed è il caso reale del nodo *VM-WorkingFolder*, che l'ha nominato come la distinzione che spiega chi
  guarisce e chi no. Il difetto non è il git nudo: è **una misura che assume il pin** e non lo verifica.

## Il parente stretto, e la differenza

[[guardia-verde-non-e-una-misura]] chiede: *in questa esecuzione la guardia poteva diventare rossa?* —
domanda sul **meccanismo** della verifica. Questa pagina chiede: *stavo misurando gli stati che credo?* —
domanda sui **capi** della misura. Una guardia può essere perfettamente capace di diventare rossa e stare
misurando la distanza fra un punto e se stesso.

## Collegate

- [[guardia-verde-non-e-una-misura]] — il meccanismo che tace; qui invece tacciono i capi della misura
- [[esito-sull-host-vs-forma-dell-asset]] — la misura che ha fatto nascere il gate d'aggiornamento
- [[misura-al-confine-pubblico]] — l'altra metà della stessa disciplina: misurare sul piano giusto
- [[difetto-che-solo-un-ospite-nuovo-puo-vedere]] — il difetto per cui questa condizione andava piantata
- [[dogfood-fidelity]] — perché certe condizioni non sono esercitabili sul dogfood
