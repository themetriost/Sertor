# Research — LLM Wiki end-to-end (FEAT-010)

Decisioni di design (rationale + alternative). Riferimento: requisito `llm-wiki` (D-1..D-17).

## R1 — `GitPort` nel dominio, adapter subprocess fuori
- **Decisione**: porta `GitPort` (Protocol) in `domain/ports.py`; `SubprocessGitAdapter` in
  `adapters/git/`. Il dominio (wiki) ottiene il **changeset** del commit via porta, senza importare git.
- **Rationale**: Principio I + testabilità (FakeGit). **Alternative**: subprocess nel dominio → viola I.

## R2 — Generazione = servizio distinto, invocato dal versioning (SRP)
- **Decisione**: la generazione vive in `wiki/generation.py`; il **configuration-manager** (o equivalente
  del client) la **invoca al commit**. Il config-manager NON contiene logica di generazione.
- **Rationale**: Principio VII (SRP) + portabilità (binding client-agnostico, D-8). **Alternative**:
  generazione dentro il config-manager → agente tuttofare. Scartata.

## R3 — Due momenti: generazione (scrive) / retrieval (collezioni separate)
- **Decisione**: (a) generazione produce pagine; (b) indicizzazione mette il **wiki generato** in una
  collezione **separata** dal codice, interrogate insieme; gli **input** (`manual_edited/`,
  `ingested_sources/`) **non** sono indicizzati. Ogni collezione si rigenera in modo indipendente.
- **Rationale**: D-3/D-7; risolve il rebuild distruttivo (collezioni a sé). **Alternative**: collezione
  unica con rebuild → cancella il codice (problema reale trovato). Scartata.

## R4 — Mappa entità→pagine derivata
- **Decisione**: derivata a ogni run da frontmatter `sources:` + wikilink; nessun indice persistito.
  Seleziona le pagine collegate al changeset per l'incrementale.
- **Rationale**: REQ-090-like, Principio III (no stato duplicato). **Alternative**: indice persistito →
  drift. Scartata.

## R5 — `manual_edited/` immutabile+compilato; `ingested_sources/` input non versionato
- **Decisione**: `manual_edited/` = input umano versionato, l'LLM non lo modifica ma ne **compila** pagine
  derivate; `ingested_sources/` (ex `sources/`) = input esterno **non versionato**, popolato
  dall'**ingest** (import, non compile) a trigger manuale.
- **Rationale**: D-1/D-6/D-11. **Alternative**: mantenere `sources/` come output di riassunti → contraddice
  il modello a due classi. Scartata (override di FEAT-003 REQ-020).

## R6 — Verità stratificata + gerarchia
- **Decisione**: codice/test = autorità sul comportamento; doc/spec/`manual_edited` = autorità sul perché.
  Gerarchia di default + **configurabile**; conflitti su `manual_edited` = **human-in-the-loop**.
- **Rationale**: D-4. **Alternative**: source-of-truth unica → semplicistica. Scartata.

## R7 — Manutenzione: lint strutturale (LLM-free) + freschezza (LLM)
- **Decisione**: lint strutturale (link rotti, orfani, copertura/cross-ref) LLM-free; **verifica di
  freschezza** via LLM (obsolescenza vs codice/test o vs decisione). Trigger
  incrementale@commit / on-demand / periodico.
- **Rationale**: D-14/FR-017. **Alternative**: solo strutturale → non cattura l'obsolescenza semantica.

## R8 — Gate al commit fuori dal dominio
- **Decisione**: il core produce **report**; il **gate** (`services/wiki_gate.py`) blocca/avvisa/propone
  soluzioni + **override tracciato**, al confine (CLI/hook). Trigger contract **portabile**;
  config-manager = binding.
- **Rationale**: D-17/Principio I. **Alternative**: gate nel dominio → accoppia core e processo. Scartata.

## R9 — Setup `sertor wiki init`
- **Decisione**: comando di setup che crea la struttura, **installa il binding del trigger** e fa un
  ingest iniziale opzionale. Una volta per repo.
- **Rationale**: D-16; senza binding il trigger si perde (R-03). **Alternative**: setup solo struttura →
  generazione non scatta. Scartata.

## R10 — Re-index incrementale = dipendenza FEAT-009
- **Decisione**: il re-index incrementale del corpus codice è abilitato da **FEAT-009**; finché assente,
  **fallback** (lettura working-tree / rigenerazione più ampia) **segnalato**.
- **Rationale**: D-5/dipendenze. **Alternative**: bloccare la feature → rinvia valore realizzabile.

## R11 — Config centralizzata (Settings)
- **Decisione**: `Settings` espone insieme **fonti-input** configurabile, **soglia gate**, **gerarchia di
  autorità**, path delle aree, nomi delle collezioni separate.
- **Rationale**: Principio VIII; FR-009/FR-014.
