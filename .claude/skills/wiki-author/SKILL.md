---
name: wiki-author
description: Genera/aggiorna l'LLM Wiki del progetto leggendo il repo e scrivendo le pagine. Usala quando l'utente dice "genera il wiki", "aggiorna il wiki", "documenta il progetto nel wiki". Pattern Karpathy: l'agente legge le fonti e scrive i .md.
---

# Genera l'LLM Wiki (autore)

Sei l'**autore** dell'LLM Wiki del progetto: leggi il repo e scrivi/aggiorni le pagine del wiki.

**Fonte di verità unica:** leggi `.claude/skills/wiki-author/wiki-playbook.md` (stessa cartella) e
**seguilo**. È l'**indice** con identità, tassonomia, convenzioni e il confine D↔N; la **procedura di ogni
operazione** sta in un modulo `ops/<operazione>.md` da `Read` on-demand (vedi §5 del playbook). Per questa
skill l'operazione tipica è `record` → carica `ops/record.md`. Non duplicare qui quelle regole.

**Host-agnostico:** radice del wiki, tassonomia, campi frontmatter, ruoli e cartelle-sorgente vengono da
`wiki.config.toml` (in `wiki/` sull'ospite) — non assumerli. Per il *meccanico* (inventario, lint) usa la
CLI `sertor-wiki-tools` invece di Glob/Grep a mano (vedi playbook).

## Specifico di questa skill (operazione `record` dal repo)

1. **Leggi prima il playbook**, poi l'indice del wiki (catalogo) per sapere cosa esiste già; lancia
   `sertor-wiki-tools collect --json` per l'inventario meccanico delle pagine.
2. Determina l'**ambito**:
   - se l'utente indica un'area/feature, **limitati a quella**;
   - altrimenti copri le parti rilevanti del repo partendo dalle **`source_dirs`** della config (codice e
     test → il *cosa/come*; specifiche/requisiti → il *perché*).
3. Applica l'operazione `record` del playbook: crea/aggiorna le pagine (una per concetto, idempotente),
   aggiorna i backlink e l'indice, appendi la voce al log.
4. Segnala le contraddizioni invece di risolverle in silenzio (vedi playbook).

Per ingerire una fonte esterna, fare il lint di coerenza, generare il wiki dal repo o aggiornarlo dal
diff git (operazione `generate`, ingressi da-zero/da-diff) o ri-indicizzare nel RAG, usa le operazioni
omonime del playbook (tipicamente via il comando `/wiki <operazione>`).

## Versionamento (opzionale)
A fine generazione, se l'utente vuole versionare, **delega al ruolo VCS** (`[roles].vcs` in config; mai git
diretto): commit `docs(wiki): genera/aggiorna pagine` con staging selettivo della radice del wiki.
