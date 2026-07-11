---
title: Audit indipendente SWOT + backlog (2026-07-02)
type: synthesis
tags: [audit, swot, backlog, qualità, strategia]
created: 2026-07-02
updated: 2026-07-02
sources: ["src/sertor_core/**", "packages/**", ".claude/**", ".specify/**", "requirements/**", "specs/**", "docs/**", "wiki/**", ".github/workflows/ci.yml"]
---

# Audit indipendente — SWOT & backlog azionabile (2026-07-02)

> Audit completo del workspace richiesto dall'utente (prompt in [[fable-swot-audit-prompt]], `wiki/sources/Human/fable-swot-audit-prompt.md`).
> Metodo: 5 audit paralleli (core+test · packages+CI · governance/skill/hook · requisiti/backlog ·
> doc utente/wiki) + verifiche dirette del flusso principale (smoke MCP, re-index, spot-check dei
> finding più pesanti). Ogni claim è marcato FATTO (osservato) o INFERENZA (dedotto).

## Verdetto sintetico

**Salute: buona nel nucleo, in deriva ai bordi.** Il core `sertor-core` è production-ready sul
percorso local/Chroma: l'architettura dichiarata regge alla verifica file-per-file, 1138 test
offline, privacy engineering sopra la media. I problemi si concentrano in quattro zone: (1) il
**ciclo di vita dell'installer** ha footgun reali (`upgrade` default distrugge la coesistenza
multi-assistente); (2) i **percorsi secondari** (Azure Search non testato, hook PowerShell-only su
mac/Linux = degradazione silenziosa); (3) la **governance in prosa** che marcisce (skill SpecKit
fantasma, ~55k token di apertura sessione, status epic.md in lag cronico); (4) la **deriva
strategica**: 9 feature meta/igiene consecutive spedite mentre la leva di valore dichiarata
(`search_docs` MRR 0.55) è ferma da 11 giorni.

## SWOT (sintesi — dettaglio nel report in chat / log)

**Strengths:** architettura reale = documentazione (rarità verificata); dogfooding che trova bug
veri e li pinna con test sul componente reale; costituzione v1.4.0 operativa (12 principi
gate-checked, non aspirazionali); installer con funzioni inverse + invariante `plan ⊆ owned` +
smoke E2E reale su host terzi ({Win,Ubuntu}×{Claude,Copilot}); cultura evidence-based (ogni ✅ con
PR/SHA, zero claim fabbricati riscontrati).

**Weaknesses:** BM25 è la terza gamba senza auto-heal di staleness nel server MCP (le altre due —
Chroma, code-graph — l'hanno); track Azure Search a zero test con memoria semantica latentemente
rotta su `store_backend=azure`; `sertor upgrade` senza argomenti = capability creep + strip
dell'assistente coesistente (default `--assistant claude`); hook solo PowerShell (guardia
detect-only); ~55k token obbligatori a ogni SessionStart (roadmap 92KB letta intera per un blocco
da una schermata); frontmatter `updated:` degenerati in changelog da 13KB; 9 agenti speckit che
puntano a skill inesistenti senza guardia fail-loud; epic.md e fondo-roadmap fossili che
contraddicono l'EXEC; doc utente: `sertor configure` invisibile, quick-start Claude che manda a
Ollama quando il default è GloVe.

