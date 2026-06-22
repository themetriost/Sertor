# Feature Specification: Distribuzione della memoria via installer (FEAT-009)

**Feature Branch**: `071-distribuzione-memoria-installer` · **Created**: 2026-06-22 · **Status**: Implemented (in attesa di merge)

<!-- Deriva da: FEAT-009 (epica memoria-conversazioni) — requirements/memoria-conversazioni/distribuzione-installer/requirements.md -->

**Input**: FEAT-009 dell'epica `memoria-conversazioni` (Must, **debito di completamento**). L'MVP della
memoria conversazioni (cattura FEAT-001, ricerca episodica FEAT-002, CLI+hook feature 035, distillazione
FEAT-003) è **completo e acceso solo sul dogfood di Sertor**: vive nel `.env` di sviluppo e nel `.claude/`
del repo, **non** negli asset dell'installer. Un ospite che fa `sertor install rag` **non riceve la
memoria**. Questa feature la rende **installabile su un ospite**, chiudendo il corollario «una feature è
completa solo se installabile» (CLAUDE.md, Principio X). Recupera il rinvio **A-009 di FEAT-035**.

---

> **Allineamento alla missione (gate Constitution).** La memoria episodica serve la **freschezza/qualità
> del contesto reso all'agente** nel tempo (ricordare cosa è già stato deciso/discusso). Distribuirla agli
> ospiti **estende la capacità oltre il dogfood**: è la stessa missione (auto-conoscenza interrogabile e
> **portabile**, senza lock-in). Non è un concern periferico — è il completamento di una capacità di
> prodotto già costruita ma non ancora consegnabile.

> **Natura del cambiamento: ADDITIVO.** Nessuna modifica a `sertor-core` (porte/servizi/CLI memoria già
> esistono). Le modifiche vivono nei **pacchetti installer** (`sertor` / `sertor-install-kit`) e negli
> **asset**: manopole nei template `.env`, hook + wiring `SessionEnd`, cenno nelle istruzioni host-facing.
> La memoria **cavalca `sertor install rag`** (stesso runtime `.sertor/`, CLI `sertor-rag`, `.env`).

> **Ancoraggio all'esistente (dato di partenza, non da progettare).**
> - Le **8 manopole memoria** esistono in `src/sertor_core/config/settings.py` (`SERTOR_MEMORY`,
>   `SERTOR_MEMORY_ADAPTER`, `SERTOR_MEMORY_RETENTION_DAYS`, `SERTOR_MEMORY_SCRUB_PATTERNS`,
>   `SERTOR_EPISODIC_LIMIT`, `SERTOR_EPISODIC_SNIPPET_TOKENS`, `SERTOR_MEMORY_LIST_LIMIT`,
>   `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`); i template `.env` dell'installer
>   (`packages/sertor/src/sertor_installer/assets/rag/env.{local,azure}.tmpl`) **non** le contengono.
> - L'hook di cattura `.claude/hooks/memory-capture.ps1` e la voce `SessionEnd` vivono **solo** nel
>   `.claude/` di Sertor (`.claude/settings.json`), non negli asset.
> - Il **pattern gemello da rispecchiare** è l'hook rag-usage in
>   `packages/sertor/src/sertor_installer/install_rag.py` (feature 042/044/011): `ArtifactKind.FILE`
>   (CREATE_IF_ABSENT, byte-copy) + `ArtifactKind.SETTINGS_MERGE` (MERGE_DEDUP, preserva gli hook utente),
>   routing per-assistente via `AssistantProfile`, lifecycle inverso (upgrade/uninstall) e
>   `sertor_owned_paths`. I riferimenti a file ancorano i requisiti, non prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Un ospite installa la memoria con le sue manopole (P1, Must)
Un maintainer esegue `sertor install rag` su un progetto pulito. Il `.sertor/.env` generato contiene
**tutte** le manopole memoria, commentate e con `SERTOR_MEMORY` **disattivata** (privacy-by-default), così
il maintainer può accendere e regolare la memoria senza scoprire le manopole leggendo il codice.

**Independent Test**: dopo `sertor install rag` su un host temporaneo, il `.sertor/.env` generato contiene
le 8 chiavi memoria; `SERTOR_MEMORY` è off/commentata; ogni chiave ha un commento d'uso.

**Acceptance**:
1. **Given** un host pulito, **When** eseguo `sertor install rag` (backend local **o** azure), **Then** il
   `.sertor/.env` contiene tutte le manopole memoria di `Settings`, con `SERTOR_MEMORY` off di default.
