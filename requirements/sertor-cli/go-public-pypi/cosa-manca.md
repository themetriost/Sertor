# Go-public — cosa manca davvero (guida operativa)

> **Cos'è questo file.** Una guida **operativa** allo stato del go-public: cosa è già fatto, cosa manca,
> in che ordine, e cosa serve **da te** (umano) perché io non posso farlo da solo. Non duplica i
> requisiti: quelli stanno in [`requirements.md`](requirements.md), qui c'è il *dove siamo e cosa
> facciamo adesso*.
>
> **Verificato il 2026-07-16** — ogni riga «stato» sotto è stata controllata sul campo, non ricordata.

---

## TL;DR

**Il go-public è già fatto per l'80%.** Il repo è pubblico, la release `v0.1.0` esiste, l'auto-updater
funziona, l'install esterno via `uvx` è provato. **Quello che manca è solo il canale PyPI** — cioè far sì
che `pip install sertor` funzioni.

**Il gate che bloccava tutto è caduto:** la CI è tornata verde il 2026-07-16 (era ferma per billing, si
credeva fino al 1° agosto). **Si può procedere ora.**

**Cosa serve da te:** una decisione su **come autenticarsi a PyPI** (vedi §3) — è l'unica cosa che
blocca. Tutto il resto è lavoro.

---

## 1. Stato reale — verificato, non ricordato

