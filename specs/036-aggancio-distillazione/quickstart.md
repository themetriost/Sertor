# Quickstart — Recuperare una conversazione per distillarla (FEAT-003)

Come usare i nuovi comandi `memory show` / `memory list` e come la modalità «from conversation» di
`distill` vi attinge. Tutto **locale**, nessuna rete, nessun LLM nel percorso di lettura.

## Prerequisiti

- Memoria conversazioni abilitata: `SERTOR_MEMORY=true` (default off — privacy by design).
- Almeno una sessione archiviata: la cattura avviene via `sertor-rag memory archive` (feature 035) o
  l'hook `SessionEnd`. A memoria spenta i comandi falliscono con errore azionabile.

```bash
export SERTOR_MEMORY=true            # PowerShell: $env:SERTOR_MEMORY = "true"
```

## 1. Scoprire quale conversazione recuperare (`memory list`)

```bash
sertor-rag memory list                 # le più recenti (default 20)
sertor-rag memory list -k 5            # le ultime 5
sertor-rag memory list --json          # forma strutturata
```

Output umano:

```
[1] session=C--Workspace-Git-Sertor-abc123  @=2026-06-14T10:21:03Z  turns=3
[2] session=C--Workspace-Git-Sertor-def456  @=2026-06-13T18:02:11Z  turns=12
```

Archivio vuoto → `(no sessions)` (exit 0, nessun errore).

## 2. Recuperare il transcript intero (`memory show`)

```bash
sertor-rag memory show C--Workspace-Git-Sertor-abc123
sertor-rag memory show C--Workspace-Git-Sertor-abc123 --json   # per pipeline/parsing
```

Restituisce **tutti** i turni in ordine, con ruolo, timestamp e testo **completo** (non snippet):

```
session=C--Workspace-Git-Sertor-abc123  @=2026-06-14T10:21:03Z  turns=3  adapter=claude-code
[0] user      @=2026-06-14T10:20:55Z
    <testo completo del turno 0>
[1] assistant @=2026-06-14T10:21:01Z
    <testo completo del turno 1>
...
```

Esiti particolari:
- **chiave inesistente** → `error: session not found: <key>` su stderr, **exit 1** (distinto dal vuoto).
- **sessione esistente ma vuota** → riga di intestazione + `(empty session)`, **exit 0**.
- **memoria spenta** → `error: memory is disabled; set SERTOR_MEMORY=true …`, **exit 1**.

Per restringere *prima* del recupero (sessione molto lunga, o non sai quale): usa `memory search <query>`
(feature 035) per trovare il turno e la sessione giusta, poi `memory show` su quella.

## 3. Distillare da una conversazione archiviata (rituale, giudizio)

La modalità «from conversation» di `distill` ora **attinge all'archivio** invece di pretendere un brief
scritto a mano (`.claude/skills/wiki-author/ops/distill.md`, Gruppo C):

1. Individua la sessione: `sertor-rag memory list` (per recency) o `memory search` (per contenuto).
2. Recupera il transcript: `sertor-rag memory show <session_key>` → portalo in contesto.
3. **Condensa** (giudizio del flusso principale, Opus) e **distilla** nelle pagine wiki (entità durevoli).

> **Vincolo cardine (FR-013):** non esiste e non va introdotto **alcun trigger automatico** di
> distillazione. La distillazione da archivio avviene **solo** per invocazione esplicita, su una
> **sessione mirata**. Mai sull'intero archivio, mai per-turno/per-sessione. La cattura (economica) e la
> distillazione (costosa, LLM) restano disaccoppiate: l'archivio è cold storage di backup.

## 4. Manopole

| Manopola | Default | Effetto |
|----------|---------|---------|
| `SERTOR_MEMORY` | `false` | gate privacy: off → i comandi falliscono con errore azionabile |
| `SERTOR_MEMORY_LIST_LIMIT` | `20` | numero di sessioni di `memory list` (override con `-k/--limit`) |

## 5. Verifica rapida (dogfood)

```bash
SERTOR_MEMORY=true sertor-rag memory list -k 3 --json | python -m json.tool
SERTOR_MEMORY=true sertor-rag memory show "$(SERTOR_MEMORY=true sertor-rag memory list -k 1 --json | python -c 'import sys,json;print(json.load(sys.stdin)[0]["session_key"])')" | head -20
```

A memoria spenta:

```bash
sertor-rag memory show qualsiasi-chiave ; echo "exit=$?"   # error: memory is disabled… ; exit=1
```
