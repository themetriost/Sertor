---
title: "SpecLift — pipeline deterministica diff→requisiti ancorati"
type: concept
tags: [speclift, valutazione, requisiti, deterministic, moat, plugin-architecture, sandwich]
created: 2026-07-01
updated: 2026-07-23
sources: ["https://github.com/Sinthari/speclift", "packages/speclift/", "requirements/speclift/epic.md"]
---

# SpecLift — framework di estrazione requisiti da diff con verifica moat

**SpecLift** è una pipeline **deterministica** che trasforma un diff di codice in **requisiti EARS ancorati**, con verifica di realtà (moat).
Il suo valore: separazione netta tra gli **8 stadi meccanici** (ingest→parse→filter→locate→bundle→verify→lift→render) e il **giudizio agentico** (stesura EARS).
Sinthari lo ha progettato, Sertor lo adotta via MCP nel 2026-07-01.

## Architettura — il "sandwich"

```
┌─────────────────────────────────────────────┐
│ TIER DETERMINISTICO                         │
│ (zero LLM, zero cloud, testabile offline)   │
├─────────────────────────────────────────────┤
│ Stadio 1: Ingest (diff)                     │
│ Stadio 2: Parse (hunks, context)            │
│ Stadio 3: Filter (criteri scope)            │
│ Stadio 4: Locate (evidence finder)          │ ← Pluggable adapters
│ Stadio 5: Bundle (changeset structure)      │
│ Stadio 6: Verify (moat: filesystem re-check)│
│ Stadio 7: Lift (assembla requisiti ancorati)│
│ Stadio 8: Render (template EARS)            │
│ Output: `located.json` (requisiti grezzi    │
│         con metadata + verifica)            │
└─────────────────────────────────────────────┘
        ↓ (fatto, non discussione)
┌─────────────────────────────────────────────┐
│ TIER GIUDIZIO (agente)                      │
├─────────────────────────────────────────────┤
│ Lente: allineamento EARS,                   │
│        coerenza, completezza                │
│ Tool: ricerca codice (MCP), validazione     │
│ Output: requisiti raffinati                 │
└─────────────────────────────────────────────┘
```

La divisione è **voluta**: il tier deterministico è fast + testabile + ripetibile; il giudizio agentico resta libero di vagliare, ricercare, riscrivere.

## I due adapter — pluggable evidence locator

SpecLift non conosce **come** cercare evidence: delega a un adapter scelto a runtime.

### Adapter A: SertorRagLocator (CLI)
- **Quando:** consumo interno (Sertor sul suo corpus).
- **Come:** invoca `sertor-rag search <...>` via subprocess.
- **Pro:** autorità direta sul corpus indicizzato.
- **Contro:** vincolo esterno (Sertor deve essere installato + reachable).

### Adapter B: ProvidedEvidenceLocator (MCP)
- **Quando:** consumo esterno, agente ospite, workflow federato.
- **Come:** riceve i risultati da tool MCP `search_code` (agente chiama il tool, passa i risultati a SpecLift).
- **Pro:** decoupling totale (SpecLift non chiama nulla), agenzia agente, flusso conversazionale.
- **Contro:** ordine della ricerca deciso dall'agente (non riproducibile offline).

**Pattern cardine:** SpecLift non sceglie l'adapter — l'**host costruisce** una config (o l'agente invoca SpecLift con i risultati già in mano). Zero hardcoding.

## Il "moat" — verifica di realtà

Ogni voce in `located.json` prima di passare al render deve essere **ricondotta al vero**:

```python
# Moat check (stadio 6)
for located_file in located:
    if Path(located_file.path).exists():
        # Optionally: verify line content, symbol still there, etc.
        located_file.verified = True
    else:
        located_file.verified = False  # Exclude dalla resa
```

**Conseguenza:** se il diff proponeva un simbolo che nel frattempo è stato refactorizzato, il moat lo cattura e lo zittisce. **Non fake requisiti**.

## Template EARS — output deterministico

La resa in formato EARS è **template puro** (stadio 8), no logica:

```toml
[[requirement]]
id = "REQ-001"
title = "..."
description = "..."
# Anchor: evidence
affected_files = ["path/to/file.py:125"]
symbols = ["FunctionName"]
verified = true  # Moat outcome
```

L'agente legge `verified=true`, scarta `false`. L'attributo è **dichiarativo**, non nascosto.

## Caratteristiche

- **Deterministico:** stessa diff → stessi requisiti (diff per diff).
- **Offline-safe:** nessuna rete se l'adapter è A; niente stato cloud (B dipende dall'agente).
- **Testabile:** ogni stadio è puro, mock-friendly (adapter è sola interfaccia).
- **Ancorato:** ogni requisito sa dov'è nel codice; il moat verifica che il codice c'è ancora.
- **Composable:** l'agente può chiedere "rafforza il motivo" e SpecLift re-genera (idempotente).

## Integrazione Sertor (Adapter B)

**Flusso three-gear:**
1. Agente invoca `speclift changeset <ref>` → elenco candidati.
2. Agente usa MCP tool `search_code` per localizzare evidenza (oppure l'utente fornisce i risultati).
3. Agente invoca `speclift bundle --changeset --located <risultati MCP>` → SpecLift assembla.
4. Output: `located.json` con field `verified` da moat.
5. Agente scrive requisiti EARS finali (giudizio).

**Perché Adapter B:** Sertor non "chiama" SpecLift — è l'**agente esterno** che chiama SpecLift e lo **fornisce di evidenza** via il proprio RAG (circolo virtuoso: agente usa le stesse capacità Sertor per alimentare SpecLift).

## Concetto correlato

- [[deterministic-vs-judgment]] — il confine tra tier deterministico (8 stadi) e tier agentico (stesura).
- [[valutazione-e-non-regressione]] — entrambe ancorano qualità al codice reale (vedi/graph vs moat).
- [[mcp-server]] — il veicolo di integrazione esterna (Sertor come backend di ricerca per SpecLift).
- [[dogfooding]] — Sertor usa se stesso (via MCP) per alimentare SpecLift che a sua volta valuta Sertor.

## Note storiche

- **Creazione:** Sinthari, 2026.
- **Adopzione:** Sertor, FEAT-084, 2026-07-01 (vendoring + Adapter B via MCP).
- **Versione:** upstream hash `5ee6fc1` (SpecLift master), cambio packaging minimal (niente fork).
- **Distribuzione esterna (RISOLTA 2026-07-14, E14-FEAT-002):** la casa di distribuzione di
  SpecLift/SpecAudit su ospiti terzi è **`sertor-flow`** (*fold* nel pacchetto governance). Scelta
  coerente perché `speclift`/`specaudit` sono **zero-deps** e consumano il RAG **via MCP** (Adapter B),
  senza importare `sertor-core` — come `sertor-flow`. Vedi `requirements/speclift/epic.md` (FEAT-002).
