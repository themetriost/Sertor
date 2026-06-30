# Data Model — E10-FEAT-021 (altitude blocchi CLAUDE.md + fonte unica «How to invoke»)

La feature è **igiene di asset host-facing**: non introduce entità di runtime, porte, adapter o tipi
in `sertor_core`. Le «entità» qui sono **artefatti distribuibili** e le loro **relazioni di
deposito/citazione**, governate dai meccanismi esistenti dell'installer (`Artifact`/`ArtifactKind`/
`WriteStrategy`/`AssistantProfile`). Nessun nuovo `ArtifactKind`, `WriteStrategy`, `Surface` o seam del
kit.

## 1. Entità

### E1 — Blocco a marker ridotto (`claude-md-block*.md`)
Uno dei tre asset always-on iniettati nel file di istruzione dell'ospite (CLAUDE.md o
copilot-instructions). Dopo la feature: **sole direttive comportamentali standing + pointer**.

| Campo | Valore |
|---|---|
| Identità | marker pair (`SERTOR:WIKI-RITUAL` / `SERTOR:RAG-USAGE` / `SERTOR:SDLC-RITUAL`) |
| Sorgente | `assets/claude-md-block.md` · `assets/rag/claude-md-block-rag-usage.md` · (sertor-flow) `assets/claude-md-block-sdlc.md` |
| Wiring | invariato: `MARKER_BLOCK`/`APPEND_BLOCK` (RAG), `SharedEdit MARKER` (wiki), `MARKER_BLOCK` (SDLC) |
| Lifecycle | invariato: idempotente su install, aggiornato su upgrade (`update_marker_block`), rimosso su uninstall |
| Invariante contenuto | nessun `.claude/`, nessuno slash-command, nessun nome modello/prodotto Claude (host-agnostico) |

Stati per blocco (post-feature):
- **wiki** = golden rule + outline rituale + delega + D↔N + *pointer* `wiki-playbook.md`; operazioni/convenzioni **estratte**.
- **rag** = vehicle-only/no-import + search-first + MCP-error + memory-gate + *pointer* `sertor-cli-reference.md`; sezione «How to invoke» + Windows note **estratta**.
- **sdlc** = fasi SpecKit + constitution gate + error discipline + version-control discipline (**invariato**; nessun lookup da estrarre).

### E2 — Asset canonico «How to invoke» (`sertor-cli-reference.md`) — NUOVO
L'unica sede distribuita che ospita la sezione completa di invocazione + Windows note.

| Campo | Valore |
|---|---|
| Sorgente | `packages/sertor/src/sertor_installer/assets/rag/sertor-cli-reference.md` |
| Target host | `.sertor/sertor-cli-reference.md` (host-agnostico, identico Claude/Copilot) |
| Artifact | `Artifact(ArtifactKind.FILE, "rag/sertor-cli-reference.md", ".sertor/sertor-cli-reference.md", WriteStrategy.CREATE_IF_ABSENT)` |
| Capacità | `sertor install rag` (REQ-007; RAG = contesto primario) |
| Owned | coperto dall'owned_dir `.sertor` (rimosso in blocco su uninstall; aggiornato su upgrade come gli owned-file di `.sertor/`) |
| Contenuto | sezione «How to invoke Sertor's commands» a due livelli (runtime CLIs `uv run --project .sertor` + installer `uvx --from "git+…"`) + Windows note `pywin32`; host-agnostico |

### E3 — Pointer per nome
Riferimento, in un blocco ridotto o in una skill, all'asset che porta il dettaglio rimosso, espresso
come **nome dell'asset** (non percorso assistente-specifico).

