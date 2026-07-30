---
title: ritual-check (scoperta anti-skip per-step)
type: concept
tags: [wiki, rituale-di-step, distill, lint, anti-skip, deterministico, D-vs-N, sertor-wiki-tools]
created: 2026-07-22
updated: 2026-07-30
sources: ["src/sertor_core/wiki_tools/ritual_check.py", "requirements/debito-tecnico/epic.md", "specs/097-rituale-anti-skip/"]
---

# ritual-check

Sotto-comando deterministico di `sertor-wiki-tools` (E10-FEAT-026, `ritual_check.py`): **zero-LLM, sola
lettura, offline**. Dato lo **scope di uno step** (git-diff vs una base, fallback `--pages`/fail-loud),
**trova** i candidati che l'agente poi **giudica** — è il lato-scoperta della rete anti-skip del rituale
wiki. Confine D↔N: il tool *trova*, l'agente *giudica* (non crea pagine, non decide).

## Cosa trova

- **Candidati a distillazione:** gruppi di ≥2 pagine cambiate legate da ≥2 **nuovi** backlink incrociati con
  0 nuove pagine `concepts/`/`tech/` — un'entità durevole affiorata ma non ancora distillata.
- **Candidati a drift** (per il lint semantico): `stale-updated` (una pagina cambiata il cui `updated:` lagga
  la più fresca fra le cambiate), `neighbor-of-change` (pagina linkata da una pagina cambiata non-hub, ma non
  a sua volta cambiata), `capability-exec` (file di capacità cambiati, la pagina EXEC no — config-driven).
- **Scaffold di dichiarazione forzata** `Rituale: record · distill · lint` — l'artefatto concreto a cui la
  chiusura dello step deve rispondere (anche «non serve» va dichiarato). Output JSON `wiki.ritual_check/1`.

## ⚠️ Limite noto: il perimetro è il committato, e non lo dichiara (E10-FEAT-060)

Lo scope è `base...HEAD`, cioè **solo ciò che è già committato**. Ma il rituale prescrive di scrivere la
voce di giornale **nello stesso momento del commit**: chi chiude uno step invoca `ritual-check` *prima*
di committare, quando quel perimetro è ancora vuoto. La gemella `scan` guarda invece **anche l'albero di
lavoro** — quindi allo `Stop` il gate blocca mentre `ritual-check` risponde `0 candidati su tutto`.

Misurato su host effimeri: a **parità di contenuto**, il candidato a distillazione esiste o non esiste a
seconda del solo `git commit`. E nel caso misto (una pagina committata, una no) il tool emette sulla
seconda un candidato `neighbor-of-change` **falso** — *«not itself updated»* su una pagina appena
riscritta — perdendo insieme il candidato distill. Non è solo omissione: è anche **fabbricazione**.

Il tool non sbaglia il calcolo: **risponde a un'altra domanda e tace sulla differenza**. Rimedio in corso
(E10-FEAT-060): perimetro allineato a `scan` **e** dichiarato nell'output. Finché non atterra, leggi uno
`0` come *«nel committato non c'è nulla»*, mai come *«nello step non c'è nulla»*.

## Gemella di daily-distill-floor

`ritual-check` opera **per-step (git-diff)**: cosa è cambiato *ora*. La [[daily-distill-floor]] opera
**per-corpus, cross-sessione**: cosa si è accumulato *nel tempo* (il distill matura per accumulo — un'entità
diventa referenziata da ≥k punti settimane dopo, invisibile al diff dello step). Le due sono complementari:
`ritual-check` = tool che trova per-step + dichiarazione forzata; `daily-distill-floor` = merge-gate
bloccante + audit cross-sessione. Entrambe sono **[[fail-loud-fix-cause|Fail Loud]] applicato al *processo***:
lo skip del distill/lint non deve poter avvenire in silenzio.

## Host-agnostico

Legge scope e tassonomia da `wiki.config.toml` (Principio X); rileva il **default branch** a runtime
(`origin/HEAD` → ref esistenti, non assume `master` — E10-FEAT-033); fail-loud su scope indeterminabile
(Principio XII). Distribuito agli ospiti col sistema-wiki. Vedi [[step-ritual]], [[daily-distill-floor]].
