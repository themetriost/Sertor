# Operazione `record` — registra lavoro/decisione svolti

> **Modulo operazione.** Esecutore: **curator OK** (Haiku in background) o flusso principale.
> Per il **substrato condiviso** (confine D↔N §2, tassonomia §3, convenzioni §4, voce di log §6)
> vedi l'indice `wiki-playbook.md`. Qui solo la procedura specifica.

1. Inventario meccanico: `uv run sertor-wiki-tools collect --json` (cosa esiste già) + leggi l'indice.
2. **Scrivi/aggiorna la/e pagina/e — giudizio di contenuto.** Decidi *nuova-vs-aggiorna* (il `collect` del
   passo 1 serve a non duplicare un concetto già presente). Scegli l'area dalla **natura** della pagina
   (indice §3) e applica **il livello di significato** (indice §4): distilla il *perché* dello step (non il
   diario, che è il log), cattura le decisioni con le **alternative scartate**, e tieni il claim al **livello
   di astrazione dell'area** (evergreen in `concepts/`/`tech/`, stato datato in `experiments/`). **Giudizio:**
   cosa è conoscenza riusabile vs cronaca, e *quali* backlink dicono **perché** due pagine si connettono.
3. Aggiorna i backlink e l'indice (link + summary di una riga).
4. Appendi una voce di log `record`.
