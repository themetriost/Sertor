# Operazione `rag-sync` — re-indicizza il wiki nel RAG

> **Modulo operazione.** Esecutore: **solo flusso principale** (NON il curator).
> Per il **substrato condiviso** (confine D↔N §2, voce di log §6) vedi il playbook
> `wiki-playbook.md`. Qui solo la procedura specifica.

Rende il wiki interrogabile via RAG (ruolo "corpus" di DA-W1).

1. Esegui `uv run sertor-wiki-tools index --config wiki.config.toml`. La CLI legge `[rag]` (corpus isolato,
   default `wiki`) e fa rebuild-from-scratch idempotente; il backend (Chroma locale / Azure AI Search)
   dipende da `RAG_BACKEND` nel `.env`. **Non** lanciare interpreti Python a mano.
2. Se la CLI segnala provider di embeddings non configurato (es. `RAG_BACKEND=azure` senza credenziali),
   **fermati e segnala** (non fallire in silenzio).
3. Appendi una voce di log `rag-sync` con `documents`/`collection` dal contratto `wiki.index/1`.
4. **Costo:** con backend azure gli embeddings sono a pagamento.
