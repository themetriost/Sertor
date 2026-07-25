---
title: Avviso di aggiornamento (version-check, notice-only)
type: tech
tags: [installer, auto-update, version-check, hook, feat-013, feat-017, feat-021, dogfood]
created: 2026-07-21
updated: 2026-07-25
sources: ["specs/077-version-update-check/plan.md", "requirements/sertor-cli/version-update-check/requirements.md", "packages/sertor/src/sertor_installer/assets/rag/hooks/version-check.py", "packages/sertor/src/sertor_installer/assets/rag/hooks/version-check-start.py", "wiki/log/2026-06-26.md", "wiki/log/2026-07-10.md", "wiki/log/2026-07-13.md"]
---

# Avviso di aggiornamento (version-check, notice-only)

E2-FEAT-013 (feature 077, PR #113, 2026-06-26) dà a un ospite un modo per **sapere che esiste un
Sertor più nuovo** — senza mai aggiornare da solo. È il caso opposto dell'installer imperativo
([[installer-lifecycle]], `sertor upgrade` lo *fa*): qui la macchina **avvisa e basta**. Il valore è
l'onestà del segnale — l'ospite decide, la capacità non tocca nulla. È un tassello di
[[dogfood-fidelity]]: il dogfood riceve lo stesso avvisatore di ogni ospite e ci vive dentro (per
questo i suoi buchi — vedi sotto — sono emersi da noi stessi).

## Il meccanismo: due hook + uno stato

Due hook host-facing, depositati da `sertor install rag` e **portabili** (Python, non `.ps1` — A-09):

- **SessionEnd — `version-check.py`.** Fa una **GET HTTPS** del file `/VERSION` su `master`
  (`raw.githubusercontent.com/themetriost/Sertor/master/VERSION`), la confronta con la versione
  **derivata dal runtime** — quella a cui `sertor-core` è risolto in `.sertor/uv.lock` — e persiste
  il verdetto in `.sertor/.version-check.json` *(fino al 2026-07-25 leggeva invece lo **stamp
  d'installazione** `.sertor/.sertor-version` — vedi «Lo stato dichiarato va derivato» sotto)*.
  **Consuma zero vehicle CLI e zero LLM**: è un puro wrapper
  HTTP+file, non importa mai `sertor_core`. **Non fatale**: exit 0 sempre; una GET/parse fallita →
  verdetto `unknown`, nessun errore. La GET è **cachata ~24h**: se `checked_at` è entro le 24 ore
  (e non c'è `SERTOR_VERSION_CHECK_FORCE`) riusa il `latest` in cache invece di rifetchare. L'env
  override `SERTOR_VERSION_CHECK_URL` è onorato **solo su https** (A-08, security).
- **SessionStart — `version-check-start.py`.** **Zero rete** (la GET è già avvenuta a SessionEnd):
  legge lo stato e, **se e solo se** il verdetto è `behind`, stampa su stdout un avviso che
  l'assistente riceve come contesto d'apertura sessione. **Mai auto-upgrade**: il confine D↔N è
  netto, l'agente non applica nulla, l'utente decide. Idempotente: stato assente o verdetto ≠
  `behind` → no-op.

### Il comando dell'avviso è derivato dall'ospite (dal 2026-07-24)

Il messaggio non contiene più un comando fisso: `_upgrade_command()` legge l'URL del repository dal
**`pyproject.toml` del runtime dell'ospite stesso** (`[tool.uv.sources]`) e compone

```
uvx --refresh --from "git+<url-dell-ospite>#subdirectory=packages/sertor" sertor upgrade
```

Il frammento **`#subdirectory=packages/sertor` è la parte portante**: senza, `uvx` risolve il
pacchetto **root** `sertor-core`, che fornisce `sertor-rag` e `sertor-wiki-tools` ma **non** `sertor`
— e il comando fallisce con *«An executable named `sertor` is not provided»*.

**Perché è cambiato.** Il messaggio precedente suggeriva `uvx --refresh sertor`, cioè proprio la
forma che non funziona: **l'avvisatore che esiste per far aggiornare gli ospiti pubblicava il comando
che glielo impediva**. Segnalato dal nodo *Kaelen* (2026-07-24) dopo averlo copiato alla lettera dalle
nostre release notes. La forma corretta era nell'annuncio v0.1.0 e si era persa nelle note successive.

Derivare l'URL invece di scriverlo è ciò che rende l'avviso corretto **per qualunque ospite**, incluso
chi ha installato da un fork o da un mirror — host-agnostico per costruzione (Principio X) anziché per
coincidenza. Pinnato da `test_version_check_start_notice_on_behind`, che ora **vieta esplicitamente**
la forma nuda.

### Lo stato `version.check/1`

Il file `.sertor/.version-check.json` è il contratto tra i due hook:

```json
{ "schema": "version.check/1", "verdict": "up-to-date",
  "installed": "0.2.0", "latest": "0.2.0", "installed_source": "runtime-lock",
  "checked_at": "2026-07-25T…Z",
  "dimensions": {"sertor-core (runtime)": "0.2.0", "sertor (installer stamp)": "0.1.0"} }
```

`verdict` ∈ `{behind, up-to-date, ahead, unknown}`, calcolato da un confronto SemVer segmento-per-
segmento (numerico, fallback lessicale). `installed_source` dichiara **da dove viene il numero**
(`runtime-lock` o `stamp`); `dimensions` riporta **ogni** fonte osservabile — la versione del runtime
e lo stamp dell'installer — così una loro divergenza è **visibile** invece di essere risolta in
silenzio a favore di una delle due.

## Lo stato dichiarato va derivato, non scritto a parte (E2-FEAT-021, 2026-07-25)

Il confronto usava lo **stamp** `.sertor/.sertor-version`, che l'installer scrive con la propria
versione (`importlib.metadata.version("sertor")`). Ma «quale installer ha girato» e «cosa il runtime
esegue davvero» sono **due fatti diversi**, e divergono in **entrambe le direzioni**:

- **Falso «da aggiornare».** Un nodo che consuma `sertor-core` via `uv` con un pin al tag, **senza mai
  usare l'installer** (nodo *Acta*), ha uno stamp che non avanza mai: avviso `behind` **a ogni
  sessione, per sempre** — e con un rimedio (`sertor upgrade`) che su quell'host **non è nemmeno
  eseguibile**. Il costo non è il fastidio: è che ci si abitua a ignorare l'avviso, e quello vero un
  domani non verrà letto.
- **Falso «aggiornato».** Lo stamp scritto da un installer più nuovo del runtime che ha prodotto
  dichiara un avanzamento che al runtime non è arrivato (il pin fermo, *Sinthari*/*VM-WorkingFolder*).

Il fix è uno solo per entrambi: **derivare** la versione dal lock del runtime, tenendo lo stamp come
**fallback** per gli host il cui lock non è leggibile. È lo stesso principio che governa
[[identita-per-presenza-o-per-contenuto]] applicato ai marker di versione — e la classe che il nodo
*Acta* ha nominato: *l'artefatto dichiara uno stato, la realtà ne ha un altro, e niente confronta i
due*.

## Parità per-assistente

L'avvisatore rispetta la parità multi-assistente ([[assistant-targeting]]): su **Claude** sono i due
script hook nativi; su **Copilot CLI**, dove non c'è un hook SessionStart eseguibile, è un **prompt
statico** (`_copilot_version_check_start_specs` in `install_rag.py`) che istruisce l'agente a
surfacciare il cenno — D↔N più lasco, best-effort. Editare il lato-bundle richiede poi
`python -m sertor_installer.sync` per riallineare le copie dogfood (`.claude/hooks/version-check{,-start}.py`).

## Dormiente-fino-alla-release

L'avvisatore **parla solo su `behind`**, e `behind` scatta solo quando `/VERSION` su `master`
**supera** la versione installata (derivata dal runtime). Ma `/VERSION` si bumpa **a mano, solo a una release user-facing**
(policy A-15 SemVer con bump manuale; vedi [[dogfood-fidelity]] e roadmap): un `/VERSION` fermo mentre i commit avanzano
**non è drift**, è «nessuna release esterna ancora». Ne segue una proprietà voluta: l'avvisatore è
**dormiente-fino-alla-release** — correttamente muto finché non arriva il primo bump. La prima
release pubblica `v0.1.0` (2026-07-13) ha lasciato `/VERSION=0.1.0` senza bump: verdetto `up-to-date`,
SessionStart muto — *corretto*, non guasto. Il `behind` si accenderà alla **prossima** release che
bumpa `/VERSION`. Confondere il tracking-per-merge (compito del [[dogfood-fidelity|dogfood]], runtime
che segue HEAD) con `/VERSION` farebbe scattare l'avviso a ogni commit: i due sono tenuti separati
apposta.

## Onestà su `unknown` e repo privato (E2-FEAT-017)

Il finding del 2026-07-10 (probe dal vivo) ha scoperto un guasto silenzioso: finché il repo era
**privato**, la GET di `/VERSION` da `raw.githubusercontent` dava **404** (raw non serve i privati
senza auth) → `latest=""` → `verdict:"unknown"` **permanente**. E il SessionStart parlava *solo* su
`behind` → l'ospite non sapeva **mai** che l'updater non poteva verificare: una capacità che finge in
silenzio (viola il Principio XII, *Fail Loud*).

E2-FEAT-017 (2026-07-13) ha reso onesto lo stato inconcludente **senza nag**:
- SessionStart, su `verdict=unknown` e `unknown_notified` non settato, emette **una-tantum** «SERTOR
  UPDATE CHECK UNAVAILABLE» (non ha potuto verificare — offline o repo privato; Sertor funziona;
  appare una volta) e **persiste** `unknown_notified=true`.
- SessionEnd fa **carry-forward** di `unknown_notified` **finché** il verdetto resta `unknown`, e lo
  **resetta** (flag omesso) a qualsiasi verdetto risolto → un futuro episodio `unknown` notifica di
  nuovo una volta.

Il **go-public** (2026-07-13, repo reso pubblico) ha sciolto la parte strutturale: `GET /VERSION` →
**HTTP 200 `0.1.0`**, l'updater ora *può* verificare (verdetto `up-to-date`, corretto). Resta la
proprietà dormiente-fino-alla-release di cui sopra.

Vedi anche: [[installer-lifecycle]] · [[dogfood-fidelity]] · [[assistant-targeting]].
