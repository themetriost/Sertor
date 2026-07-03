# Feature Spec — Sync completo + guardie totali (asset-fidelity)

- **Feature branch:** `087-a05-dogfood-client-debt` (continuazione E15)
- **Deriva da:** E15-FEAT-002 (`requirements/fedelta-dogfood/sync-completo-guardie/requirements.md`)
- **Created:** 2026-07-03 · **Status:** Draft

## Perché
Chiudere i buchi dell'**asset-fidelity**: oggi `sertor_installer.sync` copre solo `assets/claude/**`, e solo
3 hook RAG hanno guardia byte → drift silenzioso su tutti gli altri file-asset RAG.

## Scoperta d'ancoraggio (che ridisegna lo scope)
`assets/rag/**` mescola **file byte-copiati** (→ `.claude/**`) e **asset non-byte** (env/mcp/settings/marker →
merge/generate, dominio process-fidelity **F1**). I file byte-copiati vanno a **dest multiple**:
`rag/hooks/*`→`.claude/hooks`, `rag/skills/*`→`.claude/skills`, `rag/agents/concierge.md`→`.claude/agents`
(`rag/sertor-cli-reference.md`→`.sertor/`, **gitignorato** → fuori dallo scope tracciato).
**Alcuni sono ASSENTI dal dogfood** (`sertor-rag-usage-check.ps1`, `guided-setup`, `concierge`): estendere il
sync e rieseguirlo **li crea** → **F2 assorbe F3** (per i soli file byte; il *wiring* `settings.json` della
rag-usage resta F1).

## User Scenarios & Testing
- **AS-1:** *Given* un asset RAG byte-copiato editato nel bundle, *when* si esegue il sync, *then* la
  controparte `.claude/**` diventa byte-identica in un comando.
- **AS-2:** *Given* la suite, *when* un file-asset byte-copiato (claude **o** rag) diverge o manca nel dogfood,
  *then* la **guardia esaustiva** fallisce nominando l'asset e il comando di fix.
- **AS-3:** *Given* si aggiunge/rimuove un file-asset byte-copiato, *when* gira la guardia, *then* è coperto
  **senza** editare una lista (deriva l'insieme dall'albero asset).
- **AS-4:** *Given* gli asset non-byte (env/mcp/settings/marker), *when* gira la guardia byte, *then* **non**
  sono inclusi (niente falsi fallimenti; sono F1).
- **AS-5:** dopo l'estensione+sync, gli asset RAG prima assenti (`sertor-rag-usage-check.ps1`, `guided-setup`,
  `concierge`) sono **presenti** e byte-identici nel dogfood. *(assorbe F3 per i file byte)*
- **AS-6:** `sertor-core` invariato; nessun asset distribuito reso Sertor-specifico.

## Requirements
REQ-001…006 in `requirements/sync-completo-guardie/requirements.md`. Sintesi vincolante: sync esteso ai
file-asset byte-copiati di `assets/rag/**` (hooks/skills/agents) + guardia **esaustiva auto-derivante**
dogfood↔bundle; confine byte vs non-byte esplicito e verificabile.

### Key Entities
- **File-asset byte-copiato:** asset che l'installer deposita come **copia identica** (FILE/CREATE_IF_ABSENT):
  `assets/claude/**` + `assets/rag/{hooks,skills,agents}/**`. *(stato: sincronizzati + guardati)*
- **Asset non-byte:** template/merge/marker (`rag/{env*,mcp*,settings*}`, `claude-md-block*`) → F1.
- **Guardia esaustiva:** test che deriva l'insieme byte-copiato dall'albero asset e pretende byte-identità.

## Success Criteria
- SC-1: sync copre `rag/{hooks,skills,agents}` oltre a `claude`.
- SC-2: guardia esaustiva (auto-derivante) → 0 file-asset byte-copiati senza copertura.
- SC-3: gli asset RAG prima assenti sono presenti nel dogfood (assorbe F3-file).
- SC-4: asset non-byte esclusi dalla guardia byte (0 falsi fallimenti).
- SC-5: `sertor-core` invariato; suite + ruff verdi.

## Scope
**In:** estensione `sertor_installer.sync` (mappe rag byte) + guardia esaustiva + popolamento asset mancanti
via sync. **Out:** asset non-byte/merge/marker (F1); `.sertor/`-dest (cli-reference, gitignorato → F4);
wiring `settings.json` della rag-usage (F1); governance `sertor_flow` (blocco SDLC); `sertor-core`.

## [NEEDS CLARIFICATION → plan]
- Come marcare in modo robusto il confine byte vs non-byte: enumerare i subtree byte per costruzione
  (`claude`, `rag/hooks`, `rag/skills`, `rag/agents`) è sufficiente e verificabile? *(default: sì — i non-byte
  vivono in `assets/rag/` root o come `*.tmpl`, mai nei 3 subtree byte).*
