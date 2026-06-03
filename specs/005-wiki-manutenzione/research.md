# Phase 0 — Research: manutenzione del wiki

Decisioni tecniche per FEAT-007 (le DA-1..DA-8 sono già risolte nei requisiti; qui le traduco in design).

## R1 — Lint come analisi del grafo dei wikilink (LLM-free)
**Decisione.** `lint(root, expected=…)` scopre tutte le pagine `.md`, estrae i wikilink `[[name]]` con
una regex, costruisce l'insieme delle pagine e il grafo dei riferimenti, e deriva: **link rotti**
(target inesistente), **orfani** (pagina non in `index.md` né target di alcun wikilink; `index.md`/`log.md`
esenti — DA-5), **indice disallineato** (pagina su disco non nel catalogo), **coperture mancanti**
(set atteso configurabile), **contraddizioni** (pagine col marcatore inserito da FEAT-003).
**Razionale.** Deterministico, veloce (adatto al gate), nessun LLM. **Alternative.** LLM per orfani/
link: inutile e non deterministico → respinto.

## R2 — Report tipizzato + esito pass/fail (gate)
**Decisione.** `LintReport` (dataclass) con liste tipizzate di `Issue(kind, page, detail)` e una
proprietà `ok` (pass/fail). Reso anche come testo. L'operazione è non interattiva → l'esito guida un
**gate** (DA-8); l'aggancio a hook è design.
**Razionale.** REQ-052/053; consumabile da CI. **Alternative.** Solo stringa: non consumabile a
programma → respinto.

## R3 — Rigenerazione indice nel blocco tra marcatori (DA-1)
**Decisione.** `regenerate_index(root)` aggiorna **solo** il blocco tra `<!-- sertor:catalog -->` …
`<!-- /sertor:catalog -->` in `index.md` (link + sommario per pagina, ordinato → idempotente); se i
marcatori mancano, li introduce in modo non distruttivo (append). Tutto il resto resta intatto.
**Razionale.** Non-distruttività + idempotenza (REQ-010/011/012). **Alternative.** Riscrivere "## Pagine":
rischio di toccare il curato → respinto.

## R4 — Lint sola lettura + `--fix` opt-in (DA-4)
**Decisione.** `lint(...)` è sola lettura; `lint(..., fix=True)` applica **solo** fix sicuri/idempotenti
(= `regenerate_index`), **mai** auto-fix dei link. **Razionale.** REQ-005/006, Principio IV/VI.

## R5 — Distillazione documentale assistita/non distruttiva (DA-3)
**Decisione.** In `distill.py`, `distill_artifact(root, source, kind, title, llm, today)`: legge la
sorgente (artifact in `specs/`/`requirements/`/costituzione, o brief), l'LLM la sintetizza in una
pagina conforme con **backlink** alla fonte (in frontmatter `sources` + riga). **Non distruttiva**:
se la pagina esiste già **non** la sovrascrive (crea-se-assente); senza LLM → errore esplicito.
**Razionale.** REQ-030..033/060..065; idempotenza strutturale; rimanda-non-duplica (DA-W1).
**Alternative.** Rigenerare sempre: sovrascrive il curato → respinto.

## R6 — Coperture documentali su set atteso configurabile (DA-7)
**Decisione.** `expected` è una lista di **requisiti di copertura** (es. path di pagine attese o aree
tematiche: una pagina architettura in `syntheses/`, presenza di `concepts/`, una pagina per feature);
il lint segnala i mancanti. Default ragionevole, override via config/parametro.
**Razionale.** REQ-060/064; flessibile e testabile.

## R7 — Sorgenti = artifact + discussioni (DA estesa)
**Decisione.** La distillazione accetta come sorgente sia i file in `raw/` sia gli **artifact** del
repo (`requirements/**`, `specs/**`, `.specify/memory/constitution.md`); il backlink usa il path
relativo della fonte. **Razionale.** Ruolo "documentazione ufficiale" (REQ-061/062).

## Sintesi
Tutte le decisioni derivano da DA-1..DA-8 già risolte; nessun NEEDS CLARIFICATION residuo → Phase 1.
