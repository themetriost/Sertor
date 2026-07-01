---
title: "FEAT-084: Self-hosting di SpecLift — adozione via MCP"
type: experiment
tags: [speclift, self-host, mcp, dogfooding, collaborazione, deterministic, valutazione]
created: 2026-07-01
updated: 2026-07-01
sources: ["packages/speclift/VENDORING.md", "PR #136", "https://github.com/Sinthari/speclift"]
---

# FEAT-084: Self-hosting SpecLift — pipeline diff→requisiti ancorati via MCP

**Riassunto:** Sertor adotta il framework **SpecLift** (Sinthari) come nuovo membro del workspace nella forma self-hosted, demonstrando **collaborazione agente-to-agente** tramite feedback → correzione → reiscrizione upstream → vendoring.
Il differenziatore: SpecLift legge i **requisiti dal codice diffato**, anchor ogni voce sul filesystem reale (moat), e procede in pipeline deterministiche — il giudizio di stesura EARS è segregato in una skill agentica con accesso ai tool MCP.

## La storia collaborativa — handoff → feedback → pluggable → vendoring

1. **Handoff iniziale:** Sinthari consegna SpecLift, costruito sul consumo di Sertor **via CLI** (`sertor-rag search-code`).
2. **Feedback nostro:** I consumatori esterni (ospiti) integrano Sertor via **server MCP** (contratto agente-to-agente), non via CLI (consumatore interno).
3. **Sinthari risolve:** Render l'`EvidenceLocator` pluggable — **due adapter**:
   - **Adapter A** (SertorRagLocator): CLI `sertor-rag search-code` — per consumo interno.
   - **Adapter B** (ProvidedEvidenceLocator): Agente + MCP tool — per consumo esterno.
4. **Noi adottiamo Adapter B:** Mergia upstream (`5ee6fc1`), vendoriamo puro (zero fork, convergenza), abilito il flusso **three-gear** agente-drivenanche nel nostro workflow.

## Design — il "sandwich" SpecLift

SpecLift è **deterministico-per-costruzione** con UN solo stadio di giudizio:

```
┌─────────────────────────────────────────────────┐
│ Deterministic Pipeline (9 stadi)                │
├─────────────────────────────────────────────────┤
│ ingest (diff)                                   │
│   ↓                                             │
│ parse (hunks)                                   │
│   ↓                                             │
│ filter (criteri scope)                          │
│   ↓                                             │
│ locate (evidence finder — pluggable adapters)   │ ← Adapter B: MCP tools
│   ↓                                             │
│ bundle (changeset structure)                    │
│   ↓                                             │
│ verify (moat: re-check filesystem)              │
│   ↓                                             │
│ render (template EARS)                          │
└─────────────────────────────────────────────────┘
        ↓ (output: `located.json` structure)
┌─────────────────────────────────────────────────┐
│ GIUDIZIO AGENTE (SpecLift Skill)                │
├─────────────────────────────────────────────────┤
│ Stesura EARS allineata ai requisiti/vincoli     │
│ (tool MCP per ricerca codice / validazione)     │
└─────────────────────────────────────────────────┘
```

**Il moat:** ogni àncora (file, linea, simbolo) è riverificata sul filesystem **prima di renderla**, non via RAG alone (controllo di realtà).

## Flusso three-gear operativo (Adapter B)

```
1. speclift changeset <commit|tag>
   ↓ list changeset candidato
   
2. [Agente + MCP]: `search_code` locate symbols/implementazioni
   ↓ generate `located.json` → esiti with verita
   
3. speclift bundle --changeset --located
   ↓ assemble structured requirements → `requisiti-EARS.toml`
```

**Verifica moat:** prima che il render tocchi il file, `located.json` contiene field `verified: bool` (true = ritrovato live su master, false = skip).

## Cosa è stato mergiato

**Commit:** `bbfb74d` (PR #136, master), **branches precedenti:** `5ee6fc1` (Sinthari, engine pluggable).

- **`packages/speclift/`** — byte-identico da `5ee6fc1`, zero fork.
  - `src/speclift/` core (9 stadi deterministici, i due adapter, model, cli).
  - `tests/` 122 test verdi (Python 3.11/3.12).
  - `VENDORING.md` (provenienza, upstream hash, changelog).
  - `LICENSE` MIT (incluso nel kit, riconoscimento + vincolo).
  - Divergenze di packaging: Python `>=3.11` (verificato); dev `jsonschema` vs runtime (no cambi logica).

- **Non-regressione:** sertor 487 · kit 151 · flow 140 · root (dogfood) 1064 test verdi.
- **`sertor-core` INVARIATO** (Principio XI).

## Dogfood e2e — prova su commit reale

Testato su commit reale di Sertor (HEAD~5):
1. `speclift changeset HEAD~5` → candidati proposti.
2. Agente invoca `search_code` su simbolo noto (`EmbeddingProvider`) → locate ha trovato il target.
3. `speclift bundle --located` → report:
   - 1 requisito generato + ancorato.
   - Moat: `verified=true` (file esiste, linea valida).
   - Esito: "excluded 0" (niente false positive).

## Natura durevole — il concetto SpecLift

La capacità è **stata estratta in pagina dedicata** [[speclift]] (concepts/) — differenziatore architetturale indipendente dalla feature di integrazione, riusabile in altri progetti.

## Pagine create/aggiornate

- **NEW** `wiki/experiments/feat-084-speclift-self-host.md` (questo file, record completo).
- **NEW** `wiki/concepts/speclift.md` (concetto durevole: sandwich deterministico, moat, adapter pattern, plugin architecture).
- **UPD** `wiki/index.md` (entry experiment + concept, updated header).

## Backlink suggeriti

Pagina experiment ← backlink entranti da:
- [[dogfooding]] (Sertor usa le sue stesse capacità).
- [[mcp-server]] (il modo di integrazione esterna).
- [[deterministic-vs-judgment]] (divisione: 9 stadi meccanici + giudizio EARS).
- [[constitution]] (Principio XI consumo via vehicle CLI/MCP).
- [[sertor-install-kit]] (toolkit where composition lives).

Pagina concept ← backlink entranti da:
- [[valutazione-e-non-regressione]] (parente: tutti ancorano qualità al codice reale).
- [[retrieval-vs-graph]] (parente: entrambe sanno che il vero segnale è il filesystem/AST, non l'indice).

## Nota di processo

- **SpecKit:** spec 18/18, plan Constitution 12/12 + missione PASS, 32 task, implement.
- **Collaborazione Sinthari:** nessuna blocco riscontrato, feedback loop veloce (handoff → plugin in ~48h).
- **Convergenza upstream:** zero fork, nessun rebase previsto; il vendoring resta in sync tramite dichiarazione `VENDORING.md`.
- **Prossimo:** distribuzione nella suite di valutazione (FEAT-XXX, quando serve), monitoraggio aggiornamenti Sinthari.
