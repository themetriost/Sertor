# Requisiti — Sync completo + guardie totali (asset-fidelity)

<!-- Deriva da: E15-FEAT-002 (epica fedelta-dogfood) -->

## 1. Contesto e problema (perché)

L'**asset-fidelity** del dogfood (avere gli stessi file-asset che un client riceve) oggi è **parziale e
disuniforme**, con **drift silenzioso** possibile:
- `python -m sertor_installer.sync` (`sertor_installer/sync.py`) copia **solo** `assets/claude/**` → `.claude/**`.
  Gli asset **RAG** (`assets/rag/**`: hook, skill eval/usabilità, agent `concierge`, `sertor-cli-reference.md`)
  **non sono coperti** — vengono copiati **a mano**.
- Le guardie byte coprono solo un sottoinsieme: `test_assets_sync` (claude+wiki) e `test_assets_rag_dogfood_sync`
  (**3 hook** RAG soli: `memory-capture`, `rag-freshness`, `version-check`). Tutti gli altri file-asset RAG
  (`rag-freshness-start.ps1`, `version-check-start.ps1`, `sertor-rag-usage-check.ps1`, skill `eval-*`,
  `guided-setup`, agent `concierge`, `sertor-cli-reference.md`) **non hanno guardia** → possono divergere dal
  bundle senza che la CI se ne accorga.

Questa feature chiude i **buchi dell'asset-fidelity**: sync a copertura completa dei file-asset distribuiti +
una guardia byte per **ognuno**. *(Nota di confine: gli asset che NON sono copie byte — merge `settings.json`,
generate `wiki.config.toml`, blocchi-marker in `CLAUDE.md` — sono **process-fidelity**, ambito di E15-FEAT-001,
non di questa feature.)*

## 2. Obiettivi e criteri di successo
- **O1.** Ogni file-asset distribuito che atterra come **copia byte** nel dogfood è **sincronizzato** dal
  meccanismo di sync (nessuna copia a mano).
- **O2.** Ogni file-asset distribuito ha una **guardia byte** dogfood↔bundle → 0 asset senza guardia.

**Criteri di successo (misurabili):**
- SC-1: `sertor_installer.sync` copre `assets/rag/**` (oltre a `assets/claude/**`); una modifica a un asset RAG
  bundlato si propaga al dogfood con un solo comando di sync.
- SC-2: esiste un test che **enumera** i file-asset byte-copiati e **fallisce** se anche uno solo non ha
  controparte dogfood byte-identica (guardia esaustiva, non a lista fissa).
- SC-3: 0 file-asset RAG byte-copiati privi di guardia (oggi: tutti tranne 3).
- SC-4: `sertor-core` invariato; nessun asset **distribuito** reso Sertor-specifico (Principio X).

## 3. Stakeholder e attori
- **Manutentore** che edita un asset bundlato → vuole un solo comando di sync e una guardia che colga il drift.
- **CI** → coglie qualunque divergenza asset dogfood↔bundle.

## 4. Ambito
### In ambito
- Estendere il meccanismo di sync (`sertor_installer.sync`) ai file-asset **RAG** byte-copiati.
- Una **guardia esaustiva** (auto-derivante dall'insieme degli asset, non a lista fissa) che pretende
  byte-identità dogfood↔bundle per **ogni** file-asset copiato.
### Fuori ambito
- Asset **non-byte** (merge settings, generate config, blocchi-marker) → process-fidelity, E15-FEAT-001.
- Portare artefatti RAG **oggi assenti** nel dogfood (rag-usage hook, concierge, ecc.) → E15-FEAT-003.
- Il sync della governance `sertor_flow` (blocco SDLC) → valutare in E15-FEAT-004/gov, non qui.
- Cambi a `sertor-core`.

## 5. Requisiti funzionali (EARS)
- **REQ-001 (Ubiquitous).** The sync mechanism shall propagate every byte-copied distributed file asset —
  `assets/claude/**` **and** `assets/rag/**` — from the bundle to the dogfood tree.
- **REQ-002 (Event-driven).** When a bundled byte-copied file asset is edited, running the sync command shall
  bring its dogfood counterpart byte-identical in one invocation.
- **REQ-003 (Ubiquitous).** A guard test shall assert byte-identity (modulo the documented allowlist, e.g.
  `uv run`) between **every** byte-copied distributed file asset and its dogfood counterpart.
- **REQ-004 (State-driven).** While the set of byte-copied file assets changes (asset added/removed), the guard
  shall stay exhaustive **without manual list edits** (it derives the set from the asset tree, not a hardcoded list).
- **REQ-005 (Unwanted behaviour).** If a byte-copied file asset has no dogfood counterpart (or diverges), then
  the guard shall fail naming the offending asset and the sync command to fix it.
- **REQ-006 (Ubiquitous).** The change shall leave `sertor-core` unmodified (Principle XI) and not embed
  host-specific assumptions in any distributed asset (Principle X).

## 6. Requisiti non funzionali
- **NFR-1 (esaustività auto-derivante):** la guardia non deve poter "dimenticare" un asset — deriva l'insieme
  dai file, così un asset nuovo è coperto automaticamente (lezione dell'attuale guardia a 3-hook fissi).
- **NFR-2 (offline/veloce):** guardia F.I.R.S.T., nessuna rete.
- **NFR-3 (allowlist esplicita):** le differenze legittime (es. `uv run` in sviluppo) restano in una allowlist
  documentata e centralizzata, non sparse.

## 7. Vincoli, assunzioni e dipendenze
- **Assunzione:** l'insieme "byte-copiato" è distinguibile per costruzione (FILE/`CREATE_IF_ABSENT` nel piano
  installer) dagli asset merge/generate/marker. La feature deve definire il confine in modo verificabile.
- **Dipendenza:** riusa/estende `sertor_installer.sync` e i pattern di `test_assets_sync.py` /
  `test_assets_rag_dogfood_sync.py` (non un secondo meccanismo).

## 8. Rischi
- **R-1:** includere per errore un asset non-byte (merge/generate) nella guardia byte → falsi fallimenti.
  *Mitigazione:* la guardia enumera solo la classe byte-copiata, definita in un punto unico.
- **R-2:** l'estensione del sync a `assets/rag/**` potrebbe rivelare **divergenze già esistenti** (asset RAG
  dogfood non allineati al bundle) → la guardia diventerebbe rossa. *Mitigazione:* atteso e voluto — è il
  drift silenzioso che vogliamo far emergere; riallineare come parte dell'implementazione (o promuovere a
  FEAT-003 se sono asset *mancanti*, non divergenti).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-003, REQ-004, REQ-005, REQ-006 (sync esteso + guardia esaustiva + confine + zero core).
- **Should:** REQ-002 (ergonomia un-comando).
- **Could:** —

## 10. Domande aperte
- **Q1 [design→plan]:** la guardia esaustiva enumera gli asset da `importlib.resources` sul package
  installer? E come marca in modo robusto la classe "byte-copiato" vs "merge/generate/marker" (una tabella
  unica già esiste nel piano installer — riusarla)?
- **Q2 [scope]:** il blocco SDLC di `sertor_flow` (non-sync oggi) entra qui o resta a FEAT-004? *(default: resta
  fuori — è governance `sertor_flow`, non `sertor_installer`.)*

---

**Commit proposto:** `docs(requirements): E15-FEAT-002 requisiti — sync completo + guardie asset-fidelity`
