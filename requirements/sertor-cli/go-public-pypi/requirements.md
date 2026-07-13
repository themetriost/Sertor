# Requisiti — Go-public: pubblicazione PyPI + prima release (passo gated a CI verde)

<!-- Deriva da: E2-FEAT-006 (PyPI, riclassificata Won't→planned il 2026-07-13) + la decisione utente
     "go-public" (2026-07-13), sequenza "repo public ora, PyPI a CI verde". Il repo è GIÀ pubblico
     (audit segreti CLEAN, 912 commit). Questo file copre il RESIDUO gated: publish PyPI + prima
     release + bump /VERSION + pip fallback reale. GATE: CI ferma per billing fino al 1° agosto 2026
     → il publish IRREVERSIBILE non si esegue senza CI verde. -->

## 1. Contesto e problema (perché)

Il repo `themetriost/Sertor` è **pubblico** dal 2026-07-13 (audit segreti/history CLEAN, nessun rewrite).
Restano i pezzi **irreversibili o gated** del go-public, tutti dipendenti dalla pubblicazione dei pacchetti
su un package index:

1. **PyPI publish** dei 4 pacchetti (`sertor`, `sertor-core`, `sertor-install-kit`, `sertor-flow`). È
   **IRREVERSIBILE** (una versione non si ripubblica; il nome è permanente) → richiede CI verde a copertura.
2. **Prima release** + **bump `/VERSION`** (oggi `0.1.0`, bump manuale A-15): attiva davvero l'auto-updater
   (`verdict=behind` quando l'installato è indietro; oggi resta `up-to-date` perché nessuna release è stata
   tagliata). Il fetch di `/VERSION` **già funziona** (200, verificato — repo pubblico).
3. **Pip fallback reale** (residuo E2-FEAT-010): oggi `_apply_deps` è solo `uv` perché `sertor-core`/
   `sertor-install-kit` sono membri workspace **non pubblicati** e pip non li risolve. **Con le deps su PyPI**
   il ramo `pip` diventa realizzabile.

**GATE assoluto:** la **CI di GitHub Actions è ferma per un problema di billing dell'account fino al 1° agosto
2026** (i runner non partono). Non si pubblica su PyPI (né si taglia una release) **senza CI verde** — è il
principio del gate pre-merge esteso alla pubblicazione: niente artefatto irreversibile senza la suite verde in CI.

## 2. Obiettivi e criteri di successo

- **O1 (installabilità pubblica).** Un utente terzo installa Sertor da **PyPI** (`uv pip install sertor` / `pip
  install sertor`) senza accesso al repo e senza `git+url`.
- **O2 (release tracciata).** Esiste una release taggata con `/VERSION` bumpato; l'auto-updater rileva
  `behind` su un'installazione più vecchia.
- **O3 (pip fallback reale).** `sertor install rag` funziona anche senza `uv` (ramo `pip`) risolvendo le deps
  pubblicate — chiude il residuo di FEAT-010.
- **O4 (sicurezza publish).** Nessun publish senza CI verde; credenziali PyPI mai in repo.

**Criteri di successo:**
- **SC-1:** i 4 pacchetti sono su PyPI a una versione ≥ `/VERSION`, installabili puliti (`uv`/`pip`) su
  macchina senza checkout.
- **SC-2:** `/VERSION` bumpato (SemVer) e una **GitHub Release** taggata; un dogfood/ospite a versione
  precedente riceve l'avviso `behind`.
- **SC-3:** `_apply_deps` ha un ramo `pip` che risolve `sertor-core`/`sertor-install-kit` da PyPI; il test
  `test_clean_install_pip_sertor` passa (xfail rimosso).
- **SC-4:** il publish gira **solo** a CI verde; token PyPI via secret CI (trusted publishing/OIDC preferito),
  mai in file tracciati.
- **SC-5:** `sertor-core` **INVARIATO** come libreria; le modifiche sono packaging/CLI/CI.

## 3. Ambito

### In ambito
- **Validazione packaging per PyPI**: nome disponibile (verifica `sertor` su PyPI), metadati completi
  (classifiers, `project.urls`, long-description = README), `uv build` dei 4 pacchetti, check `twine`/`uv
  publish --dry-run`.
- **Pipeline di publish in CI** (release workflow: tag → build → publish, trusted publishing OIDC se possibile).
- **Bump `/VERSION`** + **GitHub Release** (note da `CHANGELOG.md`).
- **Pip fallback reale** in `_apply_deps` (ramo `pip` quando `uv` assente; deps risolte da PyPI).
- **Aggiornamento doc utente** (`docs/install.md`/quick-start): install da PyPI accanto a `git+url`; rimozione
  della nota «pip non ancora disponibile» del messaggio uv-assente (FEAT-010).

### Fuori ambito
- **Marketing E13 Fase 2** (posizionamento/demo/landing): **già sbloccato** dal repo pubblico, epica E13 —
  non gated su PyPI, procede separatamente.
- Hardening supply-chain avanzato (signing/SLSA) oltre il trusted publishing: follow-up (Could).
- Modifiche a `sertor-core` come libreria.

## 4. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous).** The 4 packages shall be publishable to PyPI with complete metadata (name, version,
  license MIT, description, URLs) and install cleanly from PyPI with both `uv` and `pip`, without a repo checkout.
