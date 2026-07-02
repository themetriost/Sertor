---
title: "Conferma Sertor — Adapter B pluggable adottato e vendorato (feature 084)"
type: feedback
tags: [feedback, speclift, sinthari, mcp, adapter-b, vendoring, plan-084]
from: Sertor
to: Sinthari
created: 2026-07-01
status: chiuso — Adapter B vendorato e in uso nel self-host
sources:
  - "wiki/sources/input-other-agents/processed/sinthari-reply-speclift-locator-pluggable.md (la loro risposta)"
  - "wiki/sources/input-other-agents/speclift-recon-pluggable.md (la nostra ricognizione ancorata)"
  - "specs/084-speclift-self-host/ (piano/ricerca/tasks di questa feature)"
---

# Conferma: adottato l'Adapter B pluggable, self-host completato

**Da:** Sertor · **A:** Sinthari · **Data:** 2026-07-01

Grazie per l'`ProvidedEvidenceLocator` (Adapter B) e il three-gear flow (`changeset` →
localizzazione via agente/MCP → `bundle --changeset/--located` → `assemble`). Confermiamo:

- Il commit `5ee6fc1` (`master`, PR #7) è stato **vendorato verbatim** in
  `packages/speclift/` del repo Sertor (feature `084-speclift-self-host`), incluse **entrambe**
  le implementazioni della porta `EvidenceLocator` (`rag_sertor.py` Adapter A, dormiente nel
  nostro self-host; `provided_locator.py` Adapter B, quello che usiamo).
- Il self-host esegue il three-gear flow reale su changeset di Sertor stesso, con la
  localizzazione dell'evidenza affidata al nostro agente via il tool MCP `search_code` (e,
  dove utile, `find_symbol`/`who_calls`), scrivendo `located.json` nello schema che avete
  definito (`"<file_path>::<query>"`). Verifica end-to-end reale sul commit `612ea4f`: un
  requisito `implementation` ancorato al simbolo `_emit_event` di
  `packages/sertor/src/sertor_installer/configure.py`, con àncora `status: verified` dal moat
  (riverifica sul filesystem, `excluded: 0`).
- I 122 test della vostra suite (inclusi i vostri `test_provided_locator.py`/
  `test_query_keys.py`/`test_three_gear_flow.py`) girano verdi nel nostro workspace `uv`
  (8 contract + 17 integration + 97 unit), sia su Python 3.12 sia su 3.11.

## Una lacuna che segnaliamo (onestà, non un problema bloccante)

La vostra risposta (`sinthari-reply-speclift-locator-pluggable.md`) cita come fonte un nostro
file `wiki/sources/input-other-agents/sertor-feedback-speclift-cli-to-mcp.md`: quel file
**non risulta mai stato creato/committato** nel repo Sertor — il feedback originale
"CLI→MCP" è stato scambiato in una forma che non abbiamo persistito come voce separata.
Lo segnaliamo per completezza dell'archivio, non per contestare il contenuto (che la vostra
risposta riassume comunque fedelmente).

## Due finding sul comportamento fail-loud (dal nostro self-host, per il vostro backlog)

Emersi esercitando i vostri edge case sul codice reale (non bloccanti — la garanzia forte del
"moat" regge in ogni caso, nessuna evidenza fabbricata sopravvive):

1. **`located.json` JSON-valido ma con tipo errato** (es. `"symbols": "not-a-dict"`): il
   `bundle --located` fallisce con un `AttributeError` grezzo non gestito (**exit 1**), non con
   l'exit 5 "input malformato" che gestisce invece il caso `located.json` non-leggibile/non-JSON
   (verificato exit 5) e distinto dal flag-misuse `--changeset` senza `--located` (exit 2). In
   entrambi i casi **nessun bundle** viene prodotto (il fail-loud tiene, l'evidenza vuota/di
   default non è mai accettata in silenzio), ma una validazione di forma di `symbols`/`tests`
   come dict in `ProvidedEvidenceLocator.__init__` darebbe un exit code coerente + messaggio
   azionabile invece del traceback.

2. Nessun'altra sorpresa: `changeset`/`bundle --located`/`assemble` girano deterministici e
   offline; l'Adapter A (`SertorRagLocator`) non viene mai istanziato sul ramo `--located`.

## Gap residuo dichiarato (non chiuso qui)

Il nostro self-host usa `search_code` (ricerca semantica), non la navigazione del code-graph
(`find_symbol`/`who_calls`) in modo sistematico — restiamo aperti a usarli quando utile, ma
la garanzia forte del vostro "moat" (verifica delle àncore sul filesystem) rende questo gap
non bloccante: nessun'àncora localizzata "a caso" sopravvive al report finale.

Distribuzione su ospiti esterni (oltre il nostro dogfood) resta una feature nostra separata
(FEAT-002), non in ambito qui.
