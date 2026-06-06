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
| N1 | **record — contenuto** (sintetizzare il *perché*, scrivere la pagina) | REQ-010 | ☐ da fare | il *dove/come* (file, frontmatter, index, log) lo fa D |
| N2 | **distillazione** di sessione/conversazione → pagina | REQ-030/031 | ☐ da fare | richiede LLM configurato; input già pre-elaborato |
| N3 | **generazione** wiki (contenuto in linguaggio naturale, link concettuali) | FR-008 | ☐ da fare | momento (a) Karpathy; aggiornabile incrementalmente |
| N4 | **ingest — compile** (input esterno → pagine-concetto) | FR-030/031 (parte compile) | ☐ da fare | l'*import* in `ingested_sources/` lo fa D |
| N5 | **lint semantico** (contraddizioni, claim superati, coverage di senso) | FR-006 (parte semantica) | ◑ in corso | **metodo documentato (variante b, 2026-06-05):** procedura+tassonomia nel playbook (`lint` livello B), ground truth via git/RAG/test, host-agnostico, zero codice. **Esteso il 2026-06-06 (PR #16):** audit globale a 4 `kind` (wiki/requirements/spec/tracker) via `[[audit]]` in config; provato sull'intero repo (1 deriva ALTA corretta sulla pagina pycache). Deferito (c): probe deterministici in `wiki_tools` |
| N6 | **gerarchia di verità / autorità / obsolescenza** (giudizio) | FR-012..017 | ☐ da fare | la *rilevazione* dei segnali (mtime/git vs pagina) la fa D |
| N7 | **gate al commit** (decisione human-in-the-loop: blocca/avvisa/ignora) | FR-035..038, FR-041/042 | ☐ da fare | il *calcolo* dei segnali lo fa D |
| N8 | **orchestrazione agentica / trigger** (quando/come l'agente popola) | FR-001..005 | ☐ da fare | dipende dal contratto trigger portabile (FR-027, lato D) |

## Domanda aperta da chiudere insieme
- **FR-004 — trigger esatto del popolamento:** hook `Stop`/`SessionEnd`, comando `/wiki`, o entrambi?
  (emersa dal consolidamento, §13 del requisito). Da decidere prima di N8.

## Come la lavoriamo
Una operazione per volta, in dialogo: definiamo il comportamento (istruzioni in skill/playbook host-agnostici,
che leggono la config e chiamano `wiki_tools` per il meccanico), proviamo, aggiustiamo. Niente spec formale.
