# Requisiti — `ritual-check` rileva il default branch (non assume `master`)
<!-- Deriva da: E10-FEAT-033 (epica debito-tecnico) -->

## 1. Contesto e problema (perché)

`sertor-wiki-tools ritual-check` scopre i candidati distill/drift di uno step confrontando il diff
`base...HEAD`. La **base** si risolve in `_resolve_base` (`src/sertor_core/wiki_tools/ritual_check.py:48`):
```python
if base: return base
rc, out = _git(["merge-base", "HEAD", "master"], config_dir)   # 'master' HARDCODED
if rc == 0 and out.strip(): return out.strip()
raise ConfigError("cannot determine a git diff base (no merge-base with 'master'); pass --base …")
```
Il nome `master` è **hardcodato**. Su un repo il cui branch di default è `main` (o altro) non esiste
`master` → nessun merge-base → **fail-loud** `cannot determine a git diff base (no merge-base with
'master')`. Aggirabile solo con `--base main`.

**Perché conta:**
- **Viola il Principio X (host-agnostico):** un assunto sull'ospite scritto *dentro* un tool il cui resto
  legge tutto da `wiki.config.toml`. La mission è «framework installabile ovunque»: `main` è oggi il
  default più diffuso.
- **Arriva nel momento peggiore:** `ritual-check` è il **primo** tool che un ospite tocca quando la
  *forced declaration* del rituale (E10-FEAT-026) lo **obbliga** a dichiarare distill/lint a fine step.
  Il primo contatto con la nostra pratica di governance è un errore in faccia.

Segnalato dal nodo **Noetix** (canale Acta `Feedback Sertor`,
`2026-07-16-noetix-governance-bundle-divisibile-configuration-manager`), verificato sul codice da noi
(2026-07-17). È il **primo item** della coda dell'analisi [[setup-dichiara-presunzione-non-azione]]
già consegnata per la parte doctor (FEAT-038).

## 2. Obiettivi e criteri di successo

**Obiettivo:** `ritual-check` risolve la base del diff contro il **branch di default reale del repo**,
rilevato a runtime, senza assumere alcun nome; il contratto fail-loud e `--base`/`--pages` resta invariato.

Criteri di successo (misurabili, tech-agnostici):
- **CS-1 (default `main`):** su un repo con default `main` (senza `master`), `ritual-check` **senza flag**
  risolve la base ed esegue → **0** fail-loud spurii.
- **CS-2 (default `master`):** su un repo con default `master`, comportamento **invariato** (nessuna regressione).
- **CS-3 (`--base` esplicito):** `--base <ref>` continua a **vincere** su qualunque rilevamento.
- **CS-4 (irrisolvibile → fail-loud):** quando nessun default né candidato è risolvibile (es. repo senza
  commit di mainline, HEAD staccato senza antenato comune), `ritual-check` **fallisce a voce alta** con un
  messaggio azionabile (`--base`/`--pages`) — il contratto Principio XII resta.
- **CS-5 (host-agnostico, Principio X):** **nessun** nome di branch hardcodato nel percorso di risoluzione,
  verificabile da un guard test (un repo `main`-default passa senza `--base`).

## 3. Stakeholder e attori
- **Ospite terzo con default `main`:** oggi bloccato/costretto a `--base`; è il beneficiario diretto.
- **Nodo Noetix:** segnalatore (attesa esterna: è un loro bug verificato).
- **Rituale di step (E10-FEAT-026):** la forced declaration invoca `ritual-check`; questo lo rende usabile al primo colpo.
- **Dogfood di Sertor (default `master`):** non deve regredire.

## 4. Ambito

### In ambito
- Sostituire il `master` hardcodato in `_resolve_base` con il **rilevamento del branch di default**.
- Ordine di risoluzione deterministico con **fallback** (vedi §10) e **fail-loud** finale invariato.
- Guard test host-agnostico (repo `main` e repo `master`).

### Fuori ambito
- Qualunque altra logica di `ritual-check` (euristiche distill/drift, scope `--pages`, output JSON) — invariata.
- La *forced declaration* nel blocco host-facing (E10-FEAT-026, già consegnata).
- Il *come* esatto (comando git di rilevamento, ordine dei rami): scelto in §10 (clarify) + design.

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous):** *`ritual-check` shall resolve the git diff base against the repository's
  default branch, determined at runtime, rather than a hardcoded branch name.*
