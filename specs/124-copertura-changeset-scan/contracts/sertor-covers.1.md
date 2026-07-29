# Contract — `sertor-covers/1`: il blocco di copertura in una voce di giornale

**Feature**: `124-copertura-changeset-scan` · **Date**: 2026-07-29

Formato con cui una voce di giornale dichiara **cosa copre**. Scritto da `append-log`, letto da `scan`.
È un contratto **host-facing**: viaggia nel giornale dell'ospite e va documentato nel playbook.

## Forma

```markdown
## [2026-07-29] record | titolo della voce

corpo curato della voce…

<!-- sertor-covers/1
src/sertor_core/wiki_tools/scan.py@88aa28a1a70a70fef12421ddfea0c58d8ec4f61e
src/sertor_core/wiki_tools/vcs.py@d33aa255838951f972ec23e5d6cb7a7591f2064e
specs/124-copertura-changeset-scan/spec.md@-
-->
```

## Regole

1. **Un commento HTML**, aperto da `<!-- sertor-covers/1` su una riga propria e chiuso da `-->` su una
   riga propria. Invisibile nel markdown reso, presente nel testo grezzo.
2. **Una riga per elemento**, nella forma `<path>@<content_id>`.
   - `<path>`: relativo alla radice del progetto, POSIX. **Mai** assoluto.
   - `<content_id>`: identità del contenuto al momento della copertura; **`-`** se l'elemento è stato
     rimosso.
   - Separatore `@`: l'ultimo `@` della riga separa i due campi, così un path che contiene `@` resta
     valido.
3. **Ordine deterministico** (per path), perché il blocco finisce in un file versionato e non deve
   produrre differenze spurie.
4. **In coda alla voce**, dopo il corpo: non interrompe la prosa.
5. **Assente = copre nulla.** Una voce senza blocco non dichiara copertura. *(Eccezione di transizione:
   una voce **non consegnata** priva di blocco vale come copertura di compatibilità e viene **contata**
   in `legacy_coverage` — vedi `wiki.scan/1`.)*
6. **Il blocco non si modifica dopo la scrittura.** Il giornale è append-only: una copertura sbagliata
   si corregge con una voce nuova, non riscrivendo quella vecchia.

## Perché un commento e non prosa visibile

La prosa visibile sarebbe leggibile, ma con l'identità di contenuto diventa rumore illeggibile, e
troncarla la renderebbe non più autorevole. Il commento tiene **prosa pulita per chi legge** e **dato
esatto per chi verifica**, nello stesso artefatto — senza creare una seconda copia da riconciliare
(Principio XIV).

## Perché dentro la voce e non in un file accanto

Un file accanto può divergere dal giornale: si cancella una voce a mano e il file mente. Dentro la
voce, la copertura **non può separarsi** da ciò che descrive — si sposta, si cancella e si consegna
insieme ad essa.

## Compatibilità

- Il tag `sertor-covers/1` è **versionato per conto proprio**: bumparlo è sicuro perché nessun
  consumatore fail-open lo confronta per uguaglianza. *(È l'opposto di `wiki.scan/1`, che non si
  bumpa — la differenza è che lì un mismatch fa **sparire** una guardia.)*
- Un lettore che non conosce il blocco vede un commento HTML e lo ignora: nessun giornale esistente si
  rompe.
- Un giornale **senza** blocchi resta valido: significa «nessuna copertura dichiarata».
