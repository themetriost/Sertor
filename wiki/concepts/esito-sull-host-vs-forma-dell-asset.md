---
title: L'esito sull'host, non la forma dell'asset
type: concept
tags: [testing, guardie, installer, asset, upgrade, fedelta, principio-xii, e10]
created: 2026-07-17
updated: 2026-07-24
sources: ["packages/sertor-install-kit/tests/unit/test_settings_merge_identity.py", "packages/sertor/tests/test_claude_hook_wiring_anchored.py", "requirements/debito-tecnico/epic.md", "wiki/log/2026-07-16.md", "wiki/log/2026-07-17.md"]
---

# L'esito sull'host, non la forma dell'asset

Una guardia può essere **verde e cieca**. È la lezione che E10-FEAT-031/032 hanno pagato sul campo, ed
è più generale degli hook: vale per **ogni artefatto che distribuiamo a un ospite**.

## Il buco

Testare un asset distribuito ha due punti d'osservazione possibili, e **non sono lo stesso**:

| Cosa si asserisce | Domanda a cui risponde | Cosa non vede |
|---|---|---|
| **La forma dell'asset** | «il file che spediamo dichiara il wiring giusto?» | se quel wiring **arriva** all'ospite |
| **L'esito sull'host** | «un ospite che aggiorna finisce nello stato giusto?» | — |

FEAT-031 aveva guardie verdi sulla **forma**: gli asset `settings*.json` dichiaravano correttamente il
path ancorato. Ma su un ospite che **aggiornava**, il merge duplicava la voce (Claude) o scartava la
nuova (Copilot) — vedi [[identita-hook-nel-merge]]. **Il fix non arrivava, e nessun test lo diceva**:
il difetto viveva esattamente **nello spazio fra le due colonne**.

## Perché è insidioso

- **La guardia verde dà una falsa quietanza.** Non un errore, un errore *taciuto*: la CI conferma
  «l'asset è giusto», e si legge come «gli ospiti ce l'hanno». Sono due affermazioni diverse.
- **Il difetto è invisibile all'install pulito.** Su un ospite nuovo il merge parte da zero e produce lo
  stato giusto — il bug esiste **solo lungo la transizione**, cioè solo per chi *ha già* la versione
  vecchia. Chi testa installando da zero non lo vedrà **mai**.
- **La forma è ciò che controlliamo, l'esito è ciò che conta.** L'asset è il nostro output; lo stato
  dell'ospite è il nostro *risultato*. Asserire l'output è comodo e sembra sufficiente.

## La regola

> Per ogni asset host-facing, una guardia deve asserire l'**esito su un host che aggiorna** — partendo
> dallo stato **vecchio**, non dal vuoto — non solo la forma dell'asset spedito.

Concretamente, le 10 guardie di `test_settings_merge_identity.py` partono tutte da un host **già
cablato in una forma precedente** e asseriscono lo stato **finale**: `.ps1`→`.py`, relativo→ancorato,
`cwd` aggiunto, host già duplicato che si **ricompatta**, tre generazioni che collassano, hook
dell'utente **preservato**, idempotenza al secondo giro.

## Tre istanze dal campo (2026-07-24) — dove il punto cieco è l'installer

Quattro nodi della federazione — *VM-WorkingFolder*, *Sinthari*, *Kaelen*, *Acta* — hanno segnalato
indipendentemente lo stesso schema in tre forme. Non riguardano una guardia: riguardano **l'installer
stesso**, che è l'asset più host-facing che abbiamo.

**1. Il runtime non si muove, e l'upgrade dichiara successo.** Su *Sinthari*: stamp `.sertor-version`
a `0.1.5`, `sertor-core` nel lock fermo a **`0.1.0`** — un solo commit, quello d'installazione del 24
giugno, sopravvissuto a **tre** upgrade tutti riusciti. Causa: dipendenza senza vincolo di versione e
sorgente git **senza ref**, quindi `uv` non ha alcuna ragione di ri-risolvere il commit. L'upgrade
sposta gli **asset** e conclude di aver spostato tutto. Come lo riassume Sinthari: *«non è un
incidente della 0.1.5, è il comportamento normale dell'upgrade su host già installati, che non era
stato visto perché niente lo dichiara»*.

**2. Il comando pubblicato non è mai stato eseguito.** L'avviso dell'auto-updater suggerisce
`uvx --refresh sertor`, che fallisce perché risolve il pacchetto root, il quale non fornisce quella
console-script. Il testo è stato scritto e revisionato, mai **lanciato** su un host. Vedi
[[auto-update-version-check]].

**3. Una configurazione rotta sopravvive a ogni upgrade.** Su *Kaelen*, un `.mcp.json` con
`--directory` invece di `--project` ha reso il RAG **cieco per un mese** — ogni query `[]`,
indistinguibile da un corpus povero — e l'installer **salta** quel file perché «già registrato»:
ragiona per **presenza**, non per **contenuto**. La configurazione sbagliata è quindi *immune* agli
aggiornamenti.

**Il filo comune.** In tutti e tre i casi qualcosa di nostro era **formalmente corretto** — l'asset,
il testo, la registrazione — e l'**esito sull'host** era sbagliato. Nessuna sarebbe emersa da un test
sulla forma; tutte sono emerse da nodi che hanno **eseguito** ciò che spediamo. Il rimedio proposto da
*Sinthari* è la regola di questa pagina in una riga: l'upgrade deve riportare **la versione
effettivamente risultante, letta dal runtime**, non «ho fatto».

> **La causa ricorrente, generalizzata:** in due delle tre istanze qui sopra il meccanismo che
> avrebbe dovuto aggiornare non ha fatto nulla perché *«c'era già qualcosa»* — l'installer salta la
> `.mcp.json` registrata, l'upgrade non tocca un pin che esiste. È un pattern a sé, con una terza
> istanza fuori dall'installer (l'idempotenza dell'osservabilità): vedi
> [[identita-per-presenza-o-per-contenuto]].

## Parentele

- È il complemento di [[dogfood-fidelity]]: quella chiede *«giriamo su ciò che gira un ospite?»*,
  questa chiede *«ciò che spediamo ci arriva davvero, anche a chi aggiorna?»*. Entrambe difendono
  la stessa cosa da lati diversi — e il dogfood, da solo, non basta come prova: il bug FEAT-032 è
  stato colto da un **re-install reale** e confermato da un **nodo indipendente** (Noetix), perché il
  nodo che scrive il fix è un teste contaminato.
- È [[constitution|Principio XII]] «Fail Loud» applicato ai **test**: un path che fallisce in silenzio
  è il difetto; una guardia che non guarda dove il silenzio accade lo **istituzionalizza**.
- La ragione per cui il difetto è emerso dal **campo** e non dalla suite è la stessa già vista con
  l'adapter Chroma (FEAT-004 memoria): **un test fedele a metà del contratto nasconde i bug** — lì il
  fake accettava metadata che il componente reale scartava, qui la guardia accettava un asset giusto
  su un host che non lo riceveva.

## Riferimenti

- Origine: E10-FEAT-032 (merge `ddbfb27`/PR #192, 2026-07-17) — meccanismo in [[identita-hook-nel-merge]].
- Scoperta: re-install reale sul dogfood (2026-07-16), **non** dai test — che erano tutti verdi.
