# Operazione `ingest` — acquisisci una fonte esterna

> **Modulo operazione.** Esecutore: **curator OK** (Haiku in background) o flusso principale.
> Per il **substrato condiviso** (confine D↔N §2, tassonomia §3, voce di log §6) vedi il playbook
> `wiki-playbook.md`; per **come si scrive una pagina** vedi [`../page-craft.md`](../page-craft.md).
> Qui solo la procedura specifica.

Input: un path locale (file/PDF) o un URL.

1. Acquisisci la fonte: `Read` per file/PDF locali; `WebFetch` per URL/PDF remoti. **Non modificare** la
   fonte originale.
2. Scrivi un riassunto in `sources/<slug>.md` con frontmatter (`sources:` = path/URL d'origine). Scrivilo
   secondo [`../page-craft.md`](../page-craft.md) — in particolare il **livello di significato**:
   distilla le tesi/risultati riusabili della fonte, non parafrasarla linearmente; cattura *cosa aggiunge o
   contraddice* rispetto a ciò che già sai.
3. Integra/linka i concetti collegati nelle pagine `concepts/`/`tech/`; **segnala contraddizioni** con le
   pagine esistenti (giudizio).
4. Aggiorna l'indice e appendi una voce di log `ingest`.
