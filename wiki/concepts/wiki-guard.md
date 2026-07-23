---
title: wiki-guard — gate Stop bloccante per la freschezza del wiki
type: concept
tags: [hook, wiki, rituale, lint-semantico, record, stop, distill-floor, enforcement, principio-x, principio-xi, e10, feat-040]
created: 2026-07-23
updated: 2026-07-23
sources: ["packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-guard.py", "packages/sertor/src/sertor_installer/install_wiki.py", "requirements/debito-tecnico/epic.md"]
---

# wiki-guard — gate Stop bloccante per la freschezza del wiki

**`wiki-guard`** (E10-FEAT-040) è l'hook host-facing che dà al **record + lint semantico** del rituale
di step la stessa **rete hard** che [[daily-distill-floor]] dà al distill: allo **Stop** (fine turno), se
la sessione ha fatto lavoro indicizzato **non ancora registrato nel wiki**, **blocca la chiusura** e
ordina all'agente di chiudere il rituale prima di fermarsi. Nasce da un fallimento osservato: il
promemoria *non-bloccante* (`wiki-pending-check`) **veniva ignorato** — le istruzioni del `CLAUDE.md`
non bastano, serve enforcement deterministico (lezione registrata in memoria).

## Gemello lato-Stop di distill-floor

Le due reti coprono momenti diversi del ciclo:

| | [[daily-distill-floor]] (FEAT-039) | **wiki-guard** (FEAT-040) |
|---|---|---|
| **Evento** | `PreToolUse` (Bash) | `Stop` / `agentStop` |
| **Momento** | alla **consegna** (merge) | a **fine turno** |
| **Gate** | oggi c'è una voce `distill`? | c'è lavoro indicizzato non registrato? |
| **Rilevatore** | partizione datata del log | `sertor-wiki-tools scan` (`wiki.scan/1`) |
| **Azione** | nega il merge | blocca lo stop |

## Meccanismo (D↔N: il tool trova, l'hook esige, l'agente giudica)

Il **rilevatore è riusato, non reinventato**: `sertor-wiki-tools scan` calcola già `pending` (file di
`src`/`specs`/`requirements`/`.claude` più recenti dell'ultima voce di log). L'hook, allo Stop:
- `pending == 0` (sessione di sola lettura / domanda) → **non blocca**, chiude normalmente;
- `pending > 0` → stampa **`{"decision":"block","reason":...}`** con un `reason` **specifico** che esige
  i tre passi: **(a) record** (pagine + backlink + index + voce di log, delegabile al `wiki-curator`),
  **(b) distill** (entità durevoli → pagina propria, o un «no» motivato loggato), **(c) lint semantico**
  (verifica wiki↔codice, correggi ogni claim contraddetto). Il **giudizio resta nel main agent**
  (Principio XI) — l'hook non registra né giudica, *esige*.

La forma dell'output è **identica su Claude e Copilot** (`Stop` top-level decision ↔ `agentStop`
nativo: entrambi forzano un altro turno — verificato sui doc ufficiali). Portabilità e parità piene
(Principio X): script `.py` stdlib-only via `_hooklib`, config-driven da `wiki.config.toml` (nessun path
hardcoded, lezione [[sessionstart-hook|FEAT-029]]).

## Sicurezza & non-intrappolamento

- **Anti-loop:** se `stop_hook_active` è già attivo → esce subito (non si re-innesca all'infinito).
- **Fail-open (Principio XII, mai trappola):** no config wiki, `scan` assente o in errore → **non blocca**
  (+ breadcrumb `hook.error/1` sullo scan-error, così il guasto si vede).
- **Risolvibile in un turno:** il `reason` è specifico apposta — non esiste un cap documentato di blocchi
  consecutivi, quindi la specificità è la difesa reale.
- `exit 0` sempre (via `_hooklib.run`), così il JSON viene parsato.

## Consegna & confine

Distribuito dall'installer con **parità Claude/Copilot** (`settings.hooks.json` per Claude; `HookEntrySpec`
`agentStop` in `install_wiki.py` per Copilot). **Rimpiazza il nudge Stop** di `wiki-pending-check` (che
resta su `SessionEnd` per il riepilogo cross-sessione). **Supersessione pulita sull'`upgrade` (FEAT-041,
✅ 2026-07-23):** `_apply_wiki_upgrade` rimuove la vecchia entry `--mode Stop` di `wiki-pending-check`
**prima** del merge additivo (substring assistant-specifico via `remove_hook_entries_by_command_substring`),
così un host che aggiorna resta single-impl (solo `wiki-guard` allo Stop, SessionEnd intatta) — niente
doppio-fire. Gemello di FEAT-031→032 (identità hook per stem). *(Il difetto emerse dal dogfooding
via installer: l'`upgrade` reale sul dogfood produsse il doppio-fire, colto e corretto nella stessa
sessione — insieme al finding FEAT-042: `upgrade --dry-run` non proietta i settings-merge.)*

## Vedi anche
- [[daily-distill-floor]] — la rete gemella lato-merge; insieme coprono consegna + fine-turno.
- [[step-ritual]] — il rituale che questi hook rendono non-saltabile · [[ritual-check]] — la dichiarazione forzata per-step.
- `wiki-pending-check` — il nudge non-bloccante che questo gate supera allo Stop.
- [[fail-loud-fix-cause]] — «Fail Loud applicato al processo»: rendere visibile ed esigibile ciò che si saltava in silenzio.