2. **Given** un `.sertor/.env` già esistente con valori dell'utente, **When** ri-eseguo l'installazione,
   **Then** le sole chiavi memoria mancanti sono aggiunte; nessun valore esistente è sovrascritto.

### User Story 2 — La cattura è installata e cablata, senza rompere hook esistenti (P1, Must)
L'installazione deposita lo script di cattura sull'host e cabla una voce `SessionEnd` nella configurazione
hook dell'assistente scelto, **additivamente** (gli hook preesistenti dell'utente restano).

**Independent Test**: dopo l'installazione, lo script di cattura esiste nel container dell'assistente e la
config hook contiene la voce `SessionEnd` di cattura accanto a eventuali hook preesistenti.

**Acceptance**:
1. **Given** un host pulito, **When** installo, **Then** lo script di cattura è depositato e una voce
   `SessionEnd` che lo invoca è cablata nella config dell'assistente.
2. **Given** una config hook con voci preesistenti, **When** installo, **Then** la voce di cattura è
   aggiunta in modo additivo (dedup), senza rimuovere né duplicare le esistenti.
3. **Given** l'assistente **Copilot CLI**, **When** installo, **Then** lo script e il wiring sono
   depositati nei container nativi Copilot (`.github/**`, formato nativo), rispecchiando il routing
   dell'hook rag-usage.

### User Story 3 — L'agente sa che la memoria esiste (P1, Must)
Dopo l'installazione, le istruzioni host-facing dell'assistente menzionano i comandi `sertor-rag memory`
(search/list/show/archive) e la condizione d'uso (memoria accesa), così l'agente ospite **sa** di poterli
usare nei «casi speciali».

**Independent Test**: dopo l'installazione, la superficie istruzioni dell'assistente contiene un cenno ai
comandi `sertor-rag memory` con la nota che richiedono `SERTOR_MEMORY` acceso.

**Acceptance**:
1. **Given** un host pulito, **When** installo, **Then** la superficie istruzioni menziona i comandi
   `sertor-rag memory` e la condizione `SERTOR_MEMORY` attivo.

### User Story 4 — Privacy preservata end-to-end (P1, Must)
Su un host appena installato e **non** opt-in, **nessun** contenuto è persistito e l'hook di cattura è un
**no-op silenzioso** (exit 0): la privacy-by-default sopravvive alla distribuzione.

**Independent Test**: su un host installato senza accendere `SERTOR_MEMORY`, l'hook depositato esce 0 senza
output e nessun file di archivio viene creato.

**Acceptance**:
1. **Given** un host installato con `SERTOR_MEMORY` non attivo, **When** l'evento `SessionEnd` scatta,
   **Then** l'hook è no-op ed esce con successo, nessun contenuto persistito.
2. **Given** gli artefatti depositati, **When** li ispeziono, **Then** non contengono contenuti di
   conversazione né segreti (solo nomi di chiave + commenti).

### User Story 5 — Ciclo di vita completo (P1, Must)
Gli artefatti memoria sono coperti da `sertor upgrade` (riallineamento idempotente) e `sertor uninstall`
(rimozione pulita), incluse la voce `SessionEnd` e lo script; il test invariante `plan ⊆
sertor_owned_paths` resta verde.

**Independent Test**: `sertor uninstall` rimuove script + voce `SessionEnd` di cattura preservando gli hook
utente; `sertor upgrade` riallinea senza duplicare; `plan ⊆ owned` verde.

**Acceptance**:
1. **Given** un host con la memoria installata, **When** eseguo `sertor uninstall`, **Then** lo script e la
   voce `SessionEnd` di cattura sono rimossi; gli hook utente preesistenti restano.
2. **Given** un host con la memoria installata, **When** eseguo `sertor upgrade`, **Then** lo script e il
   wiring sono riallineati idempotentemente (nessun duplicato, nessun overwrite di valori `.env`).
3. **Given** il piano rag esteso, **When** eseguo il test di copertura, **Then** i `target_rel` del piano
   sono un sottoinsieme di `sertor_owned_paths` (manifest-replacement, FR coverage).

## Edge Cases
- **Backend azure vs local**: le manopole memoria viaggiano in **entrambi** i template (`.env`).
- **Copilot CLI**: lo script + wiring sono depositati ma la cattura è **inerte** finché FEAT-008 non porta
  un adapter che legga i transcript di quell'assistente (l'unico adapter oggi è `claude-code`) — gap
  dichiarato, non parità non-verificata.
