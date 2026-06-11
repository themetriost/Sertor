---
description: Consolida nel wiki locale il lavoro della sessione (record/distill/ingest/query/lint/reorg/generate/rag-sync)
argument-hint: "[operazione e/o ambito, es. 'lint', 'generate media', 'distill <brief conversazione>', 'ingest https://...', 'rag-sync']"
---

Mantieni l'**LLM Wiki** del progetto. Ambito/operazione richiesti: $ARGUMENTS
(se vuoto, considera il lavoro rilevante svolto in questa sessione → operazione `record`).

**Fonte di verità unica:** leggi `.claude/skills/wiki-author/wiki-playbook.md` e **seguilo**. È l'**indice**
che definisce host-agnosticità, tassonomia, convenzioni e il confine D↔N; la **procedura di ogni operazione**
sta in un modulo `ops/<operazione>.md` da `Read` on-demand (tabella in §5). Non reinventare le regole qui.

**Host-agnostico:** radice, tassonomia, frontmatter, ruoli e cartelle-sorgente vengono da
`wiki.config.toml`. Il **meccanico** (inventario, lint, scan, index) lo fa la CLI `sertor-wiki-tools`:
chiamala via Bash invece di Glob/Grep a mano. A te resta il **giudizio** (cosa scrivere, contraddizioni).

Procedi così:

1. Leggi il **playbook** (indice), poi l'indice e la coda del log del wiki (nomi-file da config) per lo stato
   attuale; usa `sertor-wiki-tools collect --json` per l'inventario meccanico delle pagine.
2. **Determina l'operazione** da `$ARGUMENTS` o dal lavoro di sessione, tra:
   `record` · `distill` (entità durevoli da step, backlog o **brief di una conversazione intera**, anche
   vecchia/esterna — mai il transcript grezzo: condensa prima) · `ingest` · `query` · `lint` (livelli A
   strutturale / B semantico / C organizzativo) ·
   `reorg` (applica il refactoring organizzativo del lint C, su conferma) · `generate` (da-zero su ospite
   privo di wiki, o da-diff incrementale — il default; profondità `leggera`/`media`/`massiva` come
   argomento, default leggera) · `rag-sync`.
   Poi fai `Read` **solo del modulo `ops/<operazione>.md`** corrispondente (vedi tabella §5 del playbook).
3. **Esegui la procedura corrispondente** del modulo (input → passi → output), rispettandone i vincoli —
   in particolare: il flusso principale ha **Bash** per le op pesanti; il `generate` da-diff delega
   `git log/diff` al ruolo VCS (`[roles].vcs`), il da-zero non richiede git; `rag-sync` lancia
   `sertor-wiki-tools index`.
4. Aggiorna i cross-reference e l'indice, e appendi al log la voce
   `## [YYYY-MM-DD] <operazione> | <titolo>` (data odierna).
5. Segnala esplicitamente contraddizioni o pagine orfane (le orfane le trova `sertor-wiki-tools lint`).

Mantieni le pagine concise e interlinkate. Non toccare le fonti originali né i wiki esclusi via `exclude`.
Al termine, riassumi in 2-3 righe cosa hai aggiornato.
