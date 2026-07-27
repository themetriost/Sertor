---
title: wiki-guard — gate Stop bloccante per la freschezza del wiki
type: concept
tags: [hook, wiki, rituale, lint-semantico, record, stop, distill-floor, enforcement, principio-x, principio-xi, e10, feat-040]
created: 2026-07-23
updated: 2026-07-27
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

Il **rilevatore è riusato, non reinventato**: `sertor-wiki-tools scan` calcola già `pending` — i file
di `src`/`specs`/`requirements`/`.claude` non coperti dall'ultima registrazione (**come** lo stabilisca
è il paragrafo sotto: fino a E10-FEAT-045 era una stima sugli orologi, ora è un fatto derivato). L'hook,
allo Stop:
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

## Su cosa poggia il gate: una registrazione esiste in **due medium** (E10-FEAT-045, 2026-07-27)

Un gate che chiede *«hai registrato?»* deve decidere **dove guardare**, e i posti sono due — non
intercambiabili:

| Medium | Cos'è | Vale? |
|---|---|---|
| **Consegnata** | l'ultima consegna che ha toccato il giornale | Sempre: **è** l'ancora, derivata dalla storia |
| **Nell'albero di lavoro** | la partizione **di oggi** risulta modificata o non tracciata | **Sì** — il gate si soddisfa senza obbligare a un commit |
| **Nell'albero, di un altro giorno** | una partizione diversa da oggi | **No** — ma viene **nominata** |

**Guardare solo la prima è ciò che sembra rigoroso ed è sbagliato.** Il gate interviene **a fine
turno**, quando tipicamente nulla è ancora consegnato — il lavoro è scritto, la voce è scritta, e il
commit è delegato e parte dopo. Un'ancora di sola storia pretenderebbe una **consegna** per potersi
soddisfare: una richiesta che non compete a questo gate, e **un deadlock nuovo al posto di quello
vecchio**.

**La scadenza è parte della regola, non un dettaglio.** Una registrazione nell'albero di lavoro vale
**solo per il giorno che dichiara**. Senza quel limite, un giornale dimenticato non consegnato spegne
il gate a tempo indeterminato — cioè rende **legittima** la via d'uscita (chiudere con l'albero
sporco) che il fix esiste per togliere. Ciò che non vale viene **nominato** (`stale_recording`):
altrimenti l'ospite vede un giornale «già modificato» e un gate che blocca lo stesso, e la diagnosi
torna a essere un'indagine.

*Perché vale oltre questo hook:* la stessa domanda si ripresenta per **ogni** presidio che misura «è
stato fatto X?» su un progetto versionato — il pavimento del distill, la guardia anti-drift della doc
utente (E13-FEAT-014), qualunque cosa nasca da E10-FEAT-051. È un bivio che si incontra ogni volta.

**Cosa è già vero e cosa no.** Il rilevatore ora **fornisce i nomi** dei file (`pending_paths` nel
contratto, elencati dalla resa umana della CLI) e i file **ignorati dal controllo di versione** non
contano più — non perché filtrati, ma perché la derivazione **non li fa mai entrare**. Su un ospite
**senza** controllo di versione l'ancora resta l'orologio, **dichiarato come stima** (`anchor_kind`),
perché la capacità è host-agnostica per progetto.
**Il motivo del blocco nomina i file** (resa condivisa `_hooklib.pending_detail`, usata anche dal
nudge `wiki-pending-check`): elenca i path, **dichiara** il troncamento, nomina l'eventuale
registrazione stantia con la sua data e — su ospite non-git — avverte che l'ancora è **una stima**,
con la causa. Prima diceva *quanti*, e chi lo riceveva doveva ricostruire *quali*.

*Compatibilità nelle due direzioni*, perché libreria e asset si aggiornano separatamente: lo schema
resta congelato per non spegnere i consumatori vecchi, **e** la resa restituisce stringa vuota sui
payload privi dei campi nuovi, così un host con l'asset aggiornato ma la libreria no vede il messaggio
di prima invece di un errore (verificato dal vivo). Vedi [[esito-sull-host-vs-forma-dell-asset]].

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
