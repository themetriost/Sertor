# FEAT-003-N — Operazioni wiki assistite da LLM (host-agnostiche) — TODO collaborativo

> **Traccia non-SpecKit.** Questa è la metà *di giudizio* del refactor host-agnostico del Wiki (l'altra metà,
> deterministica, è **FEAT-003-D** → SpecKit). Qui non si specifica a morte: sono comportamenti agentici/LLM, li
> affrontiamo **passo-passo insieme**. Questo file è il tracker vivo (aggiornato man mano).
>
> **Confine:** ciò che richiede *giudizio* (cosa scrivere, è davvero obsoleto?, è una contraddizione?) sta qui;
> il *meccanico* (dove/come scrivere, parsing, scan, link rotti) sta in FEAT-003-D.
>
> Fonte requisiti: `../wiki-creazione/requirements.md` (consolidato FEAT-003 ⊕ FEAT-010). Vincolo trasversale:
> **Principio X** (host-agnostico — nessuna assunzione dell'ospite hardcoded; tutto ciò che varia va in config).
> Riusa il nucleo deterministico **FEAT-003-D** (`wiki_tools`) per il bookkeeping (DRY, FR-002).

## Ponte D→N — FATTO (2026-06-05)

Step 0, prerequisito a N1-N8: il layer agentico (playbook + skill + comando + agente) è stato reso
**host-agnostico** (legge `wiki.config.toml`, Principio X) e **poggiato sulla CLI `sertor-wiki-tools`**
per il meccanico; all'LLM resta il giudizio. Rename coerente: skill `genera-wiki`→`wiki-author`,
playbook→`wiki-playbook.md`, agente `wiki-keeper`→`wiki-curator` (+`Bash`), comando `/wiki` invariato.
Scope leggero (zero codice). Dettagli + confine D↔N: `wiki/syntheses/ponte-d-n-host-agnostico.md`.
**Deferito (scope "completo"):** esporre i write-back (`append_log`/`upsert_index`) in CLI + riconciliare
identità/formato dell'index curato → sblocca l'offload totale di `record`.

## Stato delle operazioni

| # | Operazione (giudizio LLM) | Requisiti | Stato | Note |
|---|---|---|---|---|
| N1 | **record — contenuto** (sintetizzare il *perché*, scrivere la pagina) | REQ-010 | ◑ in corso | il *dove/come* (file, frontmatter, index, log) lo fa D. **Metodo documentato (2026-06-07):** page-craft in una **pagina-foglia** dedicata `.claude/skills/wiki-author/page-craft.md` (atomicità · auto-contenimento · link · livello di significato: distilla-non-trascrivi/perché+alternative/astrazione per area/verità ancorata/densità + esempio male→bene), **linkata da** `record`/`ingest`/`query`/lint C/`reorg` — estratta dal playbook §4 per evitare la dipendenza circolare playbook↔modulo. **Ampliata (2026-06-07)** all'anatomia completa: struttura della pagina (titolo/lead/TOC/sezioni/vedi-anche/fonti/metadati) · tipo di contenuti (piramide rovesciata, concreto, non-ridondante) · tipo di link (contestuali inline vs navigazione vs esterni) · checklist; reso host-agnostico (TOC/stato/owner/redirect/gerarchie = dipendono da host/config). Resta: esercitarlo e (se utile) la distillazione N2 |
| N2 | **distillazione** di sessione/conversazione → pagina | REQ-030/031 | ☐ da fare | richiede LLM configurato; input già pre-elaborato |
| N3 | **generazione** wiki (contenuto in linguaggio naturale, link concettuali) | FR-008 | ☐ da fare | momento (a) Karpathy; aggiornabile incrementalmente |
| N4 | **ingest** (fonte esterna → **riassunto in `sources/`** + integrazione nei concetti) | REQ-020..023 (Gruppo C riattivato) | ☐ da fare | **2026-06-09 (D-18):** rimosse `ingested_sources/`/`manual_edited/`; ingest torna alla semantica Karpathy (riassunto in `sources/`), niente separazione import≠compile |
| N5 | **lint semantico** (contraddizioni, claim superati, coverage di senso) | FR-006 (parte semantica) | ◑ in corso | **metodo documentato (variante b, 2026-06-05):** procedura+tassonomia nel playbook (`lint` livello B), ground truth via git/RAG/test, host-agnostico, zero codice. **Esteso il 2026-06-06 (PR #16):** audit globale a 4 `kind` (wiki/requirements/spec/tracker) via `[[audit]]` in config; provato sull'intero repo (1 deriva ALTA corretta sulla pagina pycache). Deferito (c): probe deterministici in `wiki_tools` |
| N6 | **gerarchia di verità / autorità / obsolescenza** (giudizio) | FR-012..017 | ☐ da fare | la *rilevazione* dei segnali (mtime/git vs pagina) la fa D |
| N7 | ~~**gate al commit**~~ | ~~FR-041/042~~ | ⛔ **DELETED BY DESIGN (2026-06-09, D-20)** | Gate-che-blocca-il-commit eliminato (incoerente col trigger manuale post-commit). Lint/freschezza restano come report non bloccante di `/wiki` (resta in N5/N9) |
| N8 | **orchestrazione agentica / trigger** (quando/come l'agente popola) | FR-001..005 | ✅ **COMPLETA come procedura (2026-06-09)** | Trigger deciso = comando manuale `/wiki` (D-19); l'operazione che popola dalle modifiche è **`generate-from-diff`** (`ops/generate-from-diff.md`): scan/diff [D, git delegato] → aggiorna solo le pagine impattate [N] → index + voce di log [D]. **Nessun codice nuovo**: è una procedura guidata dal flusso principale. Automazione non presidiata (`claude -p`) fuori scope (D-19) |
| N9 | **lint organizzativo + reorg** (collocazione per natura, atomicità, coerenza `type`↔natura, disciplina link inline/backlink) | FR-035..038 (manutenzione, D-14); → FEAT-007 | ◑ in corso | **terza categoria di deriva** oltre igiene (A) e claim (B): l'*organizzazione*. Tutto **giudizio** — natura/collocazione non sono deterministiche (cartella e `type` concordano ma mentono sul contenuto). **Metodo documentato (2026-06-06):** `lint` livello C + op `reorg` nel playbook; detection via `collect` + backlink calcolati, apply su conferma via `Read`/`Edit`. Backlog (c): helper deterministico `move`-con-link in `wiki_tools`. Nota: **nessun FR esplicito** su organizzazione/refactoring in `../wiki-creazione/requirements.md` → agganciato a FR-035..038/FEAT-007 |

## Domanda aperta da chiudere insieme
- ✅ **FR-004 — trigger del popolamento: RISOLTA (2026-06-09, D-19)** — comando manuale `/wiki`, ambito =
  changeset dell'ultimo commit (`git diff HEAD~1`); scartati hook automatico e `claude -p` headless.

## Come la lavoriamo
Una operazione per volta, in dialogo: definiamo il comportamento (istruzioni in skill/playbook host-agnostici,
che leggono la config e chiamano `wiki_tools` per il meccanico), proviamo, aggiustiamo. Niente spec formale.