- **REQ-002 (Optional):** *Where an explicit `--base <ref>` is provided, `ritual-check` shall use it and
  skip default-branch detection.*
- **REQ-003 (Event-driven):** *When the repository's default branch cannot be determined from the remote,
  `ritual-check` shall try a defined ordered set of candidate branches before failing.*
- **REQ-004 (Unwanted):** *If no diff base can be resolved (no detected default, no candidate, no
  merge-base), then `ritual-check` shall fail loud with an actionable message (pass `--base`/`--pages`),
  and shall not silently produce an empty or wrong scope.*
- **REQ-005 (Ubiquitous):** *The base-resolution path shall contain no hardcoded branch name, verifiable
  by a guard test on a repository whose default branch is `main` (Principio X).*
- **REQ-006 (Ubiquitous):** *The `--base`/`--pages` contract and the fail-loud message shape shall remain
  backward-compatible (no regression for a `master`-default repo).*

## 6. Requisiti non funzionali
- **Deterministico, offline-safe, stdlib/git only** (nessuna nuova dipendenza; già usa `subprocess` git).
- **Sola lettura** (invariato: `ritual-check` non muta il repo).
- **Zero-LLM** (invariato: il tool trova, l'agente giudica — confine D↔N).
- **Robustezza:** il rilevamento non deve **rompere** dove oggi funziona (dogfood `master`).

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo (Principio X):** host-agnostico è il cuore della feature; nessun nome di ramo assunto.
- **Vincolo (Principio XII):** fail-loud finale preservato; niente scope silenzioso.
- **Assunzione:** il branch di default è individuabile via il remote (`origin/HEAD`) sui repo con remote;
  i repo senza remote hanno un ramo locale di mainline fra i candidati noti.
- **Dipendenza:** nessuna su altre feature; **sblocca** l'usabilità della forced declaration (E10-FEAT-026) sugli ospiti `main`.
- **Riferimento:** gemella lato-tool di FEAT-038 (stesso tema «assunzione sull'ospite»); analisi
  [[setup-dichiara-presunzione-non-azione]].

## 8. Rischi
- **R-1 — `origin/HEAD` non impostato:** su alcuni cloni `refs/remotes/origin/HEAD` può mancare → serve
  fallback (mitigato da REQ-003).
- **R-2 — Ambiguità multi-candidato:** un repo con *sia* `main` sia `master` → serve un ordine
  deterministico e documentato (scelto in §10).
- **R-3 — Regressione sul dogfood `master`:** il rilevamento deve continuare a dare `master` lì → coperto da CS-2.
- **R-4 — Ambiente CI/detached:** in CI l'HEAD può essere staccato → il fail-loud onesto (CS-4) resta la rete.

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-004, REQ-005, REQ-006 (il cuore: rileva il default, preserva contratto e fail-loud, host-agnostico).
- **Should:** REQ-003 (set di fallback ordinato) — necessario per robustezza reale, ma la forma esatta è §10.
- **Could / Won't (qui):** configurare il default via `wiki.config.toml` (non necessario se il rilevamento git è affidabile).

## 10. Domande aperte — SCIOLTE (clarify, decisione 2026-07-18)
- **Ordine di risoluzione del branch di default: RISOLTO.** Precedenza deterministica:
  1. **`--base <ref>` esplicito** → vince, salta il rilevamento (REQ-002).
  2. **`git symbolic-ref --short refs/remotes/origin/HEAD`** → il default *dichiarato dal remote* (es.
     `origin/main`); merge-base con quello. È la fonte più autorevole → **copre il dogfood** (`origin/HEAD`
     del repo Sertor punta a `master`, quindi CS-2 è preservata dal path primario, non dal fallback).
  3. **Fallback a candidati ordinati** quando (2) manca (`origin/HEAD` non impostato): provare i ref
     **esistenti** in ordine — `origin/main`, `origin/master`, poi locali `main`, `master` (**`main` prima
     di `master`**: default moderno; **remoto prima di locale**) — usando il **primo** con un merge-base con HEAD.
  4. **fail-loud** se nulla risolve (REQ-004, contratto invariato).
- **Configurabilità via `wiki.config.toml`: RINVIATA (Could)** — il rilevamento git copre i casi reali; un
  override in config si aggiunge solo se emerge un ospite con layout git non standard.

---

## Commit proposto
`docs(requirements): E10-FEAT-033 — requisiti «ritual-check rileva il default branch» (EARS)`
