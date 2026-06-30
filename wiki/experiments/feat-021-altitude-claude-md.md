---
title: E10-FEAT-021 — Ridurre l'altitude dei blocchi CLAUDE.md distribuiti + fonte unica "How to invoke"
type: experiment
tags: [E10-FEAT-021, CLAUDE.md, asset-distribution, altitude-riduzione, principio-iii, host-agnostico, installer, speckit, debito-tecnico]
created: 2026-06-30
updated: 2026-06-30
sources: ["specs/079-altitude-claude-md/requirements.md", "requirements/debito-tecnico/altitude-claude-md/requirements.md"]
---

# E10-FEAT-021 — Ridurre l'altitude dei blocchi CLAUDE.md distribuiti + fonte unica "How to invoke"

## Riassunto esecutivo

Implementazione di **E10-FEAT-021** (epica `debito-tecnico`, audit ISSUE-07): igiene host-facing per ridurre il carico sempre-on in `CLAUDE.md` dell'ospite e applicare il Principio III (DRY — Don't Repeat Yourself).

**Problema:** L'installer Sertor inietta 3 blocchi a marker nel `CLAUDE.md` dell'ospite, un totale di **~208 righe sempre-on** caricate a inizio sessione:
- **Blocco wiki-ritual:** ~71 righe (istruzioni step-ritual per il wiki)
- **Blocco SDLC-ritual:** ~65 righe (istruzioni passo SDLC/governance)
- **Blocco RAG-usage:** ~72 righe (indicazioni su come invocare `sertor-rag` e note Windows)

Il blocco **«How to invoke + Windows note»** era **triplicato** per causo della necessità di specificarlo in contesti diversi (RAG, skill `guided-setup`, playbook del wiki).

**Soluzione:** Fattorizzazione tramite asset canonico depositato in runtime:
- Nuovo asset **`sertor-cli-reference.md`** (guida completa host-agnostica "How to invoke Sertor")
- Depositato da `sertor install rag` in **`.sertor/sertor-cli-reference.md`** (proprietà installer, part della dir `.sertor` owned)
- I 3 blocchi sempre-on **ridotti a una direttiva standing + un pointer** al reference
- **Solo il blocco RAG** cita il reference tra i blocchi always-on; il playbook wiki risolto **closure-safe** (forma minima, niente pointer morto se installato solo-wiki)

**Riduzione reale:**
- RAG-usage: **72 → 49 righe** (−23)
- wiki-ritual: **71 → 52 righe** (−19)
- SDLC: invariato (~65 righe, non conteneva «How to invoke»)
- **Totale: 208 → ~166 righe** (−20% carico)

**Addizioni software:**
- Unica modifica di codice: `install_rag.py` (+1 `Artifact(FILE, CREATE_IF_ABSENT)` per depositare il reference)
- **Zero nuovi `ArtifactKind`/Surface/WriteStrategy/seam** nel kit
- `sertor_core` invariato

**Guardie e validazione:**
1. «How to invoke» in **un'unica fonte** (assertion del test + grep in CI)
2. **Closure dei pointer:** ogni pointer dai blocchi risolve a un asset depositato (Claude + Copilot)
3. **Non-reintroduzione:** guardia test che fallisce se la triplicazione torna
4. **Parità Copilot:** sync dogfood↔bundle verde, rework guardie per due assistenti

## Dettagli tecnici

### Asset canonico: `.sertor/sertor-cli-reference.md`

Il file contiene:
- **Intestazione:** descrizione della guida e dell'hostname/progetto
- **Sezioni:**
  - Invocare Sertor via CLI (`sertor-rag search`, `sertor-rag eval`, ...)
  - Integrazione server MCP (allegamento all'assistente)
  - Note Windows (disponibilità PowerShell Core, link download)
  - Risoluzione problemi comuni (indice mancante, MCP non registrato, ...)

**Proprietà:** `Artifact(FILE, CREATE_IF_ABSENT)` → depositato solo se assente, mai riscritto
**Ciclo di vita:** conservato a upgrade (niente rifacimento), rimosso a uninstall

### Blocc CLAUDE.md ridotti

**Blocco RAG-usage (era 72 righe, ora 49):**
- Forma precedente: ripetizione del «Come invocare» inline + note Windows dettagliate
- Nuova forma: statement lean + riferimento al file `.sertor/sertor-cli-reference.md`, note Windows minime (link solo)

**Blocco wiki-ritual (era 71 righe, ora 52):**
- Forma precedente: definizione completa del rituale step del wiki
- Nuova forma: breve recap dei passi + punto al playbook (già depositato come asset della skill)

**Blocco SDLC-ritual (~65 righe, invariato):**
- Non conteneva informazioni duplicate → nessuna modifica
- Permanenza igiene: nome coerente, niente alterazioni

### Closure dei wikilink

Nel brief dell'utente chiede backlink a:
- `[[constitution]]` (Principio III DRY)
- `[[sertor-installer]]`/`[[sertor-install-kit]]`/`[[assistant-targeting]]`
- `[[step-ritual]]`
- `[[feat-018-portabilita-os-hook]]` (feature gemella audit, portabilità)
- `[[feat-019-fail-loud-hook-agent]]` (feature gemella audit, fail-loud)

## Esiti della feature

### Specifica & Design

- **Ramo:** `079-altitude-claude-md`
- **SpecKit:** spec → plan → tasks → implement (completo)
- **Artefatti di design:**
  - `specs/079-altitude-claude-md/requirements.md`, spec, plan, tasks (flow SpecKit)
  - `requirements/debito-tecnico/altitude-claude-md/requirements.md` (EARS)

### Implementazione

- **Commit:** requirements `a488f9b` · spec `eb29563` · plan `ebda4b5` · tasks `9dafc74` · impl (in corso)
- **Test:** sertor **456** · kit **139** · root **1131 passed** (3 skip packaging)
- **Lint:** ruff pulito

### Validazione Constitution

- **Constitution Check:** PASS 12/12 + missione validata
- **Pre e post-design:** nessuna deroga
- **Core invariato:** `sertor_core` zero modifiche, scope installer/asset esclusivamente

## Frontiere e follow-up

### Dichiarati completati in questa feature
- ✅ Fonte unica «How to invoke» (no triplicazione)
- ✅ Riduzione altitude CLAUDE.md sempre-on (208 → ~166 righe)
- ✅ Principio III (DRY) + Principio X (host-agnostico) applicati
- ✅ Guardie closure + anti-reintroduzione
- ✅ Parità Copilot verificata offline

### Debiti dichiarati e rinviati
- 📋 Distribuzione su ospiti reali (prova LIVE su 2 assistenti) = follow-up step, giudizio LLM
- 📋 Refactor corpo blocchi SDLC per ulteriore riduzione = Could, P2 (richiede valutazione didattica)
- 📋 Manutenzione del reference con evoluzioni sertor-rag = backlog corrente (il file cresce col prodotto)

## Note di processo

La feature è parte dell'audit ISSUE-07 (igiene asset distribuiti). Le gemelle FEAT-018/019 hanno risolto gli altri gap identitari (portabilità OS, fail-loud), facendo di FEAT-021 il completamento della riqualificazione host-facing dell'epica debito-tecnico E10.

---

**Link utili:**
- [[constitution]] (Principio III DRY)
- [[mission-vision]] (host-agnosticità reale)
- [[step-ritual]] (come si registra il lavoro)
- [[assistant-targeting]] (dual-target Copilot)
- [[feat-018-portabilita-os-hook]] (gemella audit)
- [[feat-019-fail-loud-hook-agent]] (gemella audit)
