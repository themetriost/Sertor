---
title: Daily distill floor (merge-gate del distill)
type: concept
tags: [wiki, rituale-di-step, distill, hook, governance, enforcement, merge, host-agnostico, D-vs-N]
created: 2026-07-22
updated: 2026-07-22
sources: ["requirements/debito-tecnico/epic.md", "specs/116-daily-distill-floor/", "packages/sertor/src/sertor_installer/assets/claude/hooks/distill-floor.py", "src/sertor_core/wiki_tools/distill_audit.py"]
---

# Daily distill floor

Il **pavimento giornaliero del distill**: la garanzia *hard* che ogni giornata che ha loggato lavoro chiuda
con **almeno una voce `distill`** nel log — una distillazione reale **o** un «no» motivato registrato come
voce distill. È la rete che mancava al passo `distill` del [[step-ritual]] (E10-FEAT-039).

## Perché

`distill` è *giudizio* + *condizionale* + *auto-eseguito dall'agente*: la stessa firma dei passi che si
saltano in silenzio. A differenza di `record` (delegato al `wiki-curator` **e** sollecitato dall'hook
`wiki-pending-check`), non aveva **alcuna rete** → dipendeva solo dalla memoria dell'agente. Danno misurato:
dal 2026-06-15 al 2026-07-21 (~5 settimane) **zero** voci `distill` loggate pur consegnando decine di step;
emerso solo su domanda diretta dell'utente. Convergenza indipendente col needfinding del nodo **Acta**
(stesso giorno): un wiki che «cresce in cronologia e resta povero nello strato che dà valore». La
*dichiarazione forzata* di E10-FEAT-026 era un contratto **comportamentale** (un hook non giudica) → non
enforced. Serviva un enforcement **deterministico**.

## Il meccanismo: bloccare il merge

L'enforcement colpisce **l'unico momento irreversibile e consequenziale** — il **merge di consegna** sulla
mainline. L'hook host-facing **`distill-floor`** (`PreToolUse`, matcher `Bash`) ispeziona il comando: se è
un merge di consegna (`gh pr merge`, oppure `git merge <feature>` — **non** `git merge <mainline>`, che è
solo un aggiornamento) **e** la partizione di log di oggi non ha una voce `distill`, **nega** la tool-call
(`permissionDecision: deny` su Claude; stdout fail-closed su Copilot). Proprietà chiave:

- **Gate = sola presenza** («c'è una voce `distill` oggi? sì/no»), letto in modo deterministico dalla
  partizione datata del log (`wiki.config.toml` → `log_dir`, host-agnostico — Principio X). **Non** un
  conteggio/soglia.
- **Il «no» costa**: soddisfa il pavimento anche un «distill: non necessario», ma va **loggato come voce
  `distill`** che nomina i candidati considerati (`append-log --entry-op distill --title "no: <why>"`) — un
  «no» a costo zero non esiste più.
- **Nessun deadlock**: distillare richiede scrivere pagine + `append-log`, **mai** un merge → il gate non
  può auto-bloccarsi. `git merge master` (aggiornare il branch) non è bloccato.
- **Fail-open**: pavimento indeterminabile (no config, log non ruotato) → **non** blocca mai (una merge non
  si intrappola su un pavimento non enforceable). Coerente con [[fail-loud-fix-cause]] (segnala, non
  sopprime; degrada in sicurezza).

## La parte deterministica come *contesto*, non gate

Il sotto-comando **`distill-audit`** (`sertor-wiki-tools`, contratto `wiki.distill_audit/1`, zero-LLM,
read-only) scandisce **tutto il corpus cross-sessione** (content pages + partizioni di log) e trova le
**entità referenziate da ≥k punti senza pagina** per due segnali strutturali: **wikilink penzolanti**
(`[[x]]` senza pagina) + **identificatori composti in backtick** (`` `x-y` ``). Emette un debito N +
candidati. **Ruolo: hint advisory allegato al blocco, MAI il gate.** Motivo empirico (dogfood): il
segnale-prosa è rumore-dominato (228 candidati vs 9 wikilink — i backtick marcano ogni simbolo di codice),
quindi un «debito» non è un numero azionabile; i wikilink penzolanti restano l'unico segnale ad alta
precisione. È la lezione [[feedback_distill_floor_obbligo_non_scoperta]]: **obbligo, non scoperta**.

## Confine deterministico ↔ giudizio

Il **tool trova** (deterministico), l'**agente giudica** (distilla o scrive un «no» motivato), l'**hook
esige e blocca** ma non giudica (Principio XI: consuma la CLI vehicle, non importa `sertor_core`). Il limite
onesto: un hook vede solo *se esiste una voce distill*, non se è genuina — un «no» falso resta possibile;
l'obiettivo è rendere lo skip **caro e visibile**, non impossibile.

## Relazioni

Gemella **lato-enforcement** di E10-FEAT-026 (`ritual-check`: scoperta per-**step** via git-diff +
dichiarazione forzata); `distill-audit` è complementare (per-**corpus** cross-sessione), non la sostituisce.
Distribuita agli ospiti via installer (parità Claude/Copilot) come parte del sistema-wiki: ogni ospite col
wiki riceve il merge-gate. Vedi [[step-ritual]], [[fail-loud-fix-cause]].
