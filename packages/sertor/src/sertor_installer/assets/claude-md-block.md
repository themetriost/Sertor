## Rituale di step / Definition of Done (LLM Wiki)

Questo progetto mantiene un **wiki locale** in `wiki/`, ispirato al pattern "LLM Wiki" di Karpathy:
un artefatto persistente e cumulativo che cresce a ogni sessione, invece di ricostruire la
conoscenza ogni volta. La configurazione vive in `wiki.config.toml` (l'unica fonte di specificità
dell'ospite: radice, tassonomia, cartelle-sorgente, lingua).

> **Regola aurea:** ogni cosa di rilievo che si fa va documentata nel wiki — esperimenti, decisioni,
> concetti/tecnologie approfonditi, fonti ingerite. Non aspettare che l'utente lo chieda.
> Le modifiche puramente meccaniche e di poco conto non richiedono una voce.

Uno **step** è un'unità di lavoro significativa (una feature, un fix, una decisione, una ricerca,
un'analisi). **Alla fine di ogni step**, il flusso principale esegue — di propria iniziativa — questa
checklist:

1. **Registra** (`record`) — crea/aggiorna le pagine impattate, i backlink e `index.md`, e appende
   la voce nel registro (file del giorno in `wiki/log/`). Lavoro di forma → delegabile all'agente
   `wiki-curator`.
2. **Distilla le entità** (`distill`) — identifica le entità/concetti durevoli che lo step ha fatto
   emergere e, se hanno identità propria e sono referenziate da più punti, dà a ciascuna una pagina
   propria in `concepts/`/`tech/`; il record datato resta magro e vi punta. È **giudizio** → resta
   nel flusso principale.
3. **Lint semantico** (`lint` liv. B) — verifica che il wiki non sia andato alla deriva rispetto alla
   realtà del progetto (codice, requisiti, stato VCS): segnala ogni claim che il repo contraddice,
   correggi su conferma. È **giudizio** → resta nel flusso principale.

**Delega.** Che queste azioni avvengano è responsabilità del flusso principale; eseguirle o delegarle
è solo una scelta per non bloccarsi. Il `record` (trascrizione strutturata) si delega all'agente
`wiki-curator`; la distillazione e il lint semantico, essendo giudizio, restano nel flusso
principale. Per innescare manualmente un consolidamento usa il comando `/wiki` (flusso principale)
oppure delega al `wiki-curator` (in background).

**Quando registrare:** nello stesso momento del commit dello step. La voce di log non è
posticipabile: un passo non è chiuso finché commit **e** voce di log non sono entrambi fatti.

### Operazioni del wiki

- **record** — registra lavoro/decisioni: pagine + backlink + `index.md` + voce di log.
- **distill** — estrae le entità durevoli che un lavoro fa emergere in pagine proprie.
- **ingest** — acquisisce una fonte esterna (file/PDF/URL) → riassunto in `sources/`, integra nelle
  pagine collegate, segnala contraddizioni.
- **query** — risponde citando le pagine; archivia un'esplorazione preziosa come nuova pagina.
- **lint** — coerenza a tre livelli: A strutturale (frontmatter/wikilink rotti/orfani/naming), B
  semantico (claim ↔ realtà del repo), C organizzativo (collocazione/atomicità/link).
- **reorg** — applica il refactoring organizzativo emerso dal lint C, su conferma.
- **generate** — genera/aggiorna il wiki dal repo (da-zero o da-diff).
- **rag-sync** — ri-indicizza il wiki nel RAG (se abilitato in `wiki.config.toml`).
- **structure** — bootstrap idempotente della struttura del wiki.

### Convenzioni

- **Frontmatter YAML** in ogni pagina: `title`, `type`, `tags`, `created`, `updated`, `sources`.
- **Backlink** in stile wikilink `[[nome-pagina]]` (compatibile Obsidian).
- **Naming** file: kebab-case descrittivo (es. `azure-ai-search.md`).
- **Voce di log:** `## [YYYY-MM-DD] <operazione> | <titolo>`.
- Crea una nuova pagina per un concetto/entità nuovo; aggiorna quella esistente altrimenti.
- Quando una fonte nuova contraddice una pagina, segnala esplicitamente la contraddizione.
