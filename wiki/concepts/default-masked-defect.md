---
title: Il difetto mascherato dal default
type: concept
tags: [difetti, osservabilita, fail-loud, manopole, testing, pattern-diagnostico]
created: 2026-07-24
updated: 2026-07-24
sources: ["src/sertor_core/wiki_tools/structure.py", "src/sertor_core/observability/logging.py", "src/sertor_core/config/settings.py", "tests/unit/test_log_event_reserved_fields.py"]
---

# Il difetto mascherato dal default

Un difetto che **esiste da sempre nel codice ma non si manifesta**, perché il percorso che lo
attraverserebbe è chiuso da una manopola spenta di default. Il codice è rotto; nessuno lo vede.

Non è un difetto *latente* qualunque: è latente **per una ragione precisa e ripetibile** — la
configurazione conservativa che il progetto adotta di proposito (Principio VIII: default sicuri) è la
stessa cosa che impedisce al difetto di emergere. La prudenza che protegge l'utente protegge anche il
bug.

## La firma

Si riconosce da tre sintomi che compaiono insieme:

| Sintomo | Perché accade |
|---|---|
| **I test passano in isolamento, falliscono nella suite** | in isolamento la manopola è al default; nella suite un test precedente l'ha accesa e non l'ha rimessa |
| **Il numero di fallimenti è alto e apparentemente scorrelato** | ogni test *successivo* a quello che accende la manopola cade, in file che non hanno relazione fra loro |
| **Il fallimento è a valle, mai dove sta la causa** | il messaggio d'errore accusa il consumatore, non il produttore del dato malformato |

Il terzo è il più insidioso: porta a cercare nel posto sbagliato.

## Il caso che ha fatto emergere il pattern (2026-07-24)

`wiki_tools/structure.py` e `registry.py` passavano `created=` come campo extra a `log_event`. Ma
**`created` è un attributo riservato di `LogRecord`** — è il timestamp del record — e
`logging.makeRecord` solleva `KeyError` quando `extra` prova a sovrascriverlo.

La manopola che lo mascherava è il **livello del logger**: finché `sertor_core` sta a `WARNING`, un
`log_event(INFO, …)` non crea alcun record e non arriva mai a `makeRecord`. Il codice sbagliato non
viene eseguito fino in fondo.

Chi accende la manopola? **`enable_observability` abbassa il livello a INFO di proposito**, perché gli
handler possano catturare gli eventi. Cioè: la funzione che rende osservabile il sistema è quella che
fa esplodere il difetto.

**Conseguenza in produzione:** con `SERTOR_OBSERVABILITY=true`, `sertor-wiki-tools structure init`
andava in crash. Non un degrado: un crash.

**Conseguenza nella suite:** 83 fallimenti, tutti dopo il primo test che abbassava il livello, ognuno
passante in isolamento — la firma completa.

## Non è un caso isolato: quattro istanze della stessa forma

Il pattern si è già presentato in questo progetto, sempre con una manopola conservativa davanti:

| Manopola | Default | Cosa nascondeva |
|---|---|---|
| livello del logger | `WARNING` | il campo riservato `created` (questo caso) |
| `SERTOR_MEMORY` | off | il gate della cattura leggeva l'ambiente sbagliato → no-op silenzioso, **zero sessioni archiviate** ([[memoria-conversazioni]], E4-FEAT-012) |
| `SERTOR_EMBED_CACHE` | off (allora) | il costo ricorrente illimitato del re-index automatico, emerso solo alla security review A-08 |
| `SERTOR_MIN_SCORE` | `None` | il segnale `low_confidence` non viene mai calcolato — quindi non esiste come informazione per l'agente ([[retrieval-confidence]]) |

L'ultimo è particolarmente istruttivo: lì il default-off non nasconde un *crash* ma un'**assenza di
capacità**. Il codice è corretto e non fa nulla.

## Perché il rapporto con *Fail Loud* è meno ovvio di quanto sembri

[[fail-loud-fix-cause]] (Principio XII) vieta di **silenziare** un errore: non disattivare una
capacità per schivarne il fallimento, non degradare senza segnalare. Questo pattern è un **parente, non
un'istanza**:

- il Principio XII parla di ciò che **facciamo noi** a un errore che si è già manifestato;
- qui l'errore **non si manifesta affatto**, e nessuno l'ha silenziato: la configurazione lo ha
  semplicemente reso irraggiungibile.

Nessuno ha nascosto niente. **Il default conservativo non è il difetto — è ciò che ritarda la
scoperta.** La lezione non è «cambia i default», che sarebbe la conclusione sbagliata (i default
conservativi hanno buone ragioni), ma «**esercita il percorso che il default chiude**».

## Il correttivo

**Un test che accende la manopola.** È l'unico rimedio strutturale: se nessun test attraversa il
percorso che il default chiude, quel percorso non è coperto — indipendentemente da quanto sia alta la
percentuale di copertura dichiarata.

Concretamente, per il caso di cui sopra
(`tests/unit/test_log_event_reserved_fields.py`):

1. una fixture porta il logger a INFO **e lo ripristina** — l'accensione va isolata, o si crea un
   nuovo accoppiamento d'ordine al posto di quello che si sta rimuovendo;
2. il test verifica il **comportamento** (l'operazione emette il proprio evento senza esplodere), non
   la forma del sorgente: un controllo del tipo «la stringa `created=` non compare nel file» passerebbe
   anche dopo una regressione scritta in modo diverso;
3. la lista dei nomi riservati è **parametrizzata**, così una versione futura di Python che ne aggiunga
   uno viene scoperta dal test invece che dall'utente.

**Corollario sulla copertura.** Una suite che gira solo ai default misura una frazione del sistema che
nessuna metrica di copertura mostra: le righe sono eseguite, i *percorsi condizionati dalla
configurazione* no. Per un progetto la cui configurabilità centralizzata è un principio
([[constitution]], Principio VIII), è un punto cieco strutturale, non accidentale.

## Rimando

Il difetto gemello — l'**ordine dei test** che nasconde una dipendenza fra di essi — è un problema
distinto e presente in questo repo: dopo il fix del caso `created` restano 4 fallimenti in
`test_observability_capture.py` che passano in isolamento e cadono nella suite. Stessa firma, causa
diversa: non un default che maschera, ma uno stato globale non ripristinato.

Vedi [[fail-loud-fix-cause]] · [[osservabilita]] · [[retrieval-confidence]] · [[wiki-tools]].
