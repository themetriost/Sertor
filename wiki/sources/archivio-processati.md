---
title: Archivio delle richieste processate (catalogo)
type: source
tags: [archivio, federazione, handoff, usersfeedback, acta, sinthari, nunzio, noetix, tracciabilita]
created: 2026-07-28
updated: 2026-07-28
sources: ["wiki/sources/input-other-agents/processed/", "wiki/sources/usersfeedback/processed/", "wiki/syntheses/roadmap.md", "requirements/debito-tecnico/epic.md"]
---

# Archivio delle richieste processate

Catalogo di ciò che è arrivato da **altri nodi** della federazione e dall'**utente**, è stato
elaborato, e si è spostato in `processed/` — dove il punto 9 del rituale lo manda perché **non venga
rielaborato**.

> **Archiviato non vuol dire nascosto.** Un documento processato resta **guardabile e collegato**, *in
> qualità di processed*: scollegarlo dal grafo — o escluderlo dalle guardie — lo renderebbe
> irraggiungibile esattamente come cancellarlo, e con in più l'illusione di averlo conservato.

**Cosa aggiunge questa pagina che la cartella non ha:** l'**esito**. Il nome del file dice *cosa è
arrivato*; solo il catalogo dice *cosa ne è venuto fuori* — ed è la sola metà non derivabile dal
filesystem. *(La metà derivabile — l'elenco dei file — è una copia senza riconciliatore: stessa forma
di [[roadmap|E10-FEAT-047]] per `wiki/log/index.md`, e istanza di
[[riassunto-invecchia-senza-riconciliatore]]. Dichiarata, non nascosta.)*

## Da altri nodi (`input-other-agents/processed/`)

