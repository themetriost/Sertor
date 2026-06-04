---
name: genera-wiki
description: Genera/aggiorna l'LLM Wiki del progetto (in wiki/) leggendo il repo e scrivendo le pagine. Usala quando l'utente dice "genera il wiki", "aggiorna il wiki", "documenta il progetto nel wiki". Pattern Karpathy: l'agente legge le fonti e scrive i .md.
---

# Genera l'LLM Wiki

Sei l'**autore** dell'LLM Wiki del progetto: leggi il repo e scrivi/aggiorni le pagine in `wiki/`.

**Fonte di verità unica:** leggi `.claude/skills/genera-wiki/playbook.md` (stessa cartella) e
**seguilo**. Contiene identità, tassonomia, convenzioni e le operazioni del wiki. Non duplicare qui
quelle regole.

## Specifico di questa skill (operazione `record` dal repo)

1. **Leggi prima il playbook**, poi `wiki/index.md` (catalogo) per sapere cosa esiste già.
2. Determina l'**ambito**:
   - se l'utente indica un'area/feature, **limitati a quella**;
   - altrimenti copri le parti rilevanti del repo partendo dalle **sorgenti** (`src/`, test → il
     *cosa/come*) e da **`specs/`/`requirements/`** (decisioni → il *perché*).
3. Applica l'operazione `record` del playbook: crea/aggiorna le pagine (una per concetto, idempotente),
   aggiorna i backlink e `index.md`, appendi la voce a `log.md`.
4. Segnala le contraddizioni invece di risolverle in silenzio (vedi playbook).

Per ingerire una fonte esterna, fare il lint di coerenza, aggiornare dal diff git o ri-indicizzare nel
RAG, usa le operazioni omonime del playbook (tipicamente via il comando `/wiki <operazione>`).

## Versionamento (opzionale)
A fine generazione, se l'utente vuole versionare, **delega al `configuration-manager`** (mai git
diretto): commit `docs(wiki): genera/aggiorna pagine` con staging selettivo di `wiki/`.
