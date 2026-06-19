---
title: Step ritual & wiki anti-drift
type: concept
tags: [wiki, automazione, hook, governance, processo, delega, fonte-unica, rituale-di-step]
created: 2026-06-04
updated: 2026-06-19 (MCP-first di apertura + smoke test di chiusura, punti 8 e standing behavior preiniziale; aggiornati anche mcp-server.md) · 2026-06-10 (rituale a 6 punti: + executive summary roadmap, + re-index dei corpora toccati)
sources: ["CLAUDE.md", ".claude/skills/wiki-author/wiki-playbook.md", ".claude/agents/wiki-curator.md", ".claude/agents/configuration-manager.md", ".claude/settings.json", ".claude/hooks/wiki-pending-check.ps1"]
---

# Step ritual & wiki anti-drift

Il **rituale di step** è la *Definition of Done* di ogni step significativo: a fine lavoro il flusso
principale, **di propria iniziativa**, registra nel wiki ciò che ha fatto e verifica che il wiki non sia
andato in **deriva** rispetto al repo. Risolve un problema concreto: il wiki di produzione (`wiki/`) **è**
la documentazione del progetto, ma senza un controllo sistematico diverge silenziosamente dalla realtà del
codice. Il *come* della discussione che lo ha originato vive in [[retrospettiva-interazione-2026-06-04]].

## Le due nature di un controllo, e il vincolo degli hook

Ogni controllo di coerenza ha **due nature**, e separarle è la chiave dell'intero design:

- **Meccanico / deterministico** — wikilink rotti, pagine orfane, frontmatter, riferimenti a path/feature
  inesistenti. È uno *script*: un **hook di Claude Code lo esegue da solo**, è automatico nel senso pieno.
- **Semantico / di ragionamento** — «la pagina afferma un comportamento che nel codice non c'è». Richiede
  un **LLM**.

Il vincolo di piattaforma che vincola tutto il resto: un hook è una *shell command fuori dal loop del
modello*. Esegue script (natura 1) ma **non può invocare una skill/subagent in-loop** (natura 2); al
massimo inietta un promemoria, o lancia un processo `claude -p` headless separato (con costi e latenza).
Per questo l'hook esistente `wiki-pending-check.ps1`, basato su `mtime` e git-blind, non può cogliere la
deriva semantica: non ragiona.

## Standing behavior batte unattended

L'intuizione che scioglie il nodo: il flusso principale (Claude) **è un LLM già nel loop**. Scrivere la
voce di log, distillare le entità, fare il lint semantico sono **tutte azioni da LLM**: se l'LLM è già qui
e scrive il log, **non c'è alcun limite tecnico** a fargli fare anche il resto, nello stesso flusso. La
distinzione da tenere ferma:

| | Cosa significa | Chi lo fa | Limite |
|---|---|---|---|
| **Unattended** | scatta senza nessuno (timer/evento) | script in hook · `claude -p` headless · routine schedulata | l'hook non ragiona, non avvia subagent in-loop |
| **Standing** | lo fai sistematicamente mentre lavori | il flusso principale (LLM) | **nessuno** — è già lavoro da loop |

Il rituale è del secondo tipo: per esso non esiste limite tecnico. L'automazione *unattended* (gate
pre-PR, guard su reset/force-push, distillazione dai transcript) resta un **secondo strato** valido ma
separato, che copre i casi «quando non c'è nessuno».

## Standing behavior prima del rituale (apertura dello step)

Dal 2026-06-19, due regole standing di apertura — comportamenti sistematici mentre lavoriamo che precedono la checklist numerata e la precedono:

