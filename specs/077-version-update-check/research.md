# Research — auto-update version check (avviso d'aggiornamento) (E2-FEAT-013)

**Branch**: `feat013-version-check-backlog` · **Data**: 2026-06-25 · **Fase**: Phase 0 (design)

> Scopo: ancorare il design ai meccanismi esistenti e **registrare come risolte** le cinque forche di
> *come* (DA-1..DA-5), già chiuse dal flusso principale (incorporate nel prompt di plan). Le quattro
> decisioni di scope sono **fisse** nella spec — qui non si riaprono. La feature è il **gemello** di
> E10-FEAT-011 (hook di freschezza): stesso pattern host-facing, stesso confine D↔N.

---

## D-0 — Ancoraggio: ciò che esiste già (dato di partenza)

Verificato via MCP `sertor-rag` (`search_code` sul wiring freschezza — nessun errore tool) + `Read`
dei file (citazioni `path:lineno`).

### D-0a — Pattern hook host (rag-freshness / memory-capture) = template del nuovo hook
**Fatto**: il gemello E10-FEAT-011 ha **già introdotto** la coppia di hook che questa feature ricalca:
`rag-freshness.ps1` (SessionEnd: lavoro + scrittura stato su `.sertor/.rag-health.json`) e
`rag-freshness-start.ps1` (SessionStart Claude: ripesca lo stato e induce). Disciplina invariante
(da riusare byte-per-byte): wrapper *thin*, exit 0 sempre, `try/catch` che assorbe ogni esito, lettura
tollerante del payload JSON da stdin, root da `$env:CLAUDE_PROJECT_DIR` → `hook.cwd` → `'.'`.
**Riferimenti**: `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.ps1:39-138`
(stdin tollerante, root, scrittura stato `.sertor/`, exit 0); `rag-freshness-start.ps1:41-60` (lettura
stato, no-op se sano, induzione su degraded, exit 0).
**Differenza**: il version-check **non** invoca alcun vehicle CLI (`sertor-rag …`) — fa una **GET
HTTP semplice** del `/VERSION` remoto + una **lettura/confronto di file** (FR-014, nessun Python nel
path caldo). È il punto in cui i due gemelli divergono: freschezza consuma vehicle, version-check
consuma HTTP+file.

### D-0b — Wiring installer per-assistente (install_rag.py) = seam riusato
**Fatto**: il cablaggio segue **esattamente** il pattern freschezza/memory-capture in `install_rag.py`
(FILE `CREATE_IF_ABSENT` per lo script + `SETTINGS_MERGE` `MERGE_DEDUP` per la voce SessionEnd/
SessionStart), parametrico su `assistant` via `AssistantProfile`/`AssistantId`. Nessun nuovo
`ArtifactKind`/`Surface`/`WriteStrategy` (YAGNI III).
**Riferimenti**: costanti+specs freschezza `install_rag.py:170-218`; append al plan `:392-440`
(2 FILE + 2 SETTINGS_MERGE, SessionStart Claude-only via `if not is_copilot`); dispatch art-aware
`_rag_hook_fragment` `:524-540`; `sertor_owned_paths` `:614-669` (owned_files per-assistente +
shared_edits, SessionStart script solo Claude — W5); uninstall/upgrade già art-aware (FILE→remove/
update; SETTINGS_MERGE→`remove_settings_entries` con `delete_if_empty` per `sertor-hooks.json`).

### D-0c — Formato hook nativo Copilot (kit) = render generato, non asset statico
**Fatto**: la voce Copilot è **generata** da `render_copilot_hooks([HookEntrySpec(...)])` (formato
`{"version":1,"hooks":{<Event>:[entry piatta con timeoutSec]}}`), via un sentinel-source nel plan,
mai un asset JSON in formato Claude. Su Copilot CLI il SessionStart è un `type:"prompt"` **statico**
(nessuno script → nessuna rete possibile, A-005).
**Riferimenti**: `_copilot_freshness_end_specs`/`_copilot_freshness_start_specs` `install_rag.py:189-218`
(gemelli del nuovo `version-check`); render `sertor-install-kit/.../surfaces.py` `render_copilot_hooks`.

