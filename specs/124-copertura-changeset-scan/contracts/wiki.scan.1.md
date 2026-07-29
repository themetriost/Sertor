# Contract — `wiki.scan/1`: campi additivi (stringa di schema INVARIATA)

**Feature**: `124-copertura-changeset-scan` · **Date**: 2026-07-29

## ⚠️ Il vincolo, prima di tutto il resto

**La stringa `wiki.scan/1` non si bumpa.** Verificato sul codice consumatore
(`wiki-guard.py:105`):

```python
if not scan or scan.get("schema") != "wiki.scan/1" or int(scan.get("pending", 0)) <= 0:
    return   # fail-open: non blocca
```

Il confronto è **per uguaglianza** e il ramo negativo è **fail-open**. Quindi un bump non romperebbe il
gate in modo rumoroso: lo farebbe **sparire in silenzio** su ogni ospite non ancora aggiornato — il
modo peggiore di rompere una guardia, perché il sintomo è *nessun sintomo*. Lo stesso vale per
`wiki-pending-check.py`.

Ogni informazione nuova viaggia quindi su **campi additivi**.

## Campi

### Invariati

`schema` · `pending` · `pending_paths` · `pending_truncated` · `anchor` · `anchor_kind` ·
`anchor_ref` · `anchor_fallback_reason` · `dirs_scanned` · `message` · `stale_recording`

### Additivi

| Campo | Tipo | Valori | Significato |
|---|---|---|---|
| `determination` | `str` | `"ok"` \| `"failed"` | se il sistema **è riuscito** a stabilire il lavoro non registrato |
| `determination_reason` | `str \| null` | causa tipizzata | valorizzato **solo** quando `failed` |
| `legacy_coverage` | `int` | `≥ 0` | quante registrazioni **non consegnate e prive di blocco di copertura** stanno valendo per compatibilità. `0` nel caso normale |

## Invariante che il contratto impone

> `pending == 0` è un'affermazione sul mondo **solo** quando `determination == "ok"`.

Con `determination == "failed"`, `pending` **non** significa «pulito»: significa «non ho potuto
guardare». Oggi le due cose sono indistinguibili, ed è il difetto della Storia 2.

## Obblighi dei consumatori

| Consumatore | Obbligo |
|---|---|
| `wiki-guard` (Stop, **bloccante**) | con `determination == "failed"` **non** trattare come pulito: scrivere il breadcrumb ispezionabile (`hook.error/1`) e **non bloccare** — un ambiente rotto non deve rendere la sessione non chiudibile (lezione FEAT-045) |
| `wiki-pending-check` (SessionEnd, promemoria) | idem, con la sola segnalazione |
| Consumatore **non aggiornato** | continua a funzionare: legge `schema`/`pending`/`pending_paths` e ignora i campi che non conosce |

## Perché il fallimento non blocca

Sembra una deroga al Principio XII e non lo è. Il principio chiede che la degradazione **segnali**, non
che si trasformi in un blocco: un `git` che non risponde renderebbe la sessione **non chiudibile**, e
la via d'uscita imboccata da chiunque sarebbe aggirare il gate. La FEAT-045 ha già pagato questa
lezione — il rimedio è **dichiarare**, non sbarrare.

## Guardia

La guardia esistente che asserisce la stringa di schema (scritta in FEAT-045) va **estesa** ai campi
nuovi, non sostituita: deve continuare a fallire se qualcuno bumpa `wiki.scan/1`, **e** verificare che
un consumatore che ignora i campi additivi resti funzionante.
