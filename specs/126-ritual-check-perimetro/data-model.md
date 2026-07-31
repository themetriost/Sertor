# Data model — `wiki.ritual_check/1` esteso (E10-FEAT-060)

Estensione **additiva**: l'identificativo di contratto **non cambia** (`wiki.ritual_check/1`), nessun
campo esistente viene rimosso o rinominato. Verificato che non esistano consumatori programmatici — solo
il playbook e le `specs/` lo citano — quindi la trappola di E10-FEAT-062 (bumpare un contratto
confrontato per uguaglianza → consumatori in fail-open → il gate sparisce in silenzio) qui non si
applica; l'additività resta comunque, per prudenza.

## Entità nuove

### `PerimeterSource`

Da dove proviene un insieme di percorsi, e quanti ne ha contribuiti. **È l'entità la cui assenza rende
il difetto invisibile**: oggi il perimetro esiste ma non ha provenienza, quindi non c'è nulla da
confrontare quando due strumenti misurano realtà diverse.

| Campo | Tipo | Significato |
|---|---|---|
| `name` | `str` | `committed` · `worktree` · `explicit` |
| `ref` | `str \| None` | riferimento git per `committed` (es. `<base>...HEAD`); `None` per le altre |
| `paths` | `int` | quanti percorsi ha contribuito **questa** sorgente (prima del filtro sulle pagine) |

### `Perimeter`

| Campo | Tipo | Significato |
|---|---|---|
| `kind` | `str` | `derived` (ricavato dal VCS) · `explicit` (fornito dall'utente con `--pages`) |
| `sources` | `list[PerimeterSource]` | le sorgenti che l'hanno composto, in ordine stabile |

## `RitualCheckResult` — forma risultante

| Campo | Stato | Note |
|---|---|---|
| `scope` | **DERIVATO** | non più mantenuto a mano: calcolato da `perimeter` da un'unica funzione |
| `perimeter` | **NUOVO** | la struttura sopra |
| `pages_in_scope` | invariato | ordinamento stabile (FR-019) |
| `distill_candidates` | invariato | |
| `drift_candidates` | invariato | |
| `declaration_scaffold` | invariato | |
| `schema` | invariato | `wiki.ritual_check/1` |

### Perché `scope` è derivata e non affiancata

È l'applicazione diretta del **Principio XIV** (*Derived State, Not Declared*), e il gate l'ha imposta
in fase di piano: mantenere la stringa **accanto** alla struttura avrebbe creato due descrizioni dello
stesso fatto, libere di divergere. Sarebbe stata la malattia che questa feature cura, reintrodotta nel
suo stesso rimedio.

Forma della stringa derivata (retrocompatibile per il caso semplice):

| Perimetro | `scope` |
|---|---|
| solo committato | `git:<base>...HEAD` — **identico a oggi** |
| committato + albero di lavoro | `git:<base>...HEAD+worktree` |
| esplicito | `explicit:<n>` — **identico a oggi** |

## Invarianti

- **Additività:** un consumatore che legge solo i campi odierni continua a funzionare.
- **Sempre popolato:** `perimeter` è presente anche quando non c'è alcun candidato — è il caso in cui
  serve di più (FR-009).
- **Nessun verdetto:** nessun campo esprime un giudizio semantico. Il tool **trova**, l'agente
  **giudica** (confine D↔N, Principio XI).
- **Stabilità:** a parità di albero, due esecuzioni producono lo stesso documento, campo per campo.