**Opportunities:** `search_docs` MRR 0.55 = leva diretta sul differenziatore (misura già in
piedi); E13 Fase 1 (0/13 iniziate, i 2 Must racconterebbero la fusione code+doc); pattern
playbook-pointer (l'unico sottosistema DRY) da estendere a tutta la governance; `sertor-wiki-tools`
esteso per servire solo l'EXEC; refactor del seam assistenti prima di Codex; SpecLift come motore
del lint semantico.

**Threats:** repo privato ⇒ oggi **nessun terzo può installare** e il version-check è inerte
(404→unknown, degradazione silenziosa che la costituzione stessa condanna); rischio legale licenza
speclift (MIT apposto su codice upstream senza licenza); loop auto-referenziale E10 (l'audit di
processo genera backlog più in fretta di quanto il fronte-valore consumi); default `azure`
dell'installer su adapter mai esercitati in CI; model ID hardcoded in `model_policy.py` destinati
a deprecazione.

## Backlog prioritizzato (deliverato in chat, riprodotto qui)

| ID | Tipo | P | Titolo | Impatto×Sforzo |
|---|---|---|---|---|
| A-01 | FIX | P0 | `upgrade` safety: assistente esplicito/rilevato, no capability creep | H×M |
| A-02 | FIX | P0 | Licenza speclift: LICENSE upstream + re-pin | H×S |
| A-03 | FIX | P0 | BM25 staleness auto-heal (terza gamba MCP) | H×S |
| A-04 | FIX | P0 | Session-open 55k→~10k token (EXEC-only + potatura CLAUDE.md) | H×M |
| A-05 | FIX | P0 | 9 skill speckit fantasma: creare o de-referenziare + guardia | H×S |
| A-06 | FIX | P0 | Doc: `configure` documentato + quick-start Claude su GloVe | H×S |
| A-07 | EVO | P1 | E5-FEAT-003 `search_docs` MRR 0.55 (leva missione) | H×M |
| A-08 | FIX | P1 | Security review installer (merge settings.json + hook auto-eseguiti) | H×M |
| A-09 | FIX | P1 | Hook POSIX story (promuovere E2-FEAT-010 da Could) | H×L |
| A-10 | FIX | P1 | CI: smoke E2E su PR + job 3.11 + (opz.) leg cloud | M×M |
| A-11 | FIX | P1 | Azure Search: dichiarare experimental o testare (memoria semantica inclusa) | M×M |
| A-12 | FIX | P1 | Riconciliazione epic.md↔EXEC enforced + pulizia fondo-roadmap zombie | M×S |
| A-13 | FIX | P1 | `updated:` = data secca; storia solo nel log | M×S |
| A-14 | FIX | P1 | Settings: parsing numerico guardato + scrub `detail` MCP | M×S |
| A-15 | FIX | P2 | VERSION policy (E2-FEAT-014): decidere il bump o il version-check resta morto | M×S |
| A-16 | FIX | P2 | Lifecycle edge: uninstall di file pre-esistenti + trappola marker corrotto | M×S |
| A-17 | FIX | P2 | Sync asset: copertura `rag/hooks` 5/5 + `--check` exit code + delete orfani | M×S |
| A-18 | EVO | P2 | E13 Fase 1 Musts (getting-started, README di valore) | M×M |
| A-19 | EVO | P2 | Refactor seam assistenti (surface-iteration, no ternari binari) pre-Codex | M×L |
| A-20 | FIX | P2 | Igiene: gitignore `.last-hook-error`, triage `sources/Human/`, 6 wikilink rotti, allocatore specs/NNN (collisione 077), OTel senza collector | L×S |

## Finding di dogfooding emersi durante l'audit stesso

- Hook SessionStart segnalava `RAG HEALTH DEGRADED` → re-index via vehicle eseguito (1191 doc /
  13305 chunk, +1) → smoke MCP verde (`search_code`/`search_docs`/`find_symbol` freschi).
- Rumore OTel confermato live: export verso `localhost:4318` fallito a ogni comando (collector
  assente, `SERTOR_OBSERVABILITY_OTEL` attivo) — già noto dal 2026-06-25, ancora aperto.
- I 5 subagent di audit sono stati troncati dal limite di sessione al primo giro: recuperati via
  resume senza rifare l'indagine.

## Non verificato

Byte-diff speclift vs upstream `5ee6fc1`; intestatario copyright della LICENSE vendorata;
accuratezza `docs/retrieval.md`; riconteggio indipendente dei 273 commit a VERSION congelata;
semantica di staleness del breadcrumb hook; comportamento reale di Claude/Copilot su host senza
`pwsh` (rumore per-tool-call vs silenzio).
