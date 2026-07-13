# Requisiti — Ergonomia dell'installer (multi-target · avviso non-Python · guida uv-assente)

<!-- Deriva da: E2-FEAT-010 (residuo dopo A-09 "hook portabili", coperta da
     `portabilita-hook-python/`). Scope fissato 2026-07-13 dopo mappatura dello stato attuale del
     codice. Il "pip fallback reale" è ESCLUSO e RINVIATO a E2-FEAT-006 (go-public/PyPI): le
     dipendenze interne (`sertor-core`/`sertor-install-kit`) sono membri workspace uv NON pubblicati
     e non risolvono sotto pip finché non si pubblica. Decisione utente 2026-07-13: "rinvia a
     go-public". Il "reviewer clean-code" è scorporato come superficie di governance a sé. -->

## 1. Contesto e problema (perché)

`sertor install rag`/`wiki` è oggi robusto sul percorso felice (ospite Python con `uv`), ma ha tre
attriti d'ergonomia su ospiti eterogenei, tutti verificati sul codice:

1. **Un solo assistente per comando.** `--assistant` è un flag **a valore singolo** (default `claude`),
   convertito con `AssistantId.from_str` (un valore dell'enum `AssistantId`, `assistant.py`). Per portare
   le capacità sia su Claude sia su Copilot CLI su uno stesso repo servono **due invocazioni separate**
   (dimostrato da `test_claude_and_copilot_coexist_no_double_block` e
   `test_claude_and_copilot_cli_coexist_on_one_repo`, che installano due volte). La coesistenza è
   garantita (container disgiunti `.claude/` vs `.github/`), ma **manca un percorso multi-target** in una
   sola invocazione. Nota: il **lifecycle** (`upgrade`/`uninstall`) ha già `--assistant` opzionale con
   auto-detect su **tutti** gli assistenti installati (`_installed_assistants`, `_run_lifecycle`,
   `_aggregate`) — l'install è l'unico verbo rimasto single-target.

2. **Nessun avviso su ospite non-Python.** L'installer **non rileva** il linguaggio dell'ospite: scrive
   sempre solo in container propri (`.sertor/`, `.mcp.json`, blocchi marker), quindi i sorgenti restano
   intatti anche su un progetto .NET (`test_non_python_host_sources_untouched`, `M2/SC-007`) — ma
   procede **in silenzio**. Un utente su un repo senza codice Python non riceve alcun cenno che il RAG
   indicizzerà comunque (doc/config) e che il runtime resta Python: l'assenza di segnale è un footgun di
   aspettative. Il primitivo per emettere note esiste già (`InstallReport.note()` /
   `InstallReport.notes`, precedente concreto: la nota memory-capture Copilot `_COPILOT_MEMORY_NOTE`).

3. **`uv` assente → errore secco senza alternativa.** Se `uv` non è sul PATH, `_apply_deps` fallisce
   loud (`DependencyError("uv is not available on the PATH: install it … and re-run")`) — corretto come
   fail-loud, ma il messaggio non orienta l'utente verso le opzioni reali. Il **vero** pip fallback (far
   risolvere le deps sotto pip) è **fuori scope** e rinviato a FEAT-006/go-public (le deps interne non
   sono pubblicate); qui si migliora solo l'**onestà del messaggio** (cosa fare oggi), senza fingere un
   percorso pip che non funziona.

Tutti e tre incidono su **adozione e Principio X** (host-agnostico): l'installer deve essere ergonomico
su ospiti eterogenei (più assistenti, linguaggi diversi, toolchain diverse), non solo sul caso canonico.

## 2. Obiettivi e criteri di successo

- **O1 (multi-target).** Una **sola** invocazione di `install` può depositare le capacità su **più
  assistenti** (Claude + Copilot CLI) senza collisioni.
- **O2 (avviso non-Python).** L'utente riceve un **avviso esplicito** quando l'ospite non è un progetto
  Python, senza che l'installer cambi comportamento (resta non-distruttivo).
- **O3 (onestà uv-assente).** Quando `uv` manca, il messaggio d'errore è **azionabile e onesto** sulle
  opzioni reali; nessuna promessa di un pip fallback non funzionante.

**Criteri di successo (misurabili, tech-agnostici):**
- **SC-1:** `install rag`/`wiki` con target multiplo (es. `--assistant claude,copilot-cli` o `all`)
  installa **entrambi** gli assistenti in una sola invocazione, con **container disgiunti** e **nessun
  doppio blocco** marker (stessa invariante di coesistenza dei due install separati odierni).
- **SC-2:** il report aggregato del comando multi-target elenca l'esito **per ciascun** assistente
  (riuso di `_aggregate`), e in `--json` è ispezionabile per-target.
- **SC-3:** su un ospite **non-Python** (es. solo `.sln`/`.csproj`, nessun `.py`/`pyproject.toml`),
  l'install emette **una nota** in `InstallReport.notes` che spiega il caso; i **sorgenti restano
  byte-identici** (invariante SC-007 preservato).