| Pointer | Da | A | Closure |
|---|---|---|---|
| ``sertor-cli-reference.md`` | RAG block (rag) | E2 | piano RAG deposita `.sertor/sertor-cli-reference.md` ✓ |
| ``sertor-cli-reference.md`` | `guided-setup` (rag) | E2 | idem ✓ |
| ``wiki-playbook.md`` | wiki block (wiki) | payload `wiki-author` | piano wiki deposita `…/wiki-playbook.md` ✓ |
| condizionale **senza filename** | `wiki-playbook` (wiki) | E2 (se RAG installato) | **fuori scope closure** (no token `*.md`) → nessun pointer morto |

### E4 — Copia inline di «How to invoke» (da centralizzare)
Le tre occorrenze storiche; dopo la feature → riferimenti/forma minima, non copie:
- `rag/claude-md-block-rag-usage.md:12-38` → **rimossa**, sostituita da pointer (E3).
- `rag/skills/guided-setup/SKILL.md:52-78` → **rimossa**, sostituita da pointer (E3).
- `claude/skills/wiki-author/wiki-playbook.md:93-112` → **rimossa**; resta la forma minima §2 + frase condizionale (E3).

### E5 — Guardie di asset
| Guardia | File | Ruolo post-feature |
|---|---|---|
| Parità + closure | `packages/sertor/tests/test_assets_copilot_parity.py` | esteso: closure su `sertor-cli-reference.md` (rag, Claude+Copilot) |
| Footgun / guide presence | `packages/sertor/tests/test_assets_cli_invocation.py` | rework: guida in E2, pointer nelle altre sedi, non-reintroduzione nei blocchi, copertura footgun su E2 |
| Sync dogfood↔bundle | `tests/unit/test_assets_sync.py` | invariato: copre `assets/claude/**`; `wiki-playbook.md` re-synced |
| Non-reintroduzione SDLC | `packages/sertor-flow/tests/...` | assert gemello: SDLC block senza «How to invoke» |

### E6 — Copie dogfood `.claude/`
`.claude/skills/wiki-author/wiki-playbook.md` re-sincronizzata via `python -m sertor_installer.sync`
(byte-parità). Gli altri asset toccati non sono sotto `assets/claude/**` → nessun re-sync.

## 2. Relazioni (closure dei pointer)

```
install rag ─┬─ MARKER_BLOCK  rag/claude-md-block-rag-usage.md ──cita──▶ sertor-cli-reference.md
             ├─ FILE          rag/skills/guided-setup/SKILL.md  ──cita──▶ sertor-cli-reference.md
             └─ FILE (NUOVO)  rag/sertor-cli-reference.md  ──▶ .sertor/sertor-cli-reference.md   (closure ✓)

install wiki ┬─ SharedEdit    claude-md-block.md (SERTOR:WIKI-RITUAL) ──cita──▶ wiki-playbook.md
             └─ FILE          claude/skills/wiki-author/wiki-playbook.md  (closure ✓)
                   └─ (frase condizionale senza filename verso il reference RAG → NO closure-check)

install governance ── MARKER_BLOCK  claude-md-block-sdlc.md  (nessun pointer di invocazione)
```

**Invariante di closure (NFR-5):** ogni pointer per nome con token di file risolve a un target
depositato dalla **stessa** capacità. Il `wiki-playbook` non cita il reference RAG per filename →
nessun pointer morto su install solo-wiki (REQ-007).

## 3. Validità / vincoli
- **VR-1 (Principio XI):** nessun import/modifica di `sertor_core`; l'unica modifica di codice è in
  `install_rag.py` (installer host-facing) per aggiungere l'`Artifact` E2 al piano RAG.
- **VR-2 (Principio X):** ogni body modificato/introdotto è host-agnostico (parità Claude↔Copilot,
  byte-copia del renderer Copilot invariata).
- **VR-3 (idempotenza/lifecycle):** E2 segue il pattern owned-file di `.sertor/` (create su install,
  update su upgrade, remove in blocco su uninstall). Nessun nuovo `ArtifactKind`/`WriteStrategy`.
- **VR-4 (fonte unica):** la sezione completa + Windows note esiste in **esattamente** E2.