### D-0d — Fonte unica della versione: `/VERSION` (accertata)
`/VERSION` a radice contiene `0.1.0` (un'unica riga). È letto dinamicamente da **tutti e quattro** i
`pyproject` via `[tool.hatch.version] path = "../../VERSION"` → un solo confronto copre i pacchetti
(A-001, FR-002/011). Verificato: `packages/sertor/pyproject.toml:39-41` (`dynamic=["version"]`,
`path="../../VERSION"`). L'URL di distribuzione del prodotto è
`DIST_URL = "https://github.com/themetriost/Sertor.git"` (`rag_profile.py:17`) → il raw del `/VERSION`
su `master` deriva da lì (D-2).

### D-0e — `RUNTIME_IGNORES` (kit) = unica fonte per la voce `.gitignore`
`RUNTIME_IGNORES` oggi è `(".sertor/.venv/", ".sertor/.index*", ".sertor/.env",
".sertor/.rag-health.json")` (`gitignore_append.py:14-19`). **Non** copre lo stato del version-check.
→ azione necessaria (D-3): aggiungere `.sertor/.version-check.json`. Lo stamp install-time
(`.sertor/.sertor-version`, D-4) è coperto **già** da nessuna regola → va aggiunto anch'esso (è stato
runtime rigenerabile, mai versionato).

### D-0f — Guardia di sync asset (oggi)
`tests/unit/test_assets_sync.py` compara `assets/claude/**` ↔ `.claude/` (sync via
`sertor_installer.sync`). **Gli hook RAG vivono in `assets/rag/hooks/`** e NON sono coperti da quel
sync; E10-FEAT-011 ha aggiunto la guardia dedicata `test_rag_freshness_dogfood_sync` in
`packages/sertor/tests/test_install_rag_freshness.py:314-330`, che itera su una lista di nomi hook e
verifica la **byte-parità** bundlato↔dogfood. → la nuova guardia version-check **estende quella
lista** (D-3, FR-016/017), invece di una guardia gemella nuova (DRY).

---

## D-1 — DA-1 + DA-4: chi esegue il check, e fusione vs separazione (RISOLTA)

**Decisione (DA-1)**: il check «vivo» (GET di `/VERSION` + confronto + scrittura stato) gira in uno
**script al SessionEnd** — `version-check.ps1` — gemello di `rag-freshness.ps1`, **eseguibile su
Claude e su Copilot CLI** (entrambi hanno hook script al SessionEnd). Il **SessionStart** è **solo
lettura + avviso**: su Claude uno script dedicato `version-check-start.ps1` (legge lo stato e, se
`behind`, emette l'avviso su stdout); su Copilot CLI un **prompt nativo statico** (Copilot non può
fare rete al SessionStart → l'agente legge lo stato persistito e relaya l'avviso). Stessa asimmetria
W5 della freschezza.
**Rationale**: nessuno fa rete in un prompt statico (R-3); la GET sta dove c'è uno script su entrambi
gli assistenti (SessionEnd); il confine D↔N regge (lo script meccanico segnala, l'utente/agente
agisce, mai auto-upgrade — FR-005/CS-4).

**Decisione (DA-4)**: asset/voci **SEPARATI** dall'hook di freschezza (gemello indipendente, come
memory-capture ↔ rag-freshness). Lifecycle granulare per la capacità, isolamento reciproco
(FR-016/017), e — soprattutto — **scope distinto**: la freschezza riguarda il *corpus*, il
version-check il *pacchetto*; coesistono entrambi al SessionEnd/SessionStart, ciascuno non-fatale,
voci merge-dedup distinte.
**Piggyback valutato e SCARTATO**: estendere `rag-freshness.ps1` perché faccia anche la GET di
`/VERSION` eviterebbe un secondo trigger, ma (a) accoppia due capacità con scope e lifecycle diversi
(uninstall/upgrade non più granulari), (b) la freschezza consuma `sertor-rag` vehicle mentre il
version-check fa solo HTTP+file — fonderle mischia due nature (vehicle vs rete pura), (c) la GET del
version-check è **cachata ~1/giorno** (FR-006) mentre il re-index gira a ogni SessionEnd: le cadenze
non coincidono. **Nessuna GET duplicata** perché sono GET di cose diverse (corpus/doctor vs `/VERSION`).
Separati è più semplice e più pulito (Principio III).