- **SC-4:** su un ospite **Python**, **nessuna** nota non-Python è emessa (nessun falso positivo).
- **SC-5:** quando `uv` è assente, l'errore nomina le opzioni reali (installare `uv`; il pip fallback è
  segnalato come **non ancora disponibile**, non come strada percorribile) e resta **fail-loud prima** di
  creare `.sertor/` (invariante REQ-214: nessuno stato parziale).
- **SC-6:** `sertor-core` **invariato**; le modifiche vivono in `sertor` / `sertor-install-kit`
  (installer), non nel core.
- **SC-7:** **retro-compatibilità**: `--assistant claude` (valore singolo, default) si comporta
  **esattamente** come oggi.

## 3. Stakeholder e attori

- **Utente che installa su multi-assistente** — oggi digita due comandi; ne digita uno.
- **Utente su repo non-Python** — riceve un'aspettativa corretta invece del silenzio.
- **Utente senza `uv`** — riceve una guida onesta invece di un errore secco.
- **Manutentore Sertor** — riusa i primitivi esistenti (`_aggregate`, `report.note()`), poca superficie
  nuova.

## 4. Ambito

### In ambito
- Estendere `--assistant` di **`install`** (rag + wiki, su `sertor`; speculare su `sertor-flow`) ad
  accettare **più assistenti** (CSV e/o `all`), con **loop** sul plan/execute e **report aggregato**.
- **Detection** ospite-non-Python + **avviso** via `InstallReport.note()`, non-distruttivo.
- **Miglioramento del messaggio** d'errore quando `uv` è assente (onestà sulle opzioni).
- Test di parità/regressione + aggiornamento della **documentazione utente** (`docs/install.md` e
  quick-start dove il flusso percepito cambia).

### Fuori ambito
- **Pip fallback reale** (risoluzione delle deps sotto pip) → **rinviato a E2-FEAT-006/go-public**;
  qui solo l'onestà del messaggio uv-assente. Confine registrato in questa spec e nel backlog epica.
- **Reviewer «clean-code»** (superficie di governance) → **scorporato** come feature a sé.
- Modifiche a `sertor-core`.
- Nuovi **provider LLM** o backend (altre epiche).
- Il **lifecycle** (`upgrade`/`uninstall`) già ha l'auto-detect multi-assistente: non si tocca.

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Optional).** Where the user passes more than one assistant to `install` (e.g.
  `--assistant claude,copilot-cli` or `all`), the installer shall deposit the selected capability for
  **each** named assistant in a **single invocation**.
- **REQ-002 (Ubiquitous).** A multi-target install shall keep the assistants' artifacts in **disjoint
  containers** (`.claude/**` + `CLAUDE.md` for Claude, `.github/**` + `.github/copilot-instructions.md`
  for Copilot CLI) with **no double marker block** — the same coexistence invariant as two separate
  installs today.
- **REQ-003 (Event-driven).** When an install targets multiple assistants, the system shall produce an
  **aggregated report** listing the outcome **per assistant** (human and `--json`), reusing the existing
  aggregation used by the lifecycle verbs.
- **REQ-004 (Unwanted behaviour).** If **one** target in a multi-target install fails, then the installer
  shall report that target's failure **without silently masking** the others' outcomes, and the overall
  exit status shall reflect the failure (fail-loud).
- **REQ-005 (Ubiquitous).** A single-value `--assistant` (including the default `claude`) shall behave
  **exactly as today** (full backward compatibility).
- **REQ-006 (Event-driven).** When `install` runs against a host that is **not a Python project** (no
  `pyproject.toml` and no `.py` sources under the host root, per a deterministic heuristic), the
  installer shall emit an **explicit note** in `InstallReport.notes` explaining that the RAG will still
  index available files but the runtime requires Python.
- **REQ-007 (Ubiquitous).** The non-Python note shall be **advisory only**: it shall **not** change the
  installer's behaviour and shall **not** modify the host's sources (the SC-007 byte-identity invariant
  is preserved).
- **REQ-008 (Unwanted behaviour).** If the host **is** a Python project, then the installer shall **not**
  emit the non-Python note (no false positive).
- **REQ-009 (Unwanted behaviour).** If `uv` is **absent** from the PATH when dependencies must be
  installed, then the installer shall fail **loud and early** (before creating `.sertor/`, invariant
  REQ-214) with an **actionable, honest** message naming the real options — install `uv`; the pip path
  is flagged as **not yet available** (pending publication), **not** presented as a working alternative.
- **REQ-010 (Ubiquitous).** The change shall leave `sertor-core` **unmodified**; the logic shall live in
  the installer packages (`sertor`, `sertor-install-kit`), never in the core library.
- **REQ-011 (Ubiquitous).** A **verification** shall exist (runnable offline in CI) covering: a
  single-command multi-target install (coexistence + aggregated report), the non-Python note (present on
  non-Python host, absent on Python host, sources untouched), and the improved uv-absent message.