| Documento | Origine · data | Esito |
|---|---|---|
| [[speclift-handoff-sinthari\|Handoff SpecLift → self-hosting + distribuzione]] | *Sinthari* · 2026-07-01 | ✅ **self-host consegnato** — E14-FEAT-001, `bbfb74d`/PR #136, vendorato in `packages/speclift`. **Distribuzione agli ospiti ancora aperta** (E14-FEAT-002) |
| [[sinthari-reply-speclift-locator-pluggable\|Risposta SpecLift — locator reso pluggable (Adapter B)]] | *Sinthari* · 2026-07-01 | ✅ mergiato upstream (`5ee6fc1`, PR #7) e vendorato: **zero fork**, convergenza upstream. Esito della collaborazione agent-to-agent che ha spostato il locator da CLI a **MCP** |
| [[sertor-confirms-speclift-adapter-b-vendored\|Conferma — Adapter B adottato e vendorato]] | *Sertor → Sinthari* · 2026-07-01 | ✅ chiuso (nostra risposta in uscita) |
| [[speclift-recon\|Ricognizione SpecLift (repo Sinthari) — per il packaging]] | *nostra* · 2026-07-01 | ✅ confluita in [[speclift]] |
| [[speclift-recon-pluggable\|Ricognizione SpecLift — `EvidenceLocator` pluggable]] | *nostra* · 2026-07-01 | ✅ confluita nell'Adapter B |
| [[specaudit-handoff-sinthari\|Handoff SpecAudit → pacchetto `sertor-flow`]] | *Sinthari* · 2026-07-02 | ✅ vendorato come `packages/specaudit` ([[specaudit]]). **Distribuzione folded in E14-FEAT-002, ancora aperta** |
| [[sinthari-reply-specaudit-followup\|Reply — handoff SpecAudit recepito, LICENSE, output T049]] | *Sinthari* · 2026-07-02 | ✅ chiuso |
| [[sinthari-proposta-principio-xii-product-vs-fixture-plane-2026-07-12\|Proposta — «Product Plane vs Fixture Plane» per lo starter]] | *Sinthari* · 2026-07-12 | ✅ **accolto e ratificato**, ma **come Principio XIII**, non XII come proposto (il XII era già *Fail Loud, Fix the Cause*). Vedi [[product-plane-vs-fixture-plane]]. ⚠️ *Il `status:` del documento dice ancora «aperto»* |
| [[sertor-reply-product-vs-fixture-plane-2026-07-14\|Accolto: Product/Fixture Plane nello starter]] | *Sertor → Sinthari* · 2026-07-14 | ✅ chiuso (nostra risposta in uscita) |
| [[nunzio-summaries-handoff-modello-wiki\|Handoff — modello wiki, lezioni da OpenWiki e wiki-compiler]] | *Nunzio* · 2026-07-09 | ✅ **elaborato per intero** → **epica E16 `evoluzione-modello-wiki`** (FEAT-001..004, 2026-07-28). Delle 7 richieste: 4 promosse a FEAT · 1 (connettori) → **E7** · 1 (dirlo fuori) → **E13 Fase 2** · 1 (hook `SessionStart` hard-coded) **già risolta** da E10-FEAT-029 + `.ps1`→`.py` |
| [[acta-domanda-distribuzione-2026-07-14\|Domanda — come distribuisci/installi nei progetti consumatori?]] | *Acta* · 2026-07-14 | ✅ risposto (riga sotto) |
| [[sertor-reply-to-acta-distribuzione-2026-07-14\|Risposta — come Sertor distribuisce/installa sé stesso]] | *Sertor → Acta* · 2026-07-14 | ✅ chiuso (nostra risposta in uscita) |
| [[acta-via-libera-installazione-2026-07-14\|Via libera: puoi installare Acta]] | *Acta* · 2026-07-14 | ✅ **Acta installato** — skill `acta` attiva, canale usato con continuità (annunci di release, triage delle segnalazioni) |
| [[acta-handover-distribuzione-2026-07-14\|Handover: installati Acta e inizia a pubblicare/scoprire]] | *Acta* · 2026-07-14 | ✅ operativo — vedi riga sopra |

## Dall'utente (`usersfeedback/processed/`)

| Documento | Data | Esito |
|---|---|---|
| [[wiki-ritual-distill-ignorato-noetix\|Passo `distill` ignorato per un'intera sessione]] (*Noetix*) | 2026-07-01 | ✅ **→ E10-FEAT-026**, poi la linea di enforcement `ritual-check` → [[daily-distill-floor]] → [[wiki-guard]] |
| [[wiki-ritual-distill-lint-discrezionale\|`record→distill→lint` discrezionale, rischio skip silenzioso]] | 2026-07-01 | ✅ **→ E10-FEAT-026** (stessa linea; è la coppia che ha originato il pavimento del distill) |
| [[memory-archive-silenzioso-path-con-spazi\|`memory archive` non cattura nulla (e tace) se il path ha uno spazio]] | 2026-07-09 | ✅ **RISOLTO** — E4-FEAT-011, `5d30635`/PR #189 (2026-07-15): `encode_project_path` collassava solo `:`/`\`/`/`, Claude Code collassa **ogni** carattere non alfanumerico → 22 sessioni recuperate su `VM-WorkingFolder`. ⚠️ *Il `status:` del documento dice ancora «da elaborare»* |
| [[evoluzione-modello-wiki-lezioni-da-openwiki-e-wiki-compiler\|Evolvere il modello wiki da OpenWiki e wiki-compiler]] | 2026-07-09 | ✅ **elaborato** → **E16** (gemello del precedente: è il documento integrale, 7 richieste). ⚠️ *Il `status:` dice ancora «da elaborare»* |

*(In `usersfeedback/processed/` stanno anche [[copilot-default-models]] → ✅ E2-FEAT-015 e
[[sertor-strumenti-audit]], già raggiungibili da altre pagine.)*

## ⚠️ Tre stati fermi, trovati scrivendo questo catalogo

Collegare l'archivio invece di nasconderlo ha fatto emergere subito ciò che nasconderlo avrebbe
sepolto — **tutti e tre sono `status:` fermi, nessuno è lavoro perso**:

1. **La proposta di *Sinthari*** porta `status: aperto — richiesta di valutazione`, ma il principio
   **è stato ratificato** (come XIII) e ha una pagina propria.
2. **Il bug `memory archive`** porta `status: da elaborare`, ma è **corretto e verificato dal vivo**
   da oltre un mese.
3. **Il modello wiki da OpenWiki/wiki-compiler** porta `status: da elaborare`, ma **era stato elaborato
   per intero**: le sue 7 richieste vivevano già come idee nella roadmap. Promosse il 2026-07-28 a
   **epica E16 `evoluzione-modello-wiki`** (FEAT-001..004; connettori → E7; «dirlo fuori» → E13 Fase 2;
   l'hook `SessionStart` era già risolto).

> **Nota su come è stato letto il n° 3.** Alla prima lettura l'avevo dato per *possibile lavoro perso*,
> perché avevo guardato **solo il `status:` e il backlog delle epiche**. Bastava aprire la roadmap: le
> sue richieste erano lì da tre settimane, ciascuna marcata *«Fonte: Nunzio»*. **Un documento processato
> ha spesso lasciato traccia altrove che nel proprio frontmatter** — cercarla prima di dichiarare un
> buco. È lo stesso errore d'ordine — *decidere prima, verificare dopo* — già registrato altrove.

Gli `status:` dei documenti **non sono stati modificati**: 1 e 2 sono documenti *ricevuti* — riscriverne
i campi falsificherebbe un record di cosa ci è stato mandato. Il 3 è un documento nostro, ma resta com'è
per la stessa ragione di coerenza. L'esito vive **qui**, dove è nostro.

## Vedi anche

- [[riassunto-invecchia-senza-riconciliatore]] — la classe di cui i tre stati fermi sono istanze.
- [[step-ritual]] — punto 9 (archivia le richieste processate) e punto 10 (regola del boy scout).
- [[dogfooding]] · [[dogfood-fidelity]] — perché la federazione ci manda segnalazioni che noi non
  vediamo: il nostro nodo è **una** configurazione, e la più favorevole.
