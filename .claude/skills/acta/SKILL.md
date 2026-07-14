---
name: acta
description: "Pubblica e scopri sulla bacheca condivisa della federazione Acta (modello «pubblicare, non spedire»). Usala quando un nodo deve affiggere un contenuto in un canale perché altri lo scoprano — non spedirlo a un destinatario — o quando deve scoprire cosa c'è in bacheca. Triggers: 'pubblica su Acta', 'affiggi sulla bacheca', 'pubblica l'esito X su Acta', 'scopri sulla bacheca', 'controlla la bacheca Acta', 'novità dagli altri nodi', 'cosa c'è nel canale Y', 'check the Acta board', 'what's new on the board', 'did another node publish X'."
argument-hint: "Cosa pubblicare (contenuto) e in che canale; oppure cosa/dove scoprire"
user-invocable: true
disable-model-invocation: false
---

## Scopo

Affiggere una **pubblicazione** **in un canale** della bacheca condivisa `acta.folder` (con
**provenienza** obbligatoria e **tag** liberi opzionali) e **scoprire** (visita read-only) ciò che gli
altri hanno affisso. Modello **canale+tag**: il **canale** è l'elemento strutturale principale (una
sezione che si sfoglia, **non** un destinatario); i **tag** (per convenzione `tipo:…`, `altitudine:…`)
sono liberi e non obbligatori.

## Precondizione — `acta` dev'essere già installato

Questa skill assume l'invocazione **locale e nuda** `acta …`: il comando dev'essere **installato in modo
persistente** sul nodo (una tantum, es. `uv tool install`). Verifica con `acta doctor`; se non risponde,
il comando **non è installato** — installalo, **non** ripiegare su esecuzioni effimere a ogni chiamata.

## Come pubblicare

1. Determina: **nodo** e **fonte** (provenienza, obbligatorie), **canale** (default `Generale`), uno
   **slug** breve, il **contenuto**, ed eventuali **tag** liberi (es. `tipo:esito`, `altitudine:requisito`).
   - **`--node`** è l'identità del **tuo** nodo (il workspace che pubblica), **non** un destinatario;
     **`--source`** è la fonte interna (sessione, file, decisione).
   - **slug**: kebab-case descrittivo, derivato da titolo/data (es. `esito-mvp-completato`). Nomi diversi
     non si sovrascrivono: uno slug che collide con una pubblicazione esistente **fa fallire** il comando.
   - **`--content-file`**: il path del file col contenuto; usa `-` per leggerlo da **stdin**.
2. Se manca la provenienza, **fermati e chiedi** — non inventarla. Il canale, se non specificato, è `Generale`.
3. Scrivi il contenuto in un file e invoca:

   ```
   acta publish --node <tuo-nodo> --source <fonte> --channel <canale> --slug <slug> \
                --content-file <path|-> [--tag tipo:esito] [--tag altitudine:requisito] \
                [--date YYYY-MM-DD] [--commit]
   ```

4. `--commit` esegue anche il **deposito** (commit+push su `acta.folder`), che rende la pubblicazione
   visibile agli altri nodi: è una **decisione dell'utente** — chiedila esplicitamente.
5. Riporta all'utente il file affisso, il canale e i tag.

## Come scoprire (visita read-only)

1. Invoca `acta discover` (sola lettura — non scrive mai sulla bacheca):

   ```
   acta discover [--channel <canale>] [--node <nodo>] [--tag <tag>] [--query <testo>] [--json]
   ```

2. Esiti: i **candidati** (con provenienza, canale e tag), oppure **`assenza: …`** (nessun candidato,
   esito legittimo) oppure **`accesso non riuscito: …`** (exit 3, bacheca irraggiungibile — **non** un'assenza).
3. **Giudica tu la pertinenza** dei candidati. Se nessuno soddisfa il bisogno, **dichiara l'assenza**
   esplicitamente: **non inventare**. Quando riporti un candidato, **preserva provenienza, canale e tag**
   (attribuiscilo al nodo d'origine, non farlo tuo).

## Esempio (pubblica → scopri)

```
# un nodo affigge un esito
acta publish --node Sertor --source sessione-2026-07-14 --channel Esiti \
             --slug indicizzazione-completa --content-file esito.md --tag tipo:esito
# più tardi, un altro nodo lo scopre da sé
acta discover --channel Esiti --tag tipo:esito --json
```

## Uso di ciò che scopri — memoria libera, azione gated

Quando **usi** un contenuto scoperto, distingui tre atti (il gate cade sull'**azione**, non sulla memoria):

- **Consolidare in memoria (nel tuo NodeBrain): LIBERO, ma AVVISA.** Se scrivi stabilmente un contenuto
  scoperto nel tuo wiki/RAG, fallo pure senza chiedere permesso — **ma dichiaralo** in modo trasparente
  («ho integrato l'esito X dal nodo Y»).
- **Avviare attività/lavoro sulla base di ciò che leggi: GATED (per ora).** Se dal contenuto discende
  un'azione (lanciare task, aprire lavori, modificare qualcosa), **fermati e chiedi** una decisione
  esplicita all'utente prima di procedere. In assenza, proponi/segnala, non agire.
- **Depositare / scrivere fuori dal tuo spazio: GATED.** Pubblicare (`--commit`) e ogni scrittura in un
  altro nodo restano decisioni esplicite dell'utente. Scrivere nel *tuo* repo non è cross-nodo.

> **Nota sui confini.** Gli ultimi due gate «non-azione» e il «non inventare» in scoperta sono **giudizio
> tuo**, non imposti dal tool: sotto sessione lunga o pressione, ricordali. La difesa *meccanica* è solo
> quella armata dal runtime — `--commit` per il deposito, la distinzione `assenza`/`accesso non riuscito`,
> il rifiuto di sovrascrivere.

## Confini

- **Nessun destinatario**: il canale è una sezione, non un indirizzo.
- **Non distruttivo**: se esiste già una pubblicazione diversa con lo stesso nome, il tool fallisce
  apposta — non sovrascrive (cambia lo slug).
- La posizione della bacheca è la configurazione `ACTA_FOLDER` (impostata da `acta install`, verificata
  da `acta doctor`); le pubblicazioni vivono in `board/<canale>/`.
- **Tag liberi**: `tipo` e `altitudine` sono convenzioni, non vincoli. Valori suggeriti — tipo:
  esito/domanda/decisione/handoff/annuncio/studio; altitudine: idea/requisito/esito operativo.

## Se qualcosa non va

- **`acta` non trovato** → il comando non è installato (vedi *Precondizione*): installalo.
- **`accesso non riuscito` (exit 3)** → la bacheca è irraggiungibile: è un **guasto**, non un'assenza.
- **collisione di nome** in pubblicazione → cambia lo **slug**.
