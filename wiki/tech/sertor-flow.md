---
title: sertor-flow — l'installer di governance/SDLC
type: tech
tags: [installer, governance, sdlc, methodology, speckit-launch, multi-assistente, host-agnostico, produzione]
created: 2026-06-15
updated: 2026-06-15 (FEAT-009: multi-assistente Copilot + pivot vendoring→launch-installer)
sources: ["packages/sertor-flow/", "specs/037-governance-sertor-flow/spec.md", "specs/037-governance-sertor-flow/research.md", "specs/037-governance-sertor-flow/plan.md", ".specify/"]
---

# `sertor-flow` — l'installer di governance

Il **veicolo d'installazione dell'apparato SDLC** su un repository ospite (feature 037). Pacchetto
**separato e indipendente** (`packages/sertor-flow`, modulo `sertor_flow`), con un proprio comando
d'ingresso, che **non dipende da `sertor-core`** (Principio X, REQ-002). Consegnato con feature
037 su master (2026-06-15).

> ⚠️ **Aggiornamento FEAT-009 (PR #65, 2026-06-15) — multi-assistente + pivot launch-installer.**
> Due cambi importanti rispetto alla descrizione "feature 037" qui sotto: **(1)** `sertor-flow install`
> accetta ora **`--assistant claude|copilot`** (default `claude`) e porta la governance anche su
> **GitHub Copilot** (superfici Sertor-authored tradotte via [[assistant-targeting]]; renderer
> condiviso spostato nel [[sertor-install-kit]]). **(2)** SpecKit **non è più vendorato**: `sertor-flow`
> **lancia l'installer di spec-kit** (`specify init --ai <assistant>`, versione pinnata, via
> `CommandRunner`, **fail-fast** se assente) — gli asset `speckit-*`/`specify/**` + NOTICE/LICENSE sono
> stati **rimossi dal bundle** (l'attribuzione viaggia con l'output di `specify`). Vale per **entrambi**
> gli assistenti (non-regressione Claude verificata). **Implicazione:** reintroduce un **fetch a
> install-time** (deroga Principio II tracciata: governance≠RAG, pinnata, fail-fast). Le sezioni
> *«Asset e vendor»* e *«Flag e opzioni»* sotto vanno lette con questa correzione.

## Che cos'è

Un installer che porta **tutto il metodo di sviluppo** di Sertor su un progetto ospite con un
comando, senza avviare alcuna attività (install ≠ run). Il bundle include:

- **Skill + agenti SpecKit** (9 skill specify/clarify/plan/tasks/analyze/checklist/implement/constitution + 7
  skill git; agenti auto-generati): copia vendored spec-kit 0.8.18 (MIT, licenza attribuita).
- **Skill + agente requirements** (Sertor-authored): gestione requisiti EARS-style.
- **Agente configuration-manager** (Sertor-authored): delega automatica git.
- **Macchinario di metodo** (`.specify/` completo): template, script shell (bash + PowerShell),
  estensioni git, workflow.
- **Costituzione-starter neutra** (Sertor-authored): 9 principi ingegneristici generali, esclusi
  RAG e mission (ospite la personalizza).
- **Blocco rituale SDLC nel `CLAUDE.md`** (Sertor-authored): disciplina di step, registrazione,
  commit. Coesiste senza conflitti con il blocco wiki se presente.

## Perché esiste (storia breve)

La governance (SpecKit + costituzione + metodologia) è **ortogonale al RAG**. Un progetto può
volere solo il metodo SDLC senza il retrieval; costringere `sertor-flow` a dipendere da
`sertor-core` avrebbe significato perdere questa libertà. La soluzione è un pacchetto separato
che dipende dal [[sertor-install-kit]] (il motore di installazione, stdlib-only, core-agnostico)
e **non** dal core.

## Cosa fa `sertor-flow install`

Esecuzione unica (idempotente, non distruttivo, fail-fast):

| Artefatto | Strategia se esiste |
|-----------|-------------------|
| Skill SpecKit (16 file + 2 skill requirements + agenti) | skip **per-file** |
| Agente configuration-manager | skip se esiste |
| Blocco rituale SDLC in `CLAUDE.md` | marker distinti da wiki, idempotente, append se manca |
| Costituzione-starter (`.specify/memory/constitution.md`) | skip se esiste (ospite decide se rigenera) |
| Template di metodo (spec/plan/tasks/checklist, script bash+ps, estensioni, workflow) | skip **per-file** (talvolta parzialmente presenti) |
| File init (`init-options.json`, `integration.json`, `integrations/*.manifest.json`) | **generati** per-host |
| `NOTICE` + licenze (MIT spec-kit) | append/merge |

Report per artefatto (`created`/`skipped`/`merged`/`block`/`error`); exit 0/1/2; idempotente per
costruzione.

## Flag e opzioni MVP

```bash
sertor-flow install [--target PATH] [--json]
  --target PATH      Directory ospite (default: cwd)
  --json             Output JSON (schema: install.report/1)
```

Selettività (install solo governance senza wiki/rag) e disinstallazione differite a post-MVP.

## Proprietà architetturali

### Indipendenza dal RAG (REQ-002, NFR-1)

**Zero dipendenza da `sertor-core`:** il pacchetto si installa e gira senza che `sertor-core` sia
presente. L'unico consumatore di dipendenze non-stdlib è [[sertor-install-kit]], che è a sua volta
puro.