- **Hook `SessionEnd` utente preesistente**: merge dedup additivo, mai perdita.
- **Re-install / upgrade**: idempotente; nessun valore `.env` dell'host sovrascritto.
- **Uninstall del file di settings dedicato Copilot**: cancella il file `sertor-hooks.json` se resta vuoto
  dopo la rimozione; il `.claude/settings.json` condiviso è sempre preservato.

## Requirements *(mandatory)*

### Requisiti funzionali
- **FR-001 (manopole `.env`).** L'installer rag include **tutte** le manopole memoria di `Settings` nel
  `.sertor/.env` generato. *(REQ-001)*
- **FR-002 (entrambi i template).** Le manopole memoria sono incluse in `env.local.tmpl` **e**
  `env.azure.tmpl`. *(REQ-002)*
- **FR-003 (privacy-by-default).** Il `.env` generato lascia `SERTOR_MEMORY` **disattivata** (off/
  commentata): nessun contenuto persistito senza opt-in. *(REQ-003)*
- **FR-004 (commenti d'uso).** Ogni manopola nel template ha un commento breve (scopo, default, opt-in).
  *(REQ-004)*
- **FR-005 (merge additivo `.env`).** Su `.env` esistente, solo le chiavi memoria mancanti sono aggiunte;
  nessun valore dell'host sovrascritto. *(REQ-005)*
- **FR-010 (deposito script).** L'installer deposita lo script di cattura come asset dell'installer
  (non più solo in `.claude/` di Sertor). *(REQ-010)*
- **FR-011 (create-if-absent).** Se lo script esiste già sull'host, è lasciato invariato. *(REQ-011)*
- **FR-012 (wiring `SessionEnd`).** L'installer cabla una voce `SessionEnd` che invoca lo script nella
  config hook dell'assistente. *(REQ-012)*
- **FR-013 (merge dedup).** Il wiring è additivo e dedup: gli hook preesistenti non sono rimossi né
  duplicati. *(REQ-013)*
- **FR-014 (routing Copilot).** Su Copilot CLI, script + wiring sono depositati nei container nativi
  (`.github/**`, formato nativo), rispecchiando il routing dell'hook rag-usage. *(REQ-014)*
- **FR-015 (corpo unico).** Il corpo dello script è riusato **identico** tra assistenti (single source);
  varia solo il contenitore/wiring. *(REQ-015)*
- **FR-020 (consapevolezza agente).** L'installer aggiunge alla superficie istruzioni host-facing un cenno
  ai comandi `sertor-rag memory` (search/list/show/archive). *(REQ-020)*
- **FR-021 (condizione d'uso).** Il cenno chiarisce che i comandi memoria richiedono `SERTOR_MEMORY`
  attivo. *(REQ-021)*
- **FR-030 (no-op se off).** L'hook depositato è no-op silenzioso ed esce con successo quando la memoria è
  disattivata. *(REQ-030)*
- **FR-031 (no segreti/contenuti negli asset).** Nessun contenuto di conversazione né segreto è scritto in
  alcun artefatto (solo nomi di chiave + commenti). *(REQ-031)*
- **FR-032 (gitignore archivio).** L'archivio resta escluso dal VCS (coperto dai runtime-ignores esistenti
  sotto `.sertor/`). *(REQ-032)*
- **FR-040 (uninstall).** `sertor uninstall` rimuove lo script e la voce `SessionEnd` di cattura aggiunti,
  preservando gli hook utente. *(REQ-040)*
- **FR-041 (upgrade).** `sertor upgrade` riallinea script e wiring idempotentemente (no duplicati, no
  overwrite di `.env`). *(REQ-041)*
- **FR-042 (owned paths).** I nuovi artefatti memoria sono dichiarati in `sertor_owned_paths`; copertura e
  obsolete-detection del lifecycle li includono (`plan ⊆ owned`). *(REQ-042)*
- **FR-043 (obsolete cross-assistente).** L'upgrade obsolete-scan rimuove il wiring memoria dell'altro
  assistente (stessa regola dell'hook rag-usage). *(REQ-043)*
- **FR-050 (host-agnostico).** Manopole e archivio operano su qualunque host senza modifiche al corpo; solo
  il trigger di cattura è assistant-specifico. *(REQ-050)*
- **FR-051 (non-regressione).** Le superfici wiki/rag già installabili restano invariate; gli artefatti
  memoria sono additivi al piano rag. *(REQ-051)*

### Requisiti non funzionali
- **RNF-1 (riuso, no nuove dipendenze):** riusa il `sertor-install-kit` e i tipi artefatto esistenti
  (`FILE`/`SETTINGS_MERGE`/`MERGE_ENV`, lifecycle inverso); nessuna nuova dipendenza, nessun nuovo
  `ArtifactKind` se evitabile.
- **RNF-2 (`sertor-core` invariato):** nessuna modifica a `src/sertor_core/`.
- **RNF-3 (additività):** ospiti che non opt-in → costo/comportamento del runtime identici a oggi.
- **RNF-4 (idempotenza & non-distruttività):** re-install/upgrade non duplicano né sovrascrivono; uninstall
  non tocca artefatti non-Sertor.
- **RNF-5 (verificabilità offline):** install/upgrade/uninstall verificabili con i runner mock esistenti,
  senza rete, su host temporanei.
- **RNF-6 (parità schema Copilot):** il wiring Copilot rispetta il formato nativo; la guardia di
  validità-schema offline non regredisce.

### Key Entities
- **Manopole memoria nel template `.env`** — le 8 chiavi di `Settings`, commentate, `SERTOR_MEMORY` off.
- **Asset script di cattura** — lo script `memory-capture.ps1` promosso da `.claude/` di Sertor ad asset
  dell'installer, byte-copiato sull'host.
- **Frammento di wiring `SessionEnd`** — la voce hook (Claude: `.claude/settings.json`; Copilot: nativo
  `.github/hooks/…`) che invoca lo script; mergeata dedup.
- **Cenno istruzioni memoria** — le righe/blocco host-facing sui comandi `sertor-rag memory`.
- **Owned paths memoria** — i `target_rel` dei nuovi artefatti, dichiarati per il lifecycle.

## Success Criteria *(mandatory)*
- **SC-001:** dopo `sertor install rag`, il `.sertor/.env` contiene le 8 manopole memoria con `SERTOR_MEMORY`
  off. *(FR-001/002/003/004)*
- **SC-002:** lo script di cattura e la voce `SessionEnd` sono depositati e cablati additivamente (Claude e
  Copilot). *(FR-010/012/013/014)*
- **SC-003:** la superficie istruzioni menziona i comandi `sertor-rag memory` e la condizione d'uso.
  *(FR-020/021)*
- **SC-004:** su host non opt-in, l'hook è no-op exit 0 e nessun contenuto è persistito; nessun segreto
  negli asset. *(FR-030/031)*
- **SC-005:** `uninstall` rimuove script + voce; `upgrade` riallinea idempotente; `plan ⊆ owned` verde.
  *(FR-040/041/042/043)*
- **SC-006:** non-regressione wiki/rag; `sertor-core` invariato; suite verde, lint pulito. *(FR-051/RNF-2/5)*
- **SC-007:** le manopole viaggiano in entrambi i template `.env`. *(FR-002)*

## Assumptions
- **La memoria cavalca `sertor install rag`** (decisione utente): nessun comando `sertor install memory`.
- **gitignore già coperto:** `memory.sqlite` vive sotto `<index_dir>` dentro `.sertor/` → già escluso dai
  `RUNTIME_IGNORES`; nessuna nuova voce `.gitignore`.
- **Adapter unico oggi = `claude-code`:** su Copilot il wiring depositato è **inerte** finché FEAT-008.
- **`sertor-core` invariato:** porte/servizi/CLI memoria già esistono; questa feature distribuisce.

### Fuori ambito (dichiarato)
- **Adapter di cattura per altri assistenti** (Copilot/Codex/…): **FEAT-008** (Could).
- **Comando `sertor install memory` separato:** scartato.
- **Enforcement della retention** (`SERTOR_MEMORY_RETENTION_DAYS` resta hook non applicato): **FEAT-006**.
- **Distribuzione della ricerca semantica** sull'archivio: dipende da **FEAT-004**.
- **Il *come* di dettaglio** (forma del cenno istruzioni, parametro `-Assistant` sullo script, riuso vs
  nuovo `ArtifactKind`, schema serializzazione): fase di **design/plan**.

> **Tracciamento dello scope.** FEAT-008/006/004 sono già nel backlog d'epica
> (`requirements/memoria-conversazioni/epic.md`): nessun rinvio reale vive solo dentro `specs/`.

### Forche di design (per `/speckit-plan`)
- **DA-a — Forma del cenno istruzioni:** blocco a marker dedicato (`SERTOR:MEMORY-USAGE`) vs poche righe
  nel blocco `SERTOR:RAG-USAGE` esistente. *Design.*
- **DA-b — Parametro `-Assistant` sullo script di cattura** per il `SessionEnd` Copilot vs corpo unico
  invariato. *Design.*
- **DA-c — Riuso `FILE`/`SETTINGS_MERGE` vs nuovo `ArtifactKind`** (RNF-1: riusare). *Design.*
