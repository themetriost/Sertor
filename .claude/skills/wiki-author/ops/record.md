# Operazione `record` — registra lavoro/decisione svolti

> **Modulo operazione.** Esecutore: **curator OK** (Haiku in background) o flusso principale.
> Per il **substrato condiviso** (confine D↔N §2, tassonomia §3, voce di log §6) vedi il playbook
> `wiki-playbook.md`; per **come si scrive una pagina** [`../page-craft.md`](../page-craft.md), per **se una
> cosa merita una pagina** (e che archetipo) [`../wiki-craft.md`](../wiki-craft.md). Qui solo la procedura specifica.
>
> **Confine con `distill`.** Questo record cattura l'**evento datato**; le **entità durevoli** che il lavoro
> fa emergere (entità di dominio, porte, adapter, servizi, decisioni, tecnologie) **non** si seppelliscono
> qui — si estraggono in pagine proprie con [`distill.md`](distill.md) (rituale di step, punto 2). Il record
> resta magro e vi *punta*.

1. Inventario meccanico: `uv run sertor-wiki-tools collect --json` (cosa esiste già) + leggi l'indice del
   wiki (`index.md`).
2. **Scrivi/aggiorna la/e pagina/e — giudizio di contenuto.** Decidi *nuova-vs-aggiorna* (il `collect` del
   passo 1 serve a non duplicare un concetto già presente); per *se* merita una pagina a sé applica i test
   del link/nome di [`../wiki-craft.md`](../wiki-craft.md) (non frammentare). Scegli l'area dalla **natura** della pagina
   (tassonomia: playbook §3) e scrivila secondo [`../page-craft.md`](../page-craft.md) — in
   particolare il **livello di significato**: distilla il *perché* dello step (non il diario, che è il log),
   cattura le decisioni con le **alternative scartate**, tieni il claim al **livello di astrazione dell'area**
   (evergreen in `concepts/`/`tech/`, stato datato in `experiments/`). **Giudizio:** cosa è conoscenza
   riusabile vs cronaca, e *quali* backlink dicono **perché** due pagine si connettono.
3. Aggiorna i backlink e l'indice (link + summary di una riga).
4. Appendi una voce di log `record` (formato: playbook §6; come si scrive bene: [`../log-craft.md`](../log-craft.md)).
