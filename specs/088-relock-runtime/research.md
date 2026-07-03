# Research — E15-FEAT-008 (re-lock runtime `.sertor/`)

Fase 0. Le due forche di design (Q1/Q2) dei requisiti sono qui risolte.

## D1 — Meccanismo di innesco (Q1)

**Decisione:** opzione **(a)** — script `scripts/dev/relock-runtime.ps1` invocato dal **rituale post-merge**
del flusso principale. Scelta dell'utente (2026-07-03).

**Rationale:** è l'unica opzione **dogfood-only per costruzione**. Lo script vive in `scripts/dev/` (come
`materialize-speckit.ps1`), che gli installer **non** bundlano → impossibile che leakki nell'hook distribuito
`rag-freshness.ps1`. Confine D↔N pulito: lo script è deterministico (il *come*), l'innesco è giudizio del
flusso principale al momento del merge (il *quando*). Non introduce un hook fragile in `settings.json` (b) né
carica l'hook host-facing con logica dogfood (c).

**Alternative scartate:**
- **(b) hook dogfood-only in `settings.json` (SessionEnd):** più automatico ma fragile — un futuro
  sync/re-install potrebbe non preservare l'entry locale, e va tenuto fuori dagli asset host-facing a mano.
- **(c) re-lock nell'hook distribuito, guardato «solo se runtime git-tracking»:** aumenta la superficie
  dell'hook host-facing per una necessità puramente dogfood → contro la direttiva «re-lock dogfood-only».

## D2 — Rilevamento cheap del «runtime indietro» (Q2)

**Decisione:** confronto tra il **commit lockato** e l'**HEAD remoto**:
1. Estrai lo SHA dal `.sertor/uv.lock` — riga `source = { git = "…Sertor.git#<SHA>" }` del package
   `sertor-core` (regex `Sertor\.git#([0-9a-f]+)`).
2. Confronta con `git rev-parse origin/master` (previo `git fetch origin master` per non leggere un ref
   stantio).
3. **Uguali → no-op** (nessun `uv sync`); **diversi o lock assente → re-lock** (`uv lock --upgrade-package
   sertor-core --project .sertor` + `uv sync --project .sertor`).

**Rationale:** il commit risolto è già registrato nel lock (verificato dal vivo: oggi `#2e8ce30…` mentre
`origin/master` è `879b688…` → 3 commit indietro). Il confronto è O(1): un `git rev-parse` + una lettura di
testo, nessuna risoluzione di dipendenze finché non serve (NFR-2). `git fetch origin master` è cheap (solo il
ramo, non tutto il remote) e necessario perché il re-lock pulla comunque dal remote (il dogfood segue
`origin/master`, non il working tree — vincolo dei requisiti).

**Alternative scartate:**
- **`uv lock --upgrade` incondizionato ad ogni evento:** viola NFR-2 (rete + risoluzione ad ogni chiamata
  anche quando già a HEAD).
- **Leggere la versione da `.sertor/.venv/…/dist-info`:** `sertor-core` ha `version = 0.1.0` fissa (non cambia
  fra commit) → non discrimina; lo SHA del lock sì.
- **`git ls-remote` invece di `fetch`+`rev-parse`:** equivalente in cheapness ma non aggiorna il ref locale
  che il rituale re-index/smoke potrebbe voler leggere; `fetch` è coerente col resto del rituale.

## D3 — Correzione del lock committato (auto-finding F1)

**Decisione:** `.sertor/uv.lock` → **gitignorato** + `git rm --cached` (untrack, resta su disco);
`.sertor/pyproject.toml` resta tracciato.

**Rationale:** con un runtime che re-locka ad ogni merge, un lock **tracciato** genera un diff ad ogni merge
(churn) e un potenziale loop (merge → re-lock → nuovo lock → commit → …). Il lock del dogfood è per natura
**locale e volatile** (sempre l'HEAD corrente); la spec **stabile** è `pyproject.toml` (dipendenza da
`git=<repo>` senza rev pin). Un clone fresco risolve HEAD via `uv sync` senza bisogno del lock committato
(SC-4). Coerente col modello `.gitignore` già usato per gli altri artefatti locali di `.sertor/`
(`.rag-health.json`, `.sertor-version`, `.venv`, `.index`).

## D4 — Fail-loud (Principio XII)

**Decisione:** lo script esce **non-zero con messaggio azionabile** se: `uv` non disponibile, progetto
`.sertor/` mancante (F1 non eseguita), `git fetch`/risoluzione falliscono (rete). Non lascia un
`.sertor/.venv` parziale spacciato per aggiornato: in caso di errore del `uv sync` lo segnala e ritorna il
codice d'errore, così il rituale post-merge non prosegue a re-index su un runtime rotto.

**Rationale:** Principio XII — la degradazione silenziosa è vietata; il fallimento del re-lock deve emergere
(il runtime resta all'ultimo lock valido, ma l'operatore lo sa).

## D5 — Confine dogfood↔distribuito, verificato da guardia

**Decisione:** una guardia di test verifica che lo script **non** compaia negli asset distribuiti
(`packages/**/assets/`) né sia referenziato dall'hook `rag-freshness.ps1`, e che il tracking del lock sia
corretto. Presence-agnostica e offline.

**Rationale:** rende il confine dogfood-only **enforced**, non solo documentato (lezione E10-FEAT-019: i
confini vanno blindati da una guardia, non affidati alla disciplina).
