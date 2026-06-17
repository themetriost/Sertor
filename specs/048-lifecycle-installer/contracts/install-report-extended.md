# Contratto — `install.report/1` esteso (outcome `updated`/`removed`)

**Feature**: `048-lifecycle-installer` (FEAT-008) | Estende il contratto esistente reso da
`InstallReport.render_json()` (`packages/sertor-install-kit/src/sertor_install_kit/report.py`).

**Schema id**: `install.report/1` (INVARIATO — additivo, retrocompatibile; **NON** un secondo schema,
NFR-06). I consumer esistenti che leggono il report d'install continuano a funzionare ignorando le
chiavi nuove.

---

## Forma JSON

```json
{
  "schema": "install.report/1",
  "target": "C:/host/project",
  "assistant": "claude",
  "outcomes": [
    { "target_rel": ".sertor", "outcome": "removed", "detail": "isolated runtime" },
    { "target_rel": "CLAUDE.md", "outcome": "removed", "detail": "SERTOR:RAG-USAGE block stripped" },
    { "target_rel": ".gitignore", "outcome": "skipped", "detail": "no Sertor lines" }
  ],
  "summary": {
    "created": 0,
    "skipped": 1,
    "merged": 0,
    "block": 0,
    "updated": 0,
    "removed": 2,
    "errors": 0
  },
  "failed_step": null
}
```

### Differenze rispetto al report d'install

| Campo | Cambiamento |
|-------|-------------|
| `outcomes[].outcome` | dominio esteso: oltre a `created`/`skipped`/`merged`/`block`/`error`, ammette `updated` e `removed` |
| `summary.updated` | **NUOVO** intero ≥ 0 — n. asset/blocchi aggiornati (upgrade) |
| `summary.removed` | **NUOVO** intero ≥ 0 — n. artefatti rimossi/de-registrati (uninstall, obsoleti) |
| tutto il resto | INVARIATO (`schema`, `target`, `assistant`, `failed_step`, gli altri contatori) |

---

## Invarianti del contratto

1. `schema == "install.report/1"` per install **e** upgrade/uninstall (un solo schema).
2. `summary` contiene **tutte** le 7 chiavi-conteggio (`created`, `skipped`, `merged`, `block`,
   `updated`, `removed`, `errors`), ognuna `>= 0`. Le due nuove valgono `0` nei report d'install
   (retrocompat).
3. `len(outcomes)` == somma dei 7 conteggi (ogni outcome contribuisce a esattamente un contatore).
4. `failed_step` è `null` salvo errore di dominio (fail-fast no-rollback); in tal caso è il
   `target_rel` del primo artefatto fallito e `errors >= 1`.
5. **Nessun segreto** in `outcomes[].detail` né altrove (FR-053): i `detail` descrivono l'azione
   (es. "isolated runtime", "block stripped", "+server sertor-rag"), mai contenuto di file rimossi.
6. `exit_code`: `0` se `errors == 0` (anche con tutto `skipped`/`removed`); `1` se `errors >= 1`;
   `2` su usage error (non produce report JSON — è errore argparse).

---

## Rendering umano (informativo)

```text
sertor uninstall rag — target: C:/host/project — assistant: claude
  removed  .sertor (isolated runtime)
  removed  CLAUDE.md (SERTOR:RAG-USAGE block stripped)
  skipped  .gitignore (no Sertor lines)
Summary: 0 created · 1 skipped · 0 merged · 0 block · 0 updated · 2 removed · 0 errors
```

In caso di errore l'ultima riga è `Aborted: failed step = <target_rel>. Fix it and re-run.`
(invariato rispetto all'install).