- **MCP-first (dogfooding prioritario, regola SEMPRE attiva).** Quando uno step richiede di **orientarsi nel codice o nella documentazione del corpus** (`src/`, `specs/`, `requirements/`, `wiki/`, doc), la **prima mossa è interrogare il RAG** via server MCP `sertor-rag` (`search_combined`/`search_code`/`search_docs`, `find_symbol`/`who_calls`/`related_docs`/`get_context`), **non** leggere i file a mano. Solo *dopo* che il RAG ha indicato, si usa `Read` per leggerli interi. **Perché:** ogni uso è il **test che lo strumento funzioni** — è così che misuriamo convenienza e così che i guasti **emergono** invece di marcire invisibili. *Se Sertor non usa Sertor, chi dovrebbe?* Corollari: (1) errori MCP = finding, mai rumore (segnala esplicitamente); (2) unica eccezione = fatto puntuale a posizione nota (es. «che default ha `default_k`?»), allora `Read` diretto. (3) Il Principio XI resta: accesso via vehicles (MCP/CLI), mai importare `sertor_core` direttamente.

## Il rituale (Definition of Done)

Codificato in `CLAUDE.md`. A fine di ogni step significativo, di propria iniziativa:

1. **Registra** — `record`: appende la voce nel **file del giorno** `wiki/log/<data>.md` (rotazione,
   FEAT-008, via `append-log`) + pagine impattate e `index.md`.
2. **Distilla le entità** — estrai in pagine proprie (`concepts/`/`tech/`) le entità/concetti durevoli che
   lo step ha fatto emergere (operazione `distill`, N2); il record datato resta magro e vi punta. È il
   *travaso* dal diario al grafo (vedi [[diary-vs-graph]]); dal 2026-06-10 `distill` accetta anche il brief
   di una **conversazione intera** (anche vecchia) come ingresso on-demand, oltre allo step del rituale.
3. **Lint semantico di allineamento** — confronta il contenuto del wiki con la realtà del repo (`src/`,
   `specs/`, `requirements/`, stato git) e segnala ogni claim contraddetto.
4. **Executive summary della roadmap** (dal 2026-06-09) — tieni vero il blocco executive in testa a
   [[roadmap]] (marker `EXEC:START/END`, iniettato a inizio sessione): si aggiorna nello stesso commit di
   ogni step che cambia lo stato di una capacità.
