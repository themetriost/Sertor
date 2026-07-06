# Data model — asset-install (Phase 1)

Questa feature non introduce entità di dominio in `sertor-core`. Il «modello» qui è la **tassonomia
operativa** che governa la procedura: cosa è prodotto dall'install, cosa è curato/preservato, cosa fa da
rete, e le invarianti che legano queste categorie.

## Categorie di artefatto

### 1. Asset host-facing (fonte attesa = installer)
Prodotti dall'esecuzione dei veri installer; devono essere byte-conformi a ciò che un ospite riceve.

| Asset | Prodotto da | Note |
|-------|-------------|------|
| `.claude/hooks/**`, `.claude/skills/**`, `.claude/agents/**` | `sertor install rag`, `sertor-flow install` | byte-copiati dal bundle `assets/` |
| `.specify/**` (machinery SpecKit) | `sertor-flow install` (`specify init --force`) | preservante su costituzione/`plan-template` (FEAT-005) |
| Blocchi marker in `CLAUDE.md` (`SERTOR:RAG-USAGE`, `SERTOR:WIKI-RITUAL`, `SERTOR:SDLC-RITUAL`) | rag / wiki / flow | idempotenti (replace-if-marker, D4) |
| Wiring in `settings.json` (hook + PreToolUse) | `sertor install rag` | merge additivo idempotente |
| `.sertor/sertor-cli-reference.md` | `sertor install rag` | residuo non-byte (FR-007) |

**Invariante:** per ognuno esiste un modo di dimostrare provenienza = **processo d'install** (SC-2); un
asset la cui unica provenienza è il sync/script è **debito**, non fedeltà.

### 2. Artefatto curato preservato (invariante = mai distrutto)
Posseduto dal dogfood; l'install NON deve sovrascriverlo silenziosamente (REQ-005).

| Artefatto | Perché preservato | Verificato dal dry-run |
|-----------|-------------------|------------------------|
| `.sertor/.env` (key Azure reale) | segreto, mai committato/toccato | ✅ preservato |
| `.specify/memory/constitution.md` v1.4.0 | governance Sertor-authored | ✅ create-if-absent salva |
| `.mcp.json` | server dogfood configurato | ✅ merge salta se esiste |
| `wiki.config.toml` (super-set dogfood) | config avanti al template | ✅ preservato |
| prosa hand-written di `CLAUDE.md` | contratto di governance IT | riconciliazione ibrida (D3) |
| `wiki/log/<data>.md` (rotazione) | conoscenza del dogfood | super-set vs template `log.md` (D9) |

### 3. Guardia byte (ruolo nuovo = rete anti-drift, non fonte)

| Guardia | Confronta | Ruolo |
|---------|-----------|-------|
| `tests/unit/test_assets_sync.py` | `assets/claude/**` ↔ `.claude/**` | anti-drift dogfood↔bundle |
| `tests/unit/test_assets_rag_dogfood_sync.py` | `assets/rag/{hooks,skills,agents}/**` ↔ `.claude/**` | enumera **ogni** asset RAG byte-copiato |
| `packages/sertor-flow/tests/unit/test_assets_sync.py` | bundle governance ↔ `.claude/**` | anti-drift SDLC |
| `tests/unit/test_asset_install_eol.py` (**NUOVO**) | EOL del repo / file toccati | fallisce su churn CRLF o EOL-inconsistenza |

**Vincolo EOL (D1):** perché le guardie restino verdi sotto LF, **bundle e dogfood** devono essere
entrambi LF (confronto LF↔LF). La normalizzazione vale sui due lati insieme.

## Esito dell'install (stati osservabili — NFR-2)

Per ogni asset, l'`InstallReport` + `git diff` producono uno di:
- **`skipped (already present)`** — byte-identico (asset già fedele) → idempotente.
- **`updated` / `block`** — deposto o blocco (ri)scritto coi marker (idempotente al ri-run).
- **`created`** — nuovo residuo (es. `.sertor/sertor-cli-reference.md`).
- **`preserved`** — artefatto curato non toccato.
- **⚠ clobber non mappato** — un curato distrutto non previsto → **stop, ispeziona sul branch** (R-1).

## Invarianti globali (i «test» del data-model)

- **INV-1 (idempotenza):** due esecuzioni consecutive dei 3 installer → 0 blocchi duplicati, 0 curati persi
  (SC-1, NFR-1).
- **INV-2 (no-churn):** `git diff` di un file toccato mostra solo contenuto reale, 0 righe da line-ending;
  `git ls-files --eol` = repo consistente (SC-2).
- **INV-3 (single-coverage):** ogni tema di governance coperto una sola volta in `CLAUDE.md` (SC-3).
- **INV-4 (guardie verdi + drift-loud):** guardie byte verdi in stato normale, **rosse** su drift indotto
  (SC-4); la doc non cita più sync/script come *fonte*.
- **INV-5 (core invariato):** `sertor-core` byte-invariato; nessun asset distribuito Sertor-specifico
  (SC-7, Principio X/XI); suite + `ruff` verdi pre-merge (SC-5, gate FEAT-008).
