---
title: Meccanica del log del wiki — FEAT-008
type: experiment
tags: [FEAT-008, wiki-tools, log, rotazione, append-log, migrate, speckit]
created: 2026-06-08
updated: 2026-06-08
sources: ["requirements/sertor-core/meccanica-log/requirements.md", "specs/008-meccanica-log/**", "src/sertor_core/wiki_tools/**"]
---

# Meccanica del log del wiki — FEAT-008

**Evento (2026-06-08).** Implementata via **flusso SpecKit completo** (requirements → specify → plan →
implement) la **meccanica del log** del nucleo [[wiki-tools]]: **rotazione** a un file per giorno, write-back
**`append_log` curato** esposto in CLI, e **`migrate`** una-tantum per splittare lo storico. Aperta la
**PR #18** (`spec/008-meccanica-log` → master); non ancora mergiata.

> Record datato: il *cosa è* (operazioni, contratti, rotazione) è distillato in [[wiki-tools]]; gli artefatti
> di processo vivono in `requirements/`/`specs/008-meccanica-log/` (citati, non ricopiati).

## Esito (al 2026-06-08)
- **Codice:** `src/sertor_core/wiki_tools/` (`profile`, `registry`, `scan`, `contracts`, `__main__`).
- **Test:** 22 unit verdi (rotazione, idempotenza sull'heading, parità `scan`, `migrate`, indice) + smoke CLI
  end-to-end. **Lint:** ruff pulito. **Constitution Check:** 10/10.
- **Contratti nuovi:** `wiki.append_log/1`, `wiki.migrate/1`; `wiki.scan/1` **invariato** (parità hook).

## Le decisioni che lo caratterizzano
- **Rotazione implicita**: nessun job periodico — la voce va nel file della sua data; senza `log_dir` vale la
  modalità a file unico (back-compat).
- **Confine deterministico↔giudizio preservato**: `append_log` riceve il **corpo curato** (log-craft) e ne fa
  solo il *piazzamento*, senza riformattarlo.
- **`migrate` non distruttivo e idempotente**: non cancella il log monolitico; rieseguito è no-op.

## Resta aperto (deliberatamente, post-merge)
- **Attivazione su Sertor**: `log_dir = "log"` in `wiki.config.toml` + `migrate` sul `wiki/log.md` reale —
  da fare **insieme** (attivare senza migrare renderebbe `scan` cieco).

---
**Cross-refs:** [[wiki-tools]] · [[deterministic-vs-judgment]] · [[architettura-wiki-llm]]
