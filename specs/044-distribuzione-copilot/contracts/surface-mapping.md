# Contract — Mappatura superfici per-assistente (`sertor.install.surface-parity/1`)

Contratto interno (verificabile da test) che garantisce la **parità funzionale** (SC-002): per ogni
capacità in ambito, ogni `Surface` prodotta per `claude` ha una resa per `copilot` **oppure** un gap
dichiarato.

## Invariante di parità

Per `capability ∈ {wiki, rag}` e per ogni `Surface` che l'`AssistantProfile(claude)` materializza per
quella capacità:
- `AssistantProfile(copilot)` MUST materializzare la stessa `Surface` con un contenitore valido,
  **oppure**
- la mappatura MUST esporre per quella `Surface` un **gap dichiarato** (motivo leggibile).

In nessun caso una `Surface` presente per `claude` può risultare **assente e non dichiarata** per
`copilot` (no omissione silenziosa, FR-016).

## Resa attesa (copilot)

| capability | Surface | Contenitore copilot atteso |
|---|---|---|
| rag | `MCP_SERVER` | `.vscode/mcp.json` (`servers.sertor-rag`) |
| rag | `INSTRUCTION_BLOCK` (rag-usage) | `.github/copilot-instructions.md` (blocco a marker) |
| rag | `HOOK` (anti-bypass XI) | `.github/hooks/*.json` (PreToolUse) + script riusato |
| wiki | `INSTRUCTION_BLOCK` (rituale) | `.github/copilot-instructions.md` (blocco a marker) |
| wiki | `COMMAND` (`/wiki`, `wiki-author`) | `.github/prompts/*.prompt.md` |
| wiki | `AGENT` (`wiki-curator`) | `.github/agents/wiki-curator.agent.md` |
| wiki | `HOOK` (record-pending) | `.github/hooks/*.json` (SessionStart/Stop) + script riusato |

## Proprietà verificabili (test)

1. **Copertura**: l'insieme delle Surface per `copilot` ⊇ quelle per `claude` (a meno di gap
   dichiarati) — test parametrico sulle due capacità.
2. **Contenuto condiviso**: il testo del blocco istruzioni e l'entry MCP resi per copilot derivano dalla
   **stessa** fonte usata per claude (anti-drift, REQ-021) — guardia che fallisce sulla divergenza.
3. **Script identici**: lo script dell'hook è byte-identico tra i due assistenti.
4. **Idempotenza**: seconda esecuzione → 0 `created`, solo `skipped`/`block-già-presente`.
5. **Coesistenza**: install claude poi copilot sullo stesso host → entrambe le configurazioni presenti,
   nessun doppio blocco istruzioni attivo (il blocco copilot va in `.github/`, non in `CLAUDE.md`).
