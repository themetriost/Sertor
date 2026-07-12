# Quickstart — verifica di accettazione (097-rituale-anti-skip)

Come verificare la feature. Il tool è deterministico → verificabile con unit test su fixture (wiki + repo
git temporaneo), più un giro dogfood reale.

## 1. Scoperta distill deterministica (SC-001, US1)

- **Unit (positivo):** fixture wiki con 2 pagine changed che si linkano a vicenda con ≥2 nuovi backlink e 0
  nuove pagine `concepts/`/`tech/` → `ritual-check` le elenca come `distill_candidate`.
- **Unit (negativo):** stato che non soddisfa l'euristica → **0** candidati spuri.
- **Sola lettura / no LLM:** il tool non modifica alcuna pagina e non importa alcun provider/LLM (SC-003).

## 2. Segnali di drift (SC-001, US3)

- **`stale-updated`:** pagina changed con `updated:` più vecchio della modifica git → compare tra i
  `drift_candidate`.
- **`neighbor-of-change`:** pagina linkata da una pagina changed ma non changed → compare.
- **`capability-exec` (config):** con `[ritual].capability_globs`+`exec_page` in `wiki.config.toml`, un diff
  che tocca i glob ma non l'`exec_page` → segnala l'`exec_page`. Senza la config → il segnale **non** appare
  (host-agnostico).

## 3. Fail-loud su scope indeterminabile (SC-005)

- Fuori da un repo git e senza `--pages` → `ritual-check` esce **1** con messaggio azionabile, **non**
  restituisce «0 candidati».

## 4. Scaffold di dichiarazione (US2, DA-4)

- L'output (summary + JSON `declaration_scaffold`) include la riga
  `Rituale: record: <?> · distill: <N…> · lint: <M…>` coi conteggi pre-popolati.

## 5. Dichiarazione forzata host-facing (SC-002, US2)

- Il blocco `SERTOR:WIKI-RITUAL` (claude-md-block) + `wiki-playbook.md` richiedono la riga di dichiarazione a
  fine step (verdetto esplicito, «non serve» incluso). Verifica: gli asset bundlati contengono la regola e
  `test_assets_sync` è verde (parità Claude/Copilot).

## 6. Dogfood reale

- Su questo stesso branch: `uv run --project .sertor sertor-wiki-tools ritual-check --json` → elenca i
  candidati dello step corrente; la chiusura dello step emette la dichiarazione coi verdetti.

## Esito atteso

Tutti i punti verdi → feature pronta per PR. `sertor-core` engine di retrieval **invariato**; gate pre-merge
(suite `not cloud` + ruff) verde; guardia sync bundle verde sugli asset host-facing.
