---
title: "Kaelen — il motore d'installazione della federazione"
type: tech
tags: [kaelen, installazione, federazione, e17, separazione, sinthari, capability]
created: 2026-10-27
updated: 2026-10-27
sources: [".kaelen/engine/run.py", ".sinthari/kaelen/skill-authoring/", "pyproject.toml", "specs/127-separazione-quattro-prodotti/migration-plan.md", "requirements/separazione-ecosistema/epic.md"]
---

# Kaelen — il motore d'installazione della federazione

**Kaelen** è il nodo della federazione che possiede il **motore d'installazione**: installa una
*capability* (skill, agenti, hook, blocchi d'istruzioni, server MCP, un ambiente Python) in un repository
per Claude Code, GitHub Copilot e Codex, e la sa aggiornare, verificare e togliere esattamente. Ha preso
questo ruolo il 2026-09-18 (decisione D1 della separazione); da quel giorno la nostra logica
d'installazione è **congelata** (sezione *Congelamento* di `CLAUDE.md`).

## Come funziona, per quello che ci tocca

- **Produttore e ospite.** Il produttore descrive ciò che pubblica in `kaelen.declaration.toml` e lo
  impacchetta (`.kaelen/packages/<capability>/`). L'ospite installa con un solo comando `uvx` puntato al
  repository e al tag del produttore. Il motore non conosce i nodi: tutto sta nella dichiarazione.
- **Ogni pacchetto porta il proprio motore.** L'ospite non installa Kaelen sulla macchina. Il primo
  pacchetto deposita anche il **Kaelen principale** in `.kaelen/engine/`, unico scrittore dei file condivisi
  (`CLAUDE.md`, `.gitignore`, `.mcp.json`, impostazioni), in sezioni marcate `kaelen:begin/end`.
- **La cartella della capability si committa.** `.<nodo>/kaelen/<capability>/` tiene registro, impronte e
  una copia del pacchetto: serve a verificare e disinstallare anche se il produttore sparisce.
- **Nessun file sovrascritto senza consenso.** Un file che il motore non ha scritto è un conflitto; un
  produttore può dichiarare in `[[previous]]` ciò che lasciava il suo vecchio installatore, così il motore
  lo adotta o lo ritira.
- **Comandi:** `install`, `update`, `verify` (anche `--live`), `uninstall`, `rollback`; per il produttore
  `draft`, `validate`, `package`.

## Da noi (stato al 2026-10-27)

- **Ospite:** è installata `sinthari/skill-authoring` **0.3.1** (target `claude-code`), col motore
  **0.16.3**. Ha portato le skill `skill-authoring`, `skill-review`, `agent-review`, `agent-authoring`, gli
  agenti `skill-author` e `agent-author`, un blocco in `CLAUDE.md`, il runtime `skillauthor`
  (`python .sinthari/kaelen/skill-authoring/launch.py skillauthor …`) e il Kaelen principale in
  `.kaelen/engine/`. Verifica: `python .kaelen/engine/run.py verify --host .`.
- **Lint:** `.kaelen`, `.sinthari` e `.claude/skills/skill-authoring` sono in `extend-exclude` di ruff:
  è codice di terzi con il suo stile, come `packages/speclift`.
- **Produttore: in preparazione.** È installato il **kit del produttore** `kaelen/producer-kit` 0.16.3
  (skill `kaelen-authoring` e `kaelen-install`, agente `kaelen-author`, sezioni in `CLAUDE.md` e
  `.gitignore`), ma Sertor non ha ancora una dichiarazione né pacchetti. Il primo è la capability `rag`
  (E17-FEAT-004, deciso il 2026-10-27): runtime sul `[runtime]` di Kaelen, `[[previous]]` per i file del
  nostro installatore. Wiki e SDLC seguono, consegnati a Thesmion e Sulcimen **dopo** la RAG, che fissa
  lo schema.

## Versioni che contano

- **0.16.3 (2026-10-27):** il `.gitignore` della cartella di capability è ancorato (`/runtime/`). Fino
  alla 0.16.2 la riga `runtime/` nascondeva anche `package/content/runtime/`, e nei clone la copia
  depositata era incompleta (`verify` → `package-unreadable`). Un pacchetto porta il motore con cui è stato
  fatto: per questo abbiamo aspettato che Sinthari re-impacchettasse (0.3.1) prima di installare.
- **Double-loading.** Installare insieme `claude-code` e `github-copilot` fa leggere a Copilot due volte
  skill, agenti e istruzioni (da `.claude/` e da `.github/`): il motore lo segnala come finding. Da noi si
  installa solo `claude-code`.

Collegati: [[roadmap]] · [[cosa-non-viaggia-in-una-migrazione]] · [[sertor-installer]].
