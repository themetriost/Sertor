# Requisiti — Skill: mantenere il wiki vivo (manutenzione)
<!-- Deriva da: FEAT-007 (backlog epica sertor-core) -->
<!-- Stato: elicitato — 2026-06-12; domande D1..D4 RISOLTE con l'utente lo stesso giorno (vedi §10):
     probe di freschezza ELIMINATO (Won't), asset installer → INGLESE canonico -->

---

## Nota di elicitazione

Questo documento è prodotto in modalità **subagent** (nessun botta-e-risposta possibile): le
assunzioni ragionevoli sono documentate; i punti che richiedono una decisione dell'utente sono
marcati `[DA CHIARIRE]` nella sezione §10 e riportati nel report finale.

---

## 0. Gap analysis — dote di FEAT-007 vs stato attuale

La tabella mappa ogni voce della dote dichiarata nel backlog dell'epica (`epic.md`, riga FEAT-007)
a ciò che **esiste già** e a ciò che **resta da costruire** (oggetto dei REQ-NNN).

| Voce della dote | Già coperto | Da cosa | Resta da costruire | Dove (REQ) |
|---|---|---|---|---|
| **Lint semantico (N5) — metodo** | Metodo ripetibile documentato ed esercitato quotidianamente nel rituale di step | `wiki-playbook.md` §5, `lint-semantico-host-agnostico.md`, punto 3 del rituale in `CLAUDE.md` | — | — |
| **N5 — probe deterministici di freschezza** (`wiki_tools`) | — | — | ❌ **ELIMINATO (D1, decisione utente 2026-06-12)**: valore marginale — i `sources` larghi (`src/**`) produrrebbero falsi positivi a ogni step; il lint B nel rituale ha il contesto dello step (sa cosa è cambiato) e batte un diff di timestamp a freddo; non coprirebbe nemmeno le derive nei doc di repo (README/docstring, come le 3 trovate il 2026-06-12). La detection del reconcile si regge sul solo `status: superseded` | — (gruppo A → Won't) |
| **Lint organizzativo/reorg (N9) — metodo** | Metodo documentato ed esercitato (2026-06-06: reorg 16→4 pagine in `syntheses/`) | `wiki-playbook.md`, `lint-organizzativo-e-reorg.md` | — | — |
| **N9 — helper deterministico `move`-con-link** | Assente: lo spostamento è manuale (`Edit`+`Edit`); la nota in `lint-organizzativo-e-reorg.md` lo definisce *nice-to-have* | — | Comando `sertor-wiki-tools move` che sposta un file e riscrive tutti i wikilink/link-relativi che la puntano; dry-run; output JSON `wiki.move/1` | REQ-010..REQ-015 |
| **Operazione `reconcile` (obsolescenze)** | Parziale: filtro `status: superseded` ottenibile via `collect` esistente; la meccanica di presentazione e il workflow su-conferma mancano | `src/sertor_core/wiki_tools/collect.py` (campo `status` non incluso nel meta corrente) | Comando `sertor-wiki-tools reconcile` (detection D: filtra pagine `status: superseded` + candidati-stale dal probe); output lista di candidati con motivazione; la risoluzione (aggiorna/fonde/conserva) è giudizio N su conferma | REQ-020..REQ-027 |
| **Trigger periodico `reconcile`** (FR-038 Could) | Assente | — | Documentato come Could (REQ-028); nessuna automazione unattended in scope | REQ-028 |
| **Tema lingua (a) — seed `structure init` localizzato** | Parziale: `structure.py` genera `_index_seed`/`_log_seed` con testo fisso italiano (`"Indice del wiki. Aggiornato dalle operazioni di registro."`, `"Registro append-only del wiki."`) indipendentemente da `language`; `language` è già in `WikiProfile` ma non usata nei seed | `src/sertor_core/wiki_tools/structure.py` righe 22–29; `src/sertor_core/wiki_tools/profile.py` campo `language` | Seed localizzati per lingua (index e log); il testo per lingua va letto da `[strings]` della config o da risorse per-lingua del pacchetto; nessun hard-code | REQ-030..REQ-034 |
| **Tema lingua (b) — asset installer in italiano fisso** | Il template `wiki.config.toml.tmpl` è correttamente parametrizzato su `language`. Il blocco rituale `claude-md-block.md` è scritto in italiano fisso anche con `language=en` (asset statico non parametrizzato) | `packages/sertor/src/sertor_installer/assets/claude-md-block.md` (italiano fisso); `packages/sertor/src/sertor_installer/assets/wiki.config.toml.tmpl` (OK, parametrizzato) | Parametrizzazione o strategia di localizzazione del blocco rituale e degli altri asset testuali dell'installer; coordinamento con l'epica CLI (chi fa cosa) | REQ-035..REQ-037 |
| **Contratti JSON versionati coerenti** | I contratti esistenti usano schema `wiki.<op>/<ver>` (es. `wiki.lint/1`, `wiki.collect/1`) — sistema consolidato | `src/sertor_core/wiki_tools/contracts.py` | Nuovi contratti `wiki.freshness/1`, `wiki.move/1`, `wiki.reconcile/1` coerenti con il sistema esistente | Trasversale (implicito nei REQ sopra) |
| **Campo `status` in `collect`** | `collect` recupera `type`/`title`/`tags`/`wikilinks` ma **non** `status` dal frontmatter | `src/sertor_core/wiki_tools/collect.py` `_page_meta()` | Esporre `status` nei metadati di `collect` così che `reconcile` (e i consumatori) possano filtrare per `status: superseded`/`stub`/ecc. | REQ-021 |

**Sintesi quantitativa (post-risoluzioni D1..D4):**
- Già coperto al 100% (metodo documentato, giudizio): lint B (N5), lint C/reorg (N9).
- Eliminato con decisione (D1): probe di freschezza.
- Da costruire (tutto deterministico, zero LLM): `move`-con-link, `reconcile` detection
  (su `status: superseded`), seed localizzati (tabella it/en), `collect`+status; più la
  **traduzione one-time degli asset installer in inglese canonico** (D4, coordinamento FEAT-012).

---

## 1. Contesto e problema (perché)

Il sistema wiki è oggi mantenuto **per intero via giudizio**: il rituale di step (punto 3 di
`CLAUDE.md`) esegue il lint semantico (B) e il lint organizzativo (C) come **azioni del flusso
principale**, esercitate su contenuti reali con risultati verificabili (2026-06-06, 2026-06-10).
Questa parte N — indispensabile e non automabilizzabile — funziona.

Il problema è nella **parte D meccanica** che la supporta: mancano tre capacità deterministiche
che oggi richiedono lavoro manuale o sono assenti:

1. **Nessun probe di freschezza automatico.** Non esiste un comando che confronti `updated`
   (frontmatter) con la data di ultima modifica delle sorgenti dichiarate (`sources:` nella
   pagina o i `source_dirs` della config). Il flusso principale rileva le pagine stale per
   ispezione manuale — lento e soggetto a omissioni su wiki grandi.

2. **Nessun helper per lo spostamento sicuro di pagine.** Il reorg (operazione N9) richiede di
   spostare fisicamente i file e riscrivere tutti i wikilink entranti: oggi è manuale, non
   atomico, e non ha dry-run. Su un wiki con centinaia di link è rischioso.

3. **Nessun workflow guidato per le obsolescenze.** Non esiste un comando che presenti la lista
   delle pagine `status: superseded` o candidate-stale e guidi la risoluzione su conferma. Il
   flusso principale deve costruire questa lista ogni volta da `collect` + ispezione manuale.

A questi si aggiunge il **tema lingua**: `structure init` genera seed in italiano fisso
indipendentemente dal campo `language` della config, e il blocco rituale installato dall'installer
è in italiano fisso anche quando il progetto ospite usa `language=en`. Il Principio X esige che
ogni testo visibile all'utente sia driven dalla config, non hard-coded.

Queste capacità mancanti appartengono tutte alla **parte D (meccanica, deterministica, stdlib-only,
zero LLM)** secondo il confine D↔N del sistema wiki. Vanno in `wiki_tools` come nuovi
sottocomandi o estensioni di sottocomandi esistenti, con contratti JSON versionati coerenti con il
sistema già in uso.

---

## 2. Obiettivi e criteri di successo (LSC)

| ID | Criterio (misurabile, senza rete, senza LLM) | Collegamento |
|----|----------------------------------------------|--------------|
| LSC-1 | ❌ rimosso (rev. D1: probe di freschezza eliminato). | — |
| LSC-2 | Dato un file wiki e un insieme di wikilink entranti, `move` sposta il file e riscrive tutti i wikilink; dopo l'operazione `lint` non riporta link rotti aggiuntivi. Con `--dry-run` nessun file è modificato. | REQ-010..015 |
| LSC-3 | `reconcile` elenca tutte e sole le pagine con `status: superseded` e non esegue alcuna modifica autonomamente; la risoluzione richiede sempre conferma esplicita. | REQ-020..027 |
| LSC-4 | `structure init` con `language=en` produce seed in inglese; con `language=it` produce seed in italiano; i testi vivono nella tabella di localizzazione, mai inline nelle operazioni. | REQ-030..034 |
| LSC-5 | Gli asset distribuiti dall'installer sono in inglese canonico e istruiscono l'agente a scrivere il contenuto del wiki nella `language` della config: su un ospite `language=it` le voci di log/pagine prodotte sono in italiano, su `language=en` in inglese. | REQ-035..037 |
| LSC-6 | I nuovi contratti JSON (`wiki.move/1`, `wiki.reconcile/1`) superano la deserializzazione su un consumatore che conosce solo il campo `schema`; campi aggiuntivi futuri non rompono i consumatori esistenti (forward-compatible). | REQ-011, REQ-022 |
| LSC-7 | Tutti i nuovi comandi sono eseguibili senza rete, senza LLM e senza credenziali cloud (deterministico, stdlib-only — invariante già in atto per `wiki_tools`). | Principio V, Principio X |
| LSC-8 | `collect` include il campo `status` (se presente nel frontmatter) nei metadati per pagina; i consumatori che non lo conoscono ricevono comunque un JSON valido (forward-compatible). | REQ-021 |

---

## 3. Stakeholder e attori

| Attore | Ruolo |
|--------|-------|
| **Flusso principale (Claude Code / Opus)** | Beneficiario primario: usa i nuovi comandi D per accelerare il giudizio N (probe-freshness → decide quali pagine rivedere; reconcile list → decide come risolvere; move → sposta sicuro). |
| **Agente `wiki-curator` (Haiku)** | Può chiamare `lint`, `collect`, `probe-freshness` e `reconcile --list`; NON esegue `move` né la risoluzione di `reconcile` (giudizio N). |
| **Epica `sertor-cli` (installer, FEAT-012)** | Consumatore del tema-lingua (b): gli asset testuali dell'installer devono rispettare la `language` richiesta al momento dell'installazione. |
| **Ospite del wiki** | Il progetto su cui si installa il sistema wiki; si aspetta che `structure init` produca seed nella propria lingua. |
| **Owner/maintainer** | Invoca `probe-freshness`, `reconcile`, `move` per la manutenzione periodica del wiki. |

---

## 4. Ambito

### In ambito

1. **`move`-con-link deterministico**: spostamento di una pagina wiki + riscrittura di tutti i
   wikilink (`[[nome-pagina]]`) e link relativi Markdown che la puntano; dry-run; idempotenza;
   output `wiki.move/1`.
2. **`reconcile` detection (parte D)**: filtro su `status: superseded` (frontmatter) — esplicito,
   zero falsi positivi; output `wiki.reconcile/1`; la risoluzione è sempre N (su conferma
   esplicita).
3. **Seed `structure init` localizzati**: index e log seed guidati da `language` della config;
   i testi (≈4 frasi) vivono in una **tabella di localizzazione dedicata** (it/en), separata dal
   corpo delle operazioni (D3 risolta: YAGNI rispetto a file-risorsa, dato il volume).
4. **Campo `status` in `collect`**: inclusione di `status` (se presente) nei metadati per pagina.
5. **Tema lingua lato installer (D4 risolta — coordinamento verso FEAT-012)**: gli asset
   distribuiti (blocco rituale, skill, playbook, agente, comando) migrano a **INGLESE canonico
   unico** (traduzione one-time, nessuna variante per-lingua); la manopola `language` della
   config governa la **lingua del CONTENUTO** che il sistema-wiki scrive sull'ospite (seed,
   pagine, voci di log): gli asset in inglese ISTRUISCONO l'agente a scrivere nella lingua
   configurata.
6. **Contratti JSON versionati** coerenti con il sistema `wiki.<op>/<ver>` esistente.

### Fuori ambito

- **Probe di freschezza** (ex gruppo A, REQ-001..006): **ELIMINATO con decisione utente (D1,
  2026-06-12)** — vedi gap analysis: falsi positivi strutturali sui `sources` larghi, il lint B
  del rituale (col contesto dello step) lo batte, e non coprirebbe i doc di repo. Se mai tornasse
  utile (wiki molto grandi mantenuti fuori dal rituale), si rivaluta.
- **Lint B (semantico)** e **Lint C (organizzativo)**: sono giudizio; restano a skill/playbook/flusso
  principale. Questa feature NON li implementa in codice.
- **Localizzazione degli asset distribuiti** (varianti per-lingua di skill/playbook): scartata
  (D4) — una sola lingua canonica (inglese), niente doppia manutenzione della metodologia viva.
- **Risoluzione automatica delle obsolescenze** (fondere, aggiornare, potare pagine): è sempre N,
  mai automatica e mai cieca. `reconcile` si ferma alla detection (lista) — la risoluzione richiede
  conferma esplicita del flusso principale.
- **Spider/crawling LLM** di contenuto esterno.
- **Trigger automatici unattended** (cron, webhook) per `reconcile` o `probe-freshness` — oltre il
  Could (REQ-028) nessun meccanismo di scheduling in scope.
- **Implementazione dell'installer** (epica CLI / FEAT-012): il coordinamento sul tema-lingua è un
  requisito di interfaccia, non un'implementazione qui.
- **Traduzione automatica** del contenuto delle pagine wiki.
- **Gerarchia di autorità configurabile** (FR-014 di FEAT-003): già classificata Could nell'epica.
- **Refresh incrementale dell'indice RAG**: è FEAT-009.

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Probe di freschezza deterministico → ❌ ELIMINATO (Won't)

> **D1 risolta (2026-06-12, decisione utente): il gruppo A (REQ-001..006) è ELIMINATO.**
> Razionale tracciato: (1) falsi positivi strutturali — i `sources` larghi delle pagine
> (`src/sertor_core/**`, `specs/NNN/**`) verrebbero toccati da ogni feature, segnalando mezza
> wiki a ogni step; (2) il lint B del rituale ha il **contesto dello step** (sa cosa è appena
> cambiato e quali pagine ne dipendono) e batte un diff di timestamp a freddo; lo Stop hook fa
> già un check mtime-like per il lavoro non registrato; (3) il probe non avrebbe coperto le
> derive nei doc di repo (README, docstring — come le 3 trovate e corrette il 2026-06-12),
> che vivono fuori dal frontmatter wiki. La numerazione REQ-001..006 non viene riusata.
> La detection del `reconcile` (Gruppo C) si regge sul solo `status: superseded`: esplicito,
> zero falsi positivi.

---

### Gruppo B — Comando `move`-con-link

**REQ-010 (Event-driven)**
*When the `move` command is invoked with a source page path and a destination path within the
wiki root, the system shall move the page file to the destination and rewrite every wikilink
(`[[page-name]]` and `[[page-name|alias]]`) in every other wiki page that resolves to the
moved page, so that all links remain valid after the move.*

**REQ-011 (Event-driven)**
*When the `move` command completes, the system shall return a result conforming to the
`wiki.move/1` contract, listing: the source path, the destination path, and the list of
rewritten files with the count of link occurrences replaced in each.*

**REQ-012 (Optional feature)**
*Where the `--dry-run` flag is passed, the system shall compute and return the full move plan
(files to move, links to rewrite, counts) without modifying any file on disk.*

**REQ-013 (Unwanted behaviour)**
*If the destination path already exists as a file, then the system shall fail with an explicit
error (no silent overwrite) and leave all files unchanged.*

**REQ-014 (Unwanted behaviour)**
*If the `move` command is interrupted after the file has been moved but before all links have
been rewritten, then the system shall, on the next invocation with the same parameters, detect
the partial state (destination exists, some links still point to source) and complete the
rewrite rather than failing.*

> Nota: l'idempotenza del comando (REQ-014) è il requisito di robustezza. L'implementazione
> può scegliere ordine atomico (rewrite prima, then move) o recovery post-move; la scelta è
> del design, non del requisito.

**REQ-015 (Ubiquitous)**
*The `move` command shall operate without network, LLM, or external service; it shall
resolve wikilinks using the same slug-matching logic as the existing `lint` command
(`src/sertor_core/wiki_tools/lint.py` `_link_targets()`), so that `move` + `lint` form a
consistent pair.*

---

### Gruppo C — `reconcile` detection (parte D)

**REQ-020 (Event-driven)**
*When the `reconcile` command is invoked, the system shall enumerate all wiki pages where
the `status` frontmatter field equals `superseded`, and report them as obsolescence
candidates with their path and, where present, the `updated` date.*

**REQ-021 (Event-driven)**
*When the `collect` command is invoked, the system shall include the value of the `status`
frontmatter field (if present) in the per-page metadata of the `wiki.collect/1` contract,
as an additional forward-compatible field.*

> Ancora: `status` è già in `frontmatter_optional` del template (`wiki.config.toml.tmpl`).
> `collect` oggi non lo espone (vedere `src/sertor_core/wiki_tools/collect.py` `_page_meta()`).

**REQ-022 (Event-driven)**
*When the `reconcile` command completes, the system shall return a result conforming to the
`wiki.reconcile/1` contract, listing for each candidate: path, status field value, the
`updated` date, the declared successor page (where present in the frontmatter or in the
supersession banner), and a `reason` string; the system shall not perform any modification
to any wiki page.*

> Rev. D1: rimosso lo «staleness signal from probe-freshness» (probe eliminato).

**REQ-023 (Ubiquitous)**
*The `reconcile` command shall never delete, overwrite, or modify any wiki page autonomously;
all modification decisions shall require explicit confirmation from the invoking agent or user,
outside the scope of this command.*

> Vincolo assoluto (Principio VI — idempotenza/non-distruttività, Costituzione v1.1.0): la
> detection D è read-only. La risoluzione è esclusivamente N.

**REQ-024** — ❌ RIMOSSO (rev. D1: integrava il probe di freschezza, eliminato; numerazione
non riusata).

**REQ-025 (Unwanted behaviour)**
*If the wiki contains no pages with `status: superseded`, then the `reconcile` command shall
return an empty candidates list and a `clean: true` field, without error.*

**REQ-026 (Ubiquitous)**
*The `reconcile` command shall operate deterministically and offline, requiring no LLM and no
network; it shall be safe to run as a health-check without side effects.*

**REQ-027 (Ubiquitous)**
*The content of a superseded page shall be preserved on disk until the invoking agent or user
explicitly requests its removal or transformation; `reconcile` detection shall never be the
trigger for deletion.*

> Ancora: il playbook §4 (`wiki-playbook.md`) codifica la stessa invariante: «il contenuto resta
> (testimonianza; gli errori cancellati si ripetono)».

---

### Gruppo D — Trigger periodico `reconcile` (Could)

**REQ-028 (Optional feature, Could)**
*Where a periodic-maintenance schedule is configured (e.g., via a config key or an external
scheduler), the system shall support invoking `reconcile` (detection only) on a schedule and
emitting the result to a configured output (file, stdout, or log); no modification shall be
performed automatically.*

> `[DA CHIARIRE D2]` — Il trigger periodico (FR-038) è classificato Could. La forma preferita
> è: (a) una riga nella config `wiki.config.toml` che attiva un hook periodico (chi lo
> chiama?), (b) un wrapper script che invoca `reconcile` e il flusso principale lo pianifica
> nell'ambiente dell'ospite, oppure (c) rinviare del tutto a una futura feature. **Raccomandazione:**
> adottare (b): `reconcile` è già un comando testabile e sicuro; la schedulazione è compito
> dell'ambiente ospite (cron, task scheduler, hook CI); `wiki_tools` non deve assumere un
> ambiente di esecuzione specifico (Principio X). Classificare (a) come fuori scope, (b) come
> documentazione d'uso, (c) come fallback se l'utente preferisce non decidere ora.

---

### Gruppo E — Seed `structure init` localizzati

**REQ-030 (Event-driven)**
*When the `structure init` command is invoked with a wiki profile where `language` is set,
the system shall generate the index seed and the log seed in the language specified by that
field.*

**REQ-031 (Ubiquitous)**
*Seed texts for each supported language shall be defined in a dedicated localisation table
(separate from the operation bodies, e.g. a `locales` module mapping language → strings),
NOT inline in the operation code; adding a language shall require touching only that table.*

> Rev. D3 (2026-06-12): i seed sono ~4 frasi → una tabella di localizzazione in modulo dedicato
> è il taglio YAGNI; file-risorsa per lingua e override `[strings]` in config restano possibili
> evoluzioni se i testi crescono (Could, non richiesti ora).

> Ancora: oggi il testo è hard-coded in `src/sertor_core/wiki_tools/structure.py` righe 22–29
> (`_index_seed` / `_log_seed`). Il campo `language` è già disponibile in `WikiProfile`
> (`src/sertor_core/wiki_tools/profile.py`) ma non viene consultato da `structure.py`.

**REQ-032 (Unwanted behaviour)**
*If the `language` field in the config specifies a language for which no seed text is defined,
then the system shall fall back to the English seed texts and emit a warning naming the
unsupported language, without failing.*

**REQ-033 (Ubiquitous)**
*The `structure init` command shall remain idempotent: if the index or log file already exist,
it shall not overwrite them regardless of language, consistent with the existing
non-destructive behaviour.*

**REQ-034 (Ubiquitous)**
*The list of supported languages for seed generation shall be discoverable without executing
the command (e.g., via a `--list-languages` flag or a manifest file bundled with the package),
so that the installer can validate the `language` value before writing `wiki.config.toml`.*

> D3 risolta (2026-06-12, flusso principale su evidenza): vedi REQ-031 — tabella di
> localizzazione in modulo dedicato, dato il volume reale (~4 frasi).

---

### Gruppo F — Tema lingua: asset installer in INGLESE canonico (coordinamento, rev. D4)

> **D4 risolta (2026-06-12, decisione utente): NESSUNA localizzazione degli asset distribuiti.**
> Gli asset (blocco rituale, skill, playbook, agente, comando) migrano a **inglese canonico
> unico** — una sola lingua da mantenere, niente drift ×2 sulla metodologia viva. La manopola
> `language` governa la **lingua del CONTENUTO** che il sistema-wiki produce sull'ospite (seed,
> pagine, voci di log), non la lingua degli asset. Implicazione dichiarata: il `.claude/` del
> repo Sertor è il DERIVATO degli assets (test di sync) → anche le skill wiki interne
> diventeranno inglesi; il wiki interno resta italiano (`language=it`).

**REQ-035 (Ubiquitous)**
*The text assets distributed by `sertor install wiki` (ritual block, skills, playbook, agent,
command) shall be authored in a single canonical language: English; no per-language asset
variants shall be maintained.*

> Implementazione lato epica CLI (FEAT-012): traduzione one-time degli asset attuali
> (oggi in italiano, es. `packages/sertor/src/sertor_installer/assets/claude-md-block.md`)
> e aggiornamento del test di sync assets↔`.claude/`.

**REQ-036 (Ubiquitous)**
*The distributed assets shall instruct the consuming agent to WRITE all wiki content (pages,
log entries, index updates) in the language specified by the `language` field of
`wiki.config.toml` on the host; the asset language (English) and the content language (host
preference) are independent by design.*

**REQ-037 (Ubiquitous)**
*The source of truth for the content language shall be the `language` field in
`wiki.config.toml` (generated by the installer); both `wiki_tools` (seed, REQ-030..034) and
the agent instructions (REQ-036) shall derive the content language from that single field.*

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| RNF-001 | **Deterministico/offline** | Tutti i comandi di questa feature (`probe-freshness`, `move`, `reconcile`, estensione di `structure`, estensione di `collect`) devono operare senza rete, senza LLM e senza credenziali cloud. Invariante già in atto per `wiki_tools`; nessuna nuova dipendenza esterna. |
| RNF-002 | **Testabilità** | Ogni nuovo comando deve avere test automatici che operano su un wiki temporaneo (tmp directory); nessun test deve richiedere un LLM o un servizio esterno. Coerente con la suite esistente (vedere `tests/unit/test_wiki_tools_*`). |
| RNF-003 | **Host-agnostico (Principio X)** | Nessun nuovo comando deve assumere nomi di cartelle, convenzioni di lingua o strutture di progetto specifiche. Tutto ciò che varia tra ospiti deriva dalla config `wiki.config.toml`. |
| RNF-004 | **Non-distruttività (Principio VI)** | I comandi `probe-freshness`, `reconcile` e `collect` sono **read-only**: non modificano mai file wiki. `move` con `--dry-run` è read-only; senza `--dry-run` modifica solo i file esplicitamente coinvolti nell'operazione richiesta, senza effetti collaterali su altri file. |
| RNF-005 | **Contratti forward-compatible** | I nuovi contratti (`wiki.freshness/1`, `wiki.move/1`, `wiki.reconcile/1`) e le estensioni di contratti esistenti (`wiki.collect/1` con campo `status`) devono essere forward-compatible: un consumatore che conosce solo il campo `schema` non deve ricevere errori di deserializzazione. |
| RNF-006 | **Consistenza con `lint`** | Il comando `move` deve usare la stessa logica di slug-matching di `lint` (`_link_targets()`) per garantire che `move` + `lint` formino un paio consistente: dopo un `move`, `lint` non deve segnalare link rotti sulle pagine riscritte. |
| RNF-007 | **Performance lineare** | I comandi devono scalare linearmente con il numero di file wiki, non con la dimensione del contenuto delle pagine. |
| RNF-008 | **Errori espliciti (Principio IV)** | Condizioni di errore prevedibili (config assente, pagina non trovata, destinazione `move` già occupata, lingua non supportata senza fallback) producono messaggi espliciti su stderr e `wiki.error/1` con `--json`, senza stati parziali silenziosi. |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **Confine D↔N (non negoziabile):** probe, `move`, `reconcile` detection e seed localizzati
  sono meccanico (D). La risoluzione delle obsolescenze, il giudizio su cosa è davvero stale,
  la decisione se spostare una pagina o dove — sono giudizio (N). Questa feature NON deve
  spostare giudizio nel codice.
- **Principio VI — non-distruttività:** `reconcile` è read-only. `move` è distruttivo solo
  sui file esplicitamente indicati; `--dry-run` è sempre disponibile.
- **Invariante stdlib-only:** tutti i nuovi comandi devono usare solo la libreria standard Python
  (o dipendenze già presenti in `sertor-core`); nessun import di SDK esterni nei moduli
  `wiki_tools` (coerente con la filosofia FEAT-003-D).
- **Contratti versionati:** ogni nuovo contratto JSON introduce uno schema `wiki.<op>/1`; la
  versione si incrementa (≥ 2) solo a rottura del contratto esistente, non ad ogni addizione di
  campo.
- **`[strings]` e risorse per-lingua:** i testi visibili all'utente (seed localizzati, messaggi)
  derivano dalla config o da risorse bundled — mai hard-coded nel corpo delle operazioni.
  Il meccanismo esatto è `[DA CHIARIRE D3]`.

### Assunzioni

- Il campo `language` in `wiki.config.toml` è già obbligatorio e validato da `load_profile`
  (`src/sertor_core/wiki_tools/profile.py`); non è necessario aggiungerlo.
- `status` è già tra `frontmatter_optional` nel template dell'installer
  (`wiki.config.toml.tmpl`); tutti i wiki installati via `sertor install wiki` lo dichiarano
  come campo opzionale.
- Il campo `sources` del frontmatter è una lista di stringhe; ciascun elemento può essere un
  percorso relativo alla radice del progetto ospite o un URL; il probe ignora gli URL
  (`[DA CHIARIRE D1]` chiarisce se git-mtime è necessario per i path di repo).
- La risoluzione delle obsolescenze (fondere, aggiornare, potare) avviene sempre con intervento
  umano/agentico; nessun automatismo unattended è in scope per questa feature.
- Le due lingue di seed garantite nell'MVP sono italiano (`it`) e inglese (`en`); altre lingue
  sono supportabili a condizione che i testi per lingua siano aggiunti alle risorse bundled.

### Dipendenze

| Dipendenza | Tipo | Note |
|------------|------|------|
| **FEAT-003-D** (`wiki_tools` esistente) | Fondazione | Tutti i nuovi comandi si appoggiano al profilo `WikiProfile`, a `iter_pages`, `collect`, `lint` e `contracts` già esistenti |
| **FEAT-012** (`sertor install wiki`) | Coordinamento | Il tema lingua (b) — REQ-035..037 — richiede modifiche all'installer; la fonte della verità (campo `language`) è definita qui |
| **Costituzione v1.1.0** (Principio VI, X, IV, III) | Architetturale | Non-distruttività, host-agnosticità, errori espliciti, YAGNI sono vincoli non negoziabili |

---

## 8. Rischi

| ID | Rischio | Prob | Impatto | Mitigazione |
|----|---------|------|---------|-------------|
| R-01 | **Probe di freschezza con falsi positivi su filesystem clonato** (mtime = data clone, non data scrittura) | Alta | Medio | Modalità `--git-mtime` come opt-in (REQ-004); default su filesystem-mtime con nota nel contratto |
| R-02 | **`move` lascia link rotti su alias non coperti** (`[[pagina|alias]]` con alias diverso dallo slug) | Media | Alto | REQ-015: usa la stessa logica `_link_targets()` di `lint`; REQ-012 dry-run obbligatorio; validare con `lint` post-move |
| R-03 | **`reconcile` usato per cancellazione cieca** da un consumatore che interpreta la lista come "da eliminare" | Bassa | Alto | REQ-023/027: la detection è read-only, il contratto non espone un campo "delete"; documentare esplicitamente che la risoluzione è N |
| R-04 | **Seed localizzati disallineati tra versioni** (stringa inglese nel seed vs `language=it`) | Media | Basso | REQ-031/032: fallback esplicito a en + warning; suite di test su entrambe le lingue obbligatorie |
| R-05 | **Asset installer non aggiornati** (claude-md-block in italiano su ospite en) | Alta (già occorre) | Medio | REQ-035..037 richiedono la parametrizzazione; il test di anti-drift dell'installer (`packages/sertor/tests/test_host_agnostic.py`) va esteso alla verifica di lingua |
| R-06 | **Scope-creep: lint B/C nel codice** | Bassa | Alto | Anti-scope esplicito in §4; il confine D↔N è invariante |

---

## 9. Prioritizzazione (MoSCoW)

| Gruppo | ID REQ | MoSCoW | Motivazione |
|--------|--------|--------|-------------|
| A — Probe di freschezza | — | **Won't** | ❌ Eliminato con decisione utente (D1, 2026-06-12): valore marginale, falsi positivi strutturali; il lint B del rituale lo batte |
| B — `move`-con-link | REQ-010..015 | **Should** | Rende il reorg (N9) sicuro e non manuale; senza, il rischio di link rotti post-reorg rimane |
| C — `reconcile` detection | REQ-020..027 (senza 024) | **Should** | Workflow guidato per le obsolescenze, su `status: superseded` (esplicito, zero falsi positivi) |
| D — Trigger periodico | REQ-028 | **Could** | Documentazione d'uso + delega all'ambiente ospite (D2 risolta) |
| E — Seed localizzati | REQ-030..034 | **Should** | Chiude il gap lingua in `structure init`; tabella di localizzazione it/en (D3) |
| F — Asset installer in inglese canonico | REQ-035..037 | **Should** | Traduzione one-time + istruzione lingua-contenuto (D4); coordinamento FEAT-012 |
| Estensione `collect` (status) | REQ-021 | **Should** | Prerequisito di `reconcile` (REQ-020); overhead minimo sull'operazione esistente |

---

## 10. Domande aperte (RISOLTE il 2026-06-12)

Tutte risolte con l'utente lo stesso giorno dell'elicitazione e codificate nei requisiti:

| # | Tema | Decisione | Codificata in |
|---|------|-----------|---------------|
| D1 | Probe di freschezza | ❌ **ELIMINATO (Won't)** — decisione utente («aggiunge poco valore»), confermata dall'analisi: falsi positivi sui `sources` larghi, il lint B del rituale ha il contesto dello step, non copre i doc di repo | Gruppo A → Won't; REQ-024 rimosso; LSC-1 rimosso; reconcile su solo `status` |
| D2 | Trigger periodico reconcile | Resta **Could** come documentazione d'uso; schedulazione delegata all'ambiente ospite (cron/hook), `wiki_tools` non assume nulla | REQ-028 |
| D3 | Fonte dei seed localizzati | **Tabella di localizzazione in modulo dedicato** (decisa dal flusso principale su evidenza: i seed sono ~4 frasi → YAGNI rispetto a file-risorsa; `[strings]` override = evoluzione Could) | REQ-031 |
| D4 | Lingua degli asset installer | **INGLESE canonico unico** (decisione utente): nessuna variante per-lingua; la `language` della config governa la lingua del CONTENUTO prodotto sull'ospite. Implicazione dichiarata: `.claude/` di Sertor (derivato) diventa inglese; il wiki interno resta italiano | Gruppo F riscritto (REQ-035..037) |

Il dettaglio originale delle opzioni valutate resta sotto, per tracciabilità.

**D1 — Git-mtime: opt-in o default per i repo git?**
Il probe di freschezza usa filesystem mtime per default. Nei repo clonati il mtime è la data
del clone → falsi positivi. Con `--git-mtime` si usa il commit più recente che tocca il file
(VCS-stable), ma richiede una chiamata git (sottoproceso).
- Opzione A (raccomandazione): filesystem-mtime default, `--git-mtime` opt-in; invariante
  stdlib-only nel caso base.
- Opzione B: git-mtime default su repo git, filesystem-mtime fallback; rompe l'invariante
  "nessuna dipendenza runtime opzionale invisibile".
Decisione richiesta prima di implementare REQ-001/004.

**D2 — Trigger periodico (REQ-028): forma preferita?**
La classificazione è Could. Tre opzioni: (a) config-key che attiva un hook (chi lo chiama?),
(b) documentazione d'uso + delega all'ambiente ospite, (c) rinvio a feature futura.
Raccomandazione: opzione (b). Se l'utente ritiene il Could non prioritario, REQ-028 può essere
rimosso da questa iterazione senza impatto sui Should.

**D3 — Fonte dei seed localizzati: `[strings]` nella config o risorse per-lingua bundled?**
Impatta su REQ-031/034. Tre opzioni: (a) solo `[strings]` (l'ospite scrive tutto), (b) risorse
bundled per-lingua + override via `[strings]`, (c) solo risorse bundled senza override.
Raccomandazione: opzione (b) — coerente con come l'installer gestisce già gli asset; l'ospite
può personalizzare senza toccare il pacchetto.

**D4 — Asset installer per lingua: template con branches o asset separati per lingua?**
Impatta su REQ-035/037 e sull'epica CLI. Opzione (a): template unico con varianti per lingua
inline; opzione (b): asset per-lingua separati (`claude-md-block.en.md`,
`claude-md-block.it.md`) scelti a install-time.
Raccomandazione: opzione (b) — coerente con `importlib.resources`, più pulito da manutenere,
testabile per lingua.

---

## 11. Tracciabilità verso FEAT-003-N e l'epica

| Elemento di dote FEAT-007 | REQ coperti | Nota |
|---|---|---|
| N5 — probe deterministici FR-036/037 | ❌ eliminati (D1) | Il metodo N5 (lint B) resta giudizio nel playbook; il residuo deterministico è stato scartato con decisione — la dote dell'epica va aggiornata |
| N9 — helper `move`-con-link | REQ-010..015 | Il metodo N9 (lint C + reorg) non è nei REQ: è giudizio, sta nel playbook |
| Reconcile (idea utente 2026-06-10) | REQ-020..028 | Detection D; risoluzione = N su conferma |
| Tema lingua (a) — seed init | REQ-030..034 | Chiude gap in `structure.py` + `profile.py` |
| Tema lingua (b) — asset installer | REQ-035..037 | Requisito di coordinamento verso FEAT-012 |
| Campo `status` in `collect` | REQ-021 | Prerequisito di `reconcile` |
