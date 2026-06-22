---
title: Copilot CLI — gestione sessioni e transcript storage
type: source
tags: [copilot, cli, session, transcript, storage, chronicle, github, feat-008]
created: 2026-06-22
updated: 2026-06-22
sources: ["https://docs.github.com/en/copilot/concepts/agents/copilot-cli/chronicle", "https://docs.github.com/en/copilot/how-tos/copilot-cli/chronicle"]
---

# Copilot CLI — Gestione Sessioni e Transcript Storage

Ricognizione tecnica della **struttura di memorizzazione** delle sessioni in **GitHub Copilot CLI**
(forma a riga di comando). Fonte per il progetto dell'adapter di cattura **FEAT-008** (epica
memoria-conversazioni), che renderà l'archivio episodico operativo anche su Copilot.

## Dove Copilot CLI conserva le sessioni

### Cartella principale
```
~/.copilot/session-state/<session-uuid>/
```

Ogni sessione è una cartella UUID, contenente:

- **`events.jsonl`** — **il transcript**: stream JSONL di eventi (1 evento per riga). Contiene i
  prompt, le risposte dell'agente, le invocazioni tool, i file consultati. È l'equivalente del
  file transcript che Claude Code salva in `~/.claude/projects/`.

- **`session.db`** — SQLite per-sessione: metadati strutturati della sessione (creazione, stato,
  configurazione).

- **`workspace.yaml`** — Metadata del contesto: il **progetto/workspace** associato (la
  **chiave di associazione** tra sessione e progetto, dove Claude Code usa il path-encoded nel
  nome della cartella).

- **`vscode.metadata.json`** — Metadata VS Code: informazioni sull'IDE/editor sorgente:
  - `origin` — identificatore del progetto
  - `created` — timestamp creazione
  - `modified` — timestamp ultima modifica

- **Sottocartelle:** `checkpoints/`, `files/`, `research/` (artefatti, cache, risultati di ricerca).

### Indice globale
```
~/.copilot/session-store.db
```

SQLite globale che indicizza **tutte le sessioni** per ricerca/synchronization.

### Sede legacy
```
~/.copilot/history-session-state/
```

Percorso precedente per sessioni storiche (Copilot migra qui le sessioni vecchie).

## Sincronizzazione con il cloud

**Di default**, Copilot CLI **sincronizza le sessioni sul cloud GitHub** (una rete privata per
l'utente). Il comando `/chronicle` consente di gestire manualmente i dati di sessione
(visualizzare, eliminare, sincronizzare).

> **Implicazione per Sertor:** il RAG locale di Sertor legge il **filesystem locale** sotto
> `~/.copilot/session-state/`, nessun accesso al cloud è richiesto. La sincronizzazione è
> trasparente all'agente.

## Differenze chiave da Claude Code

| Aspetto | Claude Code | Copilot CLI |
|---------|-------------|-------------|
| **Posizione sessioni** | `~/.claude/projects/<path-encoded>/` | `~/.copilot/session-state/<UUID>/` |
| **Associazione progetto** | Encoded nel **nome della cartella** | Metadati interni: `workspace.yaml` / `vscode.metadata.json.origin` |
| **Percorso per un progetto** | Predeterminato: una cartella per path | Dinamico: una UUID per sessione, lookup nel metadato |
| **Transcript** | JSONL file singolo per sessione (`<session-id>.jsonl`) | JSONL stesso ma all'interno della cartella sessione (`events.jsonl`) |
| **Cloud sync** | No nativo (solo locale) | Sì, di default (GitHub cloud, /chronicle per gestione) |

## Implicazioni per FEAT-008 (Adapter Copilot)

1. **Lettura transcript:** il percorso è **fisso e noto** (`events.jsonl` dentro la cartella
   sessione), il formato è JSONL identico a Claude Code → **parser può essere riusato**.

2. **Associazione sessione↔progetto:** richiede leggere `vscode.metadata.json.origin` o
   `workspace.yaml` per capire quale progetto gestisce una sessione. Poiché Copilot non
   espone programmaticamente il mapping, la ricognizione **è manuale** o via enumerazione
   (`session.db` globale).

3. **Enumerazione sessioni:** globale (`~/.copilot/session-store.db`) vs locale
   (`~/.copilot/session-state/`). Per Sertor vale lo stesso approccio di Claude Code:
   **enumerare la cartella locale**, non interrogare il cloud.

4. **Privacy:** il cloud-sync è **opt-in per Copilot**, non disattivabile lato configurazione.
   Sertor **non interagisce** con il cloud, legge il solo file system locale. Privacy-by-design.
