# Contract — verifica di process-fidelity (Phase 1)

Il «contratto» esterno di questa feature non è un'API: è la **procedura d'install** (runbook in
`quickstart.md`) più le **verifiche** che ne provano gli esiti. Qui il contratto delle verifiche.

## C1 — Guardie byte (esistenti, ruolo ri-orientato)

**Contratto:** dopo il self-install sul dogfood, per **ogni** asset host-facing byte-copiato, la copia nel
dogfood (`.claude/**`) è **byte-identica** al bundle canonico (`assets/**`). Valutato **sull'esito del
processo reale**, non del sync.

- **Vincolo EOL:** confronto LF↔LF (bundle e dogfood entrambi normalizzati a LF — D1).
- **Guardie:** `tests/unit/test_assets_sync.py`, `tests/unit/test_assets_rag_dogfood_sync.py`,
  `packages/sertor-flow/tests/unit/test_assets_sync.py`. **MUST** restare verdi.
- **Test negativo:** introdurre un drift artificiale in un asset → la guardia **MUST** fallire (SC-4).

## C2 — Idempotenza (NUOVO test / procedura, NFR-1)

**Contratto:** eseguire i 3 installer due volte di fila lascia lo stato **stabile**.

- **Prima esecuzione:** deposita/aggiorna gli asset; `git diff` mostra il residuo reale (asset nuovi +
  blocchi + wiring).
- **Seconda esecuzione (a diff committato o stashato):** **0** nuovi cambiamenti distruttivi — asset
  `skipped`, blocchi non ri-inseriti (replace-if-marker), curati preservati. Un eventuale superset è
  **dichiarato**, la perdita silenziosa è vietata.
- **Verifica:** `git status --porcelain` dopo il secondo giro = vuoto (o solo superset dichiarato).

## C3 — No-churn EOL (NUOVO test `tests/unit/test_asset_install_eol.py`, SC-2)

**Contratto:** la policy `.gitattributes` rende il repo EOL-consistente e azzera il churn da line-ending.

- `git ls-files --eol` **MUST NOT** mostrare mix `crlf`/`lf` sui file testuali versionati (a meno di
  eccezioni dichiarate in `.gitattributes`, es. `*.ps1` se scelto CRLF — da fissare in tasks).
- Ri-scrivere un file testuale via installer **MUST** produrre 0 righe-diff spurie da EOL.
- Il test asserisce l'attributo `eol=lf` effettivo sui path chiave (`CLAUDE.md`, `.claude/**`, `assets/**`).

## C4 — Single-coverage `CLAUDE.md` (SC-3)

**Contratto:** ogni tema di governance è coperto una sola volta.

- Conteggio marker: ogni coppia `SERTOR:*-RITUAL`/`RAG-USAGE` compare **una** volta (start+end).
- Nessun paragrafo di prosa duplica pura il contenuto del blocco che convive (verifica di riconciliazione,
  D3) — controllo qualitativo su branch, non un assert meccanico.
- Ri-install: i blocchi non si moltiplicano (garantito da `write_marker_block`).

## C5 — Core invariato + gate pre-merge (SC-5/SC-7)

**Contratto:**
- `git diff --stat src/sertor_core/` = **vuoto** (Principio XI).
- Nessun asset **distribuito** (`assets/**`, template) reso Sertor-specifico (Principio X): le uniche
  modifiche distribuite sono generiche (`.gitattributes`, rotazione `wiki/log/`).
- **Gate E15-FEAT-008:** `uv run pytest -m "not cloud"` **e** `uv run ruff check .` **verdi** prima del
  merge (non ci si fida di run mirati).

## Mappa contratto → criteri di successo

| Contratto | Copre |
|-----------|-------|
| C1 | SC-2 (fidelity byte), SC-4 (guardia loud) |
| C2 | SC-1, SC-4 (idempotenza), NFR-1 |
| C3 | SC-2 (no-churn) |
| C4 | SC-3 (single-coverage) |
| C5 | SC-5, SC-7 (core invariato, gate) |
