---
title: Il setup dichiara ciò che presume, non ciò che è successo (analisi E2-017/018 · E10-036/037)
type: synthesis
tags: [installer, doctor, osservabilita, fail-loud, principio-xii, e2, e10, analisi]
created: 2026-07-17
updated: 2026-07-17
sources: ["requirements/sertor-cli/epic.md", "requirements/debito-tecnico/epic.md", "src/sertor_core/services/doctor.py", "src/sertor_core/cli/__main__.py", "src/sertor_core/composition.py", "packages/sertor/src/sertor_installer/install_rag.py", "packages/sertor-install-kit/src/sertor_install_kit/artifacts.py", "packages/sertor-install-kit/src/sertor_install_kit/report.py", "acta.folder/board/Feedback Sertor"]
---

# Il setup dichiara ciò che presume, non ciò che è successo

> **Stato:** analisi completata 2026-07-17; **decisioni di scope SCIOLTE 2026-07-18**; **coda CHIUSA 2026-07-20**.
> Coda derivata: **FEAT-038 ✅ (`7075a0f`/#198) → FEAT-033 ✅ (`546cb22`/#200) → E2-018 ✅ (`0b45c24`/#202,
> 036 assorbita) → FEAT-034 ✅ (+FEAT-035 fusa, `5add90d`/#205, 2026-07-20 — 🎉 ultimo item)**. Ricognizione
> via 4 subagent (requisiti · storia · feedback esterni · codice) + verifica empirica in prima persona.

## La tesi (una malattia, non quattro bug)

I quattro item che l'utente ha raggruppato sono **sintomi della stessa radice**. Il filo l'ha nominato
**Noetix** e noi l'abbiamo adottato: *«l'installer ragiona per presenza, non per contenuto»*. Allargato
alla luce di tutti e quattro:

> **Le nostre superfici dichiarano ciò che *presumono*, non ciò che è *successo*, e non espongono
> l'evidenza su cui si basano.**

È il **Principio XII (Fail Loud, Fix the Cause)** applicato al setup e alle superfici di salute. Si rompe
su due assi, e i quattro item si dividono esattamente così:

| Asse | Cosa succede | Feature |
|---|---|---|
| **A — il racconto non descrive l'azione** | il report riporta una *precondizione* («c'era già») al posto del *fatto* («ho eseguito») | **E2-018**, **E10-036** (+ E10-032 già chiusa) |
| **B — il verdetto non è ancorato né spiegabile** | la misura dipende da dove/quando la chiedi, e non dice su cosa si fonda | **E10-037**, **E2-017** (+ E10-034) |

## Le prove (verificate in prima persona, con file:riga)

### Prova regina — il report dice il falso (`install_rag.py:689`, `_apply_deps`)
```python
res = runner.run([_UV, "add", spec], cwd=sertor_dir)      # uv add gira SEMPRE
if not res.ok: raise DependencyError(...)
outcome = Outcome.SKIPPED if already else Outcome.CREATED  # "already" = .sertor/pyproject.toml esisteva
return ArtifactOutcome(".sertor", outcome, f"uv add {spec}")
```
L'esito descrive **se la directory c'era**, non **cosa ha fatto il comando**. Contraddizione *interna alla
stessa struttura*: `detail` dice `uv add {spec}` (comando eseguito) mentre `outcome` dice `SKIPPED`.
Nostra auto-osservazione già affissa su Acta (2026-07-16): *«il report dell'installer non è un racconto
affidabile di ciò che è successo»*.

### Causa strutturale — l'enum non ha «presente ma diverso» (`artifacts.py:63-75`)
`Outcome` = CREATED/SKIPPED/MERGED/BLOCK/ERROR/UPDATED/REMOVED. **`SKIPPED` conflaziona** *«identico,
giustamente nulla da fare»* e *«divergente, non l'ho toccato»* — il buco esatto da cui sono passati
FEAT-031/032. **Ironia:** il confronto di contenuto **esiste già**, ma solo in uninstall
(`lifecycle.py:159`, `"preserved: modified since install"`). Sappiamo dire «presente ma diverso»;
l'install non lo chiede. In install: `install_rag.py:775` `if dest.exists(): return SKIPPED "already
present"` senza confronto (idem `install_governance.py:233`).