### Topologia dei pacchetti

```
sertor-core (RAG: wiki_tools, core di retrieval)
                     ↓
packages/sertor-install-kit (motore di installazione, stdlib)
         ↑                                    ↑
         |                                    |
packages/sertor (wiki+rag)  ──────  packages/sertor-flow (governance)
```

Se l'ospite installa `sertor-flow` senza `sertor`, il comando riesce. Se installa `sertor install
wiki`/`rag`, riceve il metodo SDLC come *pozzo separato*.

### Non distruttivo + Idempotente

- **Merge intelligente:** la costituzione-starter viene saltata se esiste (l'ospite la personalizza
  con una skill se vuole rigenerarla).
- **Preservazione dei file utente:** tutte le strategie sono `CREATE_IF_ABSENT` o merge che non
  perdono contenuto.
- **Due marker distinti:** il blocco SDLC ha marker `<!-- SERTOR:SDLC-RITUAL START/END -->`, il
  blocco wiki ha `<!-- SERTOR:WIKI-RITUAL START/END -->`. Coesistono senza conflitti.
- **Fail-fast senza rollback:** al primo errore, il comando arresta e segnala il passo fallito;
  gli artefatti già scritti restano (il re-run completa i buchi).

## Asset e vendor (D6–D8)

### Provenienza

Gli asset si dividono in tre categorie:

1. **Vendor spec-kit (MIT 0.8.18):** skill SpecKit + agenti, template/script/estensioni,
   workflow. Copia pinned da spec-kit pubblico con `NOTICE` e licenza attribuita (REQ-022).
2. **Sertor-authored:** skill requirements + agente requirements-analyst, agente
   configuration-manager, costituzione-starter, blocco rituale SDLC.
3. **Generati per-host:** file init (`init-options.json`, `integration.json`) con iniettati
   valori host-inferiti (OS, versione speckit, assistente disponibile).

### Costituzione-starter neutra (D8)

Derivata dalla costituzione Sertor v1.1.1 **de-RAGizzata**:
- **Include:** Principi I (dipendenze verso astrazioni), III (no speculativo), IV (errori
  espliciti), V (test), VI (idempotenza), VII (leggibilità), VIII (config centralizzata), IX
  (log strutturati) + sezioni Sicurezza/segreti, Governance (branch+PR, Constitution Check).
- **Esclusi:** II (RAG/doppio repository), X (mission Sertor). L'ospite aggiunge i propri
  principi e li personalizza con `speckit-constitution`.
- **Editabile:** depositata una volta (`CREATE_IF_ABSENT`); la skill di costituzione su ospite
  la rigenera se richiesto.

### Sincronizzazione asset (anti-drift)

La dogfood `.claude/`/`.specify/` di Sertor è **derivata**. Un guard test
(`packages/sertor-flow/tests/test_assets_sync.py`) verifica che gli asset di Sertor rimangono
allineati al bundle spedito all'ospite (limitato al sottoinsieme governance, non wiki di
`sertor`). Nessun file è *mano-mano*.

## Integrazione con Sertor CLI (puntatore)

In `packages/sertor/__main__.py`, il comando `sertor install governance` non è un'operazione;
emette un **messaggio-puntatore**:

```
Governance è fornita dal pacchetto separato sertor-flow.
Installa con: uvx --from "git+https://…#subdirectory=packages/sertor-flow" sertor-flow install
```

Exit code dedicato, nessuna dipendenza di `sertor` da `sertor-flow` (DA-f).

## Decisioni risolte (feature 037)

Le 7 domande aperte di scope erano già in fase requisiti; la ricerca ha risolto 10 decisioni di
design:

- **D1:** Estrazione di [[sertor-install-kit]] come terzo membro del workspace (sia `sertor` che
  `sertor-flow` lo riusano senza duplicare logica).
- **D2:** Confine kit (generico) ↔ bundle (policy). Il kit rimane stdlib; `sertor-flow` usa il
  kit per orchestrare i propri asset.
- **D3:** Spezzare dipendenza da `sertor-core`: il kit definisce proprie `InstallerError` +
  `log_event` stdlib; dove `sertor` attraversa il confine col core, wrappa gli errori.
- **D4:** Due marker distinti per SDLC vs wiki (idempotenza indipendente).
- **D5:** `execute_plan` generico con callback (elimina duplicazione tra wiki/rag/governance).
- **D6–D8:** Bundle asset (vendor spec-kit + Sertor-authored + generati), costituzione-starter,
  sync.
- **D9:** Puntatore `sertor install governance` (preserva storia senza accoppiare pacchetti).
- **D10:** Superficie CLI (`sertor-flow install`), thin consumer del kit.

Constitution Check: PASS 10/10, nessuna deroga (dettaglio in [`specs/037-governance-sertor-flow/research.md`](../../specs/037-governance-sertor-flow/research.md)).

## Backlink

- [[sertor-install-kit]] — il motore di installazione che `sertor-flow` riusa.
- [[sertor-installer]] — il package ombrello RAG che rimanda a `sertor-flow` per governance.
- [[constitution]] — i principi di ingegneria che lo starter incorpora (de-RAGizzati).
- [[deterministic-vs-judgment]] — il kit è meccanico; la policy del bundle è il giudizio.
- [[thin-consumer]] — il CLI di `sertor-flow` riusa il kit come thin consumer.
