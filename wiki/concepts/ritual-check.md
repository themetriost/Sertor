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

> ⚠️ **Precisione nota di `neighbor-of-change`, misurata il 2026-07-30: 11 candidati proposti, 0 reali.**
> Il segnale è di **prossimità**, non di deriva: propone ogni pagina linkata da una cambiata. Ma una
> pagina **appena creata** linka i propri parenti *per costruzione* — citarli è il cablaggio normale di
> una distillazione, non l'indizio che i parenti siano invecchiati. La soglia `hub_threshold` non
> intercetta il caso, perché una pagina-entità nuova le sta sotto. Rimedio tracciato in **E10-FEAT-067**:
> escludere i link uscenti delle pagine **aggiunte**, tenendo il segnale per quelle *modificate*, dove un
> link nuovo verso una pagina ferma è davvero un indizio. Nel frattempo: *il tool trova, tu giudichi* —
> e qui il giudizio va esercitato davvero, non timbrato.

## Perimetro dello step: committato e albero di lavoro (E10-FEAT-060)

Lo scope è l'**unione** di:
- **committato:** `base...HEAD`, cioè ciò che è già su questa linea di sviluppo.
- **albero di lavoro:** file tracciati modificati (confronto contenuto) + file non tracciati.

Per questo il tool è **usabile prima di committare**, che è il momento in cui serve: il rituale prescrive
di scrivere la voce di giornale **nello stesso momento del commit**, dunque `ritual-check` viene invocato
mentre il lavoro è ancora in sospeso nell'albero. Fino a E10-FEAT-060 vedeva solo il committato, e in quel
momento rispondeva **«0 candidati»** mentre il gate allo `Stop` bloccava — *lo strumento che deve preparare
la dichiarazione taceva proprio mentre la dichiarazione andava scritta*.

**Dichiarazione del perimetro.** L'output **dichiara sempre** quale perimetro ha misurato — anche quando i
candidati sono zero, che è il caso in cui serve di più:
- nel JSON, il campo `perimeter`: le sorgenti coi rispettivi conteggi;
- nel summary umano, la riga `perimetro: committed=N · worktree=M`.

Non è cosmesi: **è la parte che impedisce al difetto di tornare invisibile.** Uno `0` senza provenienza non
distingue *«non c'è nulla»* da *«ho guardato altrove»*, e fu proprio quell'ambiguità — non il numero — a
tenere nascosto per settimane il disallineamento con [[wiki-guard]].

**Fail-loud su git.** Se un'interrogazione git fallisce (repo non trovato, ref assente), il tool
fallisce esplicitamente anziché degradare verso l'insieme vuoto in silenzio.

**Ricordo storico:** prima di questa feature, la response era sempre `base...HEAD` (solo committato),
non veniva dichiarato quale perimetro fosse stato misurato, e il tool perdeva candidati misti. Il rimedio
unisce i due perimetri e rende trasparente qual è stato coperto.

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
