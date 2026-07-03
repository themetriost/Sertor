# Feature Spec — Installer preservante su `plan-template.md`

- **Feature branch:** (nuovo) · **Deriva da:** E15-FEAT-005 ≡ E10-FEAT-028
- **Requisiti:** `requirements/fedelta-dogfood/plan-template-preservante/requirements.md`
- **Created:** 2026-07-03 · **Meccanismo scelto:** (a) **backup/restore** (decisione utente)

## Perché
`sertor-flow install` esegue `specify init --force` (Step 0) che **clobbera** `.specify/templates/plan-template.md`;
il file non è nel piano Sertor → la customizzazione (mission-gate) è persa. Prerequisito perché il dogfood
(e ospiti che customizzano il template) possano fare il vero install (modello E15). Verificato: è l'**unico**
artefatto curato clobberato (costituzione/`feature.json` salvi).

## User Scenarios & Testing
- **AS-1 (preserva):** *Given* un host con `plan-template.md` customizzato, *when* gira `sertor-flow install`,
  *then* dopo il run il file è **byte-identico** a prima (mission-gate preservato).
- **AS-2 (fresh, no regressione):** *Given* un host senza `plan-template.md`, *when* install, *then* resta
  quello depositato da `specify init` (upstream); nessun file inventato.
- **AS-3 (idempotente):** *Given* un host già installato, *when* re-install, *then* `plan-template.md` stabile.
- **AS-4 (fail-loud):** *Given* la preservazione non completabile, *when* install, *then* errore azionabile;
  **mai** lasciare il vanilla in silenzio (Principio XII).
- **AS-5:** `sertor-core` invariato.

> **Nota (verificato nel codice):** il `FakeSpecifyRunner` **già** scrive `plan-template.md`
> incondizionatamente nel suo layout (`conftest.py:72-75`) → **clobbera** il plan-template come il `--force`
> reale. È la **costituzione** a essere create-if-absent (fedele). Quindi il test è significativo col fake
> attuale, **senza** modifiche al fake.

## Meccanismo (a) — backup/restore (design di massima, dettaglio in plan)
In `execute_governance_plan`, **attorno** allo Step 0 (`launch_speckit`): se `.specify/templates/plan-template.md`
esiste, leggine il contenuto **prima**; esegui lo Step 0; **dopo**, se il backup esisteva, **ripristina** il
contenuto salvato (idempotente: se non è cambiato, no-op). Esito nel `InstallReport` (preservato/fresh).
Host-agnostico: nessuna fonte canonica, si preserva *ciò che c'era*.

## Requirements
REQ-001…006 in `plan-template-preservante/requirements.md`. Vincolanti per l'accettazione: preserva
l'esistente (REQ-001), host-agnostico (REQ-002), no-regressione fresh (REQ-003), idempotente (REQ-004),
fail-loud (REQ-005), zero core (REQ-006).

### Key Entities
- **`plan-template.md`:** artefatto `.specify/templates/`, clobberato da `specify init --force`. *(preservato
  by backup/restore se pre-esistente)*.
- **Backup in-memoria:** il contenuto pre-Step-0, ripristinato post-Step-0.

## Success Criteria
- SC-1: host con template customizzato → byte-identico post-install.
- SC-2: host fresh → template upstream (no regressione).
- SC-3: idempotente.
- SC-4: `sertor-core` invariato; modifica in `packages/sertor-flow`; suite + ruff verdi.
- SC-5: il test usa un fake **fedele** (clobbera il plan-template).

## Scope
**In:** backup/restore di `plan-template.md` attorno allo Step 0 in `sertor-flow install` (install+upgrade) +
fake fedele + test. **Out:** altri artefatti (non clobberati); distribuire un plan-template Sertor agli ospiti;
`specify init`/`sertor-core`.

## Note
- **Correzione (verificata nel codice):** il `FakeSpecifyRunner` **già clobbera** `plan-template.md`
  (`conftest.py:72-75`, write incondizionato nel layout); è la **costituzione** a essere create-if-absent.
  Quindi il fake è fedele al clobber del plan-template — **nessuna modifica al fake** necessaria (l'earlier
  claim opposto era mio errore, conflazione con la costituzione).
