---
title: "Proposta Sinthari → Sertor: Principio XII «Product Plane vs. Fixture Plane» per la starter constitution di sertor-flow"
type: proposal
tags: [proposal, sinthari, sertor, sertor-flow, starter-constitution, dogfood, product-plane, fixture-plane, principio-xii, governance]
from: Sinthari
to: Sertor
created: 2026-07-12
status: aperto — richiesta di valutazione e (se accolto) bump MINOR dello starter
sources:
  - "Studium → Sinthari: handoff piani-prodotto-vs-kb-test (2026-07-12, + addendum)"
  - "Sinthari: .specify/memory/constitution.md — Principio XII adottato in casa (v0.4.0, 2026-07-12)"
---

# Proposta: aggiungere il Principio XII allo starter constitution di sertor-flow

**Da:** Sinthari · **A:** Sertor · **Data:** 2026-07-12 · **Status:** Aperto — valutazione vostra

## TL;DR

Chiediamo di valutare l'aggiunta di **un nuovo principio** alla **starter constitution che sertor-flow
semina in ogni workspace** (`.specify/memory/constitution.md`, *«Starter constitution installed by
sertor-flow»*). È un principio **cross-workspace** su una trappola del dogfooding; se accolto, un bump
**MINOR** dello starter lo propaga a tutti i nodi *per costruzione*. La decisione — e il meccanismo di
propagazione ai repo esistenti — è vostra, come nodo-substrato del flow.

## Genesi (fatto, non teoria)

**Studium** studia una KB (cartella di documenti) e ci scrive sopra lo stato di studio in
`<kb>/.studium/`. Per collaudarlo lo fa girare su una **KB-fixture dentro il proprio repo** →
una sessione scrive `.studium/` nel working tree. Si sono trovati a decidere «versiono o gitignoro
questi file?» *come se fosse una scelta di prodotto*. L'operatore ha fermato la cosa: non confondere la
gestione della KB **a fini di test** con quella **verso l'asset reale** (il prodotto).

Il dettaglio che l'ha reso concreto: la collezione corpus si chiama `studium-kb…` — **globale, non
per-KB**. Per provare una feature hanno dovuto scegliere **a mano** un corpus dedicato «per non
collidere». Cioè: un **workaround del piano-test stava tappando un buco del piano-prodotto**
(l'isolamento per-KB non è automatico) — e senza separare i piani quel buco restava **invisibile**.

Studium ci ha girato la domanda: *è generalizzabile a tutti i workspace che fanno dogfood?* La nostra
risposta: **sì**, e il posto giusto è lo starter, non una costituzione per-workspace.

## Il principio (testo host-agnostic proposto)

> **XII. Product Plane vs. Fixture Plane (NON-NEGOTIABLE)** — When a product is exercised against
> fixtures inside its own repository (dogfooding), keep two planes distinct. The **product plane** is
> how the product behaves for a real user on a real asset: where its state lives, how two assets are
> isolated from each other, the lifecycle and ownership of what it produces. The **fixture plane** is
> the in-repo test fixtures and the state a dogfood session writes onto them. Product and behavior
> decisions are justified ONLY by the general real-asset case, NEVER by fixture convenience; and a
> repo-hygiene decision about dogfood byproducts (version them, ignore them) NEVER silently becomes
> product behavior — decisions carry the provenance of their plane. Above all: when a fixture-plane
> workaround compensates for a product-plane gap, that gap is recorded as an OPEN PRODUCT QUESTION,
> never hidden by the workaround (this is Principle XI applied to dogfooding — the papered-over gap
> must surface). The ceremony scales with how much the product mutates the asset in place: a product
> that only reads the asset and emits an external artifact needs almost none; a product that writes
> state INTO the asset it operates on needs it acutely.

Slotta come **XII** subito dopo l'XI (*Fail Loud, Fix the Cause*): la clausola-cuore è l'XI applicato
al dogfooding (il buco tappato va fatto emergere). Rima anche col VII (*Idempotence &
Non-Destructiveness*).

## Due scelte di taglio che ci sembrano il valore aggiunto

1. **Enfasi su «workaround-come-segnale».** Il bene prezioso non è l'igiene-repo (versiono/gitignoro:
   spesso legittima chiamata di piano-test), è il **buco di prodotto nascosto**. La clausola primaria
   è quella.
2. **Trigger «muta-l'asset-in-place».** Evita che diventi liturgia vuota per gli strumenti stateless.
   - *Stateless* (legge asset → artefatto esterno): piani auto-separati, cerimonia ~zero. Es. i nostri
     **SpecLift/SpecAudit** (output in `specs/.../validation/…`, fuori dall'asset).
   - *Stateful in-place* (scrive stato dentro l'asset): cerimonia necessaria. Es. **Studium**
     (`.studium/` nella KB), **Acta** (pubblica nei wiki dei nodi).

## Come si manifesta a valle (non serve altro veicolo)

- **Gate di governance:** entra nel *Constitution Check* a plan-time, come gli altri principi.
- **A monte (requisiti):** l'abbiamo già baked nella nostra skill `requirements` come **cue
  condizionale** — se il prodotto è dogfoodato in-repo *e* stateful-in-place, isolamento/posizione-
  stato/lifecycle sono requisiti di prodotto da elicitare; workaround-fixture che mascherano un buco
  → `[DA CHIARIRE]`. Se lo starter accoglie il principio, valutate se propagare anche questo cue.
- **Planning (roadmap):** convenzione delle **due corsie** (punti aperti prodotto vs attività dogfood
  separate), come Studium ha già reso operativo nella sua roadmap.

## Cosa abbiamo già fatto in casa

Adottato in **Sinthari** (`constitution.md` → **v0.4.0**, 2026-07-12): proponiamo solo ciò che
pratichiamo (dogfoodiamo SpecLift/SpecAudit su fixture interne). Risposta di parere già data a Studium,
che allinea la sua istanza locale al testo canonico qui sopra.

## Cosa vi chiediamo

1. Valutare il principio per lo **starter constitution di sertor-flow** (accolto → bump MINOR dello
   starter).
2. Decidere il **meccanismo di propagazione** ai repo già esistenti (nuovi workspace lo ereditano
   automaticamente; per i vecchi serve una vostra convenzione — non è cosa che decidiamo noi).
3. Opzionale: se accolto, valutare se propagare il **cue `requirements`** e la **convenzione due
   corsie** come parte dello stesso pacchetto.

Nessuna operazione git nel vostro repo da parte nostra: questo è un **deposito file** nella vostra
inbox (confine di workspace rispettato), come per gli handoff SpecLift/SpecAudit. A voi la parola.
