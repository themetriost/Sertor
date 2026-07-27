# Data Model — Ancora derivata

**Feature**: `123-feat-045-ancora-derivata-scan` · **Data**: 2026-07-27

Nessuna entità **persistita**: `scan` è di sola lettura e non scrive stato. Le entità qui sono le
strutture che attraversano il calcolo e finiscono nel contratto.

---

## 1. Ancora (`Anchor`)

Il punto oltre il quale il lavoro conta come «non registrato». **Porta con sé la propria natura**: è la
proprietà che oggi manca ed è la ragione della feature.

| Campo | Tipo | Regole |
|---|---|---|
| `kind` | `"git"` \| `"mtime"` \| `None` | `None` ⇔ nessuna registrazione trovata ⇒ *tutto* è in sospeso |
| `timestamp` | `float \| None` | epoch. In modalità `git` è la **data della consegna** ancora; in `mtime` è l'orologio del file |
| `ref` | `str \| None` | identificativo della consegna. **Non nullo se e solo se** `kind == "git"` |
| `fallback_reason` | `str \| None` | **Non nullo se e solo se** si è ricaduti sul proxy pur essendo in un ambiente dove ci si aspettava di derivare, oppure per dichiarare che l'ospite non è un repo |

**Invarianti.**
- `kind == "git"` ⟹ `ref is not None` (l'ancora derivata è **citabile**: chi la riceve può verificarla)
- `kind == "mtime"` ⟹ `fallback_reason is not None` (**mai un proxy muto**: è il difetto che chiudiamo)
- `kind is None` ⟹ `ref is None and timestamp is None`

**Tassonomia di `fallback_reason`** (chiusa; un vuoto non tipizzato fa fabbricare a chi legge
un'affermazione falsa):

| Valore | Significato | È un guasto? |
|---|---|---|
| `not_a_repository` | l'ospite non è sotto controllo di versione | **No — funzionamento previsto** (Principio X) |
| `git_unavailable` | il comando non è eseguibile nell'ambiente | Sì, ma non fatale |
| `log_never_committed` | è un repo, ma la cartella di giornale non è mai stata consegnata | No — ospite nuovo, o storia troncata |

---

## 2. Registrazione (`Recording`)

L'atto che sposta l'ancora. Esiste in **due medium**, e la distinzione non è cosmetica: decide se il
gate si può soddisfare senza obbligare a una consegna.

| Medium | Come si riconosce | Vale? |
|---|---|---|
| **Consegnata** | una consegna che ha toccato la cartella di giornale | Sempre — è l'ancora derivata |
| **Nell'albero di lavoro** | la **partizione del giorno corrente** risulta modificata o non tracciata | Sì, **solo se è di oggi** (decisione `clarify`) |
| **Nell'albero, di un altro giorno** | una partizione diversa da oggi risulta modificata | **No** — ma va **nominata** (FR-004a), altrimenti il giornale sembra aggiornato e il gate blocca lo stesso |

---

## 3. Insieme in sospeso (`PendingSet`)

Non più un numero: un **elenco**, di cui il numero è una proprietà derivata — piccola applicazione
dello stesso principio che governa la feature.

| Campo | Tipo | Regole |
|---|---|---|
| `paths` | `list[str]` | relativi alla radice del progetto, ordinati, deduplicati. Filtrati per `source_dirs` e per le esclusioni del profilo |
| `count` | `int` | `len(paths)` **prima** del troncamento: il conteggio resta **sempre esatto** |
| `shown` / `truncated` | `int` | quanti nominati, quanti restano fuori. Il troncamento è **dichiarato**, mai silenzioso |

**Composizione in modalità derivata** — unione di due metà (`research.md` R2):

```
paths = ( diff(ancora → HEAD)  ∪  modifiche non consegnate )
        ∩ source_dirs  −  esclusioni_del_profilo
```

I file **ignorati dal controllo di versione** non compaiono in nessuna delle due metà: non serve
escluderli, **non ci entrano** (verificato, R3). Le **cancellazioni** contano come lavoro in sospeso e
si nominano, ma il path non esiste più su disco: si nomina, non si legge.

---

## 4. Estensione del contratto `wiki.scan/1`

> **Vincolo critico.** La stringa `"wiki.scan/1"` **non cambia**. I due hook consumatori la verificano
> per uguaglianza e vanno in **fail-open** se non corrisponde: un bump non romperebbe il gate, lo
> farebbe **sparire in silenzio** sugli ospiti che aggiornano la libreria ma non gli asset. Vedi il
> contratto per la guardia che lo presidia.

| Campo | Stato | Note |
|---|---|---|
| `pending` | **invariato** | il conteggio esatto |
| `anchor` | **invariato nel tipo** | resta ISO-8601 o `null`, anche in modalità git (FR-013) |
| `dirs_scanned` | **invariato** | |
| `message` | **invariato nella semantica** | i nomi si aggiungono, i template ospite continuano a valere (R7) |
| `schema` | **CONGELATO** | `"wiki.scan/1"` |
| `anchor_kind` | **nuovo** | `"git"` \| `"mtime"` \| `null` |
| `anchor_ref` | **nuovo** | consegna ancora, o `null` |
| `anchor_fallback_reason` | **nuovo** | causa tipizzata, o `null` |
| `pending_paths` | **nuovo** | elenco troncato |
| `pending_truncated` | **nuovo** | quanti fuori dall'elenco |
| `stale_recording` | **nuovo** | partizione non consegnata di un altro giorno, o `null` |

Tutti i campi nuovi sono **additivi**: un consumatore che non li conosce continua a leggere `pending`,
`message` e `schema` come oggi.
