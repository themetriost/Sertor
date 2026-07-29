# Data Model — la registrazione copre un changeset, non una data

**Feature**: `124-copertura-changeset-scan` · **Date**: 2026-07-29

Nessuna persistenza nuova: tutto vive nel **giornale** e nell'esito già esistente. Le entità sono
strutture in memoria più un formato testuale.

---

## `CoveredItem` — un elemento coperto

| Campo | Tipo | Significato |
|---|---|---|
| `path` | `str` | percorso **relativo al progetto**, POSIX (mai assoluto: viaggia fra host) |
| `content_id` | `str` | identità del **contenuto** al momento della copertura, oppure il sentinella `-` |

**Regole di validazione**
- `path` non vuoto, sempre POSIX, sempre relativo alla radice del progetto.
- `content_id` è l'identità che il sistema di versionamento assegna al contenuto; per un elemento
  **rimosso** vale `-` (assenza), perché una rimozione è lavoro e va poter essere coperta.
- Uguaglianza per **entrambi** i campi: è ciò che fa scadere da sé una copertura vecchia.

## `CoverageSet` — ciò che una o più registrazioni coprono

Insieme di `CoveredItem`. Operazione unica: **unione**.

- `covers(path, current_content_id) -> bool`: vero se la coppia è nell'insieme.
- Un `path` presente con un `content_id` **diverso** da quello attuale **non** è coperto — è il
  meccanismo per cui «modificato di nuovo» torna pendente (FR-011) e per cui le coperture storiche non
  inquinano il presente.

**Composizione**: le registrazioni si compongono per unione, senza ordine e senza regole di priorità.
La correttezza viene dall'ordine di **scrittura** (R6), non da una gerarchia fra voci.

## `PendingDetermination` — l'esito del guardare

| Campo | Valori | Significato |
|---|---|---|
| `status` | `ok` \| `failed` | se il sistema **è riuscito** a stabilire il lavoro non registrato |
| `reason` | `str \| None` | perché non c'è riuscito, quando `failed` |

**Invariante che chiude il difetto R1**: un insieme vuoto è un risultato **solo** quando
`status == ok`. Quando la determinazione fallisce il sistema **non fabbrica** un insieme vuoto — è
esattamente ciò che oggi fa `return … if rc == 0 else []`.

## `ScanResult` — campi **additivi** (schema invariato)

| Campo | Tipo | Nuovo? | Note |
|---|---|---|---|
| `schema` | `str` | no | **resta `wiki.scan/1`** — vincolo non negoziabile |
| `pending`, `pending_paths`, `pending_truncated` | | no | invariati |
| `anchor`, `anchor_kind`, `anchor_ref`, `anchor_fallback_reason` | | no | invariati |
| `dirs_scanned`, `message`, `stale_recording` | | no | invariati |
| **`determination`** | `str` | **sì** | `ok` \| `failed` |
| **`determination_reason`** | `str \| None` | **sì** | causa tipizzata quando `failed` |
| **`legacy_coverage`** | `int` | **sì** | quante registrazioni **non consegnate e prive di blocco** stanno valendo per compatibilità (R4). `0` nel caso normale |

Un consumatore che non conosce i campi nuovi continua a funzionare: legge `schema`, `pending`,
`pending_paths` come prima.

## `AppendLogResult` — campo additivo

| Campo | Tipo | Nuovo? | Note |
|---|---|---|---|
| **`covered`** | `int` | **sì** | quanti elementi la voce appena scritta dichiara di coprire |

Serve a rendere l'operazione **osservabile** da chi la invoca: senza, l'unico modo di sapere cosa è
stato scritto sarebbe rileggere il file.

---

## Transizioni di stato — il ciclo di vita di un elemento di lavoro

```
                    modificato
   [non toccato] ──────────────► [pendente]
         ▲                            │
         │                            │ append-log scrive una voce
         │                            ▼
         │                       [coperto]
         │                            │
         │  consegnato insieme        │ modificato di nuovo
         │  al giornale               │ (content_id cambia)
         └────────────────────────────┴──► [pendente]
```

Il passaggio **[coperto] → [pendente]** per nuova modifica è ciò che oggi non esiste: la copertura è
un fatto per contenuto, non un interruttore per giornata.

## Ciò che NON è nel modello, deliberatamente

- **Nessuna data.** Una registrazione non ha «un giorno di validità»: la data resta il nome del file.
- **Nessuna nozione di «voce recente».** Cade con R1.
- **Nessuna gerarchia fra registrazioni.** L'unione è commutativa.
- **Nessuna copertura semantica.** Che la voce *parli* davvero di quell'elemento resta giudizio: il
  modello copre i path, non i significati — limite dichiarato in spec, non aggirato qui.
