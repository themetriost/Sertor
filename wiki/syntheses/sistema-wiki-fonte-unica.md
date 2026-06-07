---
title: Sistema Wiki — Fonte Unica + Tre Interfacce
type: synthesis
tags: [wiki, governance, tooling, fonte-unica, architecture]
created: 2026-06-04
updated: 2026-06-07
sources: [".claude/skills/wiki-author/wiki-playbook.md", ".claude/skills/wiki-author/SKILL.md", ".claude/commands/wiki.md", ".claude/agents/wiki-curator.md", ".claude/hooks/wiki-pending-check.ps1", ".claude/settings.json", "CLAUDE.md"]
---

# Sistema Wiki — Fonte Unica + Tre Interfacce Sottili

## Visione

Il wiki di produzione (cartella `wiki/`) è un **LLM Wiki** in stile Karpathy con **identità, governance e intraoffice stabili**. Fino a oggi (2026-06-03), le **regole** del wiki (tassonomia, convenzioni, operazioni) **erano duplicate** in tre luoghi (skill, comando, agente), creando divergenze e punti di manutenzione. Oggi (2026-06-04) completiamo il **consolidamento** verso un **modello fonte unica** con tre **interfacce sottili** che leggono dalle regole condivise, non le riscrivono.

> **Evoluzione (2026-06-05) — host-agnostico + nucleo deterministico.** Il sistema è stato reso
> **host-agnostico** (Principio X): le regole non assumono più `wiki/`/`src/`/nomi-agente, ma leggono
> `wiki.config.toml`. Il **meccanico** (scan/lint/validate/collect/index/structure) non è più descritto
> a mano nel playbook ma **delegato alla CLI `sertor-wiki-tools`** (nucleo deterministico FEAT-003-D);
> all'LLM resta il **giudizio**. Contestuale **rename coerente** delle 4 entità: skill `genera-wiki`→
> **`wiki-author`**, playbook `playbook.md`→**`wiki-playbook.md`**, agente `wiki-keeper`→**`wiki-curator`**
> (+ `Bash`), comando `/wiki` invariato. I nomi/percorsi *vecchi* citati più sotto sono il record datato
> 2026-06-04; quelli correnti sono questi. Dettagli e confine D↔N: [[ponte-d-n-host-agnostico]].

