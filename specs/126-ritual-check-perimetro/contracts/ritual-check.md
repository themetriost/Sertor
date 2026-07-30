# Contratto — `sertor-wiki-tools ritual-check` (aggiornato, E10-FEAT-060)

Sostituisce, per le parti indicate, il contratto originario in
[`specs/097-rituale-anti-skip/contracts/ritual-check.md`](../../097-rituale-anti-skip/contracts/ritual-check.md).
Le opzioni della riga di comando **non cambiano**.

## Invocazione

```
sertor-wiki-tools ritual-check [--base <ref>] [--pages a.md,b.md] [--json]
```

- `--base <ref>` — riferimento di confronto per la porzione **già consegnata**. Significato
  **invariato**: `<ref>...HEAD`. Se omesso, si risolve col ramo di default **rilevato a runtime**.
- `--pages` — perimetro **esplicito**: sostituisce la derivazione, non vi si somma.
- `--json` — emette `wiki.ritual_check/1`; altrimenti summary umano.

## Perimetro (comportamento nuovo)

Senza `--pages`, il perimetro è l'**unione** di:

1. **`committed`** — percorsi cambiati in `<base>...HEAD`;
2. **`worktree`** — percorsi cambiati e **non ancora consegnati**: modifiche ai file tracciati
   (confronto *sul contenuto*, così una differenza di sole terminazioni di riga non entra) più i file
   **non tracciati**, elencati singolarmente e non collassati sulla cartella.

I percorsi **ignorati dal VCS** non entrano — non perché vengano filtrati, ma perché non compaiono
nelle sorgenti.

Le pagine **aggiunte** dello step comprendono sia quelle aggiunte nel committato sia quelle **non
tracciate**: una pagina di distillazione appena creata e non ancora consegnata conta come distillazione
avvenuta, altrimenti lo strumento suggerirebbe di distillare ciò che è appena stato distillato.

## Output JSON (`wiki.ritual_check/1`)

```json
{
  "scope": "git:44208ff...HEAD+worktree",
  "perimeter": {
    "kind": "derived",
    "sources": [
      {"name": "committed", "ref": "44208ff...HEAD", "paths": 3},
      {"name": "worktree",  "ref": null,             "paths": 5}
    ]
  },
  "pages_in_scope": ["concepts/ritual-check.md", "syntheses/roadmap.md"],
  "distill_candidates": [
    {"pages": ["..."], "shared_new_backlinks": 2, "reason": "..."}
  ],
  "drift_candidates": [
    {"page": "...", "signal": "stale-updated", "detail": "..."}
  ],
  "declaration_scaffold": "Rituale: record: <?> · distill: <...> · lint: <...>",
  "schema": "wiki.ritual_check/1"
}
```

Con `--pages`:

```json
{
  "scope": "explicit:2",
  "perimeter": {"kind": "explicit", "sources": [{"name": "explicit", "ref": null, "paths": 2}]}
}
```

**`scope` è derivata da `perimeter`**, non mantenuta in parallelo (Principio XIV): per il perimetro
solo-committato e per quello esplicito il suo valore è **identico a oggi**.

**`perimeter` è sempre presente**, anche a zero candidati — è il caso in cui serve di più: uno `0` senza
provenienza non distingue «non c'è nulla» da «ho guardato altrove».

## Summary umano

Anche la resa testuale dichiara il perimetro: è quella che una persona e un agente leggono davvero.

```
scope=git:44208ff...HEAD+worktree pages=2 distill=1 drift=3
  perimetro: committed=3 · worktree=5
  Rituale: record: <?> · distill: <1 candidato → verdetto?> · lint: <3 pagine drift → verdetto?>
```

## Errori (Principio XII)

| Situazione | Esito |
|---|---|
| `diff <base>...HEAD` fallisce | **errore dichiarato** (già oggi) |
| derivazione dei file tracciati non consegnati fallisce | **errore dichiarato** |
| derivazione dei file non tracciati fallisce | **errore dichiarato** |
| determinazione delle pagine **aggiunte** fallisce | **errore dichiarato** *(prima: insieme vuoto silenzioso)* |
| perimetro non determinabile (né git né `--pages`) | **errore dichiarato** (già oggi) |

**Limite dichiarato, non deroga.** Il recupero dei collegamenti di una pagina alla revisione di
confronto (`show <base>:<path>`) continua a restituire l'insieme vuoto quando fallisce: per una pagina
**mai consegnata** quella è la risposta *corretta* (tutti i collegamenti sono nuovi), e il comando usa
lo stesso codice d'uscita per «percorso assente» e «repository rotto». Poiché le interrogazioni del
perimetro falliscono forte prima, un git rotto emerge comunque.

## Invarianti preservati

- Sola lettura · zero LLM · offline · nessuna rete.
- Host-agnostico: cartelle, tassonomia e soglie da `wiki.config.toml`; ramo di default rilevato a
  runtime, mai assunto.
- Il tool **trova**, l'agente **giudica**: nessun campo porta un verdetto semantico.
- Identificativo di contratto invariato; estensione **additiva**.