### `doctor` NON è ancorato alla radice — PROVATO EMPIRICAMENTE
`cli/__main__.py:574` → `root = Path.cwd()`; `composition.py:860` risolve ogni sorgente come `root/path`,
e `os.stat` fallito → `(path, 0.0, None)` → `stale=True`. Prova deterministica (stesso indice, stesso
istante, subito dopo un re-index):
```
doctor DALLA ROOT  →  index: pass                 | last_index: 12:56:53
doctor DA src\     →  index: warn (index_stale)   | last_index: 12:56:53   ← stesso indice!
```
Anche `registered` (area `mcp`) oscilla True→False cambiando cwd. **Già visto e archiviato**: E15-FEAT-009
fu chiusa «not-a-bug» il 2026-07-04 notando che `registered=False` era «artefatto cwd del *doctor*» — il
template era innocente e ci siamo fermati lì, senza correggere la cwd di `doctor`. È lo **stesso difetto di
ancoraggio di FEAT-031** (che lo corresse per gli hook), mai corretto per `doctor`.

### `doctor` non spiega + `last_index` è mal chiamato (`doctor.py:198-249`)
Il verdetto è calcolato **per-file al momento della run** (mtime cambiato **E** hash diverso → stale);
`break` al primo offender (`:239`) → messaggio *«sources changed since the last index»* **senza dire quale
file**. `last_index` (`:224`) = `max(mtime dei file registrati)` = mtime del file più recente, **NON** l'ora
dell'indicizzazione; **nessun check lo legge**, è solo `detail`. → Assolve metà del sospetto di Acta: un
corpus fermo NON «invecchia» (nessuno confronta quel timestamp con l'età); un incrementale a 0 modifiche non
sposta `last_index` **per costruzione**, non per bug. Lo swing warn/pass che Acta ha visto è
**probabilmente E10-034** (verdetto scritto pre-riparazione, poi l'hook ripara), NON il bug cwd; il bug cwd
è un **secondo difetto indipendente** trovato cercando la loro causa.

### Segnali che nessuno legge (il difetto che nessuna delle 4 chiede)
| Segnale | Scrittore | Lettore |
|---|---|---|
| `install.report/1` | installer | stdout (perde `capability`/`op` nel JSON — `report.py:107`) |
| `rag.health/1` | rag-freshness (SessionEnd) | rag-freshness-start |
| `version.check/1` | version-check | version-check-start |
| `hook.error/1` (breadcrumb E10-019) | 3 hook | **NESSUNO (write-only)** |
| `InstallReport.notes` | installer | solo rendering |
Ogni volta che troviamo un silenzio **aggiungiamo un canale nuovo e nessuno li aggrega**. Aggiungere
`install.event/1` senza un lettore ripeterebbe l'errore per la quinta volta.

## Le proposte

- **P0 — `doctor` ancorato alla radice** *(BUG, non miglioria)*. `Path.cwd()` → radice del progetto (come
  FEAT-031 per gli hook). **Urgente:** ogni verdetto `doctor` è oggi inaffidabile e `rag-freshness` ci
  costruisce sopra l'allarme. **Riordino conseguente:** E10-034 NON è implementabile prima di questo (il suo
  rimedio è «ripara e **rimisura** con `doctor`» — rimisurare con uno strumento non ancorato non risolve).
  → **037 (doctor) deve precedere 034**, contro la coda del 2026-07-17.
- **P1 — l'esito descrive l'azione, non la precondizione** *(cuore di E2-018; ASSORBE E10-036)*. Nuovo esito
  che distingue `skipped:identical` ≠ `skipped:divergent` ≠ `updated` ≠ `left-stale`; riusa il confronto di
  uninstall. Con questo **036 sparisce come caso speciale**: «upgrade ha creato 3 artefatti ex-novo» diventa
  un fatto nel report, non un `if` hard-coded.
- **P2 — log ispezionabile** *(E2-018 vero e proprio)*. `.sertor/.install-log.jsonl` estendendo `log_event`
  (`sertor_install_kit.observability`, **già esiste** — non nuovo meccanismo): verbo reale, capability,
  comando eseguito, esito per-artefatto col perché, rev risolta. `--dry-run` proietta con **lo stesso
  codice, nessuna scorciatoia**. Report a schermo sintetico, **il log è la verità**.
- **P3 — un lettore unico** *(la parte che nessuna delle 4 chiede)*. `doctor` diventa l'unica superficie che
  **legge** i segnali runtime e li riporta (chiude il ciclo: oggi `hook.error/1` è write-only). Dà a **E2-017**
  la casa naturale: `unknown` con un `reason` (oggi collassa 3 cause: stamp assente, GET fallita, versione non
  parsabile) e senza il silenzio a vita dopo il cenno una-tantum.

**Principio da codificare (corollario del XII, non nuovo principio):**
> *Una superficie dichiara ciò che ha **fatto** e su quale **evidenza**; se non lo sa, dice che non lo sa
> **e perché**. Mai riportare una precondizione al posto di un'azione.*

## Impacchettamento proposto (feature d'ombrello = errore, troppo grande + P0 urgente)
1. **`doctor` ancorato** — bug isolato, piccolo, sblocca 034. **Primo, prima ancora di FEAT-033.**
2. **E2-018 allargata** a P1+P2 (esito-azione + log) — **E10-036 vi si fold dentro**, si chiude senza codice proprio.
3. **P3 + E2-017** — lettore unico + onestà updater.

## DECISIONI UTENTE — SCIOLTE (2026-07-18)
1. **Riordino accettato:** «doctor ancorato PRIMA di 033/034». Il doctor-non-ancorato è l'unico **P0** (verdetti inaffidabili + prerequisito di 034); 033 non ha scadenza esterna dura.
2. **036 assorbita in E2-018** (folded, non cancellata — traccia mantenuta in E10 con rimando a E2-018).
3. **034 sequenziale, non fusa** col doctor-ancorato: doctor come fix P0 a sé (shippabile/testabile), 034 come feature separata (asset host-facing → guardia esito-upgrade + sync bundle + doc utente).

**Tracciamento durevole (fatto 2026-07-18):** il bug doctor-ancorato → **nuova E10-FEAT-038 (P0)**; **E10-FEAT-037** marcata investigata (last_index non-letto = non-bug; swing = FEAT-034; cwd-bug → 038); **E10-FEAT-036** folded in **E2-FEAT-018**, il cui scope è stato allargato a P1 (esito-azione) + P2 (log). Coda risultante nell'EXEC:
> **1. FEAT-038 doctor ancorato → 2. FEAT-033 ritual-check default branch → 3. E2-018 (esito-azione + log, 036 folded) → 4. FEAT-034 rag-freshness rimisura.**

**Stato operativo (coda CHIUSA 2026-07-20):** **FEAT-038 ✅ · FEAT-033 ✅ · E2-FEAT-018 ✅** (`0b45c24`/PR #202,
assorbe E10-FEAT-036; P2-log wiki/flow/lifecycle → follow-up E2-FEAT-020) · **E10-FEAT-034 ✅** (`5add90d`/PR #205,
2026-07-20 — l'hook misura → ripara → **rimisura** → persiste, **+ FEAT-035 fusa**: auto-heal del lock `.index.lock`
su PID morto). Tutte CONSEGNATE, SpecKit completo, verificate LIVE. 🎉 **La coda «analisi setup» è chiusa.**

## Vincoli già scritti da rispettare (non partire da zero)
Principio XII (Fail Loud) · `InstallReport.notes` (canale già usato, «primo uso reale» E10-018) ·
breadcrumb `hook.error/1` (E10-019) · `log_event` del kit (contratto in uso, `operation∈{upgrade,uninstall}`) ·
cenno una-tantum con flag persistente (`unknown_notified`, E2-017) · `exit 0` preservato sui fail-safe
(E4-011) · guardia sull'**esito d'upgrade** non sulla forma dell'asset (E10-032, 10 guardie) ·
la forma-target di E2-018 è già scritta nel backlog (`install.event/1`, `skipped:identical` vs
`present-but-different`, `--verbose`/`--explain`, dry-run fedele).

## Finding collaterali emersi durante l'analisi
- **`search_docs` non recupera le righe di backlog** delle 4 feature (score ~0.02): le tabelle `epic.md` sono
  righe singole lunghissime → il chunking le penalizza. Buco di retrieval reale sul corpus requisiti (leva E5).
- **Il bug FEAT-031 ci ha morso DAL VIVO durante l'analisi**: hook `PreToolUse` con wiring relativo ha
  bloccato Bash quando la CWD era in `src/` (catch-22: non correggibile via Bash perché l'hook blocca Bash).
  Aggirato con PowerShell. È la conferma che il wiring ancorato (PR #194) va mergiato: la sessione gira ancora
  sul `settings.json` non-ancorato.

Vedi [[esito-sull-host-vs-forma-dell-asset]] · [[identita-hook-nel-merge]] · [[step-ritual]].
