# Operazione `reorg` — applica il refactoring organizzativo

> **Modulo operazione.** Esecutore: **solo flusso principale** (NON il curator).
> Per il **substrato condiviso** (confine D↔N §2, tassonomia §3, voce di log §6) vedi il playbook
> `wiki-playbook.md`; lo stato-bersaglio di una pagina (collocazione, atomicità, link) è
> [`../page-craft.md`](../page-craft.md); la *crescita per refactoring* del grafo (spezza in entità+hub,
> fondi le micro-pagine) è [`../wiki-craft.md`](../wiki-craft.md). Qui solo la procedura specifica.

Applica, **su conferma esplicita** dell'utente, le proposte del **lint livello C** (`ops/lint.md`). È **più
distruttivo** della correzione-claim (sposta file, riscrive link) → **mai automatico, mai bloccante, un
incremento per volta**. È **giudizio** (cosa spostare/dove/se splittare) + meccanica via `Read`/`Edit`:
**non si delega al `curator`**.

1. Parti dal report del lint livello C e **concorda con l'utente** le pagine da trattare.
2. Per ogni pagina: **spostala** nell'area corretta (nuovo path), **correggi il `type`** nel frontmatter, e
   **aggiorna tutti i wikilink entranti** (dai backlink calcolati nel lint C) perché area/slug cambiano; aggiorna
   l'indice (riga `- **[[slug]]** — summary` nella sezione giusta). Se splitti o riscrivi, la pagina risultante
   deve rispettare [`../page-craft.md`](../page-craft.md) (atomicità, auto-contenimento, link).
3. **Verifica l'igiene post-move:** `uv run sertor-wiki-tools lint --json` **e** `… validate --json` →
   attesi **0 link rotti / 0 orfani / 0 naming**. Se no, ripara prima di proseguire.
4. Appendi una voce di log `reorg` (pagine spostate da→a, `type` corretti).

> **Backlog (meccanica deterministica):** un comando `move`-con-aggiornamento-link sicuro in `wiki_tools`
> (FEAT-003-D) renderebbe il passo 2 meno fragile dell'`Edit` a mano — da fare **solo se** l'approccio manuale
> si rivela rumoroso. La **rilevazione** (livello C) resta comunque giudizio, non deterministica.