> **Evoluzione (2026-06-07) — modularizzazione del playbook (opzione C).** La "fonte unica" **non è più un
> file monolitico**: `wiki-playbook.md` è diventato un **indice** col substrato condiviso (host-agnosticità,
> identità, confine D↔N, tassonomia, convenzioni, voce di log, limiti) + una tabella di dispatch verso
> **moduli `ops/<operazione>.md`** (stessa cartella), caricati **on-demand** dai wrapper (`Read` del solo
> modulo dell'operazione invocata). Scopo: **progressive disclosure** (invocare `record` carica ~177 righe
> invece di 331) **senza** duplicare il substrato (DRY) e **senza** trasformare le operazioni in skill (che
> violerebbe il Principio X — le skill sono un costrutto dell'host). **NB:** le **8** operazioni correnti
> sono `record · ingest · query · lint (A/B/C) · reorg · generate-from-diff · rag-sync · structure` — il
> corpo più sotto, datato 2026-06-04, ne cita ancora 6 (prima di `reorg`/`structure`). Razionale e
> alternative scartate (A monolite, B skill): `requirements/sertor-core/wiki-llm/playbook-flussi-e-modularizzazione.md`.

## Architettura

```
┌─────────────────────────────────────┐
│  Fonte Unica                        │
│  ./.claude/skills/wiki-author/      │
│    wiki-playbook.md                      │
│ (Identità + Tassonomia + Convenzioni│
│  + 6 Operazioni)                    │
└──────────────┬──────────────────────┘
       ▲       │       ▲
       │       │       │ leggono
       │       │       │ (non duplicano)
       ▼       ▼       ▼
  ┌─────┴─────────────────────────────┐
  │   Tre Interfacce Sottili          │
  ├────────────────────────────────────┤
  │ 1. Skill (istruzioni per autore)   │ → .claude/skills/wiki-author/SKILL.md
  │    [da-repo: carica playbook,      │    (hyperlink al playbook, no duped regole)
  │     segue operazioni, scrive wiki] │
  │                                    │
  │ 2. Comando (selettore operazione)  │ → .claude/commands/wiki.md
  │    [flusso principale: `/wiki`]    │    (brief e parametri, router verso skill)
  │                                    │
  │ 3. Agente (keeper in background)   │ → .claude/agents/wiki-curator.md
  │    [subagent Haiku: legge playbook │    (prime azioni: leggi playbook,
  │     come prima azione, esegue      │     poi operazioni senza duplicazione)
  │     operazioni, no git]            │
  └────────────────────────────────────┘

┌──────────────────────────────────────┐
│   Strato Automatico (Hook)           │
├──────────────────────────────────────┤
│ ./.claude/hooks/wiki-pending-check   │
│ Attivato: SessionEnd + Stop (non     │
│ bloccante). Rileva lavoro non        │
│ registrato via mtime (src/ specs/    │
│ requirements/ .claude più recenti    │
│ del log.md) → promemoria delegazione │
│ al wiki-curator.                      │
└──────────────────────────────────────┘
```

## Benefici della Fonte Unica

| Problema (pre-consolidamento) | Soluzione |
|------|---------|
| Regole duplicate in 3 posti | Playbook unico `.claude/skills/wiki-author/wiki-playbook.md` contiene identità, tassonomia (UNICA: concepts/ tech/ experiments/ sources/ syntheses/ + index.md + log.md), convenzioni frontmatter, 6 operazioni (record, ingest, query, lint, generate-from-diff, rag-sync). |
| Tassonomia divergente | Rimossa tassonomia alternativa (`manual_edited/`, `ingested_sources/`); consolidata in `sources/`. Affermazione "sources/ non si usa" corretta. |
| Agente ricalca il playbook | Agente wiki-curator **legge playbook come prima azione** (vedi `# Prima azione` in .claude/agents/wiki-curator.md); non riscrive le regole. |
| Skill duplica convenzioni | Skill rimanda al playbook; non contiene regole di tassonomia/fronmatter/wikilink. |
| Prototipo ancora nel playbook | Rimosso riferimento a `wiki/experiments/03-graphrag.md` (residuo prototipo congelato in `prototype/`). |
| `updated` in log.md non ha senso | Rimosso da frontmatter di `wiki/log.md` (file append-only, stato dato dall'ultima voce). |
| Inconsistenza hook Setup/Stop | Consolidate regole hook in `.claude/hooks/wiki-pending-check.ps1` (unico script, attivato da SessionEnd + Stop, non bloccante). Registrate in `.claude/settings.json`. Guardia `stop_hook_active` anti-loop. Testati casi positivo/negativo/guardia. |

## Le 6 Operazioni (Playbook §4)

1. **`record`** — Registra lavoro/decisione svolti (crea/aggiorna pagine, aggiorna backlink + index.md + log.md).
2. **`ingest`** — Acquisisci fonte esterna (file locale / PDF / URL; scrivi summary in sources/; integra nei concept/tech).
3. **`query`** — Rispondi domanda sul wiki; se esplorazione è preziosa, archiviala come nuova pagina.
4. **`lint`** — Verifica coerenza (frontmatter, wikilink rotti, pagine orfane, claim superati); report senza auto-correzione.
5. **`generate-from-diff`** — Aggiorna dalle modifiche recenti (delega al configuration-manager per git log/diff; aggiorna solo pagine impattate).
6. **`rag-sync`** — Re-indicizza wiki nel RAG con corpus isolato (SERTOR_CORPUS='wiki'); flusso principale; backend azure.

## Trigger Automatici (Hook)

**Script:** `.claude/hooks/wiki-pending-check.ps1`
- **Modo:** SessionEnd (riepilogo) + Stop (promemoria, non bloccante).
- **Euristica:** confronta mtime di file in `src/`, `specs/`, `requirements/`, `.claude/` con timestamp dell'ultima voce di `log.md`.
- **Output:** se lavoro non registrato, promemoria a delegare wiki-curator (con guardia `stop_hook_active` anti-loop).
- **Registrazione:** `.claude/settings.json`, hook key `wiki-pending-check-stop` e `wiki-pending-check-sessionend`.

## File Toccati (2026-06-04)

### Nuovi / Creati
- `.claude/skills/wiki-author/wiki-playbook.md` — Fonte unica (identità + tassonomia + convenzioni + 6 operazioni).
- `.claude/hooks/wiki-pending-check.ps1` — Euristica mtime + prompt promemoria.

### Aggiornati
- `.claude/skills/wiki-author/SKILL.md` — Hyperlink a playbook, no regole duplicate.
- `.claude/commands/wiki.md` — Brief e parametri, router verso skill; no tassonomia.
- `.claude/agents/wiki-curator.md` — "# Prima azione: Leggi playbook"; operazioni legittimate lì.
- `.claude/settings.json` — Registrati hook (hook keys `wiki-pending-check-stop`, `wiki-pending-check-sessionend`).
- `CLAUDE.md` — Frase "non c'è più uno Stop hook bloccante" corretta (esplicito ora: non bloccante, promemoria).

### Rimossi / Corretti
- Tassonomia divergente (manual_edited/, ingested_sources/) — consolidata in sources/.
- Residuo prototipo in wiki-curator (riferimento a wiki/experiments/03-graphrag.md).
- `updated` da frontmatter wiki/log.md.

## Impatto Operazionale

### Per l'autore (skill wiki-author)
1. Leggi playbook come prima azione (vedi hyperlink in SKILL.md).
2. Esegui operazione richiesta seguendo playbook§4.
3. Scrivi wiki, aggiorna backlink + index.md + log.md.
4. Niente git (delegato al configuration-manager se richiesto).

### Per il flusso principale (comando /wiki)
1. Ricevi brief (cosa fatto, file, numeri, esiti).
2. Individua operazione (record/ingest/query/lint/generate-from-diff/rag-sync).
3. Invoca skill generate-wiki (da-repo, carica playbook automatico).
4. Se versionamento richiesto, delega al configuration-manager (commit docs(wiki): …).

### Per l'agente wiki-curator (background, subagent Haiku)
1. Prima azione: **Leggi playbook completo** (il file `.claude/skills/wiki-author/wiki-playbook.md`).
2. Ricevi brief.
3. Esegui operazione seguendo playbook (non duplica regole).
4. Riporta pagine toccate + voce di log.
5. Niente git; niente execute_bash (solo Read/Write wiki).

### Per l'automazione (hook)
- SessionEnd: riepilogo lavoro registrato.
- Stop (non bloccante): se mtime dice lavoro non registrato, promemoria a delegare (guardia anti-loop).

## Prossimi Step (Post-Consolidamento)

1. **Testare flusso e2e:** invoca skill/comando con brief fittizio; verifica che playbook sia letto e seguito.
2. **rag-sync wiki:** una volta che sertor_core è stabile, indexare wiki in indice dedicato (corpus='wiki', backend azure, MCP follow-up).
3. **Monitor hook:** controllare che stop/sessionend hook non loopino e forniscano prompt utile.
4. **Estensione future:** se nuove operazioni emergono, aggiungere **solo** al playbook; interfacce rimangono stabili.

## Note Tecniche

- **Playbook è tooling, non wiki.** Non va indicizzato nel RAG wiki; vive in `.claude/` e cresce con il sistema di governance.
- **Idempotenza:** playbook descrive operazioni idempotenti (record su pagina esistente = aggiornamento); niente riscritture inutili.
- **Delega git:** tutte le operazioni git (incluse letture per `generate-from-diff`) vanno al configuration-manager. Il wiki-curator non esegue git.
- **Niente auto-correzione:** lint produce report, non fixes automatiche; correzioni su conferma utente.

---

**Conclusione:** Il sistema wiki è ora **governato da una fonte unica** (`wiki-playbook.md`) con tre interfacce leggere (skill + comando + agente) + automazione (hook). Tassonomia consolidata; convenzioni esplicite; operazioni ben definite. Pronto per scalare.