- **REQ-002 (Unwanted).** If CI is not green, then the publish workflow shall **not** publish to PyPI (no
  irreversible artifact without a green suite).
- **REQ-003 (Event-driven).** When a release is cut, `/VERSION` shall be bumped (SemVer) and a GitHub Release
  tagged, so the auto-updater reports `behind` to older installs.
- **REQ-004 (Optional).** Where `uv` is absent on the host, `install rag` shall install dependencies via `pip`
  from PyPI (real pip fallback), resolving `sertor-core`/`sertor-install-kit` as published packages.
- **REQ-005 (Unwanted).** If a PyPI credential is needed, then it shall be provided via CI secret / OIDC
  trusted publishing, never committed.
- **REQ-006 (Event-driven).** When PyPI install is available, the user documentation shall present it and the
  uv-absent message shall drop the «pip not yet available» caveat (FEAT-010 closure).

## 5. Vincoli, assunzioni, dipendenze

- **GATE CI-verde (billing → 1° ago 2026):** blocca REQ-002; nessun publish prima.
- **Nome PyPI:** assumere `sertor` disponibile — **da verificare** (se occupato, decidere un nome/namespace).
- **Licenza:** MIT già presente (FEAT-001 packaging) — compatibile con PyPI pubblico.
- **Dipendenza inversa:** il pip fallback (REQ-004) dipende dalle deps effettivamente su PyPI (REQ-001) → ordine.

## 6. Rischi

- **R-1 (publish irreversibile errato):** una versione sbagliata pubblicata non si ritira. *Mitigazione:*
  `--dry-run` + CI verde + trusted publishing con environment protetto.
- **R-2 (nome occupato):** `sertor` già preso su PyPI. *Mitigazione:* verifica precoce; piano B sul nome.
- **R-3 (pip fallback fragile):** risoluzione deps pip diversa da uv. *Mitigazione:* test d'integrazione clean-room.

## 7. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-003, REQ-005.
- **Should:** REQ-004 (pip fallback reale), REQ-006 (doc).
- **Could:** hardening supply-chain avanzato (signing/attestation).

## 8. Domande aperte

- **DA-1:** nome PyPI `sertor` disponibile? (verifica prima di tutto.)
- **DA-2:** trusted publishing OIDC vs token classico? *Raccomandazione:* OIDC (nessun segreto long-lived).
- **DA-3:** versione della prima release — restare `0.1.0` o `0.1.0`→`0.2.0`? (decidere al taglio, A-15 = manuale.)

---

**Prossimo passo:** al 1° ago (CI verde) → `specify`/`plan` di questo step, poi implement (packaging validation
→ release workflow → publish → pip fallback → doc). Fino ad allora resta **planned/gated**.
