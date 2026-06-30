# Phase 0 — Research: Rimozione stub `assets/copilot/` (E10-FEAT-023)

**Branch**: `081-stub-copilot` · **Spec**: [spec.md](./spec.md) · **Requirements**:
`requirements/debito-tecnico/stub-copilot/requirements.md`

La feature è **sottrattiva / igiene host-facing**: rimuove il tree
`packages/sertor/src/sertor_installer/assets/copilot/**` (4 `.gitkeep` + 4 directory vuote
`agents/`/`hooks/`/`instructions/`/`prompts/` + `copilot/` stessa). La decisione di scope (Opzione A —
rimozione, niente README di rimpiazzo) è **già fissata** nella spec. Restano due **forche di *come***
(DA-D-1, DA-D-2) e una verifica di sicurezza pre-rimozione (zero consumatori). Nessun ignoto resta
`NEEDS CLARIFICATION`.

---

## R-0 — Verifica zero-consumatori (FR-005 / A-001) — RICONFERMATA

**Domanda.** Esiste qualche modulo Python (codice o test) che legge un percorso rooted a `copilot/`
sotto gli asset (`iter_asset_dir("copilot/...")` / `read_asset_text("copilot/...")` /
`asset_path("copilot/...")`)?

**Metodo.** Grep esaustivo sul repo (pattern su `assets/copilot`, `copilot/{agents,hooks,instructions,
prompts}`, `read_asset_text("copilot`, `iter_asset_dir("copilot`) ristretto a `*.py`.

**Esito.** **Zero consumatori.** L'unica occorrenza è un **commento di documentazione** in
`packages/sertor/tests/test_assets_copilot_guard.py:79` («there is no `copilot/instructions/*.md` body
to drift from it») — testo, non una lettura. Confermato anche dal flusso di generazione Copilot:
`build_rag_plan(COPILOT_CLI)` produce gli artefatti via `render_copilot_hooks` /
`render_custom_agent` / `render_prompt_file` (`sertor_install_kit.surfaces`, riesportate in
`sertor_installer.surfaces`) e byte-copy da `assets/claude/**` e `assets/rag/**`
(`install_rag.py:126-244`). Nessun ramo legge `assets/copilot/`.

**Decisione.** La rimozione **procede senza modifiche al codice Python**. FR-005 resta una clausola di
salvaguardia: la grep va **ripetuta all'implementazione** (un consumatore introdotto tra ora e il merge
sarebbe colto sia dalla grep sia dalla suite verde, US5).

**Rationale.** Conferma diretta sul repo, non inferenza. Allinea A-001/A-002 con la realtà su `master`.

**Alternative.** Nessuna — è un controllo di fatto, non una scelta di design.

---

## R-1 (DA-D-1) — Forma della guardia anti-ricomparsa

**Domanda.** La guardia che fallisce se `assets/copilot/` riappare deve essere un **test nuovo
dedicato** o un'**estensione di `test_assets_copilot_guard.py`**?

**Opzioni.**
- **A — Estensione di `test_assets_copilot_guard.py` (RACCOMANDATA).** Aggiungere un test
  `test_no_copilot_asset_directory` nel file che **già** è la guardia anti-drift degli asset
  Copilot-derivati e che **già documenta** (commento a `:75-83`) che nessun body deve risiedere sotto
  `copilot/`. Il nuovo test asserisce l'**assenza della directory** (`asset_path("copilot").is_dir()
  is False`), usando l'API esistente `sertor_installer.resources.asset_path` (anchor già bindato a
  `sertor_installer`, `resources.py:18`).
- **B — File di test nuovo dedicato.** Un modulo separato (es. `test_no_copilot_asset_stub.py`) con la
  sola asserzione di assenza directory.

**Decisione: Opzione A — estensione.** Il file `test_assets_copilot_guard.py` è la **casa concettuale**
della famiglia di guardie sugli asset Copilot: la sua docstring già afferma l'architettura generativa e
il vincolo «nessun body sotto `copilot/`». Asserire ora anche l'**assenza dell'intera dir** completa lo
stesso invariante nello stesso punto, dove un manutentore lo cerca. Un file separato frammenterebbe la
guardia in due luoghi senza valore aggiunto (YAGNI, Principio III).

**Forma del test (contratto in [contracts/guard-anti-reappearance.md](./contracts/guard-anti-reappearance.md)).**
```python
def test_no_copilot_asset_directory():
    """E10-FEAT-023: no static Copilot asset tree — Copilot payloads are GENERATED at runtime."""
    from sertor_installer.resources import asset_path
    assert not asset_path("copilot").is_dir()