| Pezzo | Stato | Evidenza (2026-07-16) |
|---|---|---|
| Repo pubblico | ✅ **fatto** | `gh repo view` → `visibility: PUBLIC`, `isPrivate: false` |
| Audit segreti/history | ✅ **fatto** | 912 commit, 0 segreti, nessun rewrite necessario (2026-07-13) |
| Prima release `v0.1.0` | ✅ **fatta** | tag su `00dcd62`, *Latest*, 2026-07-13 |
| `/VERSION` | ✅ `0.1.0` | baseline, **mai bumpato** (by design, policy A-15) |
| Auto-updater vivo | ✅ **fatto** | GET `/VERSION` → **200** (era 404 da privato); 3 scenari validati live |
| Install esterno via `uvx` | ✅ **provato** | dal tag pubblico, fuori dal checkout, 85 pkg, exit 0 |
| Metadati dei 4 pacchetti | ✅ **release-ready** | `uv build` + `twine check` PASSED puliti (PR #183) |
| Nomi su PyPI | ✅ **liberi** | `sertor`, `sertor-core`, `sertor-install-kit`, `sertor-flow` → tutti **404** |
| **CI verde** | ✅ **SBLOCCATA** | PR #190/#191 → **8/8 SUCCESS** (Win+Ubuntu, py3.11/3.12) — **il gate «1° agosto» non vale più** |
| **Publish su PyPI** | ❌ **DA FARE** | nessun pacchetto pubblicato |
| **Workflow di release** | ❌ **ASSENTE** | `.github/workflows/` contiene **solo `ci.yml`** |
| **Credenziali PyPI** | ❌ **ASSENTI** | nessun token in env, nessun `~/.pypirc` |
| **Pip fallback reale** | ❌ **DA FARE** | `_apply_deps` è solo `uv` (deps non pubblicate → pip non le risolve) |
| Doc utente «install da PyPI» | ❌ **DA FARE** | oggi dichiara onestamente che pip non c'è |

---

## 2. Cosa manca, in ordine

### Passo 1 — Decidere l'autenticazione a PyPI ⛔ *blocca tutto, serve una tua decisione*

Vedi §3. Finché non è deciso, i passi 2-5 non partono.

### Passo 2 — Workflow di release in CI

Non esiste. Va creato (`.github/workflows/release.yml`): **tag → build → publish**.

Vincoli già decisi, da non perdere:
- **Pubblicare SOLO i 4 pacchetti** (`sertor`, `sertor-core`, `sertor-install-kit`, `sertor-flow`).
  **NON** `speclift`/`specaudit`: sono vendored, la loro casa è `sertor-flow` (E14-FEAT-002, decisione
  2026-07-14). ⚠️ **Attenzione:** `uv build --all-packages` builderebbe **anche** quelli → il workflow
  deve **selezionare** i 4 esplicitamente.
- Il publish gira **solo a CI verde** (SC-4): è il gate pre-merge esteso alla pubblicazione. Un artefatto
  irreversibile non esce da una suite rossa.

### Passo 3 — Il publish (irreversibile ⚠️)

Prima volta = i nomi vengono **occupati in modo permanente**. Una versione pubblicata **non si
ripubblica** e non si ritira davvero (`yank` la nasconde, non la cancella).

**Ordine consigliato:** publish su **TestPyPI** prima, install di prova da lì, poi PyPI vero.

### Passo 4 — Pip fallback reale (chiude il residuo E2-FEAT-010)

Oggi `_apply_deps` (`install_rag.py:689`) va **solo** con `uv`, e il messaggio quando `uv` manca dice
onestamente «pip non è ancora disponibile perché i nostri pacchetti non sono pubblicati». **Con le deps su
PyPI quella frase diventa falsa** → va implementato il ramo `pip` e aggiornato il messaggio. Il test
`test_clean_install_pip_sertor` (oggi xfail) diventa esigibile.

### Passo 5 — Bump `/VERSION` + doc

- **Bump** `/VERSION` (manuale, policy A-15) + nuova release → è ciò che **accende `behind`** in
  produzione. La `v0.1.0` è baseline: nessun host vedrà mai `behind` finché non c'è una seconda release.
- **Doc utente**: `docs/install.md` + quick-start → install da PyPI accanto a `git+url`; rimuovere la nota
  «pip non ancora disponibile». *(Regola standing: una modifica al setup non è done finché la doc utente
  non riflette il cambiamento — stesso step.)*

---

## 3. ⛔ La decisione che serve da te: come ci autentichiamo a PyPI

Non ho credenziali e **non devo averne**: è un segreto, e la scelta di dove passa è tua. Due strade.

### Opzione A — Trusted Publishing (OIDC) — **raccomandata**

GitHub Actions si autentica a PyPI via **OIDC**, senza alcun token da custodire.

- **Pro:** nessun segreto da creare, ruotare o revocare; niente token che possa finire in un log; è lo
  standard corrente di PyPI; già previsto in `requirements.md` (SC-4 «trusted publishing/OIDC preferito»).
- **Contro:** va configurato **a mano su pypi.org** (un publisher per pacchetto: repo + workflow +
  environment) prima del primo publish. **Quello devi farlo tu** — serve il login PyPI.
- **Nota:** funziona anche per pacchetti nuovi ("pending publisher"), quindi non serve un primo upload
  manuale col token.

### Opzione B — API token in GitHub Secrets

Crei un token su PyPI e lo metti in `Settings → Secrets → Actions`.

- **Pro:** più veloce da mettere in piedi se OIDC dà attrito.
- **Contro:** è un segreto vivo, va ruotato, e con scope sbagliato è troppo potente. Non passarmelo in
  chat: mettilo tu direttamente nei secrets di GitHub.

**Raccomandazione: A.** Il costo è una configurazione una-tantum su pypi.org; il beneficio è non avere
segreti in giro. Se preferisci B, procedo lo stesso — ma il token lo inserisci tu nei secrets, non me lo
scrivi qui.

---

## 4. Cosa NON è un motivo per rimandare

- **E10-FEAT-032** (hook duplicati su chi aggiorna) — **non blocca**. Colpisce il percorso di
  **aggiornamento** di chi ha già Sertor; chi arriva da `pip install` è per definizione **nuovo**, e sulle
  install nuove il bug non esiste. Il go-public non lo amplifica. *(Prima di verificarlo avevo
  raccomandato di aspettare: quella cautela è caduta con l'esito di Noetix.)*
- **E13 Fase 2 (marketing)** — **già sbloccata** dal repo pubblico, non aspetta PyPI. Procede in
  parallelo, epica sua.

## 5. Cosa invece è un rischio reale

- **L'irreversibilità.** Occupare i 4 nomi è definitivo. Se `sertor` su PyPI dovesse chiamarsi altro, si
  decide **prima**, non dopo.
- **Pubblicare `speclift`/`specaudit` per sbaglio** con un `--all-packages` distratto: sarebbero nomi
  occupati a nostro nome per pacchetti che **non vogliamo** distribuire così.
- **La finestra fra publish e pip-fallback.** Appena i pacchetti sono su PyPI, il messaggio «pip non è
  disponibile» diventa una **bugia** verso l'utente. Passi 3 e 4 vanno vicini, o la doc va aggiornata
  subito dopo il 3.

---

## 6. Il minimo per dire «go-public completo»

1. Trusted publishing configurato su pypi.org (**tu**).
2. `release.yml` che builda **i 4** e pubblica a tag, solo a CI verde.
3. Prova su TestPyPI → install pulito da fuori.
4. Publish reale → `pip install sertor` funziona da una macchina senza checkout.
5. Ramo `pip` in `_apply_deps` + messaggio uv-assente aggiornato (chiude FEAT-010).
6. Doc utente allineata.
7. Bump `/VERSION` + release → l'auto-updater accende `behind` sul serio.

**Traccia:** E2-FEAT-006 (PyPI) + residuo E2-FEAT-010 (pip fallback). Nessuno dei due è ancora passato da
`specify`/`plan`: i requisiti ci sono, il design no.
