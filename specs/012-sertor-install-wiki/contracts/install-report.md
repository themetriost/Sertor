# Contratto — `InstallReport` (FEAT-012)

**Branch**: `012-sertor-install-wiki` | **Spec**: [`../spec.md`](../spec.md) | **Data**: 2026-06-11

Contratto di osservabilità dell'operazione `sertor install wiki` (FR-006/025, REQ-143). È l'output
che US1/US2/US3 ispezionano e su cui un agente LLM (stakeholder §3) può fare scripting.

---

## Formato umano (default, su stdout)

Una riga di intestazione, una riga per artefatto, una riga di riepilogo:

```
sertor install wiki — target: /abs/path/to/host
  created  .claude/skills/wiki-author/SKILL.md
  created  .claude/skills/wiki-author/wiki-playbook.md
  …
  created  .claude/commands/wiki.md
  created  .claude/agents/wiki-curator.md
  created  .claude/hooks/wiki-pending-check.ps1
  merged   .claude/settings.json (+3 voci hook)
  block    CLAUDE.md (sezione step-ritual inserita)
  created  wiki.config.toml (language=en, source_dirs=src,docs)
  created  wiki/ (struttura: 6 cartelle, 2 file)
Riepilogo: 12 creati · 0 saltati · 1 merged · 1 block · 0 errori
```

**Esiti per artefatto** (allineati a `ArtifactOutcome`, data-model §4):
`created` · `skipped` · `merged` · `block` · `error`.

**Re-run (idempotenza, SC-003):** secondo run su install completa →

```
sertor install wiki — target: /abs/path/to/host
  skipped  .claude/skills/wiki-author/SKILL.md (già presente)
  …
  merged   .claude/settings.json (nessuna nuova voce)
  skipped  CLAUDE.md (blocco già presente)
  skipped  wiki.config.toml (già presente)
  skipped  wiki/ (struttura già presente)
Riepilogo: 0 creati · N saltati · 1 merged · 0 block · 0 errori
```

**Fallimento parziale (fail-fast, REQ-125):**

```
sertor install wiki — target: /abs/path/to/host
  created  .claude/skills/wiki-author/SKILL.md
  …
  error    .claude/settings.json — JSON malformato alla riga 7: Expecting ',' delimiter
Interrotto: 4 artefatti scritti, passo fallito = .claude/settings.json. Risolvi e riesegui.
```
(messaggio d'errore anche su **stderr**; exit 1)

## Formato JSON (`--json`, Could — D8)

Schema `install.report/1` (versionato come i contratti `wiki.*` del core):

```json
{
  "schema": "install.report/1",
  "target": "/abs/path/to/host",
  "outcomes": [
    {"target_rel": ".claude/skills/wiki-author/SKILL.md", "outcome": "created", "detail": null},
    {"target_rel": ".claude/settings.json", "outcome": "merged", "detail": "+3 voci hook"},
    {"target_rel": "CLAUDE.md", "outcome": "block", "detail": "sezione step-ritual inserita"},
    {"target_rel": "wiki/", "outcome": "created", "detail": "6 cartelle, 2 file"}
  ],
  "summary": {"created": 12, "skipped": 0, "merged": 1, "block": 1, "errors": 0},
  "failed_step": null
}
```

Errore di dominio: `errors > 0`, `failed_step` valorizzato, JSON comunque emesso su stdout +
messaggio su stderr (come `wiki_tools/__main__.py:184-189`).

## Garanzie verificabili (mappa SC)

| Garanzia | SC | Verifica |
|----------|----|----------|
| ogni artefatto compare con un esito | SC-001 | repo vuoto → tutti `created`, exit 0 |
| zero byte utente sovrascritti fuori dai blocchi | SC-002 | repo pre-popolato → fuori-marker di `CLAUDE.md` byte-identico; voci utente di `settings.json` tutte presenti |
| stesso stato al re-run | SC-003 | due run → secondo report tutto `skipped`/`merged(0)`; filesystem identico |
| zero riferimenti Sertor | SC-004 | scansione degli artefatti installati (whitelist: nomi-comando `sertor-rag`/`sertor-wiki-tools`) |
| zero LLM/rete | SC-005/006 | install gira senza rete; `[rag] enabled=false` |