```
`asset_path("copilot")` ritorna un `Traversable` per `sertor_installer/assets/copilot`; su una dir
inesistente `.is_dir()` è `False` → la guardia **passa** allo stato corretto e **fallisce** (rosso) se
un futuro contributor ricrea `assets/copilot/<x>/.gitkeep` (la dir tornerebbe a esistere).

**Rationale.** Coesione (una sola casa per le guardie Copilot), riuso dell'API asset esistente
(`asset_path`, nessuna dipendenza nuova), asserzione minimale e deterministica (offline, niente
`uv`/rete — parità con la suite esistente). È **additiva e leggera** come richiesto da CS-3/US6.

**Alternative scartate.** (B) file nuovo = frammentazione senza beneficio. Una guardia *CI-enforced*
oltre il test pytest = **fuori ambito** (R-2 requirements: «non necessaria»; eventuale promozione a
FEAT-024).

---

## R-2 (DA-D-2) — Commento esplicativo in `install_rag.py`

**Domanda.** Conviene aggiungere, vicino alla generazione Copilot, un commento del tipo «There is no
static Copilot asset directory: all Copilot-facing artefacts are generated from claude/** and rag/**
sources» per prevenire la ricomparsa (R-2)?

**Decisione: NO — non aggiungere il commento.** Due ragioni convergenti:
1. **Coerenza con l'out-of-scope dichiarato.** La spec elenca esplicitamente «il codice di
   `install_rag.py` … invariato» tra i Fuori ambito (RNF-1/NFR-4): toccarlo, anche per un commento,
   incrina l'invariante «zero modifiche al codice Python di runtime» (US3.3, FR-005). La feature resta
   così *puramente sottrattiva*.
2. **Ridondanza col segnale durevole.** L'architettura generativa è **già documentata** in più punti di
   `install_rag.py` (es. `_COPILOT_RAG_WIRING_SENTINEL`, `install_rag.py:128-130`: «the Copilot
   PreToolUse wiring is GENERATED natively») e ora **asserita ed enforced** dal nuovo test della guardia
   (R-1). Un commento libero aggiuntivo può **divergere** nel tempo (un commento non è verificato),
   mentre il test **fallisce** se la realtà cambia — è il segnale fail-loud preferibile (Principio XII).

**Dove vive l'intento.** Nella **docstring del nuovo test** (e nel suo messaggio di asserzione): è il
punto enforced, non-driftabile, che un manutentore incontra cercando «perché non c'è `copilot/`».

**Rationale.** Massimizza il segnale (test verificato) e minimizza la superficie modificata (zero
codice runtime), in linea con la natura sottrattiva della feature.

**Alternative.** Aggiungere il commento = valore marginale, rischio di drift, viola l'out-of-scope.
Scartata.

---

## R-3 — Packaging / hatchling (FR-006 / A-002) — CONFERMATA

**Domanda.** La rimozione dei `.gitkeep` e delle dir vuote richiede modifiche a
`packages/sertor/pyproject.toml`?

**Esito.** **No.** Hatchling include il package per glob ricorsivo (`packages =
["src/sertor_installer"]`), non per lista esplicita di file. Rimuovere file e dir vuote sotto
`assets/copilot/` non altera l'insieme dei file da includere nel wheel (i `.gitkeep` non sono mai
elencati né letti). `uv build -p sertor` deve restare verde e il test
`tests/integration/test_packaging.py` non deve regredire.

**Decisione.** Nessuna modifica a `pyproject.toml`. Verifica = `uv build -p sertor` + packaging test
(passo del piano, vedi quickstart).

**Alternative.** Nessuna.

---

## R-4 — Estensioni / debiti promossi (tracciamento durevole)

Coerente con la regola «gli Out-of-Scope si promuovono, non restano appesi». I rinvii reali sono **già**
in casa durevole nel backlog d'epica (spec §Tracciamento dello scope):
- **Budget altitude in CI** (gate file-skill > N righe) → **FEAT-024**.
- **Parity guard esteso a `.ps1`/`.json`** → **FEAT-024**.
- **Riconciliazione fork IT eval-skill** → **FEAT-025**.
- **Portabilità OS degli hook** → **FEAT-018** (già completata).
- **Guardia CI (oltre il test pytest) contro la ricreazione di `assets/copilot/`** → eventuale
  **FEAT-024** se dovesse diventare CI-enforced; non necessaria qui (R-2 requirements).
- **Documentazione editoriale** dell'architettura generativa Copilot in `docs/`/`wiki/` → intervento
  autonomo separato, fuori da questa feature di igiene.

Nessun rinvio reale resta sepolto in `specs/`.

---

## Sintesi delle decisioni

| ID | Forca | Decisione |
|----|-------|-----------|
| R-0 | Zero consumatori | **Confermato zero** → rimozione senza modifiche Python; grep ripetuta all'implementazione |
| R-1 (DA-D-1) | Forma guardia | **Estensione** di `test_assets_copilot_guard.py` (`test_no_copilot_asset_directory`, assenza dir via `asset_path`) |
| R-2 (DA-D-2) | Commento in `install_rag.py` | **No** — viola out-of-scope «install_rag.py invariato»; l'intento vive nella docstring del test (enforced) |
| R-3 | Packaging | **Nessuna** modifica a `pyproject.toml`; `uv build` + packaging test verdi |
| R-4 | Debiti | Promossi a FEAT-024/FEAT-025/intervento editoriale (già nel backlog) |
