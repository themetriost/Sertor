---
title: "Bug utente — `memory archive` non cattura nulla (e tace) se il path del progetto contiene uno spazio"
type: source
tags: [usersfeedback, memory, capture-adapter, claude-code, windows, fail-loud, bug]
created: 2026-07-09
updated: 2026-07-09
source: utente vault "Nunzio Summaries" (segnalazione, 2026-07-09)
status: da elaborare
---

# Bug: `memory archive` archivia 0 sessioni sui progetti con uno spazio nel percorso

> **Fonte:** segnalazione dal vault *Nunzio Summaries*, 2026-07-09, emersa subito dopo aver abilitato
> `SERTOR_MEMORY=true`. Il bug è stato **isolato leggendo il sorgente installato** in `.sertor/.venv`;
> nessuna modifica è stata applicata a `sertor_core`, nessun aggiramento è stato messo in opera.
> L'analisi e le proposte di fix sono in fondo, chiaramente separate dai fatti osservati.

## Sintomo

Con `SERTOR_MEMORY=true` in `.sertor/.env`, su un progetto il cui percorso contiene uno spazio:

```
$ uv run --project .sertor sertor-rag memory archive
op=memory_capture_source_absent adapter_kind=claude-code source=C:\Users\domen\.claude\projects\C--Workspace-Git-Nunzio-Tools-Nunzio Summaries
archived=0 skipped=0 errors=0
```

`memory list` e `memory search` restituiscono sempre vuoto. **Exit code 0, `errors=0`, nessun warning.**
Nella cartella reale del progetto esistono 4 transcript `.jsonl` mai archiviati.

## Causa

`sertor_core/adapters/capture/claude_code.py`:

```python
def encode_project_path(project_path: str) -> str:
    """Encode an absolute project path the way Claude Code names its project folder. ..."""
    return project_path.replace(":", "-").replace("\\", "-").replace("/", "-")
```

