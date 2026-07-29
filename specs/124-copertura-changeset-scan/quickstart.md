# Quickstart — verificare la feature dal vivo

**Feature**: `124-copertura-changeset-scan` · **Date**: 2026-07-29

Come esercitare il comportamento **attraverso il vehicle** (Principio XI), non importando la libreria.
Tutti i comandi in PowerShell.

## Il difetto, prima del fix — la prova che deve invertirsi

Su un progetto con la capacità wiki installata, con la partizione di giornale di oggi **non ancora
consegnata**:

```powershell
# 1. produci lavoro in un'area sorvegliata
Add-Content src/qualcosa.py "`n# probe`n"

# 2. registra
uv run --project .sertor sertor-wiki-tools append-log --entry-op record --title "probe"

# 3. produci ALTRO lavoro, dopo la registrazione
Add-Content src/altro.py "`n# dopo`n"

# 4. chiedi se c'è lavoro non registrato
uv run --project .sertor sertor-wiki-tools scan --json
```

**Prima**: `pending: 0` — il gate non vede `src/altro.py`, né nient'altro, per il resto della giornata.
**Dopo**: `pending: 1`, con `src/altro.py` **nominato** in `pending_paths`.

## Che la registrazione dica cosa copre

```powershell
Get-Content wiki/log/$(Get-Date -Format 'yyyy-MM-dd').md -Tail 12
```

In coda alla voce deve comparire il blocco:

```
<!-- sertor-covers/1
src/qualcosa.py@<identità del contenuto>
-->
```

**Nota**: copre `src/qualcosa.py` e **non** `src/altro.py`, perché quest'ultimo non esisteva quando la
voce è stata scritta. È il punto della feature.

## Che un elemento coperto e poi modificato torni pendente

```powershell
Add-Content src/qualcosa.py "`n# modificato di nuovo`n"
uv run --project .sertor sertor-wiki-tools scan --json
```

`src/qualcosa.py` torna fra i pendenti: la copertura vale per il **contenuto** che è stato registrato,
non per il nome del file.

## Che una registrazione vuota non soddisfi il gate

```powershell
# una partizione senza alcuna voce, o una riga vuota appesa
Add-Content wiki/log/$(Get-Date -Format 'yyyy-MM-dd').md "`n"
uv run --project .sertor sertor-wiki-tools scan --json
```

Il lavoro resta pendente. **Prima** bastava toccare il file.

## Che un controllo fallito non produca un «pulito»

Rendere il sistema di versionamento non interrogabile per un istante (per esempio con un'operazione git
concorrente che tiene il lock) e poi:

```powershell
uv run --project .sertor sertor-wiki-tools scan --json
```

Atteso: `determination: "failed"` con `determination_reason` valorizzato — **non** `pending: 0` con
`determination: "ok"`. Il gate allo `Stop` **non blocca** (un ambiente rotto non deve rendere la
sessione non chiudibile) ma **lascia traccia** in `.sertor/.last-hook-error`.

## Che lo schema non sia cambiato

```powershell
uv run --project .sertor sertor-wiki-tools scan --json | ConvertFrom-Json | Select-Object -ExpandProperty schema
```

Deve restare **`wiki.scan/1`**. Se cambia, il gate sparisce in silenzio su ogni ospite non aggiornato.

## Su un progetto senza sistema di versionamento

Il comportamento di ripiego resta: l'esito continua a dichiarare che sta usando una stima **e perché**
(`anchor_kind` + `anchor_fallback_reason`). Da verificare esplicitamente: è il caso host-agnostico che
non deve regredire.
