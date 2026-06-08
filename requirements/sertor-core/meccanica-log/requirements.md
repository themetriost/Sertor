# Requisiti — Meccanica del log del wiki

<!-- Deriva da: roadmap "1a" (write-back in CLI + riconciliazione formato) in
wiki/syntheses/architettura-wiki-llm.md; famiglia FEAT-003 (wiki LLM), estende FEAT-003-D. -->

## 1. Contesto e problema (perché)

Il log del wiki (`wiki/log.md`) è oggi un **unico file append-only** che cresce indefinitamente (~680 righe)
e le cui voci sono scritte **interamente a mano dall'LLM**. Il nucleo deterministico `wiki_tools`
(FEAT-003-D) espone già una funzione `append_log(profile, op, title)`, ma:

- **scrive solo la riga di heading** (`profile.log_format` → `## [data] op | titolo`), non il corpo curato
  (lead + bullet + riga d'esito) codificato in `.claude/skills/wiki-author/log-craft.md`;
- **non è esposta dalla CLI** `sertor-wiki-tools` → nella pratica l'LLM scrive *tutta* la voce a mano;
- presuppone un **file unico** (`profile.log_path`): non c'è partizionamento.

Inoltre `scan` (rilevazione lavoro pendente, consumato dall'hook `wiki-pending-check.ps1`) usa come **àncora
temporale il `mtime` del file di log unico**: un partizionamento del log deve preservare questa rilevazione.

Servono due cose, che condividono gli stessi file (`registry.py`, `scan.py`, `profile.py`): **(A)** un
write-back del log esposto in CLI che pizzichi il posto giusto e **preservi il formato curato**; **(B)** la
**rotazione a un file per giorno** per fermare la crescita illimitata e tenere il log navigabile.

## 2. Obiettivi e criteri di successo

- **CS-1 (rotazione):** ogni nuova voce di log finisce in un file della **data di calendario** della voce
  (un file per giorno); nessuna voce nuova finisce in un file monolitico crescente.
- **CS-2 (formato preservato):** una voce scritta via la meccanica deterministica è **byte-identica** a una
  scritta a mano secondo `log-craft` (heading + lead + bullet + riga d'esito): il deterministico **non
  appiattisce** il corpo curato.
- **CS-3 (rilevazione intatta):** dopo la rotazione, `scan` riporta lo **stesso conteggio di lavoro
  pendente** che riporterebbe col log monolitico (parità con SC-003 di FEAT-003-D); l'hook continua a
  funzionare senza modifiche al suo contratto.
- **CS-4 (host-agnostico):** percorso/naming dei file giornalieri e tutto il comportamento derivano da
  `wiki.config.toml`; **nessun path hard-coded** (Principio X).
- **CS-5 (idempotenza):** ri-appendere una voce identica non produce duplicati né modifica file (SC-002 di
  FEAT-003-D).
- **CS-6 (offline/stdlib):** tutte le operazioni girano offline, solo stdlib, senza rete (SC-005).

## 3. Stakeholder e attori

- **Flusso principale (LLM/Opus)** — autore del *contenuto* curato della voce; invoca la meccanica per il
  *piazzamento*.
- **Agente `wiki-curator` (Haiku)** — consumatore della stessa CLI nel record delegato.
- **Hook `wiki-pending-check.ps1`** — thin wrapper su `scan`; non deve rompersi.
- **Ospiti diversi da Sertor** — qualunque progetto col proprio `wiki.config.toml`.

## 4. Ambito

### In ambito
- Estensione del write-back del **log** (`append_log`) per accettare il **corpo curato** e scriverlo nel file
  della data corretta.
- **Esposizione in CLI** dell'operazione di append-log con **contratto JSON versionato**.
- **Rotazione a un file per giorno** (partizione implicita per data) + creazione idempotente del file-giorno
  con header valido.
- Adeguamento di **`scan`** perché l'àncora di lavoro pendente consideri la **partizione più recente**.
- Estensione di **`WikiProfile`/`wiki.config.toml`** con la configurazione della directory di log e del
  naming giornaliero, con **back-compat** verso il file unico.
- **Indice/navigabilità** delle partizioni giornaliere.
- **Migrazione una-tantum**: split retroattivo dello storico `log.md` in file giornalieri (DA-3).

### Fuori ambito
- Il **giudizio sul contenuto** della voce (cosa scrivere): resta LLM, regolato da `log-craft` (invariato).
- Il write-back dell'**indice** (`upsert_index`) e la sua riconciliazione di formato: **feature correlata ma
  separata** (è "1a" lato indice, non lato log).
- La rotazione di **altri file** del wiki (solo il log).
- Modifiche al **formato curato** definito in `log-craft`.

## 5. Requisiti funzionali (EARS)

### Rotazione (partizione per giorno)

- **REQ-001** — *When* una voce di log viene scritta tramite la meccanica deterministica, *the* sistema
  *shall* indirizzarla al file di partizione corrispondente alla **data della voce** (un file per giorno).
- **REQ-002** — *If* il file di partizione della data target non esiste, *then the* sistema *shall* crearlo
  con un header/frontmatter valido prima di appendere (creazione idempotente), **senza** sollevare errore.
- **REQ-003** — *The* sistema *shall* derivare la **directory di log** e il **pattern di naming giornaliero**
  (formato data ISO `YYYY-MM-DD`) dalla configurazione (`wiki.config.toml`), senza path hard-coded.
- **REQ-004** — *Where* la configurazione indica la **modalità a file unico** (back-compat), *the* sistema
  *shall* continuare a operare su `log_path` come oggi (rotazione disattivata).
- **REQ-005** — *The* sistema *shall* mantenere un **indice navigabile delle partizioni** (elenco dei giorni)
  aggiornato in modo idempotente quando una nuova partizione viene creata.

### Write-back `append_log` curato in CLI

- **REQ-010** — *The* sistema *shall* esporre l'operazione di append-log via la **CLI** `sertor-wiki-tools`,
  con un **contratto JSON versionato** (es. `wiki.append_log/1`) coerente con le altre operazioni.
- **REQ-011** — *The* operazione di append-log *shall* accettare il **corpo curato** della voce (heading +
  lead + bullet + riga d'esito, formato `log-craft`) e scriverlo **senza appiattirlo** né riformattarlo.
- **REQ-012** — *When* append-log riceve una voce **identica** a una già presente nella partizione target,
  *the* sistema *shall* non scrivere nulla (idempotente, nessun duplicato).
- **REQ-013** — *The* operazione di append-log *shall* riportare nel contratto **se ha scritto**, **quale
  partizione** ha toccato ed eventuale creazione del file.

### Coupling con `scan` (rilevazione lavoro pendente)

- **REQ-020** — *The* operazione `scan` *shall* determinare l'**àncora** del lavoro pendente dalla
  **partizione di log più recente** (la più recente per data/`mtime` tra i file giornalieri), non da un file
  unico.
- **REQ-021** — *If* non esiste alcuna partizione di log, *then the* sistema *shall* considerare **tutto**
  come pendente (parità col comportamento attuale a registro assente).
- **REQ-022** — *The* contratto di `scan` (`wiki.scan/1`) e il comportamento osservato dall'hook
  *shall* restare **invariati** (nessuna modifica richiesta all'hook `wiki-pending-check.ps1`).

### Migrazione dello storico (una-tantum)

- **REQ-030** — *The* sistema *shall* fornire un'operazione (`migrate`, una-tantum, non distruttiva) che
  **splitta retroattivamente** il `log.md` monolitico esistente in file giornalieri — **una partizione per
  data distinta** — preservando **ordine e contenuto** delle voci. *(Decisione DA-3: split, non archivio.)*
- **REQ-031** — *When* più voci condividono la stessa data nel log storico, *the* sistema *shall* collocarle
  **tutte** nella stessa partizione giornaliera, nell'ordine originale.
- **REQ-032** — *If* la migrazione viene rieseguita, *then the* sistema *shall* essere **idempotente** (non
  duplica partizioni né voci già migrate).

## 6. Requisiti non funzionali

- **NFR-1 (host-agnostico):** ogni specificità da `wiki.config.toml`; stesso codice su ospiti diversi.
- **NFR-2 (stdlib/offline):** solo stdlib (`pathlib`, `datetime`, `re`, `json`…); nessuna rete; nessuna nuova
  dipendenza di terze parti.
- **NFR-3 (idempotenza & non-distruttività):** creazioni e append idempotenti; nessuna operazione cancella o
  riscrive contenuto esistente del log.
- **NFR-4 (errori espliciti):** config assente/malformata → `ConfigError` azionabile; nessuno stato parziale.
- **NFR-5 (contratti versionati):** ogni operazione CLI espone un contratto JSON con `schema` versionato.
- **NFR-6 (performance):** `scan` su N partizioni giornaliere resta veloce (ordine: trovare la partizione più
  recente senza leggere tutti i file integralmente).
- **NFR-7 (Costituzione):** Constitution Check 10/10, inclusi i NON-NEGOZIABILI I/IV/X.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo:** estende `src/sertor_core/wiki_tools/` (FEAT-003-D), riusandone `profile`/`contracts`/`registry`/
  `scan`; non rompe i contratti esistenti.
- **Vincolo:** il **confine deterministico↔giudizio** resta netto — il deterministico fa il *piazzamento*,
  l'LLM fornisce il *contenuto* (log-craft).
- **Assunzione:** la decisione di rotazione è **un file per giorno** (presa dall'utente).
- **Assunzione:** la data della voce è la data di calendario corrente salvo override esplicito (`on_date`).
- **Dipendenza:** `log-craft` (formato curato) e l'hook `wiki-pending-check.ps1` (consumatore di `scan`).

## 8. Rischi

| Rischio | Prob | Impatto | Mitigazione |
|---|---|---|---|
| `scan` cambia conteggio col partizionamento → hook rumoroso o cieco | Media | Alto | REQ-020/022 + test di parità (CS-3) col comportamento monolitico |
| Idempotenza fragile su voci multi-riga (heading+corpo) | Media | Medio | Definire l'identità della voce (es. heading univoco per `data+op+titolo`) in design |
| Deriva del formato (il deterministico appiattisce il corpo) | Bassa | Alto | REQ-011 + CS-2 byte-identico |
| Storico monolitico ingombrante o link rotti dopo migrazione | Media | Medio | REQ-030 non distruttivo; default "archivio" (DA-3) |
| Frammentazione: troppi file piccoli | Bassa | Basso | un file per giorno è grana grossa; indice li tiene navigabili (REQ-005) |

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-003, REQ-010, REQ-011, REQ-012, REQ-020, REQ-021, REQ-022.
- **Should:** REQ-005 (indice partizioni), REQ-013, REQ-004 (back-compat file unico), REQ-030/031/032
  (split retroattivo dello storico — DA-3).
- **Won't (ora):** write-back/riconciliazione dell'**indice** (`upsert_index`); rotazione di altri file.

## 10. Decisioni (chiuse 2026-06-08)

- **DA-1 ✅ Rotazione implicita.** Nessuna operazione `rotate` ricorrente: `append-log` pizzica sempre la
  partizione della data; l'unica operazione una-tantum è `migrate` (vedi DA-3).
- **DA-2 ✅ `append_log` accetta il corpo curato.** La firma si estende per ricevere l'intera voce formattata
  (heading + lead + bullet + esito, `log-craft`); l'LLM compone, il deterministico **piazza** senza
  appiattire.
- **DA-3 ✅ Split retroattivo dello storico.** Il `log.md` monolitico **si splitta** in file giornalieri
  (REQ-030/031/032), non resta come archivio. Non distruttivo e idempotente.
- **DA-4 ✅ Indice nella directory di log.** Un indice dedicato dentro `log/` (es. `log/index.md`), non una
  sezione dell'`index.md` globale.
- **DA-5 ✅ Identità voce = heading.** L'idempotenza si valuta sull'heading (`data+op+titolo`): una sola voce
  per `data+op+titolo`.

*(Nessuna domanda aperta residua: pronti per `speckit-specify`.)*

---

**Commit proposto:** `docs(requirements): requisiti feature "meccanica del log del wiki" (append_log curato in CLI + rotazione giornaliera)`