Sostituisce `:`, `\` e `/`, ma **non lo spazio**. Claude Code, invece, converte in `-` anche gli spazi
quando genera il nome della cartella in `~/.claude/projects`.

| | valore |
|---|---|
| Percorso progetto | `C:\Workspace\Git\Nunzio-Tools\Nunzio Summaries` |
| Cartella reale creata da Claude Code | `C--Workspace-Git-Nunzio-Tools-Nunzio-Summaries` |
| Cartella calcolata da `encode_project_path` | `C--Workspace-Git-Nunzio-Tools-Nunzio Summaries` |

La cartella cercata non esiste, l'adapter la considera assente e archivia zero sessioni.

Il consumo del valore è in `composition.py:424`:
`project_source_dir = settings.claude_projects_dir / encode_project_path(project_id)`.

## Impatto misurato (non stimato)

Incrociati i 13 progetti presenti in `~/.claude/projects` con i percorsi reali su disco della macchina.
**Tre progetti su tredici sono affetti**, ed è esattamente l'insieme di quelli con uno spazio nel path:

| Progetto | Percorso reale | Sessioni `.jsonl` irraggiungibili |
|---|---|---|
| Nunzio Summaries | `C:\Workspace\Git\Nunzio-Tools\Nunzio Summaries` | 4 |
| Personal Vault | `C:\Workspace\Git\Obsidian\Personal Vault` | 2 |
| VM-WorkingFolder | `C:\Workspace\Virtual Machines\VM-WorkingFolder` | **22** |

Gli altri 10 non contengono spazi e, secondo la diagnosi, non sono affetti. Fra questi
`C:\Workspace\Git\Sertor`, con **58** sessioni.

### Predizione falsificabile

Se la diagnosi è corretta, abilitando `SERTOR_MEMORY=true` su `C:\Workspace\Git\Sertor` ed eseguendo
`memory archive` si devono archiviare **58 sessioni**. Se ne archiviasse 0, questa analisi sarebbe
sbagliata e andrebbe rifatta.

## Perché è più grave del bug di encoding

Il difetto di stringa è banale da correggere. Il problema serio è il **modo in cui fallisce**.

Un progetto affetto ha la memoria formalmente abilitata e di fatto inerte: `archived=0 errors=0`,
exit code 0. L'utente crede di avere un archivio episodico e non ce l'ha, e se ne accorge solo
molte sessioni dopo, quando una `memory search` torna vuota — a quel punto le sessioni sono passate.

Questo contraddice il principio ***Fail Loud, Fix the Cause*** che Sertor stesso prescrive ai progetti
ospiti nel blocco SDLC che installa: *"Graceful degradation is acceptable only when it reports the
failure."* Una source directory assente per un progetto **con memoria attiva** non è uno stato normale
da riportare come `op=memory_capture_source_absent` a livello informativo: è un'anomalia.

Su Windows i percorsi con spazi sono la norma, non l'eccezione (`Documents`, `My Project`,
`OneDrive - Azienda`, `Virtual Machines`). Il bacino di utenti colpiti non è marginale.

## Proposte di fix

### 1. Allineare l'encoding (necessario)

Verificare sul comportamento reale di Claude Code quali caratteri collassa (almeno spazio e punto),
poi allineare. Una forma possibile:

```python
import re
def encode_project_path(project_path: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", project_path)
```

⚠️ **Attenzione alla regressione.** L'attuale `C--` per la drive letter emerge dal fatto che `:` e `\`
diventano entrambi `-`. Una regex che mappa ogni carattere non alfanumerico preserva quel
comportamento, ma va coperta da test su: drive letter, spazi, punti, trattini già presenti nel nome,
e percorsi UNC.

### 2. Rendere rumoroso il fallimento (più importante del punto 1)

Se `SERTOR_MEMORY=true` e la source directory non esiste, emettere un **finding visibile** (o un exit
code non-zero), non un `archived=0 errors=0` silenzioso. Ad esempio:

> *memoria abilitata, ma nessuna sorgente trovata in `<path>`; il progetto potrebbe non essere mai
> stato aperto con l'adapter configurato, oppure l'encoding del percorso non corrisponde.*

Questo secondo fix è indipendente dal primo, e avrebbe fatto emergere il bug il giorno in cui è nato
invece che settimane dopo. Vale la pena chiedersi se altri `op=..._absent` nel codice abbiano la stessa
forma silenziosa.

## Riproduzione minima

1. Progetto in una cartella con uno spazio nel nome.
2. `SERTOR_MEMORY=true` in `.sertor/.env`.
3. Aprire almeno una sessione con l'assistente (crea il `.jsonl` in `~/.claude/projects`).
4. `uv run --project .sertor sertor-rag memory archive` → `archived=0`, nessun errore.

## Cosa NON è stato verificato

Dichiarato per onestà, così che il team non lo dia per assodato:

- **I punti nel percorso.** Il comportamento è dedotto per analogia, non testato. Test disponibile:
  `C:\Workspace\Git\Dataverse.Skills` esiste ma non è mai stato aperto con Claude Code, quindi non ha
  ancora una cartella in `~/.claude/projects`.
- **Se `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR` offra un aggiramento pulito.** Dalla lettura di
  `composition.py:424` sembra di no, perché l'encoding difettoso viene comunque applicato al segmento
  finale — ma non è stato provato.
- **`memory index-semantic`** non è mai stato eseguito: con l'archivio vuoto non avrebbe avuto senso.
  L'interazione fra il bug e la ricerca semantica resta quindi inesplorata.
- **L'adapter `copilot-cli`.** Non esaminato; potrebbe avere lo stesso difetto nel proprio encoding.

## Contesto

Segnalazione prodotta dal vault *Nunzio Summaries*, il cui ruolo è ricerca e analisi, non
implementazione. Coerentemente: nessun symlink con il nome "giusto" è stato creato per aggirare il
problema (avrebbe mascherato la causa), e `sertor_core` non è stato modificato — la libreria si consuma
attraverso i suoi veicoli, e il fix appartiene a chi la mantiene.