5. **Re-index dei corpora toccati** (dal 2026-06-10) — se lo step ha modificato file indicizzati, rebuild
   del corpus RAG toccato (full ma atomico e namespaced), così il [[dogfooding]] non serve mai contesto
   stantio; momento obbligato: dopo un merge su `master`. Mitigante operativo del refresh incrementale
   (FEAT-009 d'epica, Could).
6. **Mostra la roadmap dopo il merge su main** (dal 2026-06-13) — quando lo step si chiude con un merge su
   `master`/`main`, mostra all'utente l'executive summary della [[roadmap]] (blocco `EXEC:START/END`), così
   dopo ogni consegna si vede subito «dove siamo e cosa fare adesso». Si innesca **solo** al merge. Fallback:
   se la roadmap non esiste, **chiedi** all'utente e creala su conferma (non inventarla a freddo).
7. **Riassunto non tecnico (explainer)** — quando uno step **sviluppa o pianifica una capacità significativa**
   (un requisito/epica, una feature, una capacità di prodotto), produci o aggiorna una **descrizione in
   linguaggio comune** nell'area `wiki/explainers/` (per non tecnici): cosa fa e perché, con un'immagine
   quotidiana e zero gergo, e un rimando «dettaglio tecnico» alla pagina di concetto/feature corrispondente.
   È giudizio (scrivere per chi non è tecnico) → resta nel flusso principale. Calibra al valore (opzionale):
   solo per capacità che vale spiegare a uno stakeholder non tecnico — non per lo step meccanico o di solo
   tooling. Vale sia per ciò che è *fatto* sia per ciò che si *sta per sviluppare* (la pagina marca lo
   stato). Fa parte dell'asset installabile (`claude-md-block.md`): gli ospiti ricevono questa pratica con il
   sistema-wiki.
8. **Smoke test del RAG di dogfooding** (dal 2026-06-19) — **allo stesso momento del commit** dello step
   (specie dopo un re-index), il flusso principale **esercita il server MCP `sertor-rag`** per verificare che
   sia *vivo e fresco*, non solo che l'indice su disco esista. Il test DEVE colpire il **path del filtro
   metadata**: `search_code` **e** `search_docs` — **non basta `search_combined`** (la query con `where`
   metadata è proprio ciò che cede quando il server è **stantio** dopo un re-index, mentre la sola ricerca
   vettoriale regge) — più un `find_symbol` su un **simbolo a posizione nota** come controllo di **freschezza**
   del code-graph (la riga deve combaciare col file reale). Un tool in errore o un indice stantio → **segnala**
   (regola *errori-MCP = finding, mai rumore*), **riconnetti** il server e **ri-verifica**; mai degradare in
   silenzio. È il **complemento di chiusura** della regola MCP-first di apertura: ogni step verifica che lo
   strumento sia usabile. Esecuzione meccanica, ma l'esito («fresco?») è giudizio → flusso principale. Calibra
   al valore: gli step che non toccano il corpus possono saltarlo; **obbligatorio dopo un re-index / merge su
   `master`**.
9. **\<altre azioni\>** — lista estendibile: ciò che l'utente chiede di rendere standing si aggiunge qui.

La voce di log **non è posticipabile**: si scrive **nello stesso momento del commit** dello step.

## Confine di delega: trascrizione vs giudizio

La delega esiste per **non bloccare il flusso**, non per saltare il rituale. Due azioni, due regole:

| Azione | Natura | Delega | Perché |
|--------|--------|--------|--------|
| **record** | trascrizione strutturata (brief → pagine, backlink, index, voce log) | ✅ `wiki-curator` (Haiku) | lavoro di forma, retto dal brief; meno costoso |
| **distill** + **lint semantico** | giudizio sui contenuti (cosa estrarre · wiki ↔ codice/repo) | ❌ flusso principale (Opus) | richiede il contesto dello step; un agente lo rileggerebbe a freddo (più costoso e lossy) |

Quindi: la trascrizione si delega a Haiku; **giudizio e riconciliazione wiki↔repo restano in casa**. Se in
casi pesanti il giudizio va proprio delegato, si usa un override `sonnet` per-invocazione, **mai** il
default Haiku. Git si delega al `configuration-manager`. Gli hook restano promemoria vincolanti.

**Calibra al valore:** lo step innesca il rituale solo quando è *significativo* (produce conoscenza,
decisioni o codice); modifiche puramente meccaniche non lo richiedono.

## Fonte unica = CLAUDE.md

La versione **operativa** del rituale (autorità che l'LLM legge a ogni step) vive in `CLAUDE.md` e **solo
lì**, finché il rituale evolve. Il motivo è la sua natura *standing*: un'azione che deve avvenire a ogni
step non può risiedere in un asset (plugin/skill) che **non è garantito in contesto** — solo `CLAUDE.md` è
iniettato sistematicamente. Mantenere una seconda copia "portabile" in parallelo creerebbe due autorità da
sincronizzare a mano, cioè una nuova fonte di deriva. *Backlog differito:* riesportare il rituale come
plugin repository-agnostico **quando sarà stabile** (coerente col goal toolset enterprise).

## Vedi anche
- `CLAUDE.md` → sezione *Rituale di step / Definition of Done* (la regola operativa).
- [[retrospettiva-interazione-2026-06-04]] — il *come* della conversazione che ha originato il rituale.
- [[lint-organizzativo-e-reorg]] — il lint livello C, anti-deriva sull'organizzazione del wiki.
- [[sistema-wiki-fonte-unica]] — il sistema wiki di cui il rituale è la disciplina d'uso.
- [[sessionstart-hook]] — l'hook che inietta lo stato del wiki a inizio sessione.
- [[deterministic-vs-judgment]] — il confine D↔N che governa cosa si delega.
