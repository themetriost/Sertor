# Research — decisioni di design (E10-FEAT-060)

Ogni decisione qui è **motivata dall'evidenza misurata** nei requisiti, non da preferenza di stile.

## R-1 — Dove vive la derivazione dell'albero di lavoro

**Decisione: in `vcs.py`, come funzione pubblica `worktree_changes()`, consumata da ENTRAMBI.**

Tre opzioni erano sul tavolo:

| Opzione | Pro | Contro |
|---|---|---|
| Copiare la logica dentro `ritual_check.py` | zero rischio su `scan` | **due copie**: è il difetto stesso, riprodotto |
| Helper in `vcs.py` consumato dal solo `ritual_check` | nessun rischio su `scan` | si passa da **una** implementazione a **due** |
| **Helper in `vcs.py` consumato da entrambi** | divergenza **impossibile per costruzione** | tocca `scan.py`, che regge l'hook bloccante su ogni ospite |

Vince la terza, ma **non era la scelta iniziale** — ed è la parte che vale la pena registrare.

*Come si è corretta.* La prima decisione era la seconda opzione, motivata dal rischio su `scan`. Una
domanda dell'utente — *«ma quindi cosa abbiamo fatto?»* — ha reso visibile il conto: **da 1 a 2**
copie, cioè duplicazione **aggiunta**, non rimossa. E il rischio invocato per rinviare **si era già
estinto grazie al lavoro stesso**: l'helper esisteva, aveva 8 test propri, e un test dimostrava che le
due producevano lo stesso identico output. Restava una modifica con **un solo punto di chiamata**.

Lezione che non riguarda questa feature soltanto: **una valutazione di rischio invecchia**. Quella
corretta al momento della decisione era diventata falsa un'ora dopo, e nulla la rivaluta — l'ha scritta
chi poi non la rilegge.

## R-2 — Quale porzione di «consegnato»

**Decisione: resta `<base>...HEAD`, cioè quella indicata dall'utente tramite `--base`.**

`scan` parte dall'**ultima registrazione** (àncora derivata dal giornale), `ritual-check` dalla
**biforcazione del ramo**. Sono due domande diverse anche sulla metà committata, e la tentazione era
allinearle entrambe.

Scartata: `--base` è un'**opzione pubblica** con un significato documentato. Cambiare cosa misura
lasciandole lo stesso nome è *ridefinire in silenzio un contratto* — esattamente il difetto in
riparazione, applicato al rimedio. Conseguenza accettata: su un ramo con più step già registrati il
perimetro è più ampio dello step corrente; la **dichiarazione** (R-3) è ciò che rende quell'ampiezza
leggibile invece che sorprendente.

## R-3 — Forma della dichiarazione del perimetro

**Decisione: una struttura `perimeter` con le sorgenti e i loro conteggi; la stringa `scope` viene
DERIVATA da essa.**

La prima stesura prevedeva di affiancare la struttura nuova alla stringa `scope` esistente. Il
**Constitution Check (Principio XIV)** l'ha bocciata: sarebbero state due descrizioni dello stesso
fatto, libere di divergere — la malattia curata, reintrodotta nel rimedio. Ora esiste **una** fonte e
una funzione che ne ricava la stringa.

**Sempre presente, anche a zero candidati.** L'alternativa «dichiara solo se il perimetro è composito»
è stata scartata: reintrodurrebbe il silenzio nel caso semplice, che è precisamente dove il difetto si
è manifestato. Uno `0` senza dichiarazione è ambiguo; è l'ambiguità il difetto, non lo zero.

## R-4 — Fail-loud: quali interrogazioni

**Decisione: tutte quelle che compongono il perimetro. Una sola tolleranza, dichiarata.**

| Interrogazione | Oggi | Dopo |
|---|---|---|
| `diff --name-only <base>...HEAD` | già solleva | invariata |
| `diff --name-only -z HEAD` (tracciati) | non esiste | **solleva** su rc≠0 |
| `status --porcelain -z -uall` (non tracciati) | non esiste | **solleva** su rc≠0 |
| `diff --diff-filter=A <base>...HEAD` (aggiunte) | **`if rc == 0:` → vuoto silenzioso** | **solleva** |
| `show <base>:<path>` (collegamenti precedenti) | vuoto su rc≠0 | **invariata, e dichiarata** |

L'ultima riga è l'unica tolleranza e non è pigrizia: per una pagina **mai consegnata** il fallimento è
la risposta corretta, e `git show` non distingue «percorso assente» da «repository rotto». Trattarla
come errore romperebbe il caso che la feature deve far funzionare. Poiché le interrogazioni del
perimetro falliscono forte *prima*, un git rotto emerge comunque.

**Perché il ramo delle «aggiunte» era il più insidioso:** fallendo in silenzio lasciava `added_pages`
vuoto, quindi `has_new_distill_page` falso, quindi il candidato a distillazione veniva emesso **come se
non avessi distillato** — un suggerimento sbagliato prodotto da un guasto invisibile.

## R-5 — Come si impedisce che la derivazione torni a essere due

**Decisione: una guardia strutturale, non un test di equivalenza.**

Con una sola implementazione il test di equivalenza della prima stesura è diventato **vacuo per
costruzione** — confrontava una funzione con sé stessa — ed è stato **rimosso**: un test che non può
fallire va tolto, non tenuto per conforto.

Al suo posto la domanda che nessun test comportamentale può porre, perché **due copie divergenti
funzionano entrambe finché non divergono**: *esiste una sola derivazione?* La guardia sorveglia le
**invocazioni git che costituiscono** la derivazione (il diff content-aware sui tracciati, lo stato dei
non tracciati) e pretende che compaiano **solo** in `vcs.py`. Un wrapper che delega — come il fail-loud
di `ritual_check` — è legittimo e non viene confuso con una copia: il criterio è la sostanza, non il nome.

**Provata contro la propria vacuità, e ne aveva bisogno.** Le prime due stesure della guardia
**passavano a vuoto**: la prima cercava per nome e catturava il wrapper; la seconda ispezionava la
*funzione* `scan` invece del *modulo*, perché il pacchetto ri-esporta le funzioni omonime. Entrambe
verdi, entrambe cieche. Ora un test verifica che gli oggetti ispezionati siano moduli, un altro che le
invocazioni esistano davvero in `vcs`, e la guardia è stata provata reintroducendo una copia: diventa
rossa.

## R-6 — Le pagine non tracciate contano come «aggiunte»

**Decisione: sì, e non è un dettaglio.**

Se ho appena creato la pagina d'entità (la distillazione) ma non l'ho ancora consegnata, e la contassi
solo come «cambiata», lo strumento mi suggerirebbe **di distillare ciò che ho appena distillato**.
L'insieme delle pagine aggiunte deve quindi comprendere sia quelle aggiunte nel committato sia quelle
non tracciate (FR-003/FR-004).

È il duale del difetto: la stessa causa che *nasconde* candidati ne *fabbrica* altri.

## R-7 — Cosa resta deliberatamente fuori

- **`--committed-only`** — nessun caso d'uso reale, sarebbe superficie non giustificata (YAGNI,
  Principio III). Additiva se emergerà.
- ~~Unificazione strutturale con `scan`~~ — **inclusa**, non rinviata: E10-FEAT-066 si chiude qui
  senza essere mai stata lavoro a sé.
- **Il perimetro di `scan` che esclude `packages/` e i file di radice** — problema reale ma **distinto**,
  già tracciato come E10-FEAT-063. Citato, non duplicato.
