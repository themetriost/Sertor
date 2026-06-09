# Operazione `generate-from-diff` — aggiorna dalle modifiche recenti

> ✅ **Stato: COMPLETA come procedura (2026-06-09).** Decisione: questa operazione resta una procedura
> guidata dal flusso principale, **senza codice nuovo**. Trigger = comando manuale `/wiki` (D-19); ambito =
> changeset dell'ultimo commit. Lint/freschezza qui sono **non bloccanti** (gate eliminato, D-20). Vedi
> `requirements/sertor-core/wiki-creazione/requirements.md` (D-19/D-20) e `wiki-llm/TODO.md` (N8).

> **Modulo operazione.** Esecutore: **solo flusso principale**.
> Per il **substrato condiviso** (confine D↔N §2, tassonomia §3, voce di log §6) vedi il playbook
> `wiki-playbook.md`; le pagine aggiornate devono restare conformi a
> [`../page-craft.md`](../page-craft.md). Qui solo la procedura specifica.

Evita di rileggere l'intero repo: aggiorna solo ciò che è cambiato.

1. Ancora il punto di partenza con `uv run sertor-wiki-tools scan --json` (file pendenti via mtime) e/o
   **delega al ruolo VCS** (`[roles].vcs`) un brief di sola lettura «`git log` + `git diff` dal punto X».
   X = data dell'ultima voce di log (o l'ultimo commit che tocca il wiki). *(Le operazioni git si delegano.)*
2. Col diff ricevuto, aggiorna **solo** le pagine impattate (giudizio).
3. Aggiorna l'indice e appendi una voce di log `generate-from-diff` che cita il range di commit.