- **REQ-012 (Event-driven).** When the multi-target install and the non-Python note change the
  user-perceived flow, the **user documentation** (`docs/install.md`, and the per-assistant quick-starts
  if the perceived flow changes) shall be updated in the **same step** (host-facing DoD rule 3).

## 6. Requisiti non funzionali

- **NFR-1 (retro-compatibilità):** nessuna rottura del contratto CLI esistente (`--assistant <single>`
  invariato); l'estensione è puramente **additiva**.
- **NFR-2 (riuso, non duplicazione):** riusare `_aggregate`/`_installed_assistants` e `InstallReport.
  note()` esistenti invece di reintrodurre logica multi-assistente parallela (Principio I, poca
  superficie).
- **NFR-3 (host-agnostico):** la detection non-Python è deterministica e OS-indipendente; nessun path
  hardcodato (Principio X).
- **NFR-4 (non-distruttività):** l'avviso non-Python non altera alcun file dell'ospite (Principio VI /
  CS-4 dell'epica).
- **NFR-5 (install≠run):** nessuna delle modifiche avvia da sola un'ingestione (Principio VI).
- **NFR-6 (fail-loud):** l'errore uv-assente resta un errore reale (exit ≠ 0), non un warning silenzioso
  (Principio XII).

## 7. Vincoli, assunzioni e dipendenze

- **Dipendenza (coesistenza):** riusa il design a **container disgiunti** di `AssistantProfile.
  for_assistant`; il multi-target è un **loop** su quel design, non un nuovo meccanismo di merge.
- **Dipendenza (aggregazione):** riusa `_aggregate` (oggi usato solo dal lifecycle) per il report
  per-target.
- **Assunzione (detection):** «progetto Python» è determinabile con un'euristica deterministica
  (presenza di `pyproject.toml` o di file `.py` sotto la root dell'ospite, con esclusione dei container
  Sertor `.sertor/`); i falsi positivi/negativi accettabili si fissano al plan.
- **Vincolo (pip rinviato):** il pip fallback reale NON è in questa feature; il messaggio uv-assente non
  deve implicare che pip funzioni oggi.
- **Vincolo (dogfood/asset):** se cambiano asset host-facing byte-copiati (docs incluse), aggiornare le
  guardie di sync dogfood↔bundle di conseguenza.

## 8. Rischi

- **R-1 (multi-target parziale):** un target fallisce a metà lasciando l'altro monco. *Mitigazione:*
  REQ-004 (report per-target, exit fedele) + i due install restano indipendenti (container disgiunti).
- **R-2 (detection non-Python imprecisa):** falso positivo su un repo poliglotta con Python marginale, o
  falso negativo su un monorepo. *Mitigazione:* euristica semplice e documentata; la nota è **advisory**
  (nessun effetto), quindi il costo di un errore è basso.
- **R-3 (retro-compatibilità del flag):** il parsing plurale rompe l'uso single-value. *Mitigazione:*
  REQ-005 + test di regressione sul valore singolo/default.
- **R-4 (aspettativa pip):** il messaggio uv-assente lascia intendere che pip funzioni. *Mitigazione:*
  REQ-009 (pip esplicitamente «non ancora disponibile»).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-002, REQ-005, REQ-006, REQ-007, REQ-008, REQ-010, REQ-011.
- **Should:** REQ-001, REQ-003, REQ-004, REQ-009, REQ-012, NFR-1..6.
- **Could:** `all` come alias oltre alla forma CSV (se il plan lo ritiene ergonomico); sintassi
  `--assistant` ripetuta (`--assistant claude --assistant copilot-cli`) in aggiunta al CSV.

## 10. Domande aperte

- **DA-1 [design→plan]:** sintassi multi-target — **CSV** (`--assistant claude,copilot-cli`), **`all`**,
  **flag ripetuto**, o una combinazione? *Raccomandazione:* CSV + `all` (semplici, testabili in un
  punto: un parser plurale su `AssistantId`).
- **DA-2 [design→plan]:** euristica esatta «progetto Python» — solo `pyproject.toml`? anche un qualsiasi
  `.py` sotto la root (con quale profondità/esclusioni)? *Raccomandazione:* `pyproject.toml` **oppure**
  almeno un `.py` fuori dai container Sertor, profondità limitata; fissare al plan.
- **DA-3 [scope]:** `sertor-flow` deve ricevere lo **stesso** multi-target in questa feature, o basta
  `sertor` (rag+wiki) e `sertor-flow` segue in un follow-up? *Raccomandazione:* includere `sertor-flow`
  per simmetria (stesso seam `--assistant`), se il costo è contenuto.
- **DA-4 [design]:** il messaggio uv-assente deve **anche** menzionare esplicitamente la data/condizione
  di sblocco pip (go-public), o restare generico («pip non ancora supportato»)? *Raccomandazione:*
  generico + onesto, senza date.

---

**Commit proposto:** `docs(requirements): E2-FEAT-010 residuo — ergonomia installer (multi-target · avviso non-Python · guida uv-assente); pip rinviato a FEAT-006`
