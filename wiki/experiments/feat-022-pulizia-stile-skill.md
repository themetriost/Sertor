---
title: FEAT-022 — Pulizia stile skill distribuite
type: experiment
tags: [debito-tecnico, igiene, host-facing, skill]
created: 2026-06-30
updated: 2026-06-30
sources: ["specs/080-pulizia-stile-skill/", "requirements/debito-tecnico/pulizia-stile-skill/requirements.md"]
---

# FEAT-022 — Pulizia stile skill distribuite

**Implementazione completata (2026-06-30):** E10-FEAT-022, epica `debito-tecnico` (ISSUE-08).

**Igiene host-facing, ZERO codice `sertor_core`, ZERO cambio semantico.**

## Cosa è stato fatto

Completamento SpecKit completo (specify→plan→tasks→implement, branch `080-pulizia-stile-skill`):

### Modifiche alle 5 skill distribuite

1. **`guided-setup` (E12-FEAT-002, sertor)**
   - ALL-CAPS → imperativo+why («ALWAYS CHECK CREDENTIALS» → «Verifica sempre le credenziali per evitare… »)
   - Rimozione sezione «Hard Boundaries / What NOT to do» (7 item, duplicati con regole inline)

2. **`eval-suite-author` (E5-FEAT-CUSTOM, sertor)**
   - Condensazione sezione «What NOT to do» (rimane 1 item unico, non riflettiamo il know-how di `evaluate`)
   - **Aggiunta pointer centralizzato** alla fonte unica «How to invoke»: ⟵ `sertor-cli-reference.md`

3. **`eval-feedback` (E5-FEAT-CUSTOM, sertor)**
   - Condensazione sezione «What NOT to do»
   - **Aggiunta pointer centralizzato** alla fonte unica

4. **`wiki-playbook.md` + sezione `ops/*` (sertor, wiki-author skill)**
   - Rimozione wikilink orfano `[[assistant-targeting]]` (asset distribuito NON linka il wiki interno Sertor → violava Principio X)
   - **Aggiunta `## Contents` ToC** (8 voci §0–§7, navigazione)
   - Condensazione sez. «Hard boundary» vs regole inline

5. **`requirements/SKILL.md` (sertor-flow governance)**
   - Solo ritocchi stile (lingua IT preservata, nessun cambio semantico)

### Guardie (anti-drift)

- **Nuova `test_assets_skill_style.py`** (sertor + sertor-flow): ALL-CAPS=0, zero orfani `[[wikilink]]`, pointer eval presenti, pin semantico (load-bearing invariato)
- **Estesa `test_assets_cli_invocation.py`**: copertura eval-suite-author, eval-feedback

### Risultati misurati

| Area | Linee | Delta |
|---|---|---|
| `guided-setup` | 133→110 | −23 (−17%) |
| `eval-suite-author` | 124→109 | −15 (−12%) |
| `eval-feedback` | ~90 | −3 (condensazione) |
| wiki-playbook | 293→~300 | +7 (ToC) |
| **Totale skill** | ~541→~519 | −22 (−4%) |

Riduzione proporzionale: focus, compattezza, ZERO perdita di significato.

## Confini rispettati

- **Host-agnosticità (Principio X):** pointer alla fonte unica `sertor-cli-reference.md` (asset di radice, non wiki), rimozione orfani
- **DRY (Principio III):** fattorizzazione source-reference da 3 locali a 1 canonico
- **Privacy/Semantica:** zero leak di nomi-assistente/slash-comandi/path-host nei body

## Verifiche

**SpecKit completo** (specify→requirements→plan→tasks→implement).

**Constitution Check:** PASS 12/12 + missione (host-agnosticità, fonte unica, confine D↔N preservati).

**Test suite:**
- `root`: 1131 verdi
- `sertor`: 473 verdi
- `sertor-flow`: 140 verdi
- `sertor-install-kit`: 139 verdi
- ruff: clean

**Commit storico:**
- requirements: `7aaea4c`
- spec: `55b1df3`
- plan: `5a8ed97`
- tasks: `2b792be`
- impl: in corso, branch `080-pulizia-stile-skill`

## Backlink

[[constitution]] · [[sertor-installer]] · [[assistant-targeting]] · [[step-ritual]] · [[feat-021-altitude-claude-md]] · [[feat-018-portabilita-os-hook]] · [[feat-019-fail-loud-hook-agent]]

## Durable entities distilled

Nessuna entità di dominio nuova (igiene, non architettura). Il lavoro riguarda la **forma** (linguaggio, DRY) e la **struttura** (ToC, pointer) delle skill già esistenti. La condensazione rende le skill **più leggibili e coerenti**, riducendo il carico cognitivo per i manutentori.

---

**Prossimi passi:** merge del branch `080` su `master` + prova LIVE ospite (installazione, verifica pointer canonico raggiungibile, stile percepito da utente).