---

## D-2 — DA-2: sorgente esatta del `/VERSION` «ultimo» (RISOLTA)

**Decisione**: URL **raw su `master`**, derivato dall'`DIST_URL` del prodotto:
`https://raw.githubusercontent.com/themetriost/Sertor/master/VERSION`. Lo script ne fa una **GET
semplice** (PowerShell `Invoke-WebRequest`/`Invoke-RestMethod`), timeout breve (~5 s), con il
contenuto interpretato come una **singola riga di versione** (`.Trim()`).
**Parametrizzazione (fork/branch)**: l'URL è sovrascrivibile via env **`SERTOR_VERSION_CHECK_URL`**
(letta dallo script all'avvio; assente → default Sertor). Questo copre gli ospiti che puntano a un
fork o a un branch diverso da `master`, senza editare lo script (Principio X/VIII: ciò che varia fra
ospiti vive nella config, non nel corpo). L'asset resta host-agnostico.
**Privacy (FR-015/RNF-4)**: l'unico egress è la GET del `/VERSION` pubblico; nessun contenuto/segreto
del progetto è trasmesso (la GET non porta query né body).
**Offline / GET fallita → skip silenzioso (FR-009)**: ogni errore di rete/parse è assorbito dal
`try/catch`; il check è trattato come *inconcludente* (nessun avviso, nessun errore, exit 0).

---

## D-3 — DA-3: sorgente della versione «installata» (RISOLTA)

**Opzioni considerate**
1. **Metadati del pacchetto a runtime** — `python -c "import importlib.metadata as m;
   print(m.version('sertor-core'))"` dentro `.sertor/.venv`. *Scartata come path caldo*: lanciare
   Python a ogni SessionEnd accoppia il check al `.sertor/.venv` (potrebbe mancare/rompersi) e
   introduce un costo/avvio Python non necessario; soprattutto **violerebbe lo spirito** del confine
   («nessun Python/`sertor_core` nel path caldo dell'hook» — DA-3 del prompt).
2. **Stamp install-time sotto `.sertor/`** — l'installer **scrive** la versione del prodotto in un
   file `.sertor/.sertor-version` (singola riga, gemello del `/VERSION`) al momento di `sertor install`
   / `upgrade`. Lo script di check fa un **confronto puro testuale** stamp↔remoto, **nessun Python**.
   **SCELTA.**

**Decisione**: **stamp install-time** `.sertor/.sertor-version`.
- **Cosa scrive l'installer**: l'installer `sertor` conosce la propria versione (la wheel la imprime
  via hatch dal `/VERSION` bundlato; recuperabile in-process con `importlib.metadata.version("sertor")`
  al momento dell'install, **non** nel path caldo dell'hook). Scrive quel valore in
  `.sertor/.sertor-version` come **nuovo Artifact** del plan rag (FILE generato a install/upgrade-time).
  A `upgrade` lo stamp è **riscritto** con la nuova versione → la loop si chiude (FR-013/US7): il
  prossimo SessionEnd confronta lo stamp aggiornato col remoto e torna `up-to-date`.
- **Perché copre le 3 dimensioni (FR-011)**: poiché `/VERSION` è la **fonte unica** di tutti i
  pacchetti (D-0d), un singolo stamp `.sertor/.sertor-version` rappresenta la versione installata di
  Sertor sull'ospite. La granularità per-dimensione (FR-012, Could) è realizzabile come stamp multipli
  (`.sertor/.sertor-version` per `sertor`, uno scritto da `sertor-flow install` per la governance) —
  vedi D-6; nell'MVP Should un solo stamp del pacchetto `sertor` è sufficiente, e se `sertor-flow`
  scrive il proprio stamp lo script li enumera e nomina quale dimensione è indietro.
- **`sertor-flow`**: l'installer di governance (pacchetto separato, **no dipendenza da `sertor-core`**)
  scrive analogamente uno stamp `.sertor/.sertor-flow-version` (stessa logica, opt-in alla copertura
  per-dimensione US6). Distribuzione del version-check via `sertor-flow install` = gemella di
  `sertor install` (parità).

**Indeterminato (FR-010)**: stamp assente o non parsabile → check inconcludente → skip silenzioso
(mai un falso «sei indietro»).

---

## D-4 — DA-5: semantica del confronto di versione (RISOLTA)

**Decisione**: confronto **semantico per segmenti numerici** con **fallback lessicale**.
- Si fa `Trim()` di entrambe le stringhe (stamp installato, `/VERSION` remoto); si splitta su `.`; si
  confrontano i segmenti come **interi** (1.2.0 vs 1.10.0 → 1.10.0 più nuovo, evitando il bug del
  confronto stringa). Se un segmento non è numerico (versioni con suffissi tipo `1.2.0rc1`) si ripiega
  al **confronto lessicale** di quel segmento (best-effort, deterministico).
- **Verdetto**: `installato < remoto` → **`behind`** (avviso, FR-003); `installato == remoto` →
  **`up-to-date`** (nessun avviso); `installato > remoto` → **`ahead`** (nessun avviso — copre il
  dev-locale «più nuovo del remoto», FR-004/DA-5); parse fallito → **`unknown`** (skip, FR-010).
  Regola netta: **installato ≥ remoto ⇒ nessun avviso**.
**Rationale**: numerico per-segmento è corretto per il versioning semantico di Sertor (`/VERSION` è
`MAJOR.MINOR.PATCH`); il fallback lessicale garantisce determinismo anche su forme inattese senza
introdurre una dipendenza (`packaging`/`semver`) nello script PowerShell (Principio III: nessuna
dipendenza nuova; lo script resta stdlib `pwsh`). Non si usa il SHA di commit (fuori ambito, R-1).

---

## D-5 — Cadenza e caching ~1/giorno (ancoraggio FR-006/RNF-1)

**Decisione**: lo stato persistito `.sertor/.version-check.json` (D-6) porta un `checked_at`
(ISO-8601 UTC). Allo SessionEnd lo script **prima legge** lo stato: se `checked_at` è entro **~24h**,
**riusa** l'esito (nessuna GET — FR-006/CS-2) e si limita a riconfermare il verdetto rispetto allo
stamp corrente (così un upgrade a metà giornata aggiorna il verdetto senza rete — R-5/FR-017/US7);
se la cache è scaduta (>24h) o assente, fa **una** GET, ricalcola e riscrive lo stato col nuovo
`checked_at`. Re-check forzato (FR-008/US9, Could) = una env/flag `SERTOR_VERSION_CHECK_FORCE` che
bypassa la finestra cache.
**Perché allo SessionEnd e non allo SessionStart**: la GET (rete, fino a ~5 s) sta al **SessionEnd**
(non rallenta l'avvio, RNF-1); il SessionStart è **zero rete**, legge solo lo stato già pronto e
avvisa. Coerente con la freschezza (lavoro a fine sessione, segnale a inizio sessione).
**No oscillazione (NFR-6 gemella)**: `up-to-date` è scritto come stato canonico (non cancellato) →
SessionStart no-op.

---

## D-6 — File di stato `.sertor/.version-check.json` + stamp `.sertor/.sertor-version`

**Decisione (stato del check)**: `.sertor/.version-check.json`, schema piatto stabile
`version.check/1`:

```json
{
  "schema": "version.check/1",
  "verdict": "behind",
  "installed": "0.1.0",
  "latest": "0.2.0",
  "checked_at": "2026-06-25T20:50:00Z",
  "dimensions": { "sertor": "0.1.0", "sertor-flow": "0.1.0" }
}
```

Campi minimi (FR-007): `verdict` (`behind`|`up-to-date`|`ahead`|`unknown`), `installed`, `latest`,
`checked_at`. `dimensions` è **additivo** (per FR-012, Could) e nomina la versione installata di
ciascuna dimensione presente; quando assente vale il confronto del solo stamp `sertor`. `schema`
versiona il contratto. Letto dal SessionStart (script Claude / prompt+agente Copilot) e da un umano.

**Decisione (stamp installato)**: `.sertor/.sertor-version` (e `.sertor/.sertor-flow-version` per la
governance), singola riga, scritto dall'installer a install/upgrade-time (D-3). È la **fonte locale**
dell'«installato», confrontabile senza Python.

**`.gitignore` (azione necessaria)**: `RUNTIME_IGNORES` += `.sertor/.version-check.json`,
`.sertor/.sertor-version`, `.sertor/.sertor-flow-version` (stato runtime rigenerabile, mai versionato
— FR-018/REQ-014). Unica modifica al kit, additiva e non-breaking (tutti i consumatori usano la
costante; `remove_gitignore_lines` le rimuove all'uninstall).

Contratti: [`contracts/version-check-state.md`](./contracts/version-check-state.md),
[`contracts/version-check-hook-wiring.md`](./contracts/version-check-hook-wiring.md).

---

## D-7 — Promozione degli Out-of-Scope (regola «si promuovono, non restano appesi»)

| Out-of-Scope | Casa durevole | Azione al plan |
|---|---|---|
| **Rilevazione a livello di commit (SHA di `master`)** | Scartata per decisione (low-noise sul bump di `/VERSION`); se mai servisse → **nuova FEAT** epica `sertor-cli` | Nessuna riga ora (scartata esplicitamente, non sepolta) |
| **Pulizia artefatti obsoleti durante l'aggiornamento** | **E10-FEAT-015** (debito separato, già esistente) | Cross-ref, nessuna riga nuova |
| **Freschezza del corpus** | **E10-FEAT-011** (gemello, già consegnato) | Cross-ref, nessuna riga nuova |
| **Pubblicazione/versioning PyPI** | **FEAT-006** epica sertor-cli (Won't) | Cross-ref, nessuna riga nuova |
| **Granularità per-dimensione (FR-012) e re-check forzato (FR-008)** | Could di **questa** feature (REQ-011/018) | Realizzabili nell'asset (stamp multipli / env force); se rinviati restano Could tracciati nel backlog E2 |

---

## D-8 — Confini e non-regressione (vincoli)

- **`sertor-core` INVARIATO**: nessun import, nessun motore/porta/comando nuovo (Principio XI,
  FR-014/RNF-5). La feature è 100% installer + asset + governance. La GET HTTP e il confronto vivono
  nello script PowerShell, **non** nel core e **non** in un comando CLI nuovo.
- **`sertor-install-kit`**: unica modifica = aggiunta di 3 righe a `RUNTIME_IGNORES`
  (`.sertor/.version-check.json`, `.sertor/.sertor-version`, `.sertor/.sertor-flow-version`),
  additiva, non-breaking. Nessun nuovo seam.
- **`sertor` (installer)**: estensione di `build_rag_plan` (+2 FILE script: SessionEnd ovunque,
  SessionStart Claude-only; +2 SETTINGS_MERGE: SessionEnd/SessionStart per-assistente; +1 FILE
  generato per lo stamp `.sertor/.sertor-version`) + costanti/sentinel + 2 `_copilot_*_specs` +
  dispatch in `_rag_hook_fragment` + `sertor_owned_paths` (+owned_files, +stamp). Uninstall/upgrade
  già art-aware (riuso). `sertor-flow` analogo per lo stamp governance.
- **Non-regressione**: le suite esistenti (`packages/sertor`, root, kit) restano verdi; il default
  `claude` non regredisce; a feature non installata comportamento/costo invariati (RNF-5).
- **Guardia sync**: la lista in `test_rag_freshness_dogfood_sync` è **estesa** ai due script
  version-check (DRY, D-0f).
